import unittest
from kobra.confidence_gate import GatedRuleReader,ConfidenceGate
from kobra.rule_assignment import RuleAssigner
from kobra.resolve_distillation import distill_for_resolve

class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reader=GatedRuleReader(RuleAssigner(),ConfidenceGate())
    def test_metadata_cannot_override_gate(self):
        caller={'request_id':'r1','ready_for_resolve':True,'groundings':{'it':'ghost'}}
        out=self.reader.read_for_resolve('Move it.',metadata=caller)
        self.assertFalse(out['state']['ready_for_resolve'])
        self.assertEqual(out['metadata']['caller']['request_id'],'r1')
        self.assertEqual(out['points'][0]['identity_bindings'],[])
        caller['groundings'].clear()
        self.assertEqual(out['metadata']['caller']['groundings'],{'it':'ghost'})
    def test_partition_exact_and_unicode_offsets(self):
        for text in ('Open and read the file.','Hello Zoë, please open the file.','🤔 what did she mean?',''):
            out=self.reader.read_for_resolve(text) if text else distill_for_resolve(dict(source='',proposal={'frames':[]},route='ASK'))
            parts=out['text_accounting']['partition']
            self.assertEqual(''.join(p['text'] for p in parts),text)
            self.assertEqual(out['metadata']['accounted_characters'],len(text))
            self.assertEqual(out['metadata']['discarded_characters'],0)
            for a,b in zip(parts,parts[1:]):self.assertEqual(a['end'],b['start'])
    def test_unparsed_is_not_garbage(self):
        out=self.reader.read_for_resolve('If the server fails, restart it.')
        self.assertEqual(out['text_accounting']['garbage'],[])
        self.assertEqual(out['text_accounting']['unresolved'][0]['text'],'If the server fails, restart it.')
    def test_explicit_garbage_annotation_does_not_delete_negation(self):
        text='Was the sensor not moved by Mira?';a=text.index('not')
        out=self.reader.read_for_resolve(text,annotations=[dict(start=a,end=a+3,text='not',category='garbage',reason='deliberately wrong fixture',provenance='test')])
        self.assertEqual(out['points'][0]['qualifiers']['negation'],'not')
        entry=out['text_accounting']['garbage'][0]
        self.assertTrue(entry['retained']);self.assertTrue(entry['overlaps_point_evidence'])
        self.assertEqual(entry['status'],'caller_annotation_not_semantically_verified')
    def test_bad_annotations_rejected(self):
        for item in [dict(start=0,end=4,text='fake',category='noise',reason='x',provenance='test'),dict(start=0,end=4,text='Move',category='garbage')]:
            with self.assertRaises(ValueError):self.reader.read_for_resolve('Move it.',annotations=[item])
    def test_finite_metadata_only(self):
        for metadata in ([],{'confidence':float('nan')},{'x':object()}):
            with self.assertRaises(ValueError):self.reader.read_for_resolve('Move it.',metadata=metadata)

    def test_calibration_is_distinct_from_missing_context(self):
        out=self.reader.read_for_resolve('Move it.',missing_context=['target'])
        items=out['text_accounting']['open_items']
        self.assertTrue(any(i['kind']=='missing_context' and i['reason']=='missing_context:target' for i in items))
        self.assertTrue(any(i['kind']=='reference_resolution' for i in items))
        out=self.reader.read_for_resolve('Move the box.')
        self.assertTrue(any(i['kind']=='calibration' for i in out['text_accounting']['open_items']))
