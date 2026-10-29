#!/usr/bin/env python3
"""Compare two versions of a sitrep watch file and list what changed. Standard library only.

Usage:
  python sitrep_diff.py OLD.json NEW.json [--stale-days N] [--json | --markdown]

OLD.json is the watch file as it was handed back after the last run. NEW.json is the candidate
written this run: the same file with one more entry in "runs", each source marked with what
happened when it was tried (last_checked, last_result), and the state as the sources give it now.
The format is in watch_check.py and references/watch-file.md. watch_check.py must sit beside this
script: both files are validated with it before anything is compared.

How items are matched: by id, and by nothing else. A state item whose id is in OLD and not in NEW
is listed as withdrawn; one whose id is in NEW and not in OLD is listed as new. Text is never
compared to guess that two different ids are the same item. If an item was reworded, keep its id
and it is reported as changed, with the old and new statement side by side.

What it lists:
  new, changed and withdrawn state items, each with its requirement's priority;
  indicators whose status changed; sources marked unreachable; sources and items not rechecked
  this run; unchanged items as a count; items past the freshness window.
  WITHDRAWN means no source reached this run still says it. It is not a finding that the
  statement is false, and this script never words it that way.
  If nothing changed and there is nothing to flag, the text and markdown output is one line.

What it enforces (ERROR, exit 1):
  - both files pass watch_check.py; the watch_id is the same; NEW has a run that OLD does not
  - a state item that rose to FACT has a source of secondary tier or better attached
  - an indicator marked seen or contradicted has evidence
  - a state item was not removed while none of its sources was reached this run (not checked is
    not withdrawn), unless NEW lists it under "withdrawn" with a reason
  - a state item dated as of this run has at least one source that was reached this run
  - no as_of moved backwards
What it reports for a person to decide (ADVISORY):
  - state items older than --stale-days (default 30) at the new run
  - a long silence between the two runs; a monthly source not tried for more than 31 days
  - "changes" in the newest run entry not matching the count found here
  - a requirement with both a withdrawn and a new item (if one is the other reworded, restore the id)
  - a statement that changed while its as_of stayed the same; earlier runs edited or removed

--markdown prints the sitrep skeleton in reporting order for the writer to complete: high-priority
changes, indicators, other changes, not checked, then one line of no change.

It cannot tell whether either file matches the world, whether a source was really read, or whether
a new statement is true. It compares two files.

Exit codes: 0 no errors (changes are not errors). 1 errors. 2 bad arguments or unreadable input.
3 could not run because watch_check.py is not beside this script (prints NOT RUN).
"""
import json
import sys

sys.dont_write_bytecode = True
try:
    from watch_check import GOOD_TIERS, InputError, emit, load_json, parse_args, parse_date, validate_watch, whole_days
except ImportError:
    print("NOT RUN: sitrep_diff needs watch_check.py in the same folder")
    sys.exit(3)

FLAGS = {"--json", "--markdown"}
VALUES = {"--stale-days"}
WITHDRAWN_LABEL = "WITHDRAWN"
WITHDRAWN_NOTE = "No source reached this run still says this. That is not a finding that it is false."
DROPPED_LABEL = "DROPPED"
DROPPED_NOTE = "Removed by decision without a check this run. Nothing was learned about whether it still holds."
METHOD_LINE = "**Sitrep, changes since last run.**"  # the first words of every later-run sitrep, so the reader can see the method
MATCH_NOTE = "Items are matched by id only. Text is never compared to guess that two ids are the same item."
RANK = {"high": 0, "medium": 1, "low": 2}


def norm(text):
    return " ".join(text.split())


def by_id(rows):
    return {x["id"]: x for x in rows}


def pair_by_id(old_rows, new_rows):
    """Return (ids in both, ids only in old, ids only in new), each in file order. Ids only."""
    old, new = by_id(old_rows), by_id(new_rows)
    both = [i for i in old if i in new]
    only_old = [i for i in old if i not in new]
    only_new = [i for i in new if i not in old]
    return both, only_old, only_new


