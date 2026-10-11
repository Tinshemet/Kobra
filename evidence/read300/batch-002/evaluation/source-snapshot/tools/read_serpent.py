"""Capture READ on student-only Serpent exams. No graph-accuracy claim."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from kobra import (
    ClientConfig,
    DomainVocabulary,
    DistillingReader,
    EnglishFrontDoor,
    Pipeline,
    Request,
    Services,
    StructuredReader,
)
from kobra.mocks import MockResolver, MockRouter
from kobra.ollama import OllamaProvider


def write(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def load_inputs(path, limit):
    exam = json.loads(path.read_text())
    if exam.get("format") != "serpent-exam" or exam.get("version") != "1.0":
        raise ValueError("Expected a Serpent student exam, not a gold pack")
    rows = exam["inputs"]
    seen = set()
    for row in rows:
        if set(row) != {"id", "sentence"}:
            raise ValueError(
                "Only standalone sentence exams are supported; no context or gold"
            )
        if not isinstance(row["id"], str) or not isinstance(row["sentence"], str):
            raise ValueError("Exam IDs and sentences must be strings")
        if row["id"] in seen:
            raise ValueError("Duplicate exam ID")
        seen.add(row["id"])
    return exam, rows[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exam", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory only")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--reader", choices=("distillation", "structured", "structured-hints"),
                        default="distillation")
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    exam, rows = load_inputs(args.exam, args.limit)
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[1]
    manifest = {
        "format": "kobra-read-pilot-1",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "model_requested": args.model,
        "reader": args.reader,
        "source_sha256": exam["source_sha256"],
        "exam_sha256": hashlib.sha256(args.exam.read_bytes()).hexdigest(),
        "selected_ids": [r["id"] for r in rows],
        "vocabulary": "empty application-independent profile",
        "source_files": {
            str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((source / "src/kobra").glob("*.py"))
        },
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "semantic_accuracy": None,
        "regression_delta": None,
        "limitation": "Structural acceptance is not semantic accuracy; no comparable baseline.",
    }
    write(args.output / "manifest.json", manifest)
    write(args.output / "inputs.json", rows)
    provider = OllamaProvider(model=args.model, url=args.url)
    try:
        identity = provider.identity()
    except Exception as exc:
        write(
            args.output / "summary.json",
            {
                "state": "blocked",
                "planned": len(rows),
                "attempted": 0,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        print(f"Blocked before inference: {exc}", flush=True)
        return 2
    write(args.output / "model.json", identity)
    pipeline = Pipeline(
        EnglishFrontDoor(DomainVocabulary()),
        (DistillingReader() if args.reader == "distillation" else
         StructuredReader(use_hints=args.reader == "structured-hints")),
        MockResolver(),
        MockRouter(),
        Services(ClientConfig("serpent-read-pilot", "1"), model=provider),
    )
    accepted = 0
    errors = 0
    with (args.output / "cases.jsonl").open("x") as capture:
        for index, row in enumerate(rows):
            start = time.monotonic()
            provider.last_exchange = None
            record = dict(row)
            try:
                result = pipeline.interpret(Request(row["sentence"]))
                record.update(
                    status="structurally_accepted", interpretation=asdict(result)
                )
                accepted += 1
            except Exception as exc:
                record.update(status="error", error=f"{type(exc).__name__}: {exc}")
                errors += 1
            record.update(
                seconds=time.monotonic() - start,
                exchange=provider.last_exchange,
                semantic_review="pending",
            )
            capture.write(json.dumps(record, ensure_ascii=False) + "\n")
            capture.flush()
            print(
                f"{index + 1}/{len(rows)} {row['id']}: {record['status']}", flush=True
            )
    write(
        args.output / "summary.json",
        {
            "state": "capture_complete",
            "planned": len(rows),
            "attempted": len(rows),
            "structurally_accepted": accepted,
            "errors": errors,
            "semantic_review": "pending",
            "semantic_accuracy": None,
            "regression_delta": None,
        },
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
