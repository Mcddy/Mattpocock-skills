#!/usr/bin/env python3
"""Check a threat model file for completeness and consistency. Standard library only.

Usage:
  python threat_check.py MODEL.json [--today YYYY-MM-DD] [--stale-days 90] [--json]

MODEL.json (one object; the template in assets/threat-model-template.json is a filled-in sample):
  {"system": "...", "schema": 1, "as_of": "YYYY-MM-DD",
   "assumptions": ["..."], "out_of_scope": ["..."],
   "assets":   [{"id": "A1", "name": "...", "sensitivity": "high|medium|low", "why": "..."}],
   "actors":   [{"id": "U1", "name": "...", "trust": "authenticated|anonymous|operator|service|external"}],
   "zones":    [{"id": "Z1", "name": "...", "trust": "words"}],
   "elements": [{"id": "E1", "kind": "process|store|external|human", "name": "...", "zone": "Z1",
                 "holds": ["A1"]}],                              holds is optional
   "flows":    [{"id": "F1", "from": "E0", "to": "E1", "data": ["A1"], "protocol": "HTTPS",
                 "authenticated": true, "crosses": ["Z0", "Z1"]}],
   "threats":  [{"id": "T1", "target": "F1 or E1",
                 "category": "spoofing|tampering|repudiation|information_disclosure|denial_of_service|elevation_of_privilege",
                 "actor": "U1", "asset": "A1",                   optional, see below
                 "scenario": "who does what to which asset, with what result",
                 "impact": "...", "likelihood": "words or unknown", "likelihood_why": "optional",
                 "status": "open|mitigated|accepted|transferred",
                 "mitigations": ["M1"], "accepted_by": null, "accepted_why": null}],
   "mitigations":   [{"id": "M1", "what": "...", "where": "code or config location",
                      "built": true, "verified_by": ["V1"]}],   built is optional, default true
   "verifications": [{"id": "V1", "kind": "automated_test|manual_check|review|config_scan",
                      "how": "the command, test name or procedure",
                      "last_result": "pass|fail|not_run", "last_run": "YYYY-MM-DD or null"}]}
Every id is unique across the whole file, because a threat's target may be a flow or an element.
A flow crosses a trust boundary when its two ends sit in different zones, or when "crosses" lists
two or more zones. A store holds the assets in its "holds" list and in any flow that touches it.

What it enforces (ERROR, exit 1). The word in brackets is the rule's code, also given by --json:
  [shape]        a missing or wrongly typed field, a value outside its list, a flow whose "crosses"
                 leaves out one of its end zones. true is not 1 and "1" is not 1.
  [duplicate_id] an id used twice.
  [reference]    an id that points at nothing: a zone, element, asset, actor, mitigation, verification.
  [date]         as_of or last_run not a real date written YYYY-MM-DD; a date after today; a pass or
                 fail with no date; not_run with a date.
  [boundary_flow_no_threat]  a flow crossing a trust boundary with no threat entry at all.
  [store_no_threat]          a store holding a high-sensitivity asset with no threat entry.
  [mitigated_no_mitigation]  a threat marked mitigated that lists no mitigation.
  [mitigated_unverified]     a threat marked mitigated that relies on a mitigation which is not
                 built, has no verification, has only not_run verifications, or has a failing one.
                 Such a threat is open. With a built mitigation listed it is reported as
                 "open: built, not verified", which is the honest name for it.
  [accepted_incomplete]      an accepted threat without both accepted_by and accepted_why.
  [scenario]     a scenario under eight words, or one that names no actor or no asset. The actor
                 and asset are found in the "actor" and "asset" fields, or by their name or id
                 appearing in the scenario text.
What it reports for a person to decide (ADVISORY, never changes the exit code):
  boundary flows that are not authenticated; assets that appear in no flow and no store; for a flow
  carrying a high-sensitivity asset across a boundary, the STRIDE categories with no entry
  (candidates only: not every category applies); verifications older than --stale-days; likelihood
  "low" with no reason given; a transferred threat that does not say to whom; elements, mitigations
  and verifications nothing refers to; keys it does not know (often a spelling slip).

What it cannot tell: whether a threat is missing, whether a scenario is believable, whether a
mitigation is adequate, or whether a recorded result is true. It reads the file. It does not run
any verification and touches no system. A pass is not a penetration test, a compliance audit or a
guarantee.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
CATEGORIES = ("spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege")
STATUSES = ("open", "mitigated", "accepted", "transferred")
SENSITIVITY = ("high", "medium", "low")
ACTOR_TRUST = ("authenticated", "anonymous", "operator", "service", "external")
ELEMENT_KINDS = ("process", "store", "external", "human")
VERIFICATION_KINDS = ("automated_test", "manual_check", "review", "config_scan")
RESULTS = ("pass", "fail", "not_run")
MIN_SCENARIO_WORDS = 8
REASON_WORDS = re.compile(r"\b(because|since|requires?|needs?|only if|unless|given that|as long as|so that)\b", re.I)
TOP_KEYS = {"system", "schema", "as_of", "assumptions", "out_of_scope", "assets", "actors", "zones", "elements", "flows",
            "threats", "mitigations", "verifications", "notes"}
ITEM_KEYS = {
    "assets": {"id", "name", "sensitivity", "why", "notes"},
    "actors": {"id", "name", "trust", "notes"},
    "zones": {"id", "name", "trust", "notes"},
    "elements": {"id", "kind", "name", "zone", "holds", "notes"},
    "flows": {"id", "from", "to", "data", "protocol", "authenticated", "crosses", "notes"},
    "threats": {"id", "target", "category", "actor", "asset", "scenario", "impact", "likelihood", "likelihood_why", "status",
                "mitigations", "accepted_by", "accepted_why", "notes"},
    "mitigations": {"id", "what", "where", "built", "verified_by", "notes"},
    "verifications": {"id", "kind", "how", "last_result", "last_run", "notes"},
}
FLAGS = {"--json"}
VALUES = {"--today", "--stale-days"}


class Unreadable(Exception):
    """The input could not be read as one strict JSON document."""


def parse_date(text):
    if not isinstance(text, str) or not ISO_DATE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def text_ok(v, min_len=1):
    return isinstance(v, str) and len(v.strip()) >= min_len


def whole(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _no_constants(name):
    raise ValueError("%s is not a JSON number" % name)


def _no_duplicates(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError("the key %r appears twice in one object" % k)
        seen[k] = v
    return seen


def load(path):
    """Read one strict JSON document. Raises Unreadable with a one-line reason."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise Unreadable("cannot read %s: %s" % (path, e.strerror or e))
    if b"\x00" in raw:
        raise Unreadable("%s contains a NUL byte; it is not a text file" % path)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Unreadable("%s is not valid UTF-8" % path)
    try:
        return json.loads(text, parse_constant=_no_constants, object_pairs_hook=_no_duplicates)
    except ValueError as e:
        raise Unreadable("%s is not valid JSON (%s)" % (path, str(e)[:90]))


