import unittest
from copy import deepcopy
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import GatedRuleReader, ConfidenceGate
from kobra.resolve_distillation import distill_for_resolve
from kobra.knowledge import KnowledgeSnapshot
from kobra.selection_read import SLOTS

class ResolveDistillationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reader=GatedRuleReader(RuleAssigner(),ConfidenceGate())
    def test_negative_question_preserved_and_gate_not_upgraded(self):
        text='Was the sensor not moved by Mira?'
        out=self.reader.read_for_resolve(text);p=out['points'][0]
        self.assertEqual(p['act'],'question');self.assertEqual(p['qualifiers']['negation'],'not')
        self.assertEqual(p['arguments'],dict(agent='Mira',patient='the sensor'))
        self.assertEqual(p['source_text'],text)
        self.assertFalse(out['state']['ready_for_resolve'])
        self.assertEqual(out['state']['read_route'],'ASK')
    def test_shared_patient_has_discontinuous_evidence(self):
        out=self.reader.read_for_resolve('Open and read the file.')
        self.assertEqual(len(out['points']),2)
        p=out['points'][0]
        self.assertEqual(p['arguments']['patient'],'the file')
        self.assertEqual([s['text'] for s in p['evidence']],['Open','the file'])
        self.assertEqual(out['relations'][0]['relationship'],'coordination_source_order_only')
        self.assertNotIn('before',out['relations'][0]['relationship'])
    def test_no_source_characters_discarded(self):
        for text in ('Open and read the file.','Move it.','Tell me what she wanted yesterday.'):
            out=self.reader.read_for_resolve(text);covered=set()
            for s in out['retained_remainder']+[e for p in out['points'] for e in p['evidence']]:
                self.assertEqual(text[s['start']:s['end']],s['text'])
                covered.update(range(s['start'],s['end']))
            self.assertEqual(covered,set(range(len(text))))
    def test_ledger_binding_keeps_literal_and_prior_evidence(self):
        k=KnowledgeSnapshot(live=dict(revision='1',source='fixture',status='current',entities={'b1':dict(name='box',number='singular')}))
        reader=GatedRuleReader(self.reader.assigner,ConfidenceGate(),knowledge=k)
        out=reader.read_for_resolve('Move it.',history=[dict(id='t1',role='user',content='box')],context_claims=[dict(id='c1',turn_id='t1',start=0,end=3,quote='box',reference='it',entity_id='b1',status='confirmed_by_client')])
        p=out['points'][0];self.assertEqual(p['arguments']['patient'],'it')
        self.assertEqual(p['identity_bindings'][0]['entity_id'],'b1')
        self.assertEqual(p['identity_bindings'][0]['evidence'][0]['prior_spans'][0]['quote'],'box')
    def test_projection_detaches_nested_memory_and_roles(self):
        r=self.reader.read('Open and read the file.');before=deepcopy(r)
        out=distill_for_resolve(r);out['points'][0]['arguments']['patient']='changed'
        out['local_entities'].clear();out['memory_context'].clear()
        self.assertEqual(r,before)
    def test_unsupported_grounding_does_not_gain_authority(self):
        r=self.reader.read('Move it.');r['proposal']['groundings']={'it':'ghost'}
        out=distill_for_resolve(r)
        self.assertEqual(out['points'][0]['identity_bindings'],[])
        self.assertIn('unsupported_grounding:it',out['state']['distillation_diagnostics'])
    def test_all_qualifiers_preserved_without_solving(self):
        # Contract fixture: not an assertion that RuleAssigner supports this text.
        text='Move three boxes tomorrow if safe, according to Mira; not now; must.'
        f=dict({s:'NONE' for s in SLOTS},act='request',predicate='Move',patient='three boxes',quantity='three',time='tomorrow',condition='if safe',attribution='according to Mira',negation='not',modality='must')
        r=dict(source=text,proposal=dict(frames=[f]),code_proposal=dict(frames=[f]),assignment_source='code',route='ASK',reasons=['fixture'])
        out=distill_for_resolve(r)
        self.assertEqual(out['points'][0]['qualifiers'],{s:f[s] for s in ('quantity','time','condition','attribution','negation','modality')})
    def test_invalid_upstream_frames_remain_unresolved_source(self):
        r=self.reader.read('Move the box.');r['proposal']['frames']=[{'predicate':'invented'}]
        out=distill_for_resolve(r);self.assertEqual(out['points'],[])
        self.assertEqual(out['retained_remainder'][0]['text'],'Move the box.')
        self.assertFalse(out['state']['ready_for_resolve'])
    def test_bad_evidence_is_rejected(self):
        r=self.reader.read('Open and read the file.')
        r['code_proposal']['chunks'][0]['span']['text']='invented'
        with self.assertRaises(ValueError):distill_for_resolve(r)
