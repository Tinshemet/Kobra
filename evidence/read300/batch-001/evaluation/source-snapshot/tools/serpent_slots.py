"""Evaluator-only source-graph projection. Never imported by the READ reader.

This deliberately bounded projection is NOT Serpent's full graph scorer.
See benchmarks/read300/protocol.json for omitted graph distinctions.
"""
from kobra.selection_read import SLOTS


def project(case):
    atoms = {a['id']: a for a in case['atoms']}
    relations = case['relations']
    sentence = case['sentence']

    def targets(identifier, kind):
        return [r['to'] for r in relations if r['from'] == identifier and r['type'] == kind]

    def segments(identifier, lexical=False):
        return [s for s in case['surface']
                if (not lexical or s['kind'] == 'lexeme') and s['kind'] not in ('noise', 'spacing', 'punctuation')
                and {'kind': 'atom', 'id': identifier} in s['sources']]

    def region(identifier):
        spans = [span for d in case['derivation'] if d['role'] != 'noise'
                 and {'kind': 'atom', 'id': identifier} in d['sources'] for span in d['intervals']]
        return (min(s[0] for s in spans), max(s[1] for s in spans)) if spans else None

    def text(identifier, clause=None, nominal=False, lexical=False):
        atom = atoms[identifier]
        if atom['realization'] == 'unrealized':
            return 'NONE' if atom['features'].get('role') == 'addressee' else 'MISSING'
        pieces = segments(identifier, lexical)
        if nominal:
            children = [r['from'] for r in relations if r['to'] == identifier
                        and r['type'] in ('ATTRIBUTE_OF', 'QUANTIFIES', 'MEMBER_OF')]
            # Predicative properties are separate frames, not noun modifiers.
            children = [i for i in children if not targets(i, 'CLAUSE_OF')]
            for child in children:
                pieces += segments(child)
            locs = targets(identifier, 'LOCATED_AT')
            for loc in locs:
                pieces += segments(loc)
        if clause and region(clause):
            lo, hi = region(clause)
            local = [s for s in pieces if lo <= s['start'] and s['end'] <= hi]
            if local:
                pieces = local
        if not pieces:
            bounds = region(identifier)
            if bounds:
                return sentence[bounds[0]:bounds[1]]
            raise ValueError(f'No source evidence for {identifier}')
        # Repeated references outside one clause: choose first local mention.
        pieces = sorted({(s['start'], s['end']) for s in pieces})
        groups = [[pieces[0]]]
        for span in pieces[1:]:
            gap = sentence[groups[-1][-1][1]:span[0]]
            if nominal and gap.strip() not in ('', 'and', 'in'):
                groups.append([])
            groups[-1].append(span)
        return sentence[groups[0][0][0]:groups[0][-1][1]]

    def scopes_to(identifier, event, visited=None):
        visited = set() if visited is None else visited
        if identifier == event:
            return True
        if identifier in visited:
            return False
        visited.add(identifier)
        return any(scopes_to(t, event, visited) for kind in ('SCOPE_OVER', 'VALUE_OF')
                   for t in targets(identifier, kind))

    condition_clauses = {r['from'] for r in relations if r['type'] == 'CONDITION_OF'}
    predicates = [a for a in case['atoms'] if a['type'] == 'EVENT' or
                  (a['type'] == 'PROPERTY' and any(atoms[t]['type'] == 'CLAUSE' for t in targets(a['id'], 'CLAUSE_OF')))]
    output = []
    for atom in predicates:
        event = atom['id']
        clauses = [t for t in targets(event, 'CLAUSE_OF') if atoms[t]['type'] == 'CLAUSE']
        clause = clauses[0] if clauses else None
        if clause in condition_clauses:
            continue
        features = atoms[clause]['features'] if clause else case['factors']
        form = features.get('form', features.get('clause_form'))
        frame = {s: ['NONE'] for s in SLOTS}
        frame['act'] = [{'imperative': 'request', 'interrogative': 'question', 'declarative': 'assertion'}[form]]
        frame['predicate'] = [text(event, clause, lexical=True)]
        argument_ids = {}
        for role, relation in [('agent', 'ACTOR'), ('patient', 'PATIENT'), ('recipient', 'RECIPIENT')]:
            ids = targets(event, relation)
            if role == 'agent' and not ids and atom['type'] == 'PROPERTY':
                ids = targets(event, 'ATTRIBUTE_OF')
            if len(ids) > 1:
                raise ValueError('Multiple arguments cannot fit one source slot')
            if ids:
                argument_ids[role] = ids[0]
                frame[role] = [text(ids[0], clause, nominal=True)]
        for candidate in case['atoms']:
            kind = candidate['features'].get('kind')
            if kind in ('negation', 'modality') and scopes_to(candidate['id'], event):
                frame[kind] = [text(candidate['id'], clause)]
        for relation in relations:
            if relation['type'] == 'CONDITION_OF' and relation['to'] == clause:
                bounds = region(relation['from'])
                markers = [s for s in case['surface'] if {'kind': 'relation', 'id': relation['id']} in s['sources']]
                if not bounds or not markers:
                    raise ValueError('Conditional evidence missing')
                frame['condition'] = [sentence[min(bounds[0], min(s['start'] for s in markers)):bounds[1]]]
            if relation['type'] == 'MODIFIES' and relation['to'] == event:
                modifier = atoms[relation['from']]
                if modifier['features'].get('lemma') == 'yesterday':
                    frame['time'] = [text(modifier['id'], clause)]
        for role in ('patient', 'agent', 'recipient'):
            quantities = [r['from'] for r in relations if r['type'] == 'QUANTIFIES'
                          and r['to'] == argument_ids.get(role)]
            if quantities:
                if len(quantities) != 1:
                    raise ValueError('Multiple quantities in one argument')
                frame['quantity'] = [text(quantities[0], clause)]
                break
        output.append(frame)
    if not output or len(output) > 4:
        raise ValueError('Unsupported frame count')
    return output
