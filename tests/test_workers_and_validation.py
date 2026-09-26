"""Worker and document tests: observable CLI, file and validation behavior."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/process_docs/scripts"))
import init_workspace
import _config
import check_agent_setup
import orchestrate_workers as workers
import validate_generated as validate
import worker_backends as backends


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kbkit_test_")
        self.root = Path(self.temp.name)
        init_workspace.install(self.root)
        self.work = self.root / "工作 space"
        self.work.mkdir()
        self.image = self.work / "image.png"
        self.image.write_bytes((Path(__file__).resolve().parents[1] / "examples/sources/workflow.png").read_bytes())
        self.output = self.work / ".image_descriptions_page_1.md"
        self.cfg = _config.load(self.root / "kb.config.yaml")
        self.cfg.update(KB_ROOT=str(self.root), WORKER_TIMEOUT=1)

    def tearDown(self):
        self.temp.cleanup()

    def fake_cli(self, backend, mode="ok"):
        path = self.root / (backend + "_" + mode)
        trace = self.root / "trace.json"
        path.write_text(f'''#!{sys.executable}
import json,os,re,sys
from pathlib import Path
p=sys.stdin.read(); args=sys.argv[1:]
trace=Path({str(trace)!r}); count=json.loads(trace.read_text())["count"]+1 if trace.exists() else 1
trace.write_text(json.dumps({{"args":args,"cwd":os.getcwd(),"count":count}}))
backend={backend!r}; mode={mode!r}
if mode=="startup":
 print("Error: failed to initialize in-process app-server client: Operation not permitted (os error 1)",file=sys.stderr)
 sys.exit(1)
if mode in ("auth","quota","error"):
 message={{"auth":"Not logged in","quota":"You've hit your usage limit","error":"Temporary server failure"}}[mode]
 print(json.dumps({{"is_error":True,"result":message}}) if backend=="claude" else json.dumps({{"type":"turn.failed","error":{{"message":message}}}}))
 sys.exit(0)
out=Path(args[args.index("--output-last-message")+1]) if backend=="codex" else None
text="## Page 1\\n\\nTable Alpha=1.25; Beta=0.75; arrow Intake to Validate; pass to Publish."
if mode=="wrong":text=text.replace("Page 1","Page 2")
if mode=="empty":text=""
if mode=="missing":text=""
if out and mode!="missing":out.write_text(text)
print(json.dumps({{"is_error":False,"result":text}}) if backend=="claude" else json.dumps({{"type":"turn.completed"}}))
''')
        path.chmod(0o755)
        return str(path)

    def describe(self, backend, mode="ok"):
        return backends.describe_image(self.cfg, backend, self.fake_cli(backend, mode),
                                       self.image, self.output, "fixture", 1,
                                       workers.DESCRIPTION_REQUIREMENTS)

    def test_both_cli_protocols_publish_current_output(self):
        for backend in backends.BACKENDS:
            with self.subTest(backend=backend):
                self.assertEqual(self.describe(backend), (True, None))
                self.assertTrue(workers.output_is_valid(self.output))
                trace = json.loads((self.root / "trace.json").read_text())
                self.assertFalse(Path(trace["cwd"]).is_relative_to(self.work))
                if backend == "codex":
                    i = trace["args"].index("--image")
                    self.assertEqual(Path(trace["args"][i + 1]).name, "input.png")
                    self.assertEqual(trace["args"][i + 2:], ["--", "-"])
                    self.assertIn("read-only", trace["args"])
                else:
                    self.assertIn("--restricted", trace["args"])
                    self.assertNotIn("bypassPermissions", trace["args"])
                    self.assertEqual(trace["args"][trace["args"].index("--tools") + 1], "Read")

    def test_bad_results_do_not_overwrite_good_file(self):
        self.output.write_text("Existing accepted output")
        for backend in backends.BACKENDS:
            for mode in ("error", "empty", "missing", "wrong"):
                with self.subTest(backend=backend, mode=mode):
                    ok, error = self.describe(backend, mode)
                    self.assertFalse(ok)
                    self.assertTrue(error)
                    self.assertEqual(self.output.read_text(), "Existing accepted output")

    def test_malformed_or_incomplete_protocol_is_rejected(self):
        for payload in ("not json", "[]", "{}", '{"result":"saved"}'):
            with self.assertRaises(ValueError):
                backends.parse_claude(payload)
        with self.assertRaises(RuntimeError):
            backends.parse_codex('{"type":"turn.started"}')
        with self.assertRaises(RuntimeError):
            backends.parse_codex('{"type":"item.completed","item":{"type":"command_execution"}}')
        with self.assertRaises(ValueError):
            backends.parse_codex('{"type":"item.completed","item":null}')

    def test_account_errors_abort_instead_of_retry(self):
        for backend in backends.BACKENDS:
            for mode, exception in (("auth", backends.AuthError), ("quota", backends.QuotaError)):
                with self.subTest(backend=backend, mode=mode), self.assertRaises(exception):
                    workers.process_page(self.cfg, self.fake_cli(backend, mode), str(self.image),
                                         1, str(self.work), "fixture", backend=backend)

    def test_missing_image_never_calls_a_model(self):
        self.image.unlink()
        result = workers.process_page(self.cfg, "not-a-command", str(self.image), 1,
                                      str(self.work), "fixture", backend="codex")
        self.assertIn("error", result[1])

    def test_host_startup_denial_aborts_without_retry(self):
        with self.assertRaises(backends.StartupError):
            workers.process_page(self.cfg, self.fake_cli("codex", "startup"), str(self.image),
                                 1, str(self.work), "fixture", backend="codex")
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 1)

    def test_input_or_backend_change_does_not_reuse_codex_cache(self):
        cli = self.fake_cli("codex")
        self.output.write_text("## Page 1\n\n" + "legacy Claude description " * 5)
        run = lambda: workers.process_page(self.cfg, cli, str(self.image), 1, str(self.work),
                                            "fixture", backend="codex")
        self.assertEqual(run(), {1: True})
        self.assertEqual(run(), {1: True})
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 1)
        self.image.write_bytes(self.image.read_bytes() + b"changed trailing bytes")
        self.assertEqual(run(), {1: True})
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 2)

    def test_transient_failure_retries_only_once(self):
        workers.process_page(self.cfg, self.fake_cli("codex", "error"), str(self.image),
                             1, str(self.work), "fixture", backend="codex")
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 2)

    def test_unprovenanced_claude_cache_is_not_trusted(self):
        cli = self.fake_cli("claude")
        self.output.write_text("## Page 1\n\n" + "legacy Claude description " * 5)
        run = lambda: workers.process_page(self.cfg, cli, str(self.image), 1, str(self.work),
                                            "fixture", backend="claude")
        self.assertEqual(run(), {1: True})
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 1)
        # A damaged record must not turn a newer backend's output into trusted legacy output.
        (self.work / ".worker_results.json").write_text("incomplete json")
        self.assertEqual(run(), {1: True})
        self.assertEqual(run(), {1: True})
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 2)

    def test_cli_argument_order_force_and_unknown_backend(self):
        self.cfg["CODEX_CLI"] = self.fake_cli("codex")
        (self.work / ".extraction_metadata.json").write_text(json.dumps({
            "image_files": [{"page": 1, "path": str(self.image)}], "total_pages": 1}))
        for args in (["--backend", "codex", str(self.work)],
                     [str(self.work), "--force", "--backend", "codex"]):
            with patch.object(sys, "argv", ["orchestrate_workers.py"] + args), \
                    patch.object(workers._config, "load", return_value=self.cfg):
                self.assertEqual(workers.main(), 0)
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 2)
        with patch.object(sys, "argv", ["orchestrate_workers.py", str(self.work), "--backend", "unknown"]), \
                self.assertRaises(SystemExit) as result:
            workers.main()
        self.assertEqual(result.exception.code, 2)
        self.assertEqual(json.loads((self.root / "trace.json").read_text())["count"], 2)

    def test_invalid_individual_page_is_not_clean_merge(self):
        self.output.write_text("## Page 2\n\n" + "wrong page " * 8)
        self.assertFalse(workers.merge_descriptions(str(self.work), {1: True}, 1))

    @unittest.skipIf(os.name == "nt", "Process-group regression exercises the POSIX deployment")
    def test_timeout_stops_child_process(self):
        pid_file = self.root / "child.pid"
        code = ("import subprocess,sys,time;from pathlib import Path;"
                "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
                f"Path({str(pid_file)!r}).write_text(str(p.pid));time.sleep(60)")
        with self.assertRaisesRegex(RuntimeError, "Timeout"):
            backends.run_cli([sys.executable, "-c", code], "", self.work, 1)
        state = subprocess.run(["ps", "-o", "stat=", "-p", pid_file.read_text()],
                               capture_output=True, text=True).stdout.strip()
        self.assertTrue(not state or state.startswith("Z"), state)

    def document(self, folder, kind="normal", extra=""):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "source.md").write_text("Known fact: total is 2.00.")
        full = ("---\nsource: source.md\nformat: md\nconverted: 2026-09-09\n"
                "category: course\ndescription: 测试文档\ndoc_type: " + kind + "\n" + extra +
                "---\n\n# Fixture\n\n## Table of Contents\n\n- [Facts](#facts)\n\n"
                "## Facts\n\nKnown fact: total is 2.00.\n\n## Related Documents\n")
        summary = ("# Fixture - Operation Guide\n\n## Overview\n\n测试文档。\n\n"
                   "## Prerequisites\n\n无。\n\n## Key Steps\n\n### Step 1: Verify\n\n核对总值。\n\n"
                   "## Configuration Reference\n\nTotal: 2.00\n\n## Common Pitfalls\n\n不要漏项。\n\n"
                   "## References\n\n[全文](full.md#facts)\n")
        (folder / "full.md").write_text(full)
        (folder / "summary.md").write_text(summary)

    def test_valid_draft_and_filed_document(self):
        self.document(self.work)
        self.assertTrue(validate.check(self.work, self.cfg)["ok"])
        self.assertTrue(validate.check(self.work, self.cfg, target="course/fixture")["ok"])
        final = self.root / "course/fixture"
        final.parent.mkdir()
        shutil.copytree(self.work, final)
        self.assertTrue(validate.check(final, self.cfg, filed=True)["ok"])
        (final / "source.md").unlink()
        self.assertFalse(validate.check(final, self.cfg, filed=True)["ok"])

    def test_translated_heading_and_missing_anchor_are_rejected(self):
        self.document(self.work)
        p = self.work / "summary.md"
        p.write_text(p.read_text().replace("## References", "## 参考资料"))
        self.assertFalse(validate.check(self.work, self.cfg)["ok"])
        self.document(self.work)
        p.write_text(p.read_text().replace("full.md#facts", "full.md#missing"))
        self.assertFalse(validate.check(self.work, self.cfg)["ok"])

    def test_inline_code_is_not_a_document_link(self):
        self.document(self.work)
        p = self.work / "full.md"
        p.write_text(p.read_text() + "\nRegex example: `[a-z](\\.[0-9]+)` is code.\n")
        p.write_text(p.read_text() + "\n> ```\n> [a-z](\\.[0-9]+)\n> ```\n")
        self.assertTrue(validate.check(self.work, self.cfg)["ok"])

    def test_cross_links_use_intended_location_and_cannot_escape(self):
        self.document(self.work)
        self.document(self.root / "course/neighbor")
        p = self.work / "summary.md"
        p.write_text(p.read_text() + "\n[Neighbor](../neighbor/summary.md)\n")
        self.assertTrue(validate.check(self.work, self.cfg)["deferred_links"])
        self.assertTrue(validate.check(self.work, self.cfg, target="course/fixture")["ok"])
        p.write_text(p.read_text() + "\n[Outside](../../../outside.md)\n")
        self.assertFalse(validate.check(self.work, self.cfg, target="course/fixture")["ok"])

    def test_parent_child_and_image_coverage(self):
        self.document(self.work, "parent", "children:\n  - child\n")
        self.assertFalse(validate.check(self.work, self.cfg)["ok"])
        self.document(self.work / "child", "child", "parent: group\n")
        self.assertTrue(validate.check(self.work, self.cfg, target="course/group")["ok"])
        self.assertTrue(validate.check(self.work / "child", self.cfg, target="course/group/child")["ok"])
        (self.work / ".extraction_metadata.json").write_text(json.dumps({"image_files": [{"page": 1}]}))
        self.assertFalse(validate.check(self.work, self.cfg)["ok"])
        (self.work / ".image_descriptions.md").write_text("## Page 1\n\nDescription.\n")
        self.assertTrue(validate.check(self.work, self.cfg)["ok"])

    def test_missing_other_backend_is_optional(self):
        with patch.object(check_agent_setup, "find_cli", side_effect=lambda cfg, name: sys.executable if name == "codex" else None):
            cfg = dict(self.cfg, SKILL_ROOT_ABS=str(self.root / ".kbkit/skills/process_docs"), READER_SKILL=str(self.root / ".kbkit/skills/kb"))
            result = check_agent_setup.check("codex", cfg=cfg, login=False)
        self.assertTrue(result["ok"], result)
        other = next(x for x in result["checks"] if x["check"] == "claude CLI")
        self.assertFalse(other["ok"])
        self.assertFalse(other["required"])

    def test_missing_tex_tools_is_not_a_pass(self):
        self.document(self.work)
        with patch.object(validate, "tex_render_errors", return_value=([], 0, "tool missing")):
            result = validate.check(self.work, self.cfg)
        self.assertFalse(result["ok"])
        self.assertTrue(result["unchecked"])

    def test_corrupt_image_never_calls_a_model(self):
        self.image.write_bytes(b"not an image" * 200)
        with patch.object(workers, "launch_worker") as launch:
            result = workers.process_page(self.cfg, "unused", str(self.image), 1,
                                          str(self.work), "fixture", backend="codex")
        self.assertIn("error", result[1])
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
