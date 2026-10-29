#!/usr/bin/env python3
"""Lint skill folders against the open Agent Skills spec. Standard library only.

Usage:
  python skill_lint.py <skill-dir> [<skill-dir> ...] [--json] [--house]
  python skill_lint.py --root <folder-of-skill-dirs> [--json] [--house]

Exit code 1 if any ERROR is found, else 0.
--house adds the owner's house rule: no em dashes anywhere in the skill text.
"""
import json
import re
import sys
from pathlib import Path

SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REF_RE = re.compile(r"(?<![\w/.-])((?:scripts|references|assets|evals)/[\w./-]+\.[A-Za-z0-9]+)")


def split_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


def parse_frontmatter(fm_lines):
    """Minimal YAML reader: top-level 'key: value' pairs, indented lines attach to the last key."""
    data, last = {}, None
    for raw in fm_lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            last = m.group(1)
            val = m.group(2).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            data[last] = val
        elif last is not None:
            data[last] = (data[last] + " " + raw.strip()).strip()
    return data


def lint_skill(skill_dir, house=False):
    skill_dir = Path(skill_dir)
    out = {"skill": skill_dir.name, "path": str(skill_dir), "errors": [], "warnings": []}
    err, warn = out["errors"].append, out["warnings"].append
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        err("SKILL.md is missing")
        return out
    text = md.read_text(encoding="utf-8", errors="replace")
    fm_lines, body = split_frontmatter(text)
    if fm_lines is None:
        err("no YAML frontmatter block at the top of SKILL.md")
        return out
    fm = parse_frontmatter(fm_lines)

    name = fm.get("name", "")
    if not name:
        err("frontmatter: name is missing")
    else:
        if len(name) > 64:
            err("name is %d characters; the limit is 64" % len(name))
        if not NAME_RE.match(name):
            err("name must be lower-case letters, digits and single hyphens, not starting or ending with a hyphen")
        if name != skill_dir.name:
            err("name '%s' does not match the directory name '%s'" % (name, skill_dir.name))

    desc = fm.get("description", "")
    out["description_chars"] = len(desc)
    if not desc:
        err("frontmatter: description is missing or empty")
    elif len(desc) > 1024:
        err("description is %d characters; the limit is 1024" % len(desc))
    elif not re.search(r"\buse (this )?(when|whenever)\b", desc, re.I):
        warn("description does not say when to use the skill (no 'Use when ...')")

    if len(fm.get("compatibility", "")) > 500:
        err("compatibility is over 500 characters")
    extra = sorted(set(fm) - SPEC_KEYS)
    if extra:
        warn("frontmatter keys outside the open spec (host-specific, may be ignored or rejected elsewhere): " + ", ".join(extra))
    if "allowed-tools" in fm:
        warn("allowed-tools is experimental in the spec; support differs between hosts")

    body_lines = body.count("\n") + 1
    out["body_lines"] = body_lines
    out["body_tokens_est"] = len(body) // 4
    if body_lines > 500:
        warn("SKILL.md body is %d lines; the spec recommends under 500" % body_lines)
    if len(body) // 4 > 5000:
        warn("SKILL.md body is about %d tokens; the spec recommends under 5000" % (len(body) // 4))

    for ref in sorted(set(REF_RE.findall(body))):
        if not (skill_dir / ref).exists():
            err("SKILL.md refers to '%s', which does not exist" % ref)
        if ref.count("/") > 1:
            warn("reference '%s' is nested more than one level below the skill root" % ref)

    if house:
        for f in sorted(skill_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in {".md", ".json", ".py", ".txt", ".html"}:
                if "evals/files" in f.as_posix():
                    continue
                t = f.read_text(encoding="utf-8", errors="replace")
                n = t.count("\u2014")
                if n:
                    err("house rule: %d em dash(es) in %s" % (n, f.relative_to(skill_dir).as_posix()))
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    as_json, house = "--json" in argv, "--house" in argv
    dirs = []
    if "--root" in argv:
        root = Path(argv[argv.index("--root") + 1])
        args = [a for a in args if Path(a) != root]
        dirs = sorted(p.parent for p in root.glob("*/SKILL.md"))
    dirs += [Path(a) for a in args]
    if not dirs:
        print(__doc__)
        return 2
    results = [lint_skill(d, house) for d in dirs]
    if as_json:
        print(json.dumps(results, indent=1))
    else:
        for r in results:
            state = "ERROR" if r["errors"] else ("WARN" if r["warnings"] else "OK")
            print("%-5s %-16s description %s chars, body %s lines" % (state, r["skill"], r.get("description_chars", "?"), r.get("body_lines", "?")))
            for e in r["errors"]:
                print("        error: " + e)
            for w in r["warnings"]:
                print("        warn:  " + w)
    return 1 if any(r["errors"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
