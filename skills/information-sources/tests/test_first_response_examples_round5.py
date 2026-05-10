from pathlib import Path
import unittest


SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


class InformationSourcesRound5FirstResponseExamplesTests(unittest.TestCase):
    def test_first_response_section_includes_github_readme_route_example(self):
        text = SKILL_PATH.read_text(encoding="utf-8")

        expected_examples = [
            "### GitHub README body",
            "Source of truth: GitHub README",
            "Preferred tool: `gh` first",
            "Fallback: `Jina Reader` for direct README body reading if `gh` is awkward or unavailable",
        ]

        for expected in expected_examples:
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
