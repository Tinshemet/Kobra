"""Bounded, caller-supplied knowledge snapshots; lookup never grants authority.

No persistence, refresh, learning, execution or implicit WORLD construction.
"""
from copy import deepcopy
import hashlib
import json
import re

VERSION = 'knowledge-snapshot-1'
TYPES = {'class', 'attribute', 'unit', 'value'}


def _string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty string')
    return value


def _strings(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f'{label} must be a list of nonempty strings')


def _key(value):
    return value.strip().casefold()


class KnowledgeSnapshot:
    """An immutable-by-interface snapshot of three separately versioned sources.

    ``current`` is the caller's freshness attestation, not a READ observation.
    Lexical records describe classes/properties; only live records have entity IDs.
    """
    def __init__(self, *, live=None, manifest=None, archive=None):
        self._sources = {}
        for layer, supplied in [('live', live), ('manifest', manifest), ('archive', archive)]:
            if supplied is None:
                continue
            if not isinstance(supplied, dict):
                raise ValueError(f'{layer} must be an object')
            source = deepcopy(supplied)
            _string(source.get('revision'), f'{layer}.revision')
            _string(source.get('source'), f'{layer}.source')
            if layer == 'live':
                if source.get('status') not in {'current', 'stale', 'unavailable'}:
                    raise ValueError('live.status must explicitly attest current, stale or unavailable')
                entities = source.get('entities')
                if not isinstance(entities, dict):
                    raise ValueError('live.entities must map IDs to records')
                for identifier, record in entities.items():
                    _string(identifier, 'entity ID')
                    if not isinstance(record, dict):
                        raise ValueError('entity record must be an object')
                    _string(record.get('name'), 'entity name')
                    _strings(record.get('aliases', []), 'entity aliases')
            else:
                records = source.get('records')
                if not isinstance(records, list):
                    raise ValueError(f'{layer}.records must be a list')
                ids = set()
                for record in records:
                    if not isinstance(record, dict):
                        raise ValueError('lexical record must be an object')
                    identifier = _string(record.get('id'), 'record ID')
                    if identifier in ids:
                        raise ValueError('duplicate lexical record ID')
                    ids.add(identifier)
                    for field in ('word', 'source', 'status', 'provenance'):
                        _string(record.get(field), field)
                    if record.get('type') not in TYPES:
                        raise ValueError('record.type must be class, attribute, unit or value')
                    if record['status'] not in {'pending', 'ratified', 'superseded'}:
                        raise ValueError('unknown lexical status')
                    if layer == 'manifest' and (record['source'] != 'manifest' or record['status'] != 'ratified'):
                        raise ValueError('manifest records must declare manifest source and ratified status')
                    if layer == 'archive' and record['source'] not in {'told', 'imported'}:
                        raise ValueError('archive source must be told or imported')
                    if type(record.get('holds', True)) is not bool:
                        raise ValueError('holds must be boolean')
                    for field in ('aliases', 'classes', 'owners', 'supersedes'):
                        _strings(record.get(field, []), field)
                    for field in ('kind', 'attribute'):
                        if field in record:
                            _string(record[field], field)
                prior = {}
                for record in records:
                    for target in record.get('supersedes', []):
                        if target not in prior or _key(prior[target]['word']) != _key(record['word']):
                            raise ValueError('supersedes must cite earlier same-word records')
                    prior[record['id']] = record
            self._sources[layer] = source
        try:
            encoded = json.dumps(self._sources, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        except (TypeError, ValueError) as exc:
            raise ValueError('knowledge sources must be finite JSON data') from exc
        self._revision = {layer: source['revision'] for layer, source in self._sources.items()}
        self._revision['sha256'] = hashlib.sha256(encoded).hexdigest()

    def snapshot(self):
        return deepcopy(dict(version=VERSION, sources=self._sources, revision=self._revision,
                             freshness='caller_attestation_only'))

    def world(self):
        live = self._sources.get('live', {})
        return deepcopy(live.get('entities', {}) if live.get('status') == 'current' else {})

    def append_archive(self, record, *, revision):
        """Return a new snapshot. Caller explicitly supplies status and provenance."""
        sources = deepcopy(self._sources)
        if 'archive' not in sources:
            raise ValueError('an archive source is required before appending')
        _string(revision, 'revision')
        if revision == sources['archive']['revision']:
            raise ValueError('append requires a new revision')
        sources['archive']['records'].append(deepcopy(record))
        sources['archive']['revision'] = revision
        return KnowledgeSnapshot(**sources)

    def _lexical(self, layer):
        records = self._sources.get(layer, {}).get('records', [])
        superseded = {identifier for row in records if row['status'] == 'ratified' and
                      row['source'] in {'told', 'manifest'} for identifier in row.get('supersedes', [])}
        result = []
        for row in records:
            reasons = []
            if row['status'] != 'ratified':
                reasons.append(row['status'])
            if row['source'] not in {'told', 'manifest'}:
                reasons.append('untrusted_source')
            if row['id'] in superseded:
                reasons.append('superseded_by_later_record')
            result.append(dict(id=row['id'], layer=layer, record=row, eligible=not reasons, reasons=reasons))
        return result

    def _class_paths(self, word, stack=(), budget=None):
        """Owner inheritance only. Conflicting class meanings remain alternatives."""
        word = _key(word)
        budget = [512] if budget is None else budget
        budget[0] -= 1
        if len(stack) >= 32 or budget[0] < 0:
            return set(), ['owner_inheritance_limit']
        if word in stack:
            return set(), ['cyclic_owner_inheritance']
        rows = []
        for layer in ('manifest', 'archive'):
            rows = [c['record'] for c in self._lexical(layer) if c['eligible'] and
                    _key(c['record']['word']) == word and c['record']['type'] == 'class']
            if rows:
                break
        ancestors, issues = {word}, []
        positive = [row for row in rows if row.get('holds', True)]
        if any(row.get('holds') is False for row in rows):
            issues.append('negative_owner_definition')
        if len(rows) > 1:
            issues.append('ambiguous_owner_definition')
        for row in positive:
            parents = row.get('classes', []) + ([row['kind']] if row.get('kind') else [])
            for parent in parents:
                found, errors = self._class_paths(parent, stack + (word,), budget)
                ancestors.update(found)
                issues.extend(errors)
        return ancestors, issues

    def lookup(self, term, owner=None):
        _string(term, 'lookup term')
        if owner is not None:
            _string(owner, 'owner')
        key = _key(term)
        candidates, issues = [], []
        live = self._sources.get('live', {})
        if live and live['status'] != 'current':
            issues.append('live_' + live['status'])
        for identifier, row in live.get('entities', {}).items():
            if key in {_key(v) for v in [row['name']] + row.get('aliases', [])}:
                eligible = live['status'] == 'current'
                candidates.append(dict(id=identifier, layer='live', record=row,
                                       eligible=eligible, reasons=[] if eligible else ['live_' + live['status']]))
        for layer in ('manifest', 'archive'):
            for candidate in self._lexical(layer):
                row = candidate['record']
                if key not in {_key(v) for v in [row['word']] + row.get('aliases', [])}:
                    continue
                if row.get('classes') and not row.get('kind') and not row.get('attribute'):
                    candidate['reasons'].append('class_target_inheritance_unsupported')
                    candidate['eligible'] = False
                owners = row.get('owners', [])
                if owners and candidate['eligible']:
                    if owner is None:
                        candidate['reasons'].append('owner_context_required')
                    else:
                        ancestors, errors = self._class_paths(owner)
                        candidate['reasons'].extend(errors)
                        if not ancestors.intersection({_key(o) for o in owners}):
                            candidate['reasons'].append('owner_mismatch')
                    candidate['eligible'] = not candidate['reasons']
                candidates.append(candidate)
        selected = []
        for layer in ('live', 'manifest', 'archive'):
            selected = [c for c in candidates if c['layer'] == layer and c['eligible']]
            if selected:
                break
        status = 'unsupported' if issues else 'unknown'
        if len(selected) > 1:
            status = 'ambiguous'
        elif selected:
            status = 'negative' if selected[0]['record'].get('holds') is False else 'resolved'
        elif candidates:
            status = 'unsupported'
        return deepcopy(dict(term=term, owner=owner, status=status, selected=selected,
                             candidates=candidates, evidence=candidates, issues=issues,
                             revision=self._revision))

    def annotate(self, source, proposal=None):
        """Exact lexical mention evidence; spans do not claim syntactic roles."""
        if not isinstance(source, str):
            raise ValueError('source must be text')
        terms = set()
        for row in self._sources.get('live', {}).get('entities', {}).values():
            terms.update([row['name']] + row.get('aliases', []))
        for layer in ('manifest', 'archive'):
            for row in self._sources.get(layer, {}).get('records', []):
                terms.update([row['word']] + row.get('aliases', []))
        mentions = []
        for term in sorted(terms, key=lambda t: (_key(t), t)):
            for match in re.finditer(r'(?<!\w)' + re.escape(term) + r'(?!\w)', source, re.I):
                mentions.append(dict(start=match.start(), end=match.end(), text=match.group(),
                                     lookup=self.lookup(match.group())))
        return dict(version=VERSION, revision=deepcopy(self._revision), mentions=mentions,
                    semantics='lexical mentions only; quotation, scope and roles are not inferred')
