from dataclasses import asdict
import json
import unittest
from unittest.mock import Mock

from kobra import ClientConfig, Diagnostic, Request, Services, TextView
from kobra.candidate_read import (ArrangingReader, Inventory, LinguisticCandidates,
                                 bind_arrangement, source_ledger)
from kobra.selection_read import Candidate, SLOTS
from kobra.ollama import OllamaProvider


def frame(**kw):
    return {'act':'request', **{s:'NONE' for s in SLOTS}, **kw}


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.text='Go there!  \ufffd\x00'
        self.request=Request(self.text,conversation_id='conversation-7')
        self.view=TextView(self.text,self.text,tuple(range(len(self.text)+1)))
        self.candidate=Candidate('c0_2','Go',0,2,0,2)
        menus={s:{} for s in SLOTS};menus['predicate']={'Go':self.candidate}
        self.inventory=Inventory((self.candidate,),menus,{'name':'test'})
        self.extractor=Mock();self.extractor.identity={'name':'test'}
        self.extractor.build.return_value=self.inventory
        self.model=Mock();self.model.select.return_value={'frames':[frame(predicate='Go')],'unrepresented':[]}
        self.services=Services(ClientConfig('test','1'),model=self.model)

    def verify(self,result):
        self.assertEqual(''.join(f.text for f in result.source_ledger),self.text)
        position=0
        for f in result.source_ledger:
            self.assertEqual(f.start,position)
            self.assertEqual(f.text,self.text[f.start:f.end])
            self.assertTrue(f.provisional)
            position=f.end
        self.assertEqual(position,len(self.text))
        self.assertEqual(result.request.conversation_id,'conversation-7')

    def test_arranged_and_all_leftover_labels_are_retained(self):
        result=ArrangingReader(self.extractor).read(self.view,self.request,self.services)
        self.verify(result)
        self.assertEqual(result.status,'arranged')
        self.assertEqual({f.label for f in result.source_ledger},
                         {'arranged','possibly_missing_context','noise_candidate','garbage_candidate'})
        self.assertFalse(self.model.select.call_args.kwargs['residual_field'])

    def test_invalid_selection_keeps_all_source_and_no_partial_frame(self):
        self.model.select.return_value={'frames':[frame(predicate='Go'),frame(patient='fabricated')],'unrepresented':[]}
        result=ArrangingReader(self.extractor).read(self.view,self.request,self.services)
        self.verify(result);self.assertEqual(result.status,'needs_review')
        self.assertEqual(result.frames,())
        self.assertIn('unlisted candidate',result.diagnostics[-1].message)

    def test_transport_failure_and_parser_failure_keep_every_character(self):
        for stage in ('parser','provider'):
            with self.subTest(stage=stage):
                self.extractor.build.side_effect=RuntimeError('parser failed') if stage=='parser' else None
                self.model.select.side_effect=TimeoutError('timeout') if stage=='provider' else None
                result=ArrangingReader(self.extractor).read(self.view,self.request,self.services)
                self.verify(result);self.assertEqual(result.status,'needs_review')

    def test_unknown_and_missing_are_not_discarded(self):
        self.model.select.return_value={'frames':[frame(predicate='MISSING',patient='UNKNOWN')],'unrepresented':[]}
        result=ArrangingReader(self.extractor).read(self.view,self.request,self.services)
        self.verify(result)
        self.assertEqual(result.frames[0].slots['patient'],'UNKNOWN')
        self.assertIn('read.unresolved-arrangement',{d.code for d in result.diagnostics})

    def test_omitted_slot_is_unknown_and_other_selections_survive(self):
        proposed=frame(predicate='Go');del proposed['time']
        self.model.select.return_value={'frames':[proposed],'unrepresented':[]}
        result=ArrangingReader(self.extractor).read(self.view,self.request,self.services)
        self.verify(result)
        self.assertEqual(result.frames[0].slots['time'],'UNKNOWN')
        self.assertEqual(result.frames[0].slots['predicate'].text,'Go')
        self.assertNotIn('time',result.proposal['frames'][0])

    def test_text_removed_by_front_door_still_has_original_ledger(self):
        original='  um...  '
        view=TextView(original,'',(0,),(Diagnostic('test','normalized away'),))
        empty=Inventory((),{s:{} for s in SLOTS},{})
        result=bind_arrangement({'frames':[],'unrepresented':[]},Request(original),view,empty)
        self.assertEqual(''.join(f.text for f in result.source_ledger),original)

    def test_ledger_json_roundtrip_keeps_unicode_control_and_whitespace(self):
        for text in ['',' \t\n','héllo 世界!','\x00\ufffd','it???  there', 'a\u0301']:
            with self.subTest(text=text):
                rows=json.loads(json.dumps([asdict(f) for f in source_ledger(text,())]))
                self.assertEqual(''.join(f['text'] for f in rows),text)

    def test_slot_specific_menu_is_enforced(self):
        self.model.select.return_value={'frames':[frame(patient='Go')],'unrepresented':[]}
        result=ArrangingReader(self.extractor).read(self.view,self.request,self.services)
        self.assertEqual(result.status,'needs_review')

    def test_provider_does_not_require_old_residual_argument(self):
        provider=OllamaProvider()
        provider._request=Mock(return_value={'done':True,'done_reason':'stop','message':{
            'tool_calls':[{'function':{'name':'arrange_read','arguments':frame(predicate='Go')}}]}})
        result=provider.select(prompt='p',text='t',schema={},name='arrange_read',residual_field=False)
        self.assertEqual(result,{'frames':[frame(predicate='Go')],'unrepresented':[]})


class ParserCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.extractor=LinguisticCandidates()
        except (ImportError,OSError):
            raise unittest.SkipTest('optional spaCy English model unavailable')

    def inventory(self,text):
        return self.extractor.build(TextView(text,text,tuple(range(len(text)+1))))

    def test_proposes_categories_without_all_substrings(self):
        inv=self.inventory('Close the gate.')
        self.assertIn('Close',inv.menus['predicate'])
        self.assertIn('the gate',inv.menus['patient'])
        self.assertNotIn('the',inv.menus['patient'])
        self.assertNotIn('Close the gate',inv.menus['predicate'])

    def test_condition_and_negation_candidates_exist(self):
        inv=self.inventory('If Sam agrees, do not paint the door.')
        self.assertIn('paint',inv.menus['predicate'])
        self.assertIn('not',inv.menus['negation'])
        self.assertIn('If Sam agrees',inv.menus['condition'])

    def test_duplicate_phrases_have_distinct_choices(self):
        inv=self.inventory('Inspect the valve and clean the valve.')
        choices=[c for c in inv.menus['patient'].values() if c.text=='the valve']
        self.assertEqual(len(choices),2)
        self.assertNotEqual(choices[0].id,choices[1].id)

    def test_content_fallback_recovers_mistagged_conjunct(self):
        inv=self.inventory('Mira arrives and waits.')
        self.assertIn('waits', inv.menus['predicate'])
        self.assertIn('R001-content-predicate-fallback',inv.rule_matches)

    def test_nominal_groups_and_fronted_phrase_remain_selectable(self):
        for text,slot,phrase in [
            ('Alex and Mira check the train.','agent','Alex and Mira'),
            ('This lamp, Nia checked.','patient','This lamp'),
            ('The server in the archive restarts.','agent','The server in the archive')]:
            with self.subTest(text=text):
                inv=self.inventory(text)
                self.assertIn(phrase,inv.menus[slot])

    def test_candidate_rules_can_be_ablated(self):
        text='Mira arrives and waits.'
        off=LinguisticCandidates(nlp=self.extractor.nlp,disabled_rules=['R001-content-predicate-fallback'])
        inv=off.build(TextView(text,text,tuple(range(len(text)+1))))
        self.assertNotIn('R001-content-predicate-fallback',inv.rule_matches)

    def test_relative_pronoun_survives_mistagging(self):
        inv=self.inventory('The sensor that Alex checks restarts.')
        self.assertIn('that', inv.menus['patient'])

    def test_initial_function_word_not_predicate_fallback(self):
        inv=self.inventory('If the train fails, Alex will check it.')
        self.assertNotIn('If',inv.menus['predicate'])


if __name__=='__main__':
    unittest.main()
