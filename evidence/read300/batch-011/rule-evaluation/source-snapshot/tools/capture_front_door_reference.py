"""Capture model-free Gorgon outputs to a NEW file for compatibility checks.

Run in a separate process. Imports the supplied trusted Gorgon checkout with
isolated storage and blocked socket connections. Never overwrite earlier captures.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

BOUNDARY_CASES = (
    "if alpha is stopped launch it",
    "when alpha stops restart the db vm",
    "when did you stop the vm",
    "how many machines carry the fleet label",
    "make sure exactly 3 vms carry the prod label",
    "restart the web vm snapshot the db vm",
    "don't stop the web vm stop the db vm",
    "I cannot start the vm restart the db vm",
    "it is not running restart the vm",
    "anything is possible with a vm restart the db vm",
    "create 3 vms named after musicians",
    "tell me if the vm is stopped",
    "stop the vm only if it is running",
    "stop the vm anyway restart the db vm",
    "if the vm is stopped then restart it",
    'say "if alpha stops restart it"',
    "um, if the report is approved send it",
    "please stop the vm",
    "stop the vm and then restart the db vm",
    "do-not-stop-the-vms",
    "stop the vm at 9pm",
    "no wati stop the vm",
)


def capture(root: Path, boundaries: bool) -> dict:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root / "files"))
    from orchestrator.languages.english.seam import front_door, scan
    from orchestrator.languages.english import codex
    from planner.formula.legal import Board

    board = Board()
    profile = {
        "nouns": sorted(scan._index(board)),
        "operations": sorted(scan._operation_words(board)),
        "statuses": sorted(front_door._statuses(board)),
        "protected_words": ["vm's", "vms"],
        "dual_verbs": sorted(codex.DUAL_CLASS_VERBS),
        "non_verbs": sorted(scan.NON_VERB_SEGMENTS),
        "known_names": [],
    }
    corpus_path = root / "files/tests/test_front_door_properties.py"
    corpus = (
        [("boundary", text) for text in BOUNDARY_CASES]
        if boundaries
        else runpy.run_path(str(corpus_path))["_corpus"]()
    )
    cases = []
    for family, text in corpus:
        result = front_door.read(text, board=board)
        cases.append(
            {
                "family": family,
                "request": text,
                "text": result.text,
                "back": result.back,
                "notices": result.notices,
            }
        )
    return {
        "purpose": "Gorgon compatibility characterization, not independently reviewed semantic gold",
        "corpus": "explicit helper-boundary cases"
        if boundaries
        else "seeded Gorgon property-test corpus",
        "corpus_source_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "profile": profile,
        "cases": cases,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gorgon", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--boundaries", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="kobra-reference-") as home:
        os.environ["GORGON_HOME"] = home
        with (
            patch(
                "socket.socket.connect", side_effect=RuntimeError("Network disabled")
            ),
            patch(
                "socket.create_connection", side_effect=RuntimeError("Network disabled")
            ),
        ):
            result = capture(args.gorgon.resolve(), args.boundaries)
        with args.output.open("x") as output:
            json.dump(result, output, indent=2, ensure_ascii=False)
            output.write("\n")
        print(f"Captured {len(result['cases'])} source cases")
