#!/usr/bin/env python3
"""Compare CueSheet timestamps with strongest band-limited peaks in final audio.
This measures offsets, not acoustic event identity. Criteria: median absolute
 offset < one frame and maximum < two frames. Default band 50:250 Hz, search
window -60:120 ms; use a narrower window for closely spaced cues.
"""
from __future__ import annotations
import json
import math
import subprocess
import sys
from result_contract import CheckArgumentParser, CheckRunnerError, check, result, emit, error_detail

try:
    import numpy as np
    from scipy import signal
    _dependency_error = None
except Exception as exc:
    np = signal = None
    _dependency_error = type(exc).__name__


def load(path, sr=48000):
    if np is None:
        raise CheckRunnerError("numpy/scipy unavailable", stage="dependencies", code=_dependency_error)
    if not isinstance(sr, (int, float)) or not math.isfinite(sr) or sr <= 0:
        raise CheckRunnerError("Sample rate must be positive", stage="input")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckRunnerError("Audio decoder could not run", stage="decode", code=type(exc).__name__) from exc
    if proc.returncode:
        raise CheckRunnerError("Audio decoder failed", stage="decode", returncode=proc.returncode,
                               stderr_tail=proc.stderr.decode(errors="replace")[-800:])
    raw = proc.stdout
    if not raw or len(raw) % 4:
        raise CheckRunnerError("Decoded audio is empty or has invalid float32 alignment", stage="decode")
    samples = np.frombuffer(raw, np.float32)
    if not np.isfinite(samples).all():
        raise CheckRunnerError("Decoded audio contains nonfinite samples", stage="decode")
    return samples, sr


def main(argv=None):
    checks, errors, observations, rows = [], [], {}, []
    selected = []
    args = None
    fatal = False
    try:
        ap = CheckArgumentParser(description=__doc__)
        ap.add_argument("--cues", required=True)
        ap.add_argument("--audio", required=True)
        ap.add_argument("--kinds", default="step")
        ap.add_argument("--band", default="50:250")
        ap.add_argument("--fps", type=float, default=24.0)
        ap.add_argument("--window", default="-60:120")
        ap.add_argument("--json", action="store_true")
        args = ap.parse_args(argv)
        lo, hi = map(float, args.band.split(":"))
        w0, w1 = map(float, args.window.split(":"))
        if not all(math.isfinite(v) for v in (lo, hi, w0, w1, args.fps)) or not (0 < lo < hi < 24000) or w0 >= w1 or args.fps <= 0:
            raise CheckRunnerError("Require positive fps, 0 < band low < high < 24000, and an ordered finite window", stage="input")
        with open(args.cues, encoding="utf-8") as fh:
            cues = json.load(fh)
        if not isinstance(cues, list):
            raise CheckRunnerError("CueSheet must be a list", stage="input")
        for index, cue in enumerate(cues):
            if not isinstance(cue, dict) or not isinstance(cue.get("kind"), str):
                raise CheckRunnerError(f"Malformed cue {index}: kind required", stage="input")
            for key in ("t", "frame"):
                value = cue.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise CheckRunnerError(f"Malformed cue {index}: finite nonnegative {key} required", stage="input")
        kinds = set(args.kinds.split(","))
        selected = [c for c in cues if c["kind"] in kinds]
        if not selected:
            checks.append(check("cue-selection", "not-applicable", "No cues of the selected kinds", observed=sorted(kinds)))
            if not args.json:
                print("no cues of kinds", kinds)
        else:
            if _dependency_error:
                raise CheckRunnerError("numpy/scipy unavailable", stage="dependencies", code=_dependency_error)
            x, sr = load(args.audio)
            sos = signal.butter(4, (lo, hi), btype="bandpass", fs=sr, output="sos")
            env = np.abs(signal.sosfilt(sos, x))
            hop = sr // 200
            if len(env) < hop:
                raise CheckRunnerError("Decoded audio shorter than one 5 ms analysis bin", stage="decode")
            e = env[:len(env) // hop * hop].reshape(-1, hop).max(1)
            frame_ms = 1000.0 / args.fps
            offsets = []
            for index, cue in enumerate(selected):
                i = int(cue["t"] * 200)
                j0, j1 = max(0, i + int(w0 / 5)), min(len(e), i + int(w1 / 5))
                row = {"index": index, "cue": cue, "window_ms": [w0, w1]}
                if j1 <= j0:
                    row.update(status="partial", reason="Search window outside decoded duration")
                    checks.append(check(f"cue-{index}", "partial", row["reason"], observed=row))
                    rows.append(row)
                    continue
                pk = j0 + int(np.argmax(e[j0:j1]))
                offset = (pk - i) * 5.0
                offsets.append(offset)
                # This individual maximum criterion is already a hard defect even if later work fails.
                state = "failed" if abs(offset) >= 2 * frame_ms else "completed"
                row.update(status=state, reason="Strongest band-limited window peak measured", offset_ms=offset)
                rows.append(row)
                checks.append(check(f"cue-{index}", state, row["reason"], observed=row,
                                    expected={"absolute_offset_ms_less_than": 2 * frame_ms}))
                if not args.json:
                    print(f"{cue['kind']:>10} f{cue['frame']:7.1f}  onset offset {offset:+6.0f} ms")
            if offsets:
                med = float(np.median(np.abs(offsets)))
                mx = float(np.max(np.abs(offsets)))
                ok = med < frame_ms and mx < 2 * frame_ms
                observations.update(median_absolute_offset_ms=med, max_absolute_offset_ms=mx, frame_ms=frame_ms)
                checks.append(check("offset-thresholds", "completed" if ok else "failed",
                                    "Thresholds evaluated over inspected cues only", observed=observations,
                                    expected={"median_less_than": frame_ms, "maximum_less_than": 2 * frame_ms}))
                if not args.json:
                    label = "PASS" if ok and len(offsets) == len(selected) else "inspected cues within thresholds; coverage incomplete" if ok else "CHECK"
                    print(f"\n{len(offsets)}/{len(selected)} cues checked; median |offset| {med:.0f} ms, max {mx:.0f} ms (1 frame = {frame_ms:.0f} ms) -> {label}")
    except Exception as exc:
        fatal = True
        errors.append(error_detail(exc))
        for index in range(len(rows), len(selected)):
            rows.append({"index": index, "cue": selected[index], "status": "partial", "reason": "Not attempted after runner error"})
            checks.append(check(f"cue-{index}", "partial", "Not attempted after runner error", observed=rows[-1]))
    receipt = result("sync_check", checks, errors, fatal=fatal,
                     meaning="Window-peak offset test; no claim of acoustic event identity or full audiovisual quality.",
                     cues=rows, cue_coverage={"selected": len(selected), "inspected": sum("offset_ms" in r for r in rows),
                                              "skipped": sum("offset_ms" not in r for r in rows)}, observations=observations)
    if args is not None and args.json:
        print(json.dumps(receipt, indent=1, allow_nan=False))
    return emit(receipt)


if __name__ == "__main__":
    sys.exit(main())
