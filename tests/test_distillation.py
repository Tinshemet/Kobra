"""Structural checks only; a valid evidence pointer does not prove a claim."""

import json
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from kobra.distillation import Distillation, Point, PointLink, Source, SourceSpan


def load_case(case):
    return Distillation(
        sources=tuple(Source(**source) for source in case["sources"]),
        points=tuple(
            Point(
                id=point["id"],
                sentence=point["sentence"],
                evidence=tuple(SourceSpan(**span) for span in point["evidence"]),
                links=tuple(PointLink(**link) for link in point["links"]),
                uncertainty=tuple(point["uncertainty"]),
            )
            for point in case["points"]
        ),
    )


class DistillationTests(unittest.TestCase):
    def setUp(self):
        self.source = Source("request", "Ask Zoë.")
        self.point = Point(
            "p1", "The user requests asking Zoë.", (SourceSpan("request", 0, 8),)
        )

    def test_draft_examples_have_valid_references(self):
        data = json.loads(
            (Path(__file__).parent / "fixtures/distillation-draft-1.json").read_text()
        )
        self.assertEqual(data["status"], "draft_pending_user_review")
        for case in data["cases"]:
            with self.subTest(case=case["id"]):
                output = load_case(case)
                self.assertEqual(output.contract_version, data["contract_version"])

    def test_missing_sources_and_out_of_bounds_evidence_rejected(self):
        for span in (SourceSpan("missing", 0, 1), SourceSpan("request", 0, 9)):
            with self.subTest(span=span), self.assertRaises(ValueError):
                Distillation((self.source,), (replace(self.point, evidence=(span,)),))

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            Distillation((self.source, self.source), (self.point,))
        with self.assertRaises(ValueError):
            Distillation((self.source,), (self.point, self.point))

    def test_dangling_and_self_links_rejected(self):
        for target in ("missing", "p1"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                Distillation(
                    (self.source,),
                    (replace(self.point, links=(PointLink(target, "qualifies"),)),),
                )

    def test_invalid_offsets_rejected(self):
        for start, end in ((-1, 2), (2, 2), (3, 2), (True, 2), (0, 1.5)):
            with (
                self.subTest(start=start, end=end),
                self.assertRaises((TypeError, ValueError)),
            ):
                SourceSpan("request", start, end)

    def test_points_require_evidence(self):
        with self.assertRaises(ValueError):
            replace(self.point, evidence=())

    def test_nested_collections_are_immutable(self):
        with self.assertRaises(TypeError):
            Distillation([self.source], (self.point,))
        with self.assertRaises(TypeError):
            replace(self.point, uncertainty=["unknown"])
        with self.assertRaises(FrozenInstanceError):
            self.point.sentence = "Changed"

    def test_multiple_sources_and_discontinuous_evidence(self):
        other = Source("document", "Zoë is the editor.")
        point = replace(
            self.point,
            evidence=(SourceSpan("request", 0, 3), SourceSpan("document", 0, 3)),
        )
        Distillation((self.source, other), (point,))

    def test_empty_input_can_have_no_points(self):
        Distillation((Source("request", ""),), ())

    def test_unknown_contract_version_rejected(self):
        with self.assertRaises(ValueError):
            Distillation((self.source,), (self.point,), "future")

    def test_structure_does_not_establish_semantic_support(self):
        # Intentionally unsupported: validation must not be advertised as a truth check.
        wrong = replace(self.point, sentence="The user requests purchasing a car.")
        output = Distillation((self.source,), (wrong,))
        self.assertEqual(output.points[0], wrong)


if __name__ == "__main__":
    unittest.main()
