"""Independent Serpent graphs plus declared memory-contract fixtures; never READ predictions."""
from collections import Counter
from copy import deepcopy
import hashlib, json, random
from itertools import product
from pathlib import Path
from serpent.grammar import Clause, NounPhrase, simple_clause
from serpent.scenarios import reference_case
from serpent.validate import validate_case
from serpent_slots import project
from generate_read300 import known_inputs, normalized
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/memory5000-1'
SEED=20261011051
FAMILIES=('live_exact','live_alias','ledger_confirmed','ledger_corrected','ledger_alias',
 'live_collision','stale','unavailable','ledger_reported','ledger_disputed','ledger_missing',
 'ledger_mismatch','ledger_number','ledger_conflict','no_history',
 'archive_ratified','archive_pending','archive_imported','archive_negative','archive_superseded')

def main():
    OUT.mkdir(exist_ok=False)
    paths=[*(ROOT/'src/kobra').glob('*.py'),*(ROOT/'tools').glob('*.py')]
    freeze={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (OUT/'reader-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    seen=known_inputs();pool={};rejected=0
    for verb,noun,person,number,tense,voice,form,negative in product(
        ('check','move','carry','repair','show','see'),('box','key','lamp','disk','book','server','sensor','train'),
        ('alex','mira','nia'),('singular','plural'),('present','past','future'),('active','passive'),('declarative','interrogative'),(False,True)):
        try:
            case=simple_clause('S000001',Clause(NounPhrase('p_'+person),'v_'+verb,NounPhrase('n_'+noun,number=number),tense=tense,voice=voice,form=form,negative=negative))
            validate_case(case)
        except ValueError:
            rejected+=1;continue
        key=normalized(case.sentence)
        if key not in seen:pool[key]=case
    candidates=list(pool.values());random.Random(SEED).shuffle(candidates)
    assert len(candidates)>=1000,len(candidates)
    inputs=[];gold=[];graphs=[]
    def add(family,case,kwargs,bindings,reason=None,lexical=None):
        identifier=f'M{len(inputs)+1:05d}'
        inputs.append(dict(id=identifier,family=family,text=case.sentence,**kwargs))
        gold.append(dict(id=identifier,expected=project(case.to_dict()),bindings=bindings,ask_reason=reason,lexical=lexical))
        graphs.append(dict(id=identifier,source_graph=case.to_dict()))
    for case in candidates[:1000]:add('parsing_fresh',case,{}, {})
    for family in FAMILIES:
      for i in range(200):
        noun=('box','key','lamp','disk')[i%4];other=('lamp' if noun!='lamp' else 'box')
        verb=('move','carry','check','move')[i%4]
        reference=family.startswith('ledger_') or family=='no_history'
        case=reference_case('S000001','v_'+verb) if reference else simple_clause('S000001',Clause(None,'v_'+verb,NounPhrase('n_'+noun),form='imperative'))
        validate_case(case)
        eid=f'{family}-object-{i}';oid=f'{family}-other-{i}'
        record=dict(name=noun,number='singular')
        live=dict(revision=f'live-{family}-{i}',source='independent-fixture',status='current',entities={eid:record})
        history=[dict(id='t1',role='user',content=noun)]
        claim=dict(id='c1',turn_id='t1',start=0,end=len(noun),quote=noun,status='confirmed_by_client',reference='it',entity_id=eid)
        claims=[claim]; bindings={'it' if reference else 'the '+noun:eid};reason=None;lexical=None
        if family=='live_alias':record.update(name='primary '+noun,aliases=[noun])
        if family=='ledger_alias':record.update(name='primary '+noun,aliases=[noun])
        if family=='live_collision':
            live['entities'][oid]=dict(name='other '+noun,aliases=[noun]);bindings={};reason='knowledge_ambiguous:0:patient'
        if family in ('stale','unavailable'):
            live['status']=family;bindings={};reason='knowledge_live_'+family
        if family in ('ledger_reported','ledger_disputed'):
            claim['status']='reported' if family=='ledger_reported' else 'disputed';bindings={}
            reason='memory_unconfirmed_reference:it' if family=='ledger_reported' else 'memory_disputed_reference:it'
        if family=='ledger_missing':live['entities']={};bindings={};reason='memory_missing_entity:it'
        if family=='ledger_mismatch':record['name']=other;bindings={};reason='memory_evidence_name_mismatch:it'
        if family=='ledger_number':record['number']='plural';bindings={};reason='memory_number_not_supported:it'
        if family in ('ledger_corrected','ledger_conflict'):
            live['entities'][oid]=dict(name=other,number='singular')
            history.append(dict(id='t2',role='user',content=other))
            claims.append(dict(id='c2',turn_id='t2',start=0,end=len(other),quote=other,status='confirmed_by_client',reference='it',entity_id=oid))
            if family=='ledger_corrected':claim.update(status='superseded',superseded_by='c2');bindings={'it':oid}
            else:bindings={};reason='memory_ambiguous_reference:it'
        if family=='no_history':history=[];claims=[];bindings={};reason='memory_unconfirmed_reference:it'
        knowledge={'live':live}
        if family.startswith('archive_'):
            bindings={};r=dict(id='lex1',word=noun,type='class',source='told',status='ratified',provenance='fixture-human',kind='object')
            if family=='archive_pending':r['status']='pending';reason='knowledge_unsupported:0:patient'
            if family=='archive_imported':r['source']='imported';reason='knowledge_unsupported:0:patient'
            if family=='archive_negative':r['holds']=False;reason='knowledge_negative:0:patient'
            records=[r];selected='lex1'
            if family=='archive_superseded':
                records.append(dict(r,id='lex2',kind='container',supersedes=['lex1']));selected='lex2'
            knowledge={'archive':dict(revision=f'archive-{i}',source='fixture',records=records)}
            if reason is None:lexical=selected
        kwargs=dict(knowledge=knowledge,history=history if reference else [],context_claims=claims if reference else [])
        add(family,case,kwargs,bindings,reason,lexical)
    assert len(inputs)==len(gold)==5000
    for name,rows in [('inputs',inputs),('gold',gold),('source-graphs',graphs)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    manifest=dict(seed=SEED,cases=5000,by_family=dict(Counter(r['family'] for r in inputs)),
        distinct_source_sentences=len({normalized(r['text']) for r in inputs}),
        unique_full_inputs=len({json.dumps({k:v for k,v in r.items() if k not in ('id','family')},sort_keys=True) for r in inputs}),
        parsing_fresh=1000,eligible_parsing_pool=len(pool),generator_constraint_rejections=rejected,
        note='4000 memory contract cases are 20 patterns x 200 combinations, including changed IDs/revisions; not 4000 independent language phenomena. History reference claims are client-confirmed fixtures, not automatic pronoun inference.',
        files={n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in ('inputs.jsonl','gold.jsonl','source-graphs.jsonl','reader-freeze.json')})
    import serpent
    sr=Path(serpent.__file__).parent
    manifest['serpent_version']=serpent.__version__
    manifest['serpent_source_hashes']={str(p.relative_to(sr)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sr.rglob('*') if p.suffix in ('.py','.json')}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','serpent_source_hashes')},indent=2))
if __name__=='__main__':main()
