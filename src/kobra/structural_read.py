"""Bounded imperative coordination and sentence-local references.

Inspired by UD coordination and deterministic coreference agreement constraints.
Not a full UD converter or general coreference implementation. All spans refer
only to the original text; new local IDs are descriptions, not WORLD objects.
"""
import re
from .selection_read import SLOTS

COUNTS = {w:i for i,w in enumerate(('zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve'))}
NUMBER = r'(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'
INTRO = re.compile(r'^(?:(?:good (?:morning|afternoon|evening)|hello|hi|hey)\b[^,;.!?]*[,;]?\s*)?(?:please\s+)?$',re.I)


def span(text, start, end):
    return dict(start=start,end=end,text=text[start:end])


def trim_end(text, start, end):
    # A connector belongs to the coordination, not to either argument.
    while end > start:
        m=re.search(r'(?:[\s,;.!]+|\b(?:and|then)\s*)$',text[start:end],re.I)
        if not m:break
        end=start+m.start()
    return end


def assign_structure(doc):
    text=doc.text
    roots=[t for t in doc if t.dep_=='ROOT']
    if len(roots)!=1:return None
    root=roots[0]
    if root.pos_!='VERB' or root.tag_!='VB' or text.rstrip().endswith('?'):
        return None
    if any(t.dep_ in {'nsubj','nsubjpass','csubj'} for t in root.children):return None
    if not INTRO.fullmatch(text[:root.idx]):return None
    if any(t.dep_ in {'relcl','advcl','ccomp','xcomp','neg'} or t.tag_=='MD' for t in doc):return None
    if any(t.lower_ in {'or','but','unless','if','until','before','after'} for t in doc):return None
    verbs=[root]
    for t in doc:
        if t==root or t.pos_!='VERB':continue
        parent=t.head
        while parent.dep_=='conj' and parent.pos_=='VERB':parent=parent.head
        coordinated=t.dep_=='conj' and parent==root
        # Parser sometimes marks a comma + then imperative as generic dep.
        explicit_then=t.dep_=='dep' and t.head==root and any(x.lower_=='then' for x in doc[max(root.i+1,t.i-2):t.i])
        if not (coordinated or explicit_then):return None
        if any(c.dep_ in {'nsubj','nsubjpass'} for c in t.children):return None
        verbs.append(t)
    verbs.sort(key=lambda t:t.i)
    if len(verbs)>4:return None
    chunks=[];frames=[];entities=[];references=[];issues=[];relations=[]
    rules=['C010-imperative-coordination'] if len(verbs)>1 else ['C011-structured-imperative']
    noun_chunks={c.root.i:c for c in doc.noun_chunks}
    for i,verb in enumerate(verbs):
        end=trim_end(text,verb.idx,verbs[i+1].idx if i+1<len(verbs) else len(text))
        chunk=dict(id=f'c{i+1}',kind='action',span=span(text,verb.idx,end),frame=i,modifiers=[],members=[])
        chunks.append(chunk)
        frame=dict({s:'NONE' for s in SLOTS},act='request',predicate=verb.text)
        frame_index=len(frames)
        frames.append(frame)
        body_start=verb.idx+len(verb.text)
        while body_start<end and text[body_start].isspace():body_start+=1
        body=text[body_start:end]
        enum=re.search(r'\bone\s+with\s+',body,re.I)
        patient=None;patient_start=None;patient_end=None;count=None;number=None
        if enum:
            prefix=body[:enum.start()].rstrip(' ,:')
            match=re.fullmatch(r'('+NUMBER+r')\s+([\w-]+(?:\s+[\w-]+){0,5})',prefix,re.I)
            if not match:
                issues.append(f'{chunk["id"]}:unsupported_enumeration_head');continue
            patient=prefix;patient_start=body_start;patient_end=body_start+len(prefix)
            count=int(match[1]) if match[1].isdigit() else COUNTS[match[1].lower()]
            frame['quantity']=match[1];number='plural' if count>1 else 'singular'
            tail=body[enum.start():]
            pattern=r'one\s+with\s+(.+?)(?=(?:,\s*(?:and\s+)?|\s+and\s+)one\s+with\b|$)'
            matches=list(re.finditer(pattern,tail,re.I))
            cursor=0
            for j,m in enumerate(matches):
                gap=tail[cursor:m.start()].strip(' ,')
                if gap.lower() not in ('','and'):issues.append(f'{chunk["id"]}:unparsed_enumeration')
                a=body_start+enum.start()+m.start();b=body_start+enum.start()+m.end()
                chunk['members'].append(dict(id=f'c{i+1}.member{j+1}',quantity=1,
                    span=span(text,a,b),specification=span(text,body_start+enum.start()+m.start(1),body_start+enum.start()+m.end(1))))
                cursor=m.end()
            if not matches or tail[cursor:].strip(' ,'):issues.append(f'{chunk["id"]}:unparsed_enumeration')
            if len(matches)!=count:issues.append(f'{chunk["id"]}:enumeration_count_mismatch')
            rules.append('C012-counted-member-specifications')
        else:
            objects=[t for t in verb.children if t.dep_ in {'dobj','obj'} and verb.idx<t.idx<end and t.lower_!='all']
            if len(objects)!=1:
                issues.append(f'{chunk["id"]}:missing_or_multiple_objects');continue
            obj=objects[0];np=noun_chunks.get(obj.i)
            if np is not None and np.start_char>=body_start and np.end_char<=end:
                patient=np.text;patient_start=np.start_char;patient_end=np.end_char
            elif obj.pos_=='PRON':
                patient=obj.text;patient_start=obj.idx;patient_end=obj.idx+len(obj.text)
            else:
                issues.append(f'{chunk["id"]}:unsupported_object_span');continue
            if text[body_start:patient_start].strip():issues.append(f'{chunk["id"]}:unassigned_before_object')
            nums=[t for t in obj.children if t.dep_=='nummod']
            if len(nums)==1:
                raw=nums[0].text
                count=int(raw) if raw.isdigit() else COUNTS.get(raw.lower())
                if count is None:issues.append(f'{chunk["id"]}:unsupported_number')
                frame['quantity']=raw
            quantifiers=[t for t in doc if patient_start<=t.idx<patient_end and t.lower_ in {'all','every','each','some','any','no','both','many','few'}]
            if quantifiers:
                if len(quantifiers)==1 and quantifiers[0].lower_=='all' and not nums:
                    frame['quantity']=quantifiers[0].text
                    rules.append('C015-explicit-all-quantity')
                else:
                    issues.append(f'{chunk["id"]}:unsupported_quantifier_scope')
            number='plural' if obj.tag_ in ('NNS','NNPS') or (count is not None and count>1) else 'singular'
            tail=text[patient_end:end]
            shared=re.fullmatch(r'\s+(?:(all)\s+)?(in|on)\s+(the\s+same\s+[\w-]+)\s*',tail,re.I)
            if shared:
                chunk['modifiers'].append(dict(kind='shared_location',span=span(text,patient_end,end),
                    relation=shared[2],value=shared[3],scope='all_members' if shared[1] else 'patient',status='source_constraint_not_WORLD_identity'))
                if shared[1]:frame['quantity']=shared[1]
                rules.append('C013-shared-location-constraint')
            elif tail.strip():
                chunk['modifiers'].append(dict(kind='unresolved_attachment',span=span(text,patient_end,end)))
                issues.append(f'{chunk["id"]}:unresolved_attachment')
        frame['patient']=patient
        chunk['patient_span']=span(text,patient_start,patient_end)
        if patient.lower() in ('it','them'):
            wanted='plural' if patient.lower()=='them' else 'singular'
            candidates=[e['id'] for e in entities if e['number']==wanted]
            ref=dict(frame=frame_index,slot='patient',mention=span(text,patient_start,patient_end),candidates=candidates,
                     status='resolved' if len(candidates)==1 else 'ambiguous' if candidates else 'missing_antecedent')
            if len(candidates)==1:
                ref['entity_id']=candidates[0];rules.append('C014-unique-local-number-agreement')
            else:issues.append(f'{chunk["id"]}:{ref["status"]}')
            references.append(ref)
        elif patient.lower() in ('he','she','him','her','they','this','that','these','those'):
            issues.append(f'{chunk["id"]}:unsupported_reference')
        else:
            entity=dict(id=f'e{len(entities)+1}',span=span(text,patient_start,patient_end),number=number,
                        quantity=count,introduced_in=chunk['id'],status='sentence_local_description_not_WORLD_object',
                        members=chunk['members'])
            entities.append(entity);chunk['entity_id']=entity['id']
        if i:
            gap=text[chunks[i-1]['span']['end']:verb.idx]
            relations.append(dict(from_chunk=chunks[i-1]['id'],to_chunk=chunk['id'],
                                  kind='explicit_then' if re.search(r'\bthen\b',gap,re.I) else 'coordination_source_order_only'))
    if not frames:return None
    ledger=[];cursor=0
    for chunk in chunks:
        a,b=chunk['span']['start'],chunk['span']['end']
        if a>cursor:ledger.append(dict(**span(text,cursor,a),label='greeting_or_politeness' if cursor==0 else 'connective_or_unassigned'))
        ledger.append(dict(**span(text,a,b),label='action_chunk'));cursor=b
    if cursor<len(text):ledger.append(dict(**span(text,cursor,len(text)),label='connective_or_unassigned'))
    return dict(source=text,frames=frames,route='unresolved' if issues else 'code',rules=sorted(set(rules)),
                reasons=issues,semantic_verified=False,version='rule-assignment-2',chunks=chunks,
                local_entities=entities,local_references=references,chunk_relations=relations,source_ledger=ledger)
