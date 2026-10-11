"""Paired development replay after C020; original fresh evidence is immutable."""
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from kobra.rule_assignment import RuleAssigner
from evaluate_selection import score

ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'evidence/passive-noun-recovery-1';out.mkdir(exist_ok=False)
    reader=GatedRuleReader(RuleAssigner(),ConfidenceGate()); groups={}; hashes={}
    def read(path):
        hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        return [json.loads(line) for line in path.read_text().splitlines()]
    groups['sets10-12']=[dict(r,before_correct=r['correct_code_proposal']) for b in (10,11,12)
        for r in read(ROOT/f'evidence/read300/batch-{b:03d}/rule-evaluation/scored.jsonl')]
    groups['sets6-9']=[dict(r,before_correct=r['after_correct']) for r in read(ROOT/'evidence/question-role-fix-2/cases.jsonl')]
    gold={}
    for b in (1,5):
        path=ROOT/f'evidence/read300/batch-{b:03d}/frozen-reference.json'
        hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        gold.update({(b,r['id']):r['expected'] for r in json.loads(path.read_text())['cases']})
    groups['older600']=[dict(r,before_correct=r['after_correct'],expected=gold[r['batch'],r['id']])
        for r in read(ROOT/'evidence/question-role-fix-2/older-600-replay/cases.jsonl')]
    summaries={};ticks=[]
    for group,oldrows in groups.items():
        rows=[]
        for old in oldrows:
            result=reader.read(old['text']);p=result['code_proposal'];scored=score(old['expected'],p['frames'])
            correct=p['route']=='code' and scored['exact']
            r=dict(id=old['id'],text=old['text'],expected=old['expected'],before_correct=old['before_correct'],
                after_correct=correct,tick=correct and not old['before_correct'],
                regression=old['before_correct'] and not correct,result=result,score=scored)
            rows.append(r)
            if r['tick']:ticks.append(dict(group=group,**r))
        summaries[group]=dict(cases=len(rows),before_correct=sum(r['before_correct'] for r in rows),
            after_correct=sum(r['after_correct'] for r in rows),ticks=sum(r['tick'] for r in rows),
            regressions=sum(r['regression'] for r in rows),
            incorrect=sum(r['result']['code_proposal']['route']=='code' and not r['after_correct'] for r in rows),
            unresolved=sum(r['result']['code_proposal']['route']!='code' for r in rows),
            retained=sum(r['result']['source']==r['text'] for r in rows),
            final_routes=dict(Counter(r['result']['route'] for r in rows)))
        (out/(group+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary=dict(kind='reused development replay after inspecting failure; not fresh accuracy',
        groups=summaries,new_model_calls=0,baseline_hashes=hashes,
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*(ROOT/'src/kobra').glob('*.py'),Path(__file__)]})
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'ticks.json').write_text(json.dumps(ticks,indent=2)+'\n')
    body='<h1>READ: remaining passive-question fix</h1><p>C020 recovers a determiner + noun absorbed into a participle by the dependency parser. It requires the complete bounded passive question shape, explicit by-agent and no extra clause. No sentence or name is hardcoded.</p>'
    body+='<p>The original fresh score remains 899/900 (99.89%). Results below are development replay after inspecting that failure, not a new fresh 100% claim. Final ASK routes still reflect absent calibration.</p><pre>'+html.escape(json.dumps(summaries,indent=2))+'</pre>'
    for r in ticks:body+='<h2>'+html.escape(r['text'])+'</h2><pre>'+html.escape(json.dumps(r['result']['code_proposal'],indent=2))+'</pre>'
    body+='<p>The earlier large gain came from repairing one repeated parser pattern in 144 passive questions, plus one double-object case. New lexical combinations in the same limited grammar then scored 899/900. This does not measure general language or memory-grounding accuracy.</p>'
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>READ passive noun recovery</title><style>body{max-width:1000px;margin:30px auto;padding:20px;font:16px/1.6 system-ui;background:#112033;color:#edf3ff}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'+body+'</html>'
    (ROOT/'reports/read-passive-noun-recovery.html').write_text(page)
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
