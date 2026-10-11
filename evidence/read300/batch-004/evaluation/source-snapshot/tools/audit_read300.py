"""Offline replay of every captured model response; no new inference."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from kobra import ArrangingReader, ClientConfig, IdentityFrontDoor, LinguisticCandidates, Request, Services
from kobra.ollama import OllamaProvider, ConstrainedSelectionProvider
from evaluate_arrangement import ledger_valid
from evaluate_selection import dump, score


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path)
    args = ap.parse_args()
    manifest=json.loads((args.output/'manifest.json').read_text())
    root=Path(__file__).resolve().parents[1]
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert all(digest(root/p)==h for p,h in manifest['source_hashes'].items())
    batch=args.output.parent
    assert digest(batch/'frozen-reference.json')==manifest['fixture_sha256']
    assert digest(batch/'serpent-source-cases.json')==manifest['source_cases_sha256']
    assert digest(batch/'generator-manifest.json')==manifest['generator_manifest_sha256']
    gold={c['id']:c for c in json.loads((batch/'frozen-reference.json').read_text())['cases']}
    extractor=LinguisticCandidates()
    assert all(digest(Path(extractor.nlp.path)/p)==h for p,h in manifest['parser_hashes'].items())
    reader=ArrangingReader(extractor)
    records=[json.loads(l) for l in (args.output/'cases.jsonl').read_text().splitlines()]
    assert len(records)==300 and len({r['id'] for r in records})==300
    replayed=0;transport_failures=[]
    for row in records:
        assert row['text']==gold[row['id']]['text']
        exchange=row['exchange']
        if not exchange or 'response' not in exchange:
            # A network failure is not replayable as a returned model response.
            transport_failures.append(row['id'])
            assert not row['score']['exact']
            continue
        provider_type=ConstrainedSelectionProvider if manifest.get('transport')=='constrained' else OllamaProvider
        provider=provider_type(think=manifest.get('thinking'))
        def replay(path,payload=None):
            assert path=='/api/chat'
            actual=dict(payload);expected=dict(exchange['request'])
            actual.pop('model');expected.pop('model')
            assert actual==expected
            return exchange['response']
        provider._request=replay
        services=Services(ClientConfig('read300','1'),model=provider)
        request=Request(row['text'])
        result=reader.read(IdentityFrontDoor().normalize(request,services),request,services)
        assert json.loads(json.dumps(asdict(result)))==row['result'],row['id']
        assert ledger_valid(result)==row['source_retained']
        predicted=[{'act':f.act,**{s:v if isinstance(v,str) else v.text for s,v in f.slots.items()}} for f in result.frames]
        assert predicted==row['selected']
        expected=gold[row['id']]['expected']
        rescored=score(expected or [],predicted)
        if expected is None:
            rescored['exact']=False
            rescored['adapter_error']=gold[row['id']]['adapter_error']
        assert rescored==row['score']
        replayed+=1
    summary=json.loads((args.output/'summary.json').read_text())
    assert summary['exact_cases']==sum(r['score']['exact'] for r in records)
    assert summary['source_retention_cases']==sum(r['source_retained'] for r in records)
    result={'state':'verified','response_replays':replayed,'transport_failures':transport_failures,
            'source_hashes_verified':True,'new_model_calls':0,'cases':300,'exact_cases':summary['exact_cases']}
    dump(args.output/'offline-audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
