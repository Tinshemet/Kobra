"""Paired development routing simulation; uses saved fallback, no model calls."""
import json, hashlib
from pathlib import Path
from kobra.rule_assignment import RuleAssigner
from evaluate_selection import score

ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'evidence/rule-assignment-1'
    out.mkdir(exist_ok=False)
    engine=RuleAssigner(); rows=[]; summaries=[]
    for batch in (1,5):
        folder=ROOT/f'evidence/read300/batch-{batch:03d}'
        gold={r['id']:r for r in json.loads((folder/'frozen-reference.json').read_text())['cases']}
        records=[json.loads(x) for x in (folder/'evaluation/cases.jsonl').read_text().splitlines()]
        start=len(rows)
        for old in records:
            p=engine.assign(old['text']); expected=gold[old['id']]['expected']
            code=score(expected,p['frames']); automatic=p['route']=='code'
            combined=code if automatic else old['score']
            rows.append(dict(batch=batch,id=old['id'],text=old['text'],proposal=p,expected=expected,
                code_score=code,model_score=old['score'],hybrid_score=combined,
                hybrid_tick=not old['score']['exact'] and combined['exact'],
                hybrid_regression=old['score']['exact'] and not combined['exact']))
        rs=rows[start:]; auto=[r for r in rs if r['proposal']['route']=='code']; fallback=[r for r in rs if r['proposal']['route']!='code']
        summaries.append(dict(batch=batch,cases=len(rs),code_routed=len(auto),code_correct=sum(r['code_score']['exact'] for r in auto),
            fallback_cases=len(fallback),fallback_correct=sum(r['model_score']['exact'] for r in fallback),
            baseline_exact=sum(r['model_score']['exact'] for r in rs),hybrid_exact=sum(r['hybrid_score']['exact'] for r in rs),
            ticks=sum(r['hybrid_tick'] for r in rs),regressions=sum(r['hybrid_regression'] for r in rs)))
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary=dict(split='reused development',new_model_calls=0,mode='routing simulation using saved original model answers; no new model receives code proposals',
        parser='en_core_web_sm: learned parser, not model-free NLP',batches=summaries,
        source_sha256=hashlib.sha256((ROOT/'src/kobra/rule_assignment.py').read_bytes()).hexdigest())
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    (out/'rule_assignment.py').write_bytes((ROOT/'src/kobra/rule_assignment.py').read_bytes())
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
