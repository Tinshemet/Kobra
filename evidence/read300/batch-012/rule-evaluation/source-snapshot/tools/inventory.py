"""Record static import sites without importing or executing Gorgon.

Includes function-local imports. Dynamic imports and runtime resources require
manual follow-up; this is an inventory, not a complete dependency closure.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path


def inventory(root):
    files = set((root / "files/orchestrator/languages").rglob("*.py"))
    files.update(
        root / name
        for name in (
            "files/orchestrator/door.py",
            "files/orchestrator/executor_client.py",
            "files/engines/orchestrator.py",
            "files/engines/executor.py",
        )
    )
    records = []
    for path in sorted(files):
        raw = path.read_bytes()
        tree = ast.parse(raw, filename=str(path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(
                    {
                        "line": node.lineno,
                        "module": ("." * node.level + (node.module or ""))
                        if isinstance(node, ast.ImportFrom)
                        else None,
                        "names": [alias.name for alias in node.names],
                    }
                )
        records.append(
            {
                "file": str(path.relative_to(root)),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "imports": sorted(imports, key=lambda item: item["line"]),
            }
        )
    return {
        "scope": "static import sites only; working-tree snapshot",
        "files": records,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gorgon", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inventory(args.gorgon), indent=2) + "\n")
