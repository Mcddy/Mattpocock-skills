"""Seeded contract generation, differential/metamorphic checks and greedy shrinking."""
import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import random
import sys
import unicodedata


def pairs(items):
    d = {}
    for k, v in items:
        if k in d: raise ValueError('duplicate JSON key: ' + k)
        d[k] = v
    return d


def load(path):
    if Path(path).stat().st_size > 2_000_000: raise ValueError('input exceeds 2 MB')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite JSON')))


def validate(spec):
    if not isinstance(spec, dict): raise ValueError('spec must be an object')
    if set(spec) - {'contract', 'seed', 'cases', 'lower', 'upper', 'observations'}: raise ValueError('unsupported spec fields')
    c = spec.get('contract')
    if c not in ('ascii-spaces', 'integer-range', 'sort-integers'): raise ValueError('unsupported contract')
    lo, hi = spec.get('lower', 0), spec.get('upper', 3)
    if type(lo) is not int or type(hi) is not int or not -100000 <= lo <= hi <= 100000: raise ValueError('invalid integer boundaries')
    if c != 'integer-range' and ('lower' in spec or 'upper' in spec): raise ValueError('boundaries only apply to integer-range')
    if type(spec.get('seed', 17)) is not int or not 0 <= spec.get('seed', 17) <= 2**32 - 1: raise ValueError('seed outside uint32')
    if type(spec.get('cases', 200)) is not int or not 1 <= spec.get('cases', 200) <= 5000: raise ValueError('cases must be 1..5000')
    return c, lo, hi


def normalise_oracle(s):
    if not isinstance(s, str) or len(s) > 96: raise ValueError('string required, <=96 characters')
    # Split only the literal ASCII space; keep all other code points verbatim.
    return ' '.join(part for part in s.split(' ') if part)


def oracle(spec, x):
    c, lo, hi = validate(spec)
    if c == 'ascii-spaces': return normalise_oracle(x)
    if c == 'integer-range': return type(x) is int and lo <= x <= hi
    if not isinstance(x, list) or len(x) > 32 or any(type(v) is not int for v in x): raise ValueError('integer list required, <=32 values')
    # A separate insertion algorithm avoids copying the target sorted() call.
    result = []
    for value in x:
        i = 0
        while i < len(result) and result[i] <= value: i += 1
        result.insert(i, value)
    return result


def target_function(spec, name):
    c, lo, hi = validate(spec)
    compatible = {'ascii-spaces': {'correct', 'whitespace', 'ascii-loss', 'coerce'},
                  'integer-range': {'correct', 'bool-int', 'exclusive-upper'},
                  'sort-integers': {'correct', 'unique-sort'}}
    if name not in compatible[c]: raise ValueError('target incompatible with contract')

    def target(x):
        if c == 'integer-range':
            if name == 'bool-int': return isinstance(x, int) and lo <= x <= hi
            if name == 'exclusive-upper': return type(x) is int and lo <= x < hi
            return type(x) is int and lo <= x <= hi
        if c == 'sort-integers':
            if not isinstance(x, list) or len(x) > 32 or any(type(v) is not int for v in x): raise ValueError('invalid list')
            return sorted(set(x)) if name == 'unique-sort' else sorted(x)
        if name == 'coerce': x = str(x)
        if not isinstance(x, str) or len(x) > 96: raise ValueError('invalid string')
        if name == 'whitespace': return ' '.join(x.split())
        if name == 'ascii-loss': x = unicodedata.normalize('NFKD', x).encode('ascii', errors='ignore').decode('ascii')
        # A state machine independent of split-based oracle.
        out, pending = [], False
        for ch in x:
            if ch == ' ':
                if out: pending = True
            else:
                if pending: out.append(' ')
                out.append(ch); pending = False
        return ''.join(out)
    return target


def outcome(fn, x):
    try: return {'accepted': True, 'value': fn(x)}
    except (ValueError, TypeError, OverflowError) as e: return {'accepted': False, 'error_type': type(e).__name__}


def difference(expected, observed):
    if expected['accepted'] != observed['accepted']: return 'false_reject' if expected['accepted'] else 'false_accept'
    if not expected['accepted']: return None
    if type(expected['value']) is bool and type(observed['value']) is bool and expected['value'] != observed['value']:
        return 'false_reject' if expected['value'] else 'false_accept'
    if type(expected['value']) is not type(observed['value']) or expected['value'] != observed['value']: return 'wrong_value'
    return None


def generate(spec):
    c, lo, hi = validate(spec); rng = random.Random(spec.get('seed', 17))
    if c == 'ascii-spaces':
        edges = ['', ' ', '  A  B  ', 'A\tB', 'café', 'e\u0301', '\u00a0A\u00a0', '\n A \n', '\U0001f642', True, None, 0]
        yield from edges
        for n in range(1, 4):
            for chars in itertools.product(' A\té', repeat=n): yield ''.join(chars)
        while True: yield ''.join(rng.choice(' AB\t\né\u00a0\u0301') for _ in range(rng.randrange(0, 33)))
    elif c == 'integer-range':
        yield from [lo, hi, lo - 1, hi + 1, 0, True, False, float(lo), str(lo), None, [], {}, 2**100]
        while True: yield rng.randint(lo - 10, hi + 10)
    else:
        yield from [[], [0], [1, 1], [2, -1, 2], [True], '1', None, [2**100, -2**100]]
        while True: yield [rng.randint(-10, 10) for _ in range(rng.randrange(0, 17))]


