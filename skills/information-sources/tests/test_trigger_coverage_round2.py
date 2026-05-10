from pathlib import Path
import unittest


SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


def load_description() -> str:
    text = SKILL_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("description:"):
            return line
    raise AssertionError("missing description frontmatter")


class InformationSourcesRound2TriggerCoverageTests(unittest.TestCase):
    def test_description_covers_source_attribution_and_authority_intents(self):
        description = load_description()

        # Fixed trigger samples for this round.
        # Pain point: English-only "source attribution / authority" asks were not explicit.
        expectations = {
            "source attribution ask": [
                "source attribution",
                "cite sources",
                "what is your source",
            ],
            "official or primary source ask": [
                "official source",
                "primary source",
                "which source should I trust",
            ],
        }

        missing = []
        for label, variants in expectations.items():
            if not any(variant in description for variant in variants):
                missing.append(label)

        if missing:
            self.fail("description missing trigger coverage for: " + ", ".join(missing))


if __name__ == "__main__":
    unittest.main()
