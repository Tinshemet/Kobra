"""Deterministic, source-only command boundaries; no NLP/model dependency.

This is a finite imperative grammar, not a general English tokenizer/parser.
Quoted/bracketed regions are protected data. Action vocabulary is explicit.
"""
import re

VERSION = 'surface-chunks-2'
ACTIONS = frozenset('archive attach cancel carry change check close configure connect copy create delete disable disconnect download draft enable export give inspect install launch list move open print read refund remove rename repair repeat restart restore run save schedule send set show sort start stop update upload verify'.split())
WORD = re.compile(r"[\w]+(?:[-'’][\w]+)*", re.UNICODE)
INTRO = re.compile(r'\s*(?:(?:good (?:morning|afternoon|evening)|hello|hi|hey)\b[^,;.!?]*[,;]\s*)?(?:please\s+)?', re.I)
SEPARATOR = re.compile(r'[,;]|\band\b(?:\s+then\b)?|\bthen\b', re.I)
SCOPE = frozenset("if unless until before after while when because although or but not never cannot don't do couldn't can't may might must should would could will shall".split())


def protected_regions(text):
    stack=[]; regions=[]; problems=[]; start=None; quote=None; escaped=False
    pairs={'(':')','[':']','{':'}'}
    quotes={'"':'"',"'":"'",'“':'”','‘':'’','`':'`'}
    for i,ch in enumerate(text):
        if quote:
            if escaped:escaped=False;continue
            if ch=='\\':escaped=True;continue
            if ch==quote:
                quote=None
                if not stack:regions.append((start,i+1));start=None
            continue
        # Apostrophes inside a word are not quotation delimiters.
        if ch in ("'",'’') and i and i+1<len(text) and text[i-1].isalnum() and text[i+1].isalnum():continue
        if ch in quotes:
            if start is None:start=i
            quote=quotes[ch]
        elif ch in pairs:
            if start is None:start=i
            stack.append(pairs[ch])
        elif ch in ')]}':
            if not stack or stack[-1]!=ch:problems.append('unmatched_bracket')
            else:
                stack.pop()
                if not stack:regions.append((start,i+1));start=None
    if start is not None:
        regions.append((start,len(text)));problems.append('unclosed_quote_or_bracket')
    return regions,problems


def chunk_commands(text, action_words=ACTIONS):
    words=frozenset(action_words)
    if any(not isinstance(w,str) or not WORD.fullmatch(w) or w!=w.lower() for w in words):
        raise ValueError('action words must be lowercase lexical forms')
    regions,issues=protected_regions(text)
    def protected(pos):return any(a<=pos<b for a,b in regions)
    prefix=INTRO.match(text).end()
    first=WORD.match(text,prefix)
    starts=[];separators=[]
    if first and first[0].lower() in words:
        starts.append((first.start(),first.end()))
    else:issues.append('unsupported_initial_action')
    for m in WORD.finditer(text):
        if not protected(m.start()) and m[0].lower() in SCOPE:
            issues.append('scope_requires_separate_analysis')
    for m in re.finditer(r'[.!?]',text):
        if not protected(m.start()) and text[m.end():].strip():
            issues.append('multiple_sentences_or_literal_punctuation')
    if starts:
        consumed=-1
        for m in SEPARATOR.finditer(text,first.end()):
            if m.start()<consumed or protected(m.start()):continue
            pos=m.end()
            while pos<len(text) and text[pos].isspace():pos+=1
            # A comma followed by and/then belongs to one connector.
            link=re.match(r'(?:and\s+)?then\s+|and\s+',text[pos:],re.I)
            if link:pos+=link.end()
            polite=re.match(r'please\s+',text[pos:],re.I)
            if polite:pos+=polite.end()
            next_word=WORD.match(text,pos)
            if next_word and not protected(pos) and next_word[0].lower() in words:
                starts.append((pos,next_word.end()));separators.append((m.start(),pos));consumed=next_word.end()
            elif m[0]==';':issues.append('unsupported_action_after_semicolon')
    if len(starts)>4:issues.append('too_many_actions')
    chunks=[];ledger=[];cursor=0
    for i,(a,predicate_end) in enumerate(starts):
        b=separators[i][0] if i<len(separators) else len(text)
        while b>a and (text[b-1].isspace() or text[b-1] in '.!?'):b-=1
        if b<=predicate_end and i == len(starts)-1:issues.append('missing_action_content')
        if a>cursor:ledger.append(dict(start=cursor,end=a,text=text[cursor:a],label='prefix' if cursor==0 else 'connector'))
        chunks.append(dict(id=f'c{i+1}',start=a,end=b,text=text[a:b],argument_omitted=b<=predicate_end,predicate=dict(start=a,end=predicate_end,text=text[a:predicate_end])))
        ledger.append(dict(start=a,end=b,text=text[a:b],label='chunk'));cursor=b
    if cursor<len(text):ledger.append(dict(start=cursor,end=len(text),text=text[cursor:],label='unassigned' if not chunks else 'suffix'))
    return dict(version=VERSION,method='deterministic_surface_rules',status='unresolved' if issues else 'supported',
                chunks=chunks,issues=sorted(set(issues)),protected_spans=[dict(start=a,end=b,text=text[a:b]) for a,b in regions],source_ledger=ledger)
