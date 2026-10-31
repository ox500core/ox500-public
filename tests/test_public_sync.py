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
        self.manifest = {"canonical_source": "https://ox500.com",
                         "public_identity": {key: "Accurate description of this established OX500 software component and its published artistic operation."
                            for key in ("overview", "editorial", "creative_boundary", "preservation",
                                        "interface", "interaction", "accountability")}}
        self.manifest["creative_identity"] = {
            "schema_version": 1,
            "tagline": "YOUR VIOLENCE HAS A DASHBOARD. WE BROUGHT FEEDBACK.",
            "manifesto": "Hardcore punk wired into a cyberpunk signal archive. Keep the damage audible.",
            "stance": "Against exploitation, institutional indifference and the use of AI for harm.",
            "creative_direction": "Specific images and abrasive language. Sol owns the artistic decisions.",
            "ownership": "Sol owns the voice. Luna audits factual capabilities once per quarter.",
        }
        self.manifest["voice_governance"] = {
            "creative_owner": "Sol", "factual_auditor": "Luna",
            "audit_cadence": "quarterly", "agent_positions": 5,
        }


    def test_valid_archive_builds_public_readme(self):
        self.assertEqual(len(validate(self.archive, self.manifest)), 1)
        page = readme(self.archive, self.manifest)
        self.assertIn("01655", page)
        self.assertIn("Accurate description", page)
        self.assertIn("data/archive.json", page)
        self.assertIn("older public snapshot", page)
        self.assertNotIn("OPENAI_API_KEY", page)
        self.assertNotIn("## Other work by the creator", page)
        self.assertNotIn("professional portfolio", page.lower())

    def test_sol_voice_precedes_facts_and_survives_fact_updates(self):
        first = readme(self.archive, self.manifest)
        voice = self.manifest["creative_identity"]
        self.assertLess(first.index(voice["manifesto"]), first.index("Accurate description"))
        for key in self.manifest["public_identity"]:
            self.manifest["public_identity"][key] = "A revised, verified factual description of the configured workflow and its actual limits."
        revised = readme(self.archive, self.manifest)
        self.assertIn(voice["manifesto"], revised)
        self.assertIn(voice["tagline"], revised)

    def test_missing_voice_fails_instead_of_publishing_a_technical_summary(self):
        del self.manifest["creative_identity"]
        with self.assertRaises(ValueError):
            readme(self.archive, self.manifest)

    def test_wrong_ownership_rejected(self):
        self.manifest["voice_governance"]["creative_owner"] = "Luna"
        with self.assertRaises(ValueError):
            readme(self.archive, self.manifest)

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
