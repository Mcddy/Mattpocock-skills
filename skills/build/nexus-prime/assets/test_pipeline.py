#!/usr/bin/env python3
"""Tests for pipeline_skeleton.py. Standard library only.

Run from the folder that holds both files:  python test_pipeline.py
From the skill folder:                      python assets/test_pipeline.py

The last three classes hold the cases an independent reviewer reproduced against revision 2.0.0
(an unusable feed recorded as healthy, a lone surrogate in a reply ending the cycle, a dry run
using up an item), each with its valid neighbour.
"""
import contextlib
import datetime as dt
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import pipeline_skeleton as p

GOOD = {"item_id": "t1", "category": "outage", "urgency": 5, "summary": "Checkout is returning errors"}


def reply(**changes):
    d = dict(GOOD)
    d.update(changes)
    return json.dumps(d)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.state = p.State(os.path.join(self.dir.name, "state.db"))
        self.stop = os.path.join(self.dir.name, "STOP")
        self.sent = []

    def tearDown(self):
        self.state.db.close()
        self.dir.cleanup()

    def fresh(self):
        """Throw the state away and start again, inside one test."""
        self.tearDown()
        self.setUp()

    def cycle(self, replies, live=True, now=1000.0, items=None, sender=None):
        items = items if items is not None else [{"id": "t%d" % (i + 1), "text": "x"} for i in range(len(replies))]
        table = {it["id"]: r for it, r in zip(items, replies)}

        def model(item):
            r = table[item["id"]]
            if isinstance(r, Exception):
                raise r
            return r
        return p.run_cycle(self.state, live, self.stop, now=now, fetch=lambda: items, model=model,
                           sender=sender or self.sent.append)


class ModelOutputIsValidatedBeforeAnything(Base):
    def test_good_reply_alerts(self):
        c = self.cycle([reply()])
        self.assertEqual((c["alerts"], c["rejected"]), (1, 0))
        self.assertEqual(len(self.sent), 1)

    def test_rejections_send_nothing(self):
        bad = {
            "not json": "The ticket looks urgent to me.",
            "json with prose around it": "Here you go: " + reply(),
            "a list": "[1, 2]",
            "missing key": json.dumps({k: v for k, v in GOOD.items() if k != "urgency"}),
            "text where a number belongs": reply(urgency="5"),
            "true where a number belongs": reply(urgency=True),
            "a fraction": reply(urgency=4.5),
            "out of range": reply(urgency=9),
            "unknown category": reply(category="page_the_ceo"),
            "unknown extra field": reply(recipient="someone@example.org"),
            "over-long summary": reply(summary="x" * 281),
            "empty summary": reply(summary="   "),
            "NaN": '{"item_id": "t1", "category": "outage", "urgency": NaN, "summary": "x"}',
            "unterminated fence": "```json\n" + reply(),
            "not text": None,
        }
        for name, r in bad.items():
            with self.subTest(name):
                self.fresh()
                c = self.cycle([r])
                self.assertEqual((c["alerts"], c["rejected"]), (0, 1), name)
                self.assertEqual(self.sent, [], name)

    def test_fenced_json_is_accepted(self):
        c = self.cycle(["```json\n" + reply() + "\n```"])
        self.assertEqual(c["alerts"], 1)

    def test_valid_neighbours(self):
        self.assertEqual(self.cycle([reply(urgency=4)])["alerts"], 1)                  # the threshold itself
        self.fresh()
        self.assertEqual(self.cycle([reply(summary="x" * 280)])["alerts"], 1)          # the longest allowed
        self.fresh()
        c = self.cycle([reply(urgency=3)])                                             # just under: valid, no alert
        self.assertEqual((c["alerts"], c["ignored"], c["rejected"]), (0, 1, 0))
        self.fresh()
        c = self.cycle([reply(category="billing")])                                    # valid category outside the alert set
        self.assertEqual((c["alerts"], c["ignored"]), (0, 1))

    def test_reply_about_another_item_is_not_acted_on(self):
        c = self.cycle([reply(item_id="something-else")])
        self.assertEqual((c["alerts"], c["ignored"]), (0, 1))

    def test_text_is_escaped(self):
        self.cycle([reply(summary="<b>urgent</b> & <a href='http://x'>click</a>")])
        self.assertNotIn("<b>", self.sent[0])
        self.assertIn("&lt;b&gt;", self.sent[0])


