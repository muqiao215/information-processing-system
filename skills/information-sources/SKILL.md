---
name: information-sources
description: Use when the user asks about 信息来源, source routing, source priority, source of truth, latest/current verification, source attribution, cite sources, what is your source, official source, primary source, which source should I trust, 可靠来源, 用什么工具找资料, 先用哪个工具, fallback 顺序, 失败后换什么工具, 读网页正文, 读链接, 读推文, 读 PDF, 读图片, 读 RSS, 读 RSS 失败怎么办, 看 GitHub 仓库, 读 GitHub README, 提取视频信息, or when deciding between Jina Reader, gh, yt-dlp, mcporter, and feedparser.
---

# Information Sources

Use this skill to choose the right source and tool before gathering information.

Think in two layers:

1. Pick the source of truth
2. Pick the access path to that source

Do not collapse these into one decision.

## First Response Shape

When this skill is used, prefer answering in this order:

1. `Source of truth: ...`
2. `Preferred tool: ...`
3. `Fallback: ...`
4. `Freshness note: ...` only when the user asks for latest/current/recent information

Keep this first response short and operational.
Lead with the routing decision before extra explanation.

## First Response Examples

Use these as the default shape when the user mainly needs routing.

### GitHub repo metadata

- Source of truth: GitHub repository metadata
- Preferred tool: `gh`
- Fallback: `Jina Reader` for direct GitHub page reading

### GitHub README body

- Source of truth: GitHub README
- Preferred tool: `gh` first
- Fallback: `Jina Reader` for direct README body reading if `gh` is awkward or unavailable

### RSS feed parsing

- Source of truth: Feed URL
- Preferred tool: `feedparser`
- Fallback: Direct feed URL check or page fetch after `feedparser` fails

### Generic page-shaped reading

- Source of truth: Original page or document
- Preferred tool: `Jina Reader`
- Fallback: Source-specific direct page reading or platform-native tool if one exists, then broad search only as last resort

### Latest or current status ask

- Source of truth: Live upstream source
- Preferred tool: source-specific official tool first
- Fallback: Direct page reading, then broad search only if the direct source path is blocked
- Freshness note: verify live; do not answer from memory alone

## Core reminders

- Source and tool are not the same thing. The platform or original document is the source of truth; the CLI or reader is only the access path.
- Prefer the most direct, structured, and official path first. Generic readers are fallback infrastructure, not the first answer to everything.
- If a platform already has a purpose-built tool in this environment, use that tool before scraping or broad search.
- For latest or current information, verify from the live upstream source instead of relying on summaries or memory.
- If the preferred tool is unavailable, fall through to the next-best access path without changing what counts as the source of truth.

## Default source priority

1. Direct primary source
2. Official tool for that source
3. Local configured MCP or parser
4. Jina Reader as a generic reader
5. Search results or summaries only as fallback

Do not use `agent-reach` as a source layer. Treat it only as an old wrapper that is no longer part of the workflow.

## Preferred tools in this environment

- `gh`: GitHub repos, releases, issues, PRs, stars, metadata
- `yt-dlp`: YouTube and other video-page metadata, subtitles, transcripts, media info
- `mcporter`: configured MCP servers and MCP-backed sources
- `feedparser`: RSS and Atom feeds
- `Jina Reader`: generic web reading, especially tweets, normal web pages, PDFs, and images

## Failure Recovery Order

When the preferred tool fails, keep the same source of truth and fall back in a fixed order.

- `gh` failed:
  keep GitHub as source of truth, then fall back to `Jina Reader` for README or page body retrieval, then broad search only if the direct GitHub page is still not readable.
- `mcporter` failed or MCP is not configured:
  only use `mcporter` when the MCP server is actually configured; if MCP is not configured, skip `mcporter` immediately and fall through to the next direct source path.
- `yt-dlp` failed:
  keep the video page as source of truth, then fall back to source-specific direct page reading with `Jina Reader` when the user mainly needs page正文, then broad search only as last resort.
- `feedparser` failed:
  keep the feed as source of truth, then fall back to direct feed URL checks or page fetch only after `feedparser` fails, and do not start from generic broad search.
- `Jina Reader` failed:
  keep the original page or document as source of truth, then fall back to source-specific direct page reading, then broad search only as last resort.

Do not change the authority layer just because the first access path broke.

## Fast route first

