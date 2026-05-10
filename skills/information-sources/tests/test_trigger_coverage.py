from pathlib import Path
import unittest


SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"


def load_description() -> str:
    text = SKILL_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("description:"):
            return line
    raise AssertionError("missing description frontmatter")


class InformationSourcesTriggerCoverageTests(unittest.TestCase):
    def test_description_covers_fixed_routing_samples(self):
        description = load_description()

        # Fixed trigger samples for this tuning round.
        # The weakness under test is fallback-oriented routing language.
        expectations = {
            "source of truth routing": ["source routing", "source of truth"],
            "tool choice for a link": ["读链接", "用什么工具找资料", "先用哪个工具", "哪个工具"],
            "github README choice": ["GitHub README", "Jina Reader", "gh"],
            "deciding between core tools": ["Jina Reader", "gh", "yt-dlp", "mcporter", "feedparser"],
            "fallback order": ["fallback 顺序", "fallback order", "fallback"],
            "tool failure reroute": ["失败后换什么工具", "失败后怎么办", "tool fails", "failover"],
            "rss failure reroute": ["读 RSS 失败", "RSS 失败", "feed fallback"],
            "latest/current freshness": ["latest/current verification", "最新", "current"],
        }

        missing = []
        for label, variants in expectations.items():
            if not any(variant in description for variant in variants):
                missing.append(label)

        if missing:
            self.fail("description missing trigger coverage for: " + ", ".join(missing))


if __name__ == "__main__":
    unittest.main()