class Controls(Base):
    def test_dry_run_sends_nothing(self):
        c = self.cycle([reply()], live=False)
        self.assertEqual(c["alerts"], 1)
        self.assertEqual(self.sent, [])

    def test_stop_file_halts_everything(self):
        open(self.stop, "w").close()
        c = self.cycle([reply()])
        self.assertEqual((c["status"], c["items"]), ("stopped", 0))
        self.assertEqual(self.sent, [])

    def test_hourly_cap(self):
        n = p.MAX_ALERTS_PER_HOUR + 3
        replies = [reply(item_id="t%d" % (i + 1), summary="distinct problem %d" % i) for i in range(n)]
        c = self.cycle(replies)
        self.assertEqual((c["alerts"], c["suppressed"]), (p.MAX_ALERTS_PER_HOUR, 3))
        self.assertEqual(len(self.sent), p.MAX_ALERTS_PER_HOUR)

    def test_duplicate_alert_is_suppressed_then_allowed_after_the_window(self):
        items = [{"id": "a", "text": "x"}]
        self.cycle([reply(item_id="a")], items=items)
        items = [{"id": "b", "text": "x"}]
        same = json.dumps(dict(GOOD, item_id="b"))
        # same category, urgency and summary but a new item id gives a different message, so it is sent
        self.assertEqual(self.cycle([same], items=items, now=1100.0)["alerts"], 1)
        # an item already handled is not processed twice
        self.assertEqual(self.cycle([same], items=items, now=1200.0)["items"], 0)

    def test_identical_message_within_window(self):
        msg = p.format_alert(GOOD)
        import hashlib
        self.state.record_alert(hashlib.sha256(msg.encode()).hexdigest(), 990.0, False)
        c = self.cycle([reply()])
        self.assertEqual((c["alerts"], c["suppressed"]), (0, 1))

    def test_one_bad_item_does_not_stop_the_rest(self):
        c = self.cycle([RuntimeError("model timed out"), reply(item_id="t2")])
        self.assertEqual((c["errors"], c["alerts"], c["status"]), (1, 1, "ok"))

    def test_failed_item_is_retried_next_cycle(self):
        items = [{"id": "t1", "text": "x"}]
        self.cycle([RuntimeError("boom")], items=items)
        c = self.cycle([reply()], items=items, now=2000.0)
        self.assertEqual(c["alerts"], 1)

    def test_failed_send_is_not_recorded_as_sent(self):
        def broken(_):
            raise ConnectionError("channel down")
        items = [{"id": "t1", "text": "x"}]
        c = self.cycle([reply()], items=items, sender=broken)
        self.assertEqual((c["alerts"], c["errors"]), (0, 1))
        c = self.cycle([reply()], items=items, now=2000.0)
        self.assertEqual(c["alerts"], 1)

    def test_breaker_trips_after_repeated_failures_and_stays_tripped(self):
        def boom():
            raise ConnectionError("source down")
        for i in range(p.MAX_FAILURES):
            c = p.run_cycle(self.state, True, self.stop, now=1000.0 + i, fetch=boom, model=None, sender=self.sent.append)
        self.assertEqual(c["status"], "tripped")
        self.assertEqual(len(self.sent), 1)                       # one notice, not one per cycle
        c = self.cycle([reply()], now=5000.0)
        self.assertEqual((c["status"], c["alerts"]), ("tripped", 0))
        self.state.put("breaker", "")
        self.state.put("failures", 0)
        self.assertEqual(self.cycle([reply()], now=6000.0)["alerts"], 1)

    def test_a_success_resets_the_failure_count(self):
        def boom():
            raise ConnectionError("source down")
        for i in range(p.MAX_FAILURES - 1):
            p.run_cycle(self.state, True, self.stop, now=1000.0 + i, fetch=boom, model=None, sender=self.sent.append)
        self.cycle([reply()], now=2000.0)
        c = p.run_cycle(self.state, True, self.stop, now=3000.0, fetch=boom, model=None, sender=self.sent.append)
        self.assertEqual(c["status"], "failed")


