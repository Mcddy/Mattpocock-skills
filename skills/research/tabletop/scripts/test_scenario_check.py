#!/usr/bin/env python3
"""Tests for scenario_check.py. Standard library only. Every fixture is built here by hand.

Usage:
  python test_scenario_check.py            run every test
  python test_scenario_check.py -v         name each test as it runs
  python test_scenario_check.py Rules.test_planted_undiscoverable_hidden_fact

base() returns a small scenario (a storeroom door left open) that produces no error and no
advisory. Each test changes one thing and asserts the exact rule code that fires and that nothing
else does. Each refusal sits beside its valid neighbour: the nearest input that must be accepted.
test_session_log.py reuses base().

The planted failure the skill's specification asks for:
  test_planted_undiscoverable_hidden_fact   a hidden fact that no action can ever reveal
Exit codes: 0 every test passed. 1 a test failed.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenario_check as sc  # noqa: E402

SCRIPT = str(HERE / "scenario_check.py")
ASSETS = HERE.parent / "assets"


def base():
    """A complete scenario with no errors and no advisories. Six turns of ten minutes from 09:00."""
    return {
        "schema": 1, "id": "storeroom-door", "version": "1.0", "title": "Test fixture: the storeroom door",
        "type": "incident_response", "subject": "fictional",
        "system_under_test": "The closing-up checklist of an invented shop.",
        "setting": "An invented shop. The storeroom door has been found open at closing time and nobody knows since when.",
        "player_role": "the person closing up",
        "duration": {"turns": 6, "minutes_per_turn": 10, "start_clock": "09:00"},
        "objectives": [{"id": "O1", "text": "Is the door dealt with before the alarm company is called out?"},
                       {"id": "O2", "text": "Is the owner told something true, and in time?"}],
        "roles": [{"id": "R1", "name": "shop assistant", "can": "Phone the owner, or check a shelf.", "available_from_turn": 2}],
        "resources": [{"id": "RES1", "name": "spare padlock", "amount": 1, "unit": "padlock"}],
        "constraints": ["One thing of your own per turn."],
        "known_facts": [{"id": "K1", "text": "The storeroom door is open and its lock is hanging off."}],
        "hidden_facts": [{"id": "H1", "text": "The lock was forced from the inside, by a delivery driver who was shut in."},
                         {"id": "H2", "text": "Nothing is missing from the shelves."}],
        "state": {"door": "open", "alarm": False},
        "actions": [
            {"id": "A1", "label": "Look closely at the lock and the frame", "class": "investigate", "costs_turn": True, "reveals": ["H1"]},
            {"id": "A2", "label": "Fit the spare padlock and close the door", "class": "act", "costs_turn": True, "needs_fact": ["H1"], "cost": {"RES1": 1}},
            {"id": "A3", "label": "Tell the owner what is known so far", "class": "communicate", "costs_turn": False, "delegable_to": ["R1"]},
            {"id": "A4", "label": "Set the alarm and leave", "class": "act", "costs_turn": True},
            {"id": "A5", "label": "Write up what happened", "class": "decide", "costs_turn": False},
        ],
        "injects": [
            {"id": "I1", "turn": 1, "told": "The storeroom door is standing open.", "truth": "Accurate. It has been open for about an hour.",
             "misleading": False, "tone": "bad", "probes": ["O1"], "task": "Deal with the door", "expects": ["A1"], "within": 1},
            {"id": "I2", "turn": 2, "told": "The assistant says the alarm panel shows all clear, so you can just set it and go.",
             "truth": "The panel does not watch the storeroom door. Setting the alarm with the door open will trip it.",
             "misleading": True, "tone": "neutral", "probes": ["O2"], "task": "Tell the owner", "expects": ["A3"], "within": 1, "bait": ["A4"]},
            {"id": "I3", "turn": 4, "told": "The owner texts: thanks for staying.", "truth": "Accurate. The owner is not coming in.",
             "misleading": False, "tone": "good", "probes": ["O1"]},
            {"id": "I4", "turn": None, "told": "The alarm is sounding and the alarm company is on the phone.", "truth": "The open door tripped it.",
             "misleading": False, "tone": "bad", "probes": ["O2"]},
            {"id": "I5", "turn": None, "told": "A neighbour knocks: your storeroom door is open.", "truth": "Accurate.",
             "misleading": False, "tone": "bad", "probes": ["O1"]},
        ],
        "rules": [
            {"id": "RU1", "when": {"action": "A2", "by_turn": 3},
             "then": {"text": "The padlock goes on and the door is shut. A stock sheet on the back of the door shows every shelf ticked.", "reveals": ["H2"], "set": {"door": "closed"}},
             "late": {"text": "The padlock goes on and the door is shut, later than it should have been.", "set": {"door": "closed"}}},
            {"id": "RU2", "when": {"action": "A4", "state": {"door": "open"}},
             "then": {"text": "The alarm trips at once on the open door.", "set": {"alarm": True}, "fires": ["I4"]},
             "unmet": {"text": "The alarm sets cleanly and you leave."}},
            {"id": "RU3", "when": {"at_turn": 5, "state": {"door": "open"}},
             "then": {"text": "The door is still open as turn 5 begins and a neighbour notices.", "fires": ["I5"]}},
        ],
        "unknowable": ["How long the driver was shut in."],
        "key_actions": [{"id": "KA1", "label": "door secured", "action": "A2", "from_inject": "I1"}],
        "plan": [{"id": "P1", "text": "Check every door before setting the alarm."}, {"id": "P2", "text": "Write up anything unusual the same day."}],
    }


def run(d):
    errors, advisories, summary = sc.check(d)
    return [e["code"] for e in errors], [a["code"] for a in advisories], summary, errors


def by_id(d, group, ident):
    return next(x for x in d[group] if x["id"] == ident)


class Rules(unittest.TestCase):
    def assert_clean(self, d):
        codes, adv, _, errors = run(d)
        self.assertEqual(codes, [], errors)
        self.assertEqual(adv, [])

    def assert_only(self, d, code, count=1):
        codes, _, _, errors = run(d)
        self.assertEqual(codes, [code] * count, errors)
        return errors

    def assert_advice(self, d, code):
        codes, adv, _, errors = run(d)
        self.assertEqual(codes, [], errors)
        self.assertEqual(adv, [code])

    def test_base_scenario_is_clean(self):
        self.assert_clean(base())
        _, _, s, _ = run(base())
        self.assertEqual(s, {"objectives": 2, "injects": 5, "misleading_injects": 1, "actions": 5, "rules": 3, "hidden_facts": 2,
                             "unknowable": 1, "turns": 6, "plan_steps": 2})

    # ---- the errors the specification names ----
    def test_objective_that_no_inject_probes(self):
        d = base()
        d["objectives"].append({"id": "O3", "text": "Does anyone check the back gate as well?"})
        errors = self.assert_only(d, "objective_unprobed")
        self.assertIn("O3", errors[0]["message"])

    def test_inject_that_probes_no_objective(self):
        d = base()
        by_id(d, "injects", "I3")["probes"] = []
        self.assert_only(d, "inject_no_objective")
        d = base()
        del by_id(d, "injects", "I3")["probes"]
        self.assert_only(d, "inject_no_objective")

    def test_inject_with_no_really_true_entry(self):
        d = base()
        del by_id(d, "injects", "I3")["truth"]
        self.assert_only(d, "inject_no_truth")
        d = base()
        by_id(d, "injects", "I3")["truth"] = "   "
        self.assert_only(d, "inject_no_truth")

    def test_misleading_inject_whose_truth_repeats_what_is_told(self):
        d = base()
        i2 = by_id(d, "injects", "I2")
        i2["truth"] = i2["told"].upper()
        self.assert_only(d, "inject_no_truth")
        d = base()                                              # valid neighbour: the same repetition on an inject that is not misleading
        i3 = by_id(d, "injects", "I3")
        i3["truth"] = i3["told"]
        self.assert_clean(d)

    def test_rule_referring_to_an_unknown_action(self):
        d = base()
        by_id(d, "rules", "RU1")["when"]["action"] = "A99"
        errors = self.assert_only(d, "reference")
        self.assertIn("A99", errors[0]["message"])

    def test_rule_referring_to_an_unknown_inject(self):
        d = base()
        by_id(d, "rules", "RU2")["then"]["fires"] = ["I4", "I99"]
        errors = self.assert_only(d, "reference")
        self.assertIn("I99", errors[0]["message"])

    def test_other_unknown_references_are_named(self):
        cases = [("actions", "A1", "reveals", ["H9"]), ("actions", "A2", "needs_fact", ["H9"]), ("actions", "A3", "delegable_to", ["R9"]),
                 ("actions", "A2", "cost", {"RES9": 1}), ("injects", "I1", "expects", ["A9"]), ("injects", "I2", "bait", ["A9"]),
                 ("injects", "I3", "probes", ["O9"]), ("injects", "I3", "reveals", ["H9"]), ("injects", "I3", "set", {"window": "open"}),
                 ("key_actions", "KA1", "action", "A9"), ("key_actions", "KA1", "from_inject", "I9")]
        for group, ident, field, value in cases:
            d = base()
            by_id(d, group, ident)[field] = value
            codes, _, _, errors = run(d)
            self.assertIn("reference", codes, (group, ident, field, errors))
        d = base()
        by_id(d, "rules", "RU1")["then"]["set"] = {"window": "shut"}
        self.assert_only(d, "reference")
        d = base()
        by_id(d, "rules", "RU3")["when"]["state"] = {"window": "open"}
        self.assert_only(d, "reference")

    def test_planted_undiscoverable_hidden_fact(self):
        d = base()
        d["hidden_facts"].append({"id": "H3", "text": "The driver left a note under the till."})
        errors = self.assert_only(d, "hidden_undiscoverable")
        self.assertIn("H3", errors[0]["message"])

    def test_a_fact_only_an_inject_or_the_clock_reveals_is_still_undiscoverable(self):
        d = base()
        d["hidden_facts"].append({"id": "H3", "text": "The driver left a note under the till."})
        by_id(d, "injects", "I3")["reveals"] = ["H3"]            # time tells the player; no action can find it
        self.assert_only(d, "hidden_undiscoverable")
        d = base()
        d["hidden_facts"].append({"id": "H3", "text": "The driver left a note under the till."})
        by_id(d, "rules", "RU3")["then"]["reveals"] = ["H3"]
        self.assert_only(d, "hidden_undiscoverable")

    def test_a_fact_revealed_by_an_action_or_by_an_action_rule_is_discoverable(self):
        d = base()                                              # valid neighbours of the planted failure
        d["hidden_facts"].append({"id": "H3", "text": "The driver left a note under the till."})
        by_id(d, "actions", "A5")["reveals"] = ["H3"]
        self.assert_clean(d)
        d = base()
        d["hidden_facts"].append({"id": "H3", "text": "The driver left a note under the till."})
        by_id(d, "rules", "RU2")["unmet"]["reveals"] = ["H3"]
        self.assert_clean(d)

    def test_turns_out_of_order(self):
        d = base()
        by_id(d, "injects", "I1")["turn"] = 3                    # listed before I2, which is on turn 2
        self.assert_only(d, "turn_order")
        d = base()
        by_id(d, "injects", "I1")["turn"] = 0
        self.assert_only(d, "turn_order")
        d = base()
        by_id(d, "injects", "I1")["turn"] = 2                    # valid neighbour: two injects on one turn
        self.assert_clean(d)

    def test_duration_that_cannot_fit_the_injects(self):
        d = base()
        by_id(d, "injects", "I3")["turn"] = 7                    # the exercise has 6 turns
        errors = self.assert_only(d, "duration")
        self.assertIn("cannot fit", errors[0]["message"])
        d = base()
        by_id(d, "injects", "I3")["turn"] = 6                    # valid neighbour: the last turn
        self.assert_clean(d)

    def test_deadlines_clock_rules_and_roles_must_fit_too(self):
        d = base()
        by_id(d, "rules", "RU1")["when"]["by_turn"] = 7
        self.assert_only(d, "duration")
        d = base()
        by_id(d, "rules", "RU3")["when"]["at_turn"] = 7
        self.assert_only(d, "duration")
        d = base()
        by_id(d, "roles", "R1")["available_from_turn"] = 7
        self.assert_only(d, "duration")
        d = base()
        by_id(d, "rules", "RU3")["when"]["at_turn"] = 6          # valid neighbour
        self.assert_clean(d)

    # ---- the other errors ----
    def test_fired_inject_that_nothing_fires(self):
        d = base()
        by_id(d, "rules", "RU2")["then"]["fires"] = []
        errors = self.assert_only(d, "inject_unreachable")
        self.assertIn("I4", errors[0]["message"])

    def test_a_rule_may_not_fire_an_inject_that_has_a_fixed_turn(self):
        d = base()
        by_id(d, "rules", "RU2")["then"]["fires"] = ["I4", "I3"]
        self.assert_only(d, "reference")

    def test_two_rules_for_one_action_that_can_both_apply(self):
        d = base()
        d["rules"].append({"id": "RU4", "when": {"action": "A2"}, "then": {"text": "The padlock does not fit this hasp."}})
        self.assert_only(d, "rule_clash")
        d = base()
        d["rules"].append({"id": "RU4", "when": {"action": "A4", "state": {"door": "open"}}, "then": {"text": "Nothing happens at all."}})
        self.assert_only(d, "rule_clash")

    def test_two_rules_for_one_action_with_conditions_that_cannot_both_hold(self):
        d = base()                                              # valid neighbour
        d["rules"].append({"id": "RU4", "when": {"action": "A4", "state": {"door": "closed"}}, "then": {"text": "The alarm sets cleanly and you leave."}})
        del by_id(d, "rules", "RU2")["unmet"]
        self.assert_clean(d)

    def test_only_one_rule_for_an_action_may_carry_unmet(self):
        d = base()
        d["rules"].append({"id": "RU4", "when": {"action": "A4", "state": {"door": "closed"}}, "then": {"text": "The alarm sets cleanly and you leave."},
                           "unmet": {"text": "Something else happens here."}})
        self.assert_only(d, "rule_clash")

    def test_an_id_used_twice(self):
        d = base()
        by_id(d, "actions", "A5")["id"] = "I1"
        codes, _, _, _ = run(d)
        self.assertIn("duplicate_id", codes)

    def test_shape_no_silent_coercion(self):
        for field, bad in (("schema", True), ("schema", "1"), ("type", "wargame"), ("subject", None), ("subject", "a competitor"),
                           ("title", ""), ("setting", "short")):
            d = base()
            d[field] = bad
            self.assert_only(d, "shape")
        for key, bad in (("turns", "6"), ("turns", True), ("turns", 0), ("minutes_per_turn", 2.5), ("start_clock", "9:00"), ("start_clock", "24:00"), ("start_clock", "09.00")):
            d = base()
            d["duration"][key] = bad
            self.assert_only(d, "shape")
        d = base()
        d["duration"]["start_clock"] = "23:59"                   # valid neighbour of 24:00
        self.assert_clean(d)
        for field, bad in (("costs_turn", "yes"), ("class", "attack")):
            d = base()
            by_id(d, "actions", "A1")[field] = bad
            self.assert_only(d, "shape")
        for field, bad in (("misleading", 0), ("tone", "awful")):
            d = base()
            by_id(d, "injects", "I1")[field] = bad
            self.assert_only(d, "shape")

    def test_outcomes_that_cannot_apply_are_refused(self):
        d = base()
        by_id(d, "rules", "RU2")["late"] = {"text": "Too late to matter."}       # late with no by_turn
        self.assert_only(d, "shape")
        d = base()
        by_id(d, "rules", "RU1")["unmet"] = {"text": "Not possible yet."}        # unmet with nothing to be unmet
        self.assert_only(d, "shape")
        d = base()
        by_id(d, "rules", "RU3")["when"]["action"] = "A1"                        # a clock rule that also names an action
        self.assert_only(d, "shape")
        d = base()
        d["rules"].append({"id": "RU4", "when": {"action": "A5"}})                # a rule with no then
        self.assert_only(d, "shape")
        d = base()
        by_id(d, "rules", "RU2")["unmet"]["done"] = "no"                         # done must be true or false
        self.assert_only(d, "shape")
        d = base()
        by_id(d, "rules", "RU2")["unmet"]["done"] = False                        # valid neighbour
        self.assert_clean(d)

    # ---- advisories ----
    def test_advisory_every_inject_is_bad_news(self):
        d = base()
        for i in d["injects"]:
            i["tone"] = "bad"
        self.assert_advice(d, "all_bad_news")

    def test_advisory_nothing_misleading(self):
        d = base()
        by_id(d, "injects", "I2")["misleading"] = False
        self.assert_advice(d, "nothing_misleading")

    def test_advisory_more_than_twelve_turns(self):
        d = base()
        d["duration"]["turns"] = 13
        self.assert_advice(d, "long_first_run")
        d = base()
        d["duration"]["turns"] = 12                              # valid neighbour
        self.assert_clean(d)

    def test_advisory_objective_count(self):
        d = base()
        d["objectives"] = d["objectives"][:1]
        by_id(d, "injects", "I2")["probes"] = ["O1"]
        by_id(d, "injects", "I4")["probes"] = ["O1"]
        self.assert_advice(d, "objective_count")
        d = base()
        for n in (3, 4, 5):
            d["objectives"].append({"id": "O%d" % n, "text": "An extra objective for the count test."})
            by_id(d, "injects", "I3")["probes"].append("O%d" % n)
        self.assert_advice(d, "objective_count")                 # five
        d["objectives"].pop()
        by_id(d, "injects", "I3")["probes"].pop()
        self.assert_clean(d)                                     # valid neighbour: four

    def test_advisory_no_plan_and_no_key_actions(self):
        d = base()
        d["plan"] = []
        self.assert_advice(d, "no_plan")
        d = base()
        del d["key_actions"]
        self.assert_advice(d, "no_key_actions")

    def test_advisory_deadline_with_no_late_outcome(self):
        d = base()
        del by_id(d, "rules", "RU1")["late"]
        self.assert_advice(d, "deadline_no_late")

    def test_advisory_cost_spent_on_an_attempt_that_does_not_take_effect(self):
        d = base()
        ru1 = by_id(d, "rules", "RU1")                           # RU1 is about A2, which costs the spare padlock
        ru1["late"]["done"] = False
        self.assert_advice(d, "cost_on_failed_attempt")
        ru1["late"]["done"] = True                               # valid neighbour: the attempt takes effect
        self.assert_clean(d)
        ru1["late"]["done"] = False
        del by_id(d, "actions", "A2")["cost"]                    # valid neighbour: nothing to spend
        self.assert_clean(d)

    def test_advisory_response_window_past_the_last_turn(self):
        d = base()
        i3 = by_id(d, "injects", "I3")
        i3["turn"], i3["expects"], i3["within"] = 6, ["A5"], 1
        self.assert_advice(d, "window_past_end")
        i3["within"] = 0                                         # valid neighbour
        self.assert_clean(d)

    def test_advisory_unknown_top_level_key(self):
        d = base()
        d["objective"] = []
        self.assert_advice(d, "unknown_key")


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        p = self.dir / name
        p.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode("utf-8"))
        return str(p)

    def call(self, *args):
        r = subprocess.run([sys.executable, "-B", SCRIPT] + list(args), capture_output=True, timeout=60)
        return r.returncode, r.stdout.decode("utf-8"), r.stderr.decode("utf-8")

    def test_exit_codes(self):
        code, out, _ = self.call(self.write("ok.json", base()))
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: PASS. 0 error(s), 0 advisory note(s).", out)
        bad = base()
        bad["hidden_facts"].append({"id": "H3", "text": "The driver left a note under the till."})
        code, out, _ = self.call(self.write("bad.json", bad))
        self.assertEqual(code, 1)
        self.assertIn("[hidden_undiscoverable]", out)
        adv = base()
        adv["plan"] = []
        code, out, _ = self.call(self.write("adv.json", adv))
        self.assertEqual(code, 0)
        self.assertIn("ADVISORY", out)

    def test_bad_arguments_and_unreadable_input_exit_two(self):
        ok = self.write("ok.json", base())
        raw = json.dumps(base()).encode("utf-8")
        cases = [["--bogus", ok], [], [ok, ok], [str(self.dir / "missing.json")],
                 [self.write("latin1.json", raw.replace(b"storeroom", b"st\xf6reroom"))], [self.write("nul.json", raw + b"\x00")],
                 [self.write("nan.json", raw.replace(b'"schema": 1', b'"schema": NaN'))], [self.write("dup.json", b'{"id": "a", "id": "b"}')],
                 [self.write("cut.json", raw[:300])], [self.write("empty.json", b"")]]
        for args in cases:
            code, out, err = self.call(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(len(err.strip().splitlines()), 1, err)
            self.assertNotIn("Traceback", err)

    def test_bom_json_output_ascii_and_untouched_input(self):
        d = base()
        d["title"] = "Caf" + chr(0xe9) + " storeroom " + chr(0x2014) + " test"
        path = self.write("uni.json", b"\xef\xbb\xbf" + json.dumps(d, ensure_ascii=False).encode("utf-8"))
        before = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        r = subprocess.run([sys.executable, "-B", SCRIPT, path], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout)
        r.stdout.decode("ascii")
        code, out, _ = self.call(path, "--json")
        self.assertEqual(json.loads(out)["result"], "PASS")
        self.assertEqual(before, hashlib.sha256(Path(path).read_bytes()).hexdigest())

    def test_every_shipped_scenario_and_the_template_pass(self):
        files = sorted((ASSETS / "scenarios").glob("*.json")) + [ASSETS / "scenario-template.json"]
        self.assertEqual(len(files), 4, files)
        for f in files:
            code, out, err = self.call(str(f))
            self.assertEqual(code, 0, "%s\n%s%s" % (f.name, out, err))
            self.assertIn("0 error(s)", out)


if __name__ == "__main__":
    unittest.main()
