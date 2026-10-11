"""Read-only knowledge lookup; lexical definitions never become WORLD identities."""
from copy import deepcopy
import hashlib
import json
import re

VERSION = 'knowledge-resolution-2'


def created_patient_frames(code):
    """Only call with trusted code output, never an AI proposal."""
    created = {e['id'] for e in code.get('local_entities', []) if e.get('created_by')}
    frames = {c['frame'] for c in code.get('chunks', []) if c.get('entity_id') in created}
    frames.update(r['frame'] for r in code.get('local_references', [])
                  if r.get('entity_id') in created and r.get('slot') == 'patient')
    return frames


def resolve_knowledge(knowledge, text, proposal, world, *, created_frames=()):
    snapshot = knowledge.snapshot()
    revision = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    merged = deepcopy(world)
    issues = []
    live_source = snapshot['sources'].get('live', {})
    if live_source and live_source['status'] != 'current':
        issues.append('knowledge_live_' + live_source['status'])
    for identifier, record in knowledge.world().items():
        if identifier in merged and merged[identifier] != record:
            issues.append('knowledge_world_conflict:' + identifier)
        else:
            merged[identifier] = deepcopy(record)
    matches = []
    bindings = []
    frames = proposal.get('frames', []) if isinstance(proposal, dict) else []
    for index, frame in enumerate(frames if isinstance(frames, list) else []):
        if not isinstance(frame, dict):
            continue
        for slot in ('agent', 'patient', 'recipient'):
            value = frame.get(slot)
            if not isinstance(value, str) or value in ('NONE', 'UNKNOWN', 'MISSING'):
                continue
            term = re.sub(r'^(?:the|a|an)\s+', '', value, flags=re.I)
            if not term.strip():
                issues.append(f'knowledge_invalid_mention:{index}:{slot}')
                continue
            creating = slot == 'patient' and (index in created_frames or
                str(frame.get('predicate', '')).casefold() in {'create', 'provision', 'clone', 'copy'})
            lookup = knowledge.lookup(term, include_live=not creating)
            live_candidates = []
            for identifier, record in merged.items():
                aliases = record.get('aliases', [])
                if not isinstance(aliases, list) or any(not isinstance(a, str) for a in aliases):
                    issues.append('knowledge_invalid_world_aliases:' + identifier)
                    aliases = []
                names = [record.get('name')] + aliases
                if any(isinstance(name, str) and name.strip().casefold() == term.strip().casefold() for name in names):
                    live_candidates.append(identifier)
            matches.append(dict(frame=index, slot=slot, mention=value, lookup=lookup,
                                live_candidates=live_candidates,
                                creates_description=creating))
            if not creating and len(live_candidates) > 1:
                issues.append(f'knowledge_ambiguous:{index}:{slot}')
            elif (creating or not live_candidates) and lookup['status'] in ('ambiguous', 'unsupported', 'negative'):
                issues.append(f'knowledge_{lookup["status"]}:{index}:{slot}')
            # A creation description is not an assertion that an object exists.
            if not creating and len(live_candidates) == 1:
                spans = [dict(start=m.start(), end=m.end(), text=m.group()) for m in
                         re.finditer(r'(?<!\w)' + re.escape(value) + r'(?!\w)', text)]
                if spans:
                    bindings.append(dict(frame=index, slot=slot, mention=value,
                                         entity_id=live_candidates[0], spans=spans,
                                         evidence='exact_current_name_or_alias'))
    # The current grounding contract is mention -> ID, not frame -> ID.
    # One literal cannot safely mean a created entity in one frame and a live
    # entity in another. Preserve both candidates and abstain instead.
    created_mentions = {m['mention'] for m in matches if m['creates_description']}
    conflicting_mentions = created_mentions.intersection(b['mention'] for b in bindings)
    issues.extend('knowledge_conflicting_mention_roles:' + m for m in conflicting_mentions)
    bindings = [b for b in bindings if b['mention'] not in conflicting_mentions]
    return dict(version=VERSION, revision=revision, snapshot=snapshot, matches=matches,
                bindings=bindings, lexical_mentions=knowledge.annotate(text)['mentions'],
                issues=sorted(set(issues)), world=merged,
                semantics='caller-supplied evidence; exact lookup is not verified real-world truth')


def validate_knowledge_proposal(proposal, evidence):
    """An existing ID alone cannot override an exact library candidate set."""
    issues = list(evidence['issues'])
    groundings = proposal.get('groundings', {}) if isinstance(proposal, dict) else {}
    if isinstance(groundings, dict):
        for mention, target in groundings.items():
            matches = [m for m in evidence['matches'] if m['mention'] == mention]
            if not matches or any(m['creates_description'] or len(m['live_candidates']) != 1 or target not in m['live_candidates'] for m in matches):
                issues.append('knowledge_grounding_not_supported:' + str(mention))
    references = proposal.get('world_references', []) if isinstance(proposal, dict) else []
    allowed = {m['live_candidates'][0] for m in evidence['matches']
               if len(m['live_candidates']) == 1 and not m['creates_description']}
    if isinstance(references, list) and any(not isinstance(r, str) or r not in allowed for r in references):
        issues.append('knowledge_world_reference_not_supported')
    return sorted(set(issues))
