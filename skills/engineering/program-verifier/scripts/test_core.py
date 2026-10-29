import unittest
from verify import run, observations, shrink, target_function, difference, outcome, oracle


class VerifierTests(unittest.TestCase):
    def test_good_controls(self):
        for c in ['ascii-spaces', 'integer-range', 'sort-integers']:
            r = run({'contract': c, 'cases': 250})
            self.assertEqual(r['status'], 'FINITE_CHECKS_PASS')

    def test_detect_and_preserve_category(self):
        for c, target in [('ascii-spaces', 'whitespace'), ('ascii-spaces', 'ascii-loss'), ('ascii-spaces', 'coerce'), ('integer-range', 'bool-int'), ('integer-range', 'exclusive-upper'), ('sort-integers', 'unique-sort')]:
            spec = {'contract': c, 'cases': 200}
            result = run(spec, target)
            self.assertGreater(result['differential_failures'], 0)
            fn = target_function(spec, target)
            for failure in result['retained_failures']:
                x = failure['shrunk']['input']
                self.assertEqual(failure['category'], difference(outcome(lambda x: oracle(spec, x), x), outcome(fn, x)))

    def test_observations_and_lexical_number(self):
        r = observations({'contract': 'integer-range', 'observations': [{'value': True, 'accepted': True}, {'value': 2.0, 'accepted': True}, {'value': 3, 'accepted': False}, {'value': 0, 'accepted': True}]})
        self.assertEqual(r['failure_count'], 3)
        r = observations({'contract': 'ascii-spaces', 'observations': [{'input': 'A\tB', 'output': 'A B'}, {'input': 'café', 'output': 'cafe'}, {'input': 'A B', 'output': 'A B'}]})
        self.assertEqual(r['failure_count'], 2)
        with self.assertRaises(ValueError): run({'contract': 'ascii-spaces', 'cases': True})


if __name__ == '__main__': unittest.main()
