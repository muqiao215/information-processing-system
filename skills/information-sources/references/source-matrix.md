# Source Matrix

## Task to tool mapping

| Task | Preferred tool | Why |
| --- | --- | --- |
| GitHub repo / release / issue / PR | `gh` | Official, structured, authenticated |
| Video metadata / subtitles / transcript | `yt-dlp` | Better extraction than generic scraping |
| RSS / Atom parsing | `feedparser` | Structured feed parsing |
| MCP-backed search or platform action | `mcporter` | Uses configured local MCP servers |
| Normal web page | `Jina Reader` | Fast plain-text read |
| Twitter/X single post | `Jina Reader` | Quick read without extra wrapper |
| PDF URL | `Jina Reader` | Direct text-friendly conversion |
| Image URL | `Jina Reader` | Quick text-side read path |

## Fallback order

1. Primary source + official tool
2. Configured MCP source
3. Jina Reader
4. Search engine result page
5. Secondary summary
