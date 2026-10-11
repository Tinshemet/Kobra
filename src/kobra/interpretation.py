"""READ owns grammatical features and unresolved source accounting."""
import re
from .selection_read import SLOTS, SPECIAL

VERSION='read-interpretation-1'
CALIBRATION_REASONS={'uncalibrated_cohort','insufficient_calibration_cases','below_external_threshold','invalid_calibration'}

def clause_grammar(doc, root, frame, passive):
    aux=[t for t in doc if t.pos_=='AUX' or t.dep_ in {'aux','auxpass'}]
    future=any(t.lower_ in {'will','shall'} for t in aux)
    finite=[t for t in aux if t.tag_ in {'VBD','VBZ','VBP'}]
    tense=('not_applicable' if frame['act']=='request' else 'future' if future else
           'past' if any(t.tag_=='VBD' for t in finite or [root]) else
           'present' if any(t.tag_ in {'VBZ','VBP'} for t in finite or [root]) else 'unspecified')
    perfect=any(t.lemma_=='have' for t in aux)
    progressive=any(t.lemma_=='be' for t in aux) and (root.tag_=='VBG' or any(t.lower_=='being' for t in aux))
    markers=aux+[t for t in doc if passive and t.dep_=='agent' and t.lower_=='by']
    return dict(tense=tense,aspect='perfect_progressive' if perfect and progressive else 'perfect' if perfect else 'progressive' if progressive else 'simple',
        voice='passive' if passive else 'active',polarity='negative' if frame['negation']!='NONE' else 'positive',
        markers=[dict(start=t.idx,end=t.idx+len(t.text),text=t.text) for t in markers])

def audit_source(text, code):
    spans=[]
    for frame in code.get('frames',[]):
        if not isinstance(frame,dict):continue
        for slot in SLOTS:
            value=frame.get(slot)
            if isinstance(value,str) and value and value not in SPECIAL:
                spans.extend((m.start(),m.end(),'role:'+slot) for m in re.finditer(r'(?<!\w)'+re.escape(value)+r'(?!\w)',text))
    for grammar in code.get('clause_grammar',[]):
        spans.extend((s['start'],s['end'],'grammar_marker') for s in grammar['markers'])
    def add_spans(value):
        if isinstance(value,dict):
            if {'start','end','text'}<=value.keys() and text[value['start']:value['end']]==value['text']:
                spans.append((value['start'],value['end'],'structural_detail'))
            else:
                for v in value.values():add_spans(v)
        elif isinstance(value,list):
            for v in value:add_spans(v)
    for chunk in code.get('chunks',[]):
        add_spans(chunk.get('members',[]));add_spans(chunk.get('modifiers',[]))
        members=chunk.get('members',[])
        for first,second in zip(members,members[1:]):
            a,b=first['span']['end'],second['span']['start']
            if re.fullmatch(r'[\s,]*(?:and)?[\s,]*',text[a:b],re.I):spans.append((a,b,'enumeration_connector'))
    # Connector text only has a known role when code produced structural links.
    if code.get('chunk_relations'):
        for part in code.get('source_ledger',[]):
            if re.fullmatch(r'[\s,;]*(?:and(?:\s+then)?|then)?[\s,;.!?]*',part['text'],re.I):
                spans.append((part['start'],part['end'],'connector'))
    social=re.match(r'\s*(?:(?:hello|hi|hey|good morning|good afternoon|good evening)(?:\s+[\w-]+)?[,;]\s*)?(?:please\s+)?',text,re.I)
    if social and social.end():spans.append((0,social.end(),'social_or_politeness'))
    tokens=[];unassigned=[]
    for m in re.finditer(r"\w+(?:['’-]\w+)*|[^\w\s]",text):
        labels=sorted({label for a,b,label in spans if a<=m.start() and m.end()<=b})
        if not labels and re.fullmatch(r'[.,;:!?]',m.group()):labels=['punctuation']
        item=dict(start=m.start(),end=m.end(),text=m.group(),roles=labels)
        tokens.append(item)
        if not labels:unassigned.append(item)
    supported=code.get('route')=='code' and bool(code.get('frames')) and not unassigned
    return dict(version=VERSION,status='supported' if supported else 'unresolved',tokens=tokens,
        unassigned=unassigned,reasons=['uninterpreted_source_material'] if unassigned else [],
        scope='bounded code grammar and explicit semantic roles; not universal entailment proof')
