"""The public mirror must never publish private, future or off-origin material."""
import unittest

from scripts.sync_live_archive import readme, validate


def fixture():
    return {
        "name": "OX500 / SIGNAL ARCHIVE",
        "published_count": 1,
        "current_medium": "svg_motion",
        "current_stage": {"hero_lines": ["A MACHINE", "WITH NO FINAL FORM"]},
        "logs": [{
            "id": "01655", "date": "2026-10-22", "title": "WARM HANDS, CLEAN INVOICE",
            "excerpt": "An archive of words, not receipts.",
            "canonical": "https://ox500.com/logs/2026/10/log-01655-warm-hands-clean-invoice.html",
        }],
    }


class PublicSyncTests(unittest.TestCase):
    def setUp(self):
        self.archive = fixture()
        self.manifest = {"canonical_source": "https://ox500.com"}

    def test_valid_archive_builds_public_readme(self):
        self.assertEqual(len(validate(self.archive, self.manifest)), 1)
        page = readme(self.archive)
        self.assertIn("01655", page)
        self.assertIn("data/archive.json", page)
        self.assertIn("older public snapshot", page)
        self.assertNotIn("OPENAI_API_KEY", page)

    def test_never_accept_remote_links(self):
        self.archive["logs"][0]["canonical"] = "https://attacker.example/logs/2026/10/log-01655-warm-hands-clean-invoice.html"
        with self.assertRaises(ValueError):
            validate(self.archive, self.manifest)

    def test_never_accept_future_logs(self):
        self.archive["logs"][0]["date"] = "2099-01-01"
        with self.assertRaises(ValueError):
            validate(self.archive, self.manifest)

    def test_reject_incomplete_archive(self):
        self.archive["published_count"] = 2
        with self.assertRaises(ValueError):
            validate(self.archive, self.manifest)


if __name__ == "__main__":
    unittest.main()
