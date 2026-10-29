#!/usr/bin/env python3
"""Check a tabletop scenario file before anyone plays it. Standard library only.

Usage:
  python scenario_check.py SCENARIO.json [--json]

SCENARIO.json (one object; assets/scenario-template.json is a filled-in sample):
  {"schema": 1, "id": "outage-small-saas", "version": "1.0", "title": "...",
   "type": "incident_response|decision|study_drill",
   "subject": "own_system|own_plan|fictional",      whose system this is; never a real third party
   "system_under_test": "the plan or system the exercise tests",
   "setting": "what the player is told at the start", "player_role": "who the player is",
   "duration": {"turns": 10, "minutes_per_turn": 15, "start_clock": "21:40"},
   "objectives": [{"id": "O1", "text": "what the exercise should reveal"}],        two to four
   "roles": [{"id": "R1", "name": "support lead", "can": "...", "available_from_turn": 1}],
   "resources": [{"id": "RES1", "name": "...", "amount": 1, "unit": "..."}],
   "constraints": ["..."],
   "known_facts": [{"id": "K1", "text": "..."}],
   "hidden_facts": [{"id": "H1", "text": "..."}],
   "state": {"service": "degraded"},                 named values the rules may change
   "actions": [{"id": "A1", "label": "...", "class": "investigate|act|decide|communicate",
                "costs_turn": true, "reveals": ["H1"], "needs_fact": ["H2"], "cost": {"RES1": 1},
                "delegable_to": ["R1"]}],
                needs_fact: the action exists for the player only once those hidden facts are revealed
   "injects": [{"id": "I1", "turn": 1, "told": "what the player is told", "truth": "what is really true",
                "misleading": false, "tone": "bad|neutral|good", "probes": ["O1"],
                "task": "optional line for the task list", "expects": ["A2"], "within": 2, "bait": ["A9"],
                "reveals": [], "set": {}}],
                turn is a whole number, or null for an inject that only a rule can fire
   "rules": [{"id": "RU1", "when": {"action": "A4", "requires": ["A2"], "state": {"db": "up"}, "by_turn": 5},
              "then": {"text": "...", "reveals": [], "fires": [], "set": {}},
              "late": {...}, "unmet": {...}},
             {"id": "RU2", "when": {"at_turn": 6, "state": {"disk": "filling"}}, "then": {...}}],
   "unknowable": ["what no action in this exercise can establish"],
   "key_actions": [{"id": "KA1", "label": "containment", "action": "A4", "from_inject": "I1"}],
   "plan": [{"id": "P1", "text": "a step of the player's own runbook"}]}
"state" holds only things the player can see; it is printed every turn. Anything the player cannot
see is a hidden fact.

How rules are read, by the facilitator and by session_log.py.
  An action rule ("when" names an action): when the player takes that action, find the rule for it
  whose "requires" actions have all been done and whose "state" values all hold. Its outcome is
  "late" if the turn is after "by_turn", else "then". If no rule for the action matches, the outcome
  is the "unmet" of the one rule for that action that has one. An action may have several rules
  only if their state conditions cannot hold together.
  A clock rule ("when" has at_turn): at the start of that turn, if its "state" values all hold, its
  "then" applies, before the player acts.
  Where the outcome that applies is not written, the rules are silent, and the facilitator must
  make a judgement call and label it.
  An outcome may carry "done": false, meaning the attempt did not take effect ("the database is not
  running, so the slot cannot be dropped"). The action then does not count as done: it can be tried
  again, and it does not answer an inject or a key action.

What it enforces (ERROR, exit 1). The word in brackets is the rule's code, also given by --json:
  [shape]          a missing or wrongly typed field, a value outside its list. true is not 1.
  [duplicate_id]   an id used twice anywhere in the file.
  [reference]      an id that points at nothing; an adjudication rule naming an unknown action or
                   inject; a rule that sets a state key the file does not declare.
  [objective_unprobed]   an objective that no inject probes.
  [inject_no_objective]  an inject that probes no objective.
  [inject_no_truth]      an inject with no "really true" entry; or one marked misleading whose
                         truth only repeats what the player is told.
  [hidden_undiscoverable] a hidden fact that no listed action, and no rule outcome an action can
                         cause, ever reveals. Something that cannot be found belongs in unknowable.
  [turn_order]     injects with fixed turns listed out of order, or a turn below 1.
  [duration]       an inject, a rule deadline or a clock rule after the last turn; a role that
                   arrives after it.
  [inject_unreachable]   an inject with no turn that no rule fires.
  [rule_clash]     two rules for the same action whose conditions can hold together, or two that
                   both carry "unmet": the facilitator could not tell which applies.
What it reports for a person to decide (ADVISORY, never changes the exit code):
  every inject is bad news (no decision can go well); no inject carries misleading information
  (too easy); more than 12 turns (long for a first run); fewer than two or more than four
  objectives; a deadline rule that says nothing about acting late; an outcome marked done: false
  on an action that has a cost (the cost is still spent); no plan steps (decisions cannot
  be logged against a plan); no key actions; an expected action that needs more turns than remain.

What it cannot tell: whether the scenario is realistic, whether the rules are fair, or whether the
exercise will teach anything. It reads the file. A pass means the file can be played by the rules
as written.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import json
import re
import sys
from pathlib import Path

TYPES = ("incident_response", "decision", "study_drill")
SUBJECTS = ("own_system", "own_plan", "fictional")
ACTION_CLASSES = ("investigate", "act", "decide", "communicate")
TONES = ("bad", "neutral", "good")
OUTCOMES = ("then", "late", "unmet")
CLOCK = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,23}")
TOP_KEYS = {"schema", "id", "version", "title", "type", "subject", "system_under_test", "setting", "player_role", "duration", "objectives",
            "roles", "resources", "constraints", "known_facts", "hidden_facts", "state", "actions", "injects", "rules", "unknowable",
            "key_actions", "plan", "addressing", "notes"}
FLAGS = {"--json"}


class Unreadable(Exception):
    """The input could not be read as one strict JSON document."""


def text_ok(v, min_len=1):
    return isinstance(v, str) and len(v.strip()) >= min_len


def whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def scalar(v):
    return isinstance(v, (str, bool)) or (isinstance(v, (int, float)) and v == v and abs(v) != float("inf"))


def _no_constants(name):
    raise ValueError("%s is not a JSON number" % name)


def _no_duplicates(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError("the key %r appears twice in one object" % k)
        seen[k] = v
    return seen


def decode(raw, name):
    if b"\x00" in raw:
        raise Unreadable("%s contains a NUL byte; it is not a text file" % name)
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Unreadable("%s is not valid UTF-8" % name)


def parse(text, name):
    try:
        return json.loads(text, parse_constant=_no_constants, object_pairs_hook=_no_duplicates)
    except ValueError as e:
        raise Unreadable("%s is not valid JSON (%s)" % (name, str(e)[:90]))


def load(path):
    """Read one strict JSON document. Raises Unreadable with a one-line reason."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise Unreadable("cannot read %s: %s" % (path, e.strerror or e))
    return parse(decode(raw, str(path)), str(path))


