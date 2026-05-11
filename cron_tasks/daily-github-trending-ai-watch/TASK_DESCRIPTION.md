# Daily GitHub Trending AI Watch

## Goal

Collect GitHub Trending daily and produce a concise Chinese report focused on
AI, agent, automation, robotics, and developer-tool projects.

## Assignment

This repository file is the source-of-truth task contract. When installed into a
native ControlMesh `cron_tasks/<name>/` folder, the runtime task should call its
local wrapper `scripts/run_task.py`, which in turn invokes this repo-owned
collector script using stable absolute workspace paths.

This is a research task. Do not call any external messaging tool. The final
answer itself is the report to be delivered by ControlMesh cron.

Execution steps:
1. Read this task's memory file.
2. Prefer the installed runtime wrapper:
   - `python3 scripts/run_task.py`
3. If you are running directly from this repository instead of an installed
   ControlMesh cron task folder, use:
   - `python3 scripts/fetch_github_trending.py > /tmp/github_trending_daily.json`
4. If direct scraping fails, state that clearly and stop. Do not fake the list.
5. From the fetched list, build:
   - `GitHub 今日趋势 Top 8`
   - `最值得看的 4 个`
5. Prefer AI, agent, automation, robotics, and developer-tool projects.
   If the daily trending list has too few such items, supplement with the next
   most obviously relevant projects from the same scraped result.

Hard rules:
- Use the actual current daily trending page, not stale memory.
- Keep the report in Chinese.
- Focus on what the project does and why it matters.
- Do not dump raw links.

## Output

Return this structure:
1. `GitHub 今日趋势 Top 8`
2. `按用户方向最值得看的 4 个`

For each Top 8 item include:
- `owner/repo`
- one-sentence description
- language | total stars | today's stars

For each of the 4 selected items include:
- project name
- why it matters for AI / agent / automation / robotics / developer tools
