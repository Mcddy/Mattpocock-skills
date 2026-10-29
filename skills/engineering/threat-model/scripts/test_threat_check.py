#!/usr/bin/env python3
"""Tests for threat_check.py. Standard library only. Every fixture is built here by hand.

Usage:
  python test_threat_check.py            run every test
  python test_threat_check.py -v         name each test as it runs
  python test_threat_check.py CheckRules.test_planted_boundary_flow_without_threats

How the tests are built: base() returns a small model that produces no error and no advisory.
Each test changes one thing and asserts the exact rule code that fires, and that nothing else
does. Each refusal is paired with its valid neighbour: the nearest input that must be accepted.

The two planted failures the skill's specification asks for:
  test_planted_mitigated_with_not_run_verification   a threat marked mitigated whose only
                                                     verification has never run
  test_planted_boundary_flow_without_threats         a flow across a trust boundary with no
                                                     threat entry at all
Exit codes: 0 every test passed. 1 a test failed.
"""
import copy
import datetime as dt
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
import threat_check as tc  # noqa: E402

TODAY = dt.date(2026, 10, 9)
SCRIPT = str(HERE / "threat_check.py")


def base():
    """A complete model with no errors and no advisories on 2026-10-09."""
    return {
        "system": "Test fixture: booking page", "schema": 1, "as_of": "2026-10-09",
        "assumptions": ["Served over HTTPS."], "out_of_scope": ["The hosting platform."],
        "assets": [
            {"id": "A1", "name": "customer records", "sensitivity": "high", "why": "Names and addresses of real people."},
            {"id": "A2", "name": "booking requests", "sensitivity": "medium", "why": "A wrong booking costs a wasted visit."},
        ],
        "actors": [
            {"id": "U1", "name": "signed-in user", "trust": "authenticated"},
            {"id": "U2", "name": "anonymous visitor", "trust": "anonymous"},
        ],
        "zones": [
            {"id": "Z1", "name": "Browser", "trust": "Controlled by the visitor."},
            {"id": "Z2", "name": "Server", "trust": "Controlled by the operator."},
        ],
        "elements": [
            {"id": "E1", "kind": "process", "name": "Booking page", "zone": "Z1"},
            {"id": "E2", "kind": "process", "name": "API server", "zone": "Z2"},
            {"id": "E3", "kind": "store", "name": "Customer database", "zone": "Z2", "holds": ["A1"]},
        ],
        "flows": [
            {"id": "F1", "from": "E1", "to": "E2", "data": ["A2"], "protocol": "HTTPS", "authenticated": True, "crosses": ["Z1", "Z2"]},
            {"id": "F2", "from": "E2", "to": "E1", "data": ["A2"], "protocol": "HTTPS", "authenticated": True, "crosses": ["Z2", "Z1"]},
            {"id": "F3", "from": "E2", "to": "E3", "data": ["A1"], "protocol": "SQL", "authenticated": True, "crosses": []},
        ],
        "threats": [
            {"id": "T1", "target": "F1", "category": "tampering", "actor": "U1", "asset": "A2",
             "scenario": "A signed-in user sends a booking for a slot that is already taken and the server stores it.",
             "impact": "Two people arrive for one slot.", "likelihood": "likely without a check", "status": "mitigated",
             "mitigations": ["M1"], "accepted_by": None, "accepted_why": None},
            {"id": "T2", "target": "F2", "category": "information_disclosure", "actor": "U2", "asset": "A2",
             "scenario": "An anonymous visitor requests the booking list and receives other people's booking requests.",
             "impact": "Other people's bookings are visible.", "likelihood": "unknown", "status": "open",
             "mitigations": [], "accepted_by": None, "accepted_why": None},
            {"id": "T3", "target": "E3", "category": "information_disclosure", "actor": "U1", "asset": "A1",
             "scenario": "A signed-in user with database access reads customer records kept as plain text.",
             "impact": "Customer records are readable by the administrator.", "likelihood": "unknown", "status": "accepted",
             "mitigations": [], "accepted_by": "the owner", "accepted_why": "One administrator, who is the owner."},
            {"id": "T4", "target": "F1", "category": "denial_of_service", "actor": "U2", "asset": "A2",
             "scenario": "An anonymous visitor floods the booking route so that real booking requests time out.",
             "impact": "Nobody can book while it lasts.", "likelihood": "unknown", "status": "transferred",
             "mitigations": [], "accepted_by": None, "accepted_why": "Handled by the hosting provider's rate limiting under its terms."},
            {"id": "T5", "target": "E3", "category": "tampering", "actor": "U1", "asset": "A1",
             "scenario": "A signed-in user edits another person's customer records by changing an id in the request.",
             "impact": "Customer records are altered by the wrong person.", "likelihood": "unknown", "status": "open",
             "mitigations": ["M2"], "accepted_by": None, "accepted_why": None},
            {"id": "T6", "target": "F2", "category": "tampering", "actor": "U2", "asset": "A2",
             "scenario": "An anonymous visitor replays an old confirmation so the booking page shows booking requests that were cancelled.",
             "impact": "A visitor believes a cancelled booking stands.", "likelihood": "unknown", "status": "open",
             "mitigations": ["M1"], "accepted_by": None, "accepted_why": None},
        ],
        "mitigations": [
            {"id": "M1", "what": "The slot is claimed in one atomic statement.", "where": "bookings.py claim_slot()", "verified_by": ["V1"]},
            {"id": "M2", "what": "Every record query filters by the owner's id.", "where": "records.py get_record()", "verified_by": ["V2"]},
        ],
        "verifications": [
            {"id": "V1", "kind": "automated_test", "how": "test_two_claims_one_slot in test_bookings.py", "last_result": "pass", "last_run": "2026-10-01"},
            {"id": "V2", "kind": "automated_test", "how": "test_other_users_record_is_404 in test_records.py", "last_result": "not_run", "last_run": None},
        ],
    }


