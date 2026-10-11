"""Client-confirmed discourse bindings; never infer identity from recency alone."""
import hashlib
import json
import re

VERSION = 'memory-grounding-2'
REFERENCES = {'it': 'singular', 'this': 'singular', 'that': 'singular', 'them': 'plural', 'these': 'plural', 'those': 'plural'}


def resolve_memory(text, code, ledger, world):
    bindings, issues, decisions = [], [], []
    claims = ledger['claims']
    source_hash=hashlib.sha256(text.encode()).hexdigest()
    for index, frame in enumerate(code.get('frames', [])):
        for slot in ('agent', 'patient', 'recipient'):
            mention = frame.get(slot, '')
            if not isinstance(mention, str) or mention.casefold() not in REFERENCES:
                continue
            if any(r.get('frame') == index and r.get('slot') == slot and r.get('status') == 'resolved'
                   for r in code.get('local_references', [])):
                continue
            relevant = [c for c in claims if c.get('reference', '').casefold() == mention.casefold()
                        and ('reference_scope' not in c or c['reference_scope']==dict(source_sha256=source_hash,frame=index,slot=slot))]
            active = [c for c in relevant if c['status'] != 'superseded']
            candidates = []
            failures = []
            for c in active:
                if c['status'] == 'reported':
                    continue
                if c['status'] == 'disputed':
                    failures.append('memory_disputed_reference:' + mention)
                    continue
                target = c.get('entity_id')
                record = world.get(target)
                if record is None:
                    failures.append('memory_missing_entity:' + mention)
                    continue
                quote = re.sub(r'^(?:the|a|an)\s+', '', c['quote'], flags=re.I).strip().casefold()
                aliases = record.get('aliases', [])
                if not isinstance(aliases, list) or any(not isinstance(a, str) for a in aliases):
                    failures.append('memory_invalid_aliases:' + mention)
                    continue
                names = [record.get('name', '')] + aliases
                if quote not in [n.strip().casefold() for n in names if isinstance(n, str)]:
                    failures.append('memory_evidence_name_mismatch:' + mention)
                    continue
                if record.get('number') != REFERENCES[mention.casefold()]:
                    failures.append('memory_number_not_supported:' + mention)
                    continue
                candidates.append(c)
            ids = sorted({c['entity_id'] for c in candidates})
            if len(ids) > 1:
                failures.append('memory_ambiguous_reference:' + mention)
            if not ids and not failures:
                failures.append('memory_unconfirmed_reference:' + mention)
            issues.extend(failures)
            decisions.append(dict(frame=index, slot=slot, mention=mention, candidate_ids=ids,
                                  claim_ids=[c['id'] for c in active], reasons=failures))
            if len(ids) == 1 and not failures:
                spans = [dict(start=m.start(), end=m.end(), text=m.group()) for m in
                         re.finditer(r'(?<!\w)' + re.escape(mention) + r'(?!\w)', text)]
                bindings.append(dict(frame=index, slot=slot, mention=mention, entity_id=ids[0], spans=spans,
                    evidence='client_confirmed_ledger_reference', claim_ids=[c['id'] for c in candidates],
                    prior_spans=[dict(turn_id=c['turn_id'],start=c['start'],end=c['end'],quote=c['quote']) for c in candidates]))
    revision = hashlib.sha256(json.dumps(ledger, sort_keys=True).encode()).hexdigest()
    return dict(version=VERSION, revision=revision, bindings=bindings, issues=sorted(set(issues)), decisions=decisions,
                semantics='caller confirms reference intent; code checks evidence, identity, number and conflicts')
