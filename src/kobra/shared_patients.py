"""Declared shared-patient command patterns, not inferred universal verb valency."""
import re

DEFAULT_PATTERNS = (
    ('create', 'launch'), ('create', 'configure'), ('create', 'configure', 'launch'),
    ('create', 'delete'), ('download', 'install'), ('open', 'read'), ('open', 'close'),
    ('read', 'print'), ('inspect', 'repair'), ('configure', 'launch'), ('print', 'archive'),
)
CREATION_ACTIONS = frozenset({'create', 'provision', 'clone', 'copy'})


def validate_patterns(patterns):
    patterns = tuple(patterns)
    if any(isinstance(p, (str, bytes)) for p in patterns):
        raise ValueError('each shared-patient pattern must be a sequence of words')
    result = tuple(tuple(p) for p in patterns)
    if any(not 2 <= len(p) <= 4 or any(not isinstance(v, str) or not re.fullmatch(r'[a-z]+', v) for v in p) for p in result):
        raise ValueError('shared-patient patterns require two to four lowercase action words')
    return result


def share_patients(text, boundaries, chunks, frames, entities, patterns):
    """Link bare predicates to one final simple NP, retaining external span edges."""
    links, issues = [], []
    pending = []
    for i, boundary in enumerate(boundaries['chunks']):
        if boundary.get('argument_omitted'):
            pending.append(i)
            continue
        if not pending:
            continue
        indexes = pending + [i]
        pending = []
        verbs = tuple(frames[j]['predicate'].casefold() for j in indexes)
        gaps = [text[chunks[a]['span']['end']:chunks[b]['span']['start']].strip() for a,b in zip(indexes,indexes[1:])]
        # Commas can enumerate earlier bare predicates, but final explicit and
        # is required. Semicolons, then alone, and alternative scopes abstain.
        connectors = all(re.fullmatch(r',|,?\s*and(?:\s+then)?(?:\s+please)?', gap, re.I) for gap in gaps)
        final_and = bool(re.fullmatch(r',?\s*and(?:\s+then)?(?:\s+please)?', gaps[-1], re.I))
        donor = chunks[i]
        entity = next((e for e in entities if e['id'] == donor.get('entity_id')), None)
        patient = frames[i]['patient']
        if (verbs not in patterns or not connectors or not final_and or entity is None
                or patient in ('NONE','UNKNOWN','MISSING') or donor['members'] or donor['modifiers']
                or frames[i]['recipient'] != 'NONE' or 'patient_span' not in donor):
            issues.append(f'{chunks[indexes[0]]["id"]}:unsupported_shared_patient')
            continue
        entity['introduced_in'] = chunks[indexes[0]]['id']
        entity['shared_by'] = [chunks[j]['id'] for j in indexes]
        entity['created_by'] = [chunks[j]['id'] for j in indexes if frames[j]['predicate'].casefold() in CREATION_ACTIONS]
        for j in indexes[:-1]:
            frames[j]['patient'] = patient
            frames[j]['quantity'] = frames[i]['quantity']
            chunks[j]['patient_span'] = dict(donor['patient_span'])
            chunks[j]['entity_id'] = entity['id']
            links.append(dict(frame=j, slot='patient', from_chunk=chunks[j]['id'],
                              donor_chunk=donor['id'], span=dict(donor['patient_span']),
                              entity_id=entity['id'], rule='C016-trailing-shared-patient'))
    if pending:
        issues.append('missing_shared_patient_donor')
    return links, issues