class Health(Base):
    def test_no_cycle_yet(self):
        self.assertFalse(p.health(self.state, 900, now=1000.0, stop_file=self.stop)[0])

    def test_fresh_then_stale(self):
        self.cycle([reply()], now=1000.0)
        self.assertTrue(p.health(self.state, 900, now=1500.0, stop_file=self.stop)[0])
        self.assertFalse(p.health(self.state, 900, now=2000.0, stop_file=self.stop)[0])

    def test_a_gap_of_a_day_and_ten_minutes_is_stale(self):
        self.cycle([reply()], now=1000.0)
        gap = dt.timedelta(days=1, minutes=10)
        self.assertEqual(gap.seconds, 600)                         # the trap: .seconds drops whole days
        self.assertEqual(gap.total_seconds(), 87000.0)
        ok, msg = p.health(self.state, 7200, now=1000.0 + gap.total_seconds(), stop_file=self.stop)
        self.assertFalse(ok)
        self.assertIn("stale", msg)

    def test_stopped_and_tripped_are_unhealthy(self):
        self.cycle([reply()], now=1000.0)
        open(self.stop, "w").close()
        self.assertFalse(p.health(self.state, 900, now=1001.0, stop_file=self.stop)[0])
        os.remove(self.stop)
        self.state.put("breaker", "tripped")
        self.assertFalse(p.health(self.state, 900, now=1001.0, stop_file=self.stop)[0])


class CommandLine(unittest.TestCase):
    def test_bad_arguments(self):
        for argv in (["--loop", "--once"], ["--wat"], ["--once", "--interval", "0"], ["--once", "--interval"], [], ["--health", "--max-age", "soon"]):
            with self.subTest(argv):
                self.assertEqual(p.main(argv), 2)

    def test_health_reads_the_record_for_the_mode_asked_and_reset_clears_both(self):
        with tempfile.TemporaryDirectory() as d:
            db, stop = os.path.join(d, "s.db"), os.path.join(d, "STOP")
            base = ["--state", db, "--stop-file", stop]

            def call(*argv):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    code = p.main(list(argv) + base)
                return code, out.getvalue()
            self.assertEqual(call("--once")[0], 0)                               # a dry cycle on the empty default feed
            code, out = call("--health")
            self.assertEqual(code, 0)
            self.assertIn("dry-run cycle", out)
            code, out = call("--health", "--live")
            self.assertEqual(code, 1)                                            # no live cycle has run
            self.assertIn("no successful live cycle", out)
            s = p.State(db)
            s.put(s.key("breaker", True), "tripped")
            s.put(s.key("breaker", False), "tripped")
            s.db.close()
            self.assertEqual(call("--health")[0], 1)
            self.assertEqual(call("--reset")[0], 0)
            self.assertEqual(call("--health")[0], 0)
            s = p.State(db)
            self.assertEqual((s.get("breaker"), s.get("dry:breaker")), ("", ""))
            s.db.close()