def reductions(x):
    if isinstance(x, (str, list)):
        size = len(x)
        for width in dict.fromkeys([size, max(1, size // 2), 1]):
            for i in range(size - width + 1): yield x[:i] + x[i + width:]
        if isinstance(x, str):
            for i, ch in enumerate(x):
                for replacement in [' ', 'A', '\t']:
                    if ord(replacement) < ord(ch): yield x[:i] + replacement + x[i + 1:]
        else:
            for i, value in enumerate(x):
                if type(value) is int:
                    for replacement in dict.fromkeys([0, int(value / 2) if abs(value) < 2**53 else value // 2]):
                        if abs(replacement) < abs(value): yield x[:i] + [replacement] + x[i + 1:]
    elif type(x) is int:
        for y in dict.fromkeys([0, x // 2, -1, 1]):
            if abs(y) < abs(x): yield y


def shrink(spec, fn, original, category, budget=300):
    current, attempts, exhausted = original, 0, False
    seen = {json.dumps(current, sort_keys=True, ensure_ascii=False)}
    while True:
        improved = False
        for candidate in reductions(current):
            signature = json.dumps(candidate, sort_keys=True, ensure_ascii=False)
            if signature in seen: continue
            seen.add(signature)
            if attempts >= budget: exhausted = True; break
            attempts += 1
            if difference(outcome(lambda x: oracle(spec, x), candidate), outcome(fn, candidate)) == category:
                current = candidate; improved = True; break
        if exhausted or not improved: break
    return {'input': current, 'expected': outcome(lambda x: oracle(spec, x), current), 'observed': outcome(fn, current),
            'attempts': attempts, 'budget_exhausted': exhausted, 'minimality': 'greedy reduction fixed point' if not exhausted else 'partial reduction'}


def metamorphic(spec, fn, x):
    c = spec['contract']; checks = []
    first = outcome(fn, x)
    if not first['accepted']: return checks
    value = first['value']
    if c == 'ascii-spaces' and isinstance(x, str) and isinstance(value, str):
        second = outcome(fn, value)
        checks.append(('idempotence', second == first))
        checks.append(('nonspace_preservation', x.replace(' ', '') == value.replace(' ', '')))
    if c == 'sort-integers' and isinstance(x, list) and all(type(v) is int for v in x) and isinstance(value, list):
        checks.append(('multiset_preservation', Counter(x) == Counter(value)))
        checks.append(('idempotence', outcome(fn, value) == first))
        checks.append(('reversal_invariance', outcome(fn, list(reversed(x))) == first))
    return checks


def run(spec, name='correct'):
    validate(spec); fn = target_function(spec, name)
    failures, failure_count, meta_counts, meta_failures = [], 0, Counter(), []
    failure_inputs = set()
    n = spec.get('cases', 200)
    for index, x in enumerate(itertools.islice(generate(spec), n)):
        expected, actual = outcome(lambda x: oracle(spec, x), x), outcome(fn, x)
        category = difference(expected, actual)
        if category:
            failure_count += 1
            if len(failures) < 12:
                reduced = shrink(spec, fn, x, category)
                signature = json.dumps(reduced['input'], sort_keys=True, ensure_ascii=False)
                if signature not in failure_inputs:
                    failure_inputs.add(signature)
                    failures.append({'case': index, 'category': category, 'original_input': x, 'expected': expected,
                                     'observed': actual, 'shrunk': reduced})
        if index < 200:
            for prop, passed in metamorphic(spec, fn, x):
                meta_counts[prop] += 1
                if not passed and len(meta_failures) < 12: meta_failures.append({'case': index, 'property': prop, 'input': x})
    return {'schema': 'verification-result/v1', 'status': 'FAILURES_FOUND' if failure_count or meta_failures else 'FINITE_CHECKS_PASS',
            'contract': spec['contract'], 'target': name, 'seed': spec.get('seed', 17), 'cases_run': n,
            'differential_failures': failure_count, 'retained_failures': failures,
            'metamorphic_checks': dict(meta_counts), 'metamorphic_failures': meta_failures,
            'scope': 'finite generated domain and registered implementation; not arbitrary-program certification'}


def observations(spec):
    c, _, _ = validate(spec); obs = spec.get('observations')
    if not isinstance(obs, list) or len(obs) > 5000: raise ValueError('observations must be a list <=5000')
    rows = []
    for i, record in enumerate(obs):
        if not isinstance(record, dict): raise ValueError('observation ' + str(i) + ' must be object')
        if c == 'integer-range':
            if set(record) != {'value', 'accepted'} or type(record['accepted']) is not bool: raise ValueError('invalid integer observation ' + str(i))
            x, actual = record['value'], {'accepted': True, 'value': record['accepted']}
        else:
            if set(record) == {'input', 'output'}: actual = {'accepted': True, 'value': record['output']}
            elif set(record) == {'input', 'rejected'} and record['rejected'] is True: actual = {'accepted': False, 'error_type': 'supplied rejection'}
            else: raise ValueError('invalid observation ' + str(i))
            x = record['input']
        expected = outcome(lambda x: oracle(spec, x), x)
        rows.append({'index': i, 'input': x, 'expected': expected, 'observed': actual,
                     'category': difference(expected, actual), 'shrinking': 'NOT RUN: no callable target supplied'})
    return {'schema': 'verification-result/v1', 'status': 'OBSERVATIONS_REVIEWED', 'rows': rows,
            'failure_count': sum(r['category'] is not None for r in rows), 'scope': 'supplied observations only; no imported code executed'}


def main():
    p = argparse.ArgumentParser(); p.add_argument('spec'); p.add_argument('--target', default='correct'); p.add_argument('--observations', action='store_true')
    a = p.parse_args()
    try:
        result = observations(load(a.spec)) if a.observations else run(load(a.spec), a.target)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)); return 0
    except (ValueError, OSError, TypeError, KeyError) as e:
        print(json.dumps({'status': 'INVALID', 'error': str(e)})); return 2


if __name__ == '__main__': sys.exit(main())
