#!/usr/bin/env python3
"""Tests for assets/scenarios/verify_subnet_drill.py. Standard library only.

Usage:
  python test_verify_subnet_drill.py [-v]

The verifier is shown to pass on the shipped drill and to fail on planted wrong facts: a claim with
the wrong answer, a prefix length changed in one place only, an address in the story that no claim
covers, and a host placed outside its VLAN. Fixtures are copies of the shipped drill, changed in
memory and written to a temporary folder.

Exit codes: 0 every test passed. 1 a test failed.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SCENARIOS = HERE.parent / "assets" / "scenarios"
SCRIPT = str(SCENARIOS / "verify_subnet_drill.py")
sys.path.insert(0, str(SCENARIOS))
import verify_subnet_drill as v  # noqa: E402


def drill():
    return json.loads((SCENARIOS / "subnet-fault-drill.json").read_bytes().decode("utf-8"))


def claim(d, ident):
    return next(c for c in d["addressing"]["claims"] if c["id"] == ident)


class Verifier(unittest.TestCase):
    def test_the_shipped_drill_holds(self):
        results, problems = v.verify(drill())
        self.assertEqual(problems, [])
        self.assertEqual(len(results), 20)
        self.assertTrue(all(r["ok"] for r in results))

    def test_the_key_facts_have_the_answers_worked_by_hand(self):
        got = {r["id"]: r["computed"] for r in v.verify(drill())[0]}
        self.assertEqual(got["C1"], "255.255.0.0")
        self.assertEqual(got["C3"], "172.16.0.0/16")
        self.assertIs(got["C5"], True)                           # 172.16.20.57 is inside 172.16.0.0/16
        self.assertIs(got["C6"], False)                          # 172.17.30.44 is not
        self.assertIs(got["C9"], False)                          # and with /24, 172.16.20.57 is outside 172.16.10.0/24
        self.assertEqual((got["C19"], got["C20"]), (254, 65534))

    def test_planted_wrong_answer_is_caught(self):
        d = drill()
        claim(d, "C6")["expect"] = True                          # claims the guest PC is on-link for the server
        results, _ = v.verify(d)
        self.assertEqual([r["id"] for r in results if not r["ok"]], ["C6"])

    def test_planted_prefix_slip_is_caught(self):
        d = drill()
        claim(d, "C5")["interface"] = "172.16.10.25/24"          # the story's fault no longer produces its symptom
        results, _ = v.verify(d)
        self.assertEqual([r["id"] for r in results if not r["ok"]], ["C5"])

    def test_true_is_not_one_and_text_is_not_a_number(self):
        d = drill()
        claim(d, "C19")["expect"] = "254"
        self.assertEqual([r["id"] for r in v.verify(d)[0] if not r["ok"]], ["C19"])
        d = drill()
        claim(d, "C5")["expect"] = 1
        self.assertEqual([r["id"] for r in v.verify(d)[0] if not r["ok"]], ["C5"])

    def test_an_address_in_the_story_that_no_claim_covers_is_caught(self):
        d = drill()
        d["known_facts"][1]["text"] += " A printer sits at 172.16.20.99."
        _, problems = v.verify(d)
        self.assertEqual(problems, ["the text mentions 172.16.20.99, which the addressing block does not list"])

    def test_a_host_outside_its_vlan_is_caught(self):
        d = drill()
        d["addressing"]["hosts"]["staff PC"] = "172.18.20.57"
        _, problems = v.verify(d)
        self.assertTrue(any("staff PC" in p and "exactly one" in p for p in problems), problems)

    def test_an_invalid_address_is_reported_not_crashed_on(self):
        d = drill()
        claim(d, "C5")["address"] = "172.16.20.300"
        results, _ = v.verify(d)
        bad = [r for r in results if not r["ok"]]
        self.assertEqual([r["id"] for r in bad], ["C5"])
        self.assertIn("could not be worked out", bad[0]["problem"])

    def test_command_line(self):
        r = subprocess.run([sys.executable, "-B", SCRIPT], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(b"RESULT: PASS. 20 of 20 claim(s) hold; 0 other problem(s).", r.stdout)
        with tempfile.TemporaryDirectory() as t:
            d = copy.deepcopy(drill())
            claim(d, "C6")["expect"] = True
            p = Path(t) / "planted.json"
            p.write_bytes(json.dumps(d).encode("utf-8"))
            r = subprocess.run([sys.executable, "-B", SCRIPT, str(p)], capture_output=True, timeout=60)
            self.assertEqual(r.returncode, 1)
            self.assertIn(b"FAIL C6", r.stdout)
            for args in (["--bogus"], [str(p), str(p)], [str(Path(t) / "missing.json")]):
                r = subprocess.run([sys.executable, "-B", SCRIPT] + args, capture_output=True, timeout=60)
                self.assertEqual(r.returncode, 2, args)
                self.assertNotIn(b"Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
