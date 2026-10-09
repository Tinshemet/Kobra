import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from kobra import (
    ClientConfig,
    Diagnostic,
    DomainVocabulary,
    EnglishFrontDoor,
    IdentityFrontDoor,
    Pipeline,
    Request,
    Services,
    TextView,
)
from kobra.read import DistillingReader, ReadContractError, ReadLimits, bind_proposal
from kobra._read_surface import anchors_in, reasons_in


def point(sentence, quote, occurrence=0, links=None, uncertainty=None):
    return {
        "sentence": sentence,
        "evidence": [{"quote": quote, "occurrence": occurrence}],
        "links": links or [],
        "uncertainty": uncertainty or [],
    }


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.model = Mock()
        self.services = Services(ClientConfig("read-test", "1"), model=self.model)
        self.reader = DistillingReader()

    def read(self, text, points, front=None):
        self.model.complete.return_value = {"points": points}
        request = Request(text)
        view = (front or IdentityFrontDoor()).normalize(request, self.services)
        return self.reader.read(view, request, self.services)

    def test_proposals_from_twelve_draft_examples_bind_without_changing_meaning(self):
        # Hand-authored provider proposals test binding, not model accuracy.
        fixture = json.loads(
            (Path(__file__).parent / "fixtures/distillation-draft-1.json").read_text()
        )
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                text = case["sources"][0]["text"]
                proposals = []
                for p in case["points"]:
                    evidence = []
                    for span in p["evidence"]:
                        quote = text[span["start"] : span["end"]]
                        occurrence = sum(
                            text.startswith(quote, i) for i in range(span["start"])
                        )
                        evidence.append({"quote": quote, "occurrence": occurrence})
                    proposals.append(
                        {
                            "sentence": p["sentence"],
                            "evidence": evidence,
                            "links": [
                                {
                                    "target": int(link["target_id"][1:]) - 1,
                                    "relationship": link["relationship"],
                                }
                                for link in p["links"]
                            ],
                            "uncertainty": p["uncertainty"],
                        }
                    )
                output = self.read(text, proposals)
                for actual, expected in zip(output.distillation.points, case["points"]):
                    self.assertEqual(actual.sentence, expected["sentence"])
                    self.assertEqual(actual.uncertainty, tuple(expected["uncertainty"]))
                    self.assertEqual(
                        [(s.start, s.end) for s in actual.evidence],
                        [(s["start"], s["end"]) for s in expected["evidence"]],
                    )
                self.assertEqual(output.distillation.sources[0].text, text)
                self.assertEqual(output.semantic_review, "not_evaluated")

    def test_normalized_proposal_maps_to_original(self):
        front = EnglishFrontDoor(
            DomainVocabulary(
                nouns=frozenset({"report"}), operations=frozenset({"send"})
            )
        )
        original = "um, send\u00a0the report to Zoë"
        output = self.read(
            original,
            [
                point(
                    "The user requests sending the report to Zoë.",
                    "send the report to Zoë",
                )
            ],
            front,
        )
        span = output.distillation.points[0].evidence[0]
        self.assertEqual(original[span.start : span.end], "send\u00a0the report to Zoë")
        self.assertEqual(
            self.model.complete.call_args.kwargs["text"], "send the report to Zoë"
        )
        self.assertEqual(output.view.original, original)
        self.assertEqual(len(output.diagnostics), 2)

    def test_repeated_quote_uses_explicit_occurrence(self):
        output = self.read(
            "Ask Jo, then ask Jo.", [point("The user names Jo a second time.", "Jo", 1)]
        )
        self.assertEqual(output.distillation.points[0].evidence[0].start, 17)

    def test_missing_or_wrong_occurrence_fails(self):
        for quote, occurrence in (("invented", 0), ("Jo", 2), ("Jo", -1), ("Jo", True)):
            with (
                self.subTest(quote=quote, occurrence=occurrence),
                self.assertRaises(ReadContractError),
            ):
                self.read(
                    "Ask Jo.",
                    [point("The user requests asking Jo.", quote, occurrence)],
                )

    def test_model_cannot_replace_sources_or_ids(self):
        request = Request("Ask Jo.")
        view = IdentityFrontDoor().normalize(request, self.services)
        for proposal in (
            {"sources": [], "points": []},
            {"points": [{**point("Ask Jo.", "Ask Jo."), "id": "admin"}]},
        ):
            with self.subTest(proposal=proposal), self.assertRaises(ReadContractError):
                bind_proposal(proposal, view, request)

    def test_bad_structure_is_rejected_atomically(self):
        good = point("The user requests asking Jo.", "Ask Jo.")
        variants = []
        for field, bad in (
            ("sentence", " "),
            ("evidence", []),
            ("links", "p1"),
            ("uncertainty", [4]),
        ):
            candidate = copy.deepcopy(good)
            candidate[field] = bad
            variants.append(candidate)
        for candidate in variants:
            with (
                self.subTest(candidate=candidate),
                self.assertRaises(ReadContractError),
            ):
                self.read("Ask Jo.", [good, candidate])

    def test_invalid_links_fail(self):
        for target in (0, 1, True, "p1"):
            with self.subTest(target=target), self.assertRaises(ReadContractError):
                self.read(
                    "Ask Jo.",
                    [
                        point(
                            "Ask Jo.",
                            "Ask Jo.",
                            links=[{"target": target, "relationship": "qualifies"}],
                        )
                    ],
                )

    def test_uncited_constraint_is_visible(self):
        output = self.read(
            "Compare the reports. Do not send them.",
            [point("The user requests comparing the reports.", "Compare the reports.")],
        )
        uncited = [
            output.view.text[s.normalized_start : s.normalized_end]
            for s in output.uncovered
        ]
        self.assertEqual(uncited, ["Do", "not", "send", "them."])
        self.assertIn("read.uncited-text", [d.code for d in output.diagnostics])

    def test_citing_everything_does_not_prove_entailment(self):
        output = self.read(
            "Do not buy anything.",
            [point("The user requests buying a car.", "Do not buy anything.")],
        )
        self.assertEqual(output.uncovered, ())
        self.assertEqual(output.semantic_review, "not_evaluated")

    def test_empty_output_is_explicit_and_empty_input_skips_model(self):
        output = self.read("Ask Jo.", [])
        self.assertIn("read.empty-proposal", [d.code for d in output.diagnostics])
        self.model.reset_mock()
        self.read("  ", [])
        self.model.complete.assert_not_called()

    def test_wrong_original_rejected_before_call(self):
        with self.assertRaises(ReadContractError):
            self.reader.read(TextView("x", "x", (0, 1)), Request("y"), self.services)
        self.model.complete.assert_not_called()

    def test_provider_failure_is_not_a_successful_empty_read(self):
        self.model.complete.side_effect = TimeoutError("provider timed out")
        with self.assertRaises(TimeoutError):
            self.read("Ask Jo.", [])
        self.model.complete.assert_called_once()

    def test_explicit_provider_required(self):
        request = Request("Ask Jo.")
        with self.assertRaises(ReadContractError):
            self.reader.read(
                IdentityFrontDoor().normalize(request, self.services),
                request,
                Services(ClientConfig("no-model", "1")),
            )

    def test_input_and_output_limits(self):
        reader = DistillingReader(ReadLimits(max_input_chars=3))
        request = Request("Ask Jo.")
        with self.assertRaises(ReadContractError):
            reader.read(
                IdentityFrontDoor().normalize(request, self.services),
                request,
                self.services,
            )
        self.model.complete.assert_not_called()
        self.reader = DistillingReader(ReadLimits(max_points=1))
        with self.assertRaises(ReadContractError):
            self.read("Ask Jo.", [point("Ask Jo.", "Ask Jo.")] * 2)

    def test_inserted_text_cannot_be_sole_evidence(self):
        view = TextView("ab", "axb", (0, 1, 1, 2), (Diagnostic("edit", "inserted x"),))
        with self.assertRaises(ReadContractError):
            bind_proposal({"points": [point("x", "x")]}, view, Request("ab"))

    def test_failure_stops_pipeline_before_resolve(self):
        self.model.complete.return_value = {"points": [point("invented", "invented")]}
        resolver, router = Mock(), Mock()
        pipeline = Pipeline(
            IdentityFrontDoor(), self.reader, resolver, router, self.services
        )
        with self.assertRaises(ReadContractError):
            pipeline.interpret(Request("Ask Jo."))
        resolver.resolve.assert_not_called()
        router.route.assert_not_called()

    def test_preserved_read_helpers_match_source_cases(self):
        fixture = json.loads(
            (
                Path(__file__).parent / "fixtures/read-surface-characterization.json"
            ).read_text()
        )
        nouns = frozenset(fixture["nouns"])
        for case in fixture["cases"]:
            with self.subTest(text=case["text"]):
                self.assertEqual(anchors_in(case["text"], nouns), case["anchors"])
                self.assertEqual(
                    [reason._asdict() for reason in reasons_in(case["text"], nouns)],
                    case["reasons"],
                )

    def test_existing_linguistic_observations_reach_provider_and_result(self):
        self.reader = DistillingReader(
            vocabulary=DomainVocabulary(nouns=frozenset({"report"}))
        )
        text = "Send the report because it is ready."
        result = self.read(
            text,
            [point("The user requests sending the report because it is ready.", text)],
        )
        self.assertEqual(result.observations.noun_anchors, ("report",))
        self.assertEqual(result.observations.reasons[0].family, "cause")
        self.assertEqual(result.observations.reasons[0].span, "it is ready")
        self.assertIn(
            '"noun_anchors": ["report"]', self.model.complete.call_args.kwargs["prompt"]
        )


if __name__ == "__main__":
    unittest.main()
