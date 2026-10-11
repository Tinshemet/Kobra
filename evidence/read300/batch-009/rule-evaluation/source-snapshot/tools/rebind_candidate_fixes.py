"""Development-only ablation: hold captured AI choices fixed, vary candidate rules.

These are binding recoveries, not new end-to-end inference or fresh accuracy.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from kobra import ClientConfig, IdentityFrontDoor, LinguisticCandidates, Request, Services
from kobra.candidate_read import bind_arrangement
from evaluate_selection import score, dump


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('batch',type=Path)
    args=ap.parse_args()
    old=[json.loads(l) for l in (args.batch/'evaluation/cases.jsonl').read_text().splitlines()]
    gold={c['id']:c['expected'] for c in json.loads((args.batch/'frozen-reference.json').read_text())['cases']}
    rules=['R001-content-predicate-fallback','R002-expanded-nominal']
    nlp=LinguisticCandidates().nlp
    services=Services(ClientConfig('candidate-ablation','1'))
    for enabled in ([rules[0]],[rules[1]],rules):
        extractor=LinguisticCandidates(nlp=nlp,disabled_rules=set(rules)-set(enabled))
        records=[]
        for row in old:
            request=Request(row['text']);view=IdentityFrontDoor().normalize(request,services)
            inventory=extractor.build(view)
            predicted=[];error=None
            try:
                bound=bind_arrangement(row['result']['proposal'],request,view,inventory)
                predicted=[{'act':f.act,**{s:v if isinstance(v,str) else v.text for s,v in f.slots.items()}} for f in bound.frames]
            except Exception as exc:
                error=str(exc)
            result=score(gold[row['id']] or [],predicted)
            was=row['score']['exact'];now=result['exact']
            records.append({'id':row['id'],'text':row['text'],'before_correct':was,'after_correct':now,
                            'tick':not was and now,'regression':was and not now,
                            'coverage':inventory.rule_matches,'score':result,'error':error})
        label='+'.join(r.split('-')[0] for r in enabled)
        dump(args.batch/f'development-binding-{label}.json',{
            'enabled_rules':enabled,'kind':'development frozen-proposal binding ablation','new_model_calls':0,
            'cases':len(records),'before_exact':sum(r['before_correct'] for r in records),
            'after_exact':sum(r['after_correct'] for r in records),
            'verified_binding_ticks':sum(r['tick'] for r in records),
            'regressions':sum(r['regression'] for r in records),'records':records,
            'limitation':'Candidate binding recovery with historical model choices fixed; not an end-to-end or fresh-batch improvement estimate.'})
        print(label,sum(r['tick'] for r in records),'binding ticks;',sum(r['regression'] for r in records),'regressions')


if __name__=='__main__':
    main()
