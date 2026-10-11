"""Replay saved independent gold after role repairs; never fresh evidence."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from kobra.rule_assignment import RuleAssigner
from evaluate_selection import score

ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'evidence/question-role-fix-2'
    out.mkdir(exist_ok=False)
    baseline=ROOT/'evidence/passive-question-fix-1/cases.jsonl'
    reader=GatedRuleReader(RuleAssigner(),ConfidenceGate())
    records=[]
    for line in baseline.read_text().splitlines():
        old=json.loads(line); result=reader.read(old['text']); proposal=result['code_proposal']
        scored=score(old['expected'],proposal['frames'])
        correct=proposal['route']=='code' and scored['exact']
        records.append(dict(set=old['set'],id=old['id'],text=old['text'],expected=old['expected'],
            before_correct=old['after_correct'],after_correct=correct,
            tick=correct and not old['after_correct'],regression=old['after_correct'] and not correct,
            result=result,score=scored))
    summary=dict(kind='reused development, not fresh accuracy',cases=len(records),
        before_correct=sum(r['before_correct'] for r in records),after_correct=sum(r['after_correct'] for r in records),
        ticks=sum(r['tick'] for r in records),regressions=sum(r['regression'] for r in records),
        wrong_code=sum(r['result']['code_proposal']['route']=='code' and not r['after_correct'] for r in records),
        unresolved=sum(r['result']['code_proposal']['route']!='code' for r in records),
        ticks_by_new_rule=dict(Counter(rule for r in records if r['tick'] for rule in r['result']['code_proposal']['rules'] if rule.startswith(('C018','C019')))),
        source_retained=sum(r['result']['source']==r['text'] for r in records),new_model_calls=0,
        final_routes=dict(Counter(r['result']['route'] for r in records)),
        baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/kobra').glob('*.py')})
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'},indent=2))

if __name__=='__main__':main()
