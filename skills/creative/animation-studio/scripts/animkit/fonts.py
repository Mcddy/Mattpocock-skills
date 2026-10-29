"""Real typefaces in any sandbox (instead of the default Arial/Courier look).

fetch("Fraunces", 700)  -> TTF path. Online: npm @fontsource package -> TTF (needs npm,
                           fontTools, brotli). Offline or on failure: falls back to
                           best_available() for the closest role.
best_available("display") -> the best installed family for a role, via fontconfig.
                           Roles: display, text, serif, mono, rounded, condensed.
path_for("Family", weight) -> installed file for a family (fc-match), or None.

Check each face's licence before commercial delivery (most open faces are SIL OFL).
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tarfile
import tempfile

CACHE = os.path.expanduser(os.environ.get("ANIMKIT_FONT_CACHE", "~/.cache/animkit-fonts"))

# Ordered preferences per role: distinctive, well-made open faces first, generic last.
# Deliberately avoids defaulting to the faces that read as templated AI design
# (Inter everywhere, Space Grotesk + Instrument Serif); choose per project, not per habit.
ROLE_PREFS = {
    "display": ["Fraunces", "Bricolage Grotesque", "Manrope", "Work Sans", "Archivo", "Cabin",
                "Clear Sans", "Cantarell", "Andika", "Arimo", "Noto Sans", "DejaVu Sans"],
    "text": ["Source Sans 3", "IBM Plex Sans", "Work Sans", "Inter", "Cabin", "Clear Sans", "Cantarell", "Arimo",
             "Noto Sans", "Liberation Sans", "DejaVu Sans"],
    "serif": ["Fraunces", "Source Serif 4", "IBM Plex Serif", "Charis SIL", "Crimson Pro", "Bitstream Charter",
              "C059", "Caladea", "Noto Serif", "Liberation Serif", "DejaVu Serif"],
    "mono": ["JetBrains Mono", "IBM Plex Mono", "Source Code Pro", "Cousine", "Noto Sans Mono",
             "Liberation Mono", "DejaVu Sans Mono"],
    "rounded": ["Nunito", "Comfortaa", "Varela Round", "Quicksand", "Andika", "Cabin", "DejaVu Sans"],
    "condensed": ["Barlow Condensed", "Oswald", "Roboto Condensed", "Archivo Narrow", "Liberation Sans Narrow",
                  "DejaVu Sans Condensed", "DejaVu Sans"],
}


def _online(host="registry.npmjs.org", port=443, timeout=3.0) -> bool:
    """Quick reachability probe so offline sandboxes don't wait on npm timeouts."""
    import os as _os
    import socket
    if _os.environ.get("HTTPS_PROXY") or _os.environ.get("https_proxy"):
        return True
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def _installed_families():
    if not shutil.which("fc-list"):
        return set()
    out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    fams = set()
    for line in out.splitlines():
        for f in line.split(","):
            if f.strip():
                fams.add(f.strip())
    return fams


def path_for(family: str, weight: int = 400) -> str | None:
    if not shutil.which("fc-match"):
        return None
    q = f"{family}:weight={int(weight / 4.0)}"
    p = subprocess.run(["fc-match", "-f", "%{family}|%{file}", q], capture_output=True, text=True).stdout
    if "|" not in p:
        return None
    fam, path = p.split("|", 1)
    return path if family.lower() in fam.lower() else None


def best_available(role: str = "text") -> str | None:
    fams = _installed_families()
    lower = {f.lower(): f for f in fams}
    for want in ROLE_PREFS.get(role, ROLE_PREFS["text"]):
        if want.lower() in lower:
            return lower[want.lower()]
    return None


def fetch(family: str, weight: int = 400, style: str = "normal", subset: str = "latin",
          role_fallback: str = "display") -> str | None:
    """TTF path for family/weight. Tries cache, installed fonts, npm; then the best installed face."""
    slug = family.lower().replace(" ", "-")
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, f"{slug}-{subset}-{weight}-{style}.ttf")
    if os.path.exists(out):
        return out
    local = path_for(family, weight)
    if local:
        return local
    if shutil.which("npm") and _online():
        try:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run(["npm", "pack", f"@fontsource/{slug}", "--silent"], cwd=td, check=True,
                               capture_output=True, timeout=45)
                tgz = glob.glob(os.path.join(td, "*.tgz"))[0]
                with tarfile.open(tgz) as tf:
                    tf.extractall(td, filter="data")
                cands = glob.glob(os.path.join(td, "package", "files", f"{slug}-{subset}-{weight}-{style}.woff2"))
                if cands:
                    from fontTools.ttLib import TTFont
                    f = TTFont(cands[0])
                    f.flavor = None
                    f.save(out)
                    return out
        except Exception:  # noqa: BLE001 - offline, missing package, missing fontTools
            pass
    fam = best_available(role_fallback)
    return path_for(fam, weight) if fam else None
