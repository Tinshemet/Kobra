"""Capture actual local knowledge-enabled READ examples; no live model calls."""
import hashlib
import html
import json
from pathlib import Path
from kobra.knowledge import KnowledgeSnapshot
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    live = dict(revision='example-live-1',source='explicit-example-fixture',status='current',
                entities={'vm-1':dict(name='Alpha',aliases=['lab machine','server']),
                          'vm-2':dict(name='Beta',aliases=['lab machine'])})
    row = dict(id='definition-1',word='jumpbox',type='class',kind='vm',source='told',
               status='ratified',provenance='explicit-example-fixture')
    archive = dict(revision='example-archive-1',source='explicit-example-fixture',records=[row])
    cases = [
        ('Unique live alias', 'Restart the server.', KnowledgeSnapshot(live=live), {}),
        ('Duplicate alias stays ambiguous', 'Restart the lab machine.', KnowledgeSnapshot(live=live), {}),
        ('Definition does not create an identity', 'Create a jumpbox.', KnowledgeSnapshot(archive=archive), {}),
        ('Pending definition cannot settle', 'Create a jumpbox.', KnowledgeSnapshot(archive=dict(archive,records=[dict(row,status='pending')])), {}),
        ('Stale inventory cannot bind', 'Restart the server.', KnowledgeSnapshot(live=dict(live,status='stale')), {}),
        ('Current entity outranks remembered meaning', 'Restart the server.', KnowledgeSnapshot(live=live,archive=dict(archive,records=[dict(row,word='server',holds=False)])), {}),
        ('Parser gap: name evidence survives unresolved roles', 'Restart Alpha.', KnowledgeSnapshot(live=live), {}),
        ('Previous turn retained; pronoun still unresolved', 'Restart it.', KnowledgeSnapshot(live=live), {'history':[dict(role='user',content='We are working with Alpha.')]}),
    ]
    assigner=RuleAssigner()
    traces=[]
    for title,text,knowledge,kwargs in cases:
        result=GatedRuleReader(assigner,ConfidenceGate(),knowledge=knowledge).read(text,**kwargs)
        traces.append(dict(title=title,source=text,result=result))
    assert traces[0]['result']['proposal']['groundings']=={'the server':'vm-1'}
    assert any('knowledge_ambiguous' in r for r in traces[1]['result']['reasons'])
    assert not traces[2]['result']['knowledge_evidence']['bindings']
    assert all(t['result']['route']=='ASK' for t in traces)
    assert traces[6]['result']['code_proposal']['route']=='unresolved'
    assert any(m['text']=='Alpha' for m in traces[6]['result']['knowledge_evidence']['lexical_mentions'])
    paths=['src/kobra/knowledge.py','src/kobra/knowledge_resolution.py','src/kobra/confidence_gate.py','src/kobra/rule_assignment.py','tools/export_knowledge_examples.py']
    payload=dict(kind='development examples; fixture inventories; actual local code; not accuracy',new_model_calls=0,
                 source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},examples=traces)
    out=ROOT/'evidence/knowledge-lookup-1';out.mkdir(exist_ok=True)
    (out/'examples.json').write_text(json.dumps(payload,indent=2)+'\n')
    body=''.join('<article><h2>'+html.escape(t['title'])+'</h2><p>'+html.escape(t['source'])+'</p><p>Gate: '+html.escape(', '.join(t['result']['reasons']))+'</p><details><summary>Complete actual output</summary><pre>'+html.escape(json.dumps(t['result'],indent=2))+'</pre></details></article>' for t in traces)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>READ: library and archive lookup</title><style>body{max-width:1000px;margin:40px auto;padding:20px;background:#101b2c;color:#edf3ff;font:17px/1.6 system-ui}article{border:1px solid #50647c;padding:20px;margin:20px 0;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}summary{cursor:pointer}</style><h1>READ: active library and archive</h1><p>Actual local outputs using explicit fixture inventories. No live AI calls or accuracy measurement. Every example ends in ASK because no real calibration is installed; additional lookup problems are shown separately.</p><p>Library = current objects. Archive = learned definitions. Ledger = prior statements. A definition never manufactures an object.</p><p>This addition does not implement remote refresh, persistent archive storage, general group relations or conversational reference resolution.</p>'''+body+'</html>'
    (ROOT/'reports/read-knowledge-current.html').write_text(page)
    print(json.dumps(dict(examples=len(traces),new_model_calls=0,output='reports/read-knowledge-current.html')))

if __name__=='__main__': main()
