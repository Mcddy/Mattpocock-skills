import copy
import unittest
from solve import solve
from verify import verify
from oracle import oracle


class SchedulingTests(unittest.TestCase):
    def test_malformed_certificate_controlled(self):
        d = {'capacity': 1, 'tasks': [{'id': 'a', 'duration': 1, 'resource': 1, 'after': []}]}
        for certificate in [[], None, 'cycle', {'cycle': [{}, {}]}, {'resource_exceeds_capacity': [{}]}]:
            self.assertFalse(verify(d, {'status': 'INFEASIBLE', 'certificate': certificate})['valid'])

    def test_independent_oracle_many_models(self):
        for capacity in (1, 2, 3):
            for duration in (1, 2, 3):
                for dependency in ([], ['A']):
                    d = {'capacity': capacity, 'tasks': [{'id': 'A', 'duration': duration, 'resource': 1, 'after': []}, {'id': 'B', 'duration': 2, 'resource': 1, 'after': dependency}]}
                    s, o = solve(d), oracle(d)
                    self.assertEqual(s['makespan'], o['makespan'])
                    self.assertTrue(verify(d, s)['valid'])

    def test_certificate_and_bound(self):
        d = {'capacity': 1, 'tasks': [{'id': 'A', 'duration': 2, 'resource': 2, 'after': []}]}
        self.assertTrue(verify(d, solve(d))['valid'])
        d['tasks'][0]['resource'] = 1
        d['tasks'][0]['after'] = ['A']
        self.assertTrue(verify(d, solve(d))['valid'])
        d['tasks'][0]['after'] = []
        d['tasks'].append({'id': 'B', 'duration': 2, 'resource': 1, 'after': []})
        self.assertEqual(solve(d, 1)['status'], 'UNRESOLVED')
        self.assertEqual(oracle(d, 1)['status'], 'UNRESOLVED')

    def test_bad_witness_and_boundary(self):
        d = {'capacity': 1, 'tasks': [{'id': 'A', 'duration': 2, 'resource': 1, 'after': []}, {'id': 'B', 'duration': 1, 'resource': 1, 'after': ['A']}]}
        s = solve(d)
        self.assertTrue(verify(d, s)['valid'])
        bad = copy.deepcopy(s); bad['starts']['B'] = 1
        self.assertFalse(verify(d, bad)['valid'])
        bad['starts']['B'] = True
        self.assertFalse(verify(d, bad)['valid'])
        d['capacity'] = True
        with self.assertRaises(ValueError): solve(d)


if __name__ == '__main__': unittest.main()
