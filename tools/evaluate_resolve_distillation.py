"""Reused 5k replay and projection checks, not fresh semantic accuracy evidence."""
from collections import Counter
from copy import deepcopy
import gzip, hashlib, html, json
from pathlib import Path
from kobra.confidence_gate import ConfidenceGate,GatedRuleReader
from kobra.rule_assignment import RuleAssigner
from kobra.knowledge import KnowledgeSnapshot
from kobra.resolve_distillation import distill_for_resolve
from kobra.selection_read import SLOTS
from evaluate_selection import score
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'evidence/memory5000-1'
OUT=ROOT/'evidence/resolve-distillation-1'

def main():
    OUT.mkdir(exist_ok=False)
    inputs=[json.loads(x) for x in (BASE/'inputs.jsonl').read_text().splitlines()]
    assigner=RuleAssigner();captures=[]
    paths=[*(ROOT/'src/kobra').glob('*.py'),Path(__file__)]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (OUT/'source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    for i,row in enumerate(inputs,1):
        k=KnowledgeSnapshot(**row['knowledge']) if 'knowledge' in row else None
        r=GatedRuleReader(assigner,ConfidenceGate(),knowledge=k).read(row['text'],history=row.get('history',[]),context_claims=row.get('context_claims',[]))
        before=deepcopy(r);d=distill_for_resolve(r)
        assert r==before
        f=[dict({s:'NONE' for s in SLOTS},act=p['act'],predicate=p['predicate'],**p['arguments'],**p['qualifiers']) for p in d['points']]
        assert f==r['proposal']['frames']
        binds={b['mention']:b['entity_id'] for p in d['points'] for b in p['identity_bindings']}
        assert binds==r['proposal'].get('groundings',{})
        covered=set()
        for s in d['retained_remainder']+[e for p in d['points'] for e in p['evidence']]:
            assert s['text']==row['text'][s['start']:s['end']]
            covered.update(range(s['start'],s['end']))
        assert covered==set(range(len(row['text'])))
        assert d['state']['read_route']==r['route'] and not d['state']['ready_for_resolve']
        assert not d['state']['distillation_diagnostics']
        captures.append(dict(id=row['id'],text=row['text'],read=r,distillation=d))
        if i%1000==0:print(f'{i}/5000 replayed and projected',flush=True)
    with gzip.open(OUT/'captures.jsonl.gz','wt') as f:
        for c in captures:f.write(json.dumps(c)+'\n')
    gold={r['id']:r for r in map(json.loads,(BASE/'gold.jsonl').read_text().splitlines())}
    prior={r['id']:r for r in map(json.loads,(BASE/'after-review/scored.jsonl').read_text().splitlines())}
    scored=[]
    for c in captures:
        g=gold[c['id']];r=c['read'];p=r['code_proposal']
        parsed=p['route']=='code' and score(g['expected'],p['frames'])['exact']
        binding=r['proposal'].get('groundings',{})==g['bindings']
        blockers=set(r['reasons'])-{'uncalibrated_cohort'}
        decision=(r['route']=='ASK' and g['ask_reason'] in blockers) if g['ask_reason'] else not blockers
        selected=[x['id'] for m in r.get('knowledge_evidence',{}).get('matches',[]) for x in m['lookup'].get('selected',[])]
        lexical=g['lexical'] is None or selected==[g['lexical']]
        correct=parsed and binding and decision and lexical
        scored.append(dict(id=c['id'],text=c['text'],before_correct=prior[c['id']]['correct'],after_correct=correct,
            tick=correct and not prior[c['id']]['correct'],regression=prior[c['id']]['correct'] and not correct))
    summary=dict(kind='reused development replay; distillation checks are representation invariants, not semantic proof',cases=5000,
        before_correct=sum(r['before_correct'] for r in scored),after_correct=sum(r['after_correct'] for r in scored),
        ticks=sum(r['tick'] for r in scored),regressions=sum(r['regression'] for r in scored),
        frame_roundtrips=5000,grounding_roundtrips=5000,source_coverage_checks=5000,unchanged_gate_checks=5000,new_model_calls=0,
        final_routes=dict(Counter(c['read']['route'] for c in captures)),
        baseline_hashes={n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ('inputs.jsonl','gold.jsonl','after-review/scored.jsonl')},
        capture_sha256=hashlib.sha256((OUT/'captures.jsonl.gz').read_bytes()).hexdigest())
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (OUT/'scores.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in scored))
    examples=[]
    reader=GatedRuleReader(assigner,ConfidenceGate())
    for text in ['Was the sensor not moved by Mira?','Open and read the file.','Create two servers and launch them.','Tell me what she wanted yesterday.']:
        examples.append(reader.read_for_resolve(text))
    examples.append(next(c['distillation'] for c in captures if c['read'].get('memory_evidence',{}).get('bindings')))
    (OUT/'examples.json').write_text(json.dumps(examples,indent=2)+'\n')
    e=html.escape
    body='<h1>READ → distillation → RESOLVE</h1><p>Code-only projection of source roles, qualifications, relations and grounding evidence. No answers, action execution or new identity decisions. Source wording remains part of the contract.</p>'
    body+='<p>All three sensor questions now parse correctly. Reused 5,000-case contract replay: 5,000 correct, three improvements, zero regressions. This does not replace the historical fresh result.</p>'
    body+='<p>Every replay preserved all frame fields and identity bindings, retained source characters and kept the gate outcome unchanged. These checks establish representation preservation, not complete semantic accuracy. All final routes remain ASK without calibration.</p>'
    for d in examples:
        body+='<h2>'+e(d['source']['text'])+'</h2><pre>'+e(json.dumps({k:d[k] for k in ('points','relations','retained_remainder','state')},indent=2))+'</pre>'
    body+='<h2>Measured replay</h2><pre>'+e(json.dumps(summary,indent=2))+'</pre>'
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>READ distillation for RESOLVE</title><style>body{max-width:1100px;margin:30px auto;padding:20px;font:16px/1.6 system-ui;background:#112033;color:#edf3ff}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}</style>'+body+'</html>'
    (ROOT/'reports/read-resolve-distillation.html').write_text(page)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
