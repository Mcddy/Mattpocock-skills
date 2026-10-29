"""Input validation shared by the solver and CLI, not feasibility verification."""
import json
from pathlib import Path


def pairs(items):
    d = {}
    for k, v in items:
        if k in d:
            raise ValueError('duplicate JSON key: ' + k)
        d[k] = v
    return d


def load(path):
    if Path(path).stat().st_size > 1_000_000:
        raise ValueError('input exceeds 1 MB')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite JSON')))


def validate(d):
    if not isinstance(d, dict) or type(d.get('capacity')) is not int or not 1 <= d['capacity'] <= 10000:
        raise ValueError('capacity must be a positive integer <=10000')
    ts = d.get('tasks')
    if not isinstance(ts, list) or not 1 <= len(ts) <= 12:
        raise ValueError('tasks must contain 1..12 entries')
    allowed = {'capacity', 'tasks', 'units', 'objective', 'time_semantics'}
    if set(d) - allowed:
        raise ValueError('unsupported model fields: ' + ', '.join(sorted(set(d) - allowed)))
    if 'units' in d and (not isinstance(d['units'], str) or not d['units'].strip() or len(d['units']) > 100):
        raise ValueError('units must be a nonempty string describing integer ticks')
    if d.get('objective', 'minimise makespan') != 'minimise makespan':
        raise ValueError('only minimise makespan supported')
    if d.get('time_semantics', 'half-open intervals [start,finish)') != 'half-open intervals [start,finish)':
        raise ValueError('only half-open integer intervals supported')
    seen = set()
    for t in ts:
        if not isinstance(t, dict) or set(t) != {'id', 'duration', 'resource', 'after'}:
            raise ValueError('task fields must be id,duration,resource,after')
        if not isinstance(t['id'], str) or not t['id'] or len(t['id']) > 100 or t['id'] in seen:
            raise ValueError('invalid or duplicate task ID')
        seen.add(t['id'])
        for k in ['duration', 'resource']:
            if type(t[k]) is not int or t[k] < 1:
                raise ValueError(k + ' must be a positive integer')
        if not isinstance(t['after'], list) or any(not isinstance(x, str) for x in t['after']) or len(set(t['after'])) != len(t['after']):
            raise ValueError('after must contain distinct IDs')
    if sum(t['duration'] for t in ts) > 120:
        raise ValueError('duration total exceeds 120-tick core limit')
    if any(set(t['after']) - seen for t in ts):
        raise ValueError('dependency ID absent from tasks')
    return d


def topological(d):
    by = {t['id']: t for t in d['tasks']}
    order, remaining = [], set(by)
    while remaining:
        ready = sorted(x for x in remaining if not set(by[x]['after']) & remaining)
        if not ready:
            # An explicit closed walk is retained as a checkable cycle certificate.
            current = sorted(remaining)[0]
            chain = []
            while current not in chain:
                chain.append(current)
                current = sorted(set(by[current]['after']) & remaining)[0]
            return None, chain[chain.index(current):] + [current]
        order.extend(ready)
        remaining.difference_update(ready)
    return order, None