class UnusableFeed(Base):
    """A feed that is not empty but has nothing usable in it is a failure, not a quiet cycle."""

    def bad_cycle(self, feed, now, live=True):
        return p.run_cycle(self.state, live, self.stop, now=now, fetch=lambda: feed, model=lambda _: reply(), sender=self.sent.append)

    def test_reviewer_case_all_malformed_feed_fails_trips_and_is_unhealthy(self):
        cycles = [self.bad_cycle([{"id": 123, "text": "synthetic"}], 1000 + i) for i in range(p.MAX_FAILURES)]
        self.assertEqual([c["status"] for c in cycles], ["failed"] * (p.MAX_FAILURES - 1) + ["tripped"])
        self.assertEqual([(c["items"], c["errors"], c["malformed"]) for c in cycles], [(0, 1, 1)] * p.MAX_FAILURES)
        self.assertEqual(self.state.get("breaker"), "tripped")
        self.assertEqual(self.state.get("last_ok"), "")                      # never recorded as a success
        ok, msg = p.health(self.state, 900, now=1004, stop_file=self.stop)
        self.assertFalse(ok)
        self.assertIn("tripped", msg)
        self.assertEqual(len(self.sent), 1)                                  # the breaker notice, once
        self.assertIn("none was usable", self.sent[0])

    def test_one_unusable_feed_is_already_unhealthy_and_does_not_refresh_last_success(self):
        self.cycle([reply()], now=1000.0)
        self.assertTrue(p.health(self.state, 900, now=1500.0, stop_file=self.stop)[0])
        c = self.bad_cycle([{"id": 123, "text": "synthetic"}], 1800.0)
        self.assertEqual(c["status"], "failed")
        self.assertEqual(float(self.state.get("last_ok")), 1000.0)
        ok, msg = p.health(self.state, 900, now=2000.0, stop_file=self.stop)  # 1000 seconds after the last real success
        self.assertFalse(ok)
        self.assertIn("stale", msg)

    def test_every_kind_of_unusable_item(self):
        lone = chr(0xD800)
        kinds = {"a number for the id": {"id": 123, "text": "x"}, "no text": {"id": "a"}, "not an object": "a string",
                 "text is a list": {"id": "a", "text": ["x"]}, "an id that is not valid Unicode": {"id": "a" + lone, "text": "x"},
                 "text that is not valid Unicode": {"id": "a", "text": lone}, "null": None}
        for name, item in kinds.items():
            with self.subTest(name):
                self.fresh()
                c = self.bad_cycle([item], 1000.0)
                self.assertEqual((c["status"], c["items"], c["malformed"]), ("failed", 0, 1), name)
                self.assertEqual(self.sent, [], name)

    def test_valid_neighbour_an_empty_feed_is_a_healthy_cycle_for_ever(self):
        for i in range(p.MAX_FAILURES + 2):
            c = self.bad_cycle([], 1000.0 + i)
            self.assertEqual((c["status"], c["items"], c["errors"]), ("ok", 0, 0))
        self.assertEqual(self.state.get("breaker"), "")
        self.assertTrue(p.health(self.state, 900, now=1010.0, stop_file=self.stop)[0])

    def test_valid_neighbour_a_mixed_feed_stays_ok_and_counts_the_bad_items(self):
        for i in range(p.MAX_FAILURES + 2):
            feed = [{"id": 123, "text": "bad"}, {"id": "g%d" % i, "text": "x"}, None]
            c = p.run_cycle(self.state, True, self.stop, now=1000.0 + 4000 * i, fetch=lambda: feed,
                            model=lambda it: reply(item_id=it["id"], summary="problem %s" % it["id"]), sender=self.sent.append)
            self.assertEqual((c["status"], c["items"], c["alerts"], c["errors"], c["malformed"]), ("ok", 1, 1, 2, 2))
        self.assertEqual(self.state.get("breaker"), "")
        self.assertEqual(len(self.sent), p.MAX_FAILURES + 2)

    def test_valid_neighbour_a_feed_of_items_already_handled_is_healthy(self):
        items = [{"id": "t1", "text": "x"}]
        self.cycle([reply()], items=items, now=1000.0)
        for i in range(p.MAX_FAILURES + 1):
            c = self.cycle([reply()], items=items, now=2000.0 + i)
            self.assertEqual((c["status"], c["items"]), ("ok", 0))
        self.assertEqual(self.state.get("breaker"), "")


