import unittest
from kobra.surface_chunks import chunk_commands

class SurfaceChunkTests(unittest.TestCase):
    def test_boundaries_need_no_parser(self):
        text='Please create three servers; then restart them and check them.'
        p=chunk_commands(text)
        self.assertEqual(p['status'],'supported')
        self.assertEqual([c['predicate']['text'] for c in p['chunks']],['create','restart','check'])
        self.assertEqual(''.join(x['text'] for x in p['source_ledger']),text)
    def test_member_list_is_not_an_action_boundary(self):
        p=chunk_commands('Create three VMs, one with Windows, one with Kali and one with Debian, then launch them.')
        self.assertEqual(len(p['chunks']),2)
        self.assertIn('one with Kali and one with Debian',p['chunks'][0]['text'])
    def test_quote_bracket_and_escape_protection(self):
        for text in ['Create "open and delete" and launch it.',
                     'Create a file (named open and delete) and launch it.',
                     'Create “open and delete” and launch it.',
                     'Create "say \\"open and delete\\"" and launch it.']:
            p=chunk_commands(text)
            self.assertEqual(len(p['chunks']),2,p)
            self.assertEqual(''.join(x['text'] for x in p['source_ledger']),text)
    def test_unbalanced_delimiters_abstain(self):
        for text in ['Create "a file and delete it.','Create a file ) and delete it.']:
            self.assertEqual(chunk_commands(text)['status'],'unresolved')
    def test_scope_is_never_flattened(self):
        for text in ['Do not open the file and delete it.','Open the file if it exists and delete it.','Open the file or delete it.']:
            self.assertEqual(chunk_commands(text)['status'],'unresolved')
    def test_custom_vocabulary_is_explicit(self):
        self.assertEqual(chunk_commands('Frobnicate the file and quux it.',{'frobnicate','quux'})['status'],'supported')
        self.assertEqual(chunk_commands('Frobnicate the file.')['status'],'unresolved')
    def test_repeatability_and_whitespace(self):
        text='  Please create three servers,\nthen launch them. '
        self.assertEqual(chunk_commands(text),chunk_commands(text))
        self.assertEqual(len(chunk_commands(text)['chunks']),2)
