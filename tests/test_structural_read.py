"""Structural cases are development regressions, not held-out accuracy claims."""
import unittest
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader, Calibration

VM = 'Good morning gorgon, please create 3 vms one with windows, one with metaspoitable and one with kali, set them  all in the same network and launch them.'

class StructuralReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reader=RuleAssigner()
    def test_nested_members_and_both_references(self):
        p=self.reader.assign(VM)
        self.assertEqual(p['route'],'code')
        self.assertEqual(p['chunking_method'],'deterministic_surface_rules')
        self.assertEqual([c['span']['start'] for c in p['chunks']], [c['start'] for c in p['surface_structure']['chunks']])
        self.assertEqual([f['predicate'] for f in p['frames']],['create','set','launch'])
        self.assertEqual([m['specification']['text'] for m in p['chunks'][0]['members']],['windows','metaspoitable','kali'])
        self.assertEqual([r['entity_id'] for r in p['local_references']],['e1','e1'])
        self.assertEqual(p['chunks'][1]['modifiers'][0]['scope'],'all_members')
        self.assertEqual(''.join(x['text'] for x in p['source_ledger']),VM)
        for c in p['chunks']:
            s=c['span'];self.assertEqual(VM[s['start']:s['end']],s['text'])
    def test_generic_enumeration_and_explicit_then(self):
        p=self.reader.assign('Create 2 boxes, one with red paint and one with blue paint, then move them.')
        self.assertEqual(p['route'],'code')
        self.assertEqual(len(p['chunks'][0]['members']),2)
        self.assertEqual(p['local_references'][0]['entity_id'],'e1')
        self.assertEqual(p['chunk_relations'][0]['kind'],'explicit_then')
    def test_number_agreement_and_singular_link(self):
        for text in ['Create three servers and restart them.','Open the file and read it.']:
            p=self.reader.assign(text)
            self.assertEqual(p['route'],'code',p)
            self.assertEqual(p['local_references'][0]['status'],'resolved')
    def test_multiple_compatible_antecedents_abstain(self):
        p=self.reader.assign('Create two servers, create two disks, then launch them.')
        self.assertEqual(p['route'],'unresolved')
        self.assertEqual(p['local_references'][0]['status'],'ambiguous')
        self.assertEqual(len(p['local_references'][0]['candidates']),2)
    def test_count_mismatch_does_not_accept(self):
        p=self.reader.assign('Create 3 boxes, one with red paint and one with blue paint, then move them.')
        self.assertEqual(p['route'],'unresolved')
        self.assertTrue(any('enumeration_count_mismatch' in r for r in p['reasons']))
    def test_number_mismatch_keeps_pronoun_unresolved(self):
        p=self.reader.assign('Create two servers and restart it.')
        self.assertEqual(p['route'],'unresolved')
        self.assertEqual(p['local_references'][0]['status'],'missing_antecedent')
    def test_condition_and_negation_not_flattened(self):
        for text in ['If the pump fails, close the gate and restart the pump.',
                     'Do not open the file and delete it.',
                     'Open the file or delete it.']:
            self.assertEqual(self.reader.assign(text)['route'],'unresolved')
    def test_no_inferred_world_identity(self):
        p=GatedRuleReader(self.reader,ConfidenceGate()).read(VM)
        self.assertEqual(p['reasons'],['uncalibrated_cohort'])
        self.assertEqual(p['context_ledger']['world_entities'],[])
    def test_model_cannot_assert_its_own_local_binding(self):
        p=self.reader.assign('Open the file and read it.')
        cohort='test'
        gate=ConfidenceGate({cohort:Calibration(1000,1000,'synthetic-test-only',cohort)})
        self.assertIn('ungrounded_reference:patient',gate.assess(p['source'],p,cohort=cohort)['reasons'])
    def test_partial_frames_rejected_even_with_calibration(self):
        p=self.reader.assign('Create two servers and restart it.')
        cohort='test';gate=ConfidenceGate({cohort:Calibration(1000,1000,'synthetic-test-only',cohort)})
        self.assertIn('unsupported_read_structure',gate.assess(p['source'],p,cohort=cohort)['reasons'])
    def test_distinct_service_actions(self):
        p=self.reader.assign('Cancel the subscription and refund the payment.')
        self.assertEqual(p['route'],'code')
        self.assertEqual([f['patient'] for f in p['frames']],['the subscription','the payment'])

    def test_all_quantity_is_not_dropped(self):
        p=self.reader.assign('Check all sensors.')
        self.assertEqual(p['route'],'code')
        self.assertEqual(p['frames'][0]['quantity'],'all')
        self.assertEqual(p['frames'][0]['patient'],'all sensors')
    def test_other_quantifier_scope_stays_unresolved(self):
        self.assertEqual(self.reader.assign('Create no servers and start them.')['route'],'unresolved')