def removed_unchecked(i, had):
    return ("state item %s was removed, but none of its sources (%s) was reached this run. Not checked is not withdrawn: "
            "keep the item with its old as_of, or list it under withdrawn with a reason" % (i, ", ".join(had)))


def context_errors(old, new):
    """Errors that need both files, found without assuming either file is well formed."""
    out = []

    def rows(d, key):
        v = d.get(key) if isinstance(d, dict) else None
        return {x["id"]: x for x in v if isinstance(x, dict) and isinstance(x.get("id"), str)} if isinstance(v, list) else {}

    tiers = {i: s.get("tier") for i, s in rows(new, "sources").items()}
    old_state, old_ind = rows(old, "state"), rows(old, "indicators")
    for i, f in rows(new, "state").items():
        was = old_state.get(i, {}).get("status")
        if f.get("status") == "FACT" and was in ("REPORTED", "ASSESSMENT", "GAP"):
            sids = f.get("source_ids") if isinstance(f.get("source_ids"), list) else []
            if not any(tiers.get(s) in GOOD_TIERS for s in sids if isinstance(s, str)):
                out.append("state item %s rose from %s to FACT with no source of secondary tier or better attached; keep it %s until one is" % (i, was, was))
    for i, x in rows(new, "indicators").items():
        was = old_ind.get(i, {}).get("status")
        ev = x.get("evidence")
        if x.get("status") in ("seen", "contradicted") and was == "not seen" and not (isinstance(ev, list) and ev):
            out.append("indicator %s went from not seen to %s with no evidence entry" % (i, x.get("status")))
    runs = new.get("runs") if isinstance(new, dict) else None
    today = runs[-1].get("date") if isinstance(runs, list) and runs and isinstance(runs[-1], dict) else None
    reached = {i for i, s in rows(new, "sources").items() if s.get("last_result") == "reached" and s.get("last_checked") == today}
    gone = new.get("withdrawn") if isinstance(new, dict) and isinstance(new.get("withdrawn"), list) else []
    listed = {w.get("id") for w in gone if isinstance(w, dict)}
    now = rows(new, "state")
    for i, f in old_state.items():
        had = [s for s in f.get("source_ids", []) if isinstance(s, str)] if isinstance(f.get("source_ids"), list) else []
        if i not in now and i not in listed and had and not any(s in reached for s in had):
            out.append(removed_unchecked(i, had))
    return out


