import unittest
from kobra.rule_assignment import RuleAssigner

class RuleAssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reader=RuleAssigner()
    def test_passive_roles(self):
        p=self.reader.assign('The parcel was carried by Lena.')
        self.assertEqual(p['route'],'code')
        self.assertEqual(p['frames'][0]['agent'],'Lena')
        self.assertEqual(p['frames'][0]['patient'],'The parcel')
    def test_complex_routes_to_fallback_preserves_source(self):
        text='If the pump fails, close the gate.';calls=[]
        p=self.reader.read(text,lambda s:calls.append(s) or {'status':'unresolved'})
        self.assertEqual(p['route'],'model_proposal');self.assertEqual(calls,[text])
        self.assertEqual(p['source'],text);self.assertFalse(p['semantic_verified'])
    def test_simple_does_not_call_fallback(self):
        p=self.reader.read('Lena moved the parcel.',lambda _:self.fail('unexpected fallback'))
        self.assertEqual(p['route'],'code')
        self.assertEqual(p['frames'][0]['patient'],'the parcel')
