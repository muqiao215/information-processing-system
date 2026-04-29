# Findings: Firecrawl Web Agent Replication

## Repository Facts

- Repo: `firecrawl/web-agent`
- License: MIT
- Description: open-source web data agent optimized for structured web research.
- Default branch: `main`
- Observed stars: 564 at inspection time.
- README describes a stack of Next.js template, Express template, Agent Core, Firecrawl AI SDK, Firecrawl SDK, and REST API.

## Useful Architecture To Replicate

- Tool abstraction: `search`, `scrape`, `scrape:extract`, `scrape:markdown`, `interact`, `map`, `crawl`, `extract`, `agent`, `bashExec`, `formatOutput`.
- Agentic loop: plan, act, observe, retry, finish.
- Skills: task-specific playbooks loaded on demand.
- Subagents: independent worker sessions for parallel research.
- Structured output: schema-enforced JSON instead of only markdown.
- Exportable procedure: completed work can become a reusable skill/recipe.

## Constraints For Our System

- `firecrawl/web-agent` requires `FIRECRAWL_API_KEY` for examples and templates.
- It also requires at least one model provider key such as Google, Anthropic, OpenAI, AI Gateway, or custom OpenAI-compatible provider.
- That dependency profile makes it unsuitable as the default fetch layer for this system.
- Its agent loop is research-oriented and can be nondeterministic; daily source collection needs repeatability and auditability.

## Correct Local Mapping

- Firecrawl `search/map/crawl` maps to source discovery recipes.
- Firecrawl `scrape` maps to local readers and fetch cascade.
- Firecrawl `interact` maps to existing server-browser / Chrome CDP capabilities.
- Firecrawl `extract/formatOutput` maps to local schemas and `knowledge_pack`.
- Firecrawl subagents map to background workers or future local worker pools.

## Recommended Placement

- Add a new acquisition orchestration layer before `knowledge_pack`.
- Treat Firecrawl/Web Agent as an optional adapter candidate under `Adapters/`, not `Sources/`.
- Keep existing source collectors such as follow-builders, BuilderPulse, and arXiv intact.
