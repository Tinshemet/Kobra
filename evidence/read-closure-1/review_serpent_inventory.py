from collections import Counter
from pathlib import Path
import json,hashlib
from serpent.planner import build_pool,Options
from serpent.vectors import VECTOR_IDS,load_vector
from serpent.scenarios import generate_scenarios
import serpent
out=Path('/home/tinshemet/Desktop/kobra/evidence/read-closure-1')
options=Options(noise='off',typos='off',distribution='balanced',strength=2)
rows=[]
for name in ('canonical',*VECTOR_IDS):
    vector=None if name=='canonical' else load_vector(name)
    pool,digest=build_pool(20261011013,options,vector)
    examples={}
    for item in pool:examples.setdefault(item.family,item.case.sentence)
    rows.append(dict(vector=name,backend='grammar' if vector is None else vector['backend'],
        cases=len(pool),families=dict(Counter(i.family for i in pool)),examples=examples,pool_sha256=digest))
root=Path(serpent.__file__).parent
report=dict(generator_version=serpent.__version__,kind='inventory coverage review; no Kobra accuracy claim',vectors=rows,
    source_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.suffix in ('.py','.json')})
(out/'serpent-inventory-review.json').write_text(json.dumps(report,indent=2)+'\n')
scenarios=generate_scenarios(16,20261011013)
(out/'serpent-context-samples.json').write_text(json.dumps(scenarios,indent=2)+'\n')
print(json.dumps([dict(vector=r['vector'],cases=r['cases'],families=len(r['families'])) for r in rows],indent=2))
