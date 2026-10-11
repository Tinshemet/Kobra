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

    def test_acl_attachment_repaired_without_answer_facts(self):
        for text, predicate, actor, patient, negation in [
            ('Were the books carried by Mira?', 'carried', 'Mira', 'the books', 'NONE'),
            ('Was the server not restarted by Nia?', 'restarted', 'Nia', 'the server', 'not')]:
            with self.subTest(text=text):
                p=self.reader.assign(text)
                self.assertEqual(p['route'],'code')
                self.assertIn('C018-passive-question-role-normalization',p['rules'])
                f=p['frames'][0]
                self.assertEqual((f['act'],f['predicate'],f['agent'],f['patient'],f['negation']),
                                 ('question',predicate,actor,patient,negation))

    def test_relative_clause_is_not_promoted(self):
        for text in ('Are the books carried by Mira damaged?', 'Are the books that Mira carried damaged?'):
            with self.subTest(text=text):
                p=self.reader.assign(text)
                self.assertEqual(p['route'],'unresolved')
                self.assertNotIn('C018-passive-question-role-normalization',p['rules'])

    def test_ordered_double_object(self):
        p=self.reader.assign('Alex shows Mira a key.')
        self.assertEqual(p['route'],'code')
        self.assertIn('C019-ordered-double-object-roles',p['rules'])
        self.assertEqual((p['frames'][0]['agent'],p['frames'][0]['recipient'],p['frames'][0]['patient']),
                         ('Alex','Mira','a key'))

    def test_single_object_is_not_double_object(self):
        p=self.reader.assign('Alex shows a key.')
        self.assertNotIn('C019-ordered-double-object-roles',p['rules'])
        self.assertEqual(p['frames'][0]['patient'],'a key')
