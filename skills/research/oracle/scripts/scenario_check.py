#!/usr/bin/env python3
"""Check a forecast or scenario set for the things that can be checked. Standard library only.

Usage:
  python scenario_check.py FORECAST.json [--today YYYY-MM-DD] [--json]

FORECAST.json:
  {"question": "Will X happen by the date?",
   "resolves_on": "2027-03-31",                    a real date, written YYYY-MM-DD
   "resolution_criterion": "what observation settles it, and where it will be read",
   "exhaustive": true,                             do the scenarios cover every outcome?
   "scenarios": [
     {"name": "Base", "description": "...",
      "probability": 60,                           a percentage, OR
      "likelihood": "likely",                      a word from the scale below; not both
      "basis": "where the number or word comes from",
      "indicators": ["an early sign that this scenario is unfolding"],
      "would_falsify": "what would rule it out"}],
   "decision": {"convention": "net", "upside": 12000, "downside": 4000, "unit": "AUD",
                "downside_is_ruin": false}}

"decision" is optional. If present it must say which of two payoff conventions its figures use,
because the same two numbers give different answers:

  "convention": "net"     with "upside" and "downside"
      Net outcomes. "upside" is what you end up ahead by if the favourable outcome happens;
      "downside" is what you end up behind by if it does not. Both positive, same unit.
      break-even chance = downside / (upside + downside)
      A net gain of 12000 against a net loss of 4000: 4000 / 16000 = 25 percent.

  "convention": "gross"   with "cost" and "gross_gain"
      A cost paid either way. "cost" is spent whichever way it turns out; "gross_gain" is what the
      favourable outcome brings in, or the loss it avoids, before taking the cost off. Both
      positive, same unit, and gross_gain must be larger than cost (otherwise the action loses
      even when it works, and no chance of success makes it pay).
      net gain = gross_gain - cost; net loss = cost; break-even chance = cost / gross_gain
      Spend 4000, paid either way, to avoid a 12000 loss: 4000 / 12000 = 33.3 percent.

A decision with no "convention", or with the other convention's fields, is refused. The script
does not guess: "spend 4k to save 12k" read as net gives 25 percent and read as gross gives 33.3.

Likelihood words and the ranges they stand for (ICD 203):
  almost no chance 1-5 | very unlikely 5-20 | unlikely 20-45 | roughly even chance 45-55 |
  likely 55-80 | very likely 80-95 | almost certain 95-99

What it enforces (ERROR, exit 1):
  - the question can be resolved: a date and a criterion are present
  - every probability or likelihood word has a stated basis of its own. A number with no basis is
    a guess wearing a number, and one basis cannot explain two different likelihoods
  - numbers are between 0 and 100; a scenario has a number or a word, not both, and words come
    from the scale
  - an exhaustive set of numbers adds up to 100 (within 1); a non-exhaustive set does not exceed 100
  - a set of words is possible: the low ends cannot add to more than 100, and for an exhaustive set
    the high ends cannot add to less than 100
  - each scenario has at least one indicator and says what would falsify it
  - a decision names its payoff convention and gives that convention's two figures, finite and
    positive; every figure the script derives is finite, or it is reported as an error. NaN and
    infinity are never printed as a computed value, and --json output is strict JSON
What it reports for a person to decide (ADVISORY):
  - a break-even that prints as 0.0 or 100.0 only because of rounding to one decimal place
  - a split that looks like a default (for example 55/25/20) when the bases are thin or identical
  - a single scenario, a resolution date in the past, a set that is not exhaustive with no "other"
For a decision it computes the break-even probability: the chance of the favourable outcome above
which the action has positive expected value, given only these two outcomes. That is arithmetic on
the two figures supplied. It is not a forecast and not advice. It is a two-outcome formula: with
three or more outcomes it does not apply, and the script does not apply it per scenario.

It cannot tell whether a basis is a good one, whether the scenarios are the right ones, or whether
the forecast is correct. Those are judgements.

Exit codes: 0 no errors. 1 errors. 2 bad arguments or unreadable input.
"""
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
SCALE = {"almost no chance": (1, 5), "very unlikely": (5, 20), "unlikely": (20, 45), "roughly even chance": (45, 55),
         "likely": (55, 80), "very likely": (80, 95), "almost certain": (95, 99)}
