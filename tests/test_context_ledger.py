import unittest
from kobra.context_ledger import context_snapshot
from kobra.confidence_gate import GatedRuleReader, ConfidenceGate

class ContextLedgerTests(unittest.TestCase):
    def test_exact_history_and_entity_mentions(self):
        history=[{'id':'u1','role':'user','content':'Move the blue box.'}]
        world={'b1':{'name':'blue box'}}
        x=context_snapshot(history,world)
        self.assertEqual(x['previous_turns'][0]['content'],history[0]['content'])
        self.assertEqual(x['world_entities'][0]['mentions'][0],dict(turn_id='u1',start=9,end=17,text='blue box'))
        world['b1']['name']='changed'
        self.assertEqual(x['world_entities'][0]['record']['name'],'blue box')
    def test_no_inferred_truth_or_missing_context_fabrication(self):
        self.assertEqual(context_snapshot()['claims'],[])
        self.assertFalse(context_snapshot()['history_supplied'])
        x=context_snapshot([{'role':'assistant','content':'The door is open.'}])
        self.assertEqual(x['claims'],[])
    def test_claim_provenance_and_explicit_correction(self):
        h=[{'role':'user','content':'Red. Blue.'}]
        claims=[dict(id='a',turn_id='turn-1',start=0,end=3,quote='Red',status='superseded',superseded_by='b'),dict(id='b',turn_id='turn-1',start=5,end=9,quote='Blue')]
        self.assertEqual(context_snapshot(h,claims=claims)['claims'][1]['status'],'reported')
        claims[1]['quote']='Green'
        with self.assertRaises(ValueError):context_snapshot(h,claims=claims)
    def test_model_mutation_cannot_rewrite_saved_world(self):
        class A:
            def assign(self,t):return {'route':'unresolved','rules':[],'frames':[]}
        def resolver(request):
            request['world']['ghost']={};request['context_ledger']['previous_turns'].clear()
            request['code_proposal']['rules'].append('invented')
            return {'frames':[],'world_references':['ghost']}
        r=GatedRuleReader(A(),ConfidenceGate(),resolver).read('Move the box.',history=[{'role':'user','content':'A box.'}])
        self.assertEqual(len(r['context_ledger']['previous_turns']),1)
        self.assertEqual(r['code_proposal']['rules'],[])
        self.assertIn('nonexistent_world_reference',r['reasons'])

    def test_correction_cycles_rejected(self):
        h=[{'role':'user','content':'A B'}]
        claims=[dict(id='a',turn_id='turn-1',start=0,end=1,quote='A',status='superseded',superseded_by='b'),dict(id='b',turn_id='turn-1',start=2,end=3,quote='B',status='superseded',superseded_by='a')]
        with self.assertRaises(ValueError):context_snapshot(h,claims=claims)
