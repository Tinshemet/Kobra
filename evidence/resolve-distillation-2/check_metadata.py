from pathlib import Path
import gzip,json,hashlib,html
from kobra.resolve_distillation import distill_for_resolve
from kobra.confidence_gate import GatedRuleReader,ConfidenceGate
from kobra.rule_assignment import RuleAssigner
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
old=ROOT/'evidence/resolve-distillation-1/captures.jsonl.gz';count=0
with gzip.open(old,'rt') as f:
 for line in f:
    row=json.loads(line);prior=row['distillation'];current=distill_for_resolve(row['read'])
    for key in prior:
        if key!='version':assert current[key]==prior[key],(row['id'],key)
    parts=current['text_accounting']['partition']
    assert ''.join(p['text'] for p in parts)==row['text']
    assert all(a['end']==b['start'] for a,b in zip(parts,parts[1:]))
    assert current['metadata']['accounted_characters']==len(row['text'])
    assert current['metadata']['discarded_characters']==0
    assert not current['text_accounting']['garbage']
    count+=1
reader=GatedRuleReader(RuleAssigner(),ConfidenceGate())
examples=[reader.read_for_resolve('Open and read the file.',metadata=dict(request_id='example-1',channel='text',language='en')),
 reader.read_for_resolve('Move it.',missing_context=['target'],metadata=dict(request_id='example-2')),
 reader.read_for_resolve('If the server fails, restart it.')]
text='[transport-marker] Open the file.'
examples.append(reader.read_for_resolve(text,annotations=[dict(start=0,end=18,text=text[:18],category='garbage',reason='fixture transport marker, retained verbatim',provenance='caller-fixture')]))
(OUT/'examples.json').write_text(json.dumps(examples,indent=2)+'\n')
summary=dict(reused_handoffs_checked=count,existing_points_bindings_and_gate_unchanged=count,exact_source_partition_checks=count,discarded_characters=0,
    garbage_policy='Only explicit caller annotations, retained and unverified; unknown text is not automatically garbage.',
    baseline_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/kobra').glob('*.py')})
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
e=html.escape
body='<h1>Distillation metadata and retained text</h1><p>Version 2 adds metadata, a complete source partition, annotation buckets and categorized open issues. No text is discarded. Existing points, bindings and gate outcomes are unchanged across 5,000 saved handoffs.</p><p>Garbage/noise/social labels may be supplied as exact caller annotations; they are not semantically verified and cannot override the interpretation. Unclassified text remains available for later turns. Evidence coverage does not mean every word was understood.</p>'
for d in examples:
 body+='<h2>'+e(d['source']['text'])+'</h2><pre>'+e(json.dumps({k:d[k] for k in ('metadata','text_accounting','state')},indent=2))+'</pre>'
page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Distillation metadata</title><style>body{max-width:1050px;margin:30px auto;padding:20px;background:#112033;color:#edf3ff;font:16px/1.6 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}</style>'+body+'</html>'
(ROOT/'reports/read-distillation-metadata.html').write_text(page)
print(json.dumps({k:v for k,v in summary.items() if k!='source_hashes'},indent=2))