DEFAULT_SPLITS = [(55, 25, 20), (60, 30, 10), (50, 30, 20), (70, 20, 10), (60, 25, 15), (50, 25, 25), (60, 20, 20), (33, 33, 33), (33, 33, 34), (25, 25, 25, 25)]
FLAGS = {"--json"}
VALUES = {"--today"}


def parse_date(text):
    if not isinstance(text, str) or not ISO_DATE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def text_ok(v, min_len=1):
    return isinstance(v, str) and len(v.strip()) >= min_len


CONVENTIONS = {"net": ("upside", "downside"), "gross": ("cost", "gross_gain")}


def break_even(dec):
    """Return (computed, None) or (None, error) for a decision block.

    The two payoffs are scaled by the larger before they are added, so two large finite figures
    cannot overflow: equal payoffs give exactly 50 whatever their size."""
    if not isinstance(dec, dict):
        return None, "decision must be an object"
    conv = dec.get("convention")
    if not isinstance(conv, str) or conv not in CONVENTIONS:
        return None, ('decision must say its payoff convention: "convention": "net" (upside and downside are net outcomes) or '
                      '"convention": "gross" (cost is paid either way; gross_gain is before the cost). The same two figures give '
                      "different break-even chances under each, so the script will not guess")
    mine = CONVENTIONS[conv]
    other = [k for c, keys in CONVENTIONS.items() if c != conv for k in keys if k in dec]
    if other:
        return None, "decision uses the %s convention but also gives %s, which belongs to the other one; give %s and %s only" % (
            conv, " and ".join(other), mine[0], mine[1])
    a, b = dec.get(mine[0]), dec.get(mine[1])
    if not number(a) or not number(b) or a <= 0 or b <= 0:
        return None, "decision (%s) needs %s and %s as positive finite numbers in the same unit (true, text, NaN and infinity are not numbers)" % (
            conv, mine[0], mine[1])
    if conv == "net":
        net_gain, net_loss = float(a), float(b)
    else:
        if not b > a:
            return None, ("decision (gross): gross_gain must be larger than cost. Here the action loses even when the favourable "
                          "outcome happens, so no chance of success makes it pay and there is no break-even figure")
        net_gain, net_loss = float(b) - float(a), float(a)
    scale = max(net_gain, net_loss)
    g, l = net_gain / scale, net_loss / scale        # the larger becomes exactly 1.0, the other is in (0, 1]
    fraction = l / (g + l)
    derived = {"net_gain": net_gain, "net_loss": net_loss, "break_even_percent": round(100.0 * fraction, 1)}
    bad = [k for k, v in derived.items() if not math.isfinite(v)]
    if bad or not 0.0 <= fraction <= 1.0:
        return None, "decision: %s could not be computed as a finite number from these figures" % (", ".join(bad) or "break-even")
    out = {"payoff_convention": conv}
    out.update(derived)
    # One decimal place can hide a real gap: 99.98 prints as 100.0. Say so; do not let 0.0 or 100.0 stand alone.
    out["rounded_to_limit"] = derived["break_even_percent"] in (0.0, 100.0)
    return out, None


