import unittest

from kobra.knowledge import KnowledgeSnapshot


def row(identifier='r1', word='jumpbox', **kw):
    return dict(id=identifier, word=word, type='class', source='told', status='ratified',
                provenance='operator turn 12', **kw)


def archive(*records):
    return dict(revision='a1', source='operator-ledger', records=list(records))


def live(entities=None, status='current'):
    return dict(revision='w1', source='test-adapter', status=status,
                entities=entities or {'vm-1': {'name': 'Alpha', 'aliases': ['jumpbox']}})


class KnowledgeTests(unittest.TestCase):
    def test_live_precedes_negative_memory_and_manifest(self):
        memory = row(holds=False)
        declared = row('m1', kind='computer')
        declared['source'] = 'manifest'
        k = KnowledgeSnapshot(live=live(), archive=archive(memory),
                              manifest=dict(revision='m1', source='design', records=[declared]))
        result = k.lookup('JUMPBOX')
        self.assertEqual('live', result['selected'][0]['layer'])
        self.assertEqual(3, len(result['evidence']))
        self.assertEqual('resolved', result['status'])

    def test_manifest_precedes_archive(self):
        declared = row('m1', kind='computer')
        declared['source'] = 'manifest'
        k = KnowledgeSnapshot(archive=archive(row(kind='other')),
                              manifest=dict(revision='m1', source='design', records=[declared]))
        self.assertEqual('manifest', k.lookup('jumpbox')['selected'][0]['layer'])
        self.assertEqual({}, k.world())

    def test_pending_imported_superseded_never_resolve(self):
        for field, value in [('status', 'pending'), ('status', 'superseded'), ('source', 'imported')]:
            record = row()
            record[field] = value
            result = KnowledgeSnapshot(archive=archive(record)).lookup('jumpbox')
            self.assertEqual('unsupported', result['status'])
            self.assertEqual([], result['selected'])
            self.assertEqual(1, len(result['evidence']))

    def test_negative_is_not_missing(self):
        k = KnowledgeSnapshot(archive=archive(row(holds=False)))
        self.assertEqual('negative', k.lookup('jumpbox')['status'])
        self.assertEqual('unknown', k.lookup('other')['status'])
        self.assertEqual({}, k.world())

    def test_live_collisions_and_id_is_not_alias(self):
        k = KnowledgeSnapshot(live=live({'Alpha': {'name': 'Beta'}, 'id2': {'name': 'Alpha'},
                                        'id3': {'name': 'ALPHA'}}))
        result = k.lookup('Alpha')
        self.assertEqual('ambiguous', result['status'])
        self.assertEqual(['id2', 'id3'], [c['id'] for c in result['selected']])
        self.assertEqual('unknown', k.lookup('id2')['status'])

    def test_stale_and_unavailable_are_not_empty_current(self):
        for status in ['stale', 'unavailable']:
            k = KnowledgeSnapshot(live=live(status=status))
            self.assertEqual({}, k.world())
            result = k.lookup('Alpha')
            self.assertEqual('unsupported', result['status'])
            self.assertIn('live_' + status, result['issues'])
            self.assertEqual(1, len(result['evidence']))
        self.assertEqual('unknown', KnowledgeSnapshot(live=live({'x': {'name': 'X'}})).lookup('none')['status'])

    def test_explicit_owner_inheritance_and_cycles(self):
        attribute = row('ram', 'RAM', owners=['computer'], attribute='memory')
        attribute['type'] = 'attribute'
        k = KnowledgeSnapshot(archive=archive(attribute, row('vm', 'vm', classes=['computer'])))
        self.assertEqual('unsupported', k.lookup('RAM')['status'])
        self.assertEqual('resolved', k.lookup('RAM', owner='vm')['status'])
        self.assertEqual('unsupported', k.lookup('RAM', owner='printer')['status'])
        cyclic = KnowledgeSnapshot(archive=archive(attribute, row('vm', 'vm', classes=['computer']),
                                                   row('pc', 'computer', classes=['vm'])))
        result = cyclic.lookup('RAM', owner='vm')
        self.assertEqual('unsupported', result['status'])
        self.assertIn('cyclic_owner_inheritance', result['candidates'][0]['reasons'])

    def test_multiple_owned_meanings_not_first_match(self):
        a = row('a', 'size', owners=['computer'], attribute='memory')
        b = row('b', 'size', owners=['computer'], attribute='storage')
        a['type'] = b['type'] = 'attribute'
        k = KnowledgeSnapshot(archive=archive(a, b))
        self.assertEqual('ambiguous', k.lookup('size', owner='computer')['status'])

    def test_immutable_append_supersession_and_pending_cannot_override(self):
        k = KnowledgeSnapshot(archive=archive(row(kind='computer')))
        pending = row('r2', kind='printer', supersedes=['r1'])
        pending['status'] = 'pending'
        p = k.append_archive(pending, revision='a2')
        self.assertEqual('r1', p.lookup('jumpbox')['selected'][0]['id'])
        replacement = row('r3', kind='router', supersedes=['r1', 'r2'])
        newest = p.append_archive(replacement, revision='a3')
        self.assertEqual('r3', newest.lookup('jumpbox')['selected'][0]['id'])
        self.assertEqual('r1', k.lookup('jumpbox')['selected'][0]['id'])
        self.assertEqual(3, len(newest.lookup('jumpbox')['evidence']))
        self.assertNotEqual(k.snapshot()['revision']['sha256'], newest.snapshot()['revision']['sha256'])
        with self.assertRaises(ValueError):
            k.append_archive(replacement, revision='a1')

    def test_defensive_copies_and_finite_json(self):
        source = live()
        k = KnowledgeSnapshot(live=source)
        source['entities']['vm-1']['name'] = 'mutated'
        k.world()['vm-1']['name'] = 'changed'
        k.lookup('Alpha')['selected'][0]['record']['name'] = 'changed'
        k.snapshot()['sources']['live']['entities'].clear()
        self.assertEqual('Alpha', k.world()['vm-1']['name'])
        bad = live()
        bad['entities']['vm-1']['value'] = float('nan')
        with self.assertRaises(ValueError):
            KnowledgeSnapshot(live=bad)

    def test_source_spans_repeat_and_full_word_boundaries(self):
        k = KnowledgeSnapshot(live=live())
        source = 'Alpha then "Alpha", not Alphabet.'
        mentions = k.annotate(source)['mentions']
        self.assertEqual(2, len(mentions))
        for mention in mentions:
            self.assertEqual('Alpha', source[mention['start']:mention['end']])

    def test_malformed_sources_are_explicit(self):
        bad = live()
        del bad['status']
        with self.assertRaises(ValueError):
            KnowledgeSnapshot(live=bad)
        for records in [[row(), row()], [row(supersedes=['missing'])], [row(holds='false')]]:
            with self.assertRaises(ValueError):
                KnowledgeSnapshot(archive=archive(*records))
        with self.assertRaises(ValueError):
            KnowledgeSnapshot(archive=archive(row(typex=object())))

    def test_class_target_chain_explicitly_unsupported(self):
        k = KnowledgeSnapshot(archive=archive(row(classes=['computer'])))
        result = k.lookup('jumpbox')
        self.assertEqual('unsupported', result['status'])
        self.assertIn('class_target_inheritance_unsupported', result['candidates'][0]['reasons'])

    def test_inheritance_depth_limit_and_unknown_owner(self):
        attribute = row('ram', 'RAM', owners=['computer'], attribute='memory')
        attribute['type'] = 'attribute'
        rows = [row('c' + str(i), 'c' + str(i), classes=['c' + str(i + 1)]) for i in range(100)]
        k = KnowledgeSnapshot(archive=archive(attribute, *rows))
        result = k.lookup('RAM', owner='c0')
        self.assertEqual('unsupported', result['status'])
        self.assertIn('owner_inheritance_limit', result['candidates'][0]['reasons'])
        self.assertEqual('unsupported', k.lookup('RAM', owner='unlisted')['status'])

    def test_negative_owner_definition_does_not_license_property(self):
        attribute = row('ram', 'RAM', owners=['computer'], attribute='memory')
        attribute['type'] = 'attribute'
        k = KnowledgeSnapshot(archive=archive(attribute, row('computer', 'computer', holds=False)))
        result = k.lookup('RAM', owner='computer')
        self.assertEqual('unsupported', result['status'])
        self.assertIn('negative_owner_definition', result['candidates'][0]['reasons'])
