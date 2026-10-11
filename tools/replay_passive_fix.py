"""Development replay of fixed false successes; preserve original fresh captures."""
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from kobra.rule_assignment import RuleAssigner
from evaluate_selection import score

ROOT=Path(__file__).resolve().parents[1]


def category(row):
    text=row['text'];reasons=row['result']['code_proposal']['reasons']
    if 'additional lexical verb' in reasons:
        tense='Past' if text.startswith(('Was ','Were ')) else 'Present'
        return tense+' negative passive question' if ' not ' in text else tense+' affirmative passive question'
    if 'multiple role candidates' in reasons:return 'Recipient/patient ambiguity'
    return 'Other unresolved'


def main():
    out=ROOT/'evidence/passive-question-fix-1';out.mkdir(exist_ok=False)
    reader=GatedRuleReader(RuleAssigner(),ConfidenceGate())
    records=[];baselines={}
    for number in range(6,10):
        path=ROOT/f'evidence/read300/batch-{number:03d}/rule-evaluation/scored.jsonl'
        baselines[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        for line in path.read_text().splitlines():
            old=json.loads(line)
            result=reader.read(old['text'])
            scored=score(old['expected'],result['code_proposal']['frames'])
            routed=result['code_proposal']['route']=='code'
            correct=routed and scored['exact']
            records.append(dict(set=number,id=old['id'],text=old['text'],expected=old['expected'],
                before=old['result']['code_proposal'],before_correct=old['correct_code_proposal'],
                result=result,score=scored,after_correct=correct,tick=correct and not old['correct_code_proposal'],
                regression=old['correct_code_proposal'] and not correct,
                category=category(old) if not routed else None))
    unresolved=[r for r in records if r['result']['code_proposal']['route']!='code']
    wrong=[r for r in records if r['result']['code_proposal']['route']=='code' and not r['after_correct']]
    counts=Counter(r['category'] for r in unresolved)
    summary=dict(split='reused development after inspecting errors; not fresh confirmation',cases=len(records),
        before_correct=sum(r['before_correct'] for r in records),after_correct=sum(r['after_correct'] for r in records),
        ticks=sum(r['tick'] for r in records),regressions=sum(r['regression'] for r in records),
        wrong_code=len(wrong),unresolved=len(unresolved),categories=dict(counts),
        source_retained=sum(r['result']['source']==r['text'] for r in records),new_model_calls=0,
        final_routes=dict(Counter(r['result']['route'] for r in records)),
        before_files=baselines,source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in list((ROOT/'src/kobra').glob('*.py'))+[Path(__file__)]})
    assert summary['ticks']==4 and summary['regressions']==0 and summary['wrong_code']==0
    assert summary['unresolved']==145
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    (out/'unresolved.json').write_text(json.dumps(unresolved,indent=2)+'\n')
    with (out/'unresolved.csv').open('w',newline='') as handle:
        writer=csv.writer(handle,lineterminator="\n");writer.writerow(['category','set','id','sentence','reason'])
        for r in sorted(unresolved,key=lambda r:(r['category'],r['text'])):
            writer.writerow([r['category'],r['set'],r['id'],r['text'],'; '.join(r['result']['code_proposal']['reasons'])])
    body='<h1>Passive-question fix and unresolved sentences</h1><p>Development replay: all four incorrect interpretations corrected; zero regressions. 942 correct code interpretations, zero wrong, 145 unresolved out of 1,087. Original fresh-set results remain unchanged. No AI calls; all final routes remain ASK without calibration.</p>'
    body+='<h2>Four corrected interpretations</h2>'
    for r in records:
        if r['tick']:
            body+='<article><h3>'+html.escape(r['text'])+'</h3><pre>'+html.escape(json.dumps(dict(before=r['before']['frames'],after=r['result']['code_proposal']['frames']),indent=2))+'</pre></article>'
    body+='<h2>Unresolved categories</h2><p>All 144 passive questions have the same observed parser problem: be is the root, and the participle is attached to the subject as acl. Tense and negation below are useful subcategories, not four separate causes. In the remaining sentence, Mira and a key are both labeled dobj.</p>'
    body+='<table><tr><th>Category</th><th>Count</th></tr>'+''.join('<tr><td>'+html.escape(k)+'</td><td>'+str(v)+'</td></tr>' for k,v in sorted(counts.items()))+'</table>'
    for cat in sorted(counts):
        body+='<h2>'+html.escape(cat)+' ('+str(counts[cat])+')</h2><ol>'
        for r in sorted((r for r in unresolved if r['category']==cat),key=lambda r:r['text']):
            body+='<li><details><summary>'+html.escape(r['text'])+'</summary><pre>'+html.escape(json.dumps(dict(expected=r['expected'],proposal=r['result']['code_proposal']),indent=2))+'</pre></details></li>'
        body+='</ol>'
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>READ fixes and unresolved categories</title><style>body{max-width:1100px;margin:30px auto;padding:20px;background:#112033;color:#edf3ff;font:16px/1.6 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}td,th{padding:10px;border:1px solid #657e97}table{border-collapse:collapse}article,details{margin:10px 0;padding:10px;border:1px solid #657e97}summary{cursor:pointer}</style>'+body+'</html>'
    (ROOT/'reports/read-passive-fix.html').write_text(page)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('before_files','source_hashes')},indent=2))

if __name__=='__main__':main()
