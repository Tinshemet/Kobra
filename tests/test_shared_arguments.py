"""Bounded shared-object regressions; synthetic gate fixtures are not accuracy."""
import unittest
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import Calibration, ConfidenceGate, GatedRuleReader
from kobra.knowledge import KnowledgeSnapshot
from kobra.knowledge_resolution import created_patient_frames
from kobra.selection_read import SLOTS


class SharedArgumentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assigner = RuleAssigner()

    def test_shared_patient_has_one_entity_and_original_source_span(self):
        text = 'Create and launch three VMs.'
        p = self.assigner.assign(text)
        self.assertEqual(p['route'], 'code', p)
        self.assertEqual([f['patient'] for f in p['frames']], ['three VMs', 'three VMs'])
        self.assertEqual([f['quantity'] for f in p['frames']], ['three', 'three'])
        self.assertEqual(len(p['local_entities']), 1)
        edge = p['shared_arguments'][0]
        self.assertEqual((edge['frame'], edge['donor_chunk']), (0, 'c2'))
        self.assertEqual(text[edge['span']['start']:edge['span']['end']], 'three VMs')
        self.assertGreaterEqual(edge['span']['start'], p['chunks'][0]['span']['end'])
        self.assertEqual([c['entity_id'] for c in p['chunks']], ['e1', 'e1'])
        self.assertEqual(''.join(s['text'] for s in p['source_ledger']), text)
        self.assertEqual(p['local_entities'][0]['created_by'], ['c1'])

    def test_following_pronoun_sees_one_shared_antecedent(self):
        p = self.assigner.assign('Create and launch three VMs, then restart them.')
        self.assertEqual(p['route'], 'code', p)
        self.assertEqual(len(p['local_entities']), 1)
        self.assertEqual(p['local_references'][0]['candidates'], ['e1'])
        self.assertEqual(p['local_references'][0]['entity_id'], 'e1')
        self.assertEqual(created_patient_frames(p), {0, 1, 2})
        self.assertEqual(p['chunk_relations'][0]['kind'], 'coordination_source_order_only')
        self.assertEqual(p['chunk_relations'][1]['kind'], 'explicit_then')

    def test_three_actions_one_shared_description(self):
        p = self.assigner.assign('Create, configure, and launch three VMs.')
        self.assertEqual(p['route'], 'code', p)
        self.assertEqual(len(p['shared_arguments']), 2)
        self.assertEqual(len(p['local_entities']), 1)
        self.assertEqual([f['patient'] for f in p['frames']], ['three VMs'] * 3)

    def test_noncreation_shared_entity_not_marked_created(self):
        p = self.assigner.assign('Open and read the file.')
        self.assertEqual(p['route'], 'code', p)
        self.assertEqual(p['local_entities'][0]['created_by'], [])
        self.assertEqual(created_patient_frames(p), set())

    def test_operational_oddity_is_not_syntactic_rejection(self):
        p = self.assigner.assign('Create and delete the box.')
        self.assertEqual(p['route'], 'code', p)
        self.assertEqual([f['patient'] for f in p['frames']], ['the box', 'the box'])

    def test_unsupported_attachment_scope_and_private_object_stay_unresolved(self):
        for text in [
            'Stop and inspect the pump.',
            'Create or launch three VMs.',
            'Create; launch three VMs.',
            'Create then launch three VMs.',
            'Do not create and launch three VMs.',
            'Create and launch three VMs with Kali.',
            'Create and launch it.',
            'Create and launch three VMs and two networks.',
            'Create and launch 2 boxes, one with red paint and one with blue paint.',
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.assigner.assign(text)['route'], 'unresolved')

    def test_no_left_object_propagation(self):
        self.assertEqual(self.assigner.assign('Open the file and read.')['route'], 'unresolved')

    def test_configured_pattern_boundary_can_be_disabled(self):
        r = RuleAssigner(nlp=self.assigner.nlp, shared_patterns=[])
        self.assertEqual(r.assign('Create and launch three VMs.')['route'], 'unresolved')

    def test_new_shared_target_never_grounded_to_existing_names_and_keeps_history(self):
        knowledge = KnowledgeSnapshot(live=dict(revision='w1', source='fixture', status='current',
            entities={'old1': {'name': 'Alpha'}, 'old2': {'name': 'ALPHA'}}),
            archive=dict(revision='a1', source='fixture', records=[dict(id='lex1', word='Alpha',
                type='class', source='told', status='ratified', provenance='human-fixture', kind='vm')]))
        source = 'Create and launch Alpha, then delete it.'
        history = [{'id': 'u1', 'role': 'user', 'content': 'Alpha was the old test machine.'}]
        gate = ConfidenceGate()
        reader = GatedRuleReader(self.assigner, gate, knowledge=knowledge)
        r = reader.read(source, history=history)
        cohort = r['cohort']
        gate.calibration[cohort] = Calibration(1000, 1000, 'synthetic-contract-only', cohort)
        r = reader.read(source, history=history)
        self.assertEqual(r['route'], 'ACCEPT', r['reasons'])
        self.assertEqual(created_patient_frames(r['code_proposal']), {0, 1, 2})
        self.assertEqual(r['knowledge_evidence']['bindings'], [])
        self.assertFalse(r['proposal'].get('groundings'))
        self.assertEqual(r['context_ledger']['previous_turns'][0]['content'], history[0]['content'])
        self.assertEqual(len(r['context_ledger']['world_entities']), 2)
        first = r['knowledge_evidence']['matches'][0]['lookup']
        self.assertEqual(first['selected'][0]['layer'], 'archive')
        self.assertEqual(first['selected'][0]['record']['kind'], 'vm')
        self.assertEqual(len(r['code_proposal']['local_entities']), 1)

    def test_model_created_metadata_does_not_override_live_candidate_check(self):
        class Unresolved:
            def assign(self, text):
                return dict(route='unresolved', rules=[], frames=[])
        knowledge = KnowledgeSnapshot(live=dict(revision='w1', source='fixture', status='current',
            entities={'one': {'name': 'box'}, 'two': {'name': 'box'}}))
        calls = []
        def resolver(_):
            calls.append(_)
            return dict(frames=[dict({s: 'NONE' for s in SLOTS}, act='request', predicate='Move', patient='box')],
                        local_entities=[dict(id='e1', created_by=['c1'])],
                        chunks=[dict(frame=0, entity_id='e1')],
                        groundings={'box': 'one'})
        gate = ConfidenceGate()
        reader = GatedRuleReader(Unresolved(), gate, resolver=resolver, knowledge=knowledge)
        r = reader.read('Move box.')
        cohort = r['cohort']
        gate.calibration[cohort] = Calibration(1000, 1000, 'synthetic-contract-only', cohort)
        r = reader.read('Move box.')
        self.assertEqual(r['route'], 'ASK')
        self.assertEqual(calls, [])
        self.assertIn('knowledge_unresolved_mention:box', r['reasons'])

    def test_different_shared_profiles_get_different_calibration_cohorts(self):
        text = 'Open the file.'
        default = GatedRuleReader(self.assigner, ConfidenceGate()).read(text)
        other = RuleAssigner(nlp=self.assigner.nlp, shared_patterns=[])
        changed = GatedRuleReader(other, ConfidenceGate()).read(text)
        self.assertNotEqual(default['cohort'], changed['cohort'])
        self.assertNotEqual(default['code_proposal']['configuration_id'],
                            changed['code_proposal']['configuration_id'])

    def test_action_vocabulary_alone_does_not_authorize_shared_pattern(self):
        r = RuleAssigner(nlp=self.assigner.nlp,
                         action_words=set(self.assigner.action_words) | {'frobnicate'})
        self.assertEqual(r.assign('Create and frobnicate three VMs.')['route'], 'unresolved')

    def test_same_literal_new_and_existing_role_cannot_get_global_grounding(self):
        knowledge = KnowledgeSnapshot(live=dict(revision='w1', source='fixture', status='current',
            entities={'old': {'name': 'Alpha'}}))
        gate = ConfidenceGate()
        reader = GatedRuleReader(self.assigner, gate, knowledge=knowledge)
        text = 'Create and launch Alpha, then inspect Alpha.'
        r = reader.read(text)
        cohort = r['cohort']
        gate.calibration[cohort] = Calibration(1000, 1000, 'synthetic-contract-only', cohort)
        r = reader.read(text)
        self.assertEqual(r['route'], 'ASK')
        self.assertFalse(r['proposal'].get('groundings'))
