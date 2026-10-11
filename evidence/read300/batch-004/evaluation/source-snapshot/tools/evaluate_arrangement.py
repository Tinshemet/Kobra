"""Same 50 fixed references; narrowed linguistic candidates and lossless ledger."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import time

from kobra import ArrangingReader, ClientConfig, IdentityFrontDoor, LinguisticCandidates, Request, Services
from kobra.candidate_read import VERSION
from kobra.ollama import OllamaProvider
from evaluate_selection import score, dump


def ledger_valid(result):
    cursor=0
    for part in result.source_ledger:
        if part.start!=cursor or part.end<=part.start or part.text!=result.request.text[part.start:part.end]:
            return False
        cursor=part.end
    return cursor==len(result.request.text) and ''.join(p.text for p in result.source_ledger)==result.request.text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=Path('tests/fixtures/selection-50.json'))
    parser.add_argument('--baseline',type=Path,default=Path('evidence/selection-50-20261009'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model',default='llama3.1:8b')
    args=parser.parse_args()
    fixture=json.loads(args.fixture.read_text());cases=fixture['cases']
    if len(cases)!=50 or len({c['id'] for c in cases})!=50:
        raise ValueError('Expected exactly the 50 uniquely identified reference cases')
    prior_manifest=json.loads((args.baseline/'manifest.json').read_text())
    fixture_hash=hashlib.sha256(args.fixture.read_bytes()).hexdigest()
    if fixture_hash!=prior_manifest['fixture_sha256']:
        raise ValueError('Fixture differs from previous 50-case run')
    args.output.mkdir(parents=True,exist_ok=False)
    extractor=LinguisticCandidates();reader=ArrangingReader(extractor)
    provider=OllamaProvider(model=args.model,timeout=120)
    services=Services(ClientConfig('arrangement-pilot','1'),model=provider)
    import spacy
    root=Path(__file__).resolve().parents[1]
    paths=list((root/'src/kobra').glob('*.py'))+[Path(__file__).resolve(),root/'tools/evaluate_selection.py']
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for p in paths:
        target=args.output/'source-snapshot'/p.relative_to(root)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    parser_path=Path(extractor.nlp.path)
    parser_hashes={str(p.relative_to(parser_path)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in parser_path.rglob('*') if p.is_file()}
    identity=provider.identity()
    dump(args.output/'manifest.json',{
        'started_utc':datetime.now(timezone.utc).isoformat(),'prompt_version':VERSION,
        'model':identity,'same_model_digest':identity['model']['digest']==prior_manifest['model']['model']['digest'],
        'fixture_sha256':fixture_hash,'source_hashes':hashes,'parser':extractor.identity,
        'spacy_version':spacy.__version__,'parser_hashes':parser_hashes,'cases':50,
        'scorer':'selection-slot-contract-1','annotation':fixture['annotation'],
        'front_door':'identity','baseline':str(args.baseline),'split':'reused development comparison, not held-out',
        'no_retries':True,'gold_excluded_from_model_input':True,
        'residual_comparison':'score identical frame slots; automatic source leftovers are not a semantic error test',
        'development_inputs':['Close the gate.','Never paint the door.','If Sam agrees, send Jo the parcel.','Rin says the motor stopped.']})
    dump(args.output/'frozen-reference.json',fixture)
    dump(args.output/'inputs.json',[{'id':c['id'],'text':c['text']} for c in cases])
    records=[];covered=possible=0
    with (args.output/'cases.jsonl').open('x') as capture:
        for case in cases:
            request=Request(case['text']);view=IdentityFrontDoor().normalize(request,services)
            start=time.monotonic();provider.last_exchange=None
            result=reader.read(view,request,services)
            elapsed=time.monotonic()-start
            predictions=[{'act':f.act,**{s:v if isinstance(v,str) else v.text for s,v in f.slots.items()}} for f in result.frames]
            coverage=[]
            for i,frame in enumerate(case['expected']):
                for slot,values in frame.items():
                    if slot=='act' or values==['NONE']:
                        continue
                    possible+=1
                    available={c.text for c in result.inventory.menus[slot].values()}
                    present=bool(set(values)&available);covered+=present
                    coverage.append({'frame':i,'slot':slot,'available':present,'expected':values})
            record={'id':case['id'],'group':case['group'],'text':case['text'],
                    'status':'accepted' if result.status=='arranged' else 'error',
                    'result':asdict(result),'selected':predictions,'seconds':elapsed,
                    'candidate_count':len(result.inventory.candidates),'candidate_coverage':coverage,
                    'source_retained':ledger_valid(result),'exchange':provider.last_exchange,
                    'score':score(case['expected'],predictions,False)}
            if result.status!='arranged':
                record['error']=result.diagnostics[-1].message
            capture.write(json.dumps(record,ensure_ascii=False)+'\n');capture.flush();records.append(record)
            print(f"{len(records)}/50 {case['id']} {record['status']} exact={record['score']['exact']} retained={record['source_retained']}",flush=True)
    unchanged=all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    totals={key:sum(r['score'][key] for r in records) for key in ('slots_correct','slots_total','required_preserved','required_total')}
    baseline_rows=[json.loads(l) for l in (args.baseline/'cases.jsonl').read_text().splitlines()]
    gold={c['id']:c['expected'] for c in cases}
    baseline_scores=[score(gold[r['id']],r.get('selected',[]),False) for r in baseline_rows]
    summary={'state':'complete','source_unchanged':unchanged,'cases':50,
             'accepted':sum(r['status']=='accepted' for r in records),'errors':sum(r['status']=='error' for r in records),
             'exact_cases':sum(r['score']['exact'] for r in records),**totals,
             'candidate_coverage':{'covered':covered,'total':possible},
             'source_retention':{'cases':sum(r['source_retained'] for r in records),'total':50,
                                 'original_characters':sum(len(r['text']) for r in records)},
             'median_seconds':statistics.median(r['seconds'] for r in records),'total_seconds':sum(r['seconds'] for r in records),
             'baseline_common_score':{'exact_cases':sum(s['exact'] for s in baseline_scores),
                                      **{key:sum(s[key] for s in baseline_scores) for key in totals}},
             'by_group':{g:{'exact':sum(r['score']['exact'] for r in records if r['group']==g),
                            'cases':sum(r['group']==g for r in records)} for g in sorted({r['group'] for r in records})},
             'limitation':'Same reused agent-authored references. Exact slot accuracy and required-slot retention are not full READ accuracy or all meaning preservation. Source retention is exact text accounting only.'}
    dump(args.output/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
    return 0 if unchanged and all(r['source_retained'] for r in records) else 2


if __name__=='__main__':
    raise SystemExit(main())
