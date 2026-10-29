#!/usr/bin/env python3
"""Check a study extraction file before any verdict is written from it. Standard library only.

Usage:
  python extraction_check.py EXTRACTION.json [--json]

EXTRACTION.json (the template with every field is in assets/extraction-template.json):
  {"audit_of": {"title": "...", "source": "who published it", "date": "YYYY-MM-DD" or null,
                "locator": "file name or address",
                "material": "full_text | abstract_only | press_release | blog_or_chart | slides | other"},
   "claim": {"quote": "the claim as the summary makes it", "locator": "abstract, sentence 3"},
   "supporting_result": {"quote": "the result in the tables that it rests on", "locator": "Table 2, row 1"},
   "design": {"type": "randomised_trial | non_randomised_comparison | cohort | case_control |
                       cross_sectional_survey | before_after | modelling | benchmark | qualitative |
                       vendor_report | other",
              "locator": "...", "ceiling": "what this design can show at most"},
   "groups": [{"name": "Intervention", "n_start": {"value": 300, "locator": "Figure 1"},
               "n_analysed": {"value": 204, "locator": "Table 2"}}],
   "outcomes": [{"name": "...", "definition": "...", "time_frame": "...", "locator": "...",
                 "status": "registered_primary | reported_primary | secondary | post_hoc | unclear",
                 "results": [{"group": "Intervention", "events": {"value": 12, "locator": "Table 2"},
                              "total": {"value": 204, "locator": "Table 2"},
                              "reported_percent": {"value": "5.9", "locator": "Table 2"}}]}],
   "other_percentages": [{"label": "...", "count": {...}, "total": {...}, "reported_percent": {...}}],
   "reporting": [{"item": "funding", "text": "what the paper says", "locator": "..."},
                 {"item": "blinding", "not_reported": true}]}
Every number taken from the paper is written {"value": N, "locator": "where it is"}. Something the
paper does not give is written {"not_reported": true}. A reported percentage is written as text,
exactly as printed ("5.9", "31"), so its precision is kept. A continuous result gives "mean", "sd"
and "n" in place of "events" and "total".

What it enforces (ERROR, exit 1): required fields are present; every extracted number has a
locator; vocabularies are respected; counts are whole numbers, events do not exceed totals,
analysed does not exceed started, and results name a group that exists; the date is a real date
written YYYY-MM-DD or null.
What it reports as a FINDING (exit 1): a reported percentage that its own counts do not give under
rounding (the same rule as effect.py check-percent). Check the extraction first; if the numbers
were copied correctly, the paper disagrees with itself.
What it reports for a person to decide (ADVISORY): loss by group and whether it differs; an outcome
denominator that is not the group's analysed size; a reported primary outcome that is not the
registered one; material that is only an abstract or a press release; items this design is
normally asked about that the file does not address.
It lists everything marked not reported, so that nothing unreported is assumed fine or assumed bad,
and prints the effect.py commands that recompute each outcome.
What it reports as CANNOT CHECK (exit 3 when nothing else is wrong): a comparison the file sets up
that could not be made because a number it needs is marked not reported. A reported percentage
whose count or total is missing, a group whose loss cannot be worked out, a difference in means
with no standard deviation. A comparison that was not made is never counted as passed.

What it cannot tell: whether a number was copied correctly, whether a locator really holds that
number, or whether the right outcome was extracted. Those take reading the paper.

The last line reads PASS (every comparison the file sets up was made and agreed), INCOMPLETE
(nothing disagreed, but at least one comparison could not be made), FINDINGS (the file is well
formed and the paper's own numbers disagree) or FAIL (the file itself has errors). It also says
how many comparisons were made, so a PASS that compared nothing can be seen for what it is.

Exit codes: 0 no errors, no findings, and nothing that could not be checked. 1 errors or findings.
2 bad arguments or unreadable input. 3 no errors and no findings, but at least one comparison
could not be made (CANNOT CHECK). Exit 3 is the ordinary result for a document that leaves numbers
out: list each CANNOT CHECK line in the verdict as a GAP.
"""
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import effect  # noqa: E402  the same arithmetic as the calculator, not a second copy of it

MATERIALS = ("full_text", "abstract_only", "press_release", "blog_or_chart", "slides", "other")
DESIGNS = ("randomised_trial", "non_randomised_comparison", "cohort", "case_control", "cross_sectional_survey", "before_after", "modelling",
           "benchmark", "qualitative", "vendor_report", "other")
