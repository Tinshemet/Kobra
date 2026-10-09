"""Paired evidence for fix ticks; never compare different sentences as flips."""
import argparse
import hashlib
import json
from pathlib import Path
from evaluate_selection import dump


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--fix-id',required=True)
    parser.add_argument('--kind',choices=['development-replay','fresh-batch-ablation'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    def load(path):
        rows=[json.loads(line) for line in (path/'cases.jsonl').read_text().splitlines()]
        assert len({r['text'] for r in rows})==len(rows)
        return {r['text']:r for r in rows}
    before,after=load(args.before),load(args.after)
    assert set(before)==set(after),'A paired comparison requires the same complete set of sentences'
    # A fix_id describes the whole intervention bundle unless a separate
    # leave-one-fix-out ablation actually isolated its contribution.
    changes=[]
    for sentence in before:
        old,new=before[sentence],after[sentence]
        was,now=bool(old['score']['exact']),bool(new['score']['exact'])
        changes.append({'sentence':sentence,'before_id':old['id'],'after_id':new['id'],
                        'before_correct':was,'after_correct':now,
                        'tick':not was and now,'regression':was and not now,
                        'slot_delta':new['score']['slots_correct']-old['score']['slots_correct']})
    dump(args.output,{'fix_id':args.fix_id,'kind':args.kind,'cases':len(changes),
                      'before':str(args.before),'after':str(args.after),
                      'before_capture_sha256':hashlib.sha256((args.before/'cases.jsonl').read_bytes()).hexdigest(),
                      'after_capture_sha256':hashlib.sha256((args.after/'cases.jsonl').read_bytes()).hexdigest(),
                      'ticks':sum(c['tick'] for c in changes),'regressions':sum(c['regression'] for c in changes),
                      'net_exact_gain':sum(c['tick']-c['regression'] for c in changes),
                      'sentences':changes,
                      'limitation':'Attribution applies to the entire recorded change between these runs; this file alone does not establish isolation of one rule.'})


if __name__=='__main__':
    main()
