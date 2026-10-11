"""External, fail-closed proposal gate. Model self-confidence is never read.

The score is a Wilson lower bound from a separately supplied held-out cohort,
not the probability that an individual sentence is correct. No calibration is
inferred from successful schema checks or reused development scores.
"""
from dataclasses import dataclass
from copy import deepcopy
from .context_ledger import context_snapshot
import math
import re
from .selection_read import ACTS, SLOTS, SPECIAL


@dataclass(frozen=True)
class Calibration:
    correct: int
    total: int
    evidence_id: str
    cohort: str
    split: str = 'held_out'

    def lower_bound(self):
        if (type(self.total) is not int or type(self.correct) is not int
                or self.total <= 0 or not 0 <= self.correct <= self.total
                or self.split != 'held_out' or not self.evidence_id or not self.cohort):
            raise ValueError('require identified held-out calibration counts')
        z = 1.96
        p = self.correct / self.total
        return (p + z*z/(2*self.total) - z*math.sqrt(p*(1-p)/self.total + z*z/(4*self.total**2))) / (1+z*z/self.total)


class ConfidenceGate:
    def __init__(self, calibration=None, threshold=0.95, min_cases=100, validators=()):
        if not 0 <= threshold <= 1 or type(min_cases) is not int or min_cases < 1:
            raise ValueError('invalid gate settings')
        self.calibration = calibration or {}
        self.threshold = threshold
        self.min_cases = min_cases
        self.validators = tuple(validators)

    def assess(self, text, proposal, *, cohort, world_ids=(), missing_context=(), local_bindings=(), role_bindings=(), validation_reasons=()):
        # cohort, world_ids and missing_context come from application code, not
        # fields inside the untrusted model proposal or Serpent teacher labels.
        reasons = [f'missing_context:{x}' for x in missing_context] + list(validation_reasons)
        if isinstance(proposal, dict) and proposal.get('route') == 'unresolved':
            reasons.append('unsupported_read_structure')
        frames = proposal.get('frames') if isinstance(proposal, dict) else None
        if not isinstance(frames, list) or not 1 <= len(frames) <= 4:
            reasons.append('missing_or_invalid_frames')
        else:
            for frame in frames:
                if not isinstance(frame, dict) or set(frame) != {'act', *SLOTS}:
                    reasons.append('invalid_frame_fields')
                    continue
                if frame['act'] not in ACTS or frame['act'] == 'unknown':
                    reasons.append('unresolved_act')
                for slot in SLOTS:
                    value = frame[slot]
                    if not isinstance(value, str) or not value:
                        reasons.append(f'invalid_value:{slot}')
                    elif value in ('MISSING', 'UNKNOWN'):
                        reasons.append(f'unresolved_slot:{slot}')
                    elif value not in SPECIAL and not re.search(r'(?<!\w)'+re.escape(value)+r'(?!\w)', text):
                        reasons.append(f'not_in_source:{slot}')
        groundings = proposal.get('groundings', {}) if isinstance(proposal, dict) else {}
        if not isinstance(groundings, dict) or any(
                not isinstance(mention, str) or not mention or mention not in text
                or not isinstance(target, str) or target not in world_ids
                for mention, target in groundings.items()):
            reasons.append('invalid_grounding')
            groundings = {}
        if isinstance(frames, list):
            for frame_index, frame in enumerate(frames):
                if not isinstance(frame, dict):
                    continue
                for slot in ('agent', 'patient', 'recipient'):
                    value = frame.get(slot)
                    if isinstance(value, str) and _REFERENCE_CUE.match(value):
                        local_match = any(r.get('frame') == frame_index and r.get('slot') == slot
                            and r.get('status') == 'resolved' and r.get('mention',{}).get('text') == value
                            for r in local_bindings)
                        scoped_match = any(b.get('frame') == frame_index and b.get('slot') == slot
                            and b.get('mention') == value and b.get('entity_id') in world_ids for b in role_bindings)
                        if value not in groundings and not local_match and not scoped_match:
                            reasons.append(f'ungrounded_reference:{slot}')
        references = proposal.get('world_references', []) if isinstance(proposal, dict) else []
        if not isinstance(references, list) or any(not isinstance(r, str) or r not in world_ids for r in references):
            reasons.append('nonexistent_world_reference')
        if not reasons:
            for validator in self.validators:
                try:
                    reasons.extend(validator(text, frames))
                except Exception:
                    reasons.append('rule_validation_failed')
        calibration = self.calibration.get(cohort)
        external_score = None
        evidence = None
        if calibration is None:
            reasons.append('uncalibrated_cohort')
        else:
            try:
                if calibration.cohort != cohort:
                    raise ValueError('cohort mismatch')
                external_score = calibration.lower_bound()
                evidence = calibration.evidence_id
                if calibration.total < self.min_cases:
                    reasons.append('insufficient_calibration_cases')
                if external_score < self.threshold:
                    reasons.append('below_external_threshold')
            except (ValueError, TypeError, AttributeError):
                reasons.append('invalid_calibration')
        return dict(route='ASK' if reasons else 'ACCEPT', source=text, proposal=proposal,
                    reasons=sorted(set(reasons)), external_score=external_score,
                    score_kind='held_out_cohort_95pct_wilson_lower_bound',
                    calibration_evidence=evidence, cohort=cohort,
                    model_self_confidence_used=False)


