#!/usr/bin/env python3
"""Rank options on weighted criteria and find the smallest changes that flip the winner.
Standard library only.

Usage:
  python sensitivity.py <board.json> [--json]

board.json:
{
  "scale_max": 10,
  "criteria": [{"name": "Cost", "weight": 3}, {"name": "Speed", "weight": 2}],
  "options": ["A", "B"],
  "scores": {"A": {"Cost": {"value": 7, "source": "quote dated 1 Oct"},
                   "Speed": {"value": 5, "source": "GUESS"}},
             "B": {"Cost": 4, "Speed": 9}}
}
A bare number is allowed and is treated as source "unstated". Weights are normalised to sum to 1.
"""
import json
import math
import sys
from pathlib import Path


def load(path):
    b = json.loads(Path(path).read_text(encoding="utf-8"))
    crit = [c["name"] for c in b["criteria"]]
    raw = [float(c["weight"]) for c in b["criteria"]]
    options = b["options"]
    smax = float(b.get("scale_max", 10))
    if not crit or len(crit) != len(set(crit)) or len(options) < 2 or len(options) != len(set(options)):
        raise SystemExit("use unique criteria and at least two unique options")
    if not math.isfinite(smax) or smax <= 0:
        raise SystemExit("scale_max must be finite and positive")
    if any(not math.isfinite(x) or x < 0 for x in raw) or not math.isfinite(sum(raw)) or sum(raw) <= 0:
        raise SystemExit("weights must be finite, nonnegative and sum to more than zero")
    w = {c: x / sum(raw) for c, x in zip(crit, raw)}
    s, src = {}, {}
    for o in b["options"]:
        s[o], src[o] = {}, {}
        for c in crit:
            cell = b["scores"][o][c]
            if isinstance(cell, dict):
                s[o][c], src[o][c] = float(cell["value"]), str(cell.get("source", "unstated"))
            else:
                s[o][c], src[o][c] = float(cell), "unstated"
    if any(not math.isfinite(s[o][c]) or not 0 <= s[o][c] <= smax for o in options for c in crit):
        raise SystemExit("scores must be finite and inside the declared scale")
    return options, crit, w, s, src, smax


def totals(options, crit, w, s):
    return {o: sum(w[c] * s[o][c] for c in crit) for o in options}


def analyse(path):
    options, crit, w, s, src, smax = load(path)
    tot = totals(options, crit, w, s)
    ranking = sorted(options, key=lambda o: -tot[o])
    top = ranking[0]
    margin = tot[top] - tot[ranking[1]] if len(ranking) > 1 else None

    weight_flips = []
    for c in crit:
        if w[c] >= 1.0:
            continue
        rest = {o: sum(w[j] * s[o][j] for j in crit if j != c) / (1.0 - w[c]) for o in options}
        best = None
        for r in options:
            if r == top:
                continue
            a = s[top][c] - s[r][c]
            b = rest[top] - rest[r]
            if abs(b - a) < 1e-12:
                continue
            t = b / (b - a)  # weight on c at which top and r tie
            if 0.0 <= t <= 1.0:
                delta = t - w[c]
                if best is None or abs(delta) < abs(best["change"]):
                    best = {"criterion": c, "weight_now": round(w[c], 4), "weight_at_flip": round(t, 4),
                            "change": round(delta, 4), "new_winner": r}
        if best:
            weight_flips.append(best)
    weight_flips.sort(key=lambda x: abs(x["change"]))

    cell_flips = []
    for o in options:
        for c in crit:
            if w[c] <= 0:
                continue
            if o == top:
                rival = ranking[1] if len(ranking) > 1 else None
                if rival is None:
                    continue
                v = s[o][c] - (tot[top] - tot[rival]) / w[c]
                new = rival
            else:
                v = s[o][c] + (tot[top] - tot[o]) / w[c]
                new = o
            if 0.0 <= v <= smax:
                cell_flips.append({"option": o, "criterion": c, "value_now": s[o][c], "value_at_flip": round(v, 3),
                                   "change": round(v - s[o][c], 3), "source": src[o][c], "new_winner": new})
    cell_flips.sort(key=lambda x: abs(x["change"]))
    guesses = [x for x in cell_flips if x["source"].strip().upper() == "GUESS"]
    return {
        "weights": {c: round(w[c], 4) for c in crit},
        "totals": {o: round(tot[o], 3) for o in ranking},
        "ranking": ranking,
        "winner": top,
        "margin": None if margin is None else round(margin, 3),
        "near_tie": margin is not None and margin < 0.025 * smax,
        "weight_flips": weight_flips,
        "cell_flips": cell_flips[:12],
        "guess_flips": guesses,
        "guess_cells": sum(1 for o in options for c in crit if src[o][c].strip().upper() == "GUESS"),
    }


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    rep = analyse(args[0])
    if "--json" in argv:
        print(json.dumps(rep, indent=1))
        return 0
    print("ranking: " + "  >  ".join("%s %.2f" % (o, rep["totals"][o]) for o in rep["ranking"]))
    if rep["margin"] is not None and rep["margin"] < 1e-9:
        print("exact tie between %s and %s: the weighted sum does not separate them" % (rep["ranking"][0], rep["ranking"][1]))
    print("winner: %s, margin %.2f%s" % (rep["winner"], rep["margin"] or 0, "  (near tie)" if rep["near_tie"] else ""))
    print("smallest weight changes that flip the winner:")
    for f in rep["weight_flips"][:5]:
        print("   %-18s %.2f -> %.2f (%+.2f): %s wins" % (f["criterion"], f["weight_now"], f["weight_at_flip"], f["change"], f["new_winner"]))
    if not rep["weight_flips"]:
        print("   none: no single weight change between 0 and 1 flips it")
    print("guessed scores that could flip the winner (%d guessed cells in total):" % rep["guess_cells"])
    for f in rep["guess_flips"][:5]:
        print("   %s / %s  %.1f -> %.1f (%+.1f): %s wins" % (f["option"], f["criterion"], f["value_now"], f["value_at_flip"], f["change"], f["new_winner"]))
    if not rep["guess_flips"]:
        print("   none within the scale")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
