import copy
import unittest

from kobra.ollama import decoding_schema
from kobra.read import ReadLimits, response_schema as prose_schema
from kobra.structured_read import response_schema as graph_schema
from kobra.structured_read import bind_structured_proposal
from kobra import Request, TextView, ReadContractError


class DecodingSchemaTests(unittest.TestCase):
    def test_projection_keeps_contract_structure_without_mutation(self):
        for schema in (prose_schema(ReadLimits()), graph_schema()):
            original = copy.deepcopy(schema)
            result = decoding_schema(schema)
            self.assertEqual(schema, original)
            self.assertEqual(result['required'], schema['required'])
            self.assertFalse(result['additionalProperties'])
            def check(value):
                if isinstance(value, dict):
                    for key, child in value.items():
                        if key in ('maxLength', 'maxItems'):
                            self.assertLess(child, 2000)
                        check(child)
                elif isinstance(value, list):
                    for child in value:
                        check(child)
            check(result)

    def test_small_bounds_and_numeric_indices_stay(self):
        schema = {'type': 'array', 'maxItems': 128, 'items':
                  {'type': 'integer', 'minimum': 0, 'maximum': 20000}}
        self.assertEqual(decoding_schema(schema), schema)

    def test_large_minimum_fails_instead_of_changing_contract(self):
        for key in ('minItems', 'minLength'):
            with self.assertRaises(ValueError):
                decoding_schema({key: 2000})

    def test_instance_literals_are_not_rewritten(self):
        schema = {'enum': [{'maxLength': 4000}], 'const': {'minItems': 4000}}
        self.assertEqual(decoding_schema(schema), schema)

    def test_property_names_are_not_schema_keywords(self):
        schema = {'type': 'object', 'properties':
                  {'const': {'type': 'string', 'maxLength': 4000}}}
        result = decoding_schema(schema)
        self.assertEqual(result['properties']['const'], {'type': 'string'})

    def test_original_upper_bound_still_rejects_generated_content(self):
        value = {'nodes': [{'kind': 'request',
                           'evidence': [{'quote': 'go', 'occurrence': 0}],
                           'uncertainty': ['x' * 4001]}], 'edges': []}
        with self.assertRaisesRegex(ReadContractError, 'at most 4000'):
            bind_structured_proposal(value, TextView('go', 'go', (0, 1, 2)), Request('go'))


if __name__ == '__main__':
    unittest.main()