class Report:
    def __init__(self):
        self.errors, self.advisories = [], []

    def error(self, code, message):
        self.errors.append({"code": code, "message": message})

    def advise(self, code, message):
        self.advisories.append({"code": code, "message": message})

    def has(self, *codes):
        return any(e["code"] in codes for e in self.errors)


def _items(model, key, rep, need_one=True):
    """Return the list under key as a list of objects, reporting shape faults."""
    v = model.get(key)
    if not isinstance(v, list):
        rep.error("shape", "%s must be a list" % key)
        return []
    if need_one and not v:
        rep.error("shape", "%s is empty; a model needs at least one" % key)
    out = []
    for i, item in enumerate(v):
        if not isinstance(item, dict):
            rep.error("shape", "%s entry %d is not an object" % (key, i + 1))
            continue
        for k in sorted(set(item) - ITEM_KEYS[key]):
            rep.advise("unknown_key", "%s entry %s has a key this checker does not know: %r. Check the spelling; it was ignored"
                       % (key, item.get("id", i + 1), k))
        out.append(item)
    return out


def _id_list(v):
    return isinstance(v, list) and all(isinstance(x, str) and x for x in v)


def _mentions(text, names):
    """True if text names any of the given ids or names as whole words, ignoring case and spacing."""
    flat = " " + re.sub(r"\s+", " ", text.lower()) + " "
    for n in names:
        n = re.sub(r"\s+", " ", n.strip().lower())
        if n and re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", flat):
            return True
    return False


def mitigation_state(m, verifs):
    """not_built | failing | verified | unverified, from the verifications it lists."""
    if m.get("built") is False:
        return "not_built"
    results = [verifs[v]["last_result"] for v in m.get("verified_by", []) if v in verifs]
    if "fail" in results:
        return "failing"
    if "pass" in results:
        return "verified"
    return "unverified"


