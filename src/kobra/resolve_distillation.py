"""Deterministic READ-to-RESOLVE projection, not an answer or semantic rewriter.

The gated READ result is the input contract. Source wording remains necessary:
current role slots do not separately encode every linguistic distinction.
"""
from copy import deepcopy
import hashlib
import json
from .selection_read import ACTS, SLOTS, SPECIAL

VERSION = 'resolve-distillation-2'
ARGUMENTS = ('agent', 'patient', 'recipient')
QUALIFIERS = tuple(s for s in SLOTS if s not in ('predicate', *ARGUMENTS))


def distill_for_resolve(result, *, metadata=None, annotations=()):
    """Return a detached, JSON-compatible handoff; never upgrade gate authority."""
    source = result.get('source')
    if not isinstance(source, str):
        raise ValueError('distillation requires the exact READ source')
    proposal = result.get('proposal')
    proposal = proposal if isinstance(proposal, dict) else {}
    frames = proposal.get('frames', [])
    diagnostics = []
    if not isinstance(frames, list) or any(
        not isinstance(f, dict) or set(f) != {'act', *SLOTS} or f['act'] not in ACTS
        or any(not isinstance(f[s], str) or not f[s] or
               (f[s] not in SPECIAL and f[s] not in source) for s in SLOTS) for f in frames):
        frames = []
        diagnostics.append('invalid_upstream_frames')
    code = result.get('code_proposal', {})
    use_code_structure = result.get('assignment_source') == 'code'
    chunks = code.get('chunks', []) if use_code_structure else []
    by_frame = {}
    for chunk in chunks:
        i = chunk.get('frame')
        if type(i) is not int or not 0 <= i < len(frames) or i in by_frame:
            diagnostics.append('invalid_chunk_frame_mapping')
            continue
        by_frame[i] = chunk

    def span(raw):
        a, b = raw.get('start'), raw.get('end')
        if (type(a) is not int or type(b) is not int or not 0 <= a < b <= len(source)
                or raw.get('text') != source[a:b]):
            raise ValueError('distillation evidence must match the original source')
        return dict(source_id='request', start=a, end=b, text=source[a:b])

    points, covered = [], []
    local_refs = code.get('local_references', []) if use_code_structure else []
    shared = code.get('shared_arguments', []) if use_code_structure else []
    groundings = proposal.get('groundings', {})
    groundings = groundings if isinstance(groundings, dict) else {}
    prior = result.get('context_ledger', {})
    world_ids = {e['id'] for e in prior.get('world_entities', [])}
    memory = result.get('memory_evidence', {})
    knowledge = result.get('knowledge_evidence', {})
    deterministic_evidence = memory.get('bindings', []) + knowledge.get('bindings', []) + knowledge.get('model_bindings', [])
    for i, frame in enumerate(frames):
        chunk = by_frame.get(i)
        raw = chunk['span'] if chunk else dict(start=0, end=len(source), text=source)
        main = span(raw)
        covered.append((main['start'], main['end']))
        evidence = [main]
        point_shared = [deepcopy(r) for r in shared if r.get('frame') == i]
        for r in point_shared:
            support = span(r['span'])
            if support not in evidence:
                evidence.append(support)
        arguments = {s: frame[s] for s in ARGUMENTS if frame[s] != 'NONE'}
        qualifiers = {s: frame[s] for s in QUALIFIERS if frame[s] != 'NONE'}
        bindings = []
        for slot, mention in arguments.items():
            if mention not in groundings:
                continue
            identifier = groundings[mention]
            proof = [deepcopy(b) for b in deterministic_evidence
                     if b.get('frame') == i and b.get('slot') == slot
                     and b.get('mention') == mention and b.get('entity_id') == identifier]
            if identifier not in world_ids or not proof:
                diagnostics.append('unsupported_grounding:' + mention)
                continue
            bindings.append(dict(slot=slot, mention=mention, entity_id=identifier,
                                 namespace='WORLD', evidence=proof))
        # A role-labelled rendering avoids conjugating away tense or changing a
        # question into an assertion. Exact source wording accompanies each point.
        rendered = dict(predicate=frame['predicate'], **arguments, **qualifiers)
        summary = frame['act'].capitalize() + ': ' + '; '.join(
            k + '=' + json.dumps(v, ensure_ascii=False) for k, v in rendered.items())
        points.append(dict(id=f'p{i+1}', act=frame['act'], predicate=frame['predicate'],
            arguments=arguments, qualifiers=qualifiers, summary=summary,
            source_text=main['text'], evidence=evidence,
            identity_bindings=bindings,
            local_references=[deepcopy(r) for r in local_refs if r.get('frame') == i],
            shared_arguments=point_shared,
            members=deepcopy(chunk.get('members', [])) if chunk else [],
            modifiers=deepcopy(chunk.get('modifiers', [])) if chunk else [],
            uncertainty=list(result.get('reasons', []))))
    # Retain every source character, including greetings, connectors and text
    # outside supported frames. Unassigned text is never classified as garbage.
    cursor = 0
    remainder = []
    for a,b in sorted(covered):
        if a > cursor:
            remainder.append(span(dict(start=cursor,end=a,text=source[cursor:a])))
        cursor = max(cursor,b)
    if cursor < len(source):
        remainder.append(span(dict(start=cursor,end=len(source),text=source[cursor:])))
    chunk_ids = {c['id']: f'p{i+1}' for i,c in by_frame.items()}
    relations = []
    for relation in code.get('chunk_relations', []) if use_code_structure else []:
        if relation.get('from_chunk') not in chunk_ids or relation.get('to_chunk') not in chunk_ids:
            diagnostics.append('unmapped_chunk_relation')
            continue
        relations.append(dict(from_point=chunk_ids[relation['from_chunk']],
            to_point=chunk_ids[relation['to_chunk']], relationship=relation['kind'], evidence=deepcopy(relation)))
    reasons = list(result.get('reasons', []))
    from .distillation_metadata import describe_text
    metadata, text_accounting = describe_text(source, points, relations, result, metadata, annotations)
    metadata['distillation_version'] = VERSION
    return dict(version=VERSION, metadata=metadata, text_accounting=text_accounting,
        source=dict(id='request',text=source,sha256=hashlib.sha256(source.encode()).hexdigest()),
        points=points, relations=relations,
        local_entities=deepcopy(code.get('local_entities', [])) if use_code_structure else [],
        retained_remainder=remainder,
        state=dict(read_route=result.get('route'),assignment_source=result.get('assignment_source'),
            ready_for_resolve=result.get('route')=='ACCEPT' and bool(points) and not diagnostics,
            reasons=reasons,distillation_diagnostics=sorted(set(diagnostics)),
            external_score=result.get('external_score'),score_kind=result.get('score_kind'),
            cohort=result.get('cohort'),semantic_reverified=False),
        memory_context=deepcopy(prior),
        grounding_evidence=deepcopy(dict(memory=memory,knowledge=knowledge)),
        rules=deepcopy(code.get('rules', [])),
        semantics='Source-backed READ proposal for RESOLVE; not a verified fact, answer, execution plan or authorization.')