def run(model, today=TODAY, stale=90):
    errors, advisories, summary, derived = tc.check(model, today, stale)
    return [e["code"] for e in errors], [a["code"] for a in advisories], summary, derived, errors


def by_id(model, group, ident):
    return next(x for x in model[group] if x["id"] == ident)


class CheckRules(unittest.TestCase):
    def assert_clean(self, model, **kw):
        codes, adv, _, _, errors = run(model, **kw)
        self.assertEqual(codes, [], errors)
        self.assertEqual(adv, [])

    def assert_only(self, model, code, count=1, **kw):
        codes, _, _, _, errors = run(model, **kw)
        self.assertEqual(codes, [code] * count, errors)
        return errors

    def test_base_model_is_clean(self):
        self.assert_clean(base())

    def test_summary_counts_have_known_answers(self):
        _, _, s, derived, _ = run(base())
        self.assertEqual(s["threats"], 6)
        self.assertEqual(s["threats_by_status"], {"open": 3, "mitigated": 1, "accepted": 1, "transferred": 1})
        self.assertEqual(s["threats_by_state"], {"mitigated_verified": 1, "open_partly_mitigated": 1, "open_built_unverified": 1,
                                                 "open_nothing_built": 1, "accepted": 1, "transferred": 1})
        self.assertEqual(s["mitigations_by_state"], {"verified": 1, "unverified": 1, "failing": 0, "not_built": 0})
        self.assertEqual(s["verifications_by_result"], {"pass": 1, "fail": 0, "not_run": 1})
        self.assertEqual((s["flows"], s["boundary_flows"]), (3, 2))
        self.assertEqual(s["likelihood_unknown"], 5)
        self.assertEqual(derived["threat_state"]["T5"], "open_built_unverified")
        self.assertEqual(derived["threat_state"]["T6"], "open_partly_mitigated")
        self.assertEqual(derived["boundary"], {"F1": True, "F2": True, "F3": False})

    # ---- shape: no silent coercion ----
    def test_schema_must_be_the_whole_number_one(self):
        for bad in (True, "1", 1.0, 2, None):
            m = base()
            m["schema"] = bad
            self.assert_only(m, "shape")

    def test_authenticated_must_be_a_boolean(self):
        for bad in (1, 0, "true", None):
            m = base()
            by_id(m, "flows", "F3")["authenticated"] = bad
            self.assert_only(m, "shape")
        m = base()
        by_id(m, "flows", "F3")["authenticated"] = False       # valid neighbour: a real false, on a flow inside one zone
        self.assert_clean(m)

    def test_values_outside_their_lists_are_refused(self):
        for group, ident, field in (("assets", "A2", "sensitivity"), ("actors", "U1", "trust"), ("elements", "E1", "kind"),
                                    ("threats", "T2", "category"), ("threats", "T2", "status"),
                                    ("verifications", "V2", "kind"), ("verifications", "V2", "last_result")):
            m = base()
            by_id(m, group, ident)[field] = "critical"
            self.assert_only(m, "shape")

    def test_a_missing_list_is_a_shape_error(self):
        m = base()
        del m["zones"]
        codes, _, _, derived, _ = run(m)
        self.assertIn("shape", codes)
        self.assertIsNone(derived)

    def test_the_file_must_hold_an_object(self):
        codes, _, _, derived, _ = run([base()])
        self.assertEqual(codes, ["shape"])
        self.assertIsNone(derived)

    # ---- ids and references ----
    def test_an_id_used_twice_is_refused_even_across_kinds(self):
        m = base()
        by_id(m, "elements", "E3")["id"] = "F3"                # an element and a flow share an id
        codes, _, _, _, _ = run(m)
        self.assertIn("duplicate_id", codes)

    def test_each_unknown_reference_is_named(self):
        cases = [
            ("elements", "E1", "zone", "Z9"), ("flows", "F3", "from", "E9"), ("flows", "F3", "to", "E9"),
            ("flows", "F3", "data", ["A9"]), ("flows", "F3", "crosses", ["Z9"]), ("threats", "T2", "target", "F9"),
            ("threats", "T2", "mitigations", ["M9"]), ("mitigations", "M2", "verified_by", ["V9"]),
            ("threats", "T2", "actor", "U9"), ("threats", "T2", "asset", "A9"), ("elements", "E3", "holds", ["A9"]),
        ]
        for group, ident, field, value in cases:
            m = base()
            by_id(m, group, ident)[field] = value
            codes, _, _, _, errors = run(m)
            self.assertIn("reference", codes, (group, ident, field))
            self.assertTrue(any(repr(value[0] if isinstance(value, list) else value) in e["message"] for e in errors), errors)

    def test_crosses_must_include_both_end_zones(self):
        m = base()
        by_id(m, "flows", "F1")["crosses"] = ["Z1"]            # runs Z1 to Z2 but declares only Z1
        self.assert_only(m, "shape")
        m = base()
        by_id(m, "flows", "F1")["crosses"] = ["Z2", "Z1"]      # valid neighbour: both ends, any order
        self.assert_clean(m)

    # ---- dates ----
    def test_dates_are_strict_calendar_dates(self):
        for bad in ("20261009", "2026-2-3", "2026-02-30", "09/10/2026", "2026-10-09T00:00:00", 20261009, None):
            m = base()
            m["as_of"] = bad
            self.assert_only(m, "date")
        m = base()
        m["as_of"] = "2026-02-28"                               # valid neighbour of 2026-02-30
        by_id(m, "verifications", "V1")["last_run"] = "2026-02-28"
        codes, _, _, _, errors = run(m, stale=400)
        self.assertEqual(codes, [], errors)

    def test_a_date_after_today_is_refused_and_today_is_accepted(self):
        m = base()
        by_id(m, "verifications", "V1")["last_run"] = "2026-10-10"
        self.assert_only(m, "date")
        m = base()
        by_id(m, "verifications", "V1")["last_run"] = "2026-10-09"
        self.assert_clean(m)
        m = base()
        m["as_of"] = "2026-10-10"
        self.assert_only(m, "date")

    def test_a_result_and_its_date_must_agree(self):
        m = base()
        by_id(m, "verifications", "V1")["last_run"] = None     # pass with no date
        codes, _, _, _, _ = run(m)
        self.assertIn("date", codes)
        m = base()
        by_id(m, "verifications", "V2")["last_run"] = "2026-10-01"   # not_run with a date
        self.assert_only(m, "date")

    # ---- the cross-file rules ----
    def test_planted_boundary_flow_without_threats(self):
        m = base()
        m["threats"] = [t for t in m["threats"] if t["target"] != "F2"]
        errors = self.assert_only(m, "boundary_flow_no_threat")
        self.assertIn("F2", errors[0]["message"])

    def test_a_threat_on_an_end_element_does_not_cover_the_flow(self):
        m = base()
        for t in m["threats"]:
            if t["target"] == "F2":
                t["target"] = "E1"
        self.assert_only(m, "boundary_flow_no_threat")

    def test_a_flow_inside_one_zone_needs_no_threat(self):
        m = base()                                              # valid neighbour: F3 stays in Z2 and has no threat
        self.assertFalse(any(t["target"] == "F3" for t in m["threats"]))
        self.assert_clean(m)

    def test_a_flow_between_same_zone_ends_that_passes_through_another_zone_is_a_boundary_flow(self):
        m = base()
        by_id(m, "flows", "F3")["crosses"] = ["Z2", "Z1"]
        self.assert_only(m, "boundary_flow_no_threat")

    def test_store_with_a_high_asset_needs_a_threat(self):
        m = base()
        m["threats"] = [t for t in m["threats"] if t["target"] != "E3"]
        errors = self.assert_only(m, "store_no_threat")
        self.assertIn("E3", errors[0]["message"])

    def test_store_rule_counts_assets_that_arrive_by_flow(self):
        m = base()
        m["threats"] = [t for t in m["threats"] if t["target"] != "E3"]
        del by_id(m, "elements", "E3")["holds"]                 # A1 still reaches E3 through F3
        self.assert_only(m, "store_no_threat")

    def test_store_with_only_a_medium_asset_needs_no_threat(self):
        m = base()
        m["threats"] = [t for t in m["threats"] if t["target"] != "E3"]
        m["mitigations"] = [x for x in m["mitigations"] if x["id"] != "M2"]     # M2 and V2 served only the removed threats
        m["verifications"] = [x for x in m["verifications"] if x["id"] != "V2"]
        by_id(m, "assets", "A1")["sensitivity"] = "medium"      # valid neighbour
        self.assert_clean(m)

    def test_mitigated_with_no_mitigation(self):
        m = base()
        by_id(m, "threats", "T1")["mitigations"] = []
        self.assert_only(m, "mitigated_no_mitigation")

    def test_planted_mitigated_with_not_run_verification(self):
        m = base()
        by_id(m, "threats", "T5")["status"] = "mitigated"       # M2's only verification, V2, is not_run
        errors = self.assert_only(m, "mitigated_unverified")
        self.assertIn("T5", errors[0]["message"])
        self.assertIn("V2", errors[0]["message"])

    def test_the_same_threat_left_open_is_reported_as_built_not_verified(self):
        m = base()                                              # valid neighbour of the planted failure
        codes, _, _, derived, _ = run(m)
        self.assertEqual(codes, [])
        self.assertEqual(derived["threat_state"]["T5"], "open_built_unverified")

    def test_mitigated_with_a_mitigation_that_has_no_verification(self):
        m = base()
        by_id(m, "mitigations", "M1")["verified_by"] = []
        errors = self.assert_only(m, "mitigated_unverified")
        self.assertIn("has no verification", errors[0]["message"])

    def test_mitigated_with_a_failing_verification(self):
        m = base()
        by_id(m, "verifications", "V1")["last_result"] = "fail"
        errors = self.assert_only(m, "mitigated_unverified")
        self.assertIn("failing", errors[0]["message"])

    def test_one_failing_verification_beside_a_passing_one_still_blocks_mitigated(self):
        m = base()
        m["verifications"].append({"id": "V3", "kind": "manual_check", "how": "Book the same slot from two phones at once.", "last_result": "fail", "last_run": "2026-10-02"})
        by_id(m, "mitigations", "M1")["verified_by"] = ["V1", "V3"]
        self.assert_only(m, "mitigated_unverified")

    def test_a_pass_beside_a_not_run_counts_as_verified(self):
        m = base()                                              # valid neighbour of the test above
        m["verifications"].append({"id": "V3", "kind": "manual_check", "how": "Book the same slot from two phones at once.", "last_result": "not_run", "last_run": None})
        by_id(m, "mitigations", "M1")["verified_by"] = ["V1", "V3"]
        self.assert_clean(m)

    def test_mitigated_with_a_mitigation_that_is_not_built(self):
        m = base()
        by_id(m, "mitigations", "M1")["built"] = False
        errors = self.assert_only(m, "mitigated_unverified")
        self.assertIn("not built", errors[0]["message"])

    def test_every_mitigation_of_a_mitigated_threat_must_be_verified(self):
        m = base()
        by_id(m, "threats", "T1")["mitigations"] = ["M1", "M2"]  # M1 verified, M2 not
        self.assert_only(m, "mitigated_unverified")

    def test_accepted_needs_both_who_and_why(self):
        for field in ("accepted_by", "accepted_why"):
            m = base()
            by_id(m, "threats", "T3")[field] = None
            self.assert_only(m, "accepted_incomplete")
            m = base()
            by_id(m, "threats", "T3")[field] = "  "
            self.assert_only(m, "accepted_incomplete")

    def test_scenario_length_boundary(self):
        m = base()
        by_id(m, "threats", "T2")["scenario"] = "Anonymous visitor reads booking requests of others."       # 7 words
        self.assert_only(m, "scenario")
        m = base()
        by_id(m, "threats", "T2")["scenario"] = "An anonymous visitor reads booking requests of others."    # 8 words
        self.assert_clean(m)

    def test_a_label_is_not_a_scenario(self):
        m = base()
        by_id(m, "threats", "T2")["scenario"] = "SQL injection"
        self.assert_only(m, "scenario")

    def test_scenario_must_name_an_actor_and_an_asset(self):
        m = base()
        t = by_id(m, "threats", "T2")
        del t["actor"], t["asset"]
        t["scenario"] = "Somebody asks for the whole list and receives things that belong to other people."
        self.assert_only(m, "scenario", count=2)
        m = base()
        t = by_id(m, "threats", "T2")
        del t["actor"], t["asset"]                              # valid neighbour: both named in the text itself
        t["scenario"] = "An anonymous visitor asks for the whole list and receives other people's booking requests."
        self.assert_clean(m)
        m = base()
        t = by_id(m, "threats", "T2")                           # valid neighbour: fields set, text names neither
        t["scenario"] = "Somebody asks for the whole list and receives things that belong to other people."
        self.assert_clean(m)

    # ---- advisories: reported, never an error ----
    def assert_advice(self, model, code, **kw):
        codes, adv, _, _, errors = run(model, **kw)
        self.assertEqual(codes, [], errors)
        self.assertEqual(adv, [code])

    def test_advisory_boundary_flow_not_authenticated(self):
        m = base()
        by_id(m, "flows", "F1")["authenticated"] = False
        self.assert_advice(m, "boundary_unauthenticated")

    def test_advisory_asset_in_no_flow_and_no_store(self):
        m = base()
        m["assets"].append({"id": "A3", "name": "payment card numbers", "sensitivity": "high", "why": "Fraud if copied."})
        self.assert_advice(m, "asset_unused")

    def test_advisory_categories_absent_on_a_high_value_flow(self):
        m = base()
        by_id(m, "flows", "F1")["data"] = ["A1"]                # high asset now crosses the boundary
        codes, adv, _, _, _ = run(m)
        self.assertEqual(codes, [])
        self.assertEqual(adv, ["categories_absent"])
        msg = tc.check(m, TODAY, 90)[1][0]["message"]
        for absent in ("spoofing", "repudiation", "information_disclosure", "elevation_of_privilege"):
            self.assertIn(absent, msg)
        self.assertNotIn("tampering,", msg)                     # T1 covers tampering on F1
        self.assertIn("Candidates only", msg)

    def test_advisory_stale_verification_boundary(self):
        m = base()
        m["as_of"] = "2026-07-11"
        by_id(m, "verifications", "V1")["last_run"] = "2026-07-11"   # exactly 90 days before 2026-10-09
        self.assert_clean(m)
        m = base()
        m["as_of"] = "2026-07-10"
        by_id(m, "verifications", "V1")["last_run"] = "2026-07-10"   # 91 days
        self.assert_advice(m, "stale_verification")
        self.assert_clean(m, stale=91)

    def test_advisory_as_of_older_than_a_verification(self):
        m = base()
        m["as_of"] = "2026-09-30"
        self.assert_advice(m, "as_of_behind")

    def test_advisory_low_likelihood_with_no_reason(self):
        m = base()
        by_id(m, "threats", "T2")["likelihood"] = "low"
        self.assert_advice(m, "low_without_reason")
        m = base()
        t = by_id(m, "threats", "T2")
        t["likelihood"], t["likelihood_why"] = "low", "The list route is not linked anywhere."
        self.assert_clean(m)
        m = base()
        t = by_id(m, "threats", "T2")
        t["likelihood"] = "low"
        t["scenario"] += " This requires knowing the route name."
        self.assert_clean(m)

    def test_unknown_likelihood_is_counted_and_never_flagged_as_low(self):
        _, adv, s, _, _ = run(base())
        self.assertEqual(adv, [])
        self.assertEqual(s["likelihood_unknown"], 5)

    def test_advisory_transfer_with_no_explanation(self):
        m = base()
        by_id(m, "threats", "T4")["accepted_why"] = None
        self.assert_advice(m, "transfer_unexplained")

    def test_advisory_unknown_key(self):
        m = base()
        by_id(m, "threats", "T2")["mitigation"] = ["M1"]        # a spelling slip for mitigations
        self.assert_advice(m, "unknown_key")

    def test_advisory_unused_mitigation_and_verification(self):
        m = base()
        m["mitigations"].append({"id": "M3", "what": "A daily copy of the database.", "where": "cron on the host", "verified_by": []})
        self.assert_advice(m, "mitigation_unused")
        m = base()
        m["verifications"].append({"id": "V3", "kind": "review", "how": "Read the query list for string joins.", "last_result": "not_run", "last_run": None})
        self.assert_advice(m, "verification_unused")


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

    def test_clean_file_exits_zero_and_errors_exit_one(self):
        code, out, _ = self.call(self.write("ok.json", base()), "--today", "2026-10-09")
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: PASS. 0 error(s), 0 advisory note(s).", out)
        self.assertIn("threats: 6   open 3 | mitigated 1 | accepted 1 | transferred 1", out)
        bad = base()
        by_id(bad, "threats", "T5")["status"] = "mitigated"
        code, out, _ = self.call(self.write("bad.json", bad), "--today", "2026-10-09")
        self.assertEqual(code, 1, out)
        self.assertIn("[mitigated_unverified]", out)
        self.assertIn("marked mitigated but not shown to work: 1 of 2", out)

    def test_advisories_alone_do_not_change_the_exit_code(self):
        m = base()
        by_id(m, "flows", "F1")["authenticated"] = False
        code, out, _ = self.call(self.write("adv.json", m), "--today", "2026-10-09")
        self.assertEqual(code, 0)
        self.assertIn("ADVISORY", out)

    def test_bad_arguments_exit_two_with_one_line_and_no_traceback(self):
        ok = self.write("ok.json", base())
        for args in (["--bogus", ok], [ok, "--today"], [ok, "--today", "20261009"], [ok, "--stale-days", "soon"],
                     [ok, "--stale-days", "0"], [], [ok, ok], [ok, "--json", "--stale-days"]):
            code, out, err = self.call(*args)
            self.assertEqual(code, 2, args)
            self.assertEqual(len(err.strip().splitlines()), 1, err)
            self.assertNotIn("Traceback", err)

    def test_unreadable_inputs_exit_two(self):
        cases = {
            "missing.json": None,
            "latin1.json": json.dumps(base()).encode("utf-8").replace(b"Browser", b"Br\xf6wser"),
            "nul.json": json.dumps(base()).encode("utf-8") + b"\x00",
            "nan.json": json.dumps(base()).encode("utf-8").replace(b'"schema": 1', b'"schema": NaN'),
            "dup.json": b'{"system": "a", "system": "b"}',
            "cut.json": json.dumps(base()).encode("utf-8")[:200],
            "empty.json": b"",
        }
        for name, data in cases.items():
            path = str(self.dir / name) if data is None else self.write(name, data)
            code, out, err = self.call(path)
            self.assertEqual(code, 2, name)
            self.assertNotIn("Traceback", err)
            self.assertTrue(err.startswith("threat_check: "), err)

    def test_a_byte_order_mark_is_accepted(self):
        code, out, _ = self.call(self.write("bom.json", b"\xef\xbb\xbf" + json.dumps(base()).encode("utf-8")), "--today", "2026-10-09")
        self.assertEqual(code, 0, out)

    def test_json_output_parses_and_carries_rule_codes(self):
        bad = base()
        bad["threats"] = [t for t in bad["threats"] if t["target"] != "F2"]
        code, out, _ = self.call(self.write("bad.json", bad), "--json", "--today", "2026-10-09")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["result"], "FAIL")
        self.assertEqual([e["code"] for e in data["errors"]], ["boundary_flow_no_threat"])

    def test_output_is_ascii_and_the_input_file_is_untouched(self):
        m = base()
        m["system"] = "Caf" + chr(0xe9) + " bookings " + chr(0x2014) + " test"
        path = self.write("uni.json", json.dumps(m, ensure_ascii=False).encode("utf-8"))
        before = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        r = subprocess.run([sys.executable, "-B", SCRIPT, path, "--today", "2026-10-09"], capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0)
        r.stdout.decode("ascii")                                # raises if any byte is not ASCII
        self.assertEqual(before, hashlib.sha256(Path(path).read_bytes()).hexdigest())

    def test_the_shipped_template_passes(self):
        code, out, _ = self.call(str(HERE.parent / "assets" / "threat-model-template.json"), "--today", "2026-10-09")
        self.assertEqual(code, 0, out)
        self.assertIn("verifications: 4   pass 0 | fail 0 | not_run 4", out)


if __name__ == "__main__":
    unittest.main()