def threat_state(t, mit_states):
    """The state reported for a threat, derived from its status and its mitigations."""
    status = t.get("status")
    states = [mit_states[m] for m in t.get("mitigations", []) if m in mit_states]
    if status == "mitigated":
        return "mitigated_verified" if states and all(s == "verified" for s in states) else "mitigated_claim_unsupported"
    if status == "open":
        if "verified" in states:
            return "open_partly_mitigated"
        if any(s in ("unverified", "failing") for s in states):
            return "open_built_unverified"
        return "open_nothing_built"
    return status if status in ("accepted", "transferred") else "unknown"


STATE_WORDS = {
    "mitigated_verified": "Mitigated and verified",
    "mitigated_claim_unsupported": "Marked mitigated, but not shown to work",
    "open_partly_mitigated": "Open: partly mitigated",
    "open_built_unverified": "Open: built, not verified",
    "open_nothing_built": "Open: nothing built",
    "accepted": "Accepted",
    "transferred": "Transferred",
    "unknown": "Status not recognised",
}


def flow_boundary(f, zone_of):
    zf, zt = zone_of.get(f.get("from")), zone_of.get(f.get("to"))
    declared = set(f.get("crosses") or []) if isinstance(f.get("crosses"), list) else set()
    return (zf is not None and zt is not None and zf != zt) or len(declared) >= 2