class Report:
    def __init__(self):
        self.errors, self.advisories = [], []

    def error(self, code, message):
        self.errors.append({"code": code, "message": message})

    def advise(self, code, message):
        self.advisories.append({"code": code, "message": message})

    def has(self, *codes):
        return any(e["code"] in codes for e in self.errors)


def _objects(d, key, rep, need_one=False):
    v = d.get(key)
    if v is None and not need_one:
        return []
    if not isinstance(v, list):
        rep.error("shape", "%s must be a list" % key)
        return []
    if need_one and not v:
        rep.error("shape", "%s is empty; the exercise needs at least one" % key)
    out = []
    for i, item in enumerate(v):
        if isinstance(item, dict):
            out.append(item)
        else:
            rep.error("shape", "%s entry %d is not an object" % (key, i + 1))
    return out


def _ids(v):
    return isinstance(v, list) and all(isinstance(x, str) and x for x in v)


def check(d):
    """Return (errors, advisories, summary). errors and advisories are lists of {"code", "message"}."""
    rep = Report()
    if not isinstance(d, dict):
        rep.error("shape", "the file must hold one JSON object")
        return rep.errors, rep.advisories, {}
    for k in sorted(set(d) - TOP_KEYS):
        rep.advise("unknown_key", "top-level key %r is not one this checker knows. Check the spelling; it was ignored" % k)
    if not whole(d.get("schema")) or d.get("schema") != 1:
        rep.error("shape", "schema must be the whole number 1 (true and \"1\" are not 1)")
    for key, hint, n in (("id", "a short name for the scenario", 2), ("version", "a version, for example \"1.0\"", 1), ("title", "a title", 4),
                         ("system_under_test", "the plan or system the exercise tests", 8), ("setting", "what the player is told at the start", 20),
                         ("player_role", "who the player is in the scenario", 3)):
        if not text_ok(d.get(key), n):
            rep.error("shape", "%s is missing: give %s" % (key, hint))
    if d.get("type") not in TYPES or not isinstance(d.get("type"), str):
        rep.error("shape", "type must be one of %s" % ", ".join(TYPES))
    if d.get("subject") not in SUBJECTS or not isinstance(d.get("subject"), str):
        rep.error("shape", "subject must be one of %s: the player's own system or plan, or a fictional organisation. "
                  "A scenario is never about a real third party" % ", ".join(SUBJECTS))
    dur = d.get("duration")
    turns = None
    if not isinstance(dur, dict):
        rep.error("shape", "duration must be an object with turns, minutes_per_turn and start_clock")
    else:
        if not whole(dur.get("turns")) or not 1 <= dur["turns"] <= 60:
            rep.error("shape", "duration.turns must be a whole number from 1 to 60")
        else:
            turns = dur["turns"]
        if not whole(dur.get("minutes_per_turn")) or not 1 <= dur["minutes_per_turn"] <= 1440:
            rep.error("shape", "duration.minutes_per_turn must be a whole number of scenario minutes, 1 to 1440")
        if not isinstance(dur.get("start_clock"), str) or not CLOCK.fullmatch(dur["start_clock"]):
            rep.error("shape", "duration.start_clock must be a 24 hour time written HH:MM, for example 09:05")
    for key in ("constraints", "unknowable"):
        v = d.get(key, [])
        if not isinstance(v, list) or not all(text_ok(x) for x in v):
            rep.error("shape", "%s must be a list of sentences" % key)
    state = d.get("state", {})
    if not isinstance(state, dict) or not all(scalar(v) for v in state.values()):
        rep.error("shape", "state must be an object of named text, number or true/false values")
        state = {}

    objectives = _objects(d, "objectives", rep, need_one=True)
    roles = _objects(d, "roles", rep)
    resources = _objects(d, "resources", rep)
    known = _objects(d, "known_facts", rep, need_one=True)
    hidden = _objects(d, "hidden_facts", rep)
    actions = _objects(d, "actions", rep, need_one=True)
    injects = _objects(d, "injects", rep, need_one=True)
    rules = _objects(d, "rules", rep)
    key_actions = _objects(d, "key_actions", rep)
    plan = _objects(d, "plan", rep)

    seen, index = {}, {}
    for kind, group in (("objective", objectives), ("role", roles), ("resource", resources), ("known fact", known), ("hidden fact", hidden),
                        ("action", actions), ("inject", injects), ("rule", rules), ("key action", key_actions), ("plan step", plan)):
        index[kind] = {}
        for item in group:
            i = item.get("id")
            if not isinstance(i, str) or not ID.fullmatch(i):
                rep.error("shape", "a %s has no usable id (a letter, then up to 23 letters, digits, hyphens or underscores)" % kind)
                continue
            if i in seen:
                rep.error("duplicate_id", "id %s is used twice (a %s and a %s). Ids are unique across the whole file" % (i, seen[i], kind))
                continue
            seen[i] = kind
            index[kind][i] = item

    def refs(owner, field, values, kind, code="reference"):
        if values is None:
            return []
        if not _ids(values):
            rep.error("shape", "%s: %s must be a list of ids" % (owner, field))
            return []
        for v in values:
            if v not in index[kind]:
                rep.error(code, "%s: %s names %r, which is not a %s in this file" % (owner, field, v, kind))
        return [v for v in values if v in index[kind]]

    for kind, group, field, n in (("objective", objectives, "text", 12), ("known fact", known, "text", 8), ("hidden fact", hidden, "text", 8),
                                  ("plan step", plan, "text", 8), ("role", roles, "name", 2), ("resource", resources, "name", 2)):
        for item in group:
            if not text_ok(item.get(field), n):
                rep.error("shape", "%s %s: %s is missing or too short" % (kind, item.get("id", "?"), field))
    for r in roles:
        if not text_ok(r.get("can"), 6):
            rep.error("shape", "role %s: say what they can be asked to do (can)" % r.get("id", "?"))
        af = r.get("available_from_turn", 1)
        if not whole(af) or af < 1:
            rep.error("shape", "role %s: available_from_turn must be a whole number, 1 or more" % r.get("id", "?"))
        elif turns and af > turns:
            rep.error("duration", "role %s arrives on turn %d, after the last turn (%d)" % (r.get("id", "?"), af, turns))
    for r in resources:
        if not isinstance(r.get("amount"), (int, float)) or isinstance(r.get("amount"), bool) or r["amount"] < 0:
            rep.error("shape", "resource %s: amount must be a number, 0 or more" % r.get("id", "?"))

    revealed_by_action = set()
    for a in actions:
        aid = a.get("id", "?")
        if not text_ok(a.get("label"), 6):
            rep.error("shape", "action %s: label is missing: say what the player does" % aid)
        if a.get("class") not in ACTION_CLASSES or not isinstance(a.get("class"), str):
            rep.error("shape", "action %s: class must be one of %s" % (aid, ", ".join(ACTION_CLASSES)))
        if not isinstance(a.get("costs_turn"), bool):
            rep.error("shape", "action %s: costs_turn must be true or false" % aid)
        revealed_by_action.update(refs("action " + aid, "reveals", a.get("reveals", []), "hidden fact"))
        refs("action " + aid, "needs_fact", a.get("needs_fact", []), "hidden fact")
        refs("action " + aid, "delegable_to", a.get("delegable_to", []), "role")
        cost = a.get("cost", {})
        if not isinstance(cost, dict) or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in cost.values()):
            rep.error("shape", "action %s: cost must map resource ids to positive numbers" % aid)
        else:
            for res in cost:
                if res not in index["resource"]:
                    rep.error("reference", "action %s: cost names %r, which is not a resource in this file" % (aid, res))

    probed, last_turn = set(), 0
    for inj in injects:
        iid = inj.get("id", "?")
        t = inj.get("turn")
        if t is not None:
            if not whole(t) or t < 1:
                rep.error("turn_order", "inject %s: turn must be a whole number, 1 or more, or null for an inject a rule fires" % iid)
            else:
                if t < last_turn:
                    rep.error("turn_order", "inject %s is on turn %d but is listed after an inject on turn %d. List injects in the order they happen" % (iid, t, last_turn))
                last_turn = max(last_turn, t)
                if turns and t > turns:
                    rep.error("duration", "inject %s is on turn %d, after the last turn (%d). The duration cannot fit the injects" % (iid, t, turns))
        if not text_ok(inj.get("told"), 8):
            rep.error("shape", "inject %s: told is missing: write what the player is told" % iid)
        if not text_ok(inj.get("truth"), 8):
            rep.error("inject_no_truth", "inject %s has no truth entry. Write what is really true, even when it matches what the player is told" % iid)
        if not isinstance(inj.get("misleading"), bool):
            rep.error("shape", "inject %s: misleading must be true or false" % iid)
        elif inj["misleading"] and text_ok(inj.get("truth"), 8) and text_ok(inj.get("told")) and \
                " ".join(inj["truth"].lower().split()) == " ".join(inj["told"].lower().split()):
            rep.error("inject_no_truth", "inject %s is marked misleading, but its truth only repeats what the player is told" % iid)
        if inj.get("tone") not in TONES or not isinstance(inj.get("tone"), str):
            rep.error("shape", "inject %s: tone must be one of %s" % (iid, ", ".join(TONES)))
        ok = refs("inject " + iid, "probes", inj.get("probes", []), "objective")
        if not ok and _ids(inj.get("probes", [])) and not inj.get("probes"):
            rep.error("inject_no_objective", "inject %s probes no objective. Tie it to one, or cut it" % iid)
        probed.update(ok)
        expects = refs("inject " + iid, "expects", inj.get("expects", []), "action")
        refs("inject " + iid, "bait", inj.get("bait", []), "action")
        refs("inject " + iid, "reveals", inj.get("reveals", []), "hidden fact")
        w = inj.get("within")
        if expects and (not whole(w) or w < 0):
            rep.error("shape", "inject %s: within must be a whole number of turns (0 means the same turn) when expects is given" % iid)
        if "task" in inj and not text_ok(inj["task"], 4):
            rep.error("shape", "inject %s: task must be a short line of text when given" % iid)
        st = inj.get("set", {})
        if not isinstance(st, dict) or not all(scalar(v) for v in st.values()):
            rep.error("shape", "inject %s: set must be an object of state values" % iid)
        else:
            for k in st:
                if k not in state:
                    rep.error("reference", "inject %s: sets %r, which is not a key in state" % (iid, k))
    for o in objectives:
        if o.get("id") in index["objective"] and o["id"] not in probed:
            rep.error("objective_unprobed", "objective %s is probed by no inject, so the exercise cannot reveal anything about it" % o["id"])

    fired, by_action, revealed_by_rule = set(), {}, set()

    def state_condition(where, cond):
        if cond is None:
            return {}
        if not isinstance(cond, dict) or not all(scalar(v) for v in cond.values()):
            rep.error("shape", "%s: when.state must be an object of state values" % where)
            return {}
        for k in cond:
            if k not in state:
                rep.error("reference", "%s: when.state names %r, which is not a key in state" % (where, k))
        return cond

    for r in rules:
        rid = r.get("id", "?")
        when = r.get("when")
        if not isinstance(when, dict):
            rep.error("shape", "rule %s: when must be an object naming an action, or giving at_turn" % rid)
            when = {}
        cond = state_condition("rule " + rid, when.get("state"))
        clock_rule = "at_turn" in when
        if clock_rule:
            at = when.get("at_turn")
            if not whole(at) or at < 1:
                rep.error("shape", "rule %s: when.at_turn must be a whole number, 1 or more" % rid)
            elif turns and at > turns:
                rep.error("duration", "rule %s applies at turn %d, after the last turn (%d)" % (rid, at, turns))
            if any(k in when for k in ("action", "requires", "by_turn")):
                rep.error("shape", "rule %s: a clock rule (at_turn) cannot also name an action, requires or by_turn" % rid)
            if "late" in r or "unmet" in r:
                rep.error("shape", "rule %s: a clock rule has only a then outcome" % rid)
        else:
            act = when.get("action")
            if act not in index["action"]:
                rep.error("reference", "rule %s: when.action %r is not an action in this file" % (rid, act))
            else:
                by_action.setdefault(act, []).append((rid, cond, "unmet" in r))
            req = refs("rule " + rid, "when.requires", when.get("requires", []), "action")
            bt = when.get("by_turn")
            if bt is not None:
                if not whole(bt) or bt < 1:
                    rep.error("shape", "rule %s: when.by_turn must be a whole number, 1 or more" % rid)
                elif turns and bt > turns:
                    rep.error("duration", "rule %s has a deadline of turn %d, after the last turn (%d)" % (rid, bt, turns))
                elif not isinstance(r.get("late"), dict):
                    rep.advise("deadline_no_late", "rule %s has a deadline but says nothing about doing %s late. The facilitator will have to make a judgement call" % (rid, act))
            if bt is None and "late" in r:
                rep.error("shape", "rule %s: late needs when.by_turn" % rid)
            if not req and not cond and "unmet" in r:
                rep.error("shape", "rule %s: unmet needs when.requires or when.state, since it applies when they do not hold" % rid)
        if not isinstance(r.get("then"), dict):
            rep.error("shape", "rule %s: then is missing: say what happens when the condition is met" % rid)
        for name in OUTCOMES:
            o = r.get(name)
            if o is None:
                continue
            where = "rule %s, %s" % (rid, name)
            if not isinstance(o, dict) or not text_ok(o.get("text"), 8):
                rep.error("shape", "%s: text is missing: write the outcome the facilitator will read out" % where)
                continue
            if "done" in o and not isinstance(o["done"], bool):
                rep.error("shape", "%s: done must be true or false" % where)
            if o.get("done") is False and not clock_rule:
                costed = [a for a in actions if isinstance(a, dict) and a.get("id") == when.get("action") and isinstance(a.get("cost"), dict) and a["cost"]]
                if costed:
                    rep.advise("cost_on_failed_attempt", "%s is marked done: false, and action %s has a cost. The cost is spent even though the attempt "
                               "does not take effect. If a failed attempt should cost nothing, take the cost off the action or say so in the outcome" % (where, when.get("action")))
            got = refs(where, "reveals", o.get("reveals", []), "hidden fact")
            if not clock_rule:
                revealed_by_rule.update(got)
            for f in refs(where, "fires", o.get("fires", []), "inject"):
                fired.add(f)
                if index["inject"][f].get("turn") is not None:
                    rep.error("reference", "%s fires inject %s, which already has a fixed turn. A fired inject has turn null" % (where, f))
            st = o.get("set", {})
            if not isinstance(st, dict) or not all(scalar(v) for v in st.values()):
                rep.error("shape", "%s: set must be an object of state values" % where)
            else:
                for k in st:
                    if k not in state:
                        rep.error("reference", "%s sets %r, which is not a key in state" % (where, k))
    for act, group in by_action.items():
        for a in range(len(group)):
            for b in range(a + 1, len(group)):
                (ra, ca, _), (rb, cb, _) = group[a], group[b]
                if not any(k in cb and cb[k] != ca[k] for k in ca):
                    rep.error("rule_clash", "rules %s and %s are both about action %s and their conditions can hold together. "
                              "Give them state conditions that differ, or merge them: the facilitator cannot tell which applies" % (ra, rb, act))
        if sum(1 for _, _, has_unmet in group if has_unmet) > 1:
            rep.error("rule_clash", "more than one rule for action %s carries an unmet outcome (%s). Only one may" % (act, ", ".join(g[0] for g in group if g[2])))
    for inj in injects:
        if inj.get("turn") is None and inj.get("id") in index["inject"] and inj["id"] not in fired:
            rep.error("inject_unreachable", "inject %s has no turn and no rule fires it, so it can never be delivered" % inj["id"])
    for h in hidden:
        if h.get("id") in index["hidden fact"] and h["id"] not in revealed_by_action and h["id"] not in revealed_by_rule:
            rep.error("hidden_undiscoverable", "hidden fact %s can never be discovered: no action reveals it and no rule outcome an action can cause reveals it. "
                      "Give an action that finds it, or move it to unknowable" % h["id"])
    # Conservative fact/action reachability. State predicates, deadlines and resources
    # may still block a syntactically reachable action, so this is not a playability proof.
    if not rep.has("shape", "reference", "duplicate_id"):
        known, possible_actions, possible_injects = set(), set(), set()
        for inj in injects:
            if inj.get("turn") is not None:
                possible_injects.add(inj["id"])
        changed = True
        while changed:
            prior = (len(known), len(possible_actions), len(possible_injects))
            for inj in injects:
                if inj["id"] in possible_injects:
                    known.update(inj.get("reveals", []))
            for action in actions:
                if set(action.get("needs_fact", [])) <= known:
                    possible_actions.add(action["id"])
                    known.update(action.get("reveals", []))
            for rule in rules:
                when = rule["when"]
                eligible = ("at_turn" in when or when.get("action") in possible_actions)
                if eligible and set(when.get("requires", [])) <= possible_actions:
                    for name in OUTCOMES:
                        outcome = rule.get(name, {})
                        known.update(outcome.get("reveals", []))
                        possible_injects.update(outcome.get("fires", []))
            changed = prior != (len(known), len(possible_actions), len(possible_injects))
        for fact in hidden:
            if fact["id"] not in known and fact["id"] in revealed_by_action | revealed_by_rule:
                rep.error("hidden_dependency_cycle", "hidden fact %s is mentioned by a reveal but no fact/action dependency path reaches it" % fact["id"])
    for k in key_actions:
        kid = k.get("id", "?")
        if not text_ok(k.get("label"), 3):
            rep.error("shape", "key action %s: label is missing" % kid)
        if k.get("action") not in index["action"]:
            rep.error("reference", "key action %s: action %r is not an action in this file" % (kid, k.get("action")))
        if k.get("from_inject") not in index["inject"]:
            rep.error("reference", "key action %s: from_inject %r is not an inject in this file" % (kid, k.get("from_inject")))

    if not rep.has("shape", "reference", "duplicate_id"):
        fixed = [i for i in injects if i.get("turn") is not None]
        if injects and all(i["tone"] == "bad" for i in injects):
            rep.advise("all_bad_news", "every inject is bad news. If no decision can make anything go well, the player learns only to endure. Add one that rewards a good call")
        if injects and not any(i["misleading"] for i in injects):
            rep.advise("nothing_misleading", "no inject carries misleading information. Real incidents do; without one the exercise is too easy")
        if turns and turns > 12:
            rep.advise("long_first_run", "%d turns is long for a first run. About 8 to 12 holds attention" % turns)
        if not 2 <= len(objectives) <= 4:
            rep.advise("objective_count", "%d objective(s). Two to four is the range an exercise of this size can say something about" % len(objectives))
        if not plan:
            rep.advise("no_plan", "no plan steps are given, so decisions cannot be logged against the player's plan. Add the runbook's steps if one exists")
        if not key_actions:
            rep.advise("no_key_actions", "no key actions are named, so the after-action tables cannot report time to containment or the like")
        for i in fixed:
            if turns and i.get("expects") and whole(i.get("within")) and i["turn"] + i["within"] > turns:
                rep.advise("window_past_end", "inject %s on turn %d allows %d more turn(s), which runs past the last turn (%d)" % (i["id"], i["turn"], i["within"], turns))
    summary = {"objectives": len(objectives), "injects": len(injects), "misleading_injects": sum(1 for i in injects if i.get("misleading") is True),
               "actions": len(actions), "rules": len(rules), "hidden_facts": len(hidden), "unknowable": len(d.get("unknowable", []) or []),
               "turns": turns, "plan_steps": len(plan)}
    return rep.errors, rep.advisories, summary


