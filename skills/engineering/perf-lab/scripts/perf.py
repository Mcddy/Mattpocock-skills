"""Controlled stdlib benchmarks and strict supplied-record analysis."""
import argparse
from collections import defaultdict
import cProfile
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import pstats
import random
import statistics
import sys
import time
import tracemalloc


def pairs(items):
    d = {}
    for k, v in items:
        if k in d: raise ValueError('duplicate JSON key: ' + k)
        d[k] = v
    return d


def load(path):
    if Path(path).stat().st_size > 4_000_000: raise ValueError('JSON input exceeds 4 MB')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite JSON')))


def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
def digest(value): return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def percentile(values, p):
    values = sorted(values)
    if not values: return None
    position = (len(values) - 1) * p
    low = math.floor(position); high = math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def summary(values):
    return {'n': len(values), 'median_ms': statistics.median(values), 'p90_ms': percentile(values, .9),
            'min_ms': min(values), 'max_ms': max(values)} if values else {'n': 0}


def paired_summary(pairs_data, seed=23):
    usable = [(a, b) for a, b in pairs_data if a > 0 and b > 0]
    if not usable: return {'pairs': 0, 'reason': 'no positive complete paired timings'}
    ratios = [a / b for a, b in usable]
    result = {'pairs': len(usable), 'median_speed_ratio_baseline_over_candidate': statistics.median(ratios)}
    if len(usable) >= 3:
        rng = random.Random(seed)
        samples = [statistics.median(rng.choices(ratios, k=len(ratios))) for _ in range(500)]
        result['descriptive_bootstrap_95pct'] = [percentile(samples, .025), percentile(samples, .975)]
    result['scope'] = 'matched workload repeats, not production or independent-population inference'
    return result


