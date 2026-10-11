"""Replay an arrangement capture and verify its ledger and scores without inference."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from kobra import ArrangingReader, ClientConfig, IdentityFrontDoor, LinguisticCandidates, Request, Services
from kobra.ollama import OllamaProvider
from evaluate_arrangement import ledger_valid
from evaluate_selection import score, dump


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((args.run/'manifest.json').read_text())
    assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in manifest['source_hashes'].items())
    fixture=json.loads((args.run/'frozen-reference.json').read_text())
    gold={c['id']:c for c in fixture['cases']}
    records=[json.loads(l) for l in (args.run/'cases.jsonl').read_text().splitlines()]
    assert len(records)==50 and {r['id'] for r in records}==set(gold)
    extractor=LinguisticCandidates();reader=ArrangingReader(extractor)
    model_root=Path(extractor.nlp.path)
    assert all(hashlib.sha256((model_root/p).read_bytes()).hexdigest()==h for p,h in manifest['parser_hashes'].items())
    errors=Counter();wrong_slots=Counter();leftovers=Counter();missing=[]
    exact=slots=required=chars=0
    for row in records:
        reply=row['exchange']['response']
        provider=OllamaProvider()
        provider._request=lambda *a,**kw:reply
        request=Request(row['text']);services=Services(ClientConfig('offline','1'),model=provider)
        result=reader.read(IdentityFrontDoor().normalize(request,services),request,services)
        assert json.loads(json.dumps(asdict(result)))==row['result'],row['id']
        assert ledger_valid(result) and row['source_retained'],row['id']
        selected=[{'act':f.act,**{s:v if isinstance(v,str) else v.text for s,v in f.slots.items()}} for f in result.frames]
        rescored=score(gold[row['id']]['expected'],selected,False)
        assert rescored==row['score'],row['id']
        exact+=rescored['exact'];slots+=rescored['slots_correct'];required+=rescored['required_preserved']
        chars+=sum(len(p.text) for p in result.source_ledger)
        if row['status']=='error':errors[row['error']]+=1
        wrong_slots.update(m['slot'] for m in rescored['mismatches'])
        leftovers.update({label:sum(len(p.text) for p in result.source_ledger if p.label==label)
                          for label in {p.label for p in result.source_ledger}})
        for c in row['candidate_coverage']:
            if not c['available']:missing.append({'id':row['id'],**c})
    summary=json.loads((args.run/'summary.json').read_text())
    assert (exact,slots,required,chars)==(summary['exact_cases'],summary['slots_correct'],summary['required_preserved'],summary['source_retention']['original_characters'])
    with (args.run/'case-review.csv').open('x') as stream:
        writer=csv.writer(stream)
        writer.writerow(['id','group','sentence','status','exact','source_retained','expected','selected','mismatches','error','seconds'])
        for row in records:
            writer.writerow([row['id'],row['group'],row['text'],row['status'],row['score']['exact'],row['source_retained'],
                             json.dumps(gold[row['id']]['expected']),json.dumps(row['selected']),json.dumps(row['score']['mismatches']),
                             row.get('error',''),round(row['seconds'],3)])
    audit={'cases_replayed':50,'scores_matched':50,'source_ledgers_matched':50,'characters_reconstructed':chars,
           'model_calls':0,'code_and_parser_hashes_matched':True,'errors':dict(errors),'wrong_slots':dict(wrong_slots),
           'missing_candidates':missing,'source_characters_by_provisional_label':dict(leftovers),
           'limitation':'Same-agent replay verifies reproducibility and text retention, not independent reference correctness.'}
    dump(args.run/'offline-audit.json',audit)
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    main()