def check(model, today=None, stale_days=90):
    """Return (errors, advisories, summary, derived). errors and advisories are lists of
    {"code", "message"}. derived is None when the file's shape or references are broken."""
    today = today or dt.date.today()
    rep = Report()
    if not isinstance(model, dict):
        rep.error("shape", "the file must hold one JSON object")
        return rep.errors, rep.advisories, {}, None
    for k in sorted(set(model) - TOP_KEYS):
        rep.advise("unknown_key", "top-level key %r is not one this checker knows. Check the spelling; it was ignored" % k)
    if not text_ok(model.get("system"), 3):
        rep.error("shape", "system is missing: name the app or system this model describes")
    if not whole(model.get("schema")) or model.get("schema") != 1:
        rep.error("shape", "schema must be the whole number 1 (true and \"1\" are not 1)")
    as_of = parse_date(model.get("as_of"))
    if as_of is None:
        rep.error("date", "as_of must be a real date written YYYY-MM-DD, for example 2026-10-09 (not 20261009)")
    elif as_of > today:
        rep.error("date", "as_of %s is after today (%s)" % (model["as_of"], today.isoformat()))
    for key in ("assumptions", "out_of_scope"):
        v = model.get(key)
        if not isinstance(v, list) or not all(text_ok(x) for x in v):
            rep.error("shape", "%s must be a list of sentences (an empty list is allowed)" % key)

    assets = _items(model, "assets", rep)
    actors = _items(model, "actors", rep)
    zones = _items(model, "zones", rep)
    elements = _items(model, "elements", rep)
    flows = _items(model, "flows", rep)
    threats = _items(model, "threats", rep, need_one=False)
    mitigations = _items(model, "mitigations", rep, need_one=False)
    verifications = _items(model, "verifications", rep, need_one=False)

    seen, index = {}, {}
    for kind, group in (("asset", assets), ("actor", actors), ("zone", zones), ("element", elements), ("flow", flows),
                        ("threat", threats), ("mitigation", mitigations), ("verification", verifications)):
        index[kind] = {}
        for item in group:
            i = item.get("id")
            if not text_ok(i) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,23}", i):
                rep.error("shape", "a %s has no usable id (a letter, then up to 23 letters, digits, hyphens or underscores)" % kind)
                continue
            if i in seen:
                rep.error("duplicate_id", "id %s is used twice (a %s and a %s). Ids are unique across the whole file" % (i, seen[i], kind))
                continue
            seen[i] = kind
            index[kind][i] = item

    def need_text(item, field, kind, hint, min_len=3):
        if not text_ok(item.get(field), min_len):
            rep.error("shape", "%s %s: %s is missing. %s" % (kind, item.get("id", "?"), field, hint))

    def need_choice(item, field, kind, allowed):
        if item.get(field) not in allowed or not isinstance(item.get(field), str):
            rep.error("shape", "%s %s: %s must be one of %s" % (kind, item.get("id", "?"), field, ", ".join(allowed)))

    for a in assets:
        need_text(a, "name", "asset", "Say what it is")
        need_choice(a, "sensitivity", "asset", SENSITIVITY)
        need_text(a, "why", "asset", "Say why it matters; that is what ranks the threats against it", 8)
    for u in actors:
        need_text(u, "name", "actor", "Say who or what it is")
        need_choice(u, "trust", "actor", ACTOR_TRUST)
    for z in zones:
        need_text(z, "name", "zone", "Name the zone")
        need_text(z, "trust", "zone", "Say in words who controls this zone and how far it is trusted")
    for e in elements:
        need_text(e, "name", "element", "Name the element")
        need_choice(e, "kind", "element", ELEMENT_KINDS)
        if e.get("zone") not in index["zone"]:
            rep.error("reference", "element %s: zone %r is not a zone in this file" % (e.get("id", "?"), e.get("zone")))
        if "holds" in e:
            if not _id_list(e["holds"]):
                rep.error("shape", "element %s: holds must be a list of asset ids" % e.get("id", "?"))
            else:
                for a in e["holds"]:
                    if a not in index["asset"]:
                        rep.error("reference", "element %s: holds %r, which is not an asset in this file" % (e.get("id", "?"), a))
    zone_of = {i: e.get("zone") for i, e in index["element"].items() if e.get("zone") in index["zone"]}
    for f in flows:
        fid = f.get("id", "?")
        for end in ("from", "to"):
            if f.get(end) not in index["element"]:
                rep.error("reference", "flow %s: %s %r is not an element in this file" % (fid, end, f.get(end)))
        if not _id_list(f.get("data")):
            rep.error("shape", "flow %s: data must be a list of asset ids (an empty list is allowed)" % fid)
        else:
            for a in f["data"]:
                if a not in index["asset"]:
                    rep.error("reference", "flow %s: data names %r, which is not an asset in this file" % (fid, a))
            if not f["data"]:
                rep.advise("flow_no_data", "flow %s names no asset. Say what it carries, or the threats against it cannot be ranked" % fid)
        need_text(f, "protocol", "flow", "Say how the data travels: HTTPS, a file read, a function call", 2)
        if not isinstance(f.get("authenticated"), bool):
            rep.error("shape", "flow %s: authenticated must be true or false (not 1, 0 or text)" % fid)
        if not _id_list(f.get("crosses")):
            rep.error("shape", "flow %s: crosses must be a list of zone ids (empty when the flow stays inside one zone)" % fid)
        else:
            for z in f["crosses"]:
                if z not in index["zone"]:
                    rep.error("reference", "flow %s: crosses names %r, which is not a zone in this file" % (fid, z))
            zf, zt = zone_of.get(f.get("from")), zone_of.get(f.get("to"))
            if zf and zt and zf != zt and not {zf, zt} <= set(f["crosses"]):
                rep.error("shape", "flow %s runs from zone %s to zone %s, but crosses says %s. List every zone it passes through, both ends included"
                          % (fid, zf, zt, json.dumps(f["crosses"])))
    for v in verifications:
        vid = v.get("id", "?")
        need_choice(v, "kind", "verification", VERIFICATION_KINDS)
        need_text(v, "how", "verification", "Give the command, the test name or the exact steps", 8)
        need_choice(v, "last_result", "verification", RESULTS)
        lr = v.get("last_run")
        if lr is None:
            if v.get("last_result") in ("pass", "fail"):
                rep.error("date", "verification %s records %s with no last_run date. A result with no date was not recorded" % (vid, v["last_result"]))
        else:
            d = parse_date(lr)
            if d is None:
                rep.error("date", "verification %s: last_run must be a real date written YYYY-MM-DD, or null" % vid)
            elif v.get("last_result") == "not_run":
                rep.error("date", "verification %s is not_run but carries a last_run date. Either it ran (pass or fail) or the date is null" % vid)
            elif d > today:
                rep.error("date", "verification %s: last_run %s is after today (%s)" % (vid, lr, today.isoformat()))
            else:
                if (today - d).days > stale_days:
                    rep.advise("stale_verification", "verification %s last ran %s, %d days ago, which is over the %d day limit. Run it again"
                               % (vid, lr, (today - d).days, stale_days))
                if as_of and d > as_of:
                    rep.advise("as_of_behind", "verification %s ran on %s, after the file's as_of date %s. Update as_of" % (vid, lr, model["as_of"]))
    for m in mitigations:
        mid = m.get("id", "?")
        need_text(m, "what", "mitigation", "Say what the defence is", 8)
        need_text(m, "where", "mitigation", "Say where it lives: a file and function, a config key, a proxy rule")
        if "built" in m and not isinstance(m["built"], bool):
            rep.error("shape", "mitigation %s: built must be true or false" % mid)
        if not _id_list(m.get("verified_by")):
            rep.error("shape", "mitigation %s: verified_by must be a list of verification ids (empty if there is none yet)" % mid)
        else:
            for v in m["verified_by"]:
                if v not in index["verification"]:
                    rep.error("reference", "mitigation %s: verified_by names %r, which is not a verification in this file" % (mid, v))
    targets = dict(index["flow"])
    targets.update(index["element"])
    for t in threats:
        tid = t.get("id", "?")
        if (not isinstance(t.get("target"), str) or t.get("target") not in targets):
            rep.error("reference", "threat %s: target %r is not a flow or an element in this file" % (tid, t.get("target")))
        need_choice(t, "category", "threat", CATEGORIES)
        need_choice(t, "status", "threat", STATUSES)
        need_text(t, "impact", "threat", "Say what it would cost if it happened", 8)
        need_text(t, "likelihood", "threat", "Use words, or write unknown. Unknown is not low")
        if not _id_list(t.get("mitigations")):
            rep.error("shape", "threat %s: mitigations must be a list of mitigation ids (empty if none)" % tid)
        else:
            for m in t["mitigations"]:
                if m not in index["mitigation"]:
                    rep.error("reference", "threat %s: mitigations names %r, which is not a mitigation in this file" % (tid, m))
        for field, kind in (("actor", "actor"), ("asset", "asset")):
            if t.get(field) is not None and t.get(field) not in index[kind]:
                rep.error("reference", "threat %s: %s %r is not an %s in this file" % (tid, field, t.get(field), kind))
        sc = t.get("scenario")
        if not isinstance(sc, str) or len(sc.split()) < MIN_SCENARIO_WORDS:
            rep.error("scenario", "threat %s: the scenario is shorter than a sentence (under %d words). Write who does what to which asset, with what result"
                      % (tid, MIN_SCENARIO_WORDS))
        else:
            if t.get("actor") not in index["actor"] and not _mentions(sc, [x for u in actors for x in (u.get("id", ""), u.get("name", "")) if isinstance(x, str)]):
                rep.error("scenario", "threat %s: the scenario names no actor. Set \"actor\" to an actor id, or name one in the text" % tid)
            if t.get("asset") not in index["asset"] and not _mentions(sc, [x for a in assets for x in (a.get("id", ""), a.get("name", "")) if isinstance(x, str)]):
                rep.error("scenario", "threat %s: the scenario names no asset. Set \"asset\" to an asset id, or name one in the text" % tid)
        if t.get("status") == "accepted" and not (text_ok(t.get("accepted_by"), 2) and text_ok(t.get("accepted_why"), 8)):
            rep.error("accepted_incomplete", "threat %s is accepted but does not say both who accepted it (accepted_by) and why (accepted_why)" % tid)
        if t.get("status") == "transferred" and not text_ok(t.get("accepted_why"), 8):
            rep.advise("transfer_unexplained", "threat %s is transferred but nothing says to whom or under what agreement. Put that in accepted_why" % tid)
        lk = t.get("likelihood")
        if isinstance(lk, str) and lk.strip().lower() == "low" and not text_ok(t.get("likelihood_why"), 8) and isinstance(sc, str) and not REASON_WORDS.search(sc):
            rep.advise("low_without_reason", "threat %s: likelihood is low and no reason is given (likelihood_why is empty and the scenario gives none). "
                       "If it is not known, write unknown" % tid)

    if rep.has("shape", "reference", "duplicate_id"):
        # The rules below read across the file. With broken structure they would mislead.
        summary = {"note": "structure errors: the cross-file rules and the counts were not computed"}
        return rep.errors, rep.advisories, summary, None

    verifs = index["verification"]
    mit_states = {i: mitigation_state(m, verifs) for i, m in index["mitigation"].items()}
    threats_on = {}
    for t in threats:
        threats_on.setdefault(t["target"], []).append(t)
    boundary = {f["id"]: flow_boundary(f, zone_of) for f in flows}
    sens = {i: a["sensitivity"] for i, a in index["asset"].items()}

    for f in flows:
        if boundary[f["id"]] and not threats_on.get(f["id"]):
            rep.error("boundary_flow_no_threat", "flow %s (%s to %s) crosses a trust boundary and has no threat entry at all. Walk the six categories for it"
                      % (f["id"], index["element"][f["from"]]["name"], index["element"][f["to"]]["name"]))
        if boundary[f["id"]] and f["authenticated"] is False:
            rep.advise("boundary_unauthenticated", "flow %s crosses a trust boundary and is not authenticated" % f["id"])
        if boundary[f["id"]] and any(sens[a] == "high" for a in f["data"]):
            present = {t["category"] for t in threats_on.get(f["id"], [])}
            absent = [c for c in CATEGORIES if c not in present]
            if absent:
                rep.advise("categories_absent", "flow %s carries a high-sensitivity asset across a boundary and has no entry for: %s. "
                           "Candidates only: not every category applies. Write the ones with a believable scenario" % (f["id"], ", ".join(absent)))
    held = {}
    for e in elements:
        held[e["id"]] = set(e.get("holds", []))
    for f in flows:
        for end in ("from", "to"):
            held[f[end]].update(f["data"])
    for e in elements:
        if e["kind"] == "store" and any(sens[a] == "high" for a in held[e["id"]]) and not threats_on.get(e["id"]):
            high = sorted(a for a in held[e["id"]] if sens[a] == "high")
            rep.error("store_no_threat", "store %s (%s) holds high-sensitivity %s and has no threat entry" % (e["id"], e["name"], ", ".join(high)))
    used_assets = set()
    for e in elements:
        used_assets.update(held[e["id"]])
    for a in assets:
        if a["id"] not in used_assets:
            rep.advise("asset_unused", "asset %s (%s) appears in no flow and no element holds it. Either it is not in this system or a flow is missing"
                       % (a["id"], a["name"]))
    touched = {f[end] for f in flows for end in ("from", "to")}
    for e in elements:
        if e["id"] not in touched:
            rep.advise("element_unconnected", "element %s (%s) has no flow to or from it" % (e["id"], e["name"]))
    used_m = {m for t in threats for m in t["mitigations"]}
    for m in mitigations:
        if m["id"] not in used_m:
            rep.advise("mitigation_unused", "mitigation %s is not listed by any threat" % m["id"])
    used_v = {v for m in mitigations for v in m["verified_by"]}
    for v in verifications:
        if v["id"] not in used_v:
            rep.advise("verification_unused", "verification %s is not listed by any mitigation" % v["id"])
    if not threats:
        rep.advise("no_threats", "the model records no threats. That is a result only if every flow and store was walked")

    t_states = {}
    for t in threats:
        tid = t["id"]
        if t["status"] == "mitigated":
            if not t["mitigations"]:
                rep.error("mitigated_no_mitigation", "threat %s is marked mitigated and lists no mitigation" % tid)
            for m in t["mitigations"]:
                st = mit_states[m]
                if st == "verified":
                    continue
                vs = index["mitigation"][m]["verified_by"]
                if st == "not_built":
                    why = "%s is not built" % m
                elif st == "failing":
                    why = "%s has a failing verification (%s)" % (m, ", ".join(v for v in vs if verifs[v]["last_result"] == "fail"))
                elif not vs:
                    why = "%s has no verification" % m
                else:
                    why = "the verifications of %s have not been run (%s)" % (m, ", ".join(vs))
                rep.error("mitigated_unverified", "threat %s is marked mitigated, but %s. Mark the threat open (it is then reported as "
                          "built, not verified) until a verification has run and passed" % (tid, why))
        t_states[tid] = threat_state(t, mit_states)

    by_status = {s: sum(1 for t in threats if t["status"] == s) for s in STATUSES}
    summary = {
        "threats": len(threats),
        "threats_by_status": by_status,
        "threats_by_state": {k: sum(1 for s in t_states.values() if s == k) for k in STATE_WORDS if any(s == k for s in t_states.values())},
        "mitigations": len(mitigations),
        "mitigations_by_state": {k: sum(1 for s in mit_states.values() if s == k) for k in ("verified", "unverified", "failing", "not_built")},
        "verifications": len(verifications),
        "verifications_by_result": {r: sum(1 for v in verifications if v["last_result"] == r) for r in RESULTS},
        "flows": len(flows),
        "boundary_flows": sum(1 for b in boundary.values() if b),
        "likelihood_unknown": sum(1 for t in threats if t["likelihood"].strip().lower() == "unknown"),
    }
    derived = {"threat_state": t_states, "mitigation_state": mit_states, "boundary": boundary}
    return rep.errors, rep.advisories, summary, derived


