# Publishing to GitHub / 发布步骤

This guide describes manual next steps. Preparing this repository or running its
release builder does not create a GitHub repository, upload files or make them public.

## 1. Review the clean release

Run the tests and static gate, then build the archive:

```sh
python -m unittest discover -s tests -v
python scripts/validate_release.py
python scripts/build_release.py
```

The `dist/` ZIP contains only `release-files.txt` entries. Its neighboring
`.zip.sha256` and `release-manifest.json` record archive and per-file hashes.
Extract that clean ZIP into a separate folder for the first upload. Do not upload
`_local/`, personal workspaces, account logs, source backups or a parent directory.
Inspect the bilingual README, examples, LICENSE and THIRD_PARTY_NOTICES first.

## 2. Start fresh Git history

From the extracted `knowledge-base-kit` folder, inspect the intended commit
identity with `git config user.name` and `git config user.email`. Set the identity
you want public; a GitHub no-reply email is an option. Do not import history from
a private knowledge base.

```sh
git init -b main
git add --pathspec-from-file=release-files.txt
git diff --cached --check
git diff --cached --stat
git status --short
```

Review the exact staged file list, then make the initial commit:

```sh
git commit -m "Initial public toolkit release"
```

## 3. Upload privately and run CI

Confirm the GitHub account and repository name. Suggested repository name:
`knowledge-base-kit`. Suggested description:
“Source-backed Markdown knowledge bases for Claude Code and Codex.”

After explicitly choosing that account/name, GitHub CLI users can run:

```sh
gh repo create knowledge-base-kit --private --source=. --remote=origin --push
```

Alternatively, create an empty private repository in GitHub and follow its
provided remote/push instructions. Do not pre-create an unrelated README/license
in the remote. See GitHub's official
[local repository import guide](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

Wait for every configured Actions job. Fix failures and review the repository
contents as rendered on GitHub. No model credentials are needed in Actions.
Enable private vulnerability reporting and available secret-scanning protections.
The latter are useful checks, not a substitute for inspecting the upload list.

## 4. Make public and create the release

When the owner approves the exact repository, change visibility in GitHub's
repository settings. Review GitHub's
[visibility consequences](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
before confirming. Public disclosure is not reliably reversible by changing it
back to private.

Create a tag such as `v0.1.1`, push it, and create a GitHub Release using the
matching prepared notes, for example [v0.1.1](release-notes-v0.1.1.md). Attach the clean ZIP and
its checksum if desired. Set useful topics such as `knowledge-base`, `markdown`,
`document-processing`, `claude-code` and `codex`. Add the actual repository link
to any announcement only after the public URL exists.

## 中文执行顺序

先从发布 ZIP 建立干净目录，再检查提交身份与文件清单；新建 Git 历史，不带私人库历史。
建议先上传 private 仓库，等 CI 和 GitHub 页面审阅通过，再由仓库拥有者确认改为 public，
最后打标签和发布 Release。这里的命令是操作指南，准备文件本身不会自动上传或公开。
