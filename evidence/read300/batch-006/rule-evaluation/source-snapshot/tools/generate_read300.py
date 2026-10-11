"""Generate fresh batches through Serpent with independent pre-reader context accounting."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unicodedata

from serpent import __version__
from serpent.context_requirements import assess_case, context_report, matches_policy
from serpent.planner import Options, build_pool, select
from serpent.validate import validate_case
from serpent_slots import project

ROOT = Path(__file__).resolve().parents[1]


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def dump(path, data):
    with path.open('x') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def known_inputs():
    known = set()
    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get('text'), str):
                known.add(normalized(value['text']))
            if isinstance(value.get('source'), str):
                known.add(normalized(value['source']))
            if isinstance(value.get('sentence'), str):
                known.add(normalized(value['sentence']))
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)
    paths = list((ROOT/'tests/fixtures').rglob('*.json'))
    paths += list((ROOT/'evidence').rglob('*.json'))
    paths += list((ROOT/'benchmarks').rglob('*.json'))
    for path in paths:
        visit(json.loads(path.read_text()))
    for path in (ROOT/'evidence').rglob('*.jsonl'):
        for line in path.read_text().splitlines():
            if line.strip():
                visit(json.loads(line))
    # Include explicit examples in tests/tools, not only archived batch inputs.
    for folder in ('tests', 'tools'):
        for path in (ROOT/folder).rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    known.add(normalized(node.value))
    for line in ('Close the gate.', 'Never paint the door.', 'If Sam agrees, send Jo the parcel.', 'Rin says the motor stopped.'):
        known.add(normalized(line))
    return known


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--context-policy', choices=['account','self-contained','read-resolvable'], default='account')
    parser.add_argument('--max-ambiguity', type=float, default=1.0)
    args = parser.parse_args()
    if not 0 <= args.max_ambiguity <= 1:
        parser.error('--max-ambiguity must be between 0 and 1')
    protocol_path = ROOT/'benchmarks/read300/protocol.json'
    protocol = json.loads(protocol_path.read_text())
    seed = protocol['seed_base'] + args.batch
    options = Options(**protocol['options'])
    pool, pool_hash = build_pool(seed, options)
    known = known_inputs()
    eligible = tuple(item for item in pool if normalized(item.case.sentence) not in known)
    before_context_count = len(eligible)
    excluded = []
    kept = []
    for item in eligible:
        annotation = assess_case(item.case)
        allowed = matches_policy(annotation, args.context_policy, args.max_ambiguity)
        (kept if allowed else excluded).append(item if allowed else {'text':item.case.sentence,'context_requirements':annotation})
    eligible = tuple(kept)
    # Selection sees only generator factors, never READ output or candidate coverage.
    cases = select(eligible, protocol['batch_size'], seed, options)
    families = {item.case.sentence: item.family for item in eligible}
    output = ROOT/f'evidence/read300/batch-{args.batch:03d}'
    output.mkdir(exist_ok=False)
    references = []
    errors = []
    for case in cases:
        validate_case(case)
        row = {'id':case.id,'text':case.sentence,'group':families[case.sentence]}
        try:
            row['expected'] = project(case.to_dict())
        except Exception as exc:
            row['expected'] = None
            row['adapter_error'] = f'{type(exc).__name__}: {exc}'
            errors.append({'id':case.id,'error':row['adapter_error']})
        references.append(row)
    assert len({normalized(c.sentence) for c in cases}) == 300
    assert not {normalized(c.sentence) for c in cases} & known
    serpent_root = Path(__import__('serpent').__file__).resolve().parent
    dump(output/'generator-manifest.json', {
        'created_utc':datetime.now(timezone.utc).isoformat(), 'serpent_version':__version__,
        'seed':seed, 'protocol':protocol, 'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        'pool_sha256':pool_hash,'pool_count':len(pool),'eligible_count':len(eligible),'seen_count':len(known),
        'known_normalized_sha256':hashlib.sha256(json.dumps(sorted(known)).encode()).hexdigest(),
        'generator_source_hashes':{str(p.relative_to(serpent_root)):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in serpent_root.rglob('*') if p.suffix in ('.py','.json')},
        'by_group':dict(Counter(families[c.sentence] for c in cases)), 'adapter_errors':errors,
        'adapter_sha256':hashlib.sha256(Path(__file__).with_name('serpent_slots.py').read_bytes()).hexdigest(),
        'selection':'Serpent planner over normalized-unseen pool with declared pre-reader context policy; no performance filters',
        'context_policy':args.context_policy,'max_ambiguity':args.max_ambiguity,
        'before_context_filter_count':before_context_count,'context_excluded_count':len(excluded)})
    dump(output/'serpent-source-cases.json', {'cases':[c.to_dict() for c in cases]})
    dump(output/'frozen-reference.json', {'cases':references})
    dump(output/'context-requirements.json', context_report(cases))
    dump(output/'context-exclusions.json', excluded)
    dump(output/'inputs.json', [{'id':c.id,'text':c.sentence} for c in cases])
    print(json.dumps({'output':str(output),'cases':300,'adapter_errors':errors},indent=2))


if __name__ == '__main__':
    main()
