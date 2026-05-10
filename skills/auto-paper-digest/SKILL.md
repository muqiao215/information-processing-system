---
name: auto-paper-digest
description: Operate the local Auto Paper Digest project at `E:\web\tools\auto-paper-digest`, including Hugging Face paper fetching, arXiv PDF download, NotebookLM login reuse, video generation, Hugging Face publishing, Douyin publishing, status checks, and full weekly pipeline runs. Use when the user mentions APD, auto-paper-digest, paper digest, NotebookLM paper videos, Hugging Face paper scraping, or asks to run or troubleshoot the paper-to-video workflow.
---

# Auto Paper Digest

Use this skill to operate the local `Auto Paper Digest` repo:

- repo: `E:\web\tools\auto-paper-digest`
- CLI entry: `python -m apd.cli ...`
- wrapper in this skill: `scripts/apd.ps1`

This skill is for running the existing pipeline, not rewriting the project from scratch.

## When to Use

Trigger on requests like:

- "跑一下 auto-paper-digest"
- "抓本周 HF 论文并下载 PDF"
- "用 NotebookLM 生成论文讲解视频"
- "复用 NotebookLM 登录态"
- "把视频发布到 HuggingFace / 抖音"
- "看看 APD 现在处理到哪一步"
- "把 auto-paper-digest 改造成长期可用工作流"

## Workflow

### 1. First-time or login repair

Google / NotebookLM login:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" login
```

Douyin login:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" douyin-login
```

### 2. Fetch papers

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" fetch --week 2026-01 --max 20
```

For a single date:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" fetch --date 2026-01-08 --max 20
```

### 3. Download PDFs

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" download --week 2026-01
```

### 4. Run NotebookLM generation

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" nblm --week 2026-01 --max 10
```

For first-time login or visual debugging:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" nblm --week 2026-01 --headful
```

### 5. Run the full weekly pipeline

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" run --week 2026-01 --max 10
```

### 6. Publish outputs

Hugging Face + digest:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" publish --week 2026-01
```

Douyin:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" publish-douyin --week 2026-01 --headful
```

### 7. Status and repair

Show status:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" status --week 2026-01
```

Delete stale NotebookLM notebooks:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\11614\.agents\skills\auto-paper-digest\scripts\apd.ps1" clean-nblm --yes
```

## Operating Rules

- Default to operating the repo in place at `E:\web\tools\auto-paper-digest`.
- Prefer `python -m apd.cli ...` through the wrapper instead of guessing ad hoc scripts.
- Reuse NotebookLM login state when possible instead of forcing repeated login.
- Treat `.env` values as required for publish steps; do not invent missing tokens.
- For troubleshooting, start with `status`, then inspect the specific phase command.

## References

- Read [references/commands.md](references/commands.md) for the command map and example flows.
- Read [references/env.md](references/env.md) for environment variables and NotebookLM profile reuse.

