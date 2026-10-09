"""Hand-checked graph projection cases, independent of READ predictions."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from serpent_slots import project


class SerpentProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases={r['sentence']:r['source'] for r in json.loads((ROOT/'benchmarks/read300/adapter-development.json').read_text())}

    def test_conditional_is_not_asserted_and_repeated_object_is_local(self):
        result=project(self.cases['If the server fails, Alex will check the server.'])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['patient'],['the server'])
        self.assertEqual(result[0]['condition'],['If the server fails'])
        self.assertEqual(result[0]['modality'],['will'])

    def test_passive_roles(self):
        result=project(self.cases['The server was checked by Alex.'])[0]
        self.assertEqual(result['predicate'],['checked'])
        self.assertEqual(result['agent'],['Alex'])
        self.assertEqual(result['patient'],['The server'])

    def test_scope_chain(self):
        result=project(self.cases['Alex might not check the server.'])[0]
        self.assertEqual(result['negation'],['not'])
        self.assertEqual(result['modality'],['might'])

    def test_missing_is_not_absent(self):
        result=project(self.cases['Check one.'])[0]
        self.assertEqual(result['patient'],['MISSING'])
        self.assertEqual(result['agent'],['NONE'])
        self.assertEqual(result['quantity'],['one'])

    def test_elided_verb_not_invented(self):
        result=project(self.cases['Alex checked a server, and Mira a server.'])
        self.assertEqual(result[1]['predicate'],['MISSING'])
        self.assertEqual(result[1]['agent'],['Mira'])

    def test_shared_agent(self):
        result=project(self.cases['Alex waits and hums.'])
        self.assertEqual([f['agent'] for f in result],[['Alex'],['Alex']])

    def test_np_quantifiers_retained(self):
        result=project(self.cases['Alex gives each student two books.'])[0]
        self.assertEqual(result['recipient'],['each student'])
        self.assertEqual(result['patient'],['two books'])
        self.assertEqual(result['quantity'],['two'])

    def test_nominal_coordination(self):
        result=project(self.cases['Alex and Mira check the server.'])[0]
        self.assertEqual(result['agent'],['Alex and Mira'])

    def test_relative_reference_not_resolved(self):
        result=project(self.cases['The server that Alex checked restarted.'])
        self.assertEqual(result[0]['patient'],['that'])
        self.assertEqual(result[1]['agent'],['The server'])

    def test_full_sources_not_mutated(self):
        before=json.dumps(self.cases,sort_keys=True)
        for case in self.cases.values():
            project(case)
        self.assertEqual(json.dumps(self.cases,sort_keys=True),before)
