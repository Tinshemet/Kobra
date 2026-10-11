import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from evaluate_routing import judge, evaluate
from kobra.selection_read import SLOTS
from kobra.confidence_gate import Calibration, ConfidenceGate, GatedRuleReader


def frame():
    return dict({s:'NONE' for s in SLOTS},act='request',predicate='Move',patient='the parcel')


def gold(ask=False):
    return dict(ask_required=ask,ask_reasons=['missing_context:target'] if ask else [],
                expected=[{k:[v] for k,v in frame().items()}])


class RoutingTests(unittest.TestCase):
    def test_three_correct_categories_and_failures(self):
        records=[]
        for origin in ('code','AI'):
            r=dict(route='ACCEPT',assignment_source=origin,proposal={'frames':[frame()]})
            self.assertEqual(judge(gold(),r),'correct_'+origin)
            records.append(dict(id=origin,gold=gold(),result=r))
            bad=copy.deepcopy(r);bad['proposal']['frames'][0]['patient']='NONE'
            self.assertEqual(judge(gold(),bad),'wrong_'+origin)
            self.assertEqual(judge(gold(True),r),'unsafe_accept')
        ask=dict(route='ASK',reasons=['missing_context:target'])
        self.assertEqual(judge(gold(True),ask),'correct_ASK')
        self.assertEqual(judge(gold(),ask),'unnecessary_ASK')
        records.append(dict(id='ASK',gold=gold(True),result=ask))
        self.assertEqual(evaluate(records)['counts'],{'correct_code':1,'correct_AI':1,'correct_ASK':1})
    def test_ask_everything_does_not_pass(self):
        r=dict(route='ASK',reasons=['uncalibrated_cohort'])
        self.assertEqual(judge(gold(),r),'unnecessary_ASK')
        self.assertEqual(judge(gold(True),r),'unjustified_ASK')
    def test_wrong_existing_world_id_is_wrong_ai(self):
        g=gold();g['groundings']={'it':'box-1'}
        r=dict(route='ACCEPT',assignment_source='AI',proposal={'frames':[frame()],'groundings':{'it':'box-2'}})
        self.assertEqual(judge(g,r),'wrong_AI')
    def test_real_wrapper_routes_all_three_with_fixture_resolver(self):
        class Assigner:
            def __init__(self,resolved):self.resolved=resolved
            def assign(self,text):
                return dict(route='code' if self.resolved else 'unresolved',rules=['fixture'],frames=[frame()] if self.resolved else [],source=text)
        calibration={c:Calibration(1000,1000,'synthetic-test-only',c) for c in ('code:fixture:memory-grounding-2','model-unresolved-v1:memory-grounding-2')}
        gate=ConfidenceGate(calibration)
        code=GatedRuleReader(Assigner(True),gate).read('Move the parcel.')
        ai=GatedRuleReader(Assigner(False),gate,lambda request:{'frames':[frame()]}).read('Move the parcel.')
        ask=GatedRuleReader(Assigner(False),gate).read('Move the parcel.',missing_context=['target'])
        self.assertEqual(judge(gold(),code),'correct_code')
        self.assertEqual(judge(gold(),ai),'correct_AI')
        self.assertEqual(judge(gold(True),ask),'correct_ASK')
    def test_accepted_malformed_output_is_not_a_success(self):
        for p in (None, {}, {'frames':['bad']}):
            self.assertEqual(judge(gold(),dict(route='ACCEPT',assignment_source='AI',proposal=p)),'invalid_proposal')

    def test_missing_gold_ask_reason_is_rejected(self):
        g=gold(True);g['ask_reasons']=[]
        with self.assertRaises(ValueError):judge(g,{'route':'ASK'})
