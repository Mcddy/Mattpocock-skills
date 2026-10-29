#!/usr/bin/env python3
"""Validate a tabletop play log against its scenario and print the after-action tables.

Usage:
  python session_log.py SCENARIO.json LOG.jsonl [--state] [--json]

SCENARIO.json is the file scenario_check.py checks. It must pass that check first.
LOG.jsonl holds one JSON object per line, written by the facilitator as play goes on:
  {"turn": 3, "clock": "22:10",
   "class": "start|clock|inject|investigate|act|decide|communicate|delegate|other|wait|command",
   "inject": "I3",                 an inject id, a list of ids, or null: what was delivered on this line
   "input": "what the player typed", "action": "A4",
   "to": "R2",                     the role, when class is delegate
   "rule": "RU4",                  a rule id, "judgement call", or null
   "outcome": "then|late|unmet",   with a rule id
   "reason": "why",                required with "judgement call" and with "refused"
   "refused": "why the action was not allowed", optional; a refused action changes nothing
                                   and is not counted as done. Nor is one whose rule outcome carries
                                   "done": false in the scenario
   "costs_turn": true,             for class other: did the free input use up the player's turn
   "changes": [{"reveal": "H2"}, {"set": {"disk": "ok"}}, {"spend": {"RES1": 1}}, {"fire": "I6"}],
   "plan": {"step": "P3", "relation": "follows|skips|contradicts|silent"},
   "hint": true, "text": "the hint that was given"}
Classes. start: the first line of a turn, delivering that turn's injects if it has any; the
facilitator writes it before printing the turn block, so the block can be checked against
--state. clock: a clock rule applied at the start of a turn, before the start line. inject: a
line that only delivers an inject. investigate, act, decide, communicate: the player's own
action, matching the action's class.
delegate: an action handed to a role. other: free input the action list does not cover, always a
judgement call. wait: the player lets the turn pass. command: status, log, help, hint, pause, end.

What it enforces (ERROR, exit 1). Each error names the log line. Codes, also given by --json:
  [shape]                 a line that is not the shape above
  [reference]             an inject, action, rule, role, fact, resource or plan step the scenario
                          does not have
  [turn_order]            the first line is not turn 1, a turn goes backwards or skips, a line
                          follows "end", or the turn is past the scenario's last
  [clock]                 the clock is not start_clock plus the turns played
  [inject_timing]         an inject delivered on the wrong turn, twice, or with nothing to fire it
  [inject_missed]         a due inject or a fired inject that was never delivered
  [clock_rule]            a clock rule applied when its condition did not hold, on the wrong
                          turn or after the player acted; or one that should have applied and
                          was not logged
  [rule_mismatch]         the rule or outcome logged is not the one the scenario's rules give; or
                          the rules were silent and the line is not labelled a judgement call
  [missing_consequence]   the rules say something happens and the log does not record it
  [reveal_without_cause]  FACILITATION ERROR: a hidden fact revealed with no action, rule outcome
                          or inject that discovers it
  [change_without_cause]  any other state change with no cause
  [needs_fact]            FACILITATION ERROR: an action that depends on a hidden fact was offered
                          or accepted before the fact was discovered
  [turn_budget]           two turn-costing actions by the player in one turn, or a role used twice
  [delegate]              an action handed to a role that cannot take it or is not yet available
  [resource]              an action allowed although its cost was more than was left
What it reports for a person to decide: nothing is scored. The tables are counts with their
denominators: the decision timeline, turns from an inject to each key action, each inject as
handled, late, missed or not expecting a response, bait taken, hidden facts found and not found,
hints, judgement calls with their reasons, decisions against the plan, resources, final state.

What it cannot tell: whether a decision was wise, whether a judgement call was fair, or whether
what the facilitator said in the conversation matched what was logged. It reads the log.

--state prints only the compact state block computed from the log, for comparing with the one the
facilitator printed, or for resuming.

Exit codes: 0 the log is consistent with the scenario. 1 it is not. 2 bad arguments, unreadable
input, or a scenario that does not pass scenario_check.py.
"""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenario_check as sc  # noqa: E402

COMMANDS = ("status", "log", "help", "hint", "pause", "end")
ACTION_CLASSES = ("investigate", "act", "decide", "communicate")
CLASSES = ("start", "clock", "inject") + ACTION_CLASSES + ("delegate", "other", "wait", "command")
RELATIONS = ("follows", "skips", "contradicts", "silent")
JUDGEMENT = "judgement call"
FLAGS = {"--json", "--state"}
LINE_KEYS = {"turn", "clock", "class", "inject", "input", "action", "to", "rule", "outcome", "reason", "refused", "costs_turn", "changes", "plan", "hint", "text"}


