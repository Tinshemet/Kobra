"""Regression tests for observed false successes; not fresh accuracy evidence."""
import unittest
from kobra.rule_assignment import RuleAssigner

class PassiveQuestionFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader=RuleAssigner()

    def test_four_observed_wrong_cases_preserve_patient_agent_and_negation(self):
        for actor,negative in [('Alex',False),('Mira',True),('Nia',True),('Alex',True)]:
            text=f'Are the servers {"not " if negative else ""}checked by {actor}?'
            with self.subTest(text=text):
                p=self.reader.assign(text)
                self.assertEqual(p['route'],'code')
                self.assertIn('C017-inverted-passive-agent-evidence',p['rules'])
                f=p['frames'][0]
                self.assertEqual((f['act'],f['predicate'],f['agent'],f['patient'],f['negation']),
                                 ('question','checked',actor,'the servers','not' if negative else 'NONE'))

    def test_agent_can_be_full_noun_phrase(self):
        p=self.reader.assign('Are the servers checked by the technician?')
        self.assertEqual(p['route'],'code')
        self.assertEqual(p['frames'][0]['agent'],'the technician')
        self.assertEqual(p['frames'][0]['patient'],'the servers')

    def test_active_question_not_reversed(self):
        p=self.reader.assign('Have the engineers checked the servers?')
        self.assertEqual(p['route'],'code')
        self.assertEqual(p['frames'][0]['agent'],'the engineers')
        self.assertEqual(p['frames'][0]['patient'],'the servers')
        self.assertNotIn('C017-inverted-passive-agent-evidence',p['rules'])

    def test_by_location_does_not_make_passive_agent(self):
        p=self.reader.assign('Are the servers running by the river?')
        self.assertEqual(p['route'],'unresolved')
        self.assertNotIn('C017-inverted-passive-agent-evidence',p['rules'])

    def test_different_parser_failure_stays_explicit(self):
        p=self.reader.assign('Were the books carried by Mira?')
        self.assertEqual(p['route'],'unresolved')
        self.assertIn('additional lexical verb',p['reasons'])
