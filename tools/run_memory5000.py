"""Capture source/context only, then score independent gold; never install calibration."""
from collections import Counter
import argparse, hashlib, json, time
from pathlib import Path
import kobra.rule_assignment as assignment_module
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from kobra.knowledge import KnowledgeSnapshot
from evaluate_selection import score
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'evidence/memory5000-1'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--label',choices=('before','after','after-review'),required=True);a=p.parse_args()
    manifest=json.loads((BASE/'manifest.json').read_text())
    assert all(digest(BASE/n)==h for n,h in manifest['files'].items())
    if a.label.startswith('after'):
        freeze=json.loads((BASE/('reader-freeze-reviewed.json' if a.label=='after-review' else 'reader-freeze.json')).read_text())
        assert all(digest(ROOT/n)==h for n,h in freeze.items())
    out=BASE/a.label;out.mkdir(exist_ok=False)
    rows=[json.loads(line) for line in (BASE/'inputs.jsonl').read_text().splitlines()]
    assigner=RuleAssigner();captures=[]
    source=Path(assignment_module.__file__).parent
    provenance=dict(assignment_version=assignment_module.VERSION,source_hashes={p.name:digest(p) for p in source.glob('*.py')},input_hash=digest(BASE/'inputs.jsonl'),gold_excluded_from_reader=True,new_model_calls=0)
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('STARTED '+a.label+' 5000-case capture',flush=True)
    with (out/'captures.jsonl').open('w') as f:
      for i,row in enumerate(rows,1):
        start=time.monotonic()
        try:
            k=KnowledgeSnapshot(**row['knowledge']) if 'knowledge' in row else None
            result=GatedRuleReader(assigner,ConfidenceGate(),knowledge=k).read(row['text'],history=row.get('history',[]),context_claims=row.get('context_claims',[]))
        except Exception as exc:result=dict(route='ERROR',error=type(exc).__name__)
        capture=dict(id=row['id'],family=row['family'],text=row['text'],result=result,seconds=time.monotonic()-start)
        captures.append(capture);f.write(json.dumps(capture)+'\n')
        if i%1000==0: print(str(i)+'/5000 captured',flush=True)
    gold={r['id']:r for r in map(json.loads,(BASE/'gold.jsonl').read_text().splitlines())}
    scored=[]
    for r in captures:
        g=gold[r['id']];result=r['result'];code=result.get('code_proposal',{});proposal=result.get('proposal',{})
        parsed=code.get('route')=='code' and score(g['expected'],code.get('frames',[]))['exact']
        bindings=proposal.get('groundings',{})
        binding_ok=bindings==g['bindings']
        blockers=[x for x in result.get('reasons',[]) if x!='uncalibrated_cohort']
        selected=[c['id'] for m in result.get('knowledge_evidence',{}).get('matches',[]) for c in m['lookup'].get('selected',[])]
        lexical_ok=g['lexical'] is None or selected==[g['lexical']]
        ask_ok=result.get('route')=='ASK' and g['ask_reason'] in blockers if g['ask_reason'] else not blockers
        correct=parsed and binding_ok and lexical_ok and ask_ok
        scored.append(dict(r,expected=g,parsed_correct=parsed,binding_correct=binding_ok,lexical_correct=lexical_ok,
            decision_correct=ask_ok,correct=correct,actual_groundings=bindings,validation_reasons=blockers))
    counts=Counter(r['family'] for r in scored)
    summary=dict(cases=len(scored),correct=sum(r['correct'] for r in scored),
        parsing_correct=sum(r['parsed_correct'] for r in scored),
        incorrect_code_parses=sum(r['result'].get('code_proposal',{}).get('route')=='code' and not r['parsed_correct'] for r in scored),
        wrong_nonempty_bindings=sum(bool(r['actual_groundings']) and not r['binding_correct'] for r in scored),
        expected_binding_cases=sum(bool(r['expected']['bindings']) for r in scored),
        correct_expected_bindings=sum(bool(r['expected']['bindings']) and r['binding_correct'] for r in scored),
        expected_ASK_cases=sum(bool(r['expected']['ask_reason']) for r in scored),
        correct_ASK_reasons=sum(bool(r['expected']['ask_reason']) and r['decision_correct'] and r['binding_correct'] for r in scored),
        runtime_errors=sum(r['result'].get('route')=='ERROR' for r in scored),
        source_retained=sum(r['result'].get('source')==r['text'] for r in scored),
        final_routes=dict(Counter(r['result'].get('route') for r in scored)),new_model_calls=0,
        by_family={k:dict(cases=n,correct=sum(r['family']==k and r['correct'] for r in scored)) for k,n in counts.items()},
        seconds=sum(r['seconds'] for r in scored),
        semantics='Underlying parsing/binding/ASK-reason contract score; final acceptance unavailable without calibration. No AI-correct score.',
        source_and_gold_unchanged=all(digest(BASE/n)==h for n,h in manifest['files'].items()))
    for name,data in [('scored',scored),('failures',[r for r in scored if not r['correct']])]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
