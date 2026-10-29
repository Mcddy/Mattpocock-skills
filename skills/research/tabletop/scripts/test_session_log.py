#!/usr/bin/env python3
"""Tests for session_log.py. Standard library only. Every fixture is built here by hand.

Usage:
  python test_session_log.py            run every test
  python test_session_log.py -v         name each test as it runs
  python test_session_log.py Validation.test_planted_hidden_fact_revealed_with_no_discovering_action

The scenario is the storeroom-door fixture from test_scenario_check.py. log() returns a play log
for it that is consistent with the scenario and whose after-action tables have known answers,
worked out by hand in test_tables_have_known_answers. Each validation test changes one thing in the
log and asserts the exact error code, beside the valid neighbour that must pass.

The planted failure the skill's specification asks for:
  test_planted_hidden_fact_revealed_with_no_discovering_action
      a log in which a hidden fact is revealed on a line whose action does not discover it.
      It is reported as a FACILITATION ERROR.
The specification's three named refusals: test_unknown_inject, test_turns_out_of_order and
test_state_change_with_no_cause.
Exit codes: 0 every test passed. 1 a test failed.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import session_log as sl  # noqa: E402
from test_scenario_check import base, by_id  # noqa: E402

SCRIPT = str(HERE / "session_log.py")


def log():
    """Five turns of play, ended by the player. Consistent with base()."""
    return [
        {"turn": 1, "clock": "09:00", "class": "investigate", "inject": "I1", "input": "look closely at the lock", "action": "A1", "rule": None,
         "changes": [{"reveal": "H1"}], "plan": {"step": "P1", "relation": "follows"}},
        {"turn": 2, "clock": "09:10", "class": "delegate", "inject": "I2", "input": "ask the assistant to ring the owner", "action": "A3", "to": "R1", "rule": None, "changes": []},
        {"turn": 2, "clock": "09:10", "class": "act", "input": "fit the padlock", "action": "A2", "rule": "RU1", "outcome": "then",
         "changes": [{"reveal": "H2"}, {"set": {"door": "closed"}}, {"spend": {"RES1": 1}}]},
        {"turn": 3, "clock": "09:20", "class": "wait", "input": "wait"},
        {"turn": 4, "clock": "09:30", "class": "command", "inject": "I3", "input": "hint", "hint": True, "text": "Think about what the owner would want written down."},
        {"turn": 4, "clock": "09:30", "class": "other", "input": "I tape a note to the door", "rule": "judgement call",
         "reason": "The rules do not cover notes. Ruling: it takes no time and changes nothing.", "costs_turn": False, "changes": []},
        {"turn": 5, "clock": "09:40", "class": "decide", "input": "write it up", "action": "A5", "rule": None, "changes": [], "plan": {"step": "P2", "relation": "follows"}},
        {"turn": 5, "clock": "09:40", "class": "command", "input": "end"},
    ]


def play(lines, scenario=None):
    engine = sl.Engine(scenario or base())
    for n, line in enumerate(lines, 1):
        engine.feed(n, line)
    return engine, [e["code"] for e in engine.errors]


class Validation(unittest.TestCase):
    def assert_clean(self, lines, scenario=None):
        engine, codes = play(lines, scenario)
        self.assertEqual(codes, [], engine.errors)
        return engine

    def assert_only(self, lines, code, scenario=None, count=1):
        engine, codes = play(lines, scenario)
        self.assertEqual(codes, [code] * count, engine.errors)
        return engine.errors

    def test_base_log_is_consistent(self):
        self.assert_clean(log())

    # ---- the planted failure and the three refusals the specification names ----
    def test_planted_hidden_fact_revealed_with_no_discovering_action(self):
        lines = log()
        lines[0]["changes"].append({"reveal": "H2"})            # looking at the lock does not show that nothing is missing
        errors = self.assert_only(lines, "reveal_without_cause")
        self.assertIn("FACILITATION ERROR", errors[0]["message"])
        self.assertIn("H2", errors[0]["message"])
        self.assertIn("line 1", errors[0]["message"])

    def test_a_hint_or_a_status_command_may_not_reveal_a_hidden_fact(self):
        lines = log()[:1] + [{"turn": 1, "clock": "09:00", "class": "command", "input": "hint", "hint": True, "text": "Nothing is missing, by the way.",
                              "changes": [{"reveal": "H2"}]}]
        self.assert_only(lines, "reveal_without_cause")
        lines = log()[:1] + [{"turn": 1, "clock": "09:00", "class": "command", "input": "status", "changes": [{"reveal": "H2"}]}]
        self.assert_only(lines, "reveal_without_cause")

    def test_the_same_fact_revealed_by_the_action_that_finds_it_is_accepted(self):
        engine = self.assert_clean(log())                       # valid neighbour of the planted failure
        self.assertEqual([(r["fact"], r["turn"], r["cause"]) for r in engine.reveal_log], [("H1", 1, "action A1"), ("H2", 2, "rule RU1 (then)")])

    def test_unknown_inject(self):
        lines = log()
        lines[4]["inject"] = "I99"
        codes = play(lines)[1]
        self.assertIn("reference", codes)
        self.assertIn("inject_missed", codes)                   # and I3, due on turn 4, was then never delivered

    def test_turns_out_of_order(self):
        lines = log()
        lines[3]["turn"], lines[3]["clock"] = 5, "09:40"          # turn 3 is skipped
        self.assertIn("turn_order", play(lines)[1])
        lines = log()
        lines[6]["turn"], lines[6]["clock"] = 3, "09:20"          # goes back from turn 4 to turn 3
        self.assertIn("turn_order", play(lines)[1])
        lines = log()[1:]                                        # starts at turn 2
        self.assertIn("turn_order", play(lines)[1])
        lines = log() + [{"turn": 5, "clock": "09:40", "class": "wait", "input": "wait"}]     # a line after end
        self.assertIn("turn_order", play(lines)[1])

    def test_a_turn_past_the_last_turn_is_refused(self):
        lines = log()[:-1]
        lines += [{"turn": 6, "clock": "09:50", "class": "wait", "input": "wait"}]            # valid neighbour: turn 6 of 6
        self.assert_clean(lines)
        lines += [{"turn": 7, "clock": "10:00", "class": "wait", "input": "wait"}]
        self.assert_only(lines, "turn_order")

    def test_state_change_with_no_cause(self):
        lines = log()
        lines[3]["changes"] = [{"set": {"alarm": True}}]         # waiting does not set the alarm
        errors = self.assert_only(lines, "change_without_cause")
        self.assertIn("set alarm=true", errors[0]["message"])
        lines = log()
        lines[6]["changes"] = [{"spend": {"RES1": 1}}]           # writing it up costs nothing
        self.assert_only(lines, "change_without_cause")

    # ---- rules ----
    def test_a_consequence_the_rules_require_cannot_be_left_out(self):
        lines = log()
        lines[2]["changes"] = [{"reveal": "H2"}, {"spend": {"RES1": 1}}]     # the door is not recorded as closed
        errors = self.assert_only(lines, "missing_consequence")
        self.assertIn("set door=closed", errors[0]["message"])

    def test_the_logged_rule_and_outcome_must_be_the_ones_the_scenario_gives(self):
        lines = log()
        lines[2]["outcome"] = "late"
        self.assert_only(lines, "rule_mismatch")
        lines = log()
        lines[2]["rule"], lines[2]["outcome"] = None, None
        self.assert_only(lines, "rule_mismatch")
        lines = log()
        lines[0]["rule"] = "RU1"                                 # A1 has no rule
        self.assert_only(lines, "rule_mismatch")

    def test_deadline_boundary_then_on_turn_three_late_on_turn_four(self):
        on_time = [log()[0],
                   {"turn": 2, "clock": "09:10", "class": "wait", "inject": "I2", "input": "wait"},
                   {"turn": 3, "clock": "09:20", "class": "act", "input": "fit the padlock", "action": "A2", "rule": "RU1", "outcome": "then",
                    "changes": [{"reveal": "H2"}, {"set": {"door": "closed"}}, {"spend": {"RES1": 1}}]}]
        self.assert_clean(on_time)
        late = [log()[0],
                {"turn": 2, "clock": "09:10", "class": "wait", "inject": "I2", "input": "wait"},
                {"turn": 3, "clock": "09:20", "class": "wait", "input": "wait"},
                {"turn": 4, "clock": "09:30", "class": "act", "inject": "I3", "input": "fit the padlock", "action": "A2", "rule": "RU1", "outcome": "late",
                 "changes": [{"set": {"door": "closed"}}, {"spend": {"RES1": 1}}]}]
        engine = self.assert_clean(late)
        self.assertNotIn("H2", engine.revealed)                  # the late outcome does not show the stock sheet
        late[3]["outcome"] = "then"
        late[3]["changes"].append({"reveal": "H2"})
        self.assertIn("rule_mismatch", play(late)[1])

    def test_unmet_outcome_and_bait(self):
        lines = log()[:3] + [{"turn": 3, "clock": "09:20", "class": "act", "input": "set the alarm and go", "action": "A4", "rule": "RU2", "outcome": "unmet", "changes": []}]
        self.assert_clean(lines)                                 # door closed: the alarm sets cleanly
        bait = [log()[0],
                {"turn": 2, "clock": "09:10", "class": "act", "inject": ["I2", "I4"], "input": "set the alarm and go", "action": "A4", "rule": "RU2", "outcome": "then",
                 "changes": [{"set": {"alarm": True}}, {"fire": "I4"}]}]
        engine = self.assert_clean(bait)                         # door open: it trips, and the fired inject arrives on the same line
        rows = {r["id"]: r for r in engine.tables()["injects"]}
        self.assertEqual(rows["I2"]["bait_taken_turn"], 2)
        self.assertEqual(rows["I2"]["status"], "missed")
        self.assertEqual(rows["I4"]["delivered_turn"], 2)

    def test_an_outcome_marked_not_done_does_not_count_as_doing_the_action(self):
        scenario = base()
        by_id(scenario, "rules", "RU2")["unmet"]["done"] = False       # "the alarm will not set": the attempt did not take effect
        by_id(scenario, "key_actions", "KA1")["action"] = "A4"
        attempt = {"turn": 3, "clock": "09:20", "class": "act", "input": "set the alarm and go", "action": "A4", "rule": "RU2", "outcome": "unmet", "changes": []}
        engine = self.assert_clean(log()[:3] + [attempt], scenario)
        self.assertNotIn("A4", engine.done)
        self.assertEqual(engine.tables()["key_actions"][0]["status"], "not done by turn 3")
        engine = self.assert_clean(log()[:3] + [attempt])        # valid neighbour: without the mark, the same line counts
        self.assertEqual(engine.done["A4"], 3)

    def test_where_the_rules_are_silent_the_line_must_be_a_labelled_judgement_call(self):
        scenario = base()
        del by_id(scenario, "rules", "RU2")["unmet"]             # now nothing is written for setting the alarm with the door closed
        silent = {"turn": 3, "clock": "09:20", "class": "act", "input": "set the alarm and go", "action": "A4", "rule": "RU2", "outcome": "unmet", "changes": []}
        self.assert_only(log()[:3] + [silent], "rule_mismatch", scenario)
        called = dict(silent, rule="judgement call", outcome=None, reason="Nothing is written for a closed door. Ruling: the alarm sets cleanly, because nothing is open.")
        engine = self.assert_clean(log()[:3] + [called], scenario)
        self.assertEqual(len(engine.judgements), 1)
        no_reason = dict(called, reason="ok")
        self.assert_only(log()[:3] + [no_reason], "rule_mismatch", scenario)

    def test_free_input_outside_the_action_list_is_always_a_judgement_call(self):
        lines = log()
        lines[5]["rule"] = None
        self.assert_only(lines, "rule_mismatch")
        lines = log()
        lines[5]["changes"] = [{"set": {"alarm": True}}]         # a judgement call may change state; it is recorded, not refused
        engine = self.assert_clean(lines)
        self.assertEqual(engine.judgements[0]["changes"], ["set alarm=true"])

    # ---- hidden-fact gating, budgets, roles, resources ----
    def test_an_action_that_depends_on_an_undiscovered_fact_is_a_facilitation_error(self):
        lines = [{"turn": 1, "clock": "09:00", "class": "act", "inject": "I1", "input": "fit the padlock", "action": "A2", "rule": "RU1", "outcome": "then",
                  "changes": [{"reveal": "H2"}, {"set": {"door": "closed"}}, {"spend": {"RES1": 1}}]}]
        errors = self.assert_only(lines, "needs_fact")
        self.assertIn("FACILITATION ERROR", errors[0]["message"])
        refused = [{"turn": 1, "clock": "09:00", "class": "act", "inject": "I1", "input": "fit the padlock", "action": "A2",
                    "refused": "You have not looked at the lock, so you do not know a padlock would hold."}]
        engine = self.assert_clean(refused)                      # valid neighbour: the facilitator refuses it
        self.assertNotIn("A2", engine.done)

    def test_two_turn_costing_actions_in_one_turn(self):
        lines = log()
        lines.insert(1, {"turn": 1, "clock": "09:00", "class": "wait", "input": "wait"})
        self.assert_only(lines, "turn_budget")
        lines = log()                                            # valid neighbour: a free action after the turn-costing one
        lines.insert(1, {"turn": 1, "clock": "09:00", "class": "decide", "input": "write it up", "action": "A5", "rule": None, "changes": []})
        self.assert_clean(lines)

    def test_delegation_rules(self):
        early = [dict(log()[0]), {"turn": 1, "clock": "09:00", "class": "delegate", "input": "ring the owner", "action": "A3", "to": "R1", "rule": None, "changes": []}]
        self.assert_only(early, "delegate")                      # the assistant arrives on turn 2
        lines = log()
        lines[1]["action"] = "A5"                                # writing up cannot be handed over
        self.assert_only(lines, "delegate")
        lines = log()
        lines.insert(2, dict(lines[1], inject=None))             # the same role twice in one turn
        self.assert_only(lines, "turn_budget")
        lines = log()
        lines[1]["to"] = "R9"
        self.assert_only(lines, "reference")

    def test_spending_more_than_is_left(self):
        again = {"turn": 3, "clock": "09:20", "class": "act", "input": "fit another padlock", "action": "A2", "rule": "RU1", "outcome": "then", "changes": [{"spend": {"RES1": 1}}]}
        self.assert_only(log()[:3] + [again], "resource")
        refused = {"turn": 3, "clock": "09:20", "class": "act", "input": "fit another padlock", "action": "A2", "refused": "There was one spare padlock and it is on the door."}
        self.assert_clean(log()[:3] + [refused])

    # ---- injects and the clock ----
    def test_inject_timing(self):
        lines = log()
        lines[1]["inject"], lines[3]["inject"] = None, "I2"      # I2 belongs to turn 2 and arrives on turn 3
        codes = play(lines)[1]
        self.assertEqual(sorted(codes), ["inject_missed", "inject_timing"])
        lines = log()
        lines[3]["inject"] = "I1"                                # delivered twice
        self.assert_only(lines, "inject_timing")
        lines = log()
        lines[3]["inject"] = "I4"                                # nothing fired it
        self.assert_only(lines, "inject_timing")

    def test_a_due_inject_that_is_never_delivered(self):
        lines = log()
        lines[4]["inject"] = None
        errors = self.assert_only(lines, "inject_missed")
        self.assertIn("I3", errors[0]["message"])

    def test_clock_must_match_the_turn(self):
        lines = log()
        lines[3]["clock"] = "09:25"
        self.assert_only(lines, "clock")
        lines = log()
        lines[3]["clock"] = "9:20"
        self.assert_only(lines, "clock")

    def test_clock_rule_must_be_logged_when_its_condition_holds(self):
        idle = [log()[0],
                {"turn": 2, "clock": "09:10", "class": "wait", "inject": "I2", "input": "wait"},
                {"turn": 3, "clock": "09:20", "class": "wait", "input": "wait"},
                {"turn": 4, "clock": "09:30", "class": "wait", "inject": "I3", "input": "wait"},
                {"turn": 5, "clock": "09:40", "class": "wait", "input": "wait"},
                {"turn": 5, "clock": "09:40", "class": "command", "input": "end"}]
        errors = self.assert_only(idle, "clock_rule")            # the door is still open at turn 5 and RU3 was not applied
        self.assertIn("RU3", errors[0]["message"])
        with_clock = idle[:4] + [{"turn": 5, "clock": "09:40", "class": "clock", "inject": "I5", "rule": "RU3", "outcome": "then", "changes": [{"fire": "I5"}]}] + idle[4:]
        self.assert_clean(with_clock)
        after = idle[:5] + [{"turn": 5, "clock": "09:40", "class": "clock", "inject": "I5", "rule": "RU3", "outcome": "then", "changes": [{"fire": "I5"}]}, idle[5]]
        self.assert_only(after, "clock_rule")                    # applied after the player had acted

    def test_clock_rule_applied_when_its_condition_does_not_hold(self):
        lines = log()
        lines.insert(6, {"turn": 5, "clock": "09:40", "class": "clock", "inject": "I5", "rule": "RU3", "outcome": "then", "changes": [{"fire": "I5"}]})
        errors = self.assert_only(lines, "clock_rule")           # the door was closed on turn 2
        self.assertIn("did not hold", errors[0]["message"])

    def test_a_log_without_end_is_valid_and_says_the_last_turn_was_not_checked(self):
        lines = log()[:4]
        engine = self.assert_clean(lines)
        text = sl.render(engine, engine.tables())
        self.assertIn("no end command, so the last turn was not checked", text)

    def test_shape_and_reference_errors(self):
        for field, bad in (("class", "attack"), ("turn", "1"), ("turn", True), ("changes", "none")):
            lines = log()
            lines[0][field] = bad
            self.assertIn("shape", play(lines)[1], (field, bad))
        lines = log()
        lines[0]["action"] = "A99"
        self.assertIn("reference", play(lines)[1])
        lines = log()
        lines[0]["plan"] = {"step": "P9", "relation": "follows"}
        self.assert_only(lines, "reference")
        lines = log()
        lines[0]["changes"] = [{"reveal": "H9"}]
        self.assertIn("reference", play(lines)[1])
        lines = log()
        lines[0]["colour"] = "red"
        self.assert_only(lines, "shape")

    def test_no_silent_coercion_in_state_conditions(self):
        scenario = base()
        scenario["state"]["alarm"] = 0                           # zero, not false
        by_id(scenario, "rules", "RU3")["when"]["state"] = {"alarm": False}
        idle = [log()[0],
                {"turn": 2, "clock": "09:10", "class": "wait", "inject": "I2", "input": "wait"},
                {"turn": 3, "clock": "09:20", "class": "wait", "input": "wait"},
                {"turn": 4, "clock": "09:30", "class": "wait", "inject": "I3", "input": "wait"},
                {"turn": 5, "clock": "09:40", "class": "wait", "input": "wait"},
                {"turn": 5, "clock": "09:40", "class": "command", "input": "end"}]
        self.assert_clean(idle, scenario)                        # 0 is not false, so the rule's condition does not hold


class Tables(unittest.TestCase):
    def test_tables_have_known_answers(self):
        engine, codes = play(log())
        self.assertEqual(codes, [])
        t = engine.tables()
        self.assertEqual((t["turns_played"], t["ended"]), (5, True))
        self.assertEqual([(r["turn"], r["who"], r["action"] or r["class"], r["adjudication"]) for r in t["timeline"]], [
            (1, "player", "A1", "no rule"), (2, "R1", "A3", "no rule"), (2, "player", "A2", "RU1 then"), (3, "player", "wait", "waited"),
            (4, "player", "command", "command"), (4, "player", "other", "judgement call"), (5, "player", "A5", "no rule"), (5, "player", "command", "command")])
        self.assertEqual(t["key_actions"][0]["status"], "1 turn(s) after the inject (10 scenario minutes): inject turn 1, action turn 2")
        self.assertEqual({r["id"]: r["status"] for r in t["injects"]}, {
            "I1": "handled (turn 1, 0 after)", "I2": "handled (turn 2, 0 after)", "I3": "no response expected",
            "I4": "not delivered (never fired)", "I5": "not delivered (never fired)"})
        self.assertTrue(all(r["bait_taken_turn"] is None for r in t["injects"]))
        o1, o2 = t["objectives"]
        self.assertEqual((o1["probing"], o1["delivered"], o1["expecting_a_response"], o1["handled"], o1["late"], o1["missed"]), (3, 2, 1, 1, 0, 0))
        self.assertEqual((o2["probing"], o2["delivered"], o2["expecting_a_response"], o2["handled"], o2["late"], o2["missed"]), (2, 1, 1, 1, 0, 0))
        self.assertEqual(t["hidden_not_found"], [])
        self.assertEqual([(h["turn"], h["text"]) for h in t["hints"]], [(4, "Think about what the owner would want written down.")])
        self.assertEqual(len(t["judgement_calls"]), 1)
        self.assertEqual(t["plan"]["counts"], {"follows": 2, "skips": 0, "contradicts": 0, "silent": 0})
        self.assertEqual((t["plan"]["marked_decisions"], t["plan"]["steps"], t["plan"]["steps_never_referenced"]), (2, 2, []))
        self.assertEqual(t["resources"], [{"id": "RES1", "start": 1, "spent": 1, "left": 0}])
        self.assertEqual(t["final_state"], {"door": "closed", "alarm": False})

    def test_late_and_missed_have_known_answers(self):
        lines = [{"turn": 1, "clock": "09:00", "class": "wait", "inject": "I1", "input": "wait"},
                 {"turn": 2, "clock": "09:10", "class": "wait", "inject": "I2", "input": "wait"},
                 {"turn": 3, "clock": "09:20", "class": "investigate", "input": "look at the lock", "action": "A1", "rule": None, "changes": [{"reveal": "H1"}]}]
        engine, codes = play(lines)
        self.assertEqual(codes, [])
        rows = {r["id"]: r["status"] for r in engine.tables()["injects"]}
        self.assertEqual(rows["I1"], "late (turn 3, 2 after; 1 allowed)")
        self.assertEqual(rows["I2"], "missed")
        self.assertEqual(rows["I3"], "not delivered (turn 4 was not reached)")
        self.assertEqual(engine.tables()["key_actions"][0]["status"], "not done by turn 3")
        self.assertEqual(engine.tables()["hidden_not_found"], ["H2"])

    def test_state_block_has_a_known_answer(self):
        engine, _ = play(log()[:3])
        self.assertEqual(engine.state_block(), "\n".join([
            "STATE v1 | scenario storeroom-door@1.0 | turn 2 of 6 | clock 09:10 | own action this turn: used",
            "known: K1 | revealed: H1 H2",
            "state: door=closed alarm=false",
            "done: A1@1 A2@2 A3@2",
            "injects: I1@1 I2@2 | pending: none",
            "tasks open: none | closed: Deal with the door (I1); Tell the owner (I2)",
            "resources: RES1=0",
            "hints: 0 | judgement calls: 0 | log lines: 3"]))

    def test_no_score_and_no_percentage_anywhere_in_the_output(self):
        engine, _ = play(log())
        text = sl.render(engine, engine.tables())
        self.assertNotIn("%", text)
        self.assertNotRegex(text.lower(), r"\bscored?\s*[:=]?\s*\d|\d\s*/\s*100\b|\bout of 100\b|\bgrade\b|\brating\b|\bpoints\b")
        self.assertIn("There is no score", text)


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.scenario = self.write("scenario.json", json.dumps(base()))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        p = self.dir / name
        p.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return str(p)

    def jsonl(self, name, lines):
        return self.write(name, "\n".join(json.dumps(x) for x in lines) + "\n")

    def call(self, *args):
        r = subprocess.run([sys.executable, "-B", SCRIPT] + list(args), capture_output=True, timeout=60)
        return r.returncode, r.stdout.decode("utf-8"), r.stderr.decode("utf-8")

    def test_exit_codes_and_output(self):
        code, out, _ = self.call(self.scenario, self.jsonl("ok.jsonl", log()))
        self.assertEqual(code, 0, out)
        self.assertIn("The log is consistent with the scenario: 8 line(s), 5 turn(s) played of 6.", out)
        self.assertIn("RESULT: PASS. 0 error(s).", out)
        out.encode("ascii")
        bad = log()
        bad[0]["changes"].append({"reveal": "H2"})
        code, out, _ = self.call(self.scenario, self.jsonl("bad.jsonl", bad))
        self.assertEqual(code, 1)
        self.assertIn("FACILITATION ERROR", out)
        self.assertIn("[reveal_without_cause]", out)
        self.assertIn("RESULT: FAIL. 1 error(s).", out)

    def test_state_and_json_options(self):
        path = self.jsonl("ok.jsonl", log())
        code, out, _ = self.call(self.scenario, path, "--state")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("STATE v1 | scenario storeroom-door@1.0 | turn 5 of 6 | clock 09:40 | own action this turn: free | ENDED"), out)
        code, out, _ = self.call(self.scenario, path, "--json")
        data = json.loads(out)
        self.assertEqual((data["result"], data["errors"]), ("PASS", []))
        self.assertEqual(data["tables"]["final_state"], {"door": "closed", "alarm": False})

    def test_bad_arguments_and_unreadable_input_exit_two(self):
        ok = self.jsonl("ok.jsonl", log())
        broken = base()
        broken["hidden_facts"].append({"id": "H3", "text": "The driver left a note under the till."})
        cases = [[self.scenario], [self.scenario, ok, "--bogus"], [self.scenario, ok, ok], [self.scenario, str(self.dir / "missing.jsonl")],
                 [self.write("broken.json", json.dumps(broken)), ok], [self.scenario, self.write("notjson.jsonl", '{"turn": 1,\n')],
                 [self.scenario, self.write("empty.jsonl", "\n\n")], [self.scenario, self.write("nul.jsonl", b'{"turn": 1}\x00\n')],
                 [self.scenario, self.write("nan.jsonl", '{"turn": NaN, "clock": "09:00", "class": "wait"}\n')]]
        for args in cases:
            code, out, err = self.call(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(len(err.strip().splitlines()), 1, err)
            self.assertNotIn("Traceback", err)
        code, out, err = self.call(self.scenario, self.write("notjson2.jsonl", json.dumps(log()[0]) + "\nnot json at all\n"))
        self.assertIn("line 2", err)

    def test_a_shipped_scenario_accepts_a_first_turn(self):
        scenario = str(HERE.parent / "assets" / "scenarios" / "outage-small-saas.json")
        first = [{"turn": 1, "clock": "21:40", "class": "act", "inject": "I1", "input": "1", "action": "A1", "rule": None, "changes": []},
                 {"turn": 1, "clock": "21:40", "class": "investigate", "input": "what is using the disk?", "action": "A2", "rule": None, "changes": [{"reveal": "H1"}]}]
        code, out, _ = self.call(scenario, self.jsonl("first.jsonl", first))
        self.assertEqual(code, 0, out)
        leak = [dict(first[0], changes=[{"reveal": "H2"}])]
        code, out, _ = self.call(scenario, self.jsonl("leak.jsonl", leak))
        self.assertEqual(code, 1)
        self.assertIn("hidden fact H2 was revealed on turn 1", out)


if __name__ == "__main__":
    unittest.main()