_REFERENCE_CUE = re.compile(
    r"\b(?:it|them|he|him|she|her|they|their|theirs|his|hers|its|"
    r"this|that|these|those|here|there|I|me|my|mine|we|us|our|ours|"
    r"you|your|yours|myself|yourself|himself|herself|itself|themselves)\b", re.I)


def _grounding_blockers(text, code, knowledge_evidence, missing_context):
    """Conservative source check even when a failed parse returned no frames.

    This does not infer identities from recency or an AI proposal. Quoted and
    bracketed cues also abstain until the grammar establishes their scope.
    """
    reasons = [f'missing_context:{x}' for x in missing_context]
    references = code.get('local_references', ())
    if any(r.get('status') != 'resolved' for r in references):
        reasons.append('unresolved_local_reference')
    supported = []
    for reference in references:
        if reference.get('status') == 'resolved':
            mention = reference.get('mention', {})
            if isinstance(mention.get('start'), int) and isinstance(mention.get('end'), int):
                supported.append((mention['start'], mention['end']))
    if knowledge_evidence is not None:
        reasons.extend(knowledge_evidence['issues'])
        for mention in knowledge_evidence.get('lexical_mentions', ()):
            if mention['lookup']['status'] in ('ambiguous', 'unsupported', 'negative'):
                reasons.append('knowledge_unresolved_mention:' + mention['text'])
        supported.extend((span['start'], span['end'])
                         for binding in knowledge_evidence['bindings']
                         for span in binding['spans'])
    for cue in _REFERENCE_CUE.finditer(text):
        if not any(start <= cue.start() and cue.end() <= end for start, end in supported):
            reasons.append('unresolved_reference_requires_ASK:' + cue.group().casefold())
    return sorted(set(reasons))


