#!/usr/bin/env python3
"""Read-only source candidates and opaque-sRGB contrast, using the standard library.

Results: completed=0, failed=1, partial=3, runner_error=4, not_applicable=5.
Candidate matches remain advisory. Each check emits one stderr RECEIPT; help emits none.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import stat

VERSION = "2026.10.25"
EXIT_CODES = {"completed": 0, "failed": 1, "partial": 3, "runner_error": 4, "not_applicable": 5}


EXTENSIONS = {".html", ".htm", ".css", ".scss", ".sass", ".less",
              ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte"}
EXCLUDED = {".git", ".next", ".nuxt", ".cache", ".venv", "venv",
            "__pycache__", "node_modules", "vendor", "dist", "build",
            "out", "coverage", "target"}
RULES = [
    ("gradient", "preference",
     r"(?:linear|radial|conic)-gradient\s*\(|\bbg-(?:gradient|linear|radial|conic)-[\w-]+",
     "Check the rendered purpose and current brand; this does not identify gradient colours."),
    ("gradient-text", "preference",
     r"\bbg-clip-text\b|(?:-webkit-)?background-clip\s*:\s*text\b",
     "Inspect actual text/background contrast and whether this display treatment fits the brief."),
    ("translucent-blur", "preference",
     r"\bbackdrop-filter\s*:\s*blur\s*\(|\bbackdrop-blur(?:-[\w.\[\]-]+)?",
     "Inspect changing backdrops, fallback and legibility; blur can have a legitimate role."),
    ("scroll-reveal", "preference",
     r"\bwhileInView\b|\bdata-aos\b|\b(?:scroll-reveal|animate-on-scroll)\b",
     "Verify content remains available without motion; a name or observer alone is not a defect."),
    ("cursor-ornament", "preference",
     r"\b(?:cursor-beam|cursor-glow|cursor-trail|pointer-glow)\b",
     "Inspect whether an ambient effect distracts from the task or belongs to the creative brief."),
    ("hover-opacity", "verification",
     r"\bhover:opacity-(?:0|[1-8]\d|90)\b|:hover\s*\{[^}]{0,1200}?\bopacity\s*:\s*(?:0?\.\d+|0)\b",
     "Measure the hover state's legibility; the match is not a computed accessibility failure."),
    ("focus-removal", "verification",
     r"\boutline\s*:\s*(?:none|0)(?:\s|;|}|$)|\b(?:focus:|focus-visible:)?outline-none\b",
     "Check for an effective replacement focus indicator before diagnosing lost keyboard focus."),
    ("font-signal", "dependency",
     r"\bfont-family\s*:[^;\n]*(?:\bInter\b|Space Grotesk|Instrument Serif)",
     "Inspect typography roles and accepted brand; a font name alone proves no design defect."),
    ("icon-library", "dependency",
     r"\blucide-(?:react|vue|svelte|angular)\b|\blucide[_-]icons?\b",
     "Inspect decorative saturation and accessible labels; do not remove a library merely for existing."),
    ("generic-copy", "preference",
     r"\b(?:unlock your (?:potential|productivity)|seamless(?:ly)?|revolutioni[sz]e|next[- ]gen(?:eration)?|supercharge|game[- ]changing|AI[- ]powered insights)\b",
     "Confirm this is visible product copy, not a comment/example or a genuine domain term."),
    ("heading-punctuation", "preference",
     r"<h[1-6]\b[^>]{0,300}>[^<\n]{0,180}\u2014",
     "Review visible heading punctuation against the brief; punctuation cannot establish authorship."),
    ("heading-emoji", "preference",
     r"<h[1-6]\b[^>]{0,300}>[^<\n]{0,180}[\U0001F300-\U0001FAFF\u2600-\u27BF]",
     "Inspect whether emoji is subject content or redundant heading decoration."),
]
COMPILED = [(key, basis, re.compile(pattern, re.IGNORECASE), review)
            for key, basis, pattern, review in RULES]


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Use a positive integer.")
    return number


def hex_colour(value):
    match = re.fullmatch(r"#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value)
    if not match:
        raise argparse.ArgumentTypeError(
            "Use an opaque three- or six-digit hex colour. Alpha and CSS expressions are unsupported.")
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(char * 2 for char in digits)
    return "#" + digits.upper()


def luminance(colour):
    channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
              for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(foreground, background, role):
    a, b = luminance(foreground), luminance(background)
    ratio = (max(a, b) + 0.05) / (min(a, b) + 0.05)
    threshold = 4.5 if role == "normal" else 3.0
    return {
        "mode": "opaque-srgb-colour-pair",
        "foreground": foreground,
        "background": background,
        "role": role,
        "ratio": ratio,
        "threshold": threshold,
        "passes_pair_threshold": ratio >= threshold,
        "limitations": [
            "This compares one opaque colour pair, not a rendered interface or full WCAG conformance.",
            "The selected role's eligibility, exceptions and actual compositing require inspection.",
            "Pass/fail uses the unrounded ratio.",
        ],
    }


def is_link_or_reparse(path):
    """Do not traverse Windows junctions/reparse points or symbolic links."""
    return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0)
                                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def scan(project, max_bytes, limit):
    root = Path(project).expanduser()
    if is_link_or_reparse(root):
        raise ValueError("The scan root must not be a symlink, junction or reparse point.")
    if not root.exists():
        raise ValueError("The scan root does not exist.")
    if not (root.is_dir() or root.is_file()):
        raise ValueError("The scan root must be a directory or regular source file.")
    root = root.resolve()
    base = root if root.is_dir() else root.parent
    skipped = []
    paths = []
    excluded_directories = 0
    unsupported_files = 0
    excluded_links = []
    if root.is_file():
        if root.suffix.lower() not in EXTENSIONS:
            unsupported_files = 1
        else:
            paths = [root]
    else:
        def walk_error(error):
            skipped.append({"path": str(error.filename), "reason": "directory-read-error"})
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
            keep = []
            for name in sorted(dirs):
                child = Path(folder) / name
                if name.lower() in EXCLUDED:
                    excluded_directories += 1
                    continue
                try:
                    linked = is_link_or_reparse(child)
                except OSError:
                    skipped.append({"path": str(child.relative_to(base)), "reason": "directory-stat-error"})
                    continue
                if linked:
                    excluded_directories += 1
                    if linked:
                        excluded_links.append(str(child.relative_to(base)))
                else:
                    keep.append(name)
            dirs[:] = keep
            paths.extend(Path(folder) / name for name in sorted(files)
                         if Path(name).suffix.lower() in EXTENSIONS)
            unsupported_files += sum(Path(name).suffix.lower() not in EXTENSIONS for name in files)
    candidates = []
    total = 0
    scanned = 0
    for path in sorted(paths):
        relative = str(path.relative_to(base))
        try:
            if is_link_or_reparse(path):
                skipped.append({"path": relative, "reason": "link-or-reparse-point"})
                excluded_links.append(relative)
                continue
            if not path.is_file():
                skipped.append({"path": relative, "reason": "not-regular-file"})
                continue
            if path.stat().st_size > max_bytes:
                skipped.append({"path": relative, "reason": "size-limit"})
                continue
            data = path.read_bytes()
            if len(data) > max_bytes:
                skipped.append({"path": relative, "reason": "size-limit"})
                continue
            if b"\x00" in data:
                skipped.append({"path": relative, "reason": "binary"})
                continue
            source = data.decode("utf-8-sig")
        except (OSError, UnicodeError):
            skipped.append({"path": relative, "reason": "read-or-encoding-error"})
            continue
        scanned += 1
        for key, basis, pattern, review in COMPILED:
            for match in pattern.finditer(source):
                total += 1
                if len(candidates) < limit:
                    candidates.append({
                        "kind": "candidate",
                        "rule": key,
                        "basis": basis,
                        "path": relative,
                        "line": source.count("\n", 0, match.start()) + 1,
                        "sample": re.sub(r"\s+", " ", match.group(0))[:180],
                        "review": review,
                    })
    return {
        "mode": "read-only-web-source-triage",
        "root": str(root),
        "files_scanned": scanned,
        "excluded_directories": excluded_directories,
        "skipped": skipped,
        "candidates_total": total,
        "candidates_returned": len(candidates),
        "truncated": total > len(candidates),
        "candidates": candidates,
        "coverage": {
            "supported_inputs_discovered": len(paths),
            "files_scanned": scanned,
            "applicable_skipped": [item for item in skipped if item["reason"] != "link-or-reparse-point"],
            "scope_exclusions": {
                "unsupported_formats": unsupported_files,
                "excluded_directories": excluded_directories,
                "links_or_reparse_points": excluded_links,
            },
            "returned_candidates_truncated": total > len(candidates),
        },
        "limitations": [
            "Lexical matches can include comments, examples and justified uses; inspect the actual UI.",
            "This does not parse layout, execute code, measure rendered contrast or identify AI authorship.",
            "Unsupported formats, dependencies, build output, symlinks and oversized files are not inspected.",
            "Zero candidates is not visual approval or accessibility certification.",
        ],
    }


def emit(result, output_format):
    if output_format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["mode"] == "opaque-srgb-colour-pair":
        verdict = "PASS" if result["passes_pair_threshold"] else "FAIL"
        print(f"{verdict} colour pair: ratio {result['ratio']!r}:1; "
              f"{result['role']} threshold {result['threshold']}:1")
        print("One opaque pair only; inspect compositing, role eligibility and exceptions.")
    else:
        print(f"Read-only triage: {result['files_scanned']} source files; "
              f"{result['candidates_total']} candidates; {len(result['skipped'])} skipped.")
        for item in result["candidates"]:
            print(f"{item['path']}:{item['line']} [{item['rule']}; {item['basis']}] "
                  f"{item['sample']}")
            print("  Review: " + item["review"])
        if result["truncated"]:
            print("Output truncated; raise --limit for additional candidates.")
        print("Candidates are not defects or authorship evidence. Zero matches is not approval.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    triage = commands.add_parser("scan", help="Read supported web sources; never modify them.")
    triage.add_argument("project")
    triage.add_argument("--max-bytes", type=positive_int, default=1_000_000)
    triage.add_argument("--limit", type=positive_int, default=500)
    triage.add_argument("--format", choices=("json", "text"), default="json")
    pair = commands.add_parser("contrast", help="Compare an opaque hex colour pair.")
    pair.add_argument("foreground", type=hex_colour)
    pair.add_argument("background", type=hex_colour)
    pair.add_argument("--role", choices=("normal", "large", "non-text"), default="normal")
    pair.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    if args.command == "contrast":
        result = contrast(args.foreground, args.background, args.role)
        status = "completed" if result["passes_pair_threshold"] else "failed"
        result["coverage"] = {"pairs_requested": 1, "pairs_checked": 1}
        reason = "Requested opaque colour-pair threshold was evaluated."
    else:
        result = scan(args.project, args.max_bytes, args.limit)
        coverage = result["coverage"]
        if coverage["applicable_skipped"] or result["truncated"]:
            status = "partial"
            reason = "Applicable input or returned-candidate coverage is incomplete."
        elif not result["files_scanned"]:
            status = "not_applicable"
            reason = "No supported, in-scope regular web source inputs were available."
        else:
            status = "completed"
            reason = "The declared source scope was scanned; candidates are advisory, not approval."
    result.update({"status": status, "exit": EXIT_CODES[status], "status_reason": reason})
    emit(result, args.format)
    receipt(result)
    return EXIT_CODES[status]


def receipt(result):
    """Report bounded semantic coverage without changing existing stdout fields."""
    record = {"tool": "ui_review", "version": VERSION, "status": result["status"],
              "exit": result["exit"], "mode": result["mode"],
              "reason": result.get("status_reason"), "coverage": result.get("coverage", {})}
    for key in ("root", "foreground", "background", "role", "ratio", "threshold",
                "passes_pair_threshold", "files_scanned", "candidates_total", "candidates_returned", "error"):
        if key in result:
            record[key] = result[key]
    print("RECEIPT " + json.dumps(record, ensure_ascii=True), file=sys.stderr)


def run():
    try:
        return main()
    except SystemExit as error:
        if not error.code:  # argparse help
            return 0
        message = "Input arguments were rejected; see the parser diagnostic."
    except Exception as error:
        message = str(error) or type(error).__name__
    result = {"mode": "runner-error", "status": "runner_error", "exit": 4,
              "status_reason": "The tool could not complete the requested check.",
              "error": message, "coverage": {"check_completed": False}}
    try:
        print(json.dumps(result, ensure_ascii=True))
    except (BrokenPipeError, OSError):
        pass
    receipt(result)
    return 4


if __name__ == "__main__":
    sys.exit(run())
