#!/usr/bin/env python3
"""Check or refresh the library copies pasted into a single-file tool. Standard library only.

Usage:
  python pocket_embed.py PAGE.html [--lib-dir DIR] [--json]
  python pocket_embed.py PAGE.html --out NEW.html [--lib-dir DIR] [--json]

A page built with this skill carries its libraries inside one script tag, each between a pair of
marker comments:

  /* pocket-embed: pocket-state.js begin */
  ... the file, unchanged ...
  /* pocket-embed: pocket-state.js end */

Without --out this checks, and changes nothing: every marked block must be byte-identical to the
file of that name in the library folder (by default the assets folder beside this scripts folder).
With --out it writes a copy of the page in which each marked block holds the current library
file. PAGE itself is never modified, and --out may not name the same file.

What it enforces (ERROR, exit 1):
  - the page has a pocket-state.js block, and every begin marker has its end marker, once
  - every block names a .js file that exists in the library folder
  - (check mode) each block matches its library file byte for byte
  - no library file contains a closing script tag, which would end the page's script early
What it reports for a person to decide (ADVISORY, exit 0):
  - a form element, or a call to alert, confirm or prompt, in the page: none of them work in a
    sandboxed preview
  - an http or https address in a src or href attribute or a CSS url(): a single-file tool
    should make no outside requests

It cannot tell whether the page uses the library correctly or whether the tool works. Run the
page's own tests for that.

Each check adds one stderr RECEIPT with completed, partial, not-applicable, failed or runner-error
and semantic block/readback coverage, while retaining successful stdout/JSON fields.
Legacy exits: 0 completed; 1 failed marked-library contract; 2 runner-error (invalid input,
unreadable library/page or output/readback failure); 3 partial intended-block coverage.
Exit 5 is reserved for justified whole-check not-applicability; a missing required block fails.
Check-only writing and application runtime are explicitly not-applicable subchecks.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

FLAGS = {"--json"}
VALUES = {"--out", "--lib-dir"}
BEGIN = re.compile(r"/\* pocket-embed: ([A-Za-z0-9._-]+) begin \*/")
REQUIRED = "pocket-state.js"
VERSION = "1.1.0"
CONTRACT = {}


def run(argv):
    CONTRACT.clear()
    CONTRACT.update({"tool": "pocket_embed", "version": VERSION,
                     "reason": "Input could not be read or the requested check could not complete.",
                     "coverage": {"phase": "input", "blocks": []}})
    try:
        code = main(argv)
    except Exception as error:
        code = 2
        CONTRACT.update({"status": "runner-error", "error": str(error)[:240],
                         "error_type": type(error).__name__})
    coverage = CONTRACT.get("coverage", {})
    if "declared_blocks" in coverage:
        observed = {r["name"] for r in coverage["blocks"]}
        coverage["not_reached"] = [name for name in coverage["declared_blocks"] if name not in observed]
    CONTRACT.setdefault("status", {0: "completed", 1: "failed", 2: "runner-error", 3: "partial", 5: "not-applicable"}.get(code, "runner-error"))
    CONTRACT["exit"] = code
    print("RECEIPT " + json.dumps(CONTRACT, ensure_ascii=True), file=sys.stderr)
    return code


def read_text(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        return None, "cannot read %s: %s" % (path, e.strerror or e)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "%s is not valid UTF-8" % path
    if "\x00" in text:
        return None, "%s contains NUL bytes; is it really a text file?" % path
    return text, None


def find_blocks(page):
    """Return (blocks, errors). Each block: name, start and end offsets of the text between markers."""
    blocks, errors, seen = [], [], set()
    for m in BEGIN.finditer(page):
        name = m.group(1)
        if name in seen:
            errors.append("the block for %s is opened more than once" % name)
            continue
        seen.add(name)
        end_marker = "/* pocket-embed: %s end */" % name
        end = page.find(end_marker, m.end())
        if end < 0:
            errors.append("the block for %s has no end marker" % name)
            continue
        if page.count(end_marker) != 1:
            errors.append("the end marker for %s appears more than once" % name)
            continue
        blocks.append({"name": name, "start": m.end(), "end": end})
    if REQUIRED not in seen:
        errors.append("the page has no block for %s (expected the marker comment /* pocket-embed: %s begin */)" % (REQUIRED, REQUIRED))
    return blocks, errors


def advisories_for(page, blocks):
    """Things in the page's own code (outside the library blocks) that a sandboxed preview breaks."""
    own = page
    for b in sorted(blocks, key=lambda x: -x["start"]):
        own = own[:b["start"]] + own[b["end"]:]
    own = re.sub(r"<!--.*?-->", "", own, flags=re.S)
    code = re.sub(r"/\*.*?\*/", "", own, flags=re.S)
    code = re.sub(r"(?m)^\s*//.*$", "", code)
    out = []
    if re.search(r"<form[\s>]", code, re.I):
        out.append("the page has a form element; a sandboxed preview drops form submission. Use type=button controls with click handlers")
    for word in ("alert", "confirm", "prompt"):
        if re.search(r"(?<![\w.$])(?:window\.)?%s\s*\(" % word, code):
            out.append("the page calls %s(); a sandboxed preview blocks it. Ask in the page instead" % word)
    outside = sorted(set(re.findall(r"""(?:src|href)\s*=\s*["'](https?://[^"']+)["']|url\(\s*["']?(https?://[^"')]+)""", code, re.I)))
    for a, b in outside[:5]:
        out.append("the page points at an outside address (%s); a single-file tool should make no outside requests" % (a or b)[:80])
    return out


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or not v.strip() or v.startswith("--"):
                print("pocket_embed: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("pocket_embed: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__)
        return 2
    page_path = Path(args[0])
    CONTRACT["page"] = str(page_path)
    lib_dir = Path(opts["--lib-dir"]) if "--lib-dir" in opts else Path(__file__).resolve().parent.parent / "assets"
    if not lib_dir.is_dir():
        print("pocket_embed: the library folder %s does not exist" % lib_dir, file=sys.stderr)
        return 2
    page, e = read_text(page_path)
    if e:
        print("pocket_embed: " + e, file=sys.stderr)
        return 2
    out_path = Path(opts["--out"]) if "--out" in opts else None
    if out_path is not None and out_path.resolve() == page_path.resolve():
        print("pocket_embed: --out must name a different file; the input page is never modified", file=sys.stderr)
        return 2

    blocks, errors = find_blocks(page)
    report = []
    libs = {}
    CONTRACT.update({"mode": "refresh" if out_path is not None else "check",
                     "coverage": {"phase": "blocks", "declared_blocks": [b["name"] for b in blocks],
                                  "blocks": [], "errors": errors,
                                  "runtime_test": {"status": "not-applicable", "reason": "This checks embedded copies, not application behaviour."},
                                  "write_readback": ({"status": "partial", "reason": "Requested output copy has not yet been written and verified."}
                                                     if out_path is not None else
                                                     {"status": "not-applicable", "reason": "Check mode; no output copy requested."})}})
    for b in blocks:
        lib_path = lib_dir / b["name"]
        if not b["name"].endswith(".js") or not lib_path.is_file():
            errors.append("the block names %s, and there is no such .js file in %s" % (b["name"], lib_dir))
            CONTRACT["coverage"]["blocks"].append({"name": b["name"], "status": "failed", "reason": "No matching declared .js library file."})
            continue
        lib, e = read_text(lib_path)
        if e:
            CONTRACT["coverage"]["blocks"].append({"name": b["name"], "status": "runner-error", "reason": e})
            print("pocket_embed: " + e, file=sys.stderr)
            return 2
        if re.search(r"</script", lib, re.I):
            errors.append("%s contains a closing script tag and cannot be pasted into a page" % b["name"])
            CONTRACT["coverage"]["blocks"].append({"name": b["name"], "status": "failed", "reason": "Library contains a closing script tag."})
            continue
        libs[b["name"]] = lib
        want = "\n" + lib.rstrip("\n") + "\n"
        have = page[b["start"]:b["end"]]
        same = have == want
        CONTRACT["coverage"]["blocks"].append({"name": b["name"], "status": "completed" if same or out_path is not None else "failed",
                                              "input_identical": same, "checked_library": str(lib_path)})
        report.append({"name": b["name"], "identical": same, "library_bytes": len(lib.encode("utf-8")),
                       "library_sha256": hashlib.sha256(lib.encode("utf-8")).hexdigest(),
                       # The block is hashed as it would be saved to a file, with the library's own final newline.
                       "embedded_sha256": hashlib.sha256((have.strip("\n") + ("\n" if lib.endswith("\n") else "")).encode("utf-8")).hexdigest() if have.strip() else None})
        if out_path is None and not same:
            errors.append("the embedded copy of %s %s" % (b["name"], "is empty" if not have.strip() else "differs from the library file"))

    advisories = advisories_for(page, blocks)
    written = None
    if out_path is not None and not errors:
        new = page
        for b in sorted(blocks, key=lambda x: -x["start"]):
            new = new[:b["start"]] + "\n" + libs[b["name"]].rstrip("\n") + "\n" + new[b["end"]:]
        try:
            out_path.write_bytes(new.encode("utf-8"))
            readback = out_path.read_bytes()
        except OSError as e:
            CONTRACT["coverage"]["write_readback"] = {"status": "runner-error", "path": str(out_path), "reason": str(e)}
            print("pocket_embed: cannot write %s: %s" % (out_path, e.strerror or e), file=sys.stderr)
            return 2
        actual_blocks, readback_errors = find_blocks(readback.decode("utf-8"))
        actual = {b["name"]: readback.decode("utf-8")[b["start"]:b["end"]] for b in actual_blocks}
        matching = [name for name, lib in libs.items() if actual.get(name) == "\n" + lib.rstrip("\n") + "\n"]
        identical = readback == new.encode("utf-8") and not readback_errors and len(matching) == len(libs)
        CONTRACT["coverage"]["write_readback"] = {"status": "completed" if identical else "runner-error", "path": str(out_path),
                                                "bytes_identical": readback == new.encode("utf-8"),
                                                "intended_blocks_verified": matching, "errors": readback_errors}
        if not identical:
            print("pocket_embed: the requested output copy failed readback verification", file=sys.stderr)
            return 2
        written = {"path": str(out_path), "bytes": len(new.encode("utf-8"))}

    observed = {r["name"] for r in CONTRACT["coverage"]["blocks"]}
    CONTRACT["coverage"]["not_reached"] = [b["name"] for b in blocks if b["name"] not in observed]
    CONTRACT.update({"status": "failed" if errors else "partial" if CONTRACT["coverage"]["not_reached"] else "completed",
                     "reason": "Marked library copies checked by identity and content; this is no application runtime test.",
                     "advisories": advisories})

    if "--json" in flags:
        text = json.dumps({"page": str(page_path), "blocks": report, "errors": errors, "advisories": advisories, "written": written}, indent=1, ensure_ascii=True)
    else:
        L = ["pocket_embed: %s, %d marked block(s)" % (page_path.name, len(blocks))]
        for r in report:
            if out_path is not None:
                L.append("  BLOCK     %s: %d bytes, sha256 %s" % (r["name"], r["library_bytes"], r["library_sha256"][:16]))
            else:
                L.append("  BLOCK     %s: %s (library %d bytes, sha256 %s)" % (r["name"], "identical to the library file" if r["identical"] else "DIFFERS", r["library_bytes"], r["library_sha256"][:16]))
        L += ["  ERROR     " + m for m in errors]
        L += ["  ADVISORY  " + m for m in advisories]
        if written:
            L.append("  WROTE     %s (%d bytes)" % (written["path"], written["bytes"]))
        L.append("RESULT: %s. %d error(s), %d advisory note(s). This compares pasted library copies; it does not test the tool."
                 % ("FAIL" if errors else "PASS", len(errors), len(advisories)))
        text = "\n".join(L).encode("ascii", "replace").decode("ascii")
    try:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return 1 if errors else 3 if CONTRACT["status"] == "partial" else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