class GatedRuleReader:
    """Code first, optional model proposal, external gate, explicit ASK handoff."""
    def __init__(self, assigner, gate, resolver=None, model_cohort='model-unresolved-v1', knowledge=None):
        self.assigner, self.gate, self.resolver = assigner, gate, resolver
        self.model_cohort = model_cohort
        self.knowledge = knowledge

    def read_for_resolve(self, text, *, metadata=None, annotations=(), **context):
        """Run the existing gated reader, then project its result without new authority."""
        from .resolve_distillation import distill_for_resolve
        return distill_for_resolve(self.read(text, **context), metadata=metadata, annotations=annotations)

    def read(self, text, *, world=None, history=(), missing_context=(), context_claims=()):
        world = deepcopy(world or {})
        history = deepcopy(list(history))
        ledger = context_snapshot(history, world, context_claims)
        code = self.assigner.assign(text)
        from .interpretation import audit_source, CALIBRATION_REASONS
        source_audit = audit_source(text, code)
        knowledge_evidence = None
        if self.knowledge is not None:
            from .knowledge_resolution import resolve_knowledge, created_patient_frames
            knowledge_evidence = resolve_knowledge(self.knowledge, text, code, world,
                                                   created_frames=created_patient_frames(code))
            world = deepcopy(knowledge_evidence.pop('world'))
            ledger = context_snapshot(history, world, context_claims)
        from .memory_grounding import resolve_memory
        memory_evidence = resolve_memory(text, code, ledger, world)
        combined_evidence = deepcopy(knowledge_evidence) if knowledge_evidence is not None else dict(
            issues=[], lexical_mentions=[], bindings=[])
        combined_evidence['issues'].extend(memory_evidence['issues'])
        combined_evidence['bindings'].extend(memory_evidence['bindings'])
        grounding_blockers = _grounding_blockers(text, code, combined_evidence, missing_context)
        proposal = deepcopy(code)
        origin = 'code' if code['route'] == 'code' else 'unresolved'
        cohort = 'code:' + '+'.join(sorted(code['rules']))
        if code['route'] != 'code':
            cohort = self.model_cohort
            if self.resolver is not None and not grounding_blockers:
                origin = 'AI'
                try:
                    proposal = self.resolver({'source':text, 'code_proposal':deepcopy(code),
                                              'world':deepcopy(world), 'history':deepcopy(history),
                                              'context_ledger':deepcopy(ledger),
                                              **({'knowledge_evidence':deepcopy(knowledge_evidence)} if knowledge_evidence is not None else {})})
                except Exception as exc:
                    proposal = {'error_type':type(exc).__name__}
        # Only trusted code-side links may satisfy a local reference. A model
        # cannot authorize invented local IDs by including them in its proposal.
        local_bindings = code.get('local_references', ()) if origin == 'code' else ()
        if code.get('configuration_id'):
            cohort += ':assignment:' + code['configuration_id']
        knowledge_reasons = list(grounding_blockers) if code['route'] != 'code' else []
        deterministic_bindings = []
        if knowledge_evidence is not None:
            from .knowledge_resolution import resolve_knowledge, validate_knowledge_proposal
            # Model may supply different roles: evaluate those mentions as well.
            if origin == 'AI' and isinstance(proposal, dict):
                final_evidence = resolve_knowledge(self.knowledge, text, proposal, world)
                final_evidence.pop('world')
                knowledge_evidence['model_matches'] = final_evidence['matches']
                knowledge_evidence['model_bindings'] = deepcopy(final_evidence['bindings'])
                deterministic_bindings = final_evidence['bindings']
                knowledge_reasons.extend(validate_knowledge_proposal(proposal, final_evidence))
            if origin != 'AI':
                knowledge_reasons.extend(validate_knowledge_proposal(proposal, knowledge_evidence))
            else:
                knowledge_reasons.extend(knowledge_evidence['issues'])
            cohort += ':' + knowledge_evidence['version'] + ':' + knowledge_evidence['revision']
            if origin == 'code':
                deterministic_bindings = knowledge_evidence['bindings']
        if origin == 'code':
            knowledge_reasons.extend(memory_evidence['issues'])
            deterministic_bindings = list(deterministic_bindings) + memory_evidence['bindings']
            by_role = {}
            for binding in deterministic_bindings:
                key=(binding['frame'],binding['slot'])
                by_role.setdefault(key,set()).add(binding['entity_id'])
            conflicts={key for key,ids in by_role.items() if len(ids)>1}
            knowledge_reasons.extend(f'memory_binding_conflict:{f}:{slot}' for f,slot in conflicts)
            deterministic_bindings=[b for b in deterministic_bindings if (b['frame'],b['slot']) not in conflicts]
        cohort += ':' + memory_evidence['version']
        if origin == 'AI' and isinstance(proposal, dict):
            # Identity decisions never gain authority merely by naming an existing ID.
            supplied = proposal.pop('groundings', {})
            supplied_references = proposal.pop('world_references', [])
            allowed = {b['mention']: b['entity_id'] for b in deterministic_bindings}
            if not isinstance(supplied, dict) or any(allowed.get(m) != v for m, v in supplied.items()):
                knowledge_reasons.append('model_identity_assignment_not_supported')
            if not isinstance(supplied_references, list) or any(v not in allowed.values() for v in supplied_references):
                knowledge_reasons.append('model_identity_assignment_not_supported')
            if isinstance(supplied_references, list) and any(not isinstance(v, str) or v not in world for v in supplied_references):
                knowledge_reasons.append('nonexistent_world_reference')
            proposal.pop('local_references', None)
            proposal.pop('role_bindings', None)
        if isinstance(proposal, dict):
            proposal['role_bindings'] = deepcopy(deterministic_bindings)
            # Compatibility map only when a literal has one interpretation in
            # every role occurrence and does not also name a local entity.
            global_ids={}
            for binding in deterministic_bindings:
                global_ids.setdefault(binding['mention'],set()).add(binding['entity_id'])
            local_mentions={r.get('mention',{}).get('text') for r in local_bindings}
            for mention,ids in global_ids.items():
                occurrences={(i,slot) for i,f in enumerate(proposal.get('frames',[])) if isinstance(f,dict)
                             for slot in ('agent','patient','recipient') if f.get(slot)==mention}
                bound={(b['frame'],b['slot']) for b in deterministic_bindings if b['mention']==mention}
                if len(ids)==1 and occurrences==bound and mention not in local_mentions:
                    proposal.setdefault('groundings',{})[mention]=next(iter(ids))
        if origin=='code':knowledge_reasons.extend(source_audit['reasons'])
        result = self.gate.assess(text, proposal, cohort=cohort, world_ids=tuple(world),
                                 missing_context=missing_context, local_bindings=local_bindings,
                                 validation_reasons=knowledge_reasons, role_bindings=deterministic_bindings)
        semantic_reasons=[r for r in result['reasons'] if r not in CALIBRATION_REASONS]
        result['interpretation']=dict(source_audit, status='supported' if source_audit['status']=='supported' and not semantic_reasons else 'unresolved',
            needs_ASK=bool(semantic_reasons) or source_audit['status']!='supported',reasons=semantic_reasons)
        result['acceptance']=dict(status='accepted' if result['route']=='ACCEPT' else 'blocked',
            calibration_reasons=[r for r in result['reasons'] if r in CALIBRATION_REASONS])
        result['memory_evidence'] = memory_evidence
        result['context_ledger'] = ledger
        result['assignment_source'] = origin
        result['grounding_policy'] = 'deterministic_evidence_or_ASK'
        result['resolver_blocked_reasons'] = grounding_blockers if code['route'] != 'code' else []
        result['code_proposal'] = code
        if knowledge_evidence is not None:
            result['knowledge_evidence'] = knowledge_evidence
        return result
