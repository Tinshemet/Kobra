"""Score correctness and ASK suitability separately; no model judge.

Gold: expected frames use the existing per-slot allowed-value contract;
ask_required is declared before inference, with reason codes. A correct ASK
must name an expected missing/ambiguous item, not merely fail a transport call.
Input records have id, gold and result; gold must never be sent to the reader.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from evaluate_selection import score


def judge(gold, result):
    route = result.get('route')
    origin = result.get('assignment_source', 'unknown')
    if type(gold.get('ask_required')) is not bool:
        raise ValueError('gold must explicitly declare ASK requirement')
    if gold['ask_required'] and not gold.get('ask_reasons'):
        raise ValueError('ASK gold needs predeclared reason codes')
    if route == 'ASK':
        if not gold['ask_required']:
            return 'unnecessary_ASK'
        actual = set(result.get('reasons', []))
        if actual.intersection(gold['ask_reasons']):
            return 'correct_ASK'
        return 'unjustified_ASK'
    if route != 'ACCEPT':
        return 'invalid_route'
    if gold['ask_required']:
        return 'unsafe_accept'
    if origin not in ('code', 'AI'):
        return 'invalid_origin'
    proposal = result.get('proposal')
    if not isinstance(proposal, dict):
        return 'invalid_proposal'
    frames = proposal.get('frames')
    if not isinstance(frames, list) or not 1 <= len(frames) <= 4 or any(not isinstance(f, dict) for f in frames):
        return 'invalid_proposal'
    exact = score(gold['expected'], frames)['exact']
    # Resolved WORLD identities are independently scored when the task requires
    # grounding, even if literal extraction matches every surface slot.
    expected_bindings = gold.get('groundings', {})
    actual_bindings = result.get('proposal', {}).get('groundings', {})
    exact = exact and all(actual_bindings.get(k) == v for k,v in expected_bindings.items())
    return ('correct_' if exact else 'wrong_') + origin


def evaluate(records):
    judged = [dict(id=r['id'], outcome=judge(r['gold'],r['result'])) for r in records]
    counts = Counter(r['outcome'] for r in judged)
    total = len(judged)
    asks = sum(r['result'].get('route')=='ASK' for r in records)
    expected_asks = sum(r['gold']['ask_required'] for r in records)
    return dict(cases=total,counts=dict(counts),
                correct_code=counts['correct_code'],correct_AI=counts['correct_AI'],correct_ASK=counts['correct_ASK'],
                ask_precision=counts['correct_ASK']/asks if asks else None,
                ask_recall=counts['correct_ASK']/expected_asks if expected_asks else None,
                correct=sum(counts[k] for k in ('correct_code','correct_AI','correct_ASK')),
                accepted=sum(r['result'].get('route')=='ACCEPT' for r in records),
                ask=sum(r['result'].get('route')=='ASK' for r in records),
                records=judged)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('records',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    records=[json.loads(line) for line in args.records.read_text().splitlines() if line.strip()]
    result=evaluate(records)
    with args.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))

if __name__=='__main__':main()