def same(a, b):
    """Equal without coercion: true is not 1 and "1" is not 1. A whole number equals the same float."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return type(a) is type(b) and a == b


def clock_at(start, minutes_per_turn, turn):
    h, m = start.split(":")
    total = (int(h) * 60 + int(m) + (turn - 1) * minutes_per_turn) % 1440
    return "%02d:%02d" % (total // 60, total % 60)


def show(v):
    return json.dumps(v, ensure_ascii=True) if not isinstance(v, str) or re.search(r"[\s=|,]", v) else v


class Engine:
    def __init__(self, scenario):
        s = self.s = scenario
        d = s["duration"]
        self.last_turn, self.mpt, self.start = d["turns"], d["minutes_per_turn"], d["start_clock"]
        self.actions = {a["id"]: a for a in s["actions"]}
        self.injects = {i["id"]: i for i in s["injects"]}
        self.roles = {r["id"]: r for r in s.get("roles", [])}
        self.hidden = {h["id"]: h for h in s.get("hidden_facts", [])}
        self.plan = {p["id"]: p for p in s.get("plan", [])}
        self.rules = {r["id"]: r for r in s.get("rules", [])}
        self.action_rules, self.clock_rules = {}, []
        for r in s.get("rules", []):
            if "at_turn" in r["when"]:
                self.clock_rules.append(r)
            else:
                self.action_rules.setdefault(r["when"]["action"], []).append(r)
        self.state = dict(s.get("state", {}))
        self.start_amount = {r["id"]: r["amount"] for r in s.get("resources", [])}
        self.left = dict(self.start_amount)
        self.revealed, self.done, self.delivered, self.fired = {}, {}, {}, {}
        self.turn, self.ended, self.lines = 0, False, 0
        self.own_spent, self.roles_used, self.player_acted = False, set(), False
        self.clock_due, self.clock_seen = set(), set()
        self.errors, self.timeline, self.hints, self.judgements, self.plan_marks, self.reveal_log = [], [], [], [], [], []

    # ---- helpers ----
    def err(self, n, code, message):
        self.errors.append({"line": n, "code": code, "message": "line %d: %s" % (n, message)})

    def holds(self, cond):
        return all(k in self.state and same(self.state[k], v) for k, v in (cond or {}).items())

    def open_turn(self, turn):
        self.turn, self.own_spent, self.roles_used, self.player_acted = turn, False, set(), False
        self.clock_due = {r["id"] for r in self.clock_rules if r["when"]["at_turn"] == turn and self.holds(r["when"].get("state"))}
        self.clock_seen = set()

    def close_turn(self, n):
        t = self.turn
        for rid in sorted(self.clock_due - self.clock_seen):
            self.err(n, "clock_rule", "rule %s applied at the start of turn %d (its condition held) and the log has no line for it. The rules say: %s"
                     % (rid, t, self.rules[rid]["then"]["text"]))
        for i in self.s["injects"]:
            if i.get("turn") == t and i["id"] not in self.delivered:
                self.err(n, "inject_missed", "inject %s was due on turn %d and was never delivered" % (i["id"], t))
        for iid, when in sorted(self.fired.items()):
            if iid not in self.delivered and when < t:
                self.err(n, "inject_missed", "inject %s was fired on turn %d and was not delivered by turn %d" % (iid, when, t))

    def resolve(self, action_id, turn):
        """(rule, outcome, status). status: none (no rule), written, or silent."""
        rules = self.action_rules.get(action_id, [])
        if not rules:
            return None, None, "none"
        match = [r for r in rules if all(x in self.done for x in r["when"].get("requires", [])) and self.holds(r["when"].get("state"))]
        if match:
            r = match[0]
            outcome = "late" if ("by_turn" in r["when"] and turn > r["when"]["by_turn"]) else "then"
        else:
            with_unmet = [r for r in rules if "unmet" in r]
            if len(with_unmet) != 1:
                return None, None, "silent"
            r, outcome = with_unmet[0], "unmet"
        return (r, outcome, "written") if outcome in r else (r, outcome, "silent")

    def effects(self, source, required, optional):
        """Add what a rule outcome, an inject or an action declares to the required and optional sets."""
        for h in source.get("reveals", []):
            (optional if h in self.revealed else required).add(("reveal", h))
        for k, v in (source.get("set") or {}).items():
            (optional if (k in self.state and same(self.state[k], v)) else required).add(("set", k, json.dumps(v)))
        for f in source.get("fires", []):
            required.add(("fire", f))
        for res, amt in (source.get("cost") or {}).items():
            required.add(("spend", res, float(amt)))

    def take(self, n, source, cause, required, optional, causes):
        """Collect what an inject, an action or a rule outcome declares, and apply it at once, so that
        whatever comes next on the same line is judged against the state it would really see."""
        req, opt = set(), set()
        self.effects(source, req, opt)
        required |= req
        optional |= opt
        causes.append(cause)
        self.apply(n, req, cause)

    def read_changes(self, n, line):
        got, raw = set(), line.get("changes", [])
        if not isinstance(raw, list):
            self.err(n, "shape", "changes must be a list")
            return got
        for c in raw:
            if not isinstance(c, dict) or len(c) != 1:
                self.err(n, "shape", "each change is an object with one key: reveal, set, spend or fire")
                continue
            kind, val = next(iter(c.items()))
            if kind == "reveal" and isinstance(val, str):
                if val not in self.hidden:
                    self.err(n, "reference", "change reveals %r, which is not a hidden fact in the scenario" % val)
                else:
                    got.add(("reveal", val))
            elif kind == "fire" and isinstance(val, str):
                if val not in self.injects:
                    self.err(n, "reference", "change fires %r, which is not an inject in the scenario" % val)
                else:
                    got.add(("fire", val))
            elif kind == "set" and isinstance(val, dict) and all(sc.scalar(v) for v in val.values()):
                for k, v in val.items():
                    if k not in self.state:
                        self.err(n, "reference", "change sets %r, which is not a key in the scenario's state" % k)
                    else:
                        got.add(("set", k, json.dumps(v)))
            elif kind == "spend" and isinstance(val, dict) and all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in val.values()):
                for k, v in val.items():
                    if k not in self.left:
                        self.err(n, "reference", "change spends %r, which is not a resource in the scenario" % k)
                    else:
                        got.add(("spend", k, float(v)))
            else:
                self.err(n, "shape", "change %s is not one of reveal (a fact id), set (state values), spend (resource amounts) or fire (an inject id)" % json.dumps(c)[:60])
        return got

    def apply(self, n, changes, cause):
        for c in sorted(changes, key=lambda x: [str(p) for p in x]):
            if c[0] == "reveal" and c[1] not in self.revealed:
                self.revealed[c[1]] = self.turn
                self.reveal_log.append({"fact": c[1], "turn": self.turn, "line": n, "cause": cause})
            elif c[0] == "set":
                self.state[c[1]] = json.loads(c[2])
            elif c[0] == "spend":
                self.left[c[1]] -= c[2]
            elif c[0] == "fire" and c[1] not in self.fired and c[1] not in self.delivered:
                self.fired[c[1]] = self.turn

    def deliver(self, n, iid, fixed_pass):
        """Deliver one inject. Fixed-turn injects are handled before the action, fired ones after."""
        inj = self.injects[iid]
        if (inj.get("turn") is not None) != fixed_pass:
            return None
        if iid in self.delivered:
            self.err(n, "inject_timing", "inject %s was already delivered on turn %d" % (iid, self.delivered[iid]))
            return None
        if inj.get("turn") is not None:
            if inj["turn"] != self.turn:
                self.err(n, "inject_timing", "inject %s belongs to turn %d and was delivered on turn %d" % (iid, inj["turn"], self.turn))
        elif iid not in self.fired:
            self.err(n, "inject_timing", "inject %s was delivered, but no rule had fired it" % iid)
        elif self.turn > self.fired[iid] + 1:
            self.err(n, "inject_timing", "inject %s was fired on turn %d and delivered on turn %d; a fired inject arrives the same turn or the next" % (iid, self.fired[iid], self.turn))
        self.delivered[iid] = self.turn
        return inj

    # ---- one line ----
    def feed(self, n, line):
        self.lines += 1
        if not isinstance(line, dict):
            self.err(n, "shape", "the line is not a JSON object")
            return
        for k in sorted(set(line) - LINE_KEYS):
            self.err(n, "shape", "unknown key %r" % k)
        if line.get("input") is not None and not isinstance(line["input"], str):
            self.err(n, "shape", "input must be text or null")
            return
        turn, cls = line.get("turn"), line.get("class")
        if not sc.whole(turn) or turn < 1:
            self.err(n, "shape", "turn must be a whole number, 1 or more")
            return
        if cls not in CLASSES or not isinstance(cls, str):
            self.err(n, "shape", "class must be one of %s" % ", ".join(CLASSES))
            return
        if self.ended:
            self.err(n, "turn_order", "this line comes after the end command")
        if self.turn == 0:
            if turn != 1:
                self.err(n, "turn_order", "the log starts at turn %d; it must start at turn 1" % turn)
            self.open_turn(turn)
        elif turn == self.turn + 1:
            self.close_turn(n)
            self.open_turn(turn)
        elif turn != self.turn:
            self.err(n, "turn_order", "turn %d follows turn %d; turns go up one at a time and never back" % (turn, self.turn))
            if turn > self.turn:
                self.open_turn(turn)
        if turn > self.last_turn:
            self.err(n, "turn_order", "turn %d is past the scenario's last turn (%d)" % (turn, self.last_turn))
        want_clock = clock_at(self.start, self.mpt, self.turn)
        if line.get("clock") != want_clock:
            self.err(n, "clock", "the clock reads %r; turn %d is %s (start %s, %d minutes a turn)" % (line.get("clock"), self.turn, want_clock, self.start, self.mpt))

        inj_ids = line.get("inject")
        inj_ids = [] if inj_ids is None else ([inj_ids] if isinstance(inj_ids, str) else inj_ids)
        if not isinstance(inj_ids, list) or not all(isinstance(x, str) for x in inj_ids):
            self.err(n, "shape", "inject must be an id, a list of ids, or null")
            inj_ids = []
        for iid in [x for x in inj_ids if x not in self.injects]:
            self.err(n, "reference", "inject %r is not in the scenario" % iid)
        inj_ids = [x for x in inj_ids if x in self.injects]

        required, optional, causes = set(), set(), []
        for iid in inj_ids:
            inj = self.deliver(n, iid, fixed_pass=True)
            if inj:
                self.take(n, inj, "inject " + iid, required, optional, causes)
        got = self.read_changes(n, line)
        judged, adjudication, action, who, took_effect = False, "", None, "player", True
        rule_id, outcome = line.get("rule"), line.get("outcome")
        refused = line.get("refused")

        if cls in ("start", "inject"):
            if cls == "inject" and not inj_ids:
                self.err(n, "shape", "an inject line delivers at least one inject")
            if cls == "start" and self.player_acted:
                self.err(n, "shape", "a start line is the first thing in its turn, before the player acts")
            if line.get("action") is not None or rule_id is not None:
                self.err(n, "shape", "a %s line carries no action and no rule" % cls)
        elif cls == "clock":
            r = self.rules.get(rule_id)
            if r is None or "at_turn" not in r["when"]:
                self.err(n, "reference" if r is None else "clock_rule", "a clock line names a clock rule; %r is not one" % rule_id)
            else:
                if r["when"]["at_turn"] != self.turn:
                    self.err(n, "clock_rule", "rule %s applies at turn %d, not turn %d" % (rule_id, r["when"]["at_turn"], self.turn))
                elif rule_id not in self.clock_due:
                    self.err(n, "clock_rule", "rule %s was applied, but its condition %s did not hold at the start of turn %d"
                             % (rule_id, json.dumps(r["when"].get("state", {})), self.turn))
                elif self.player_acted:
                    self.err(n, "clock_rule", "rule %s applies at the start of the turn, before the player acts" % rule_id)
                if rule_id in self.clock_seen:
                    self.err(n, "clock_rule", "rule %s was already applied this turn" % rule_id)
                self.clock_seen.add(rule_id)
                self.take(n, r["then"], "rule " + rule_id, required, optional, causes)
                adjudication = "%s then" % rule_id
        elif cls == "command":
            word = (line["input"].strip().lower() if isinstance(line.get("input"), str) else "")
            if word not in COMMANDS:
                self.err(n, "shape", "a command line's input is one of %s" % ", ".join(COMMANDS))
            if line.get("action") is not None or rule_id is not None:
                self.err(n, "shape", "a command carries no action and no rule; it never changes the scenario")
            if word == "hint" or line.get("hint") is True:
                if not sc.text_ok(line.get("text"), 8):
                    self.err(n, "shape", "a hint line records the hint that was given, in text")
                self.hints.append({"turn": self.turn, "line": n, "text": line.get("text") or ""})
            if word == "end":
                self.ended = True
            adjudication = "command"
        elif cls == "wait":
            if self.own_spent:
                self.err(n, "turn_budget", "the player's turn on turn %d was already used" % self.turn)
            self.own_spent = self.player_acted = True
            adjudication = "waited"
        elif cls == "other":
            self.player_acted = judged = True
            if line.get("action") is not None:
                self.err(n, "shape", "class other is for input the action list does not cover; it carries no action id")
            if not isinstance(line.get("costs_turn"), bool):
                self.err(n, "shape", "class other says whether the input used the player's turn: costs_turn true or false")
            elif line["costs_turn"]:
                if self.own_spent:
                    self.err(n, "turn_budget", "the player's turn on turn %d was already used" % self.turn)
                self.own_spent = True
            if rule_id != JUDGEMENT or not sc.text_ok(line.get("reason"), 12):
                self.err(n, "rule_mismatch", "free input outside the action list is adjudicated by a judgement call: rule must be \"judgement call\" with a reason")
            adjudication = JUDGEMENT
        else:                                   # the player's own action, or a delegated one
            self.player_acted = True
            action = self.actions.get(line.get("action"))
            if action is None:
                self.err(n, "reference", "action %r is not in the scenario" % line.get("action"))
            else:
                aid = action["id"]
                if cls == "delegate":
                    who = line.get("to")
                    role = self.roles.get(who)
                    if role is None:
                        self.err(n, "reference", "role %r is not in the scenario" % who)
                    elif not refused:
                        if who not in action.get("delegable_to", []):
                            self.err(n, "delegate", "action %s cannot be handed to %s (%s)" % (aid, who, role["name"]))
                        if role.get("available_from_turn", 1) > self.turn:
                            self.err(n, "delegate", "%s (%s) is not available until turn %d" % (who, role["name"], role.get("available_from_turn", 1)))
                        if who in self.roles_used:
                            self.err(n, "turn_budget", "%s (%s) was already given something to do on turn %d" % (who, role["name"], self.turn))
                        self.roles_used.add(who)
                elif cls != action["class"]:
                    self.err(n, "shape", "action %s is of class %s, but the line says %s" % (aid, action["class"], cls))
                missing_facts = [h for h in action.get("needs_fact", []) if h not in self.revealed]
                short = [r for r, amt in action.get("cost", {}).items() if self.left.get(r, 0) < amt]
                if refused is not None:
                    if not sc.text_ok(refused, 8):
                        self.err(n, "shape", "refused carries the reason the action was not allowed")
                    if rule_id is not None or got:
                        self.err(n, "change_without_cause", "a refused action applies no rule and changes nothing")
                        got = set()
                    adjudication, action = "refused", None
                else:
                    if missing_facts:
                        self.err(n, "needs_fact", "FACILITATION ERROR: action %s depends on %s, which the player had not discovered. Offering or accepting it gives the hidden fact away"
                                 % (aid, ", ".join(missing_facts)))
                    if short:
                        self.err(n, "resource", "action %s costs more %s than is left; by the rules it is refused" % (aid, ", ".join(short)))
                    if cls != "delegate" and action["costs_turn"]:
                        if self.own_spent:
                            self.err(n, "turn_budget", "a second turn-costing action by the player on turn %d (%s)" % (self.turn, aid))
                        self.own_spent = True
                    rule, want, status = self.resolve(aid, self.turn)
                    self.take(n, action, "action " + aid, required, optional, causes)
                    if status == "none":
                        if rule_id is not None:
                            self.err(n, "rule_mismatch", "action %s has no rule; its own effects are all that happens, so rule must be null (the log says %r)" % (aid, rule_id))
                        adjudication = "no rule"
                    elif status == "written":
                        if rule_id != rule["id"] or outcome != want:
                            self.err(n, "rule_mismatch", "the scenario's rules give %s, outcome %s, for action %s here; the log records %r, outcome %r"
                                     % (rule["id"], want, aid, rule_id, outcome))
                        self.take(n, rule[want], "rule %s (%s)" % (rule["id"], want), required, optional, causes)
                        adjudication = "%s %s" % (rule["id"], want)
                        took_effect = rule[want].get("done") is not False
                    else:
                        judged = True
                        if rule_id != JUDGEMENT or not sc.text_ok(line.get("reason"), 12):
                            self.err(n, "rule_mismatch", "the rules are silent on action %s in this situation%s; the line must be a \"judgement call\" with a reason"
                                     % (aid, (" (no %s outcome is written for %s)" % (want, rule["id"])) if rule else ""))
                        adjudication = JUDGEMENT

        for iid in inj_ids:
            # Fired injects are delivered after the rule on this line has had the chance to fire them.
            if self.injects[iid].get("turn") is None:
                for c in list(required) + list(got):
                    if c[0] == "fire" and c[1] == iid and iid not in self.fired and iid not in self.delivered:
                        self.fired[iid] = self.turn
                inj = self.deliver(n, iid, fixed_pass=False)
                if inj:
                    self.take(n, inj, "inject " + iid, required, optional, causes)

        for c in sorted(required - got, key=str):
            self.err(n, "missing_consequence", "%s should have happened here (%s) and the log does not record it" % (self.describe(c), ", ".join(causes) or "the rules"))
        extra = got - required - optional
        if judged:
            # A judgement call may change things the rules do not cover. It is recorded, with its reason.
            self.judgements.append({"turn": self.turn, "line": n, "input": line.get("input") or "", "reason": line.get("reason") or "",
                                    "changes": sorted(self.describe(c) for c in extra)})
            self.apply(n, extra, JUDGEMENT)
        else:
            for c in sorted(extra, key=str):
                if c[0] == "reveal":
                    self.err(n, "reveal_without_cause", "FACILITATION ERROR: hidden fact %s was revealed on turn %d with no action, rule outcome or inject that discovers it" % (c[1], self.turn))
                else:
                    self.err(n, "change_without_cause", "%s has no cause: no rule, inject or action on this line produces it" % self.describe(c))
            self.apply(n, extra, "no cause (see the errors)")
        if action is not None and adjudication != "refused" and took_effect:
            self.done.setdefault(action["id"], self.turn)

        mark = line.get("plan")
        if mark is not None:
            if not isinstance(mark, dict) or mark.get("relation") not in RELATIONS or (mark.get("step") is not None and mark.get("step") not in self.plan):
                self.err(n, "reference", "plan must be {\"step\": a plan step id or null, \"relation\": one of %s}" % ", ".join(RELATIONS))
            else:
                self.plan_marks.append({"turn": self.turn, "line": n, "step": mark.get("step"), "relation": mark["relation"],
                                        "what": (action["label"] if action else (line.get("input") or cls))})
        if cls not in ("start", "inject", "clock"):
            self.timeline.append({"turn": self.turn, "clock": want_clock, "who": who if cls == "delegate" else "player", "class": cls,
                                  "input": line.get("input") or "", "action": line.get("action"), "adjudication": adjudication,
                                  "plan": ("%s %s" % (mark.get("relation"), mark.get("step") or "")).strip() if isinstance(mark, dict) and mark.get("relation") in RELATIONS else ""})
        if self.ended and cls == "command":
            self.close_turn(n)

    def describe(self, c):
        if c[0] == "reveal":
            return "reveal %s" % c[1]
        if c[0] == "set":
            return "set %s=%s" % (c[1], show(json.loads(c[2])))
        if c[0] == "spend":
            return "spend %g of %s" % (c[2], c[1])
        return "fire %s" % c[1]

    # ---- tables ----
    def tables(self):
        s, out = self.s, {}
        mpt = self.mpt
        out["turns_played"] = self.turn
        out["ended"] = self.ended
        out["timeline"] = self.timeline
        keys = []
        for k in s.get("key_actions", []):
            ti, ta = self.delivered.get(k["from_inject"]), self.done.get(k["action"])
            if ta is None:
                status = "not done by turn %d" % self.turn
            elif ti is None:
                status = "done on turn %d; inject %s was never delivered" % (ta, k["from_inject"])
            elif ta < ti:
                status = "done on turn %d, before the inject (turn %d)" % (ta, ti)
            else:
                status = "%d turn(s) after the inject (%d scenario minutes): inject turn %d, action turn %d" % (ta - ti, (ta - ti) * mpt, ti, ta)
            keys.append({"id": k["id"], "label": k["label"], "action": k["action"], "from_inject": k["from_inject"], "inject_turn": ti, "action_turn": ta, "status": status})
        out["key_actions"] = keys
        injects = []
        for i in s["injects"]:
            iid, ti = i["id"], self.delivered.get(i["id"])
            row = {"id": iid, "delivered_turn": ti, "misleading": i["misleading"], "probes": i.get("probes", []), "bait_taken_turn": None}
            if ti is None:
                row["status"] = "not delivered (never fired)" if i.get("turn") is None else (
                    "not delivered (turn %d was not reached)" % i["turn"] if i["turn"] > self.turn else "not delivered (it was due on turn %d)" % i["turn"])
            elif not i.get("expects"):
                row["status"] = "no response expected"
            else:
                times = [self.done[a] for a in i["expects"] if a in self.done]
                if not times:
                    row["status"] = "missed"
                else:
                    ta = min(times)
                    row["response_turn"] = ta
                    if ta < ti:
                        row["status"] = "handled (already done on turn %d)" % ta
                    elif ta - ti <= i["within"]:
                        row["status"] = "handled (turn %d, %d after)" % (ta, ta - ti)
                    else:
                        row["status"] = "late (turn %d, %d after; %d allowed)" % (ta, ta - ti, i["within"])
            if ti is not None and i.get("bait"):
                taken = [self.done[a] for a in i["bait"] if a in self.done and self.done[a] >= ti]
                if taken:
                    row["bait_taken_turn"] = min(taken)
            injects.append(row)
        out["injects"] = injects
        objectives = []
        for o in s["objectives"]:
            rows = [r for r in injects if o["id"] in r["probes"]]
            expecting = [r for r in rows if r["delivered_turn"] is not None and r["status"] != "no response expected"]
            objectives.append({"id": o["id"], "text": o["text"], "injects": [{"id": r["id"], "status": r["status"], "bait_taken_turn": r["bait_taken_turn"]} for r in rows],
                               "handled": sum(1 for r in expecting if r["status"].startswith("handled")), "late": sum(1 for r in expecting if r["status"].startswith("late")),
                               "missed": sum(1 for r in expecting if r["status"] == "missed"), "expecting_a_response": len(expecting),
                               "delivered": sum(1 for r in rows if r["delivered_turn"] is not None), "probing": len(rows)})
        out["objectives"] = objectives
        out["hidden_found"] = self.reveal_log
        out["hidden_not_found"] = [h for h in self.hidden if h not in self.revealed]
        out["hints"] = self.hints
        out["judgement_calls"] = self.judgements
        counts = {r: sum(1 for m in self.plan_marks if m["relation"] == r) for r in RELATIONS}
        used = {m["step"] for m in self.plan_marks if m["step"]}
        out["plan"] = {"steps": len(self.plan), "marked_decisions": len(self.plan_marks), "counts": counts, "marks": self.plan_marks,
                       "steps_never_referenced": [p for p in self.plan if p not in used]}
        out["resources"] = [{"id": r, "start": self.start_amount[r], "spent": self.start_amount[r] - self.left[r], "left": self.left[r]} for r in self.start_amount]
        out["final_state"] = self.state
        return out

    def state_block(self):
        s = self.s
        tasks_open, tasks_closed = [], []
        for i in s["injects"]:
            if i["id"] in self.delivered and i.get("task"):
                (tasks_closed if any(a in self.done for a in i.get("expects", [])) else tasks_open).append("%s (%s)" % (i["task"], i["id"]))
        pending = sorted(i for i in self.fired if i not in self.delivered)
        L = ["STATE v1 | scenario %s@%s | turn %d of %d | clock %s | own action this turn: %s%s"
             % (s["id"], s["version"], self.turn, self.last_turn, clock_at(self.start, self.mpt, max(self.turn, 1)), "used" if self.own_spent else "free", " | ENDED" if self.ended else ""),
             "known: %s | revealed: %s" % (" ".join(k["id"] for k in s["known_facts"]), " ".join(sorted(self.revealed, key=lambda h: (self.revealed[h], h))) or "none"),
             "state: " + (" ".join("%s=%s" % (k, show(v)) for k, v in self.state.items()) or "none"),
             "done: " + (" ".join("%s@%d" % (a, t) for a, t in sorted(self.done.items(), key=lambda x: (x[1], x[0]))) or "none"),
             "injects: %s | pending: %s" % (" ".join("%s@%d" % (i, t) for i, t in sorted(self.delivered.items(), key=lambda x: (x[1], x[0]))) or "none", " ".join(pending) or "none"),
             "tasks open: %s | closed: %s" % ("; ".join(tasks_open) or "none", "; ".join(tasks_closed) or "none"),
             "resources: " + (" ".join("%s=%g" % (r, v) for r, v in self.left.items()) or "none"),
             "hints: %d | judgement calls: %d | log lines: %d" % (len(self.hints), len(self.judgements), self.lines)]
        return "\n".join(L)


def render(engine, t):
    s = engine.s
    L = ["session_log: %s (%s@%s)" % (s["title"], s["id"], s["version"]), ""]
    L.append("VALIDATION")
    if engine.errors:
        L += ["  ERROR  %s  [%s]" % (e["message"], e["code"]) for e in engine.errors]
        L.append("  %d error(s). The tables below describe the log as written; read them with that in mind." % len(engine.errors))
    else:
        L.append("  The log is consistent with the scenario: %d line(s), %d turn(s) played of %d%s."
                 % (engine.lines, t["turns_played"], engine.last_turn, "" if t["ended"] else "; no end command, so the last turn was not checked for completeness"))
    L += ["", "DECISION TIMELINE"]
    for r in t["timeline"]:
        what = r["action"] or r["class"]
        L.append("  T%-2d %s  %-8s %-11s %-18s %s%s" % (r["turn"], r["clock"], r["who"], what, r["adjudication"], ("\"%s\"" % r["input"][:70]) if r["input"] else "",
                                                       ("  [plan: %s]" % r["plan"]) if r["plan"] else ""))
    L += ["", "TIME TO KEY ACTIONS"]
    L += ["  %-4s %-32s %s" % (k["id"], k["label"], k["status"]) for k in t["key_actions"]] or ["  none named in the scenario"]
    L += ["", "INJECTS"]
    for r in t["injects"]:
        L.append("  %-4s %-9s %s%s%s" % (r["id"], ("turn %d" % r["delivered_turn"]) if r["delivered_turn"] else "-", r["status"],
                                        "  [misleading]" if r["misleading"] else "", ("  [bait taken on turn %d]" % r["bait_taken_turn"]) if r["bait_taken_turn"] else ""))
    L += ["", "OBJECTIVES (counts, not a score)"]
    for o in t["objectives"]:
        L.append("  %s  %s" % (o["id"], o["text"]))
        L.append("      %d of %d probing inject(s) delivered; of the %d that expected a response: %d handled, %d late, %d missed"
                 % (o["delivered"], o["probing"], o["expecting_a_response"], o["handled"], o["late"], o["missed"]))
        L.append("      " + "; ".join("%s %s%s" % (i["id"], i["status"], (", bait taken on turn %d" % i["bait_taken_turn"]) if i["bait_taken_turn"] else "") for i in o["injects"]))
    L += ["", "HIDDEN FACTS"]
    L += ["  %-4s found on turn %d by %s" % (h["fact"], h["turn"], h["cause"]) for h in t["hidden_found"]]
    L.append("  not found: %s (%d of %d)" % (", ".join(t["hidden_not_found"]) or "none", len(t["hidden_not_found"]), len(engine.hidden)))
    L += ["", "HINTS USED: %d" % len(t["hints"])]
    L += ["  turn %d: %s" % (h["turn"], h["text"]) for h in t["hints"]]
    L += ["", "JUDGEMENT CALLS: %d" % len(t["judgement_calls"])]
    for j in t["judgement_calls"]:
        L.append("  turn %d: \"%s\"" % (j["turn"], j["input"][:80]))
        L.append("      ruling: %s" % j["reason"])
        L.append("      changes: %s" % (", ".join(j["changes"]) or "none"))
    p = t["plan"]
    L += ["", "PLAN"]
    if not p["steps"]:
        L.append("  the scenario has no plan steps")
    else:
        c = p["counts"]
        L.append("  %d decision(s) were logged against the plan: follows %d | skips %d | contradicts %d | plan silent %d"
                 % (p["marked_decisions"], c["follows"], c["skips"], c["contradicts"], c["silent"]))
        L += ["  T%-2d %-11s %-4s %s" % (m["turn"], m["relation"], m["step"] or "-", m["what"][:80]) for m in p["marks"]]
        L.append("  steps never referenced: %s (%d of %d)" % (", ".join(p["steps_never_referenced"]) or "none", len(p["steps_never_referenced"]), p["steps"]))
    L += ["", "RESOURCES"]
    L += ["  %-5s start %g, spent %g, left %g" % (r["id"], r["start"], r["spent"], r["left"]) for r in t["resources"]] or ["  none"]
    L += ["", "FINAL STATE", "  " + (" ".join("%s=%s" % (k, show(v)) for k, v in t["final_state"].items()) or "none")]
    L += ["", "RESULT: %s. %d error(s). These tables are counts for the after-action review. There is no score: an exercise is a way of finding things out, not an exam."
          % ("FAIL" if engine.errors else "PASS", len(engine.errors))]
    return "\n".join(L)


def read_log(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise sc.Unreadable("cannot read %s: %s" % (path, e.strerror or e))
    lines = []
    for n, text in enumerate(sc.decode(raw, str(path)).splitlines(), 1):
        if not text.strip():
            continue
        lines.append((n, sc.parse(text, "%s line %d" % (path, n))))
    if not lines:
        raise sc.Unreadable("%s holds no log lines" % path)
    return lines


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a in FLAGS:
            flags.add(a)
        elif a.startswith("-") and a != "-":
            print("session_log: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 2:
        print("session_log: give the scenario file and the log file. Usage: python session_log.py SCENARIO.json LOG.jsonl [--state] [--json]", file=sys.stderr)
        return 2
    try:
        scenario = sc.load(args[0])
        errors, _, _ = sc.check(scenario)
        if errors:
            print("session_log: %s does not pass scenario_check.py (%d error(s); first: %s). Fix the scenario first" % (args[0], len(errors), errors[0]["message"][:120]), file=sys.stderr)
            return 2
        lines = read_log(args[1])
    except sc.Unreadable as e:
        print("session_log: %s" % e, file=sys.stderr)
        return 2
    engine = Engine(scenario)
    for n, line in lines:
        engine.feed(n, line)
    tables = engine.tables()
    if "--json" in flags:
        text = json.dumps({"errors": engine.errors, "tables": tables, "state_block": engine.state_block(), "result": "FAIL" if engine.errors else "PASS"}, indent=1, ensure_ascii=True)
    elif "--state" in flags:
        text = engine.state_block() + ("\n(%d validation error(s); run without --state to see them)" % len(engine.errors) if engine.errors else "")
    else:
        text = render(engine, tables)
    try:
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if engine.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