def render(model, errors, advisories, summary):
    name = model.get("system") if isinstance(model, dict) and text_ok(model.get("system")) else "(no system name)"
    as_of = model.get("as_of") if isinstance(model, dict) and isinstance(model.get("as_of"), str) else "no date"
    L = ["threat_check: %s (as of %s)" % (name, as_of)]
    L += ["  ERROR     %s  [%s]" % (e["message"], e["code"]) for e in errors]
    L += ["  ADVISORY  %s  [%s]" % (a["message"], a["code"]) for a in advisories]
    if "threats" in summary:
        s = summary
        b = s["threats_by_status"]
        L.append("  SUMMARY")
        L.append("    threats: %d   open %d | mitigated %d | accepted %d | transferred %d" % (s["threats"], b["open"], b["mitigated"], b["accepted"], b["transferred"]))
        st = s["threats_by_state"]
        if b["open"]:
            L.append("    of the %d open: nothing built %d | built, not verified %d | partly mitigated (a verified mitigation exists) %d"
                     % (b["open"], st.get("open_nothing_built", 0), st.get("open_built_unverified", 0), st.get("open_partly_mitigated", 0)))
        if st.get("mitigated_claim_unsupported"):
            L.append("    marked mitigated but not shown to work: %d of %d" % (st["mitigated_claim_unsupported"], b["mitigated"]))
        m = s["mitigations_by_state"]
        L.append("    mitigations: %d   verified %d | unverified %d | failing %d | not built %d" % (s["mitigations"], m["verified"], m["unverified"], m["failing"], m["not_built"]))
        v = s["verifications_by_result"]
        L.append("    verifications: %d   pass %d | fail %d | not_run %d" % (s["verifications"], v["pass"], v["fail"], v["not_run"]))
        L.append("    flows: %d, of which %d cross a trust boundary" % (s["flows"], s["boundary_flows"]))
        L.append("    likelihood unknown: %d of %d threat(s). Unknown is not low." % (s["likelihood_unknown"], s["threats"]))
    elif summary.get("note"):
        L.append("  " + summary["note"])
    L.append("RESULT: %s. %d error(s), %d advisory note(s). This checks that the file is complete and consistent. It is not a penetration "
             "test, a compliance audit or a guarantee, and it cannot tell whether a threat is missing." % ("FAIL" if errors else "PASS", len(errors), len(advisories)))
    return "\n".join(L).encode("ascii", "replace").decode("ascii")


