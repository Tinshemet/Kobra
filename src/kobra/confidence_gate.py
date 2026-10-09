"""External, fail-closed proposal gate. Model self-confidence is never read.

The score is a Wilson lower bound from a separately supplied held-out cohort,
not the probability that an individual sentence is correct. No calibration is
inferred from successful schema checks or reused development scores.
"""
from dataclasses import dataclass
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

    def assess(self, text, proposal, *, cohort, world_ids=(), missing_context=()):
        # cohort, world_ids and missing_context come from application code, not
        # fields inside the untrusted model proposal or Serpent teacher labels.
        reasons = [f'missing_context:{x}' for x in missing_context]
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
            for frame in frames:
                if not isinstance(frame, dict):
                    continue
                for slot in ('agent', 'patient', 'recipient'):
                    value = frame.get(slot)
                    if isinstance(value, str) and re.match(r'^(it|them|he|she|they|this|that|these|those|here|there)(?:\s|$)', value, re.I):
                        if value not in groundings:
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
    def __init__(self, assigner, gate, resolver=None, model_cohort='model-unresolved-v1'):
        self.assigner, self.gate, self.resolver = assigner, gate, resolver
        self.model_cohort = model_cohort

    def read(self, text, *, world=None, history=(), missing_context=()):
        world = world or {}
        code = self.assigner.assign(text)
        proposal = code
        origin = 'code' if code['route'] == 'code' else 'unresolved'
        cohort = 'code:' + '+'.join(sorted(code['rules']))
        if code['route'] != 'code':
            cohort = self.model_cohort
            if self.resolver is not None:
                origin = 'AI'
                try:
                    proposal = self.resolver({'source':text, 'code_proposal':code,
                                              'world':world, 'history':list(history)})
                except Exception as exc:
                    proposal = {'error_type':type(exc).__name__}
        result = self.gate.assess(text, proposal, cohort=cohort, world_ids=tuple(world), missing_context=missing_context)
        result['assignment_source'] = origin
        result['code_proposal'] = code
        return result