STATUSES = ("registered_primary", "reported_primary", "secondary", "post_hoc", "unclear")
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
COMMON = ("funding", "author_affiliations", "data_availability", "replication")
EXPECTED = {
    "randomised_trial": ("registration", "allocation_method", "blinding", "analysis_population", "reasons_for_loss") + COMMON,
    "non_randomised_comparison": ("how_groups_were_formed", "baseline_comparison", "other_differences_between_groups", "blinding", "reasons_for_loss") + COMMON,
    "cohort": ("how_participants_were_selected", "exposure_measurement", "confounders_adjusted", "reasons_for_loss") + COMMON,
    "case_control": ("how_cases_and_controls_were_selected", "exposure_measurement", "confounders_adjusted") + COMMON,
    "cross_sectional_survey": ("sampling_method", "response_rate", "question_wording", "weighting") + COMMON,
    "before_after": ("comparison_group", "other_changes_in_the_period", "measurement_same_before_and_after") + COMMON,
    "modelling": ("assumptions", "input_data_sources", "validation_against_outcomes", "sensitivity_analysis") + COMMON,
    "benchmark": ("what_was_run", "test_set_origin", "prompts_and_settings", "number_of_runs", "run_to_run_variation",
                  "contamination_check", "baseline_tuning", "metric_definition") + COMMON,
    "vendor_report": ("what_was_run", "test_set_origin", "prompts_and_settings", "number_of_runs", "run_to_run_variation",
                      "contamination_check", "baseline_tuning", "metric_definition") + COMMON,
    "qualitative": ("how_participants_were_selected", "analysis_method", "who_coded_the_data") + COMMON,
    "other": COMMON,
}


def text_ok(v, least=1):
    return isinstance(v, str) and len(v.strip()) >= least


def whole(v):
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10 ** 12


def number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return abs(v) <= 10 ** 15
    return isinstance(v, float) and math.isfinite(v)


FINDING_NOTE = ("Check the extraction against the document first. If the numbers are copied correctly, the document disagrees with itself: "
                "the count, the total or the percentage is misprinted, or the percentage uses a different denominator. What would settle it: "
                "the denominator the authors used, from the text, a supplement or the authors. A finding is a discrepancy to be explained, nothing more.")


class Checker(object):
    def __init__(self):
        self.errors, self.findings, self.advisories, self.not_reported, self.commands = [], [], [], [], []
        self.cannot = []
        self.numbers = 0
        self.percent_checks = 0
        self.losses = 0

    def field(self, obj, where, kind):
        """Read a {"value", "locator"} object. Returns the value, or None if absent, unreported or wrong.
        kind is count, number or percent."""
        if obj is None:
            return None
        if not isinstance(obj, dict):
            self.errors.append("%s must be written {\"value\": ..., \"locator\": \"...\"} or {\"not_reported\": true}; a bare value has no locator" % where)
            return None
        if obj.get("not_reported") is True:
            self.not_reported.append(where)
            return None
        if "value" not in obj:
            self.errors.append("%s has neither a value nor not_reported" % where)
            return None
        v = obj["value"]
        if not text_ok(obj.get("locator")):
            self.errors.append("%s has no locator: say where in the paper the number is" % where)
        if kind == "count" and not whole(v):
            self.errors.append("%s must be a whole number from zero to a million million (text, true and fractions are refused)" % where)
            return None
        if kind == "number" and (not number(v) or abs(v) > 1e12):
            self.errors.append("%s must be a number (text, true and NaN are refused)" % where)
            return None
        if kind == "percent":
            if not isinstance(v, str) or not effect.PERCENT.fullmatch(v.strip()) or float(v) > 100:
                self.errors.append("%s must be the percentage as text, exactly as printed (\"31\" or \"30.8\"), so its precision is kept" % where)
                return None
            v = v.strip()
        self.numbers += 1
        return v

    def percent(self, where, count, total, reported, raw=None):
        """Compare a reported percentage with its counts. raw is the three objects as written in the
        file, so that a comparison lost to a not_reported number is recorded as CANNOT CHECK."""
        if count is None or total is None or reported is None or total == 0 or count > total:
            if raw is not None:
                names = ("count", "total", "reported percentage")
                gone = [n for n, o in zip(names, raw) if isinstance(o, dict) and o.get("not_reported") is True]
                have = [n for n, v in zip(names, (count, total, reported)) if v is not None]
                if gone and have and (reported is not None or (count is not None and total is not None and "reported percentage" in gone)):
                    if reported is not None:
                        self.cannot.append("%s: the reported %s%% cannot be checked against its counts (%s not reported)"
                                           % (where, reported, " and ".join(g for g in gone if g != "reported percentage")))
                    else:
                        self.cannot.append("%s: %d of %d has no reported percentage to be checked against (not reported)" % (where, count, total))
            return
        self.percent_checks += 1
        r = effect.percent_check(count, total, reported)
        if not r["consistent"]:
            fits = r["counts_that_fit"]
            tail = ("%s%% would need a count of %s" % (reported, " or ".join(str(k) for k in fits))) if fits else \
                   ("no whole count out of %d gives %s%%" % (total, reported))
            self.findings.append("%s: reported %s%%, but %d of %d is %.*f%% (%s)"
                                 % (where, reported, count, total, max(2, r["places"] + 1), float(r["exact"]), tail))


