import unittest
from kobra.confidence_gate import Calibration, ConfidenceGate, GatedRuleReader
from kobra.selection_read import SLOTS


def proposal():
    return {'frames':[dict({s:'NONE' for s in SLOTS}, act='request', predicate='Move', patient='the parcel')]}


class GateTests(unittest.TestCase):
    def gate(self, **kwargs):
        return ConfidenceGate({'test':Calibration(1000,1000,'heldout-fixture','test')}, **kwargs)
    def test_valid_calibrated(self):
        self.assertEqual(self.gate().assess('Move the parcel.',proposal(),cohort='test')['route'],'ACCEPT')
    def test_self_confidence_never_calibrates(self):
        p=proposal();p['confidence']=1
        r=ConfidenceGate().assess('Move the parcel.',p,cohort='test')
        self.assertEqual(r['route'],'ASK');self.assertIsNone(r['external_score'])
    def test_invented_reference_even_with_high_score(self):
        p=proposal();p['world_references']=['ghost']
        r=self.gate().assess('Move the parcel.',p,cohort='test',world_ids=['box'])
        self.assertIn('nonexistent_world_reference',r['reasons'])
    def test_source_invention(self):
        p=proposal();p['frames'][0]['patient']='dragon'
        self.assertIn('not_in_source:patient',self.gate().assess('Move the parcel.',p,cohort='test')['reasons'])
    def test_missing_context_overrides_score(self):
        r=self.gate().assess('Move the parcel.',proposal(),cohort='test',missing_context=['referent'])
        self.assertEqual(r['route'],'ASK')
    def test_rule_conflict_overrides_score(self):
        g=self.gate(validators=[lambda text,frames:['conflicting_role']])
        self.assertIn('conflicting_role',g.assess('Move the parcel.',proposal(),cohort='test')['reasons'])
    def test_empty_and_malformed(self):
        for p in (None,{}, {'frames':[{}]}, {'frames':['bad']}):
            self.assertEqual(self.gate().assess('Move the parcel.',p,cohort='test')['route'],'ASK')
    def test_reused_development_not_calibration(self):
        g=ConfidenceGate({'test':Calibration(280,280,'dev','test',split='development')})
        self.assertIn('invalid_calibration',g.assess('Move the parcel.',proposal(),cohort='test')['reasons'])
    def test_low_score_and_small_sample(self):
        for correct,total in [(80,100),(5,5)]:
            g=ConfidenceGate({'test':Calibration(correct,total,'heldout','test')})
            self.assertEqual(g.assess('Move the parcel.',proposal(),cohort='test')['route'],'ASK')
    def test_pronoun_requires_binding_to_existing_world_entity(self):
        p=proposal();p['frames'][0]['patient']='it'
        self.assertEqual(self.gate().assess('Move it.',p,cohort='test')['route'],'ASK')
        p['groundings']={'it':'box-1'}
        self.assertEqual(self.gate().assess('Move it.',p,cohort='test',world_ids=['box-1'])['route'],'ACCEPT')
        self.assertEqual(self.gate().assess('Move it.',p,cohort='test',world_ids=['box-2'])['route'],'ASK')

    def test_resolver_error_routes_ask(self):
        class Assigner:
            def assign(self,text):return dict(route='unresolved',rules=[],source=text,frames=[])
        def bad(_):raise TimeoutError()
        r=GatedRuleReader(Assigner(),self.gate(),bad).read('Move the parcel.')
        self.assertEqual(r['route'],'ASK');self.assertEqual(r['source'],'Move the parcel.')