def check(d, today):
    errors, advisories, out = [], [], {}
    if not isinstance(d, dict):
        return ["the file must hold one JSON object"], [], {}
    if not text_ok(d.get("question"), 8):
        errors.append("question is missing or too short to be a question")
    res = parse_date(d.get("resolves_on"))
    if res is None:
        errors.append("resolves_on must be a real date written YYYY-MM-DD; a forecast with no date cannot be scored")
    elif res < today:
        advisories.append("resolves_on %s is in the past; is this a forecast or a record?" % d["resolves_on"])
    if not text_ok(d.get("resolution_criterion"), 12):
        errors.append("resolution_criterion is missing: say what observation settles it and where it will be read")
    if not isinstance(d.get("exhaustive"), bool):
        errors.append("exhaustive must be true or false: do the scenarios cover every outcome?")
    sc = d.get("scenarios")
    if not isinstance(sc, list) or not sc:
        errors.append("scenarios must be a non-empty list")
        return errors, advisories, out
    if len(sc) == 1:
        advisories.append("there is one scenario; a forecast needs at least the case where it does not happen")
    nums, words, bases, names = [], [], [], set()
    for i, s in enumerate(sc):
        where = "scenario %d" % (i + 1)
        if not isinstance(s, dict):
            errors.append(where + " is not an object")
            continue
        if text_ok(s.get("name")):
            where = "scenario %r" % s["name"].strip()[:30]
            if s["name"].strip().lower() in names:
                errors.append(where + ": name is used twice")
            names.add(s["name"].strip().lower())
        else:
            errors.append(where + " has no name")
        p, w = s.get("probability"), s.get("likelihood")
        has_p, has_w = p is not None, w is not None
        if has_p and has_w:
            errors.append(where + ": give a probability or a likelihood word, not both")
        elif has_p:
            if not number(p) or not 0 <= p <= 100:
                errors.append(where + ": probability must be a number from 0 to 100 (true, text and NaN are not numbers)")
            else:
                nums.append(float(p))
        elif has_w:
            if not isinstance(w, str) or w.strip().lower() not in SCALE:
                errors.append(where + ": likelihood %r is not on the scale (%s)" % (w, ", ".join(SCALE)))
            else:
                words.append(w.strip().lower())
        if (has_p or has_w) and not text_ok(s.get("basis"), 15):
            errors.append(where + ": a likelihood is given with no basis. Say where it comes from (a reference class, a count, a market price, a model), or remove it")
        if text_ok(s.get("basis"), 15):
            b = " ".join(s["basis"].lower().split())
            if (has_p or has_w) and b in bases:
                errors.append(where + ": gives the same basis as another scenario. One basis cannot explain two different likelihoods; say what supports this one")
            bases.append(b)
        ind = s.get("indicators")
        if not isinstance(ind, list) or not any(text_ok(x, 6) for x in ind):
            errors.append(where + ": needs at least one indicator: a few words naming an early observable sign that it is unfolding")
        if not text_ok(s.get("would_falsify"), 6):
            errors.append(where + ": say what would falsify it")
    if nums and words:
        errors.append("the set mixes numbers and likelihood words; use one or the other so the set can be checked for coherence")
    exhaustive = d.get("exhaustive")
    if nums and not words and len(nums) == len(sc):
        total = sum(nums)
        out["total"] = round(total, 2)
        if exhaustive is True and abs(total - 100) > 1:
            errors.append("the scenarios are declared exhaustive but their probabilities add to %g, not 100" % total)
        if exhaustive is False and total > 100.5:
            errors.append("the probabilities add to %g, which is more than 100" % total)
        if exhaustive is False and total < 99 and not any("other" in n or "else" in n for n in names):
            advisories.append("the set covers %g%%; name the remainder (an 'other' scenario) so it is visible" % total)
        split = tuple(sorted((int(round(x)) for x in nums), reverse=True))
        if split in DEFAULT_SPLITS and (len(set(bases)) < len(nums) or any(len(b) < 40 for b in bases)):
            advisories.append("the split %s is a common default and the bases are thin or repeated; check the numbers were derived, not filled in" % "/".join(str(x) for x in split))
    elif words and not nums and len(words) == len(sc):
        lo, hi = sum(SCALE[w][0] for w in words), sum(SCALE[w][1] for w in words)
        out["word_range_total"] = [lo, hi]
        if lo > 100:
            errors.append("these likelihood words cannot all hold: their lowest values add to %d%%" % lo)
        if exhaustive is True and hi < 100:
            errors.append("the scenarios are declared exhaustive but their highest values add to only %d%%" % hi)
    elif (nums or words) and len(nums) + len(words) < len(sc):
        advisories.append("some scenarios have a likelihood and some do not; coherence could not be checked")
    dec = d.get("decision")
    if dec is not None:
        computed, err = break_even(dec)
        if err:
            errors.append(err)
        else:
            out.update(computed)
            if computed["rounded_to_limit"]:
                advisories.append("break-even prints as %.1f%% only because of rounding to one decimal place: one figure is under a two-thousandth of the other. "
                                  "The exact value is strictly between 0 and 100" % computed["break_even_percent"])
            out["unit"] = dec.get("unit") if text_ok(dec.get("unit")) else ""
            out["ruin"] = dec.get("downside_is_ruin") is True
            if not text_ok(dec.get("unit")):
                advisories.append("decision has no unit; say what the two figures are measured in")
    return errors, advisories, out


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--"):
                print("scenario_check: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("scenario_check: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    today = dt.date.today()
    if "--today" in opts:
        today = parse_date(opts["--today"])
        if today is None:
            print("scenario_check: --today needs a real date written YYYY-MM-DD", file=sys.stderr)
            return 2
    try:
        data = json.loads(Path(args[0]).read_bytes().decode("utf-8-sig"), parse_constant=lambda c: float("nan"))
    except OSError as e:
        print("scenario_check: cannot read %s: %s" % (args[0], e.strerror or e), file=sys.stderr)
        return 2
    except (UnicodeDecodeError, ValueError) as e:
        print("scenario_check: %s is not valid UTF-8 JSON (%s)" % (args[0], str(e)[:60]), file=sys.stderr)
        return 2
    errors, advisories, out = check(data, today)
    if "--json" in flags:
        try:
            text = json.dumps({"errors": errors, "advisories": advisories, "computed": out}, indent=1, ensure_ascii=True, allow_nan=False)
        except ValueError:
            print("scenario_check: a computed value was not a finite number; nothing was printed. Check the figures in " + args[0], file=sys.stderr)
            return 2
    else:
        n = len(data.get("scenarios", [])) if isinstance(data, dict) and isinstance(data.get("scenarios"), list) else 0
        L = ["scenario_check: %d scenario(s)" % n]
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        if "total" in out:
            L.append("  probabilities add to %g" % out["total"])
        if "word_range_total" in out:
            L.append("  the likelihood words together span %d%% to %d%%" % tuple(out["word_range_total"]))
        if "break_even_percent" in out:
            unit = (" " + out["unit"]) if out["unit"] else ""
            if out["payoff_convention"] == "gross":
                L.append("  PAYOFFS     gross: a cost of %g%s paid either way and a gross gain of %g%s, so a net gain of %g and a net loss of %g."
                         % (data["decision"]["cost"], unit, data["decision"]["gross_gain"], unit, out["net_gain"], out["net_loss"]))
            else:
                L.append("  PAYOFFS     net: a net gain of %g%s and a net loss of %g%s, as given." % (out["net_gain"], unit, out["net_loss"], unit))
            L.append("  BREAK-EVEN  the action has positive expected value only if the chance of the gain is above %.1f%%." % out["break_even_percent"])
            L.append("              That is arithmetic on the two figures given, for these two outcomes only. It is not a forecast and not advice.")
            if out["ruin"]:
                L.append("              The loss is marked as ruin. Expected value does not apply to a loss you cannot survive; decide that first.")
        L.append("RESULT: %s. %d error(s), %d advisory note(s). This checks form and arithmetic, not whether the forecast is right."
                 % ("FAIL" if errors else "PASS", len(errors), len(advisories)))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
