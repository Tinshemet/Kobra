"""Frozen Serpent 300-case evaluation, lossless captures and failure ledger."""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time

from kobra import ArrangingReader, ClientConfig, IdentityFrontDoor, LinguisticCandidates, Request, Services
from kobra.candidate_read import VERSION
from kobra.ollama import OllamaProvider
from evaluate_arrangement import ledger_valid
from evaluate_selection import score, dump

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True)
    parser.add_argument('--model', default='llama3.1:8b')
    parser.add_argument('--label', default='evaluation')
    args = parser.parse_args()
    batch = ROOT/f'evidence/read300/batch-{args.batch:03d}'
    output = batch/args.label
    output.mkdir(exist_ok=False)
    fixture_path = batch/'frozen-reference.json'
    cases = json.loads(fixture_path.read_text())['cases']
    inputs = json.loads((batch/'inputs.json').read_text())
    assert len(cases) == len(inputs) == 300
    assert inputs == [{'id':c['id'],'text':c['text']} for c in cases]
    extractor = LinguisticCandidates()
    reader = ArrangingReader(extractor)
    provider = OllamaProvider(model=args.model, timeout=180)
    services = Services(ClientConfig('read300', '1'), model=provider)
    paths = list((ROOT/'src/kobra').glob('*.py')) + list((ROOT/'tools').glob('*.py'))
    paths += [ROOT/'benchmarks/read300/protocol.json']
    hashes = {str(p.relative_to(ROOT)):digest(p) for p in paths}
    for path in paths:
        dest = output/'source-snapshot'/path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    parser_path = Path(extractor.nlp.path)
    parser_hashes = {str(p.relative_to(parser_path)):digest(p) for p in parser_path.rglob('*') if p.is_file()}
    manifest = {'started_utc':datetime.now(timezone.utc).isoformat(),'prompt_version':VERSION,
                'model':provider.identity(),'source_hashes':hashes,'parser_hashes':parser_hashes,
                'parser':extractor.identity,'fixture_sha256':digest(fixture_path),
                'generator_manifest_sha256':digest(batch/'generator-manifest.json'),
                'source_cases_sha256':digest(batch/'serpent-source-cases.json'),
                'batch':args.batch,'label':args.label,'cases':300,'no_retries':True,
                'gold_excluded_from_reader':True,'fixes':json.loads((ROOT/'benchmarks/read300/fixes.json').read_text())}
    dump(output/'manifest.json',manifest)
    rows = []
    started = time.monotonic()
    print(f"STARTED {manifest['started_utc']} batch={args.batch} model={args.model}", flush=True)
    with (output/'cases.jsonl').open('x') as capture, (output/'failures.jsonl').open('x') as failures:
        for case in cases:
            request = Request(case['text'])
            view = IdentityFrontDoor().normalize(request, services)
            provider.last_exchange = None
            start = time.monotonic()
            result = reader.read(view, request, services)
            predictions = [{'act':f.act,**{s:v if isinstance(v,str) else v.text for s,v in f.slots.items()}} for f in result.frames]
            scored = score(case['expected'] or [], predictions)
            if case['expected'] is None:
                scored['exact'] = False
                scored['adapter_error'] = case['adapter_error']
            coverage = []
            for i, frame in enumerate(case['expected'] or []):
                for slot, options in frame.items():
                    if slot == 'act' or options in (['NONE'],['MISSING'],['UNKNOWN']):
                        continue
                    available = {c.text for c in result.inventory.menus[slot].values()}
                    coverage.append({'frame':i,'slot':slot,'available':bool(available.intersection(options)), 'expected':options})
            record = {'id':case['id'],'text':case['text'],'group':case['group'],
                      'seconds':time.monotonic()-start,'result':asdict(result),'selected':predictions,
                      'score':scored,'source_retained':ledger_valid(result),'exchange':provider.last_exchange,
                      'candidate_coverage':coverage}
            capture.write(json.dumps(record,ensure_ascii=False)+'\n');capture.flush()
            if not scored['exact']:
                failure = {'batch':args.batch,'case_id':case['id'],'sentence':case['text'],'group':case['group'],
                           'expected':case['expected'],'predicted':predictions,'mismatches':scored['mismatches'],
                           'diagnostics':record['result']['diagnostics'],'candidate_misses':[c for c in coverage if not c['available']],
                           'status':'open','fix_ids':[],'verified_ticks':[],'adapter_error':case.get('adapter_error')}
                failures.write(json.dumps(failure,ensure_ascii=False)+'\n');failures.flush()
            rows.append(record)
            progress = {'batch':args.batch,'completed':len(rows),'total':300,
                        'exact':sum(r['score']['exact'] for r in rows),'retained':sum(r['source_retained'] for r in rows),
                        'elapsed_seconds':time.monotonic()-started,'updated_utc':datetime.now(timezone.utc).isoformat()}
            temp = output/'progress.tmp'
            temp.write_text(json.dumps(progress,indent=2));temp.replace(output/'progress.json')
            if len(rows) % 10 == 0:
                print(json.dumps(progress),flush=True)
    unchanged = all(digest(ROOT/p) == h for p,h in hashes.items())
    unchanged = unchanged and digest(fixture_path) == manifest['fixture_sha256']
    coverage = [c for r in rows for c in r['candidate_coverage']]
    summary = {'state':'complete','batch':args.batch,'cases':300,'exact_cases':sum(r['score']['exact'] for r in rows),
               'source_unchanged':unchanged,'source_retention_cases':sum(r['source_retained'] for r in rows),
               'source_characters':sum(len(r['text']) for r in rows),'seconds':time.monotonic()-started,
               'adapter_errors':sum(c['expected'] is None for c in cases),
               'candidate_coverage':{'covered':sum(c['available'] for c in coverage),'total':len(coverage)},
               'errors':dict(Counter(r['result']['status'] for r in rows)),
               **{k:sum(r['score'][k] for r in rows) for k in ('slots_correct','slots_total','required_preserved','required_total')},
               'by_group':{g:{'exact':sum(r['score']['exact'] for r in rows if r['group']==g),'cases':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})},
               'passing_threshold':285,'needs_offline_audit':True,
               'scope':'Bounded 11-slot projection, not full graph accuracy or meaning preservation'}
    dump(output/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if unchanged and summary['source_retention_cases']==300 else 2


if __name__ == '__main__':
    raise SystemExit(main())
