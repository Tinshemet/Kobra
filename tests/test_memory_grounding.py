import unittest
from kobra.confidence_gate import GatedRuleReader, ConfidenceGate
from kobra.rule_assignment import RuleAssigner
from kobra.knowledge import KnowledgeSnapshot

class MemoryGroundingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assigner=RuleAssigner()
    def read(self, status='confirmed_by_client', entities=None, claims=None, history=None):
        entities=entities if entities is not None else {'b1':dict(name='box',number='singular')}
        history=history or [dict(id='t1',role='user',content='box')]
        claims=claims if claims is not None else [dict(id='c1',turn_id='t1',start=0,end=3,quote='box',status=status,reference='it',entity_id='b1')]
        k=KnowledgeSnapshot(live=dict(revision='1',source='fixture',status='current',entities=entities))
        return GatedRuleReader(self.assigner,ConfidenceGate(),knowledge=k).read('Move it.',history=history,context_claims=claims)
    def test_confirmed_reference(self):
        r=self.read();self.assertEqual(r['proposal']['groundings'],{'it':'b1'})
        self.assertEqual(r['reasons'],['uncalibrated_cohort'])
        self.assertEqual(r['proposal']['frames'][0]['patient'],'it')
        self.assertEqual(r['memory_evidence']['bindings'][0]['prior_spans'][0]['quote'],'box')
    def test_reported_is_not_confirmed(self):
        r=self.read(status='reported');self.assertFalse(r['proposal'].get('groundings'))
        self.assertIn('memory_unconfirmed_reference:it',r['reasons'])
    def test_disputed(self):
        self.assertIn('memory_disputed_reference:it',self.read(status='disputed')['reasons'])
    def test_missing_target(self):
        self.assertIn('memory_missing_entity:it',self.read(entities={})['reasons'])
    def test_identity_does_not_match_quote(self):
        self.assertIn('memory_evidence_name_mismatch:it',self.read(entities={'b1':dict(name='lamp',number='singular')})['reasons'])
    def test_number_required(self):
        for record in (dict(name='box'),dict(name='box',number='plural')):
            self.assertIn('memory_number_not_supported:it',self.read(entities={'b1':record})['reasons'])
    def test_correction_and_conflict(self):
        history=[dict(id='t1',role='user',content='box'),dict(id='t2',role='user',content='lamp')]
        claims=[dict(id='c1',turn_id='t1',start=0,end=3,quote='box',status='superseded',reference='it',entity_id='b1',superseded_by='c2'),dict(id='c2',turn_id='t2',start=0,end=4,quote='lamp',status='confirmed_by_client',reference='it',entity_id='l1')]
        entities={'b1':dict(name='box',number='singular'),'l1':dict(name='lamp',number='singular')}
        r=self.read(entities=entities,claims=claims,history=history)
        self.assertEqual(r['proposal']['groundings'],{'it':'l1'})
        claims[0].update(status='confirmed_by_client');claims[0].pop('superseded_by')
        r=self.read(entities=entities,claims=claims,history=history)
        self.assertFalse(r['proposal'].get('groundings'))
        self.assertIn('memory_ambiguous_reference:it',r['reasons'])
    def test_forged_quote_rejected(self):
        with self.assertRaises(ValueError):self.read(history=[dict(id='t1',role='user',content='red')])
    def test_reference_supersession_cannot_change_cue(self):
        claims=[dict(id='c1',turn_id='t1',start=0,end=3,quote='box',status='superseded',reference='it',entity_id='b1',superseded_by='c2'),dict(id='c2',turn_id='t1',start=0,end=3,quote='box',status='confirmed_by_client',reference='them',entity_id='b1')]
        with self.assertRaises(ValueError):self.read(claims=claims)

    def test_scoped_binding_keeps_local_and_ledger_roles_separate(self):
        from kobra.memory_grounding import resolve_memory
        from kobra.context_ledger import context_snapshot
        from kobra.selection_read import SLOTS
        f=dict({s:'NONE' for s in SLOTS},act='request',predicate='Move',patient='it')
        code=dict(frames=[f,f],local_references=[dict(frame=0,slot='patient',status='resolved',mention=dict(text='it'),entity_id='local1')])
        world={'b1':dict(name='box',number='singular')}
        ledger=context_snapshot([dict(id='t1',role='user',content='box')],world,[dict(id='c1',turn_id='t1',start=0,end=3,quote='box',reference='it',entity_id='b1',status='confirmed_by_client')])
        r=resolve_memory('Move it. Move it.',code,ledger,world)
        self.assertEqual(len(r['bindings']),1)
        self.assertEqual(r['bindings'][0]['frame'],1)
        self.assertEqual(r['bindings'][0]['entity_id'],'b1')
        self.assertEqual(r['issues'],[])
