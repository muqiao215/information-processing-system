from pathlib import Path
import unittest


SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


class InformationSourcesSkillSmokeTests(unittest.TestCase):
    def test_frontmatter_and_entry_routing_are_present(self):
        text = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("name: information-sources", text)
        self.assertIn("source routing", text)
        self.assertIn("网页正文", text)
        self.assertIn("GitHub README", text)

        self.assertIn("## First Response Shape", text)
        self.assertIn("Source of truth:", text)
        self.assertIn("Preferred tool:", text)
        self.assertIn("Fallback:", text)

        self.assertIn("## Failure Recovery Order", text)
        self.assertIn("`gh` failed", text)
        self.assertIn("`yt-dlp` failed", text)
        self.assertIn("`feedparser` failed", text)
        self.assertIn("`Jina Reader` failed", text)
        self.assertIn("`mcporter` failed or MCP is not configured", text)
        self.assertIn("keep GitHub as source of truth", text)
        self.assertIn("only use `mcporter` when the MCP server is actually configured", text)
        self.assertIn("if MCP is not configured, skip `mcporter` immediately and fall through to the next direct source path", text)
        self.assertIn("fall back to direct feed URL checks or page fetch only after `feedparser` fails", text)
        self.assertIn("fall back to source-specific direct page reading, then broad search only as last resort", text)
        self.assertIn("[references/fallback-matrix.md](references/fallback-matrix.md)", text)

        self.assertIn('"看这个 GitHub 仓库" -> `gh`', text)
        self.assertIn('"读这个 GitHub README" -> `gh` first, `Jina Reader` fallback', text)
        self.assertIn('"读这个网页/推文/PDF/图片" -> `Jina Reader`', text)
        self.assertIn('"看最新/最近/今天的情况" -> live upstream source first, not memory', text)


if __name__ == "__main__":
    unittest.main()
