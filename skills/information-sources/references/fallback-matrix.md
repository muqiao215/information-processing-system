# Fallback Matrix

Use this table when the preferred tool path is blocked and you need the next access path without changing the source of truth.

| Preferred tool | Use only when | If it fails or is unavailable | Keep as source of truth | Do not do first |
| --- | --- | --- | --- | --- |
| `gh` | GitHub repo metadata, releases, issues, PRs, stars, or README retrieval | Fall back to `Jina Reader` for direct GitHub page/README body retrieval, then broad search only if the direct GitHub page is still not readable | GitHub | Do not switch to generic web summaries first |
| `mcporter` | MCP server is configured and callable | If MCP is not configured, skip `mcporter` immediately and fall through to the next direct source path; if configured but call fails, use the next direct source path for that source | The original MCP-backed source | Do not stall on "maybe configured" |
| `yt-dlp` | Video page metadata, subtitles, transcript-like extraction | Fall back to source-specific direct page reading with `Jina Reader` when the user mainly needs page正文, then broad search only as last resort | The video page | Do not treat surrounding summaries as authoritative |
| `feedparser` | RSS or Atom feed parsing | Fall back to direct feed URL checks or page fetch only after `feedparser` fails, then broader search only if the feed is still inaccessible | The feed URL | Do not begin from generic page scraping |
| `Jina Reader` | Generic page-shaped reading for tweets, web pages, PDFs, and images | Fall back to source-specific direct page reading or the platform-native tool if one exists, then broad search only as last resort | The original page or document | Do not change the authority layer because the first reader failed |

## Short Rule

- Keep the source of truth stable.
- Change the access path, not the authority layer.
- Prefer one direct fallback before broad search.