def parse_args(argv, name):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("%s: %s needs a value" % (name, a), file=sys.stderr)
                return None
            opts[a] = v
        elif a.startswith("-") and a != "-":
            print("%s: unknown option %s" % (name, a), file=sys.stderr)
            return None
        else:
            args.append(a)
    return flags, opts, args


def main(argv):
    parsed = parse_args(argv, "threat_check")
    if parsed is None:
        return 2
    flags, opts, args = parsed
    if len(args) != 1:
        print("threat_check: give exactly one model file. Usage: python threat_check.py MODEL.json [--today YYYY-MM-DD] [--stale-days 90] [--json]", file=sys.stderr)
        return 2
    today = dt.date.today()
    if "--today" in opts:
        today = parse_date(opts["--today"])
        if today is None:
            print("threat_check: --today needs a real date written YYYY-MM-DD", file=sys.stderr)
            return 2
    stale = 90
    if "--stale-days" in opts:
        if not re.fullmatch(r"\d{1,5}", opts["--stale-days"]) or int(opts["--stale-days"]) < 1:
            print("threat_check: --stale-days needs a whole number of days, 1 or more", file=sys.stderr)
            return 2
        stale = int(opts["--stale-days"])
    try:
        model = load(args[0])
    except Unreadable as e:
        print("threat_check: %s" % e, file=sys.stderr)
        return 2
    errors, advisories, summary, _ = check(model, today, stale)
    if "--json" in flags:
        text = json.dumps({"errors": errors, "advisories": advisories, "summary": summary, "result": "FAIL" if errors else "PASS"},
                          indent=1, ensure_ascii=True)
    else:
        text = render(model, errors, advisories, summary)
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