def render(d, errors, advisories, summary):
    title = d.get("title") if isinstance(d, dict) and text_ok(d.get("title")) else "(no title)"
    L = ["scenario_check: %s" % title]
    L += ["  ERROR     %s  [%s]" % (e["message"], e["code"]) for e in errors]
    L += ["  ADVISORY  %s  [%s]" % (a["message"], a["code"]) for a in advisories]
    if summary:
        L.append("  %s turn(s) | %d objective(s) | %d inject(s), %d misleading | %d action(s) | %d rule(s) | %d hidden fact(s) | %d unknowable | %d plan step(s)"
                 % (summary["turns"] if summary["turns"] else "?", summary["objectives"], summary["injects"], summary["misleading_injects"],
                    summary["actions"], summary["rules"], summary["hidden_facts"], summary["unknowable"], summary["plan_steps"]))
    L.append("RESULT: %s. %d error(s), %d advisory note(s). A pass means the file can be played by its own rules. "
             "It does not mean the scenario is realistic or fair." % ("FAIL" if errors else "PASS", len(errors), len(advisories)))
    return "\n".join(L).encode("ascii", "replace").decode("ascii")


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a in FLAGS:
            flags.add(a)
        elif a.startswith("-") and a != "-":
            print("scenario_check: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print("scenario_check: give exactly one scenario file. Usage: python scenario_check.py SCENARIO.json [--json]", file=sys.stderr)
        return 2
    try:
        d = load(args[0])
    except Unreadable as e:
        print("scenario_check: %s" % e, file=sys.stderr)
        return 2
    errors, advisories, summary = check(d)
    if "--json" in flags:
        text = json.dumps({"errors": errors, "advisories": advisories, "summary": summary, "result": "FAIL" if errors else "PASS"}, indent=1, ensure_ascii=True)
    else:
        text = render(d, errors, advisories, summary)
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
