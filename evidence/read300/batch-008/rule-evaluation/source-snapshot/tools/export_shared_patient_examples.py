"""Capture paired development examples and a live/archive/ledger integration trace."""
import hashlib
import html
import json
from pathlib import Path
from kobra.rule_assignment import RuleAssigner
from kobra.confidence_gate import ConfidenceGate, GatedRuleReader
from kobra.knowledge import KnowledgeSnapshot

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/shared-patients-1'


def main():
    assigner = RuleAssigner()
    before = json.loads((OUT / 'before.json').read_text())
    after = [dict(text=row['text'], proposal=assigner.assign(row['text'])) for row in before]
    (OUT / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
    ticks = [new['text'] for old, new in zip(before, after)
             if old['proposal']['route'] != 'code' and new['proposal']['route'] == 'code']
    assert len(ticks) == 7
    assert all(r['proposal']['route'] == 'unresolved' for r in after[7:])
    knowledge = KnowledgeSnapshot(
        live=dict(revision='shared-fixture-live-1', source='explicit-fixture', status='current',
                  entities={'old-1': {'name': 'Alpha'}, 'old-2': {'name': 'ALPHA'}}),
        archive=dict(revision='shared-fixture-archive-1', source='explicit-fixture', records=[
            dict(id='definition-1', word='Alpha', type='class', kind='vm', source='told',
                 status='ratified', provenance='explicit-fixture')]))
    history = [dict(id='u1', role='user', content='Alpha was the old test machine.')]
    result = GatedRuleReader(assigner, ConfidenceGate(), knowledge=knowledge).read(
        'Create and launch Alpha, then delete it.', history=history)
    assert result['reasons'] == ['uncalibrated_cohort']
    assert not result['knowledge_evidence']['bindings']
    assert result['context_ledger']['previous_turns'][0]['content'] == history[0]['content']
    paths = ['src/kobra/rule_assignment.py', 'src/kobra/structural_read.py', 'src/kobra/surface_chunks.py',
             'src/kobra/shared_patients.py', 'src/kobra/knowledge.py', 'src/kobra/knowledge_resolution.py',
             'src/kobra/confidence_gate.py', 'tools/export_shared_patient_examples.py']
    payload = dict(kind='selected development examples; no fresh accuracy measurement', new_model_calls=0,
                   newly_code_supported=ticks, retained_unresolved=8, integration=result,
                   source_hashes={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths})
    (OUT / 'summary.json').write_text(json.dumps(payload, indent=2) + '\n')
    cards = []
    for old, new in zip(before, after):
        cards.append('<article><h2>' + html.escape(new['text']) + '</h2><p>Before: ' +
                     old['proposal']['route'] + ' → After: ' + new['proposal']['route'] +
                     '</p><details><summary>Actual before and after JSON</summary><pre>' +
                     html.escape(json.dumps(dict(before=old['proposal'], after=new['proposal']), indent=2)) +
                     '</pre></details></article>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>READ shared objects</title><style>body{max-width:1000px;margin:40px auto;padding:20px;background:#101b2c;color:#edf3ff;font:17px/1.6 system-ui}article{border:1px solid #50647c;padding:20px;margin:20px 0;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}summary{cursor:pointer}</style><h1>Shared objects across actions</h1><p>15 selected development cases: 7 newly code-supported, 8 remain unresolved. This is not a fresh accuracy sample. No live AI calls. Code-supported proposals still require external calibration.</p><p>Supported patterns preserve one noun-phrase span and one local entity. Creation stays distinct from current library identity. General scope and attachment remain unfinished.</p>'''
    page += ''.join(cards) + '<h2>Archive, library and ledger together</h2><p>Two old objects named Alpha remain in WORLD. The new Alpha stays a sentence-local description, its archive type is retained, and the previous turn survives. Final route is ASK because calibration is absent.</p><pre>' + html.escape(json.dumps(result, indent=2)) + '</pre></html>'
    (ROOT / 'reports/read-shared-patients-current.html').write_text(page)
    print(json.dumps(dict(development_cases=15, newly_code_supported=len(ticks), retained_unresolved=8, new_model_calls=0)))

if __name__ == '__main__':
    main()
