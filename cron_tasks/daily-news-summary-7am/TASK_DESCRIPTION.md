# Daily News Summary

## Goal

Produce the daily Chinese AI and developer-tools news briefing for this ControlMesh chat.

## Assignment

This is a text-only research task. Do not call any external messaging tool.
Your final answer is the digest itself; ControlMesh cron will deliver it.

Research scope:
1. CLI updates:
   - Claude Code
   - OpenAI Codex CLI
2. 橘鸦 AI 早报 latest full article
3. 2-3 international AI or developer-tool news items
4. 阮一峰周刊 latest issue in the current window

Hard rules:
1. Do not summarize from title-only RSS snippets when a full article or release note
   is available.
2. For CLI updates, open the actual GitHub release page and read the release body
   before summarizing.
3. For 橘鸦 AI 早报, read the latest full article before selecting the top three items.
4. If a page cannot be fetched or the content is too thin, say so explicitly.
5. Default to Chinese. Keep links minimal. Focus on facts and implications.

Suggested workflow:
1. Check the latest Claude Code and Codex CLI releases from GitHub.
2. Check the latest 橘鸦 AI 早报 article and extract the top 3 items.
3. Pick 2-3 real international items worth reading today.
4. Check whether 阮一峰周刊 has a new issue in the relevant time window.
5. Write the fixed-format morning briefing.

## Output

Return exactly five sections in Chinese:
1. `CLI更新`
2. `橘鸦前三条`
3. `国际资讯`
4. `阮一峰`
5. `一句话判断`

Style rules:
- Concise, like an edited morning brief
- Explain what changed and why it matters
- No link dump
- If evidence is insufficient, say `正文不可得` or `细节不足`
