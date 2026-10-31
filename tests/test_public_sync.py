"""Public mirror must preserve autonomous prose and accept only published records."""
import unittest
from scripts.sync_live_archive import readme, validate


def fixture():
    return {'name': 'OX500 / SIGNAL ARCHIVE', 'published_count': 1, 'current_medium': 'svg_motion',
            'current_stage': {'hero_lines': ['ANY STAGE']}, 'logs': [{
                'id': '01655', 'date': '2026-10-22', 'title': 'WARM HANDS, CLEAN INVOICE',
                'excerpt': 'Test excerpt',
                'canonical': 'https://ox500.com/logs/2026/10/log-01655-warm-hands-clean-invoice.html'}]}


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

    def test_revised_identity_is_allowed(self):
        self.manifest['public_presence']['readme'] = '# A new identity\n\nThe author can change the entire public description on a later review.'
        self.assertTrue(readme(self.archive, self.manifest).startswith('# A new identity'))

    def test_missing_autonomous_document_fails_closed(self):
        del self.manifest['public_presence']
        with self.assertRaises(ValueError): readme(self.archive, self.manifest)

    def test_markup_rejected(self):
        self.manifest['public_presence']['readme'] = '<script>alert(1)</script>' + 'x'*50
        with self.assertRaises(ValueError): readme(self.archive, self.manifest)

    def test_never_accept_remote_links(self):
        self.archive['logs'][0]['canonical'] = 'https://attacker.example/logs/2026/10/log-01655-warm-hands-clean-invoice.html'
        with self.assertRaises(ValueError): validate(self.archive, self.manifest)

    def test_never_accept_future_logs(self):
        self.archive['logs'][0]['date'] = '2099-01-01'
        with self.assertRaises(ValueError): validate(self.archive, self.manifest)

    def test_incomplete_archive_rejected(self):
        self.archive['published_count'] = 2
        with self.assertRaises(ValueError): validate(self.archive, self.manifest)
