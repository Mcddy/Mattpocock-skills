#!/usr/bin/env python3
"""Inventory one or more folders of skills. Standard library only. Reads files, changes nothing.

Usage:
  python inventory.py <root> [<root> ...] [--json out.json]

Finds every SKILL.md under each root and reports:
  duplicates   same body under two or more paths
  forks        same name, different body
  collisions   a quoted trigger phrase claimed by two or more differently named skills
  broad        descriptions with catch-all wording
  oversize     descriptions over 1024 characters, bodies over 500 lines
  undescribed  skills with no description
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BROAD = re.compile(r"\b(any (request|task|time|situation)|always|constantly|proactively|every (request|task|situation)|everything)\b", re.I)
QUOTED = re.compile(r"[\"\u201C]([^\"\u201D]{4,80})[\"\u201D]")


def read_skill(md):
    text = md.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    fm, body = {}, text
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                last = None
                for raw in lines[1:i]:
                    m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", raw)
                    if m and not raw.startswith((" ", "\t")):
                        last = m.group(1)
                        fm[last] = m.group(2).strip().strip("\"'")
                    elif last and raw.strip():
                        fm[last] = (fm[last] + " " + raw.strip()).strip()
                body = "\n".join(lines[i + 1:])
                break
    norm = re.sub(r"\s+", " ", body).strip()
    desc = fm.get("description", "")
    return {
        "name": fm.get("name", md.parent.name),
        "dir": md.parent.name,
        "path": str(md.parent),
        "description_chars": len(desc),
        "description": desc,
        "body_lines": body.count("\n") + 1,
        "body_sha256": hashlib.sha256(norm.encode("utf-8")).hexdigest(),
        "frontmatter_keys": sorted(fm),
        "has_scripts": (md.parent / "scripts").is_dir(),
        "phrases": sorted({p.lower().strip(" .,") for p in QUOTED.findall(desc)}),
        "broad_terms": sorted({m.group(0).lower() for m in BROAD.finditer(desc)}),
    }


def main(argv):
    out_path = None
    if "--json" in argv:
        out_path = argv[argv.index("--json") + 1]
        argv = [a for a in argv if a not in ("--json", out_path)]
    roots = [Path(a) for a in argv]
    if not roots:
        print(__doc__)
        return 2
    skills = []
    for root in roots:
        for md in sorted(root.rglob("SKILL.md")):
            if "node_modules" in md.parts:
                continue
            skills.append(read_skill(md))

    by_hash, by_name, by_phrase = defaultdict(list), defaultdict(list), defaultdict(set)
    for s in skills:
        by_hash[s["body_sha256"]].append(s["path"])
        by_name[s["name"]].append(s)
        for p in s["phrases"]:
            by_phrase[p].add(s["name"])

    report = {
        "roots": [str(r) for r in roots],
        "skill_count": len(skills),
        "distinct_names": len(by_name),
        "duplicates": [paths for paths in by_hash.values() if len(paths) > 1],
        "forks": [
            {"name": n, "paths": [x["path"] for x in group]}
            for n, group in sorted(by_name.items())
            if len({x["body_sha256"] for x in group}) > 1
        ],
        "collisions": [
            {"phrase": p, "skills": sorted(names)} for p, names in sorted(by_phrase.items()) if len(names) > 1
        ],
        "broad": [{"name": s["name"], "terms": s["broad_terms"]} for s in skills if s["broad_terms"]],
        "oversize": [
            {"name": s["name"], "description_chars": s["description_chars"], "body_lines": s["body_lines"]}
            for s in skills
            if s["description_chars"] > 1024 or s["body_lines"] > 500
        ],
        "undescribed": sorted({s["name"] for s in skills if not s["description"]}),
        "skills": [{k: v for k, v in s.items() if k != "description"} for s in skills],
    }
    if out_path:
        Path(out_path).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("skills found: %d (%d distinct names)" % (report["skill_count"], report["distinct_names"]))
    print("true duplicates (same body): %d group(s)" % len(report["duplicates"]))
    for g in report["duplicates"]:
        print("   " + "  ==  ".join(g))
    print("forks (same name, different body): %d" % len(report["forks"]))
    for f in report["forks"]:
        print("   %s: %s" % (f["name"], "  |  ".join(f["paths"])))
    print("trigger phrases claimed by 2+ skills: %d" % len(report["collisions"]))
    for c in report["collisions"]:
        print("   \"%s\": %s" % (c["phrase"], ", ".join(c["skills"])))
    print("descriptions with catch-all wording: %d" % len(report["broad"]))
    for b in report["broad"]:
        print("   %s: %s" % (b["name"], ", ".join(b["terms"])))
    print("oversize: %d, undescribed: %d" % (len(report["oversize"]), len(report["undescribed"])))
    if out_path:
        print("full report written to " + out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
