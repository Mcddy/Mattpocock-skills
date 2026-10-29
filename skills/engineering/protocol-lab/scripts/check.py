"""Bounded explicit-state BFS and deterministic trace replay, stdlib only."""
import argparse
from collections import Counter, deque
import json
from pathlib import Path
import sys


def strict_pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d: raise ValueError('duplicate JSON key: ' + k)
        d[k] = v
    return d


def load(path):
    if Path(path).stat().st_size > 2_000_000: raise ValueError('input exceeds 2 MB')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=strict_pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non-finite JSON')))


def key(state):
    return json.dumps(state, sort_keys=True, separators=(',', ':'), allow_nan=False)


class AppendModel:
    def __init__(self, spec):
        allowed = {'kind', 'strategy', 'operations', 'max_sends', 'max_events', 'max_states', 'max_messages'}
        if set(spec) - allowed: raise ValueError('unsupported append fields')
        self.strategy = spec.get('strategy')
        if self.strategy not in ('volatile', 'durable'): raise ValueError('strategy must be volatile or durable')
        self.ops = spec.get('operations', ['op1'])
        if not isinstance(self.ops, list) or not 1 <= len(self.ops) <= 3 or any(not isinstance(x, str) or not x or len(x) > 100 for x in self.ops) or len(set(self.ops)) != len(self.ops):
            raise ValueError('operations must contain 1..3 unique IDs')
        self.max_sends = integer(spec.get('max_sends', 2), 1, 3, 'max_sends')
        self.max_messages = integer(spec.get('max_messages', 3), 1, 6, 'max_messages')
        self.initial = {'up': True, 'queue': [], 'log': [], 'seen': [], 'done': [], 'sent': {x: 0 for x in self.ops}}

    def safe(self, s): return all(v <= 1 for v in Counter(s['log']).values())

    def successors(self, state):
        results = []

        def add(action, mutate):
            s = json.loads(key(state))
            mutate(s)
            results.append((action, s))

        if len(state['queue']) < self.max_messages:
            for op in self.ops:
                if op not in state['done'] and state['sent'][op] < self.max_sends:
                    def send(s, op=op):
                        s['sent'][op] += 1; s['queue'].append(['write', op])
                    add({'event': 'send', 'op': op}, send)
        for i, (kind, op) in enumerate(state['queue']):
            add({'event': 'drop', 'index': i}, lambda s, i=i: s['queue'].pop(i))
            if kind == 'write' and len(state['queue']) < self.max_messages:
                add({'event': 'duplicate', 'index': i}, lambda s, i=i: s['queue'].append(list(s['queue'][i])))
            if kind == 'ack' or state['up']:
                def deliver(s, i=i, kind=kind, op=op):
                    s['queue'].pop(i)
                    if kind == 'ack':
                        if op not in s['done']: s['done'].append(op); s['done'].sort()
                    else:
                        if op not in s['seen']:
                            # Atomic in this model: record and identity are one transition.
                            s['log'].append(op); s['seen'].append(op); s['seen'].sort()
                        if len(s['queue']) < self.max_messages: s['queue'].append(['ack', op])
                add({'event': 'deliver', 'index': i}, deliver)
        if state['up']:
            def crash(s):
                s['up'] = False
                if self.strategy == 'volatile': s['seen'] = []
            add({'event': 'crash'}, crash)
        else:
            add({'event': 'restart'}, lambda s: s.update(up=True))
        return results

    def summary(self, state):
        return {'durable_counts': dict(Counter(state['log'])), 'client_completed': state['done'],
                'unknown_outcomes': [x for x in self.ops if state['sent'][x] and x not in state['done']],
                'reconciliation': {x: ('committed' if x in state['log'] else 'absent') if state['up'] else 'unavailable' for x in self.ops}}


def integer(x, lo, hi, name):
    if type(x) is not int or not lo <= x <= hi: raise ValueError(name + ' outside bounded integer range')
    return x