def analyse(measurements, outputs, expected):
    if not isinstance(outputs, dict): raise ValueError('outputs must map output IDs to objects')
    if Path(measurements).stat().st_size > 4_000_000: raise ValueError('CSV exceeds 4 MB')
    required = {'run_id', 'arm', 'cache_mode', 'elapsed_ms', 'exit_code', 'output_id'}
    accepted, rejected, seen, seen_pairs = [], [], set(), set()
    with open(measurements, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not required <= set(reader.fieldnames) or set(reader.fieldnames) - required - {'pair_id'}:
            raise ValueError('CSV header must contain required fields, optional pair_id only')
        for i, r in enumerate(reader):
            if i >= 10000: raise ValueError('row count exceeds 10000')
            reasons = []
            if None in r or any(v is None for v in r.values()): raise ValueError('malformed CSV row ' + str(i + 2))
            if not all(r[k] for k in ['run_id', 'arm', 'cache_mode']): raise ValueError('empty run identity')
            if r['run_id'] in seen: raise ValueError('duplicate run ID')
            seen.add(r['run_id'])
            if r.get('pair_id'):
                pair_identity = (r['cache_mode'], r['arm'], r['pair_id'])
                if pair_identity in seen_pairs: raise ValueError('duplicate arm/stratum/pair identity')
                seen_pairs.add(pair_identity)
            try:
                elapsed = float(r['elapsed_ms'])
                if not math.isfinite(elapsed) or elapsed < 0: raise ValueError()
                exit_code = int(r['exit_code'])
                if str(exit_code) != r['exit_code'].strip(): raise ValueError()
            except ValueError: raise ValueError('invalid timing or exit code in row ' + str(i + 2))
            if exit_code != 0: reasons.append('nonzero exit code')
            if r['output_id'] not in outputs: reasons.append('output absent')
            elif canonical(outputs[r['output_id']]) != canonical(expected): reasons.append('output differs from required result')
            record = {**r, 'elapsed_ms': elapsed, 'exit_code': exit_code}
            if reasons: rejected.append({**record, 'reasons': reasons})
            else: accepted.append(record)
    groups = defaultdict(list)
    for r in accepted: groups[(r['cache_mode'], r['arm'])].append(r)
    comparisons = []
    for cache in sorted({r['cache_mode'] for r in accepted}):
        baseline = groups[(cache, 'baseline')]
        for arm in sorted({r['arm'] for r in accepted if r['cache_mode'] == cache} - {'baseline'}):
            candidate = groups[(cache, arm)]
            entry = {'cache_mode': cache, 'candidate': arm, 'baseline': summary([r['elapsed_ms'] for r in baseline]), 'candidate_summary': summary([r['elapsed_ms'] for r in candidate])}
            if not baseline:
                entry['status'] = 'NO_VALID_BASELINE'
            elif all(r.get('pair_id') for r in baseline + candidate):
                bs, cs = {}, {}
                for records, store in [(baseline, bs), (candidate, cs)]:
                    for r in records:
                        if r['pair_id'] in store: raise ValueError('duplicate arm/stratum/pair identity')
                        store[r['pair_id']] = r['elapsed_ms']
                common = sorted(set(bs) & set(cs))
                entry.update(status='PAIRED', pair_ids=common, unmatched_baseline=sorted(set(bs) - set(cs)), unmatched_candidate=sorted(set(cs) - set(bs)), paired=paired_summary([(bs[x], cs[x]) for x in common]))
            else:
                base_med, cand_med = statistics.median(r['elapsed_ms'] for r in baseline), statistics.median(r['elapsed_ms'] for r in candidate)
                entry.update(status='UNPAIRED', median_speed_ratio_baseline_over_candidate=base_med / cand_med if cand_med > 0 else None,
                             limitation='no complete pair IDs; no paired uncertainty interval')
            comparisons.append(entry)
    return {'schema': 'perf-result/v1', 'origin': 'supplied_records', 'executed_here': False, 'accepted_runs': accepted, 'rejected_runs': rejected,
            'comparisons': comparisons, 'expected_sha256': digest(expected), 'cross_cache_comparison': 'NOT PERFORMED: confounded conditions'}


def workload(n, seed=23):
    rng = random.Random(seed)
    return [{'id': i, 'group': i % 7, 'value': rng.randrange(-100, 101)} for i in range(n)]


def baseline(rows):
    return [(r['id'], sum(p['value'] for p in rows if p['group'] == r['group'])) for r in rows]


def candidate(rows):
    totals = defaultdict(int)
    for r in rows: totals[r['group']] += r['value']
    return [(r['id'], totals[r['group']]) for r in rows]


def corrupt(rows): return candidate(rows)[:-1]


def reference(rows):
    groups = {}
    for r in rows: groups.setdefault(r['group'], []).append(r['value'])
    totals = {g: sum(v) for g, v in groups.items()}
    return [(r['id'], totals[r['group']]) for r in rows]


def profile(fn, rows):
    pr = cProfile.Profile(); pr.enable(); fn(rows); pr.disable()
    stats = pstats.Stats(pr)
    functions = sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:10]
    call_summary = [{'file': Path(k[0]).name, 'line': k[1], 'function': k[2], 'primitive_calls': v[0], 'total_calls': v[1], 'self_seconds': v[2], 'cumulative_seconds': v[3]} for k, v in functions]
    tracemalloc.start()
    try:
        fn(rows); current, peak = tracemalloc.get_traced_memory()
    finally: tracemalloc.stop()
    return {'profiled_function_calls': stats.total_calls, 'top_functions': call_summary, 'traced_python_peak_bytes': peak,
            'scope': 'separate instrumented run; allocation peak is not RSS; timings excluded from clean comparison'}


def scaling(points):
    if len(points) < 3 or any(y <= 0 for _, y in points): return {'status': 'INSUFFICIENT_POSITIVE_SIZES'}
    xs, ys = [math.log(x) for x, _ in points], [math.log(y) for _, y in points]
    xm, ym = statistics.mean(xs), statistics.mean(ys)
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / sum((x - xm)**2 for x in xs)
    return {'observed_log_log_slope': slope, 'sizes': [x for x, _ in points], 'scope': 'range-specific noisy timing fit, not asymptotic proof'}


