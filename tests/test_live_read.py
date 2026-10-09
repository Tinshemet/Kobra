import io
import json
import unittest
from unittest.mock import patch

from kobra import (
    ClientConfig,
    DomainVocabulary,
    DistillingReader,
    EnglishFrontDoor,
    Pipeline,
    Request,
    Services,
    RouteStatus,
)
from kobra.mocks import MockResolver, MockRouter
from kobra.ollama import OllamaProvider


class LiveReadBoundaryTests(unittest.TestCase):
    def reply(self, content, reason="stop"):
        return io.BytesIO(
            json.dumps(
                {
                    "done": True,
                    "done_reason": reason,
                    "message": {"content": json.dumps(content)},
                }
            ).encode()
        )

    def test_mock_pipeline_and_transport_preserve_read(self):
        provider = OllamaProvider()
        proposal = {
            "points": [
                {
                    "sentence": "Do not send the report.",
                    "evidence": [{"quote": "Do not send the report.", "occurrence": 0}],
                    "links": [],
                    "uncertainty": [],
                }
            ]
        }
        pipeline = Pipeline(
            EnglishFrontDoor(DomainVocabulary()),
            DistillingReader(),
            MockResolver(),
            MockRouter(),
            Services(ClientConfig("test", "1"), model=provider),
        )
        with patch("kobra.ollama.urlopen", return_value=self.reply(proposal)) as call:
            result = pipeline.interpret(Request("Do not send the report."))
        self.assertIs(result.reading, result.resolved)
        self.assertEqual(result.decision.status, RouteStatus.UNSUPPORTED)
        self.assertIsNone(result.decision.capability_id)
        self.assertEqual(result.decision.diagnostics[0].code, "route.mock")
        payload = json.loads(call.call_args.args[0].data)
        self.assertEqual(payload["model"], "llama3.1:8b")
        self.assertEqual(payload["messages"][1]["content"], result.view.text)
        self.assertNotIn("tools", payload)
        self.assertFalse(payload["stream"])

    def test_truncation_is_rejected_even_if_json_valid(self):
        provider = OllamaProvider()
        with patch(
            "kobra.ollama.urlopen", return_value=self.reply({"points": []}, "length")
        ):
            with self.assertRaisesRegex(ValueError, "finish normally"):
                provider.complete(prompt="p", text="t", schema={})
        self.assertIn("response", provider.last_exchange)

    def test_transport_failure_is_not_retried(self):
        provider = OllamaProvider()
        with patch("kobra.ollama.urlopen", side_effect=TimeoutError) as call:
            with self.assertRaises(TimeoutError):
                provider.complete(prompt="p", text="t", schema={})
        self.assertEqual(call.call_count, 1)

    def test_bad_evidence_stops_before_resolve(self):
        provider = OllamaProvider()
        proposal = {
            "points": [
                {
                    "sentence": "Invented",
                    "evidence": [{"quote": "absent", "occurrence": 0}],
                    "links": [],
                    "uncertainty": [],
                }
            ]
        }
        resolver = MockResolver()
        pipeline = Pipeline(
            EnglishFrontDoor(DomainVocabulary()),
            DistillingReader(),
            resolver,
            MockRouter(),
            Services(ClientConfig("test", "1"), model=provider),
        )
        with (
            patch("kobra.ollama.urlopen", return_value=self.reply(proposal)),
            patch.object(resolver, "resolve") as resolve,
        ):
            with self.assertRaises(ValueError):
                pipeline.interpret(Request("Do not send the report."))
        resolve.assert_not_called()

    def test_runner_captures_mocked_transport_end_to_end(self):
        import importlib.util
        from pathlib import Path
        import tempfile

        spec = importlib.util.spec_from_file_location(
            "pilot", Path(__file__).parents[1] / "tools/read_serpent.py"
        )
        pilot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pilot)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exam = root / "exam.json"
            exam.write_text(
                json.dumps(
                    {
                        "format": "serpent-exam",
                        "version": "1.0",
                        "source_sha256": "test-only",
                        "inputs": [{"id": "a", "sentence": "Hello."}],
                    }
                )
            )
            with (
                patch(
                    "sys.argv",
                    ["pilot", "--exam", str(exam), "--output", str(root / "run")],
                ),
                patch.object(
                    OllamaProvider, "identity", return_value={"test_only": True}
                ),
                patch("kobra.ollama.urlopen", return_value=self.reply({"points": []})),
            ):
                self.assertEqual(pilot.main(), 0)
            summary = json.loads((root / "run/summary.json").read_text())
            self.assertEqual(summary["structurally_accepted"], 1)
            self.assertIsNone(summary["semantic_accuracy"])
            records = (root / "run/cases.jsonl").read_text().splitlines()
            self.assertEqual(len(records), 1)
            self.assertEqual(
                json.loads(records[0])["interpretation"]["decision"]["status"],
                "unsupported",
            )