class GraphModel:
    def __init__(self, spec):
        if set(spec) - {'kind', 'states', 'initial', 'transitions', 'max_events', 'max_states'}: raise ValueError('unsupported graph fields')
        self.states = spec.get('states')
        if not isinstance(self.states, dict) or not 1 <= len(self.states) <= 1000: raise ValueError('graph needs 1..1000 states')
        for name, s in self.states.items():
            if not name or not isinstance(s, dict) or type(s.get('safe')) is not bool: raise ValueError('states need nonempty IDs and boolean safe')
        self.initial = spec.get('initial')
        if not isinstance(self.initial, str) or self.initial not in self.states: raise ValueError('initial state absent')
        edges = spec.get('transitions')
        if not isinstance(edges, list) or len(edges) > 10000: raise ValueError('invalid transitions')
        self.edges = {}
        seen_edges = set()
        for e in edges:
            if not isinstance(e, dict) or set(e) != {'from', 'to', 'event'} or any(not isinstance(e[k], str) or not e[k] for k in e): raise ValueError('invalid transition')
            if e['from'] not in self.states or e['to'] not in self.states: raise ValueError('transition endpoint absent')
            identity = (e['from'], e['to'], e['event'])
            if identity in seen_edges: raise ValueError('duplicate identical graph transition')
            seen_edges.add(identity)
            self.edges.setdefault(e['from'], []).append(e)

    def safe(self, s): return self.states[s]['safe']
    def successors(self, s): return [({'event': e['event'], 'to': e['to']}, e['to']) for e in self.edges.get(s, [])]
    def summary(self, s): return {'state': s, 'terminal': not self.edges.get(s)}


def model(spec):
    if not isinstance(spec, dict): raise ValueError('spec must be an object')
    if spec.get('kind') == 'append': return AppendModel(spec)
    if spec.get('kind') == 'graph': return GraphModel(spec)
    raise ValueError('kind must be append or graph')


def explore(spec):
    m = model(spec)
    max_depth = integer(spec.get('max_events', 8), 1, 16, 'max_events')
    max_states = integer(spec.get('max_states', 10000), 1, 100000, 'max_states')
    initial = key(m.initial)
    seen = {initial: (None, None)}
    queue = deque([(m.initial, 0)])
    terminals, depth_limit, observed_depth = [], False, 0

    def trace(k):
        actions = []
        while seen[k][0] is not None:
            parent, action = seen[k]; actions.append(action); k = parent
        return list(reversed(actions))

    while queue:
        s, depth = queue.popleft(); observed_depth = max(observed_depth, depth)
        if not m.safe(s):
            actions = trace(key(s))
            return {'schema': 'protocol-result/v1', 'status': 'COUNTEREXAMPLE', 'trace': actions, 'final_state': s,
                    'summary': m.summary(s), 'visited_states': len(seen), 'depth': depth,
                    'shortest_within_model': True, 'liveness_claim': 'UNPROVEN'}
        successors = m.successors(s)
        if not successors and len(terminals) < 100: terminals.append(m.summary(s))
        if depth == max_depth:
            if successors: depth_limit = True
            continue
        for action, nxt in successors:
            nk = key(nxt)
            if nk in seen: continue
            if len(seen) >= max_states:
                return {'schema': 'protocol-result/v1', 'status': 'UNRESOLVED', 'reason': 'state budget reached',
                        'visited_states': len(seen), 'depth': observed_depth, 'max_events': max_depth, 'max_states': max_states,
                        'frontier_states': len(queue) + 1, 'liveness_claim': 'UNPROVEN'}
            seen[nk] = (key(s), action); queue.append((nxt, depth + 1))
    return {'schema': 'protocol-result/v1', 'status': 'BOUNDED_NO_COUNTEREXAMPLE' if depth_limit else 'EXHAUSTED_FINITE_MODEL',
            'visited_states': len(seen), 'depth': observed_depth, 'max_events': max_depth, 'max_states': max_states,
            'depth_frontier': depth_limit, 'terminal_examples': terminals, 'liveness_claim': 'UNPROVEN',
            'scope': 'safety only in this finite supplied model, including its send and queue bounds'}


def replay(spec, actions):
    m = model(spec)
    if isinstance(actions, dict): actions = actions.get('trace')
    if not isinstance(actions, list) or len(actions) > 100: raise ValueError('trace must contain <=100 action objects')
    s = m.initial; states = [s]
    first_violation = None if m.safe(s) else 0
    for i, action in enumerate(actions):
        enabled = [(a, nxt) for a, nxt in m.successors(s) if a == action]
        if len(enabled) != 1:
            return {'valid_trace': False, 'index': i, 'error': 'action not uniquely enabled', 'state': s}
        s = enabled[0][1]; states.append(s)
        if first_violation is None and not m.safe(s): first_violation = i + 1
    return {'valid_trace': True, 'safe': m.safe(s), 'trace_safe': first_violation is None, 'first_violation_state_index': first_violation,
            'states': states, 'summary': m.summary(s), 'scope': 'model replay, not external implementation'}


def main():
    p = argparse.ArgumentParser(); p.add_argument('spec'); p.add_argument('--replay')
    a = p.parse_args()
    try:
        s = load(a.spec)
        result = replay(s, load(a.replay)) if a.replay else explore(s)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as e:
        print(json.dumps({'status': 'INVALID', 'error': str(e)})); return 2


if __name__ == '__main__': sys.exit(main())
