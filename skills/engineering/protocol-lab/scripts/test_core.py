import unittest
from check import explore, replay


class ProtocolTests(unittest.TestCase):
    def test_duplicate_graph_rejected_valid_neighbour_replays(self):
        edge = {'from': 'a', 'to': 'bad', 'event': 'go'}
        g = {'kind': 'graph', 'initial': 'a', 'states': {'a': {'safe': True}, 'bad': {'safe': False}}, 'transitions': [edge, dict(edge)]}
        with self.assertRaises(ValueError): explore(g)
        g['transitions'] = [edge]
        self.assertTrue(replay(g, explore(g))['valid_trace'])

    def test_volatile_failure_and_replay(self):
        s = {'kind': 'append', 'strategy': 'volatile', 'operations': ['op7'], 'max_events': 8, 'max_states': 10000}
        r = explore(s)
        self.assertEqual(r['status'], 'COUNTEREXAMPLE')
        self.assertEqual(r['depth'], 6)
        p = replay(s, r)
        self.assertTrue(p['valid_trace']); self.assertFalse(p['safe'])
        s['strategy'] = 'durable'
        self.assertTrue(replay(s, r)['safe'])
        self.assertNotEqual(explore(s)['status'], 'COUNTEREXAMPLE')

    def test_controls_and_unknown_outcome(self):
        s = {'kind': 'append', 'strategy': 'durable', 'operations': ['op7']}
        r = replay(s, [{'event': 'send', 'op': 'op7'}, {'event': 'deliver', 'index': 0}, {'event': 'drop', 'index': 0}])
        self.assertEqual(r['summary']['unknown_outcomes'], ['op7'])
        self.assertEqual(r['summary']['reconciliation']['op7'], 'committed')
        delivered = replay(s, [{'event': 'send', 'op': 'op7'}, {'event': 'deliver', 'index': 0}, {'event': 'deliver', 'index': 0}])
        self.assertEqual(delivered['summary']['client_completed'], ['op7'])
        self.assertFalse(replay(s, [{'event': 'deliver', 'index': 0}])['valid_trace'])

    def test_graph_bounds_and_shortest(self):
        s = {'kind': 'graph', 'initial': 'a', 'states': {'a': {'safe': True}, 'b': {'safe': False}}, 'transitions': [{'from': 'a', 'to': 'b', 'event': 'bug'}]}
        r = explore(s); self.assertEqual(r['depth'], 1); self.assertFalse(replay(s, r)['safe'])
        s['max_states'] = 1
        self.assertEqual(explore(s)['status'], 'UNRESOLVED')
        s['max_states'] = True
        with self.assertRaises(ValueError): explore(s)


if __name__ == '__main__': unittest.main()
