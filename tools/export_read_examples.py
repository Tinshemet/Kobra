"""Capture real local READ traces and embed them in the offline pipeline HTML.

No model calls. One resolver is a deliberately invalid scripted test fixture.
"""
import hashlib
import json
from pathlib import Path
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from kobra.selection_read import SLOTS

ROOT = Path(__file__).resolve().parents[1]


def main():
    assigner = RuleAssigner()
    examples = [
        dict(title='Service request: cancel a subscription', text='Cancel the subscription.',
             explanation='Code identifies a request to cancel the subscription. No AI is called. The actual final route is ASK only because this code cohort has no held-out calibration; it is not missing the subscription phrase.'),
        dict(title='Passive voice: Alex carries the books', text='Will the books be carried by Alex?',
             explanation='The passive rule assigns Alex as agent and the books as patient. No AI is called. This fixes the role reversal shown earlier, but the current gate still requires calibration.'),
        dict(title='Pronoun without context: “it” is unresolved', text='Move it.',
             explanation='Code can assign “it” to the patient slot without knowing its identity. The gate detects the missing binding. No AI is called because code did not abstain; automatic retry through AI after gate rejection is not implemented.'),
        dict(title='Pronoun with prior context: what is retained?', text='Move it.',
             history=[dict(id='u1',role='user',content='We are discussing the blue box.')],
             world={'box-1':{'name':'blue box'}},
             explanation='The ledger preserves the prior turn and box-1, including the exact mention span. The code does not automatically bind “it” to box-1. The gate still reports an ungrounded reference. Having context available is not the same as using it correctly.'),
        dict(title='Provisioning: code abstains, no AI connected', text='Create three Debian VMs with 16 GB of RAM each.',
             explanation='The current rules abstain on the prepositional attachment. A resolver would be called here if supplied. This trace supplies none, so it ends at ASK with no valid frames. The complete instruction survives.'),
        dict(title='Model branch: reject a nonexistent WORLD reference', text='Refund the order if it was cancelled.',
             scripted=True, world={'order-1':{'name':'order'}},
             explanation='Code abstains on the conditional clause. A scripted resolver returns a source-based frame but cites order-ghost, which is absent from supplied WORLD. The real gate rejects it. This illustrates the model interface and validation; it is not a live AI answer or a model-accuracy result.'),
    ]
    traces=[]
    for e in examples:
        calls=[]
        def fixture(payload):
            calls.append(payload)
            frame=dict({s:'NONE' for s in SLOTS},act='request',predicate='Refund',patient='the order',condition='if it was cancelled')
            return {'frames':[frame],'world_references':['order-ghost'],'confidence':1.0}
        result=GatedRuleReader(assigner, ConfidenceGate(), fixture if e.get('scripted') else None).read(
            e['text'], history=e.get('history',()),world=e.get('world',{}))
        code=result['code_proposal']
        parser=[dict(text=t.text,pos=t.pos_,dependency=t.dep_,head=t.head.text) for t in assigner.nlp(e['text'])]
        context_input=dict(source=e['text'],history=e.get('history',[]),world=e.get('world',{}))
        ledger=result['context_ledger']
        gate_input=dict(source=e['text'],proposal=result['proposal'],cohort=result['cohort'],world_ids=list(e.get('world',{})),missing_context=[],calibration_registry={})
        ai_state='Scripted resolver called — no live AI' if calls else 'AI skipped: code assigned roles' if code['route']=='code' else 'AI unavailable: no resolver supplied'
        traces.append(dict(title=e['title'],source=e['text'],explanation=e['explanation'],ai_state=ai_state,
            steps=[
                dict(title='1 · Receive the source and supplied context',input=context_input,output=ledger,passes='The original sentence goes to the assigner. A preserved context snapshot is retained; copied context is available if the resolver is needed.'),
                dict(title='2 · Dependency parser proposes syntax',input={'text':e['text']},output=parser,passes='Token text, part-of-speech tags and dependency relations are used internally by the role rules. This parser is a learned model, distinct from a generative AI resolver.'),
                dict(title='3 · Code constructs the interpretation',input={'syntax':'Exact token records shown in stage 2'},output=code,passes='If route=code, frames go directly to the gate and bypass the resolver. If route=unresolved, the original text and proposal may be sent to a resolver.'),
                dict(title='4 · Optional AI / resolver branch',input=calls[0] if calls else {'called':False,'reason':ai_state},output=result['proposal'] if calls else {'called':False},passes='A called resolver returns an untrusted proposal. No resolver confidence is used by the external gate. When skipped, the gate receives the code proposal.'),
                dict(title='5 · External validation and confidence',input=gate_input,output={k:result[k] for k in ('route','reasons','external_score','score_kind','calibration_evidence','model_self_confidence_used')},passes='The gate emits ACCEPT or ASK with reasons. There is no installed calibration for these examples; external_score remains null.'),
                dict(title='6 · Final READ product',input={'gate_route':result['route'],'assignment_source':result['assignment_source']},output=result,passes='This record is returned to the caller. It does not execute cancellation, refunds, movement or provisioning, and does not itself ask a conversational question.')
            ]))
    evidence=ROOT/'evidence/read-pipeline-examples'
    evidence.mkdir(exist_ok=True)
    payload=dict(kind='development walkthrough; no accuracy measurement',new_model_calls=0,scripted_resolver_calls=1,
                 source_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['src/kobra/rule_assignment.py','src/kobra/confidence_gate.py','src/kobra/context_ledger.py']},examples=traces)
    (evidence/'traces.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    (evidence/'inputs.json').write_text(json.dumps([{'id':str(i),'text':e['text']} for i,e in enumerate(examples,1)],indent=2)+'\n')
    page=ROOT/'reports/read-pipeline-current.html'
    text=page.read_text()
    start='<!-- WORKED-EXAMPLES-START -->';end='<!-- WORKED-EXAMPLES-END -->'
    if start in text:text=text[:text.index(start)]+text[text.index(end)+len(end):]
    section='''<!-- WORKED-EXAMPLES-START -->
<section id="worked-examples"><h2>Watch a sentence move through READ</h2>
<p>These six traces were run through the current local code. Every stage shows its input, output and handoff. No live generative AI was called. The last trace uses an explicitly scripted invalid response to demonstrate the resolver branch.</p>
<p class="note"><b>Why do all these real traces end in ASK?</b> No external calibration is installed yet. Even a correct code interpretation cannot currently receive ACCEPT. Some examples also fail grounding or structural checks. The page shows the actual result rather than silently adding artificial confidence.</p>
<label for="example-select">Choose an example</label><select id="example-select" style="display:block;width:100%;padding:14px;margin:12px 0;background:#1e3149;color:#e9eff8;border:1px solid #67849e;border-radius:8px;font:inherit"></select>
<div id="example-intro" class="detail" aria-live="polite"></div><div id="example-trace"></div>
<details><summary>What would ACCEPT return once there is sufficient real calibration?</summary><p>This is an illustrative shape, not an observed acceptance or a claim of calibrated accuracy. For the cancellation example, the same code-generated frame would be retained; route would be ACCEPT only if the checks pass and independent held-out evidence supports it. No generative AI would be needed.</p><pre>{
  "route": "ACCEPT",
  "assignment_source": "code",
  "proposal": {"frames": [{"act": "request", "predicate": "Cancel", "patient": "the subscription", "...": "remaining actual fields"}]},
  "external_score": "computed from real held-out evidence — not supplied here",
  "context_ledger": "the retained context snapshot"
}</pre></details>
</section>
<script type="application/json" id="read-examples-data">PAYLOAD</script>
<script>
const examplesData=JSON.parse(document.getElementById('read-examples-data').textContent);
const exampleSelect=document.getElementById('example-select');
examplesData.examples.forEach((e,i)=>{const option=document.createElement('option');option.value=i;option.textContent=e.title;exampleSelect.append(option)});
function renderExample(){const e=examplesData.examples[Number(exampleSelect.value)],intro=document.getElementById('example-intro'),trace=document.getElementById('example-trace');intro.replaceChildren();trace.replaceChildren();const title=document.createElement('h3');title.textContent='Input: “'+e.source+'”';const badge=document.createElement('span');badge.className='badge';badge.textContent=e.ai_state;const explanation=document.createElement('p');explanation.textContent=e.explanation;intro.append(title,badge,explanation);
for(const step of e.steps){const card=document.createElement('article');card.className='detail';card.style.marginTop='16px';const h=document.createElement('h3');h.textContent=step.title;card.append(h);const columns=document.createElement('div');columns.className='cols';for(const [label,value] of [['Receives',step.input],['Produces',step.output]]){const col=document.createElement('div'),heading=document.createElement('h4'),pre=document.createElement('pre');heading.textContent=label;pre.textContent=JSON.stringify(value,null,2);pre.style.maxHeight='400px';pre.style.overflow='auto';col.append(heading,pre);columns.append(col)}const handoff=document.createElement('p');handoff.textContent='Next handoff: '+step.passes;card.append(columns,handoff);trace.append(card)}}
exampleSelect.addEventListener('change',renderExample);renderExample();
</script>
<!-- WORKED-EXAMPLES-END -->'''
    section=section.replace('PAYLOAD',json.dumps(payload,ensure_ascii=False).replace('<','\\u003c'))
    text=text.replace('<h2>Explore the flow</h2>',section+'\n<h2>Explore the flow</h2>',1)
    page.write_text(text)
    assert all(e['steps'][-1]['output']['route']=='ASK' for e in traces)
    assert traces[1]['steps'][2]['output']['frames'][0]['agent']=='Alex'
    assert not traces[3]['steps'][3]['input']['called']
    assert 'nonexistent_world_reference' in traces[-1]['steps'][-1]['output']['reasons']
    print(json.dumps({'examples':len(traces),'live_model_calls':0,'scripted_resolver_calls':1,'output':str(page)},indent=2))

if __name__=='__main__':main()
