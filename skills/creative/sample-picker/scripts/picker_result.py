"""Additive stderr-only five-category receipts; legacy stdout and documented exits remain."""
import json
import sys

VERSION = "1.2.0"
STATES = {"completed", "partial", "not-applicable", "failed", "runner-error"}
DATA = {}
KNOWN_FAILURES = []


def observe_failures(errors, reason):
    if errors:
        KNOWN_FAILURES.extend(str(e) for e in errors)
        DATA["failure_reason"] = reason


def result(status, coverage, reason):
    if status not in STATES:
        raise ValueError("unknown result category: " + status)
    DATA.update(status=status, coverage=coverage, reason=reason)
    if status == "failed":
        observe_failures(coverage.get("errors") or coverage.get("failed") or [reason], reason)


def run(tool, main, argv):
    DATA.clear()
    KNOWN_FAILURES.clear()
    DATA.update(tool=tool, revision=VERSION, phase={"validate_picker": "validation", "build_picker": "build", "parse_choice": "choice", "test_picker": "browser-test"}[tool], coverage={})
    interruption = None
    try:
        code = main(list(argv))
        code = 0 if code is None else code
    except Exception as e:
        interruption = {"reason": str(e)[:240], "type": type(e).__name__}
        # Explicit test_picker NOT RUN still returns 3 from main; unexpected Python errors retain exit 1.
        code = 1
        DATA.update(status="failed" if KNOWN_FAILURES else "runner-error", reason="Execution stopped; inspect the interruption and any earlier criterion failure.")
    default = {0: "completed", 1: "failed", 2: "runner-error", 3: "runner-error"}.get(code, "runner-error")
    DATA.setdefault("status", default)
    DATA.setdefault("reason", "Invalid/unreadable command or input." if code == 2 else "Runner unavailable or stopped." if code == 3 else "Legacy operation finished; inspect coverage.")
    if KNOWN_FAILURES:
        if DATA["status"] != "failed" or code in (2, 3):
            interruption = interruption or {"reason": DATA["reason"], "legacy_exit": code}
        DATA["status"] = "failed"
        DATA["known_failures"] = list(dict.fromkeys(KNOWN_FAILURES))
    if interruption:
        DATA["execution_interruption"] = interruption
    DATA.update(exit=code, exit_policy="legacy: 0 normal success, 1 refusal/test failure, 2 input/setup; test_picker also uses 3 NOT RUN. Read status and coverage, not exit alone.")
    try:
        print("RECEIPT " + json.dumps(DATA, ensure_ascii=True, default=str), file=sys.stderr)
    except OSError:
        DATA["receipt_delivery"] = {"status": "runner-error", "reason": "stderr receipt could not be delivered"}
        return code if code else 1
    return code
