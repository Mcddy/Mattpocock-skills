#!/usr/bin/env python3
"""Static scan of a third-party skill, plugin, MCP server or prompt pack. Standard library only.

Reads files. Never imports, runs or installs anything from the target.

Usage:
  python scan.py <dir> [--json] [--skip <glob> ...]

Exit code: 0 = no findings above low, 1 = review needed, 2 = reject-level finding.
A clean scan is not proof of safety. It only means none of these rules matched.
"""
import fnmatch
import json
import re
import sys
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".zsh", ".ps1", ".bat",
            ".cmd", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".html", ".css", ".rb", ".go", ".rs", ".php", ""}
MAX_BYTES = 2_000_000

RULES = [
    # id, severity, regex, meaning
    ("concealment", "critical", r"(do not|don't|never|without)\s+(tell|telling|mention|mentioning|inform|informing|reveal|revealing|notify|notifying)[^.\n]{0,40}\b(user|human|operator)\b", "tells the agent to hide something from the user"),
    ("override", "critical", r"(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|system)\s+(instructions?|rules?|prompts?|messages?)", "tries to override the agent's instructions"),
    ("pipe-to-shell", "critical", r"(curl|wget|iwr|invoke-webrequest)[^\n|;]{0,200}\|\s*(sudo\s+)?(ba|z)?sh\b|\|\s*iex\b|invoke-expression", "downloads and runs remote code"),
    ("encoded-command", "critical", r"powershell[^\n]{0,80}-(enc|encodedcommand)\b|base64\s+(-d|--decode)[^\n|]{0,80}\|\s*(ba|z)?sh\b", "runs an encoded command"),
    ("secret-path", "high", r"(~|\$HOME|%USERPROFILE%)?[/\\]?\.(ssh|aws|gnupg|kube|docker)[/\\]|id_(rsa|ed25519)|\.npmrc|\.netrc|\.pypirc|credentials\.json|\.env\b|keychain|wallet\.dat", "touches credential or key locations"),
    ("secret-env", "high", r"(API[_-]?KEY|SECRET[_-]?KEY|ACCESS[_-]?TOKEN|AUTH[_-]?TOKEN|PRIVATE[_-]?KEY|PASSWORD)\b", "reads or names secrets"),
    ("agent-config", "high", r"(\.claude|\.codex|\.cursor|\.gemini)[/\\]|settings(\.local)?\.json|CLAUDE\.md|AGENTS\.md|mcp(_servers)?\.json", "reads or writes agent configuration"),
    ("permission-bypass", "high", r"dangerously|--no-sandbox|skip[- ]?permissions?|bypass(ing)?\s+(the\s+)?(sandbox|approval|permission)|--yolo|approval[_-]?policy\s*[:=]\s*[\"']?never", "asks to weaken sandbox or approvals"),
    ("dynamic-exec", "high", r"\beval\s*\(|\bexec\s*\(|os\.system\s*\(|shell\s*=\s*True|child_process|new\s+Function\s*\(|subprocess\.(run|Popen|call|check_output)", "runs commands or dynamic code"),
    ("network", "medium", r"\b(curl|wget)\s|invoke-webrequest|requests\.(get|post|put)|urllib\.request|http\.client|fetch\s*\(|XMLHttpRequest|socket\.socket|net\.connect", "makes network calls"),
    ("install-time", "medium", r"\"(pre|post)install\"\s*:|\bnpx\s+\S|npm\s+(i|install)\s+-g|pip\s+install\b|setup\.py", "runs or installs code at install time"),
    ("persistence", "medium", r"crontab|schtasks|launchctl|systemctl\s+enable|autostart|\\CurrentVersion\\Run|\.bashrc|\.zshrc|profile\.ps1", "sets up something that keeps running"),
    ("destructive", "medium", r"rm\s+-rf\s+[/~$]|del\s+/[sq]|format\s+[a-z]:|git\s+push\s+--force|drop\s+table", "can destroy data"),
]
COMPILED = [(i, s, re.compile(r, re.I), m) for i, s, r, m in RULES]
URL_RE = re.compile(r"https?://([A-Za-z0-9.-]+)")
B64_RE = re.compile(r"[A-Za-z0-9+/=]{200,}")
ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0}


