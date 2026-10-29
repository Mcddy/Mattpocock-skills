from pathlib import Path
import unittest
from perf import bench, analyse, baseline, candidate, reference, corrupt, workload, canonical


class PerfTests(unittest.TestCase):
    def test_duplicate_pair_rejected_before_unpaired_fallback(self):
        path = Path(__file__).resolve().parents[1] / 'assets' / 'duplicate-pair-control.csv'
        with self.assertRaisesRegex(ValueError, 'duplicate arm/stratum/pair'):
            analyse(path, {'ok': {'sum': 2}}, {'sum': 2})

    def test_equivalence_and_actual_paired_runs(self):
        for n in [2, 7, 13, 40]:
            rows = workload(n)
            self.assertEqual(baseline(rows), reference(rows))
            self.assertEqual(candidate(rows), reference(rows))
            self.assertNotEqual(corrupt(rows), reference(rows))
        result = bench([10, 20, 40], repeats=3, seconds=3)
        self.assertEqual(len(result['runs']), 18)
        self.assertTrue(all(r['correct'] for r in result['runs']))
        self.assertEqual(len(result['profiles']), 2)
        self.assertEqual(result['completed_sizes'], [10, 20, 40])

    def test_invalid_and_distinct_boolean_output(self):
        self.assertNotEqual(canonical(True), canonical(1))
        for sizes in [[True], [0], [20, 10], [2001]]:
            with self.assertRaises(ValueError): bench(sizes)
        with self.assertRaises(ValueError): bench([10], seconds=float('nan'))

    def test_supplied_rows_retained_and_stratified(self):
        path = Path(__file__).resolve().parents[1] / 'assets' / 'control-records.csv'
        result = analyse(path, {'ok': {'sum': 2}, 'bad': {'sum': 1}}, {'sum': 2})
        self.assertFalse(result['executed_here'])
        self.assertEqual(len(result['rejected_runs']), 1)
        self.assertEqual(result['comparisons'][0]['status'], 'UNPAIRED')
        self.assertEqual(result['comparisons'][0]['median_speed_ratio_baseline_over_candidate'], 1.25)


if __name__ == '__main__': unittest.main()
