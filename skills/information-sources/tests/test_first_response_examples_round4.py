from pathlib import Path
import unittest


SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


class InformationSourcesRound4FirstResponseExamplesTests(unittest.TestCase):
    def test_first_response_section_includes_generic_page_route_example(self):
        text = SKILL_PATH.read_text(encoding="utf-8")

        expected_examples = [
            "### Generic page-shaped reading",
            "Source of truth: Original page or document",
            "Preferred tool: `Jina Reader`",
            "Fallback: Source-specific direct page reading or platform-native tool if one exists, then broad search only as last resort",
        ]

        for expected in expected_examples:
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
