"""Fresh code-first READ capture; source retention is not semantic preservation."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil
import time
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from evaluate_selection import score

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')


def summarize(batch, output):
    gold = {r['id']:r for r in json.loads((batch/'frozen-reference.json').read_text())['cases']}
    context = {r['case_id']:r for r in json.loads((batch/'context-requirements.json').read_text())['cases']}
    inputs = json.loads((batch/'inputs.json').read_text())
    records = [json.loads(line) for line in (output/'captures.jsonl').read_text().splitlines()]
    assert [r['id'] for r in records] == [r['id'] for r in inputs]
    expected_size = json.loads((batch/'generator-manifest.json').read_text()).get('requested_size', 300)
    assert len(records) == len(gold) == expected_size
    rows = []
    for record, source in zip(records, inputs):
        assert source['text'] == record['text'] == gold[record['id']]['text']
        reference = gold[record['id']]
        result = record['result']
        proposal = result.get('code_proposal', {})
        scored = score(reference['expected'] or [], proposal.get('frames', []))
        if reference['expected'] is None:
            scored['exact'] = False
        automatic = proposal.get('route') == 'code'
        row = dict(record, group=reference['group'], expected=reference['expected'], score=scored,
                   code_routed=automatic, correct_code_proposal=automatic and scored['exact'],
                   context=context[record['id']], source_retained=result.get('source') == source['text'])
        rows.append(row)
    code = [r for r in rows if r['code_routed']]
    exact = sum(r['correct_code_proposal'] for r in rows)
    groups = sorted({r['group'] for r in rows})
    summary = dict(cases=len(rows), code_routed=len(code), code_correct=exact,
        code_incorrect=sum(not r['score']['exact'] for r in code), unresolved=len(rows)-len(code),
        correct_code_over_all=exact/len(rows), code_precision=exact/len(code) if code else None,
        source_retained=sum(r['source_retained'] for r in rows),
        required_slots_preserved=sum(r['score']['required_preserved'] for r in rows),
        required_slots_total=sum(r['score']['required_total'] for r in rows),
        new_model_calls=0, AI_correct=None, correct_ASK=None,
        final_routes=dict(Counter(r['result'].get('route','ERROR') for r in rows)),
        gate_reasons=dict(Counter(reason for r in rows for reason in r['result'].get('reasons',[]))),
        context_flagged=sum(r['context']['requires_context'] for r in rows),
        context_breakdown={label:dict(cases=len(subset),code_correct=sum(r['correct_code_proposal'] for r in subset))
          for label in ['requires_context','no_external_requirement_identified']
          for subset in [[r for r in rows if r['context']['requires_context']==(label=='requires_context')]]},
        by_group={g:dict(cases=sum(r['group']==g for r in rows),code_correct=sum(r['group']==g and r['correct_code_proposal'] for r in rows)) for g in groups},
        rule_coverage=dict(Counter(rule for r in rows for rule in r['result'].get('code_proposal',{}).get('rules',[]))),
        adapter_errors=sum(r['expected'] is None for r in rows),
        runtime_errors=sum('runtime_error' in r for r in rows),
        seconds=sum(r['seconds'] for r in rows),
        scope='Fresh sentences within existing Serpent grammar; bounded literal-slot scoring, not complete semantic accuracy.',
        configuration='Current RuleAssigner + GatedRuleReader; no live resolver, calibration or knowledge snapshot supplied.',
        ASK_note='No independent case-specific ASK-reason gold for this batch. Report routes/context flags, not a fabricated correct-ASK score.',
        comparison_note='Earlier 86.67% involved a live AI arranger; 97.67% was a reused-data hybrid simulation. Neither is this configuration.')
    return rows, summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=int,required=True)
    parser.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    batch=ROOT/f'evidence/read300/batch-{args.batch:03d}'
    output=batch/'rule-evaluation'
    if args.audit:
        rows,summary=summarize(batch,output)
        saved=json.loads((output/'summary.json').read_text())
        manifest=json.loads((output/'manifest.json').read_text())
        checks=dict(recomputed_summary_matches=summary==saved,
                    source_unchanged=all(digest(ROOT/p)==h for p,h in manifest['source_hashes'].items()),
                    frozen_files_unchanged=all(digest(batch/p)==h for p,h in manifest['batch_hashes'].items()),
                    source_retention_all=all(r['source_retained'] for r in rows),
                    captures_sha256=digest(output/'captures.jsonl'))
        dump(output/'audit.json',checks)
        print(json.dumps(checks,indent=2))
        assert all(checks[k] for k in checks if k!='captures_sha256')
        return
    output.mkdir(exist_ok=False)
    inputs=json.loads((batch/'inputs.json').read_text())
    count=json.loads((batch/'generator-manifest.json').read_text()).get('requested_size',300)
    assert 1 <= count <= 300 and len(inputs)==count and len({r['id'] for r in inputs})==count
    assigner=RuleAssigner()
    reader=GatedRuleReader(assigner,ConfidenceGate())
    paths=list((ROOT/'src/kobra').glob('*.py'))+list((ROOT/'tools').glob('*.py'))
    hashes={str(p.relative_to(ROOT)):digest(p) for p in paths}
    for p in paths:
        dest=output/'source-snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    modelpath=Path(assigner.nlp.path)
    manifest=dict(started_utc=datetime.now(timezone.utc).isoformat(),cases=count,
                  source_hashes=hashes,assignment_configuration=assigner.configuration_id,
                  parser_hashes={str(p.relative_to(modelpath)):digest(p) for p in modelpath.rglob('*') if p.is_file()},
                  batch_hashes={p.name:digest(p) for p in batch.glob('*.json')},
                  gold_excluded_from_reader=True,context_teacher_labels_excluded=True,
                  split='fresh sentences; same generator grammar',new_model_calls=0,no_retries=True)
    dump(output/'manifest.json',manifest)
    print(f'STARTED fresh {count}-case current code-first READ set',flush=True)
    with (output/'captures.jsonl').open('x') as capture:
        for i,row in enumerate(inputs,1):
            started=time.monotonic()
            try:
                result=reader.read(row['text'])
                record=dict(row,result=result)
            except Exception as exc:
                record=dict(row,result={'route':'ERROR','source':row['text']},runtime_error=type(exc).__name__)
            record['seconds']=time.monotonic()-started
            capture.write(json.dumps(record)+'\n');capture.flush()
            if i%50==0: print(f'{i}/{count} captured',flush=True)
    # Reference and teacher context labels are loaded only after capture completes.
    rows,summary=summarize(batch,output)
    dump(output/'summary.json',summary)
    with (output/'scored.jsonl').open('x') as handle, (output/'failures.jsonl').open('x') as failures:
        for row in rows:
            handle.write(json.dumps(row)+'\n')
            if not row['correct_code_proposal']: failures.write(json.dumps(row)+'\n')
    body='<h1>Fresh READ batch '+str(args.batch)+'</h1><p>'+str(summary['cases'])+' new sentences; current code-first configuration. No live AI or calibration. Source retention is not semantic preservation. All-case proposal coverage and correctness are reported separately from gate outcomes.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>'
    for row in rows:
        body+='<details><summary>'+html.escape(row['id']+' — '+row['text']+' — '+('code correct' if row['correct_code_proposal'] else 'code wrong' if row['code_routed'] else 'unresolved'))+'</summary><pre>'+html.escape(json.dumps(row,indent=2))+'</pre></details>'
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Fresh READ batch</title><style>body{max-width:1100px;margin:30px auto;padding:20px;font:16px/1.6 system-ui;background:#112033;color:#edf3ff}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}details{border:1px solid #667f99;padding:12px;margin:10px 0}summary{cursor:pointer}</style>'+body+'</html>'
    (ROOT/f'reports/read-batch-{args.batch:03d}.html').write_text(page)
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
