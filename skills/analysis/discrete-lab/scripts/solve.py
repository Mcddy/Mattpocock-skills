"""Bounded exact integer resource scheduler; no external solver dependencies."""
import argparse
import json
import sys
from model import load, validate, topological


def solve(d, max_nodes=200000):
    validate(d)
    if type(max_nodes) is not int or not 1 <= max_nodes <= 2_000_000:
        raise ValueError('max_nodes must be 1..2000000')
    order, cycle = topological(d)
    base = {'schema': 'discrete-result/v1', 'model_scope': 'integer renewable-resource schedule', 'nodes': 0}
    if cycle:
        return {**base, 'status': 'INFEASIBLE', 'certificate': {'cycle': cycle}}
    excessive = [t['id'] for t in d['tasks'] if t['resource'] > d['capacity']]
    if excessive:
        return {**base, 'status': 'INFEASIBLE', 'certificate': {'resource_exceeds_capacity': excessive}}
    by = {t['id']: t for t in d['tasks']}
    paths = {}
    serial, cursor = {}, 0
    for x in order:
        t = by[x]
        paths[x] = t['duration'] + max((paths[p] for p in t['after']), default=0)
        serial[x], cursor = cursor, cursor + t['duration']
    work = sum(t['duration'] * t['resource'] for t in d['tasks'])
    lower = max(max(paths.values()), (work + d['capacity'] - 1) // d['capacity'])
    nodes = 0
    for horizon in range(lower, cursor + 1):
        used, starts = [0] * horizon, {}

        def visit(i):
            nonlocal nodes
            if i == len(order):
                return dict(starts)
            t = by[order[i]]
            earliest = max((starts[p] + by[p]['duration'] for p in t['after']), default=0)
            for s in range(earliest, horizon - t['duration'] + 1):
                if nodes >= max_nodes:
                    raise RuntimeError('search budget')
                nodes += 1
                ticks = range(s, s + t['duration'])
                if any(used[k] + t['resource'] > d['capacity'] for k in ticks):
                    continue
                starts[t['id']] = s
                for k in ticks:
                    used[k] += t['resource']
                result = visit(i + 1)
                for k in ticks:
                    used[k] -= t['resource']
                del starts[t['id']]
                if result is not None:
                    return result
            return None

        try:
            witness = visit(0)
        except RuntimeError:
            return {**base, 'status': 'UNRESOLVED', 'nodes': nodes, 'lower_bound': horizon,
                    'upper_bound': cursor, 'makespan': cursor, 'starts': serial,
                    'reason': 'assignment budget reached; serial feasible incumbent retained'}
        if witness is not None:
            return {**base, 'status': 'OPTIMAL', 'nodes': nodes, 'lower_bound': horizon,
                    'upper_bound': horizon, 'makespan': horizon, 'starts': witness,
                    'proof_scope': 'all smaller integer horizons exhausted for this supplied model'}
    raise AssertionError('serial schedule must fit')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('model')
    p.add_argument('--max-nodes', type=int, default=200000)
    a = p.parse_args()
    try:
        print(json.dumps(solve(load(a.model), a.max_nodes), indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(json.dumps({'status': 'INVALID', 'error': str(e)}))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
