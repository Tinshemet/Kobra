"""Grounding authority remains deterministic even with a resolver installed."""
import unittest
from copy import deepcopy
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from kobra.selection_read import SLOTS


class FixedAssigner:
    def __init__(self, proposal=None):
        self.proposal = proposal or dict(route='unresolved', rules=[], frames=[])

    def assign(self, text):
        return deepcopy(self.proposal)


def frame(patient='the parcel'):
    return dict({s: 'NONE' for s in SLOTS}, act='request', predicate='Move', patient=patient)


class GroundingPolicyTests(unittest.TestCase):
    def test_missing_context_never_invokes_model(self):
        calls = []
        reader = GatedRuleReader(FixedAssigner(), ConfidenceGate(), lambda x: calls.append(x))
        result = reader.read('Move the parcel.', missing_context=['recipient'])
        self.assertEqual(calls, [])
        self.assertEqual(result['assignment_source'], 'unresolved')
        self.assertIn('missing_context:recipient', result['reasons'])

    def test_reference_cues_with_empty_frames_never_invoke_model(self):
        for text in ('Move it.', 'Did she finish my task?', 'Restart the second one and move them.',
                     'Show your account.', 'Move this.', 'Say "move it".'):
            with self.subTest(text=text):
                calls = []
                reader = GatedRuleReader(FixedAssigner(), ConfidenceGate(), lambda x: calls.append(x))
                result = reader.read(text, world={'box': {'name': 'box'}},
                                     history=[{'role': 'user', 'content': 'The box.'}])
                self.assertEqual(calls, [])
                self.assertEqual(result['route'], 'ASK')
                self.assertTrue(result['resolver_blocked_reasons'])

    def test_known_unresolved_local_reference_blocks_resolver(self):
        proposal = dict(route='unresolved', rules=[], frames=[],
                        local_references=[{'status': 'ambiguous', 'mention': {'text': 'target'}}])
        calls = []
        result = GatedRuleReader(FixedAssigner(proposal), ConfidenceGate(),
                                lambda x: calls.append(x)).read('Move target.')
        self.assertEqual(calls, [])
        self.assertIn('unresolved_local_reference', result['reasons'])

    def test_grammar_only_fallback_remains_available(self):
        calls = []
        def resolver(request):
            calls.append(request)
            return {'frames': [frame()]}
        result = GatedRuleReader(FixedAssigner(), ConfidenceGate(), resolver).read('Move the parcel.')
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['assignment_source'], 'AI')

    def test_existing_world_id_does_not_authorize_model_identity(self):
        def resolver(request):
            return {'frames': [frame()], 'groundings': {'the parcel': 'parcel-1'},
                    'world_references': ['parcel-1']}
        result = GatedRuleReader(FixedAssigner(), ConfidenceGate(), resolver).read(
            'Move the parcel.', world={'parcel-1': {'name': 'parcel'}})
        self.assertIn('model_identity_assignment_not_supported', result['reasons'])
        self.assertNotIn('groundings', result['proposal'])
        self.assertNotIn('world_references', result['proposal'])

    def test_question_parse_does_not_require_world_answer(self):
        proposal = dict(route='code', rules=['test'], frames=[dict(
            frame('the books'), act='question', predicate='carried', agent='Mira')])
        result = GatedRuleReader(FixedAssigner(proposal), ConfidenceGate()).read(
            'Were the books carried by Mira?')
        self.assertEqual(result['reasons'], ['uncalibrated_cohort'])
        self.assertEqual(result['assignment_source'], 'code')

    def test_stale_or_ambiguous_knowledge_blocks_before_model(self):
        from kobra.knowledge import KnowledgeSnapshot
        for status, entities in (
                ('stale', {'b': {'name': 'box'}}),
                ('current', {'a': {'name': 'red', 'aliases': ['box']},
                             'b': {'name': 'blue', 'aliases': ['box']}})):
            with self.subTest(status=status):
                knowledge = KnowledgeSnapshot(live=dict(
                    revision='fixture', source='fixture', status=status, entities=entities))
                calls = []
                result = GatedRuleReader(FixedAssigner(), ConfidenceGate(),
                    lambda x: calls.append(x), knowledge=knowledge).read('Move the box.')
                self.assertEqual(calls, [])
                self.assertEqual(result['route'], 'ASK')

    def test_code_generated_local_binding_survives(self):
        proposal = dict(route='code', rules=['fixture'], frames=[frame('it')],
                        local_references=[dict(frame=0, slot='patient', status='resolved',
                                              mention=dict(text='it', start=5, end=7), entity_id='e1')])
        result = GatedRuleReader(FixedAssigner(proposal), ConfidenceGate()).read('Move it.')
        self.assertEqual(result['reasons'], ['uncalibrated_cohort'])

    def test_code_personal_or_possessive_role_requires_grounding(self):
        for patient in ('you', 'your parcel', 'her', 'my parcel'):
            with self.subTest(patient=patient):
                proposal = dict(route='code', rules=['fixture'], frames=[frame(patient)])
                result = GatedRuleReader(FixedAssigner(proposal), ConfidenceGate()).read(
                    'Move ' + patient + '.')
                self.assertIn('ungrounded_reference:patient', result['reasons'])
