"""Offline regressions for the public workspace and source-preservation boundary."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills/process_docs/scripts"))
import init_workspace
import _config
from extract_document import extract
from fold_archives import fold_text
from validate_generated import archive_blocks, unfolded_archives, tex_render_errors
from orchestrate_workers import validate_manifest
from kb_tree import scan
import render_rmd


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kbkit_portable_")
        self.base = Path(self.temp.name)
        self.root = self.base / "library with 空格"

    def tearDown(self):
        self.temp.cleanup()

    def install(self, **kw):
        init_workspace.install(self.root, **kw)
        return _config.load(self.root / "kb.config.yaml")

    def test_dry_run_does_not_create_directory(self):
        result = init_workspace.install(self.root, dry_run=True)
        self.assertTrue(result["files_to_write"])
        self.assertFalse(self.root.exists())

    def test_reinstall_preserves_user_config_and_documents(self):
        self.install()
        config = self.root / "kb.config.yaml"
        config.write_text("KB_ROOT: .\nOUTPUT_LANGUAGE: zh-CN\n")
        catalog = self.root / "catalog.md"
        catalog.write_text("My catalog")
        init_workspace.install(self.root)
        self.assertEqual(_config.load(config)["OUTPUT_LANGUAGE"], "zh-CN")
        self.assertEqual(catalog.read_text(), "My catalog")
        for path in (self.root / ".agents/skills").iterdir():
            self.assertTrue(path.is_symlink())
            self.assertTrue(path.resolve().is_relative_to(self.root.resolve()))

    def test_changed_managed_file_aborts_before_writes(self):
        self.install()
        managed = self.root / "kb.py"
        managed.write_text("local edits")
        before = (self.root / ".kbkit/install.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "locally edited"):
            init_workspace.install(self.root)
        self.assertEqual(managed.read_text(), "local edits")
        self.assertEqual((self.root / ".kbkit/install.json").read_bytes(), before)

    def test_nonempty_or_symlinked_destination_is_refused(self):
        self.root.mkdir()
        (self.root / "personal.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            init_workspace.install(self.root)
        self.assertEqual(list(p.name for p in self.root.iterdir()), ["personal.txt"])

    def test_reserved_symlink_aborts_update(self):
        self.install()
        (self.root / ".trash").rmdir()
        (self.root / ".trash").symlink_to(self.base / "external")
        before = (self.root / ".kbkit/install.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "reserved"):
            init_workspace.install(self.root)
        self.assertFalse((self.base / "external").exists())
        self.assertEqual((self.root / ".kbkit/install.json").read_bytes(), before)

    def test_config_unknown_duplicate_and_path_escape_fail(self):
        self.install()
        path = self.root / "kb.config.yaml"
        for text in ("UNKNOWN: true\n", "KB_ROOT: .\nKB_ROOT: elsewhere\n",
                     "WORKER_TIMEOUT: true\n", "INPUT_DIR: ../outside\n",
                     "OUTPUT_LANGUAGE: nonsense\n", "RMD_WHEN_NO_RENDER: render\n"):
            with self.subTest(text=text):
                path.write_text(text)
                with self.assertRaises(_config.ConfigError):
                    _config.load(path)

    def test_installed_config_is_bound_to_workspace_from_other_cwd(self):
        self.install(backend="codex")
        proc = subprocess.run([sys.executable, str(self.root / "kb.py"), "config"],
                              cwd=self.base, capture_output=True, text=True,
                              env={k: v for k, v in os.environ.items() if k != "KB_CONFIG"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(Path(json.loads(proc.stdout)["KB_ROOT"]), self.root.resolve())
        self.assertFalse((self.root / ".claude/skills").exists())

    def test_tree_does_not_follow_symlink_loops(self):
        cfg = self.install()
        (self.root / "loop").symlink_to(self.root, target_is_directory=True)
        self.assertEqual(scan(cfg)["documents"], [])

    def test_manifest_rejects_external_duplicate_and_failed_images(self):
        cfg = self.install()
        entries = [{"page": 1, "path": "images/a.png"}]
        for meta in ({"image_files": [{"page": 1, "path": "../outside.png"}]},
                     {"image_files": entries * 2}, {"image_files": entries, "failed_images": [1]}):
            with self.subTest(meta=meta), self.assertRaises(ValueError):
                validate_manifest(meta, self.root, cfg)


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kbkit_extract_")
        self.root = Path(self.temp.name)
        path = self.root / "kb.config.yaml"
        path.write_text("KB_ROOT: .\n")
        self.cfg = _config.load(path)

    def tearDown(self):
        self.temp.cleanup()

    def run_source(self, name):
        source = ROOT / "examples/sources" / name
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        result = extract(source, self.root / name, self.cfg)
        self.assertEqual(result["source_sha256"], before)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        self.assertFalse(result["failed_images"], result)
        return result, Path(result["text_file"]).read_text()

    def test_pdf_all_pages_tables_and_zero(self):
        result, text = self.run_source("sample.pdf")
        self.assertEqual(len(result["image_files"]), 2)
        for value in ("Alpha", "1.25", "0.75", "2.00", "0.00", "Validate", "Revise"):
            self.assertIn(value, text)

    def test_docx_preserves_interleaving(self):
        result, text = self.run_source("sample.docx")
        values = ("Paragraph before", "Alpha", "Paragraph after the table", "![Image 1]", "Paragraph after the image")
        self.assertEqual([text.index(x) for x in values], sorted(text.index(x) for x in values))
        self.assertEqual(len(result["image_files"]), 1)

    def test_html_data_image_and_table_order(self):
        result, text = self.run_source("sample.html")
        values = ("Before the table", "Alpha", "0.00", "before the inline image", "![Image 1", "After the image")
        self.assertEqual([text.index(x) for x in values], sorted(text.index(x) for x in values))
        self.assertEqual(len(result["image_files"]), 1)
        self.assertNotIn("data:image", text)

    def test_html_remote_image_never_fetches_network(self):
        source = self.root / "remote.html"
        source.write_text('<p>Keep text.</p><img src="https://example.com/a.png" alt="Missing diagram">')
        result = extract(source, self.root / "out", self.cfg)
        self.assertEqual(len(result["failed_images"]), 1)
        self.assertTrue((self.root / "out/.extraction_failed.json").exists())

    def test_notebook_saved_outputs_with_null_execution_count(self):
        result, text = self.run_source("sample.ipynb")
        self.assertFalse(result["notebook"]["outputs_cleared"])
        self.assertIn("2.0", text)
        self.assertIn("print(1.25 + 0.75)", text)
        self.assertEqual(len(result["image_files"]), 1)

    def test_notebook_code_is_not_executed(self):
        source = self.root / "sentinel.ipynb"
        marker = self.root / "SHOULD_NOT_EXIST"
        source.write_text(json.dumps({"nbformat": 4, "cells": [{"cell_type": "code", "source": f"open({str(marker)!r}, 'w').write('bad')", "outputs": []}]}))
        result = extract(source, self.root / "out", self.cfg)
        self.assertFalse(marker.exists())
        self.assertTrue(result["notebook"]["outputs_cleared"])

    def test_existing_output_is_not_overwritten(self):
        output = self.root / "out"
        output.mkdir()
        (output / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "new or empty"):
            extract(ROOT / "examples/sources/quickstart.md", output, self.cfg)
        self.assertEqual((output / "keep.txt").read_text(), "keep")


class ArchiveAndMathTests(unittest.TestCase):
    def test_folding_is_lossless_idempotent_and_ignores_nested_fences(self):
        text = '````markdown\n```text\nexample\n```\n````\n\n```text\nExact $ raw > <details>\n```\n'
        folded, count = fold_text(text)
        self.assertEqual(count, 1)
        self.assertEqual(fold_text(folded), (folded, 0))
        self.assertEqual(unfolded_archives(folded), [])
        self.assertIn('```text\nExact $ raw > <details>\n```', folded)
        self.assertEqual(len(archive_blocks(text)), 1)

    def test_summary_without_details_is_not_folded(self):
        text = '<summary>Fake wrapper</summary>\n\n```text\nraw\n```'
        self.assertEqual(unfolded_archives(text), [3])

    def test_unclosed_fence_stays_unresolved(self):
        text = '```text\nraw'
        self.assertEqual(fold_text(text), (text, 0))
        self.assertEqual(unfolded_archives(text), [1])

    def test_formula_check_distinguishes_math_code_and_currency(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "math.md"
            path.write_text("A $45 price.\n\n" + r"`$invalid$`; $\dbinom{n}{k}$." + "\n")
            bad, count, skip = tex_render_errors(path)
            self.assertIsNone(skip)
            self.assertEqual((bad, count), ([], 1))
            path.write_text(r"$\binom{n}{k$" + "\n")
            bad, count, skip = tex_render_errors(path)
            self.assertTrue(bad)
            self.assertIsNone(skip)


class RmdTests(unittest.TestCase):
    def test_detection_never_executes_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.Rmd"
            source.write_text("```{r}\nstop('must not execute')\n```\n")
            with patch.object(sys, "argv", ["render_rmd.py", str(source)]), \
                    patch.object(render_rmd, "r_toolchain", return_value={}), \
                    patch.object(render_rmd, "render") as render, \
                    self.assertRaises(SystemExit) as result:
                render_rmd.main()
            self.assertEqual(result.exception.code, 0)
            render.assert_not_called()

    def test_render_rejects_stale_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "old.html").write_text("old")
            with patch.object(render_rmd.shutil, "which", return_value="Rscript"), \
                    patch.object(render_rmd.subprocess, "run") as call:
                result = render_rmd.render("source.Rmd", tmp, "html")
            self.assertFalse(result["ok"])
            call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
