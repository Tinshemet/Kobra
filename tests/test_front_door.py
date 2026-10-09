import json
import subprocess
import sys
import unittest
from pathlib import Path

from kobra import ClientConfig, DomainVocabulary, EnglishFrontDoor, Request, Services


class FrontDoorTests(unittest.TestCase):
    def setUp(self):
        self.services = Services(ClientConfig("documents", "1"))
        self.vocabulary = DomainVocabulary(
            nouns=frozenset({"report", "reports"}),
            operations=frozenset({"send", "compare"}),
            statuses=frozenset({"approved", "pending"}),
            known_names=frozenset({"alpha"}),
        )
        self.front = EnglishFrontDoor(self.vocabulary)

    def normalize(self, text):
        return self.front.normalize(Request(text), self.services)

    def test_source_compatibility(self):
        for path in sorted(
            (Path(__file__).parent / "fixtures").glob("front-door-*.json")
        ):
            fixture = json.loads(path.read_text())
            front = EnglishFrontDoor(
                DomainVocabulary(
                    **{
                        key: frozenset(words)
                        for key, words in fixture["profile"].items()
                    }
                )
            )
            for case in fixture["cases"]:
                with self.subTest(
                    fixture=path.name, family=case["family"], request=case["request"]
                ):
                    view = front.normalize(Request(case["request"]), self.services)
                    self.assertEqual(view.text, case["text"])
                    self.assertEqual(list(view.back), case["back"])
                    self.assertEqual(
                        [note.message for note in view.diagnostics], case["notices"]
                    )

    def test_pause_removal_keeps_original_offsets(self):
        text = "um, compare the reports"
        view = self.normalize(text)
        self.assertEqual(view.text, "compare the reports")
        self.assertEqual(view.back, tuple(range(4, len(text) + 1)))
        self.assertEqual(view.original, text)
        self.assertTrue(view.diagnostics)

    def test_conditional_clause_boundary(self):
        self.assertEqual(
            self.normalize("if the report is approved send it").text,
            "if the report is approved, send it",
        )

    def test_quoted_instructions_are_not_rewritten(self):
        text = 'Translate "um no wati send-the-report"'
        self.assertEqual(self.normalize(text).text, text)

    def test_unicode_whitespace_is_announced(self):
        view = self.normalize("send\u00a0the report to Zoë")
        self.assertEqual(view.text, "send the report to Zoë")
        self.assertEqual(view.back, tuple(range(len(view.original) + 1)))
        self.assertTrue(view.diagnostics)

    def test_known_names_are_per_client(self):
        self.assertEqual(self.normalize("sendalpha").text, "send alpha")
        other = EnglishFrontDoor(
            DomainVocabulary(
                nouns=frozenset({"appointment", "appointments"}),
                operations=frozenset({"schedule"}),
                known_names=frozenset({"beta"}),
            )
        )
        self.assertEqual(
            other.normalize(Request("sendalpha"), self.services).text, "sendalpha"
        )
        self.assertEqual(
            other.normalize(Request("schedulebeta"), self.services).text,
            "schedule beta",
        )
        self.assertEqual(self.normalize("schedulebeta").text, "schedulebeta")

    def test_flags_and_identifiers_remain_intact(self):
        for text in ("send --all-the-reports", "send report-alpha-2", "send alpah"):
            with self.subTest(text=text):
                self.assertEqual(self.normalize(text).text, text)

    def test_no_application_imports(self):
        code = """
import importlib.abc, sys
class BlockApplications(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'planner', 'orchestrator', 'engines', 'executor'}:
            raise RuntimeError('Application import: ' + fullname)
sys.meta_path.insert(0, BlockApplications())
from kobra import DomainVocabulary, EnglishFrontDoor, Request, Services, ClientConfig
front = EnglishFrontDoor(DomainVocabulary(nouns=frozenset({'report'}), operations=frozenset({'send'})))
view = front.normalize(Request('um if the report is approved send it'), Services(ClientConfig('isolated', '1')))
assert view.text == 'if the report is approved, send it', view
"""
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_configuration_is_immutable_and_explicit(self):
        with self.assertRaises(TypeError):
            DomainVocabulary(nouns={"report"})
        with self.assertRaises(ValueError):
            DomainVocabulary(nouns=frozenset({"Report"}))
        with self.assertRaises(TypeError):
            EnglishFrontDoor()


if __name__ == "__main__":
    unittest.main()
