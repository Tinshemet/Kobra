"""Adversarial integration contracts; synthetic calibration is NOT accuracy evidence."""
from copy import deepcopy
import unittest

from kobra.confidence_gate import Calibration, ConfidenceGate, GatedRuleReader
from kobra.knowledge import KnowledgeSnapshot
from kobra.selection_read import SLOTS


def frame(predicate='Move', patient='the box'):
    return dict({slot: 'NONE' for slot in SLOTS}, act='request', predicate=predicate, patient=patient)


def library(entities, status='current'):
    return dict(revision='live-1', source='fixture-client', status=status, entities=entities)


def archive_record(**changes):
    record = dict(id='lex-1', word='jumpbox', type='class', source='told',
                  status='ratified', provenance='fixture-human', kind='vm')
    record.update(changes)
    return record


def archive(record):
    return dict(revision='archive-1', source='fixture-archive', records=[record])


class FixedAssigner:
    def __init__(self, proposal):
        self.proposal = proposal

    def assign(self, text):
        return dict(source=text, rules=['FIXTURE'], **deepcopy(self.proposal))


class KnowledgeIntegrationTests(unittest.TestCase):
    def read(self, knowledge, *, patient='the box', predicate='Move', world=None,
             resolver=None, history=(), calibrated=True):
        text = f'{predicate} {patient}.'
        assigner = FixedAssigner(dict(route='unresolved' if resolver else 'code',
                                     frames=[] if resolver else [frame(predicate, patient)]))
        gate = ConfidenceGate()
        reader = GatedRuleReader(assigner, gate, resolver=resolver, knowledge=knowledge)
        result = reader.read(text, world=world, history=history)
        if calibrated:
            cohort = result['cohort']
            gate.calibration[cohort] = Calibration(1000, 1000, 'synthetic-contract-fixture', cohort)
            result = reader.read(text, world=world, history=history)
        return result

    def test_exact_live_binding_preserves_role_literal_and_input(self):
        entities = {'box-1': {'name': 'box', 'kind': 'parcel'}}
        knowledge = KnowledgeSnapshot(live=library(entities))
        result = self.read(knowledge)
        self.assertEqual(result['route'], 'ACCEPT')
        self.assertEqual(result['proposal']['groundings'], {'the box': 'box-1'})
        self.assertEqual(result['proposal']['frames'][0]['patient'], 'the box')
        self.assertNotIn('groundings', result['code_proposal'])
        self.assertEqual(entities, {'box-1': {'name': 'box', 'kind': 'parcel'}})

    def test_duplicate_live_alias_is_ask_even_with_synthetic_calibration(self):
        knowledge = KnowledgeSnapshot(live=library({
            'one': {'name': 'red', 'aliases': ['box']},
            'two': {'name': 'blue', 'aliases': ['box']}}))
        result = self.read(knowledge)
        self.assertEqual(result['route'], 'ASK')
        self.assertIn('knowledge_ambiguous:0:patient', result['reasons'])
        self.assertEqual(result['knowledge_evidence']['bindings'], [])

    def test_caller_world_alias_collision_cannot_silently_choose_library(self):
        knowledge = KnowledgeSnapshot(live=library({'one': {'name': 'box'}}))
        result = self.read(knowledge, world={'two': {'name': 'other', 'aliases': ['box']}})
        self.assertEqual(result['route'], 'ASK')
        self.assertEqual(result['knowledge_evidence']['bindings'], [])

    def test_same_id_disagreement_is_ask_and_preserved(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box', 'kind': 'vm'}}))
        result = self.read(knowledge, world={'box-1': {'name': 'box', 'kind': 'parcel'}})
        self.assertEqual(result['route'], 'ASK')
        self.assertIn('knowledge_world_conflict:box-1', result['reasons'])

    def test_id_is_not_implicitly_an_entity_name(self):
        knowledge = KnowledgeSnapshot(live=library({
            'box': {'name': 'other'}, 'actual-box': {'name': 'box'}}))
        result = self.read(knowledge)
        self.assertEqual(result['proposal']['groundings'], {'the box': 'actual-box'})

    def test_stale_live_record_cannot_supply_grounding(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}, status='stale'))
        result = self.read(knowledge)
        self.assertEqual(result['route'], 'ASK')
        self.assertEqual(result['context_ledger']['world_entities'], [])
        self.assertFalse(result['proposal'].get('groundings'))

    def test_archive_class_definition_never_becomes_live_instance(self):
        knowledge = KnowledgeSnapshot(archive=archive(archive_record()))
        result = self.read(knowledge, patient='a jumpbox', predicate='Create')
        self.assertEqual(result['context_ledger']['world_entities'], [])
        self.assertEqual(result['knowledge_evidence']['bindings'], [])
        self.assertFalse(result['proposal'].get('groundings'))
        lookup = result['knowledge_evidence']['matches'][0]['lookup']
        self.assertEqual(lookup['selected'][0]['record']['kind'], 'vm')

    def test_pending_and_imported_archive_never_settle_reading(self):
        for changes in ({'status': 'pending'}, {'source': 'imported'}):
            with self.subTest(changes=changes):
                knowledge = KnowledgeSnapshot(archive=archive(archive_record(**changes)))
                result = self.read(knowledge, patient='the jumpbox')
                self.assertEqual(result['route'], 'ASK')
                self.assertFalse(result['proposal'].get('groundings'))

    def test_negative_archive_does_not_silently_authorize_existing_target(self):
        knowledge = KnowledgeSnapshot(archive=archive(archive_record(holds=False)))
        result = self.read(knowledge, patient='the jumpbox')
        self.assertEqual(result['route'], 'ASK')
        self.assertEqual(result['knowledge_evidence']['matches'][0]['lookup']['status'], 'negative')

    def test_live_identity_outranks_negative_archive(self):
        knowledge = KnowledgeSnapshot(live=library({'vm-1': {'name': 'jumpbox'}}),
                                      archive=archive(archive_record(holds=False)))
        result = self.read(knowledge, patient='the jumpbox')
        self.assertEqual(result['route'], 'ACCEPT')
        self.assertEqual(result['proposal']['groundings'], {'the jumpbox': 'vm-1'})

    def test_creation_does_not_bind_description_to_existing_entity(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}))
        result = self.read(knowledge, predicate='Create', patient='a box')
        self.assertEqual(result['knowledge_evidence']['bindings'], [])
        self.assertFalse(result['proposal'].get('groundings'))

    def test_valid_model_named_binding_can_pass_supported_candidate_check(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}))
        def resolver(_):
            return dict(frames=[frame()], groundings={'the box': 'box-1'})
        result = self.read(knowledge, resolver=resolver)
        self.assertEqual(result['route'], 'ACCEPT')
        self.assertEqual(result['assignment_source'], 'AI')
        self.assertEqual(result['proposal']['groundings'], {'the box': 'box-1'})

    def test_resolver_cannot_choose_other_existing_id_for_exact_name(self):
        knowledge = KnowledgeSnapshot(live=library({
            'box-1': {'name': 'box'}, 'other-1': {'name': 'other'}}))
        def resolver(_):
            return dict(frames=[frame()], groundings={'the box': 'other-1'})
        result = self.read(knowledge, resolver=resolver)
        self.assertEqual(result['route'], 'ASK')
        self.assertIn('knowledge_grounding_not_supported:the box', result['reasons'])

    def test_resolver_mutation_cannot_create_authority(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}))
        before = knowledge.snapshot()
        def resolver(request):
            request['world']['ghost'] = {'name': 'box'}
            request['knowledge_evidence']['snapshot'].clear()
            request['knowledge_evidence']['issues'].clear()
            request['context_ledger']['previous_turns'].clear()
            return dict(frames=[frame()], groundings={'the box': 'ghost'})
        result = self.read(knowledge, resolver=resolver,
                           history=[{'role': 'user', 'content': 'There is a box.'}])
        self.assertEqual(result['route'], 'ASK')
        self.assertEqual(knowledge.snapshot(), before)
        self.assertEqual(result['knowledge_evidence']['snapshot'], before)
        self.assertEqual(len(result['context_ledger']['previous_turns']), 1)
        self.assertEqual([e['id'] for e in result['context_ledger']['world_entities']], ['box-1'])

    def test_malformed_model_frames_are_ask_not_reader_crash(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}))
        for frames in (None, 5, 'not frames', [None]):
            with self.subTest(frames=frames):
                result = self.read(knowledge, resolver=lambda _, f=frames: {'frames': f})
                self.assertEqual(result['route'], 'ASK')

    def test_cross_turn_pronoun_cannot_select_arbitrary_existing_id(self):
        knowledge = KnowledgeSnapshot(live=library({
            'red-1': {'name': 'red box'}, 'blue-1': {'name': 'blue box'}}))
        def resolver(_):
            return dict(frames=[frame(patient='it')], groundings={'it': 'blue-1'})
        result = self.read(knowledge, patient='it', resolver=resolver,
                           history=[{'role': 'user', 'content': 'Move the red box first.'}])
        self.assertEqual(result['route'], 'ASK')
        self.assertIn('knowledge_grounding_not_supported:it', result['reasons'])

    def test_malformed_empty_role_is_ask_not_lookup_crash(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}))
        for patient in ('', ' ', 'the '):
            with self.subTest(patient=patient):
                result = self.read(knowledge, resolver=lambda _, p=patient: {'frames': [frame(patient=p)]})
                self.assertEqual(result['route'], 'ASK')

    def test_world_reference_cannot_add_unmentioned_existing_entity(self):
        knowledge = KnowledgeSnapshot(live=library({
            'box-1': {'name': 'box'}, 'other-1': {'name': 'other'}}))
        def resolver(_):
            return dict(frames=[frame()], world_references=['other-1'])
        result = self.read(knowledge, resolver=resolver)
        self.assertEqual(result['route'], 'ASK')
        self.assertIn('knowledge_world_reference_not_supported', result['reasons'])

    def test_model_creation_cannot_ground_new_description_to_existing_entity(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}))
        def resolver(_):
            return dict(frames=[frame(predicate='Create', patient='a box')],
                        groundings={'a box': 'box-1'}, world_references=['box-1'])
        result = self.read(knowledge, patient='a box', predicate='Create', resolver=resolver)
        self.assertEqual(result['route'], 'ASK')
        self.assertIn('knowledge_grounding_not_supported:a box', result['reasons'])
        self.assertIn('knowledge_world_reference_not_supported', result['reasons'])

    def test_malformed_caller_aliases_are_ask_not_reader_crash(self):
        knowledge = KnowledgeSnapshot()
        for aliases in (None, 'box', [5]):
            with self.subTest(aliases=aliases):
                result = self.read(knowledge, world={'box-1': {'name': 'box', 'aliases': aliases}})
                self.assertEqual(result['route'], 'ASK')
                self.assertIn('knowledge_invalid_world_aliases:box-1', result['reasons'])

    def test_lookup_does_not_manufacture_calibration(self):
        knowledge = KnowledgeSnapshot(live=library({'box-1': {'name': 'box'}}))
        result = self.read(knowledge, calibrated=False)
        self.assertEqual(result['route'], 'ASK')
        self.assertIn('uncalibrated_cohort', result['reasons'])
        self.assertIsNone(result['external_score'])
