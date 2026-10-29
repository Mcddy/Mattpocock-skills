#!/usr/bin/env python3
"""Inventory local animation capabilities. Default is offline; --probe-network tests
only a direct TCP connection to pypi.org:443, not installation or service access.
Negative capability findings are inventory results, not rendering success.
"""
from __future__ import annotations
import importlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from qa.result_contract import CheckArgumentParser, CheckRunnerError, check, result, emit, error_detail


def has(mod):
    try:
        m = importlib.import_module(mod)
        return getattr(m, "__version__", True) or True
    except Exception:
        return None


def network(host="pypi.org", port=443, timeout=3):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def fonts(limit=400):
    if not shutil.which("fc-list"):
        raise CheckRunnerError("fc-list unavailable; installed font count unknown", stage="fonts")
    try:
        proc = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckRunnerError("Font inventory could not run", stage="fonts", code=type(exc).__name__) from exc
    if proc.returncode:
        raise CheckRunnerError("Font inventory command failed", stage="fonts", returncode=proc.returncode)
    fams = sorted({f.split(",")[0].strip() for f in proc.stdout.splitlines() if f.strip()})
    return fams[:limit]


def main(argv=None):
    checks, errors, details = [], [], {}
    info = {}
    try:
        ap = CheckArgumentParser(description=__doc__)
        ap.add_argument("--json", action="store_true")
        ap.add_argument("--probe-network", action="store_true")
        args = ap.parse_args(argv)
        info = {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count()}
        for mod in ("numpy", "scipy", "PIL", "matplotlib", "cv2", "skia", "bpy", "fontTools"):
            try:
                loaded = importlib.import_module(mod)
                value = loaded.app.version_string if mod == "bpy" else getattr(loaded, "__version__", True) or True
                info[mod] = value
                checks.append(check(mod, "completed", "Import succeeded", observed=value))
            except ModuleNotFoundError as exc:
                info[mod] = None
                # Missing requested module is a known absence; a missing transitive dependency is not.
                absent = exc.name in (mod, mod.split('.')[0])
                status = "completed" if absent else "partial"
                details[mod] = {"status": status, "reason": "not installed" if absent else "import could not complete"}
                checks.append(check(mod, status, details[mod]["reason"], observed=None))
            except Exception as exc:
                info[mod] = None
                details[mod] = {"status": "partial", "reason": type(exc).__name__}
                checks.append(check(mod, "partial", "Import could not be inspected", evidence=details[mod]))
        for key, binary in (("ffmpeg", "ffmpeg"), ("blender_binary", "blender"), ("npm", "npm")):
            info[key] = shutil.which(binary)
            checks.append(check(key, "completed", "Executable lookup completed", observed=info[key]))
        probe = {"requested": args.probe_network, "status": "not-applicable", "reason": "not requested",
                 "endpoint": None, "reachable": None,
                 "proxy_configured": bool(os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"))}
        info["network"] = False
        if args.probe_network:
            probe.update(endpoint="pypi.org:443", reachable=network(), status="completed",
                         reason="Direct TCP reachability only; proxy reachability and package installation untested")
            info["network"] = probe["reachable"]
        info["network_probe"] = probe
        checks.append(check("network", probe["status"], probe["reason"], observed=probe["reachable"]))
        info["ram_gb"] = None
        try:
            with open("/proc/meminfo", encoding="utf-8") as fh:
                info["ram_gb"] = round(int(fh.readline().split()[1]) / 1e6, 1)
        except (OSError, ValueError, IndexError):
            details["ram_gb"] = {"status": "not-applicable", "reason": "Linux total-memory source unavailable"}
        try:
            canvas = importlib.import_module("animkit.canvas")
            info["canvas_backend"] = canvas.BACKEND
            checks.append(check("canvas", "completed", "Canvas backend imported", observed=canvas.BACKEND))
        except Exception as exc:
            info["canvas_backend"] = "unavailable: " + type(exc).__name__
            details["canvas"] = {"status": "partial", "reason": "Backend could not be inspected"}
            checks.append(check("canvas", "partial", details["canvas"]["reason"]))
        try:
            fams = fonts()
            info["fonts_installed"] = len(fams)
            checks.append(check("font-inventory", "completed", "fc-list inventory completed (capped at 400)", observed=len(fams)))
        except Exception as exc:
            info["fonts_installed"] = None
            details["fonts_installed"] = error_detail(exc, "fonts")
            checks.append(check("font-inventory", "partial", "Installed font count unknown", evidence=details["fonts_installed"]))
        info["font_picks"] = {}
        try:
            font_module = importlib.import_module("animkit.fonts")
            info["font_picks"] = {role: font_module.best_available(role) for role in font_module.ROLE_PREFS}
            checks.append(check("font-picks", "completed", "Font helper completed", observed=info["font_picks"]))
        except Exception as exc:
            details["font_picks"] = error_detail(exc, "font-picks")
            checks.append(check("font-picks", "partial", "Font helper unavailable", evidence=details["font_picks"]))
        route = {}
        backend = str(info["canvas_backend"]).lower()
        if backend == "skia" and info["skia"] and info["numpy"] and info["PIL"]:
            route["2d"] = "animkit/skia"
        elif backend == "soft" and info["numpy"] and info["PIL"]:
            route["2d"] = "animkit/soft (numpy+PIL fallback)"
        else:
            route["2d"] = "unavailable: required imports or a recognised canvas backend did not succeed"
        route["3d"] = ("Blender via scripts/blender/scene_kit.py" if info["bpy"] or info["blender_binary"] else
                       "no Blender here: use an available 2-D route or hand off source for a separately verified host")
        route["sound"] = "animkit.audio + ffmpeg loudnorm" if info["ffmpeg"] and info["scipy"] and info["numpy"] else "MISSING ffmpeg/scipy/numpy"
        route["fonts"] = "offline: animkit.fonts.best_available(role)" if info["font_picks"] else "unavailable: font helper did not complete"
        info["memory_available_mb"] = None
        workers = max(1, min(4, (info["cpus"] or 1)))
        sized = False
        try:
            timeline = importlib.import_module("animkit.timeline")
            mem = timeline._mem_available()
            if not mem or mem <= 0:
                raise CheckRunnerError("Free-memory sizing unavailable", stage="workers")
            info["memory_available_mb"] = mem // 2**20
            workers = timeline.auto_workers(1920, 1080)
            sized = True
            checks.append(check("workers", "completed", "Worker sizing and free memory inspected", observed=workers))
        except Exception as exc:
            details["render_workers"] = error_detail(exc, "workers")
            checks.append(check("workers", "partial", "CPU-only fallback; free-memory sizing unverified", observed=workers))
        route["render_workers"] = (f"{workers} at 1080p (sized to free memory; leave render(workers=) unset)" if sized else
                                   f"{workers} CPU-only suggestion; memory sizing unknown; verify before rendering")
        route["long_runs"] = "if tool calls time out, render in chunks (--frames a:b) and join with animkit.timeline.concat"
        info.update(route=route, capability_details=details)
        receipt = result("env_check", checks, errors, meaning="Capability inventory only; completed does not establish render readiness.")
        info.update(receipt)
        if args.json:
            print(json.dumps(info, indent=1, default=str, allow_nan=False))
        else:
            for key, value in info.items():
                if key not in ("checks", "errors", "route", "font_picks"):
                    print(f"{key:16s} {value}")
            print("\nfont picks:")
            for key, value in info["font_picks"].items():
                print(f"  {key:10s} {value}")
            print("\nroute:")
            for key, value in route.items():
                print(f"  {key:14s} {value}")
        return emit(receipt)
    except Exception as exc:
        receipt = result("env_check", checks, [error_detail(exc)], fatal=True, observations=info)
        return emit(receipt)


if __name__ == "__main__":
    sys.exit(main())