def compare(old, new, stale_days):
    """Both files have passed validation. Return the result dictionary."""
    errors, adv = [], []
    res = {"watch_id": new["watch_id"], "title": new["title"], "purpose": new["purpose"], "matching": MATCH_NOTE}
    old_run, new_run = old["runs"][-1]["date"], new["runs"][-1]["date"]
    old_day, new_day = parse_date(old_run), parse_date(new_run)
    res.update({"old_run": old_run, "new_run": new_run, "days_between": (new_day - old_day).days})
    if old["watch_id"] != new["watch_id"]:
        errors.append("the two files are different watches (%s and %s); nothing was compared" % (old["watch_id"], new["watch_id"]))
        res.update({"errors": errors, "advisories": adv, "compared": False})
        return res
    res["compared"] = True
    if len(new["runs"]) <= len(old["runs"]):
        errors.append("NEW has no run that OLD lacks (%d and %d runs); add this run to runs with today's date" % (len(new["runs"]), len(old["runs"])))
    elif new_day < old_day:
        errors.append("NEW's last run (%s) is earlier than OLD's (%s); the files may be the wrong way round" % (new_run, old_run))
    if new["runs"][:len(old["runs"])] != old["runs"]:
        adv.append("the earlier runs recorded in NEW differ from OLD's; the run history is meant to be kept as it was")
    if res["days_between"] > stale_days:
        adv.append("the last run was %d days before this one; with a gap that long, read every item as close to a new baseline" % res["days_between"])

    prio = {r["id"]: r["priority"] for r in old["requirements"]}
    prio.update({r["id"]: r["priority"] for r in new["requirements"]})
    src = by_id(new["sources"])
    old_src = by_id(old["sources"])
    reached = {i for i, s in src.items() if s.get("last_result") == "reached" and s.get("last_checked") == new_run}

    def tag(sids, table):
        return ["%s %s" % (s, table[s]["tier"]) if s in table else s for s in sids]

    def view(f, table):
        return {"id": f["id"], "requirement": f["requirement"], "priority": prio[f["requirement"]], "statement": norm(f["statement"]),
                "status": f["status"], "source_ids": list(f["source_ids"]), "sources": tag(f["source_ids"], table), "as_of": f["as_of"]}

    # ---- state items ----
    both, only_old, only_new = pair_by_id(old["state"], new["state"])
    o, n = by_id(old["state"]), by_id(new["state"])
    reasons = {w["id"]: w for w in new.get("withdrawn", [])}
    added = [view(n[i], src) for i in only_new]
    withdrawn, dropped, changed, rechecked, carried = [], [], [], [], []
    for i in only_old:
        item = view(o[i], old_src)
        item["reason"] = norm(reasons[i]["reason"]) if i in reasons else ""
        had = o[i]["source_ids"]
        if had and not any(s in reached for s in had):
            if i in reasons:
                dropped.append(item)
            else:
                errors.append(removed_unchecked(i, had))
                item["reason"] = "removed without a check"
                dropped.append(item)
        else:
            withdrawn.append(item)
    for i in both:
        a, b = o[i], n[i]
        fields = []
        if norm(a["statement"]) != norm(b["statement"]):
            fields.append("statement")
        if a["status"] != b["status"]:
            fields.append("status %s -> %s" % (a["status"], b["status"]))
        if sorted(a["source_ids"]) != sorted(b["source_ids"]):
            fields.append("sources")
        if a["requirement"] != b["requirement"]:
            fields.append("requirement %s -> %s" % (a["requirement"], b["requirement"]))
        if b["as_of"] < a["as_of"]:
            errors.append("state item %s: as_of moved backwards, from %s to %s" % (i, a["as_of"], b["as_of"]))
        if fields:
            changed.append({"id": i, "requirement": b["requirement"], "priority": prio[b["requirement"]], "fields": fields,
                            "old": view(a, old_src), "new": view(b, src)})
            if "statement" in fields and not any(s in reached for s in b["source_ids"]):
                reason = b.get("editorial_reason")
                if not isinstance(reason, str) or len(reason.strip()) < 12:
                    errors.append("state item %s changed without a current source check; a purely editorial correction needs an explicit editorial_reason. Otherwise retain the old statement or mark the new claim GAP" % i)
                else:
                    adv.append("state item %s is an unchecked editorial correction: %s; human review must confirm its meaning is unchanged" % (i, reason.strip()))
            if "statement" in fields and a["as_of"] == b["as_of"]:
                adv.append("state item %s: the statement changed but as_of stayed %s. If the world changed, set as_of to the run date; "
                           "if only the wording was corrected, say so in the sitrep" % (i, b["as_of"]))
        elif b["as_of"] == new_run:
            rechecked.append(i)
        else:
            carried.append({"id": i, "as_of": b["as_of"]})
    for i, f in n.items():
        if f["as_of"] == new_run and f["source_ids"] and not any(s in reached for s in f["source_ids"]):
            errors.append("state item %s is dated as of this run (%s), but none of its sources (%s) is marked reached on %s; "
                          "a statement is dated by when a source was read, not by when the run happened"
                          % (i, new_run, ", ".join(f["source_ids"]), new_run))
    for req in sorted({x["requirement"] for x in withdrawn + dropped} & {x["requirement"] for x in added}):
        adv.append("requirement %s has both a removed item (%s) and a new item (%s). They were not compared by text. If the new one is the old "
                   "one reworded, give it back its id so it is reported as changed"
                   % (req, ", ".join(x["id"] for x in withdrawn + dropped if x["requirement"] == req),
                      ", ".join(x["id"] for x in added if x["requirement"] == req)))
    stale = []
    for i, f in n.items():
        age = (new_day - parse_date(f["as_of"])).days
        if age > stale_days:
            stale.append({"id": i, "as_of": f["as_of"], "days": age})
    if stale:
        adv.append("%d state item(s) are past the %d-day freshness window: %s"
                   % (len(stale), stale_days, ", ".join("%s (%d days)" % (x["id"], x["days"]) for x in stale)))

    def order(rows):
        return sorted(rows, key=lambda x: RANK[x["priority"]])

    res["state"] = {"new": order(added), "changed": order(changed), "withdrawn": order(withdrawn), "dropped": order(dropped),
                    "unchanged_rechecked": rechecked, "unchanged_carried_forward": carried, "total_now": len(n), "total_before": len(o)}
    res["stale"] = stale

    # ---- indicators ----
    both, only_old, only_new = pair_by_id(old["indicators"], new["indicators"])
    oi, ni = by_id(old["indicators"]), by_id(new["indicators"])
    moved, reworded, same = [], [], 0
    for i in both:
        a, b = oi[i], ni[i]
        if a["status"] != b["status"]:
            moved.append({"id": i, "requirement": b["requirement"], "priority": prio[b["requirement"]], "old": a["status"], "new": b["status"],
                          "seen_on": b["seen_on"], "watch_for": norm(b["watch_for"]), "would_mean": norm(b["would_mean"]),
                          "evidence": ["%s (%s): %s" % (e["source_id"], src[e["source_id"]]["tier"], norm(e["note"])) for e in b["evidence"]]})
        else:
            same += 1
            if norm(a["watch_for"]) != norm(b["watch_for"]):
                reworded.append(i)
    res["indicators"] = {"status_changed": order(moved), "added": only_new, "removed": only_old, "reworded": reworded, "unchanged": same,
                         "total_now": len(ni)}

    # ---- sources ----
    rests = {}
    for i, f in n.items():
        for s in f["source_ids"]:
            rests.setdefault(s, []).append(i)
    unreachable, not_checked = [], []
    for i, s in src.items():
        row = {"id": i, "title": norm(s["title"]), "tier": s["tier"], "check": s["check"], "last_checked": s.get("last_checked"),
               "note": norm(s["note"]) if isinstance(s.get("note"), str) else "", "items": rests.get(i, [])}
        if s.get("last_result") == "unreachable" and s.get("last_checked") == new_run:
            unreachable.append(row)
        elif i not in reached:
            if s["check"] == "each run":
                not_checked.append(row)
            else:
                last = parse_date(s.get("last_checked"))
                if last is None or (new_day - last).days > 31:
                    adv.append("monthly source %s was last tried %s; that is more than 31 days before this run"
                               % (i, s.get("last_checked") or "never"))
    due = [i for i, s in src.items() if s["check"] == "each run" or s.get("last_checked") == new_run]
    res["sources"] = {"unreachable": unreachable, "not_checked": not_checked, "reached": len(reached), "due": len(due),
                      "monthly_not_due": len(src) - len(due), "total": len(src),
                      "added": [i for i in src if i not in old_src], "removed": [i for i in old_src if i not in src]}

    # ---- the watch definition ----
    orq, nrq = by_id(old["requirements"]), by_id(new["requirements"])
    res["definition"] = {"requirements_added": [i for i in nrq if i not in orq], "requirements_removed": [i for i in orq if i not in nrq],
                         "requirements_edited": [i for i in nrq if i in orq and (norm(orq[i]["question"]) != norm(nrq[i]["question"])
                                                                                    or orq[i]["priority"] != nrq[i]["priority"])]}
    count = len(added) + len(changed) + len(withdrawn) + len(dropped) + len(moved)
    res["change_count"] = count
    defn = res["definition"]
    res["no_change"] = (count == 0 and not only_new and not only_old and not reworded and not res["sources"]["added"]
                        and not res["sources"]["removed"] and not any(defn.values()))
    said = new["runs"][-1]["changes"]
    if said != count and len(new["runs"]) > len(old["runs"]):
        adv.append("the newest run entry says changes: %d; this comparison counts %d (new, changed, withdrawn and dropped items plus "
                   "indicator status changes). Set it to %d before handing the file back" % (said, count, count))
    res.update({"errors": errors, "advisories": adv})
    return res


