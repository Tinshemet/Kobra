import json
import unittest
from unittest.mock import Mock
from kobra.ollama import ConstrainedSelectionProvider, GenerateSelectionProvider


class ConstrainedSelectionTests(unittest.TestCase):
    def test_generate_endpoint_preserves_instruction_data_and_schema(self):
        provider=GenerateSelectionProvider(think=False)
        provider._request=Mock(return_value={'done':True,'done_reason':'stop','response':'{"frames":[{"choice":"A"}]}','context':[1,2,3]})
        result=provider.select(prompt='p',text='{"sentence":"s"}',schema={'properties':{'choice':{'enum':['A']}},'required':['choice']},name='arrange_read',residual_field=False)
        path,payload=provider._request.call_args.args
        self.assertEqual(path,'/api/generate')
        self.assertNotIn('messages',payload)
        self.assertIn('p',payload['system'])
        self.assertEqual(json.loads(payload['prompt'])['sentence'],'s')
        self.assertEqual(result['frames'],[{'choice':'A'}])
        self.assertNotIn('context',payload)

    def test_transport_preflight_rejects_ignored_constraints(self):
        provider=ConstrainedSelectionProvider()
        provider.complete=Mock(return_value={'frames':[{'choice':'FORBIDDEN_RED'}]})
        with self.assertRaisesRegex(ValueError,'did not enforce'):
            provider.check_constraints()

    def test_transport_preflight_accepts_verified_nested_output(self):
        provider=ConstrainedSelectionProvider()
        provider.complete=Mock(return_value={'frames':[{'choice':'ALLOWED_BLUE','required_marker':'PRESENT'}]})
        self.assertEqual(provider.check_constraints()['state'],'verified')

    def test_explicit_thinking_and_penalty_controls(self):
        provider=ConstrainedSelectionProvider(think=False)
        provider._request=Mock(return_value={'done':True,'done_reason':'stop','message':{'content':'{"frames":[{}]}'}})
        provider.select(prompt='p',text='{}',schema={'properties':{}},name='arrange_read',residual_field=False)
        payload=provider._request.call_args.args[1]
        self.assertIs(payload['think'],False)
        self.assertEqual(payload['options']['presence_penalty'],0)
        self.assertEqual(payload['options']['repeat_penalty'],1)

    def test_schema_and_visible_menus_agree(self):
        provider=ConstrainedSelectionProvider()
        frame={'act':'request','predicate':'Open'}
        provider._request=Mock(return_value={'done':True,'done_reason':'stop',
                                            'message':{'content':json.dumps({'frames':[frame]})}})
        schema={'type':'object','properties':{'act':{'type':'string','enum':['request']},
                    'predicate':{'type':'string','enum':['NONE','Open']}},
                'required':['act','predicate'],'additionalProperties':False}
        result=provider.select(prompt='Arrange by calling arrange_read.',text='{"sentence":"Open."}',
                               schema=schema,name='arrange_read',residual_field=False)
        self.assertEqual(result,{'frames':[frame],'unrepresented':[]})
        payload=provider._request.call_args.args[1]
        self.assertEqual(payload['format']['properties']['frames']['items'],schema)
        self.assertNotIn('tools',payload)
        visible=json.loads(payload['messages'][1]['content'])['slot_menus']
        self.assertEqual(visible['predicate'],['NONE','Open'])

    def test_truncation_not_accepted(self):
        provider=ConstrainedSelectionProvider()
        provider._request=Mock(return_value={'done':True,'done_reason':'length','message':{'content':'{}'}})
        with self.assertRaisesRegex(ValueError,'finish normally'):
            provider.select(prompt='p',text='{}',schema={'properties':{}},name='arrange_read',residual_field=False)

    def test_schema_violation_is_not_silently_accepted(self):
        schema={'properties':{'choice':{'enum':['A']}},'required':['choice']}
        for frame in ({},{'choice':'B'}):
            with self.subTest(frame=frame):
                provider=ConstrainedSelectionProvider()
                provider.complete=Mock(return_value={'frames':[frame]})
                with self.assertRaises(ValueError):
                    provider.select(prompt='p',text='{}',schema=schema,name='arrange_read',residual_field=False)

    def test_unexpected_envelope_not_repaired(self):
        provider=ConstrainedSelectionProvider()
        provider._request=Mock(return_value={'done':True,'done_reason':'stop','message':{'content':'{"frames":[],"extra":1}'}})
        with self.assertRaisesRegex(ValueError,'unexpected constrained'):
            provider.select(prompt='p',text='{}',schema={'properties':{}},name='arrange_read',residual_field=False)