def check(d):
    c = Checker()
    if not isinstance(d, dict):
        c.errors.append("the file must hold one JSON object")
        return c, {}
    summary = {}
    a = d.get("audit_of")
    if not isinstance(a, dict):
        c.errors.append("audit_of is missing: say what is being audited")
        a = {}
    else:
        for k in ("title", "source", "locator"):
            if not text_ok(a.get(k)):
                c.errors.append("audit_of.%s is missing" % k)
        if a.get("material") not in MATERIALS:
            c.errors.append("audit_of.material must be one of %s" % ", ".join(MATERIALS))
        elif a["material"] in ("abstract_only", "press_release"):
            c.advisories.append("only the %s is available: this is an audit of its claims, most of the rest is GAP, and the "
                                "full text should be asked for" % a["material"].replace("_", " "))
        elif a["material"] in ("blog_or_chart", "slides"):
            c.advisories.append("the material is %s: treat it as a claim with an unknown method and say what would be needed"
                                % a["material"].replace("_", " "))
        when = a.get("date")
        if when is None:
            c.not_reported.append("audit_of.date")
        else:
            ok = isinstance(when, str) and ISO_DATE.fullmatch(when)
            if ok:
                try:
                    dt.date.fromisoformat(when)
                except ValueError:
                    ok = False
            if not ok:
                c.errors.append("audit_of.date must be a real date written YYYY-MM-DD, or null if the paper gives none")
    for key, what in (("claim", "the claim as the summary makes it"), ("supporting_result", "the result in the body that the claim rests on")):
        q = d.get(key)
        if isinstance(q, dict) and q.get("not_reported") is True and key == "supporting_result":
            c.not_reported.append("supporting_result (no result in the material supports the claim)")
        elif not isinstance(q, dict) or not text_ok(q.get("quote"), 8):
            c.errors.append("%s.quote is missing: quote %s" % (key, what))
        elif not text_ok(q.get("locator")):
            c.errors.append("%s has no locator" % key)
    design = d.get("design")
    dtype = None
    if not isinstance(design, dict) or design.get("type") not in DESIGNS:
        c.errors.append("design.type must be one of %s" % ", ".join(DESIGNS))
    else:
        dtype = design["type"]
        if not text_ok(design.get("ceiling"), 12):
            c.errors.append("design.ceiling is missing: say what this design can show at most, before anything else")
        if not text_ok(design.get("locator")):
            c.errors.append("design has no locator: say where the paper describes how the study was done")
    groups, names = d.get("groups"), {}
    if not isinstance(groups, list) or not groups:
        c.errors.append("groups must be a non-empty list (one group is fine for a single-sample study)")
        groups = []
    loss = []
    for i, g in enumerate(groups):
        where = "group %d" % (i + 1)
        if not isinstance(g, dict) or not text_ok(g.get("name")):
            c.errors.append(where + " has no name")
            continue
        name = g["name"].strip()
        where = "group %s" % name
        if name in names:
            c.errors.append(where + ": name is used twice")
        if "n_start" not in g or "n_analysed" not in g:
            c.errors.append(where + ": needs n_start and n_analysed (each a value with a locator, or not_reported)")
        ns = c.field(g.get("n_start"), where + " n_start", "count")
        na = c.field(g.get("n_analysed"), where + " n_analysed", "count")
        names[name] = (ns, na)
        gone = [k for k, o in (("n_start", g.get("n_start")), ("n_analysed", g.get("n_analysed"))) if isinstance(o, dict) and o.get("not_reported") is True]
        if gone:
            c.cannot.append("%s: loss cannot be worked out (%s not reported)" % (where, " and ".join(gone)))
        if ns is not None and na is not None:
            if na > ns:
                c.errors.append("%s: analysed (%d) is more than started (%d), which is impossible. Check the extraction" % (where, na, ns))
            elif ns > 0:
                loss.append((name, ns, na))
                c.losses += 1
    if loss:
        summary["attrition"] = [{"group": n, "start": s, "analysed": an, "lost": s - an,
                                 "lost_percent": effect.jnum(100.0 * (s - an) / s, effect.places_for(s))} for n, s, an in loss]
        ts, ta = sum(s for _n, s, _a in loss), sum(an for _n, _s, an in loss)
        cmd = "python effect.py attrition --start %d --analysed %d" % (ts, ta)
        if ts == ta:
            cmd = None
        elif len(loss) >= 2:
            cmd += "".join(" --by-group \"%s:%d:%d\"" % (n, s, an) for n, s, an in loss)
            ordered = sorted(loss, key=lambda x: (x[1] - x[2]) / x[1])
            lo, hi = ordered[0], ordered[-1]
            diff, dlo, dhi = effect.newcombe_difference(hi[1] - hi[2], hi[1], lo[1] - lo[2], lo[1], effect.z_for(95))
            if not dlo <= 0.0 <= dhi:
                pp = effect.places_for(min(hi[1], lo[1]))
                c.advisories.append("loss differs between groups: %s lost %d of %d, %s lost %d of %d, a gap of %s percentage "
                                    "points (interval %s to %s). Read why people left"
                                    % (hi[0], hi[1] - hi[2], hi[1], lo[0], lo[1] - lo[2], lo[1], effect.num(100 * diff, pp),
                                       effect.num(100 * dlo, pp), effect.num(100 * dhi, pp)))
        if cmd:
            c.commands.append(cmd)
    outcomes = d.get("outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        c.errors.append("outcomes must be a non-empty list")
        outcomes = []
    statuses = []
    for i, o in enumerate(outcomes):
        where = "outcome %d" % (i + 1)
        if not isinstance(o, dict) or not text_ok(o.get("name")):
            c.errors.append(where + " has no name")
            continue
        oname = o["name"].strip()
        where = "outcome %r" % oname[:70]
        if not text_ok(o.get("definition"), 8):
            c.errors.append(where + ": definition is missing: say exactly what was counted or measured")
        if not text_ok(o.get("locator")):
            c.errors.append(where + " has no locator")
        if o.get("status") not in STATUSES:
            c.errors.append(where + ": status must be one of %s" % ", ".join(STATUSES))
        else:
            statuses.append((o["status"], oname))
        if not text_ok(o.get("time_frame")):
            c.not_reported.append(where + " time_frame")
        results = o.get("results")
        if not isinstance(results, list) or not results:
            c.errors.append(where + ": results must be a non-empty list, or the outcome does not belong in the file")
            continue
        binary = []
        continuous = []
        for j, r in enumerate(results):
            rw = "%s result %d" % (where, j + 1)
            if not isinstance(r, dict) or not text_ok(r.get("group")):
                c.errors.append(rw + " names no group")
                continue
            gname = r["group"].strip()
            rw = "%s, %s" % (where, gname)
            if gname not in names:
                c.errors.append(rw + ": there is no group with that name")
                continue
            if "mean" in r or "sd" in r or "n" in r:
                m = c.field(r.get("mean"), rw + " mean", "number")
                s = c.field(r.get("sd"), rw + " sd", "number")
                n = c.field(r.get("n"), rw + " n", "count")
                for k in ("mean", "sd", "n"):
                    if k not in r:
                        c.errors.append("%s: a continuous result needs mean, sd and n (each a value with a locator, or not_reported)" % rw)
                        break
                if s is not None and s < 0:
                    c.errors.append(rw + ": a standard deviation cannot be negative")
                    s = None
                if None not in (m, s, n) and n >= 2:
                    continuous.append((gname, m, s, n))
                else:
                    gone = [k for k in ("mean", "sd", "n") if isinstance(r.get(k), dict) and r[k].get("not_reported") is True]
                    if gone:
                        c.cannot.append("%s: the difference in means and its interval cannot be recomputed (%s not reported)" % (rw, " and ".join(gone)))
                continue
            if "events" not in r or "total" not in r:
                c.errors.append("%s: needs events and total, or mean, sd and n (each a value with a locator, or not_reported)" % rw)
                continue
            ev = c.field(r.get("events"), rw + " events", "count")
            tot = c.field(r.get("total"), rw + " total", "count")
            rp = c.field(r.get("reported_percent"), rw + " reported_percent", "percent")
            if ev is None or tot is None:
                c.percent(rw, ev, tot, rp, (r.get("events"), r.get("total"), r.get("reported_percent")))
                gone = [k for k in ("events", "total") if isinstance(r.get(k), dict) and r[k].get("not_reported") is True]
                if gone and rp is None:
                    c.cannot.append("%s: the risk and any difference cannot be recomputed (%s not reported)" % (rw, " and ".join(gone)))
            if ev is not None and tot is not None:
                if tot == 0:
                    c.errors.append(rw + ": total is zero")
                    continue
                if ev > tot:
                    c.errors.append("%s: events (%d) are more than the total (%d), which is impossible. Check the extraction" % (rw, ev, tot))
                    continue
                ns, na = names[gname]
                if ns is not None and tot > ns:
                    c.errors.append("%s: the total (%d) is more than the group started with (%d)" % (rw, tot, ns))
                elif na is not None and tot != na:
                    c.advisories.append("%s: this outcome is out of %d, but the group's analysed size is %d. Find out what this "
                                        "denominator leaves out or adds" % (rw, tot, na))
                c.percent(rw, ev, tot, rp, (r.get("events"), r.get("total"), r.get("reported_percent")))
                binary.append((gname, ev, tot))
        if len(binary) == 2:
            (ga, ea, ta_), (gb, eb, tb) = binary
            c.commands.append("python effect.py two-by-two --a-events %d --a-total %d --b-events %d --b-total %d --a-label \"%s\" --b-label \"%s\""
                              % (ea, ta_, eb, tb, ga, gb))
        elif len(binary) == 1:
            c.commands.append("python effect.py proportion --events %d --total %d" % (binary[0][1], binary[0][2]))
        elif len(binary) > 2:
            c.advisories.append("%s has %d groups: the commands below compare the first group listed with each of the others. "
                                "Put the group the claim is about first" % (where, len(binary)))
            ga, ea, ta_ = binary[0]
            for gb, eb, tb in binary[1:]:
                c.commands.append("python effect.py two-by-two --a-events %d --a-total %d --b-events %d --b-total %d --a-label \"%s\" --b-label \"%s\""
                                  % (ea, ta_, eb, tb, ga, gb))
        if len(continuous) == 2:
            (g1, m1, s1, n1), (g2, m2, s2, n2) = continuous
            c.commands.append("python effect.py means --mean1 %r --sd1 %r --n1 %d --mean2 %r --sd2 %r --n2 %d" % (m1, s1, n1, m2, s2, n2))
    registered = [n for s, n in statuses if s == "registered_primary"]
    reported = [n for s, n in statuses if s == "reported_primary"]
    if reported and registered:
        c.advisories.append("the outcome reported as primary (%s) is not the one registered as primary (%s). Report both results, "
                            "and say which the headline claim uses" % ("; ".join(reported), "; ".join(registered)))
    elif reported and dtype == "randomised_trial":
        c.advisories.append("an outcome is marked reported_primary and none is marked registered_primary: find the protocol or "
                            "registration, or record registration as not reported")
    others = d.get("other_percentages", [])
    if not isinstance(others, list):
        c.errors.append("other_percentages must be a list")
        others = []
    for i, p in enumerate(others):
        where = "other percentage %d" % (i + 1)
        if not isinstance(p, dict) or not text_ok(p.get("label")):
            c.errors.append(where + " has no label")
            continue
        where = "percentage %r" % p["label"].strip()[:50]
        cnt = c.field(p.get("count"), where + " count", "count")
        tot = c.field(p.get("total"), where + " total", "count")
        rp = c.field(p.get("reported_percent"), where + " reported_percent", "percent")
        for k in ("count", "total", "reported_percent"):
            if k not in p:
                c.errors.append("%s: needs count, total and reported_percent" % where)
                break
        if cnt is not None and tot is not None and cnt > tot:
            c.errors.append("%s: the count (%d) is more than the total (%d), which is impossible. Check the extraction" % (where, cnt, tot))
        c.percent(where, cnt, tot, rp, (p.get("count"), p.get("total"), p.get("reported_percent")))
    reporting = d.get("reporting", [])
    if not isinstance(reporting, list):
        c.errors.append("reporting must be a list")
        reporting = []
    addressed = set()
    for i, r in enumerate(reporting):
        if not isinstance(r, dict) or not text_ok(r.get("item")):
            c.errors.append("reporting entry %d has no item" % (i + 1))
            continue
        item = r["item"].strip()
        addressed.add(item)
        if r.get("not_reported") is True:
            c.not_reported.append(item.replace("_", " "))
        elif not text_ok(r.get("text")):
            c.errors.append("reporting item %s: give what the paper says in \"text\", or mark it not_reported" % item)
        elif not text_ok(r.get("locator")):
            c.errors.append("reporting item %s has no locator" % item)
    if dtype:
        missing = [x for x in EXPECTED[dtype] if x not in addressed]
        if missing:
            c.advisories.append("not addressed for a %s: %s. For each, record what the paper says or mark it not_reported"
                                % (dtype.replace("_", " "), ", ".join(missing)))
    summary["numbers_with_locators"] = c.numbers
    summary["comparisons_made"] = {"percentages_against_counts": c.percent_checks, "group_losses": c.losses}
    return c, summary


def say(text):
    """Print to standard output; a reader that closes the pipe early is not an error."""
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, args = set(), []
    for a in argv:
        if a == "--json":
            flags.add(a)
        elif a.startswith("-"):
            print("extraction_check: unknown option " + a.encode("ascii", "replace").decode("ascii"), file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        say(__doc__)
        return 2
    try:
        raw = Path(args[0]).read_bytes()
    except OSError as e:
        print("extraction_check: cannot read %s: %s" % (args[0], e.strerror or e), file=sys.stderr)
        return 2
    try:
        text = raw.decode("utf-8-sig")
        if "\x00" in text:
            raise ValueError("it contains NUL bytes")

        def refuse(const):
            raise ValueError("%s is not a JSON number" % const)

        data = json.loads(text, parse_constant=refuse)
    except (UnicodeDecodeError, ValueError) as e:
        print("extraction_check: %s is not valid UTF-8 JSON (%s)" % (args[0], str(e)[:70]), file=sys.stderr)
        return 2
    c, summary = check(data)
    failed = bool(c.errors or c.findings)
    word = "FAIL" if c.errors else ("FINDINGS" if c.findings else ("INCOMPLETE" if c.cannot else "PASS"))
    made = "%d percentage(s) compared with their counts, %d group loss(es) worked out, %d comparison(s) could not be made" \
           % (c.percent_checks, c.losses, len(c.cannot))
    if "--json" in flags:
        out = json.dumps({"errors": c.errors, "findings": c.findings, "advisories": c.advisories, "not_reported": c.not_reported,
                          "finding_note": FINDING_NOTE if c.findings else None,
                          "cannot_check": c.cannot, "summary": summary, "commands": c.commands, "result": word},
                         indent=1, ensure_ascii=True, allow_nan=False)
    else:
        L = ["extraction_check: %d number(s) with locators, %d item(s) marked not reported" % (c.numbers, len(c.not_reported))]
        L += ["  ERROR     " + m for m in c.errors]
        L += ["  FINDING   " + m for m in c.findings]
        if c.findings:
            L.append("            " + FINDING_NOTE)
        L += ["  ADVISORY  " + m for m in c.advisories]
        for row in summary.get("attrition", []):
            L.append("  LOSS      %s: %d started, %d analysed, %d lost (%s%% of %d)"
                     % (row["group"], row["start"], row["analysed"], row["lost"],
                        effect.num(row["lost_percent"], effect.places_for(row["start"])), row["start"]))
        if c.not_reported:
            L.append("  NOT REPORTED (list these in the verdict as not reported; do not assume them fine or bad):")
            L += ["            " + m for m in c.not_reported]
        if c.cannot:
            L.append("  CANNOT CHECK (not a pass: each is a comparison that could not be made; report it as a GAP):")
            L += ["            " + m for m in c.cannot]
        if c.commands and not c.errors:
            L.append("  RECOMPUTE with:")
            L += ["            " + m for m in c.commands]
        L.append("RESULT: %s. %d error(s), %d finding(s), %d advisory note(s); %s. This checks the file's form and "
                 "arithmetic, not whether the numbers were copied correctly." % (word, len(c.errors), len(c.findings), len(c.advisories), made))
        out = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(out + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if failed else (3 if c.cannot else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
