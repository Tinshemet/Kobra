"""Combine captured sets, recompute scores and check frozen runtime provenance."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import unicodedata
from run_rule_batch import summarize, digest

ROOT=Path(__file__).resolve().parents[1]


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC',text).casefold().split())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sets',nargs='+',type=int,default=[6,7,8,9])
    args=parser.parse_args()
    tag=f'{min(args.sets):03d}-{max(args.sets):03d}'
    out=ROOT/'evidence/read300'/f'series-{tag}';out.mkdir(exist_ok=False)
    rows=[];sets=[];manifests=[];checks=[]
    for number in args.sets:
        batch=ROOT/f'evidence/read300/batch-{number:03d}';folder=batch/'rule-evaluation'
        records,summary=summarize(batch,folder)
        assert summary==json.loads((folder/'summary.json').read_text())
        manifest=json.loads((folder/'manifest.json').read_text());manifests.append(manifest)
        assert all(digest(batch/p)==h for p,h in manifest['batch_hashes'].items())
        rows.extend(dict(r,set=number) for r in records)
        sets.append(dict(set=number,**summary))
        checks.append(dict(set=number,recomputed_summary_matches=True,frozen_inputs_unchanged=True,
                           captures_sha256=digest(folder/'captures.jsonl')))
    runtime_keys=[k for k in manifests[0]['source_hashes'] if k.startswith('src/kobra/') or k=='tools/evaluate_selection.py']
    assert all(all(m['source_hashes'][k]==manifests[0]['source_hashes'][k]==digest(ROOT/k) for k in runtime_keys) for m in manifests)
    assert all(m['parser_hashes']==manifests[0]['parser_hashes'] for m in manifests)
    assert len({m['assignment_configuration'] for m in manifests})==1
    seen=[normalized(r['text']) for r in rows];assert len(seen)==len(set(seen))
    selected_dirs={ROOT/f'evidence/read300/batch-{n:03d}' for n in args.sets}
    prior=set()
    for path in (ROOT/'evidence').rglob('inputs.json'):
        if any(b in path.parents for b in selected_dirs):continue
        for row in json.loads(path.read_text()):
            if isinstance(row,dict) and 'text' in row:prior.add(normalized(row['text']))
    assert not set(seen).intersection(prior)
    routed=sum(r['code_routed'] for r in rows);correct=sum(r['correct_code_proposal'] for r in rows)
    unresolved=[r for r in rows if not r['code_routed']]
    wrong=[r for r in rows if r['code_routed'] and not r['correct_code_proposal']]
    summary=dict(sets=[{k:s[k] for k in ['set','cases','code_correct','code_incorrect','unresolved','correct_code_over_all']} for s in sets],
        total=len(rows),unique_sentences=len(set(seen)),correct_code=correct,wrong_code=len(wrong),unresolved=len(unresolved),
        correct_over_all=correct/len(rows),precision_when_code_routed=correct/routed,
        source_retained=sum(r['source_retained'] for r in rows),new_model_calls=0,
        final_routes=dict(Counter(r['result']['route'] for r in rows)),
        unresolved_reasons=dict(Counter(reason for r in unresolved for reason in r['result']['code_proposal']['reasons'])),
        by_group=dict(Counter(r['group'] for r in rows)),
        context_flagged=sum(r['context']['requires_context'] for r in rows),
        required_slots_preserved=sum(r['score']['required_preserved'] for r in rows),
        required_slots_total=sum(r['score']['required_total'] for r in rows),
        checks=dict(per_set=checks,identical_runtime_and_scorer=True,identical_parser=True,identical_configuration=True,
                    duplicate_count=0,overlap_with_prior_inputs=0),
        final_set_note='The unchanged finite Serpent inventory had only 187 unseen cases left; final set uses all of them. Cardinality handling changed, not grammar, READ rules or scoring.',
        limits=['Literal-slot correctness, not full semantic accuracy.','Later sets are entirely voice/tense because other unseen construction families were exhausted.','No new shared-object, archive/library, context-grounding or AI-resolution coverage.','All gate routes are ASK because real calibration is absent; correct-ASK is not scored.','Same frozen rules throughout; differing set scores are not improvement or regression measurements.'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'failures.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in unresolved+wrong))
    header='<h1>READ: '+str(len(sets))+' fresh sets</h1><p>'+format(len(rows),',')+' distinct sentences, frozen READ rules and scorer, no generative AI calls. The final set contains 187 cases because the unchanged inventory ran out of unseen sentences.</p>'
    table='<table><tr><th>Set</th><th>Cases</th><th>Correct code</th><th>Wrong code</th><th>Unresolved</th><th>Correct / all</th></tr>'
    for s in sets:table+=f"<tr><td>{s['set']}</td><td>{s['cases']}</td><td>{s['code_correct']}</td><td>{s['code_incorrect']}</td><td>{s['unresolved']}</td><td>{100*s['correct_code_over_all']:.2f}%</td></tr>"
    table+=f'<tr><th>Total</th><th>{len(rows)}</th><th>{correct}</th><th>{len(wrong)}</th><th>{len(unresolved)}</th><th>{100*correct/len(rows):.2f}%</th></tr></table>'
    caveats='<ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in summary['limits'])+'</ul>'
    failures='<h2>All incorrect code interpretations</h2>'
    for r in wrong:
        failures+='<article><h3>'+html.escape(r['text'])+'</h3><pre>'+html.escape(json.dumps(r['score']['mismatches'],indent=2))+'</pre></article>'
    failures+='<h2>All '+str(len(unresolved))+' unresolved sentences</h2><p>The code recorded these reasons; they are diagnostics, not manually assigned correctness labels.</p>'
    for r in unresolved:
        failures+='<details><summary>Set '+str(r['set'])+': '+html.escape(r['text'])+'</summary><p>'+html.escape(', '.join(r['result']['code_proposal']['reasons']))+'</p><pre>'+html.escape(json.dumps(dict(expected=r['expected'],proposal=r['result']['code_proposal']),indent=2))+'</pre></details>'
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>READ '+str(len(rows))+'-case results</title><style>body{max-width:1100px;margin:30px auto;padding:20px;font:16px/1.6 system-ui;background:#112033;color:#edf3ff}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #657e97}details,article{border:1px solid #657e97;padding:12px;margin:10px 0}summary{cursor:pointer}</style>'+header+table+caveats+failures+'<h2>Machine-computed summary and checks</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></html>'
    (ROOT/f'reports/read-sets-{tag}.html').write_text(page)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
