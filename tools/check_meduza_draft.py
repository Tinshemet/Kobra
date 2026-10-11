"""Check the draft's JSON shape only. No execution or semantic-validation claim.

Requires jsonschema in the development environment; does not add a runtime dep.
"""
import json
from copy import deepcopy
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT = Path(__file__).resolve().parents[1]

def main():
    schema=json.loads((ROOT/'schemas/meduza-program-0.2.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema)
    valid={p.stem:json.loads(p.read_text()) for p in sorted((ROOT/'examples/meduza-v2').glob('*.json'))}
    checks=[]
    for name,p in valid.items():
        errors=list(validator.iter_errors(p))
        checks.append(dict(case=name,expected='valid_shape',passed=not errors))
    def bad(name,original,change):
        p=deepcopy(valid[original]);change(p)
        checks.append(dict(case=name,expected='invalid_shape',passed=bool(list(validator.iter_errors(p)))))
    bad('unknown-version','fetch',lambda p:p.update(schema='meduza.program/999'))
    bad('self-issued-grant','fetch',lambda p:p.update(authorized=True))
    bad('bad-mode','fetch',lambda p:p.update(mode='anything'))
    bad('unknown-operation','fetch',lambda p:p['body'][0].update(op='python_eval'))
    bad('empty-dependencies','fetch',lambda p:p.update(dependencies=[]))
    bad('bad-hash','fetch',lambda p:p['origin'].update(artifact_sha256='not-a-hash'))
    bad('unknown-as-false','conditional',lambda p:p['body'][1].update(on_unknown='else'))
    bad('conflict-as-true','conditional',lambda p:p['body'][1].update(on_conflict='then'))
    bad('implicit-reference','fetch',lambda p:p['body'][0]['args'].update(target='$vm'))
    bad('missing-provenance','fetch',lambda p:p['body'][0].update(origins=[]))
    bad('unbounded-loop','set',lambda p:p['body'][0].update(max_items=0))
    bad('live-loop-selection','set',lambda p:p['body'][0].update(selection='live'))
    bad('unbounded-achieve','achieve',lambda p:p['body'][1].update(max_rounds=0))
    bad('boolean-count','creation',lambda p:p['body'][0].update(count=True))
    bad('negative-time-budget','fetch',lambda p:p['limits'].update(max_wall_ms=-1))
    bad('mixed-value-tags','fetch',lambda p:p['body'][0]['args'].update(target={'ref':'vm','literal':'other'}))
    # Demonstrate an important limit: undefined references remain shape-valid.
    p=deepcopy(valid['fetch']);p['body'][0]['args']['target']={'ref':'never_bound'}
    checks.append(dict(case='undefined-reference-needs-future-semantic-checker',expected='valid_shape_only',passed=not list(validator.iter_errors(p))))
    summary=dict(kind='draft schema conformance, not language/runtime correctness',checks=len(checks),passed=sum(c['passed'] for c in checks),failed=[c for c in checks if not c['passed']],examples=len(valid),runtime_tests=0,model_calls=0,details=checks)
    print(json.dumps(summary,indent=2))
    return 0 if all(c['passed'] for c in checks) else 1
if __name__=='__main__':raise SystemExit(main())