| User intent | Source of truth | Preferred tool | Notes |
| --- | --- | --- | --- |
| 看 GitHub 仓库信息 | GitHub repo metadata | `gh` | Metadata, releases, issues, stars all use `gh` first |
| 读 GitHub README 正文 | GitHub README | `gh` first, `Jina Reader` fallback | Keep GitHub as source of truth even if Jina is used for body text |
| 提取视频字幕/元数据 | Video platform page | `yt-dlp` | Better than generic scraping |
| 读 RSS/Atom | Feed itself | `feedparser` | Do not scrape feed HTML first |
| 调 MCP 已配置源 | MCP-backed source | `mcporter` | Only when server is actually configured |
| 读普通网页/推文/PDF/图片 | Original page/document | `Jina Reader` | Best generic page-shaped reader in this environment |
| 问 latest/current/recent | Live upstream source | source-specific tool first | Never rely on memory or stale summaries |

## Source selection rules

### 1. GitHub content

Prefer `gh` first for:

- repository metadata
- releases and tags
- issues and pull requests
- stars and watchers
- authenticated access
- README body retrieval when possible

Use Jina Reader only for plain-page reading fallback, not as the first choice for GitHub.

Practical split:

- Repo metadata / release / issue / PR / stars -> `gh`
- README or page body when `gh` is awkward -> `Jina Reader` fallback is acceptable
- Even on fallback, GitHub remains the source of truth

### 2. Video pages

Prefer `yt-dlp` first for:

- subtitles
- transcript-like text
- title, uploader, duration, upload date
- multi-site media extraction

If the user only wants to read the surrounding article page, Jina Reader is acceptable, but `yt-dlp` remains the source of truth for video metadata.

### 3. RSS and Atom

Prefer `feedparser` first.

Use it for:

- parsing feed entries
- timestamps
- titles and links
- structured feed consumption

Do not scrape RSS pages with Jina Reader unless the feed itself is inaccessible.

### 4. MCP-backed sources

Prefer `mcporter` when the target source has a configured MCP server.

Typical examples:

- Exa search through MCP
- platform-specific MCP integrations
- structured tool calls where the MCP exposes the canonical action

Before using `mcporter`, check whether the server is locally configured.
If it is not configured, do not stall there; fall through to the next direct source path.
Do not treat "MCP might exist" as enough reason to pause routing; configured and callable is the bar.

### 5. Web pages, tweets, PDFs, images

Prefer Jina Reader first.

Use:

```powershell
curl "https://r.jina.ai/<original-url>"
```

Default Jina Reader wins for:

- Twitter/X single-post reading
- normal web pages
- PDFs
- image URLs

WeChat articles often require login or render unstably, so do not assume Jina Reader is a reliable default there.

## Latest and current rule

If the request includes words like:

- latest
- current
- today
- recent
- 最新
- 现在
- 今天

then treat freshness as a hard requirement.

That means:

1. Verify against the live upstream source
2. Prefer structured official tooling over summaries
3. Mention when you are falling back
4. Do not answer from memory alone

## What to avoid

- Do not use a generic web reader first when a structured official tool already exists.
- Do not treat `Jina Reader` output as the source of truth for GitHub metadata, video metadata, or feed parsing.
- Do not scrape RSS with a generic web reader when `feedparser` can parse the feed directly.
- Do not use `agent-reach` as a source layer. It is not part of the current source-selection workflow.
- Do not mistake access convenience for authority. A readable page is not automatically the canonical source.

## Decision matrix

Read [references/source-matrix.md](references/source-matrix.md) when you need the task-to-tool mapping in compact form.
Read [references/fallback-matrix.md](references/fallback-matrix.md) when the preferred tool failed and you need the next access path in table form.

## Operating rules

- Prefer the most direct source over a derived summary.
- If the user asks for the latest or current status, verify with the live source, not memory.
- If a primary source is available, do not lead with secondary commentary.
- If the requested page is easy to read directly, use the direct reader instead of broad search.
- When multiple tools could work, choose the one that yields the most structured, authoritative output.
- If the user only wants fast page正文 and not structured metadata, prefer the shortest reliable path.

## Fast choices

- "看这个 GitHub 仓库" -> `gh`
- "读这个 GitHub README" -> `gh` first, `Jina Reader` fallback
- "提取这个视频字幕" -> `yt-dlp`
- "读这个 RSS" -> `feedparser`
- "调用已配置的 MCP 源" -> `mcporter`
- "读这个网页/推文/PDF/图片" -> `Jina Reader`
- "看最新/最近/今天的情况" -> live upstream source first, not memory