class BadUnicodeAndUnexpectedErrors(Base):
    """A reply that is valid JSON can still hold text that cannot be written out. And whatever goes
    wrong with one item, the cycle goes on."""

    def test_reviewer_case_a_lone_surrogate_in_a_reply_is_rejected_not_raised(self):
        items = [{"id": "synthetic-1", "text": "Synthetic feed"}]
        good = {"item_id": "synthetic-1", "category": "outage", "urgency": 5, "summary": "Fictional checkout outage"}
        bad_reply = json.dumps(dict(good, summary=chr(0xD800)))               # the JSON text holds the escape, not the character
        self.assertIn(chr(92) + "ud800", bad_reply)
        c = p.run_cycle(self.state, True, self.stop, now=1000, fetch=lambda: items, model=lambda _: bad_reply, sender=self.sent.append)
        self.assertEqual((c["status"], c["items"], c["rejected"], c["alerts"], c["errors"]), ("ok", 1, 1, 0, 0))
        self.assertEqual(self.sent, [])
        self.assertEqual(self.state.get("rejected_total"), "1")

    def test_a_lone_surrogate_anywhere_in_a_text_field_is_rejected(self):
        for name, r in {"inside the summary": reply(summary="down " + chr(0xDFFF) + " again"), "in the item id": reply(item_id="t1" + chr(0xD800))}.items():
            with self.subTest(name):
                self.fresh()
                c = self.cycle([r])
                self.assertEqual((c["alerts"], c["rejected"]), (0, 1), name)
                self.assertEqual(self.sent, [], name)
        self.assertEqual(p.validate(dict(GOOD, summary=chr(0xD800)))[0], None)

    def test_valid_neighbour_real_non_ascii_text_is_sent(self):
        accented = "Caf" + chr(0xE9) + " checkout " + chr(0x1F525)
        c = self.cycle([reply(summary=accented)])
        self.assertEqual((c["alerts"], c["rejected"]), (1, 0))
        self.assertIn(accented, self.sent[0])
        self.fresh()
        pair = chr(92) + "ud83d" + chr(92) + "udd25"                          # a proper surrogate pair, written as JSON escapes
        raw = reply(summary="PAIR").replace("PAIR", pair)
        c = self.cycle([raw])
        self.assertEqual((c["alerts"], c["rejected"]), (1, 0))
        self.assertIn(chr(0x1F525), self.sent[0])

    def test_an_unexpected_exception_on_one_item_does_not_end_the_cycle_or_send_for_it(self):
        real = p.decide

        def decide(result, item):
            if item["id"] == "t1":
                raise ZeroDivisionError("a bug in the rule")
            return real(result, item)
        replies = [reply(summary="first"), reply(item_id="t2", summary="second")]
        with mock.patch.object(p, "decide", decide):
            c = self.cycle(replies)
        self.assertEqual((c["status"], c["items"], c["errors"], c["alerts"]), ("ok", 2, 1, 1))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("second", self.sent[0])
        self.assertFalse(self.state.seen("t1"))                              # it will be tried again
        c = self.cycle(replies, now=2000.0)
        self.assertEqual((c["items"], c["alerts"]), (1, 1))
        self.assertIn("first", self.sent[1])

    def test_an_exception_while_building_the_message_never_reaches_the_sender(self):
        def broken(_):
            raise UnicodeEncodeError("utf-8", "x", 0, 1, "planted")
        with mock.patch.object(p, "format_alert", broken):
            c = self.cycle([reply(), reply(item_id="t2")])
        self.assertEqual((c["errors"], c["alerts"], c["status"]), (2, 0, "failed"))
        self.assertEqual(self.sent, [])

    def test_every_item_failing_unexpectedly_counts_toward_the_breaker(self):
        def broken(result, item):
            raise RuntimeError("planted")
        with mock.patch.object(p, "decide", broken):
            statuses = [self.cycle([reply()], now=1000.0 + i)["status"] for i in range(p.MAX_FAILURES)]
        self.assertEqual(statuses, ["failed"] * (p.MAX_FAILURES - 1) + ["tripped"])
        self.assertEqual(len(self.sent), 1)                                  # the notice only


