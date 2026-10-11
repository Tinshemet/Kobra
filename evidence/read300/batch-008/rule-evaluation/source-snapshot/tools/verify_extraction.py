"""Check extracted syntax against the recorded Gorgon working-tree symbols."""

import argparse
import ast
import hashlib
import json
from pathlib import Path


def symbols(tree):
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        found[name.id] = node
    return found


def verify(root, gorgon):
    provenance = json.loads((root / "evidence/provenance.json").read_text())
    count = 0
    for record in provenance["extracted_symbols"]:
        original = (gorgon / "files" / record["source"]).read_text()
        target = (
            "clock_vocabulary.py"
            if record["source"].endswith("/codex.py")
            else "clock.py"
        )
        extracted = (root / "src/kobra" / target).read_text()
        old = symbols(ast.parse(original))[record["symbols"][0]]
        new = symbols(ast.parse(extracted))[record["symbols"][0]]
        digest = hashlib.sha256(
            ast.get_source_segment(original, old).encode()
        ).hexdigest()
        if digest != record["sha256"]:
            raise ValueError(f"Source drift: {record['symbols']}")
        if ast.dump(old) != ast.dump(new):
            raise ValueError(f"Extraction changed syntax: {record['symbols']}")
        count += 1
    return {"checked_definitions": count, "syntax_matches": count, "failures": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gorgon", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(verify(Path(__file__).resolve().parents[1], args.gorgon), indent=2)
    )
