# APD command map

Repo:

- `E:\web\tools\auto-paper-digest`

Primary CLI:

- `python -m apd.cli`

## Core commands

- `fetch`
  - get papers from Hugging Face by week or date
- `download`
  - download arXiv PDFs
- `nblm`
  - upload PDFs to NotebookLM and generate video overviews
- `run`
  - full pipeline: fetch -> download -> nblm -> digest
- `status`
  - inspect processing state
- `publish`
  - upload videos to Hugging Face and generate markdown digest
- `publish-douyin`
  - publish videos to Douyin Creator Studio
- `login`
  - NotebookLM / Google login
- `douyin-login`
  - Douyin Creator Studio login
- `clean-nblm`
  - remove NotebookLM notebooks

## Recommended flows

### Weekly batch

1. `fetch --week 2026-01 --max 20`
2. `download --week 2026-01`
3. `nblm --week 2026-01 --max 10`
4. `publish --week 2026-01`
5. `publish-douyin --week 2026-01 --headful`

### First-time setup

1. `login`
2. `douyin-login`
3. `status --week 2026-01`

### Lightweight smoke

1. `fetch --week 2026-01 --max 3`
2. `download --week 2026-01 --max 3`
3. `nblm --week 2026-01 --max 1 --headful`

