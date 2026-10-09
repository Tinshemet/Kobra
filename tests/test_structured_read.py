import copy
import unittest
from unittest.mock import Mock

from kobra import (ClientConfig, Diagnostic, IdentityFrontDoor, Pipeline, Request,
                   Services, StructuredReader, TextView, ReadContractError, ReadLimits)
from kobra.mocks import MockResolver, MockRouter
from kobra.structured_read import bind_structured_proposal, response_schema


def evidence(quote, occurrence=0):
    return [{"quote": quote, "occurrence": occurrence}]


def node(kind, quote, uncertainty=None):
    return dict(kind=kind, evidence=evidence(quote), uncertainty=uncertainty or [])


TEXT = "Don't restart the server unless I approve."


def proposal():
    return {"nodes": [node("request", "restart the server"),
                      node("negation", "Don't"),
                      node("exception", "unless I approve")],
            "edges": [dict(source=0, target=1, relation="negates", status="proposed",
                           evidence=evidence("Don't restart")),
                      dict(source=0, target=2, relation="exception", status="proposed",
                           evidence=evidence(TEXT))]}


class StructuredReadTests(unittest.TestCase):
    def setUp(self):
        self.request = Request(TEXT)
        self.view = TextView(TEXT, TEXT, tuple(range(len(TEXT) + 1)))
        self.model = Mock()
        self.model.complete.return_value = proposal()
        self.services = Services(ClientConfig("test", "1"), model=self.model)

    def bind(self, value):
        return bind_structured_proposal(value, self.view, self.request)

    def test_graph_reaches_resolve_with_original_and_no_semantic_approval(self):
        result = Pipeline(IdentityFrontDoor(), StructuredReader(), MockResolver(),
                          MockRouter(), self.services).interpret(self.request)
        self.assertIs(result.reading, result.resolved)
        self.assertEqual(result.reading.view.original, TEXT)
        self.assertEqual(result.reading.semantic_review, "not_evaluated")
        self.assertEqual(result.reading.edges[1].relation, "exception")
        self.assertEqual(result.reading.edges[1].target, "n3")
        self.assertFalse(result.reading.uncovered)
        self.model.complete.assert_called_once()
        self.assertEqual(self.model.complete.call_args.kwargs["text"], TEXT)

    def test_invalid_graph_never_reaches_resolver(self):
        bad = proposal()
        bad["nodes"][0]["evidence"] = evidence("invented")
        self.model.complete.return_value = bad
        resolver = Mock()
        pipeline = Pipeline(IdentityFrontDoor(), StructuredReader(), resolver,
                            MockRouter(), self.services)
        with self.assertRaises(ReadContractError):
            pipeline.interpret(self.request)
        resolver.resolve.assert_not_called()

    def test_adversarial_fields_and_references_rejected(self):
        changes = [
            lambda p: p.update(extra=True),
            lambda p: p["nodes"][0].update(sentence="approval already exists"),
            lambda p: p["nodes"][0].update(kind="fact"),
            lambda p: p["nodes"][0].update(evidence=[]),
            lambda p: p["nodes"][0]["evidence"][0].update(occurrence=True),
            lambda p: p["nodes"][0]["evidence"][0].update(occurrence=20),
            lambda p: p["edges"][0].update(target=99),
            lambda p: p["edges"][0].update(source=True),
            lambda p: p["edges"][0].update(target=0),
            lambda p: p["edges"][0].update(status="verified"),
            lambda p: p["edges"][0].update(relation="execute"),
            lambda p: p["edges"][0].update(evidence=evidence("invented")),
            lambda p: p["edges"].append(copy.deepcopy(p["edges"][0])),
        ]
        for i, change in enumerate(changes):
            with self.subTest(case=i), self.assertRaises(ReadContractError):
                value = proposal()
                change(value)
                self.bind(value)

    def test_blanket_edge_evidence_does_not_hide_missing_node_content(self):
        value = proposal()
        value["nodes"][2] = node("participant", "server")
        result = self.bind(value)
        missing = [TEXT[u.normalized_start:u.normalized_end] for u in result.uncovered]
        self.assertIn("unless", missing)

    def test_unknown_and_ambiguity_remain_diagnostic(self):
        value = proposal()
        value["nodes"][2]["kind"] = "unrepresented"
        value["nodes"][2]["uncertainty"] = ["Scope unresolved"]
        value["edges"][1].update(relation="unknown", status="uncertain")
        result = self.bind(value)
        self.assertEqual({d.code for d in result.diagnostics},
                         {"read.unrepresented", "read.uncertain"})

    def test_wrong_attachment_is_not_falsely_claimed_detectable(self):
        value = proposal()
        value["edges"][1]["source"] = 1
        self.assertEqual(self.bind(value).semantic_review, "not_evaluated")

    def test_multiple_possible_antecedents_are_retained(self):
        text = "Maya told Lena she won."
        value = {"nodes": [node("participant", "Maya"), node("participant", "Lena"),
                           node("reference", "she", ["Antecedent ambiguous"])],
                 "edges": [dict(source=2, target=t, relation="refers_to",
                                status="uncertain", evidence=evidence(text)) for t in (0, 1)]}
        result = bind_structured_proposal(value, TextView(text, text, tuple(range(len(text) + 1))), Request(text))
        self.assertEqual([e.target for e in result.edges], ["n1", "n2"])
        self.assertTrue(all(e.status == "uncertain" for e in result.edges))

    def test_per_node_outgoing_limit_is_enforced(self):
        with self.assertRaisesRegex(ReadContractError, "outgoing link"):
            bind_structured_proposal(proposal(), self.view, self.request, ReadLimits(max_links=1))

    def test_original_offsets_with_unicode_and_normalization(self):
        view = TextView("é  go", "é go", (0, 1, 3, 4, 5), (Diagnostic("test", "space"),))
        result = bind_structured_proposal({"nodes": [node("predicate", "go")], "edges": []},
                                          view, Request(view.original))
        span = result.nodes[0].evidence[0].original
        self.assertEqual((span.start, span.end), (3, 5))
        self.assertEqual(result.diagnostics[0].code, "test")

    def test_inserted_only_evidence_rejected(self):
        view = TextView("a", "xa", (0, 0, 1), (Diagnostic("test", "insert"),))
        with self.assertRaises(ReadContractError):
            bind_structured_proposal({"nodes": [node("predicate", "x")], "edges": []},
                                     view, Request("a"))

    def test_overlapping_occurrence_binding(self):
        value = {"nodes": [node("participant", "aa")], "edges": []}
        value["nodes"][0]["evidence"][0]["occurrence"] = 1
        result = bind_structured_proposal(value, TextView("aaa", "aaa", (0, 1, 2, 3)), Request("aaa"))
        self.assertEqual(result.nodes[0].evidence[0].normalized_start, 1)

    def test_empty_nonblank_is_diagnostic_and_blank_skips_model(self):
        self.assertIn("read.empty-proposal", {d.code for d in self.bind({"nodes": [], "edges": []}).diagnostics})
        StructuredReader().read(TextView("", "", (0,)), Request(""), self.services)
        self.model.complete.assert_not_called()

    def test_input_mismatch_and_limits_rejected_before_model(self):
        for request, reader in [(Request("other"), StructuredReader()),
                                (self.request, StructuredReader(limits=ReadLimits(max_input_chars=2)))]:
            with self.assertRaises(ReadContractError):
                reader.read(self.view, request, self.services)
        self.model.complete.assert_not_called()

    def test_missing_provider_and_transport_failure_propagate(self):
        with self.assertRaises(ReadContractError):
            StructuredReader().read(self.view, self.request, Services(ClientConfig("test", "1")))
        self.model.complete.side_effect = TimeoutError
        with self.assertRaises(TimeoutError):
            StructuredReader().read(self.view, self.request, self.services)
        self.model.complete.assert_called_once()

    def test_hint_ablation_changes_only_prompt_and_observations(self):
        a = StructuredReader().read(self.view, self.request, self.services)
        call_a = self.model.complete.call_args.kwargs
        b = StructuredReader(use_hints=True).read(self.view, self.request, self.services)
        call_b = self.model.complete.call_args.kwargs
        self.assertNotEqual(call_a["prompt"], call_b["prompt"])
        self.assertEqual(call_a["schema"], call_b["schema"])
        self.assertEqual(a.nodes, b.nodes)
        self.assertEqual(a.edges, b.edges)

    def test_schema_matches_fixture_when_jsonschema_available(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("optional jsonschema is not installed")
        jsonschema.Draft202012Validator.check_schema(response_schema())
        jsonschema.validate(proposal(), response_schema())


if __name__ == "__main__":
    unittest.main()