def bench(sizes, repeats=5, seconds=8.0, cache='cold'):
    if not isinstance(sizes, list) or not 1 <= len(sizes) <= 5 or any(type(x) is not int or not 2 <= x <= 2000 for x in sizes) or sizes != sorted(set(sizes)): raise ValueError('sizes must be 1..5 distinct increasing integers 2..2000')
    if type(repeats) is not int or not 3 <= repeats <= 15: raise ValueError('repeats must be 3..15')
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not .1 <= seconds <= 20: raise ValueError('seconds must be finite 0.1..20')
    if cache not in ('cold', 'warm'): raise ValueError('cache must be cold or warm')
    started = time.monotonic(); rows_out, comparisons, rejected, completed_sizes = [], [], [], []
    last_rows = None
    for n in sizes:
        rows = workload(n); expected = reference(rows); expected_hash = digest(expected)
        bad = corrupt(rows)
        rejected.append({'size': n, 'arm': 'corrupt', 'reason': 'output differs from required result', 'expected_sha256': expected_hash, 'observed_sha256': digest(bad), 'timing_in_comparison': False})
        pairs_data = []
        for repeat in range(repeats):
            if time.monotonic() - started >= seconds: break
            if cache == 'warm': baseline(rows); candidate(rows)
            arms = [('baseline', baseline), ('candidate', candidate)] if repeat % 2 == 0 else [('candidate', candidate), ('baseline', baseline)]
            timed = {}
            for arm, fn in arms:
                t = time.perf_counter_ns(); actual = fn(rows); elapsed = (time.perf_counter_ns() - t) / 1_000_000
                same = digest(actual) == expected_hash
                rows_out.append({'pair_id': str(n) + ':' + str(repeat), 'size': n, 'repeat': repeat, 'arm': arm, 'order': [a for a, _ in arms], 'cache_mode': cache, 'elapsed_ms': elapsed, 'correct': same, 'output_sha256': digest(actual)})
                if not same: raise ValueError('built-in candidate failed required output')
                timed[arm] = elapsed
            pairs_data.append((timed['baseline'], timed['candidate']))
        if pairs_data:
            comparisons.append({'size': n, 'baseline': summary([a for a, _ in pairs_data]), 'candidate': summary([b for _, b in pairs_data]), 'paired': paired_summary(pairs_data),
                                'software_inspection_counts': {'baseline': n*n, 'candidate': 2*n}, 'completed_repeats': len(pairs_data)})
            last_rows = rows
        if len(pairs_data) == repeats: completed_sizes.append(n)
        else: break
    profiles = {}
    if last_rows is not None and time.monotonic() - started < seconds:
        for arm, fn in [('baseline', baseline), ('candidate', candidate)]:
            if time.monotonic() - started >= seconds: break
            profiles[arm] = profile(fn, last_rows)
    clock = time.get_clock_info('perf_counter')
    return {'schema': 'perf-result/v1', 'origin': 'executed_builtin_workload', 'runs': rows_out, 'comparisons': comparisons,
            'rejected_variants': rejected, 'profiles': profiles, 'profile_size': len(last_rows) if last_rows else None,
            'scaling': {arm: scaling([(c['size'], c[arm]['median_ms']) for c in comparisons if c['size'] in completed_sizes]) for arm in ['baseline', 'candidate']},
            'budget_seconds': seconds, 'actual_seconds': time.monotonic() - started, 'requested_sizes': sizes,
            'completed_sizes': completed_sizes, 'budget_checks': 'between bounded calls; no pre-emption',
            'environment': {'python': platform.python_version(), 'platform_family': sys.platform, 'timer': clock.implementation, 'timer_resolution_seconds': clock.resolution},
            'scope': 'in-memory seeded aggregation; no I/O or hardware attribution; no production speedup claim'}


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest='mode', required=True)
    b = sub.add_parser('bench'); b.add_argument('--sizes', default='40,80,160'); b.add_argument('--repeats', type=int, default=5); b.add_argument('--seconds', type=float, default=8); b.add_argument('--cache', choices=['cold', 'warm'], default='cold')
    r = sub.add_parser('records'); r.add_argument('--measurements', required=True); r.add_argument('--outputs', required=True); r.add_argument('--expected', required=True)
    a = p.parse_args()
    try:
        result = bench([int(x) for x in a.sizes.split(',')], a.repeats, a.seconds, a.cache) if a.mode == 'bench' else analyse(a.measurements, load(a.outputs), load(a.expected))
        print(json.dumps(result, indent=2, allow_nan=False)); return 0
    except (ValueError, OSError, TypeError, KeyError) as e:
        print(json.dumps({'status': 'INVALID', 'error': str(e)})); return 2


if __name__ == '__main__': sys.exit(main())
