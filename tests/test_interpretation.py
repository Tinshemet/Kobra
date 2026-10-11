import hashlib,unittest
from copy import deepcopy
from kobra.confidence_gate import GatedRuleReader,ConfidenceGate,Calibration
from kobra.rule_assignment import RuleAssigner
from kobra.resolve_distillation import distill_for_resolve
from kobra.selection_read import SLOTS

class InterpretationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reader=GatedRuleReader(RuleAssigner(),ConfidenceGate())
    def test_calibration_is_not_unresolved_meaning(self):
        r=self.reader.read('Was the sensor not moved by Mira?')
        self.assertEqual(r['interpretation']['status'],'supported')
        self.assertFalse(r['interpretation']['needs_ASK'])
        self.assertEqual(r['acceptance']['calibration_reasons'],['uncalibrated_cohort'])
        self.assertEqual(r['route'],'ASK')
    def test_grammar_preserves_tense_aspect_voice(self):
        for text,tense,aspect,voice in [('Was the sensor not moved by Mira?','past','simple','passive'),
                ('Mira has moved the box.','present','perfect','active'),
                ('Mira is moving the box.','present','progressive','active'),
                ('Mira will move the box.','future','simple','active')]:
            d=self.reader.read_for_resolve(text)
            with self.subTest(text=text):
                g=d['points'][0]['grammar'];self.assertEqual((g['tense'],g['aspect'],g['voice']),(tense,aspect,voice))
    def test_qualifying_word_inside_full_source_evidence_is_not_lost(self):
        # Existing adjective-state slots omit the degree word; READ must expose it.
        r=self.reader.read('The server is very quiet.')
        self.assertTrue(r['interpretation']['needs_ASK'])
        self.assertIn('very',[x['text'] for x in r['interpretation']['unassigned']])
        self.assertFalse(distill_for_resolve(r)['state']['ready_for_resolve'])
    def test_arbitrary_suffix_is_not_hidden_by_evidence(self):
        class A:
            def assign(self,text):return dict(route='code',rules=['fixture'],frames=[dict({s:'NONE' for s in SLOTS},act='request',predicate='Move',patient='the box')])
        r=GatedRuleReader(A(),ConfidenceGate()).read('Move the box only if safe.')
        self.assertTrue(r['interpretation']['needs_ASK'])
        self.assertEqual([x['text'] for x in r['interpretation']['unassigned']],['only','if','safe'])
    def test_two_scoped_references_can_have_different_identities(self):
        text='Move it and inspect it.'
        class A:
            def assign(self,t):return dict(route='code',rules=['fixture'],frames=[dict({s:'NONE' for s in SLOTS},act='request',predicate=v,patient='it') for v in ('Move','inspect')],chunk_relations=[dict(from_chunk='c1',to_chunk='c2',kind='coordination_source_order_only')],source_ledger=[dict(start=7,end=12,text=' and ')])
        h=[dict(id='t1',role='user',content='box'),dict(id='t2',role='user',content='lamp')]
        world={'b':dict(name='box',number='singular'),'l':dict(name='lamp',number='singular')}
        claims=[dict(id=f'c{i}',turn_id=f't{i+1}',start=0,end=len(name),quote=name,reference='it',entity_id=e,status='confirmed_by_client',reference_scope=dict(source_sha256=hashlib.sha256(text.encode()).hexdigest(),frame=i,slot='patient')) for i,(name,e) in enumerate([('box','b'),('lamp','l')])]
        r=GatedRuleReader(A(),ConfidenceGate()).read(text,world=world,history=h,context_claims=claims)
        self.assertFalse(r['proposal'].get('groundings'))
        self.assertEqual([(b['frame'],b['entity_id']) for b in r['proposal']['role_bindings']],[(0,'b'),(1,'l')])
        self.assertFalse(r['interpretation']['needs_ASK'])
        d=distill_for_resolve(r)
        self.assertEqual([p['identity_bindings'][0]['entity_id'] for p in d['points']],['b','l'])
        changed=deepcopy(claims);changed[1]['reference_scope']['source_sha256']='0'*64
        bad=GatedRuleReader(A(),ConfidenceGate()).read(text,world=world,history=h,context_claims=changed)
        self.assertTrue(bad['interpretation']['needs_ASK'])

    def test_calibration_cannot_cover_uninterpreted_words(self):
        # Synthetic calibration tests routing mechanics, not measured accuracy.
        for text,ready in [('Move the box.',True),('The server is very quiet.',False)]:
            initial=self.reader.read(text)
            cohort=initial['cohort']
            gate=ConfidenceGate({cohort:Calibration(1000,1000,'contract-fixture',cohort)})
            r=GatedRuleReader(self.reader.assigner,gate).read(text)
            self.assertEqual(distill_for_resolve(r)['state']['ready_for_resolve'],ready)
            self.assertEqual(r['interpretation']['needs_ASK'],not ready)
            self.assertEqual(r['acceptance']['calibration_reasons'],[])

    def test_invalid_reference_scope_is_rejected(self):
        from kobra.context_ledger import context_snapshot
        h=[dict(id='t1',role='user',content='box')]
        claim=dict(id='c1',turn_id='t1',start=0,end=3,quote='box',reference='it',entity_id='b',
                   reference_scope=dict(source_sha256='0'*64,frame=0,slot='patient'))
        context_snapshot(h,claims=[claim])
        for patch in ({'frame':True},{'frame':-1},{'slot':'predicate'},{'source_sha256':'bad'},{'extra':1}):
            bad=deepcopy(claim);bad['reference_scope'].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                context_snapshot(h,claims=[bad])
