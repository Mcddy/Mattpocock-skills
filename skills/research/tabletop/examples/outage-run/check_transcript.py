#!/usr/bin/env python3
"""Check the example transcript against its scenario and its play log. Standard library only.

Usage:
  python check_transcript.py TRANSCRIPT.md SCENARIO.json LOG.jsonl --scripts DIR

  --scripts  the skill's scripts folder, which holds session_log.py and scenario_check.py

It is a review aid for this one example, not part of the skill. A transcript is prose, so most of
it cannot be checked by a program. These five things can, and each is a way a facilitator could
quietly cheat or slip:

  1. every state block printed in the transcript is exactly what session_log.py computes from the
     log up to that point (blocks are matched to the log by their "log lines: n" count)
  2. no hidden fact's text appears before the line that finds it ("found: H2 ...")
  3. no menu lists an action that depends on a hidden fact not yet found
  4. after every "RULE RUn (outcome)" line, the next line is that rule outcome's text, word for word
  5. the player's inputs in the transcript are the inputs in the log, in the same order

Exit codes: 0 all five hold. 1 one does not. 2 bad arguments or unreadable input.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main(argv):
    args, scripts, it = [], None, iter(argv)
    for a in it:
        if a == "--scripts":
            scripts = next(it, None)
        elif a.startswith("-"):
            print("check_transcript: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 3 or not scripts or not (Path(scripts) / "session_log.py").is_file():
        print("check_transcript: give TRANSCRIPT.md SCENARIO.json LOG.jsonl and --scripts DIR (the folder holding session_log.py)", file=sys.stderr)
        return 2
    sys.path.insert(0, scripts)
    import scenario_check as sc
    import session_log as sl
    try:
        text = Path(args[0]).read_bytes().decode("utf-8")
        scenario = sc.load(args[1])
        log = sl.read_log(args[2])
    except (OSError, UnicodeDecodeError, sc.Unreadable) as e:
        print("check_transcript: %s" % e, file=sys.stderr)
        return 2
    lines = text.splitlines()
    problems = []

    # 1. state blocks
    blocks = 0
    for i, line in enumerate(lines):
        if line.startswith("STATE v1 |"):
            block = "\n".join(lines[i:i + 8])
            m = re.search(r"log lines: (\d+)", block)
            if not m:
                problems.append("line %d: a state block does not end with its log line count" % (i + 1))
                continue
            engine = sl.Engine(scenario)
            for n, entry in log[:int(m.group(1))]:
                engine.feed(n, entry)
            blocks += 1
            if engine.state_block() != block:
                problems.append("line %d: the state block is not what the log gives after %s line(s)" % (i + 1, m.group(1)))

    # 2 and 3. hidden facts and gated actions, read in order
    hidden = {h["id"]: h["text"] for h in scenario.get("hidden_facts", [])}
    gated = {a["label"]: a.get("needs_fact", []) for a in scenario["actions"] if a.get("needs_fact")}
    found = set()
    for i, line in enumerate(lines):
        m = re.match(r"found: (\w+)  (.*)", line)
        if m:
            if hidden.get(m.group(1)) != m.group(2):
                problems.append("line %d: 'found: %s' does not give that fact's text as written in the scenario" % (i + 1, m.group(1)))
            found.add(m.group(1))
            continue
        for hid, htext in hidden.items():
            if hid not in found and htext[:40] in line:
                problems.append("line %d: the text of hidden fact %s appears before it was found" % (i + 1, hid))
        if re.match(r"\d+  ", line):
            for label, needs in gated.items():
                if label in line and any(h not in found for h in needs):
                    problems.append("line %d: the menu lists '%s', which depends on %s, not yet found" % (i + 1, label[:40], ", ".join(needs)))

    # 4. rule text
    rules = {r["id"]: r for r in scenario.get("rules", [])}
    cited = 0
    for i, line in enumerate(lines):
        m = re.search(r"RULE (\w+) \((then|late|unmet)\)$", line)
        if m:
            cited += 1
            want = rules.get(m.group(1), {}).get(m.group(2), {}).get("text")
            if want is None or i + 1 >= len(lines) or lines[i + 1] != want:
                problems.append("line %d: the line after 'RULE %s (%s)' is not that outcome's text" % (i + 1, m.group(1), m.group(2)))

    # 5. inputs
    typed = [l[2:] for l in lines if l.startswith("> ")]
    logged = [e["input"] for _, e in log if e.get("input")]
    if typed != logged:
        problems.append("the player's inputs in the transcript (%d) are not the inputs in the log (%d), in order" % (len(typed), len(logged)))

    for p in problems:
        print("  FAIL  " + p)
    print("check_transcript: %d state block(s) compared, %d hidden fact(s) found in order, %d rule citation(s), %d player input(s). RESULT: %s."
          % (blocks, len(found), cited, len(typed), "FAIL, %d problem(s)" % len(problems) if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
