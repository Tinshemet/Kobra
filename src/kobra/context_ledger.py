"""In-memory context evidence; persistence and fact acceptance belong to the client."""
from copy import deepcopy
import hashlib
import re


def context_snapshot(history=(), world=None, claims=()):
    turns = []
    ids = set()
    for i, turn in enumerate(history, 1):
        identifier = turn.get('id', f'turn-{i}')
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError('turn IDs must be unique nonempty strings')
        text = turn.get('content')
        if not isinstance(text, str) or turn.get('role') not in ('user','assistant','system','tool'):
            raise ValueError('each turn requires a role and exact content')
        ids.add(identifier)
        turns.append(dict(id=identifier,role=turn['role'],content=text,
                          sha256=hashlib.sha256(text.encode()).hexdigest()))
    entities = []
    for identifier, data in (world or {}).items():
        if not isinstance(identifier, str) or not identifier or not isinstance(data, dict):
            raise ValueError('WORLD must map nonempty IDs to entity records')
        mentions=[]
        name=data.get('name')
        if isinstance(name,str) and name:
            for turn in turns:
                for match in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',turn['content'],re.I):
                    mentions.append(dict(turn_id=turn['id'],start=match.start(),end=match.end(),text=match.group()))
        entities.append(dict(id=identifier,record=deepcopy(data),mentions=mentions,
                             provenance='caller_supplied_WORLD',truth_status='not_verified_by_READ'))
    checked=[]
    claim_ids=set()
    for claim in claims:
        c=deepcopy(claim)
        if not isinstance(c.get('id'),str) or not c['id'] or c['id'] in claim_ids:
            raise ValueError('claim IDs must be unique nonempty strings')
        turn=next((t for t in turns if t['id']==c.get('turn_id')),None)
        start,end=c.get('start'),c.get('end')
        if turn is None or type(start) is not int or type(end) is not int or not 0<=start<end<=len(turn['content']):
            raise ValueError('claim must cite a valid prior-turn span')
        if turn['content'][start:end]!=c.get('quote'):
            raise ValueError('claim quote does not match source')
        if c.get('status','reported') not in ('reported','confirmed_by_client','superseded','disputed'):
            raise ValueError('unknown claim status')
        if 'reference' in c or 'entity_id' in c:
            if (not isinstance(c.get('reference'), str) or c['reference'].casefold() not in
                    {'it','this','that','them','these','those'} or
                    not isinstance(c.get('entity_id'), str) or not c['entity_id']):
                raise ValueError('reference claims require a supported pronoun and nonempty entity ID')
        if 'reference_scope' in c:
            scope=c['reference_scope']
            if (not c.get('reference') or not isinstance(scope,dict) or set(scope)!={'source_sha256','frame','slot'}
                    or not isinstance(scope['source_sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',scope['source_sha256'])
                    or type(scope['frame']) is not int or scope['frame']<0
                    or scope['slot'] not in {'agent','patient','recipient'}):
                raise ValueError('reference scope requires source hash, frame and role')
        c.setdefault('status','reported');claim_ids.add(c['id']);checked.append(c)
    for c in checked:
        target=c.get('superseded_by')
        if target is not None and (target not in claim_ids or target==c['id'] or c['status']!='superseded'):
            raise ValueError('supersession must link to another recorded claim')
    for c in checked:
        if c.get('reference') and c.get('superseded_by'):
            replacement=next(x for x in checked if x['id']==c['superseded_by'])
            if replacement.get('reference','').casefold()!=c['reference'].casefold():
                raise ValueError('reference supersession must preserve the reference cue')
    successors={c['id']:c.get('superseded_by') for c in checked}
    for identifier in successors:
        seen=set()
        while identifier is not None:
            if identifier in seen:
                raise ValueError('cyclic claim supersession')
            seen.add(identifier);identifier=successors[identifier]
    return dict(version='context-ledger-1',previous_turns=turns,world_entities=entities,
                claims=checked,history_supplied=bool(turns),world_supplied=bool(entities),
                semantics='recorded evidence and caller assertions, not inferred or verified facts')
