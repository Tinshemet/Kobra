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

    def test_absorbed_noun_passive_question(self):
        p=self.reader.assign('Is the key moved by Mira?')
        self.assertEqual(p['route'],'code')
        self.assertIn('C020-passive-question-noun-recovery',p['rules'])
        f=p['frames'][0]
        self.assertEqual((f['act'],f['predicate'],f['agent'],f['patient']),
                         ('question','moved','Mira','the key'))

    def test_absorbed_noun_repair_rejects_other_clause_shapes(self):
        for text in ('Is the key moved by Mira broken?',
                     'Is the key that Mira moved broken?',
                     'Is the key moved by the river?',
                     'Is the key moved?', 'The key moved by Mira.'):
            with self.subTest(text=text):
                p=self.reader.assign(text)
                self.assertNotIn('C020-passive-question-noun-recovery',p['rules'])

    def test_attr_recovery_depends_on_structure_not_vocabulary(self):
        from spacy.tokens import Doc
        from kobra.question_roles import passive_question_subject
        # A controlled parser-error fixture, not fresh accuracy evidence.
        def document(words):
            return Doc(self.reader.nlp.vocab, words=words,
                heads=[0,2,3,0,3,4,0], deps=['ROOT','det','amod','attr','agent','pobj','punct'],
                pos=['AUX','DET','NOUN','VERB','ADP','PROPN','PUNCT'],
                tags=['VBZ','DT','NN','VBN','IN','NNP','.'],
                lemmas=['be',words[1],words[2],words[3],'by',words[5],'?'])
        for noun,verb,actor in [('parcel','carried','Ravi'),('engine','repaired','Sam')]:
            d=document(['Is','the',noun,verb,'by',actor,'?'])
            repaired=passive_question_subject(d,d[0],{c.root.i:c for c in d.noun_chunks})
            self.assertIsNotNone(repaired)
            predicate,subject,patient=repaired
            self.assertEqual((predicate.text,subject.text,patient.text),(verb,noun,'the '+noun))
        d=document(['Is','every','parcel','carried','by','Ravi','?'])
        self.assertIsNone(passive_question_subject(d,d[0],{c.root.i:c for c in d.noun_chunks}))

    def test_three_sensor_questions_preserve_negative_question(self):
        for verb,actor in [('moved','Mira'),('checked','Alex'),('moved','Alex')]:
            p=self.reader.assign(f'Was the sensor not {verb} by {actor}?')
            self.assertEqual(p['route'],'code')
            self.assertIn('C021-passive-question-complement-repair',p['rules'])
            f=p['frames'][0]
            self.assertEqual((f['act'],f['predicate'],f['agent'],f['patient'],f['negation']),
                             ('question',verb,actor,'the sensor','not'))

    def test_real_complement_is_not_passive_repair(self):
        for text in ('Did Mira say the sensor was moved?', 'Was the sensor that Alex checked moved by Mira?',
                     'Was the sensor not moved by Mira because it failed?'):
            p=self.reader.assign(text)
            self.assertEqual(p['route'],'unresolved')
            self.assertNotIn('C021-passive-question-complement-repair',p['rules'])
