#!/usr/bin/env python3
"""Put picker data into the picker engine and write one self-contained HTML file. Standard library only.

Usage:
  python build_picker.py PICKER.json --out PICKER.html [--engine assets/picker.html] [--renderers FILE.js] [--json]

What it does: validates the data with validate_picker.py (the same rules, the same messages), then
copies the engine and replaces the block between its PICKER-DATA markers with the data as strict
JSON. For kind "custom", --renderers names a JavaScript file that defines
    const RENDERERS = {"option-id": function (root, ctx) { ... }, ...};
which replaces the block between the PICKER-RENDERERS markers.

What it enforces (exit 1, nothing written):
  - every error validate_picker.py reports
  - kind "custom" without --renderers, or --renderers that lacks a function for an option
  - a renderers file that is not plain ASCII, that closes the script element, or that reaches for
    the network (fetch, XMLHttpRequest, WebSocket, import, a URL with a scheme)
It never writes over the engine or over the data file, and it changes neither.

What it cannot tell: whether the picker looks right. Open it, and run test_picker.py on it.

Exit codes: 0 written. 1 the data or the renderers were refused. 2 bad arguments or unreadable input.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_picker as vp  # noqa: E402
import picker_result as pr  # noqa: E402


FLAGS = {"--json"}
VALUES = {"--out", "--engine", "--renderers"}
R_START, R_END = "/* PICKER-RENDERERS:START */", "/* PICKER-RENDERERS:END */"
NETWORK = re.compile(r"\bfetch\s*\(|XMLHttpRequest|WebSocket|EventSource|\bimport\s*\(|\bimportScripts\b|sendBeacon|[a-z][a-z0-9+.-]*://", re.I)


def emit(lines):
    try:
        sys.stdout.write("\n".join(lines).encode("ascii", "replace").decode("ascii") + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        pass


def main(argv):
    flags, opts, args, it = set(), {}, [], iter(argv)
    for a in it:
        if a in FLAGS:
            flags.add(a)
        elif a in VALUES:
            v = next(it, None)
            if v is None or v.startswith("--") or not v.strip():
                print("build_picker: %s needs a value" % a, file=sys.stderr)
                return 2
            opts[a] = v
        elif a.startswith("--"):
            print("build_picker: unknown option " + a, file=sys.stderr)
            return 2
        else:
            args.append(a)
    if len(args) != 1 or "--out" not in opts:
        print(__doc__)
        return 2
    data_path, out_path = Path(args[0]), Path(opts["--out"])
    engine_path = Path(opts["--engine"]) if "--engine" in opts else Path(__file__).resolve().parent.parent / "assets" / "picker.html"
    try:
        data = vp.read_data(data_path)
        engine = engine_path.read_bytes().decode("utf-8-sig")
    except vp.Bad as e:
        print("build_picker: " + str(e), file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as e:
        print("build_picker: cannot read the engine %s (%s)" % (engine_path, str(e)[:60]), file=sys.stderr)
        return 2
    if out_path.resolve() in (engine_path.resolve(), data_path.resolve()):
        print("build_picker: --out must not be the engine or the data file", file=sys.stderr)
        return 2
    for marker in (vp.DATA_START, vp.DATA_END, R_START, R_END):
        if engine.count(marker) != 1:
            print("build_picker: the engine must contain %s exactly once" % marker, file=sys.stderr)
            return 2
    errors, advisories, _ = vp.check(data)
    pr.observe_failures(errors, 'Picker data failed validation before renderer/output work.')
    renderers = None
    if isinstance(data, dict) and data.get("kind") == "custom":
        if "--renderers" not in opts:
            errors.append("kind custom needs --renderers FILE.js with one function per option")
        else:
            try:
                raw = Path(opts["--renderers"]).read_bytes()
            except OSError as e:
                print("build_picker: cannot read %s: %s" % (opts["--renderers"], e.strerror or e), file=sys.stderr)
                return 2
            if any(b > 126 or (b < 32 and b not in (9, 10, 13)) for b in raw):
                errors.append("the renderers file must be plain ASCII")
            else:
                renderers = raw.decode("ascii").strip()
                if not re.search(r"\bconst\s+RENDERERS\s*=", renderers):
                    errors.append("the renderers file must define: const RENDERERS = {...};")
                if "</script" in renderers.lower() or "<!--" in renderers:
                    errors.append("the renderers file must not contain a closing script tag or an HTML comment opener")
                m = NETWORK.search(renderers)
                if m:
                    errors.append("the renderers file reaches outside the page (%r). A picker makes no requests" % m.group(0))
                for o in data.get("options", []):
                    if isinstance(o, dict) and isinstance(o.get("id"), str) and not re.search(r"[\"']%s[\"']\s*:" % re.escape(o["id"]), renderers):
                        errors.append("the renderers file has no entry for option %r" % o["id"])
    elif "--renderers" in opts:
        errors.append("--renderers is only for kind custom; the built-in kinds draw themselves")
    if errors:
        pr.result('failed', {'written': None, 'errors': errors, 'advisories': advisories}, 'Picker data or renderers refused; no output was written.')
        if "--json" in flags:
            emit([json.dumps({"tool": "build_picker", "written": None, "errors": errors, "advisories": advisories}, indent=1, ensure_ascii=True)])
        else:
            emit(["build_picker: %s was refused. Nothing was written." % data_path.name] + ["  ERROR     " + m for m in errors])
        return 1
    blob = json.dumps(data, ensure_ascii=True, indent=1).replace("<", chr(92) + "u003c")
    a, b = engine.index(vp.DATA_START) + len(vp.DATA_START), engine.index(vp.DATA_END)
    html = engine[:a] + "\nconst PICKER = " + blob + ";\n" + engine[b:]
    if renderers is not None:
        a, b = html.index(R_START) + len(R_START), html.index(R_END)
        html = html[:a] + "\n" + renderers + "\n" + html[b:]
    title = str(data.get("title", "Sample picker")).replace("&", "&amp;").replace("<", "&lt;")
    html = html.replace("<title>Sample picker</title>", "<title>%s</title>" % title, 1)
    try:
        out_path.write_text(html, encoding="utf-8")
    except OSError as e:
        print("build_picker: cannot write %s: %s" % (out_path, e.strerror or e), file=sys.stderr)
        return 2
    readback = vp.read_data(out_path)
    expected_written_bytes = html.replace("\n", os.linesep).encode("utf-8")
    actual_written_bytes = out_path.read_bytes()
    exact_bytes = actual_written_bytes == expected_written_bytes
    semantic_match = readback == data
    pr.result('completed' if exact_bytes and semantic_match else 'failed', {'written': str(out_path), 'bytes_identical': exact_bytes, 'written_bytes': len(actual_written_bytes), 'newline_policy': 'Preserved Python text-write platform newline translation', 'picker_payload_equal': semantic_match, 'picker_id': readback.get('id') if isinstance(readback, dict) else None, 'version': readback.get('version', 1) if isinstance(readback, dict) else None, 'kind': readback.get('kind') if isinstance(readback, dict) else None, 'option_ids': [o['id'] for o in data['options']], 'runtime': {'status': 'not-applicable', 'reason': 'Building/readback does not drive or judge the picker.'}}, 'Output bytes and strict embedded PICKER payload read back.' )
    if not exact_bytes or not semantic_match:
        print('build_picker: output did not match the intended picker', file=sys.stderr)
        return 1
    if "--json" in flags:
        emit([json.dumps({"tool": "build_picker", "written": str(out_path), "bytes": len(html.encode("utf-8")), "options": len(data["options"]),
                          "kind": data["kind"], "errors": [], "advisories": advisories}, indent=1, ensure_ascii=True)])
        return 0
    L = ["build_picker: wrote %s (%s bytes): %d option(s), kind %s" % (out_path, format(len(html.encode("utf-8")), ","), len(data["options"]), data["kind"])]
    L += ["  ADVISORY  " + m for m in advisories]
    L.append("Open it and look, then run test_picker.py on it. Building it is not checking it.")
    emit(L)
    return 0


if __name__ == "__main__":
    sys.exit(pr.run("build_picker", main, sys.argv[1:]))
