"""Fresh existing-grammar instances, with graph-first independent Serpent gold.

Run only after READ fixes and this recipe have been frozen. Does not import READ,
change Serpent, reuse frozen pack rows, or select by downstream performance.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path

from serpent import __version__
from serpent.context_requirements import context_report
from serpent.grammar import Clause, NounPhrase, simple_clause
from serpent.planner import Item, Options, select
from serpent.serialization import canonical_bytes
from serpent.validate import validate_case
from generate_read300 import ROOT, dump, known_inputs, normalized
from serpent_slots import project


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def construct_pool(recipe, batch):
    bindings = recipe['bindings_by_set'][str(batch)]
    dimensions = (recipe['people'], bindings, recipe['numbers'], recipe['tenses'],
                  recipe['voices'], recipe['forms'], recipe['negative'])
    pool = []
    for index, (person, (verb, noun), number, tense, voice, form, negative) in enumerate(product(*dimensions), 1):
        case = simple_clause('S000001', Clause(
            NounPhrase(person), verb, NounPhrase(noun, number=number),
            tense=tense, voice=voice, form=form, negative=negative))
        pool.append(Item(f'same-scope/{batch}/{index:06d}', 'voice_tense', case))
    return tuple(pool)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=int, required=True, choices=(10, 11, 12))
    parser.add_argument('--reader-freeze', type=Path, required=True,
                        help='JSON mapping relative Kobra source paths to SHA256; requires exact current match')
    args = parser.parse_args()
    freeze = json.loads(args.reader_freeze.read_text())
    if not isinstance(freeze, dict) or not freeze or not any(p.startswith('src/kobra/') for p in freeze):
        parser.error('reader freeze must cover Kobra source files')
    required = {str(p.relative_to(ROOT)) for p in (ROOT/'src/kobra').glob('*.py')}
    required.update({'tools/evaluate_selection.py', 'tools/serpent_slots.py',
                     'tools/generate_same_scope_sets.py', 'benchmarks/read300/same-scope-recipe.json'})
    if not required.issubset(freeze):
        parser.error('reader freeze must include all Kobra modules, scorer, adapter, generator and recipe')
    for relative, expected in freeze.items():
        if digest(ROOT / relative) != expected:
            parser.error(f'changed frozen source: {relative}')
    recipe_path = ROOT/'benchmarks/read300/same-scope-recipe.json'
    recipe = json.loads(recipe_path.read_text())
    seed = recipe['seed_base'] + args.batch
    options = Options(distribution='balanced', noise='off', typos='off', strength=2)
    pool = construct_pool(recipe, args.batch)
    known = known_inputs()
    eligible = tuple(item for item in pool if normalized(item.case.sentence) not in known)
    cases = select(eligible, recipe['size'], seed, options)
    references, errors = [], []
    for case in cases:
        validate_case(case)
        row = {'id': case.id, 'text': case.sentence, 'group': 'voice_tense'}
        try:
            row['expected'] = project(case.to_dict())
        except Exception as exc:
            row.update(expected=None, adapter_error=f'{type(exc).__name__}: {exc}')
            errors.append({'id': case.id, 'error': row['adapter_error']})
        references.append(row)
    normalized_selected = {normalized(case.sentence) for case in cases}
    assert len(normalized_selected) == recipe['size'] and not normalized_selected & known
    serpent_root = Path(__import__('serpent').__file__).resolve().parent
    output = ROOT/f'evidence/read300/batch-{args.batch:03d}'
    output.mkdir(exist_ok=False)
    dump(output/'generator-manifest.json', {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'serpent_version': __version__, 'external_inventory_version': recipe['version'],
        'requested_size': recipe['size'], 'seed': seed, 'recipe': recipe,
        'recipe_sha256': digest(recipe_path), 'tool_sha256': digest(Path(__file__)),
        'reader_freeze_sha256': digest(args.reader_freeze), 'reader_freeze': freeze,
        'pool_sha256': hashlib.sha256(b''.join(canonical_bytes({'key': i.key, 'case': i.case.to_dict()}) for i in pool)).hexdigest(),
        'pool_count': len(pool), 'eligible_count': len(eligible), 'seen_count': len(known),
        'known_normalized_sha256': hashlib.sha256(json.dumps(sorted(known)).encode()).hexdigest(),
        'generator_source_hashes': {str(p.relative_to(serpent_root)): digest(p)
                                    for p in serpent_root.rglob('*') if p.suffix in ('.py', '.json')},
        'adapter_sha256': digest(Path(__file__).with_name('serpent_slots.py')),
        'adapter_errors': errors, 'by_group': dict(Counter(r['group'] for r in references)),
        'selection': recipe['selection'], 'context_policy': 'account',
        'before_context_filter_count': len(eligible), 'context_excluded_count': 0})
    dump(output/'serpent-source-cases.json', {'cases': [c.to_dict() for c in cases]})
    dump(output/'frozen-reference.json', {'cases': references})
    dump(output/'context-requirements.json', context_report(cases))
    dump(output/'context-exclusions.json', [])
    dump(output/'inputs.json', [{'id': c.id, 'text': c.sentence} for c in cases])
    print(json.dumps({'output': str(output), 'cases': len(cases), 'adapter_errors': errors}))


if __name__ == '__main__':
    main()
