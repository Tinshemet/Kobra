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

    def assess(self, text, proposal, *, cohort, world_ids=(), missing_context=(), local_bindings=(), validation_reasons=()):
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
                    if isinstance(value, str) and re.match(r'^(it|them|he|she|they|this|that|these|those|here|there)(?:\s|$)', value, re.I):
                        local_match = any(r.get('frame') == frame_index and r.get('slot') == slot
                            and r.get('status') == 'resolved' and r.get('mention',{}).get('text') == value
                            for r in local_bindings)
                        if value not in groundings and not local_match:
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


class GatedRuleReader:
    """Code first, optional model proposal, external gate, explicit ASK handoff."""
    def __init__(self, assigner, gate, resolver=None, model_cohort='model-unresolved-v1', knowledge=None):
        self.assigner, self.gate, self.resolver = assigner, gate, resolver
        self.model_cohort = model_cohort
        self.knowledge = knowledge

    def read(self, text, *, world=None, history=(), missing_context=(), context_claims=()):
        world = deepcopy(world or {})
        history = deepcopy(list(history))
        ledger = context_snapshot(history, world, context_claims)
        code = self.assigner.assign(text)
        knowledge_evidence = None
        if self.knowledge is not None:
            from .knowledge_resolution import resolve_knowledge, created_patient_frames
            knowledge_evidence = resolve_knowledge(self.knowledge, text, code, world,
                                                   created_frames=created_patient_frames(code))
            world = deepcopy(knowledge_evidence.pop('world'))
            ledger = context_snapshot(history, world, context_claims)
        proposal = deepcopy(code)
        origin = 'code' if code['route'] == 'code' else 'unresolved'
        cohort = 'code:' + '+'.join(sorted(code['rules']))
        if code['route'] != 'code':
            cohort = self.model_cohort
            if self.resolver is not None:
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
        knowledge_reasons = []
        if knowledge_evidence is not None:
            from .knowledge_resolution import resolve_knowledge, validate_knowledge_proposal
            # Model may supply different roles: evaluate those mentions as well.
            if origin == 'AI' and isinstance(proposal, dict):
                final_evidence = resolve_knowledge(self.knowledge, text, proposal, world)
                final_evidence.pop('world')
                knowledge_evidence['model_matches'] = final_evidence['matches']
                knowledge_reasons.extend(validate_knowledge_proposal(proposal, final_evidence))
            if origin != 'AI':
                knowledge_reasons.extend(validate_knowledge_proposal(proposal, knowledge_evidence))
            else:
                knowledge_reasons.extend(knowledge_evidence['issues'])
            cohort += ':' + knowledge_evidence['version'] + ':' + knowledge_evidence['revision']
            if origin == 'code':
                for binding in knowledge_evidence['bindings']:
                    proposal.setdefault('groundings', {})[binding['mention']] = binding['entity_id']
        result = self.gate.assess(text, proposal, cohort=cohort, world_ids=tuple(world),
                                 missing_context=missing_context, local_bindings=local_bindings,
                                 validation_reasons=knowledge_reasons)
        result['context_ledger'] = ledger
        result['assignment_source'] = origin
        result['code_proposal'] = code
        if knowledge_evidence is not None:
            result['knowledge_evidence'] = knowledge_evidence
        return result
