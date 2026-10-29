"""Small independent Cartesian oracle; not the production search algorithm."""
import argparse
import itertools
import json
import sys
from model import load, validate


def oracle(d, max_combinations=500000):
    validate(d)
    if type(max_combinations) is not int or not 1 <= max_combinations <= 2_000_000:
        raise ValueError('combination budget must be 1..2000000')
    ts = d['tasks']
    count = 0
    for h in range(max(t['duration'] for t in ts), sum(t['duration'] for t in ts) + 1):
        domains = [range(h - t['duration'] + 1) for t in ts]
        for positions in itertools.product(*domains):
            if count >= max_combinations:
                return {'status': 'UNRESOLVED', 'combinations': count, 'reason': 'oracle budget reached'}
            count += 1
            starts = dict(zip((t['id'] for t in ts), positions))
            finishes = {t['id']: starts[t['id']] + t['duration'] for t in ts}
            if any(finishes[p] > starts[t['id']] for t in ts for p in t['after']):
                continue
            boundaries = sorted(set(positions) | set(finishes.values()))
            if any(sum(t['resource'] for t in ts if starts[t['id']] <= tick < finishes[t['id']]) > d['capacity'] for tick in boundaries):
                continue
            return {'status': 'OPTIMAL', 'makespan': h, 'starts': starts, 'combinations': count}
    return {'status': 'INFEASIBLE', 'combinations': count, 'scope': 'all integer starts within serial horizon enumerated'}


def main():
    p = argparse.ArgumentParser(); p.add_argument('model'); p.add_argument('--max-combinations', type=int, default=500000)
    a = p.parse_args()
    try:
        print(json.dumps(oracle(load(a.model), a.max_combinations), indent=2))
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(json.dumps({'status': 'INVALID', 'error': str(e)})); return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
