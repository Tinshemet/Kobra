"""Paired replay of archived code assignments; no new model calls or fresh score."""
import argparse
import hashlib
import json
from pathlib import Path
from kobra.rule_assignment import RuleAssigner
from evaluate_selection import score


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(exist_ok=False)
    engine=RuleAssigner();results=[]
    root=Path(__file__).resolve().parents[1]
    references={}
    for b in (1,5):
        rows=json.loads((root/f'evidence/read300/batch-{b:03d}/frozen-reference.json').read_text())['cases']
        references.update({(b,r['id']):r for r in rows})
    for line in args.before.read_text().splitlines():
        old=json.loads(line);before=old['after_correct'];prediction=engine.assign(old['text'])
        scored=score(references[old['batch'],old['id']]['expected'],prediction['frames'])
        routed=prediction['route']=='code';after=routed and scored['exact']
        results.append(dict(batch=old['batch'],id=old['id'],text=old['text'],before_correct=before,
            after_correct=after,after_code_routed=routed,tick=not before and after,regression=before and not after,
            proposal=prediction,score=scored))
    summary=dict(kind='paired reused development; literal-slot score, not full structure accuracy',cases=len(results),
        before_correct=sum(r['before_correct'] for r in results),after_correct=sum(r['after_correct'] for r in results),
        code_routed=sum(r['after_code_routed'] for r in results),ticks=sum(r['tick'] for r in results),
        regressions=sum(r['regression'] for r in results),accepted_incorrect=sum(r['after_code_routed'] and not r['after_correct'] for r in results),new_model_calls=0)
    (args.output/'cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    paths=['src/kobra/rule_assignment.py','src/kobra/structural_read.py','src/kobra/surface_chunks.py', 'src/kobra/shared_patients.py', 'tools/compare_code_replay.py']
    (args.output/'provenance.json').write_text(json.dumps({'baseline_sha256':hashlib.sha256(args.before.read_bytes()).hexdigest(),'files':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in paths}},indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