def no_change_line(res):
    st, so = res["state"], res["sources"]
    line = ("NO CHANGE since %s (run %s). %d of %d state item(s) unchanged: %d rechecked, %d carried forward. %d indicator(s) unchanged. "
            "%d of %d source(s) due this run reached."
            % (res["old_run"], res["new_run"], len(st["unchanged_rechecked"]) + len(st["unchanged_carried_forward"]), st["total_now"],
               len(st["unchanged_rechecked"]), len(st["unchanged_carried_forward"]), res["indicators"]["unchanged"], so["reached"], so["due"]))
    missed = [x["id"] for x in so["unreachable"]] + [x["id"] for x in so["not_checked"]]
    if missed:
        line += " Not checked: %s." % ", ".join(missed)
    return line


def not_checked_lines(res, bullet):
    L = []
    st, so = res["state"], res["sources"]
    for x in so["unreachable"]:
        L.append("%s%s unreachable (%s%s). Rests on it: %s." % (bullet, x["id"], x["title"], ("; " + x["note"]) if x["note"] else "",
                                                                ", ".join(x["items"]) or "no state item"))
    for x in so["not_checked"]:
        L.append("%s%s not tried this run (%s; last tried %s). Rests on it: %s." % (bullet, x["id"], x["title"], x["last_checked"] or "never",
                                                                                 ", ".join(x["items"]) or "no state item"))
    if st["unchanged_carried_forward"]:
        L.append("%sCarried forward without a recheck: %s." % (bullet, ", ".join("%s (as of %s)" % (x["id"], x["as_of"]) for x in st["unchanged_carried_forward"])))
    return L


