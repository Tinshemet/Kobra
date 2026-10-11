"""Frozen 50-case pilot: native tool selections, raw captures, bounded slot scoring."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import statistics
import time

from kobra import ClientConfig, IdentityFrontDoor, Request, SelectingReader, Services
from kobra.ollama import OllamaProvider
from kobra.selection_read import SLOTS, VERSION, candidates_for

FIELDS = ('act', *SLOTS)


def score(expected, predicted, residual=False):
    """Exact predeclared slot alternatives, no model judge or post-hoc gold edits."""
    n = max(len(expected), len(predicted))
    required = sum(v != ['NONE'] for frame in expected for v in frame.values())
    best = None
    for order in itertools.permutations(range(n)):
        correct = preserved = 0
        mismatches = []
        for i in range(n):
            gold = expected[i] if i < len(expected) else None
            pred = predicted[order[i]] if order[i] < len(predicted) else None
            for field in FIELDS:
                allowed = gold[field] if gold else []
                value = pred.get(field) if pred else None
                match = gold is not None and pred is not None and value in allowed
                correct += match
                preserved += match and allowed != ['NONE']
                if not match:
                    mismatches.append({'frame': i, 'slot': field, 'expected': allowed, 'selected': value})
        candidate = (correct, preserved, mismatches)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    correct, preserved, mismatches = best or (0, 0, [])
    return {'exact': not mismatches and not residual and len(expected) == len(predicted),
            'slots_correct': correct, 'slots_total': n * len(FIELDS),
            'required_preserved': preserved, 'required_total': required,
            'mismatches': mismatches, 'unrepresented': residual}


def dump(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=Path('tests/fixtures/selection-50.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', default='llama3.1:8b')
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    cases = fixture['cases']
    if len(cases) != 50 or len({c['id'] for c in cases}) != 50:
        raise ValueError('Expected 50 uniquely identified cases')
    args.output.mkdir(parents=True, exist_ok=False)
    provider = OllamaProvider(model=args.model, timeout=120)
    services = Services(ClientConfig('selection-pilot', '1'), model=provider)
    front = IdentityFrontDoor()
    root = Path(__file__).resolve().parents[1]
    source_paths = list((root/'src/kobra').glob('*.py')) + [Path(__file__).resolve()]
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    dump(args.output/'manifest.json', {
        'started_utc': datetime.now(timezone.utc).isoformat(), 'prompt_version': VERSION,
        'model': provider.identity(), 'fixture_sha256': hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
        'source_hashes': hashes, 'cases': len(cases), 'front_door': 'identity',
        'scorer': 'selection-slot-contract-1', 'annotation': fixture['annotation'],
        'no_retries': True, 'gold_excluded_from_model_input': True,
        'development_inputs': ['Close the gate.', 'Never paint the door.']})
    dump(args.output/'frozen-reference.json', fixture)
    dump(args.output/'inputs.json', [{'id':c['id'],'text':c['text']} for c in cases])
    records = []
    covered = possible = 0
    with (args.output/'cases.jsonl').open('x') as capture:
        for case in cases:
            request = Request(case['text'])
            view = front.normalize(request, services)
            candidates = candidates_for(view)
            available = {c.text for c in candidates}
            coverage = []
            for i, frame in enumerate(case['expected']):
                for field, options in frame.items():
                    if field == 'act' or options == ['NONE']:
                        continue
                    possible += 1
                    present = bool(available.intersection(options))
                    covered += present
                    coverage.append({'frame':i, 'slot':field, 'available':present})
            start = time.monotonic()
            provider.last_exchange = None
            record = {'id':case['id'], 'group':case['group'], 'text':case['text'],
                      'candidate_coverage':coverage, 'candidate_count':len(candidates)}
            selected = []
            residual = False
            try:
                result = SelectingReader().read(view, request, services)
                selected = [{'act':f.act, **{s:v if isinstance(v,str) else v.text for s,v in f.slots.items()}}
                            for f in result.frames]
                residual = bool(result.unrepresented)
                record.update(status='accepted', result=asdict(result), selected=selected)
            except Exception as exc:
                record.update(status='error', error=f'{type(exc).__name__}: {exc}')
            record.update(seconds=time.monotonic()-start, exchange=provider.last_exchange,
                          score=score(case['expected'], selected, residual))
            capture.write(json.dumps(record, ensure_ascii=False)+'\n')
            capture.flush()
            records.append(record)
            print(f"{len(records)}/50 {case['id']} {record['status']} exact={record['score']['exact']}",flush=True)
    unchanged = all(hashlib.sha256((root/p).read_bytes()).hexdigest() == h for p,h in hashes.items())
    totals = {key:sum(r['score'][key] for r in records) for key in
              ('slots_correct','slots_total','required_preserved','required_total')}
    summary = {
        'state':'complete', 'source_unchanged':unchanged, 'cases':50,
        'accepted':sum(r['status']=='accepted' for r in records),
        'errors':sum(r['status']=='error' for r in records),
        'exact_cases':sum(r['score']['exact'] for r in records), **totals,
        'candidate_coverage':{'covered':covered,'total':possible},
        'median_seconds':statistics.median(r['seconds'] for r in records),
        'total_seconds':sum(r['seconds'] for r in records),
        'by_group':{g:{'exact':sum(r['score']['exact'] for r in records if r['group']==g),
                       'cases':sum(r['group']==g for r in records)} for g in sorted({r['group'] for r in records})},
        'limitation':'Agent-authored fixed references, not independent gold; bounded slot accuracy and required-slot retention, not full READ meaning preservation.',
    }
    dump(args.output/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if unchanged else 2


if __name__=='__main__':
    raise SystemExit(main())
