"""Independent endpoint feasibility verifier. Does not import search code."""
import argparse
import json
import sys
from model import load, validate


def verify(d, result):
    validate(d)
    if not isinstance(result, dict):
        raise ValueError('result must be an object')
    if result.get('status') == 'INFEASIBLE':
        c = result.get('certificate', {})
        if not isinstance(c, dict):
            return {'valid': False, 'errors': ['certificate must be an object'], 'optimality_verified': False}
        by = {t['id']: t for t in d['tasks']}
        cycle = c.get('cycle')
        resource = c.get('resource_exceeds_capacity')
        if isinstance(cycle, list) and len(cycle) > 1 and cycle[0] == cycle[-1] and all(isinstance(x, str) and x in by for x in cycle):
            valid = all(b in by[a]['after'] for a, b in zip(cycle, cycle[1:]))
            return {'valid': valid, 'kind': 'cycle certificate', 'optimality_verified': False}
        valid = isinstance(resource, list) and bool(resource) and all(isinstance(x, str) and x in by and by[x]['resource'] > d['capacity'] for x in resource)
        return {'valid': valid, 'kind': 'resource certificate', 'optimality_verified': False}
    starts = result.get('starts')
    ids = {t['id'] for t in d['tasks']}
    if not isinstance(starts, dict) or set(starts) != ids or any(type(s) is not int or s < 0 for s in starts.values()):
        return {'valid': False, 'errors': ['starts must contain exactly all IDs with nonnegative integer values'], 'optimality_verified': False}
    by = {t['id']: t for t in d['tasks']}
    errors, events = [], []
    for t in d['tasks']:
        s, finish = starts[t['id']], starts[t['id']] + t['duration']
        events.extend([(s, t['resource']), (finish, -t['resource'])])
        for predecessor in t['after']:
            if starts[predecessor] + by[predecessor]['duration'] > s:
                errors.append('dependency violated: ' + predecessor + ' -> ' + t['id'])
    demand = 0
    # Aggregate same-tick finishes and starts; half-open boundaries do not overlap.
    for tick in sorted(set(t for t, _ in events)):
        demand += sum(delta for t, delta in events if t == tick)
        if demand > d['capacity']:
            errors.append('capacity exceeded at tick ' + str(tick))
    actual = max(starts[t['id']] + t['duration'] for t in d['tasks'])
    if type(result.get('makespan')) is not int or result['makespan'] != actual:
        errors.append('makespan does not equal actual latest finish')
    return {'valid': not errors, 'errors': errors, 'makespan': actual, 'optimality_verified': False,
            'scope': 'feasibility only; optimality requires completed search or separate lower-bound proof'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('model'); p.add_argument('result')
    a = p.parse_args()
    try:
        outcome = verify(load(a.model), load(a.result))
        print(json.dumps(outcome, indent=2))
        return 0 if outcome['valid'] else 1
    except (ValueError, OSError, TypeError, KeyError) as e:
        print(json.dumps({'valid': False, 'error': str(e)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