def hidden_unicode(line):
    hits = []
    for ch in line:
        cp = ord(ch)
        if 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
            hits.append(("bidi-override", "critical", "text direction override character U+%04X" % cp))
        elif 0xE0000 <= cp <= 0xE007F:
            hits.append(("tag-character", "critical", "invisible tag character U+%05X" % cp))
        elif cp in (0x200B, 0x200C, 0x200D, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0xFEFF):
            hits.append(("zero-width", "high", "zero-width character U+%04X" % cp))
    return hits[:3]


def scan(root, skips):
    root = Path(root)
    findings, hosts, unchecked, files = [], set(), [], 0
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        if any(fnmatch.fnmatch(rel, g) for g in skips) or "/.git/" in "/" + rel:
            continue
        if f.suffix.lower() not in TEXT_EXT or f.stat().st_size > MAX_BYTES:
            unchecked.append(rel)
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            unchecked.append(rel)
            continue
        files += 1
        per_file = set()
        for n, line in enumerate(text.splitlines(), 1):
            for h in URL_RE.findall(line):
                hosts.add(h.lower())
            for rid, sev, rx, meaning in COMPILED:
                if rx.search(line):
                    findings.append({"file": rel, "line": n, "rule": rid, "severity": sev, "meaning": meaning, "text": line.strip()[:160]})
                    per_file.add(rid)
            for rid, sev, meaning in hidden_unicode(line):
                findings.append({"file": rel, "line": n, "rule": rid, "severity": sev, "meaning": meaning, "text": "(invisible character on this line)"})
            if B64_RE.search(line):
                findings.append({"file": rel, "line": n, "rule": "encoded-blob", "severity": "high", "meaning": "long encoded blob that cannot be read by eye", "text": line.strip()[:60] + "..."})
        if "network" in per_file and ({"secret-path", "secret-env"} & per_file):
            findings.append({"file": rel, "line": 0, "rule": "possible-exfiltration", "severity": "critical", "meaning": "the same file reads secrets and makes network calls", "text": ""})
    top = max((ORDER[x["severity"]] for x in findings), default=0)
    verdict = {3: "reject", 2: "review: install only with edits", 1: "review: read the flagged lines", 0: "no rule matched"}[top]
    return {"target": str(root), "files_scanned": files, "unchecked_files": unchecked, "hosts": sorted(hosts),
            "verdict": verdict, "level": top, "findings": findings}


def main(argv):
    skips = []
    while "--skip" in argv:
        i = argv.index("--skip")
        skips.append(argv[i + 1])
        del argv[i:i + 2]
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    rep = scan(args[0], skips)
    if as_json:
        print(json.dumps(rep, indent=1, ensure_ascii=True))
    else:
        print("target:  %s" % rep["target"])
        print("verdict: %s   (files scanned %d, not readable as text %d)" % (rep["verdict"], rep["files_scanned"], len(rep["unchecked_files"])))
        if rep["hosts"]:
            print("hosts named: " + ", ".join(rep["hosts"]))
        for sev in ("critical", "high", "medium"):
            rows = [x for x in rep["findings"] if x["severity"] == sev]
            if rows:
                print("%s (%d):" % (sev.upper(), len(rows)))
                for x in rows[:40]:
                    print("   %s:%s  [%s] %s  | %s" % (x["file"], x["line"], x["rule"], x["meaning"], x["text"]))
        if rep["unchecked_files"]:
            print("not checked: " + ", ".join(rep["unchecked_files"][:20]))
    return {3: 2, 2: 1, 1: 1, 0: 0}[rep["level"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