def change_blocks(res):
    """Yield (priority, kind, item) for state changes in reporting order within a priority."""
    st = res["state"]
    rows = [(x["priority"], "NEW", x) for x in st["new"]] + [(x["priority"], "CHANGED", x) for x in st["changed"]] \
        + [(x["priority"], WITHDRAWN_LABEL, x) for x in st["withdrawn"]] + [(x["priority"], DROPPED_LABEL, x) for x in st["dropped"]]
    return sorted(rows, key=lambda r: RANK[r[0]])


def text_report(res):
    if not res.get("compared"):
        return "\n".join(["sitrep_diff: not compared"] + ["  ERROR     " + m for m in res["errors"]] + ["RESULT: FAIL. %d error(s)." % len(res["errors"])])
    errors, adv = res["errors"], res["advisories"]
    if res["no_change"] and not errors and not adv:
        return "sitrep_diff: " + no_change_line(res)
    st, ind = res["state"], res["indicators"]
    L = ["sitrep_diff: %s: run %s compared with run %s (%d days). %d change(s)."
         % (res["watch_id"], res["new_run"], res["old_run"], res["days_between"], res["change_count"]), "  " + MATCH_NOTE]

    def block(kind, x):
        if kind == "CHANGED":
            b = x["new"]
            L.append("  %-10s %s (%s, %s) %s as of %s [%s]; changed: %s" % (kind, x["id"], x["requirement"], x["priority"], b["status"], b["as_of"],
                                                                         ", ".join(b["sources"]) or "no source", ", ".join(x["fields"])))
            L.append("             was: " + x["old"]["statement"])
            L.append("             now: " + b["statement"])
        else:
            L.append("  %-10s %s (%s, %s) %s%s as of %s [%s]" % (kind, x["id"], x["requirement"], x["priority"], "" if kind == "NEW" else "was ",
                                                               x["status"], x["as_of"], ", ".join(x["sources"]) or "no source"))
            L.append("             " + x["statement"])
            if kind == WITHDRAWN_LABEL:
                L.append("             " + WITHDRAWN_NOTE)
            if kind == DROPPED_LABEL:
                L.append("             " + DROPPED_NOTE)
            if kind != "NEW" and x.get("reason"):
                L.append("             reason recorded: " + x["reason"])

    blocks = change_blocks(res)
    high = [b for b in blocks if b[0] == "high"]
    rest = [b for b in blocks if b[0] != "high"]
    if high:
        L.append("HIGH PRIORITY")
        for _, kind, x in high:
            block(kind, x)
    if ind["status_changed"] or ind["added"] or ind["removed"] or ind["reworded"]:
        L.append("INDICATORS")
        for x in ind["status_changed"]:
            L.append("  %s (%s, %s) %s -> %s%s" % (x["id"], x["requirement"], x["priority"], x["old"], x["new"], (" on " + x["seen_on"]) if x["seen_on"] else ""))
            L.append("             watch for: " + x["watch_for"])
            L.append("             would mean: " + x["would_mean"])
            for e in x["evidence"]:
                L.append("             evidence: " + e)
        for key, word in (("added", "added"), ("removed", "removed"), ("reworded", "reworded, status unchanged")):
            if ind[key]:
                L.append("  %s: %s" % (word, ", ".join(ind[key])))
    if rest:
        L.append("OTHER CHANGES")
        for _, kind, x in rest:
            block(kind, x)
    defn, so = res["definition"], res["sources"]
    if any(defn.values()) or so["added"] or so["removed"]:
        L.append("WATCH DEFINITION")
        for key, word in (("requirements_added", "requirements added"), ("requirements_removed", "requirements removed"),
                          ("requirements_edited", "requirements edited")):
            if defn[key]:
                L.append("  %s: %s" % (word, ", ".join(defn[key])))
        if so["added"]:
            L.append("  sources added: " + ", ".join(so["added"]))
        if so["removed"]:
            L.append("  sources removed: " + ", ".join(so["removed"]))
    nc = not_checked_lines(res, "  ")
    if nc:
        L.append("NOT CHECKED THIS RUN")
        L += nc
    L.append("NO CHANGE")
    L.append("  %d state item(s) rechecked and the same%s; %d carried forward; of %d. %d of %d indicator(s). "
             "%d of %d source(s) due this run reached; %d monthly source(s) not due."
             % (len(st["unchanged_rechecked"]), (": " + ", ".join(st["unchanged_rechecked"])) if st["unchanged_rechecked"] else "",
                len(st["unchanged_carried_forward"]), st["total_now"], ind["unchanged"], ind["total_now"], so["reached"], so["due"],
                so["monthly_not_due"]))
    L += ["  ERROR     " + m for m in errors]
    L += ["  ADVISORY  " + m for m in adv]
    L.append("RESULT: %s. %d error(s), %d advisory note(s). %d change(s). This compares two files; it does not check either against the world."
             % ("FAIL" if errors else "PASS", len(errors), len(adv), res["change_count"]))
    return "\n".join(L)


