"""Public mirror must preserve autonomous prose and accept only published records."""
import unittest
from scripts.sync_live_archive import readme, validate, published_export, read_public_text


def fixture():
    return {'name': 'OX500 / SIGNAL ARCHIVE', 'published_count': 1, 'current_medium': 'svg_motion',
            'current_stage': {'hero_lines': ['ANY STAGE']}, 'logs': [{
                'id': '01655', 'date': '2026-10-22', 'title': 'WARM HANDS, CLEAN INVOICE',
                'excerpt': 'Test excerpt',
                'canonical': 'https://ox500.com/logs/2026/10/log-01655-warm-hands-clean-invoice.html',
                'full_text': '/vision/log/01655/text.txt', 'sources': []}]}


class PublicSyncTests(unittest.TestCase):
    def setUp(self):
        self.archive = fixture()
        self.manifest = {'canonical_source': 'https://ox500.com',
            'identity_governance': {'review_cadence': 'quarterly', 'agent_positions': 5},
            'public_presence': {'schema_version': 1,
                'summary': 'An independently authored description of the archive.',
                'llms': 'A freely chosen document with its own structure and no mandatory slogan.',
                'readme': '# A different title\n\nAn autonomous editorial decision, preserved literally.\n{{RECENT_TRANSMISSIONS}}'}}

    def test_valid_published_archive(self):
        self.assertEqual(len(validate(self.archive, self.manifest)), 1)
        self.assertIn('01655', readme(self.archive, self.manifest))

    def test_author_structure_is_preserved_without_assistant_framing(self):
        text = '# A title chosen by the author\n\nNo compulsory genre, fixed slogan or technical report.\n'
        self.manifest['public_presence']['readme'] = text
        self.assertEqual(readme(self.archive, self.manifest), text)

    def test_markdown_blockquote_is_preserved(self):
        text = '# Author choice\n\n> A complete blockquote chosen freely by the author, without a template.\n'
        self.manifest['public_presence']['readme'] = text
        self.assertEqual(readme(self.archive, self.manifest), text)

    def test_revised_identity_is_allowed(self):
        self.manifest['public_presence']['readme'] = '# A new identity\n\nThe author can change the entire public description on a later review.'
        self.assertTrue(readme(self.archive, self.manifest).startswith('# A new identity'))

    def test_private_provenance_is_not_part_of_public_documents(self):
        self.manifest['public_presence']['response_id'] = 'private-ledger-only'
        with self.assertRaises(ValueError):
            readme(self.archive, self.manifest)

    def test_authored_discovery_fields_are_mirrored_without_rewriting_readme(self):
        before = readme(self.archive, self.manifest)
        self.manifest['public_presence']['agent_manifest'] = {'a_chosen_field': ['Own voice', 'Own structure']}
        self.manifest['public_presence']['reader_skill'] = 'A reader-skill description selected by the archive author.'
        self.assertEqual(readme(self.archive, self.manifest), before)

    def test_missing_autonomous_document_fails_closed(self):
        del self.manifest['public_presence']
        with self.assertRaises(ValueError): readme(self.archive, self.manifest)

    def test_markup_rejected(self):
        self.manifest['public_presence']['readme'] = '<script>alert(1)</script>' + 'x'*50
        with self.assertRaises(ValueError): readme(self.archive, self.manifest)

    def test_unknown_template_marker_fails_closed(self):
        self.manifest['public_presence']['readme'] = '# Archive\\n\\n{{UNKNOWN_DATA}}' + 'a' * 45
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            readme(self.archive, self.manifest)

    def test_never_accept_remote_links(self):
        self.archive['logs'][0]['canonical'] = 'https://attacker.example/logs/2026/10/log-01655-warm-hands-clean-invoice.html'
        with self.assertRaises(ValueError): validate(self.archive, self.manifest)

    def test_never_accept_future_logs(self):
        self.archive['logs'][0]['date'] = '2099-01-01'
        with self.assertRaises(ValueError): validate(self.archive, self.manifest)

    def test_incomplete_archive_rejected(self):
        self.archive['published_count'] = 2
        with self.assertRaises(ValueError): validate(self.archive, self.manifest)

    def test_full_text_export_matches_every_published_log(self):
        out = published_export(self.archive, lambda log: "A complete public text for " + log["id"])
        self.assertEqual(out["published_count"], len(out["logs"]))
        self.assertEqual([x["id"] for x in out["logs"]], [x["id"] for x in self.archive["logs"]])
        self.assertEqual(out["logs"][0]["canonical"], self.archive["logs"][0]["canonical"])
        self.assertIn("complete public text", out["logs"][0]["text"])
        self.assertNotIn("art_direction", out["logs"][0])

    def test_missing_text_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Missing text"):
            published_export(self.archive, lambda log: "")

    def test_missing_text_pointer_is_rejected(self):
        self.archive["logs"][0].pop("full_text")
        with self.assertRaisesRegex(ValueError, "public text pointer"):
            validate(self.archive, self.manifest)

    def test_private_or_redirected_text_pointer_is_rejected(self):
        for text_path in ("https://other.invalid/secret", "/internal/01655", "/vision/log/01654/text.txt"):
            self.archive["logs"][0]["full_text"] = text_path
            with self.assertRaises(ValueError):
                validate(self.archive, self.manifest)
            with self.assertRaises(ValueError):
                read_public_text(self.archive["logs"][0])

    def test_duplicate_published_id_fails_closed(self):
        self.archive["logs"].append(dict(self.archive["logs"][0]))
        self.archive["published_count"] = 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate(self.archive, self.manifest)

    def test_public_sources_only_and_reject_unsafe_source_url(self):
        self.archive["logs"][0]["sources"] = [{
            "publisher": "Publisher", "title": "Report", "url": "https://publisher.example/report",
            "published": "2026-10", "private_token": "MUST_NOT_LEAK",
        }]
        out = published_export(self.archive, lambda log: "The full public poem goes here.")
        self.assertNotIn("private_token", out["logs"][0]["sources"][0])
        self.archive["logs"][0]["sources"][0]["url"] = "http://localhost/private"
        with self.assertRaisesRegex(ValueError, "Unexpected source URL"):
            published_export(self.archive, lambda log: "The full public poem goes here.")