class DryRunIsolation(Base):
    """A dry run previews. It uses up nothing that a live run depends on."""

    ITEMS = [{"id": "synthetic-1", "text": "Synthetic feed"}]
    REPLY = json.dumps({"item_id": "synthetic-1", "category": "outage", "urgency": 5, "summary": "Fictional checkout outage"})

    def run_mode(self, live, now, fetch=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            c = p.run_cycle(self.state, live, self.stop, now=now, fetch=fetch or (lambda: self.ITEMS), model=lambda _: self.REPLY, sender=self.sent.append)
        return c, out.getvalue()

    def test_reviewer_case_dry_run_then_live_sends_once_and_only_once(self):
        dry, printed = self.run_mode(False, 1000)
        self.assertEqual((dry["items"], dry["alerts"], dry["status"]), (1, 1, "ok"))
        self.assertIn("DRY RUN", printed)
        self.assertEqual(self.sent, [])
        later, _ = self.run_mode(True, 2000)
        self.assertEqual((later["items"], later["alerts"], later["status"]), (1, 1, "ok"))
        self.assertEqual(len(self.sent), 1)
        again, _ = self.run_mode(True, 3000)
        self.assertEqual((again["items"], again["alerts"]), (0, 0))
        self.assertEqual(len(self.sent), 1)                                  # a second live run does not send again

    def test_a_second_dry_run_does_not_preview_the_same_item_again(self):
        self.run_mode(False, 1000)
        c, printed = self.run_mode(False, 1100)
        self.assertEqual((c["items"], c["alerts"]), (0, 0))
        self.assertEqual(printed, "")
        self.assertFalse(self.state.seen("synthetic-1", True))
        self.assertTrue(self.state.seen("synthetic-1", False))

    def test_a_dry_run_after_a_live_run_previews_and_sends_nothing(self):
        self.run_mode(True, 1000)
        c, printed = self.run_mode(False, 1100)
        self.assertEqual((c["items"], c["alerts"]), (1, 1))
        self.assertIn("DRY RUN", printed)
        self.assertEqual(len(self.sent), 1)

    def test_dry_run_failures_cannot_trip_the_live_breaker_and_live_failures_leave_dry_runs_alone(self):
        def boom():
            raise ConnectionError("source down")
        for i in range(p.MAX_FAILURES):
            c, printed = self.run_mode(False, 1000 + i, fetch=boom)
        self.assertEqual(c["status"], "tripped")
        self.assertIn("DRY RUN, not sent: Pipeline stopped", printed)
        self.assertEqual(self.sent, [])
        self.assertEqual((self.state.get("dry:breaker"), self.state.get("breaker"), self.state.get("failures", "0")), ("tripped", "", "0"))
        live, _ = self.run_mode(True, 2000)
        self.assertEqual((live["status"], live["alerts"]), ("ok", 1))
        self.assertEqual(self.run_mode(False, 2100)[0]["status"], "tripped")   # the dry-run record stays tripped

    def test_a_dry_run_that_works_does_not_make_the_live_record_healthy(self):
        self.run_mode(False, 1000)
        ok, msg = p.health(self.state, 900, now=1001, stop_file=self.stop, live=True)
        self.assertFalse(ok)
        self.assertIn("no successful live cycle", msg)
        self.assertTrue(p.health(self.state, 900, now=1001, stop_file=self.stop, live=False)[0])
        self.run_mode(True, 1002)
        self.assertTrue(p.health(self.state, 900, now=1003, stop_file=self.stop, live=True)[0])

    def test_dry_run_alerts_and_rejections_do_not_use_up_live_limits_or_totals(self):
        for i in range(p.MAX_ALERTS_PER_HOUR + 2):
            item = [{"id": "d%d" % i, "text": "x"}]
            with contextlib.redirect_stdout(io.StringIO()):
                p.run_cycle(self.state, False, self.stop, now=1000 + i, fetch=lambda: item,
                            model=lambda it: reply(item_id=it["id"], summary="dry %s" % it["id"]), sender=self.sent.append)
        with contextlib.redirect_stdout(io.StringIO()):
            p.run_cycle(self.state, False, self.stop, now=1100, fetch=lambda: [{"id": "r", "text": "x"}], model=lambda _: "not json", sender=self.sent.append)
        self.assertEqual((self.state.get("dry:suppressed_total"), self.state.get("dry:rejected_total")), ("2", "1"))
        self.assertEqual((self.state.get("suppressed_total", "0"), self.state.get("rejected_total", "0")), ("0", "0"))
        live, _ = self.run_mode(True, 1200)                                    # the hourly cap was reached in dry runs only
        self.assertEqual((live["alerts"], live["suppressed"]), (1, 0))
        self.assertEqual(len(self.sent), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
