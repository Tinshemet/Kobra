"""Bounded role repairs for observed question parses; source text is never rewritten."""


def passive_question_subject(doc, auxiliary, noun_chunks):
    """Recognize BE + NP + [not] + VBN + by + NP + ? despite bounded acl or attr attachment errors.

    Returns the lexical predicate and grammatical subject only when every segment
    fits this shape. Does not promote general relative clauses or answer questions.
    """
    text=doc.text
    if auxiliary.i != 0 or auxiliary.lemma_ != 'be' or not text.rstrip().endswith('?'):
        return None
    subjects=[t for t in auxiliary.children if t.dep_ in {'nsubj','nsubjpass'}]
    lexical=[t for t in doc if t.pos_=='VERB' and t!=auxiliary]
    if len(lexical)!=1:
        return None
    predicate=lexical[0]
    if predicate.tag_!='VBN':
        return None
    if len(subjects)==1 and predicate.dep_=='acl' and predicate.head==subjects[0]:
        subject=subjects[0]
        patient=noun_chunks.get(subject.i)
    elif not subjects and predicate.dep_=='attr' and predicate.head==auxiliary:
        # Another observed parser error: determiner + noun is absorbed into
        # the participle, with the noun mislabeled amod and no noun chunk.
        # Recover only that complete two-token NP, never an arbitrary prefix.
        end=predicate.i
        if end>auxiliary.i+1 and doc[end-1].lower_=='not':
            end-=1
        patient=doc[auxiliary.i+1:end]
        if len(patient)!=2:
            return None
        determiner,subject=patient
        if (determiner.lower_ not in {'a','an','the'} or determiner.pos_!='DET'
                or determiner.dep_!='det' or determiner.head!=subject
                or subject.pos_!='NOUN' or subject.dep_!='amod' or subject.head!=predicate
                or list(subject.children)!=[determiner]):
            return None
    else:
        return None
    agents=[t for t in predicate.children if t.dep_=='agent' and t.lower_=='by']
    if len(agents)!=1:
        return None
    by=agents[0];actors=[t for t in by.children if t.dep_=='pobj']
    if len(actors)!=1:
        return None
    actor=noun_chunks.get(actors[0].i)
    if patient is None or actor is None:
        return None
    if not (auxiliary.idx+len(auxiliary.text) <= patient.start_char < patient.end_char <= predicate.idx
            < by.idx < actor.start_char < actor.end_char):
        return None
    gaps=[text[auxiliary.idx+len(auxiliary.text):patient.start_char],
          text[predicate.idx+len(predicate.text):by.idx],text[by.idx+len(by.text):actor.start_char]]
    if any(gap.strip() for gap in gaps):
        return None
    if text[patient.end_char:predicate.idx].strip().casefold() not in ('','not'):
        return None
    if text[actor.end_char:].strip()!='?':
        return None
    return predicate,subject,patient


DOUBLE_OBJECT_VERBS = frozenset({'give','show','send','hand','lend','offer','teach','tell'})


def double_object_roles(doc, root, subjects, objects, recipients, noun_chunks):
    """Repair two dobj labels for a declared dative-alternation verb.

    Require an overt subject followed by verb, recipient NP, then patient NP,
    with complete contiguous phrases and no intervening material.
    """
    if root.lemma_ not in DOUBLE_OBJECT_VERBS or len(subjects)!=1 or len(objects)!=2 or recipients:
        return None
    if any(c.dep_ in {'auxpass','agent'} for c in root.children):
        return None
    first,last=sorted(objects,key=lambda t:t.idx)
    a=noun_chunks.get(first.i);b=noun_chunks.get(last.i)
    if a is None or b is None or not subjects[0].idx < root.idx < a.start_char < a.end_char <= b.start_char:
        return None
    if doc.text[root.idx+len(root.text):a.start_char].strip() or doc.text[a.end_char:b.start_char].strip():
        return None
    return [last],[first]