def markdown_report(res):
    if res["no_change"]:
        return "%s %s. No change since %s. %s" % (METHOD_LINE, res["title"], res["old_run"], no_change_line(res).split("). ", 1)[1])
    st, ind = res["state"], res["indicators"]
    L = ["%s %s. Run %s against %s: %d change(s)." % (METHOD_LINE, res["title"], res["new_run"], res["old_run"], res["change_count"]), ""]

    def block(kind, x):
        if kind == "CHANGED":
            b = x["new"]
            L.append("- CHANGED %s (%s). %s, %s, as of %s. Changed: %s." % (x["id"], x["requirement"], b["status"], ", ".join(b["sources"]) or "no source",
                                                                      b["as_of"], ", ".join(x["fields"])))
            L.append("  - Was: " + x["old"]["statement"])
            L.append("  - Now: " + b["statement"])
        elif kind == "NEW":
            L.append("- NEW %s (%s). %s, %s, as of %s. %s" % (x["id"], x["requirement"], x["status"], ", ".join(x["sources"]) or "no source", x["as_of"], x["statement"]))
        else:
            L.append("- %s %s (%s). Was %s, %s, as of %s: %s" % (kind, x["id"], x["requirement"], x["status"], ", ".join(x["sources"]) or "no source",
                                                              x["as_of"], x["statement"]))
            L.append("  - " + (WITHDRAWN_NOTE if kind == WITHDRAWN_LABEL else DROPPED_NOTE) + ((" Reason recorded: " + x["reason"]) if x.get("reason") else ""))
            if kind == WITHDRAWN_LABEL:
                L.append("  - [complete: what the source says now, or that it is silent]")

    blocks = change_blocks(res)
    high = [b for b in blocks if b[0] == "high"]
    rest = [b for b in blocks if b[0] != "high"]
    if high:
        L.append("**High priority**")
        for _, kind, x in high:
            block(kind, x)
    if ind["status_changed"]:
        L.append("**Indicators**")
        for x in ind["status_changed"]:
            L.append("- %s (%s): %s to %s%s. Watch for: %s Would mean: %s Evidence: %s"
                     % (x["id"], x["requirement"], x["old"], x["new"], (" on " + x["seen_on"]) if x["seen_on"] else "", x["watch_for"].rstrip(".") + ".",
                        x["would_mean"].rstrip(".") + ".", "; ".join(x["evidence"])))
    if rest:
        L.append("**Other changes**")
        for _, kind, x in rest:
            block(kind, x)
    defn, so = res["definition"], res["sources"]
    edits = [w + ": " + ", ".join(v) for w, v in (("indicators added", ind["added"]), ("indicators removed", ind["removed"]),
                                                  ("indicators reworded", ind["reworded"]), ("requirements added", defn["requirements_added"]),
                                                  ("requirements removed", defn["requirements_removed"]),
                                                  ("requirements edited", defn["requirements_edited"]), ("sources added", so["added"]),
                                                  ("sources removed", so["removed"])) if v]
    if edits:
        L.append("**Watch definition:** " + "; ".join(edits) + ".")
    nc = not_checked_lines(res, "- ")
    if nc:
        L.append("**Not checked this run**")
        L += nc
    L.append("**No change:** %d state item(s) rechecked and the same%s, %d carried forward, of %d; %d of %d indicator(s)."
             % (len(st["unchanged_rechecked"]), (" (" + ", ".join(st["unchanged_rechecked"]) + ")") if st["unchanged_rechecked"] else "",
                len(st["unchanged_carried_forward"]), st["total_now"], ind["unchanged"], ind["total_now"]))
    L.append("")
    L.append("[complete: one or two sentences on what the changes mean for the purpose, marked ASSESSMENT with a confidence. Purpose: %s]" % norm(res["purpose"]))
    return "\n".join(L)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    flags, opts, paths = parse_args(argv, "sitrep_diff", FLAGS, VALUES, 2)
    if "--json" in flags and "--markdown" in flags:
        print("sitrep_diff: choose --json or --markdown, not both", file=sys.stderr)
        return 2
    stale = whole_days(opts.get("--stale-days", "30"), "sitrep_diff")
    docs = []
    for p in paths:
        try:
            docs.append(load_json(p))
        except InputError as e:
            print("sitrep_diff: %s" % e, file=sys.stderr)
            return 2
    old, new = docs
    errors = []
    for label, d in (("OLD", old), ("NEW", new)):
        errs, _, _ = validate_watch(d, stale)
        errors += ["%s: %s" % (label, m) for m in errs]
    if errors:
        errors += context_errors(old, new)
        res = {"compared": False, "errors": errors, "advisories": []}
        if "--json" in flags:
            emit(json.dumps(res, indent=1, ensure_ascii=True))
        else:
            emit("\n".join(["sitrep_diff: the files did not pass validation, so nothing was compared"] + ["  ERROR     " + m for m in errors]
                           + ["RESULT: FAIL. %d error(s). Fix the file and run again." % len(errors)]))
        return 1
    res = compare(old, new, stale)
    if "--json" in flags:
        emit(json.dumps(res, indent=1, ensure_ascii=True))
    elif "--markdown" in flags and res.get("compared") and not res["errors"]:
        emit(markdown_report(res))
    else:
        emit(text_report(res))
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
