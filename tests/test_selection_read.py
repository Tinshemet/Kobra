import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

from kobra import ClientConfig, IdentityFrontDoor, ReadContractError, Request, SelectingReader, Services, TextView
from kobra.selection_read import SLOTS, bind_selection, candidates_for
from kobra.ollama import OllamaProvider


def frame(**kw):
    return {'act':'request',**{s:'NONE' for s in SLOTS},**kw}


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.text='Do not open the door.'
        self.view=TextView(self.text,self.text,tuple(range(len(self.text)+1)))
        self.candidates=candidates_for(self.view)
        self.ids={c.text:c.id for c in self.candidates}

    def test_code_binds_source_and_repeated_occurrences(self):
        result=bind_selection({'frames':[frame(predicate=self.ids['open'],patient=self.ids['the door'],negation=self.ids['not'])], 'unrepresented':[]},self.view,self.candidates)
        c=result.frames[0].slots['patient']
        self.assertEqual(self.text[c.original_start:c.original_end],'the door')
        text='go go'
        cs=candidates_for(TextView(text,text,tuple(range(6))))
        matches=[c for c in cs if c.text=='go']
        self.assertEqual(len(matches),2)
        self.assertNotEqual(matches[0].id,matches[1].id)

    def test_unknown_missing_and_unrepresented_survive(self):
        result=bind_selection({'frames':[frame(predicate='MISSING',agent='UNKNOWN')], 'unrepresented':[self.ids['the door']]},self.view,self.candidates)
        self.assertEqual(result.frames[0].slots['predicate'],'MISSING')
        self.assertEqual({d.code for d in result.diagnostics},{'read.unresolved-selection','read.unrepresented'})

    def test_fabrication_and_wrong_structure_rejected(self):
        for proposal in [ {'frames':[frame(predicate='invented')],'unrepresented':[]},
                          {'frames':'[]','unrepresented':[]},
                          {'frames':[frame(extra='bad')],'unrepresented':[]},
                          {'frames':[frame(predicate=1)],'unrepresented':[]} ]:
            with self.subTest(proposal=proposal),self.assertRaises(ReadContractError):
                bind_selection(proposal,self.view,self.candidates)

    def test_one_batched_selection_call_no_gold(self):
        model=Mock()
        model.select.return_value={'frames':[frame(predicate=self.ids['open'])],'unrepresented':[]}
        services=Services(ClientConfig('test','1'),model=model)
        SelectingReader().read(self.view,Request(self.text),services)
        model.select.assert_called_once()
        self.assertIn(self.text,model.select.call_args.kwargs['text'])
        self.assertNotIn('expected',model.select.call_args.kwargs['text'])

    def test_oversize_is_explicit_not_truncated(self):
        text=' '.join(['word']*33)
        with self.assertRaises(ReadContractError):
            candidates_for(TextView(text,text,tuple(range(len(text)+1))))

    def test_native_flat_calls_construct_frame_list(self):
        provider=OllamaProvider()
        args=frame(predicate='s0_0',unrepresented='NONE')
        provider._request=Mock(return_value={'done':True,'done_reason':'stop','message':{
            'tool_calls':[{'function':{'name':'select_read','arguments':args}}]}})
        result=provider.select(prompt='p',text='t',schema={},name='select_read')
        self.assertEqual(result,{'frames':[frame(predicate='s0_0')],'unrepresented':[]})
        self.assertIn('tools',provider.last_exchange['request'])

    def test_foreign_tool_and_truncation_rejected(self):
        for reply in [{'done':True,'done_reason':'length'}, {'done':True,'done_reason':'stop','message':{'tool_calls':[{'function':{'name':'execute','arguments':{}}}]}}]:
            provider=OllamaProvider();provider._request=Mock(return_value=reply)
            with self.assertRaises(ValueError):
                provider.select(prompt='p',text='t',schema={},name='select_read')


class ScorerTests(unittest.TestCase):
    def test_missing_extra_and_wrong_slots_count(self):
        path=Path(__file__).parents[1]/'tools/evaluate_selection.py'
        spec=importlib.util.spec_from_file_location('selection_eval',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        pred=frame(predicate='open')
        gold=[{k:[v] for k,v in pred.items()}]
        self.assertTrue(module.score(gold,[pred])['exact'])
        self.assertEqual(module.score(gold,[])['slots_correct'],0)
        self.assertEqual(module.score(gold,[pred,pred])['slots_total'],22)
        self.assertFalse(module.score(gold,[pred],True)['exact'])
        wrong=dict(pred,act='assertion')
        self.assertEqual(module.score(gold,[wrong])['slots_correct'],10)


if __name__=='__main__':
    unittest.main()
