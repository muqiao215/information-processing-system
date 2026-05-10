from pathlib import Path
import unittest


SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


class InformationSourcesRound3FirstResponseExamplesTests(unittest.TestCase):
    def test_first_response_section_includes_fixed_route_examples(self):
        text = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("## First Response Examples", text)

        expected_examples = [
            "### GitHub repo metadata",
            "Source of truth: GitHub repository metadata",
            "Preferred tool: `gh`",
            "Fallback: `Jina Reader` for direct GitHub page reading",
            "### RSS feed parsing",
            "Source of truth: Feed URL",
            "Preferred tool: `feedparser`",
            "Fallback: Direct feed URL check or page fetch after `feedparser` fails",
            "### Latest or current status ask",
            "Source of truth: Live upstream source",
            "Preferred tool: source-specific official tool first",
            "Fallback: Direct page reading, then broad search only if the direct source path is blocked",
            "Freshness note: verify live; do not answer from memory alone",
        ]

        for expected in expected_examples:
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
