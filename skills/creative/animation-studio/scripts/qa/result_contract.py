"""Shared, standard-library-only receipts. Completion is not aesthetic approval."""
from __future__ import annotations

import argparse
import json
import sys

STATUSES = ("completed", "partial", "not-applicable", "failed", "runner-error")
EXITS = {"completed": 0, "not-applicable": 0, "failed": 2, "partial": 3, "runner-error": 1}


class CheckRunnerError(Exception):
    def __init__(self, message, *, stage="execution", code="unavailable", **evidence):
        super().__init__(message)
        self.detail = {"stage": stage, "code": code, "message": str(message), **evidence}


class CheckArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CheckRunnerError(message, stage="arguments", code="invalid-arguments")


def check(id, status, reason, **evidence):
    if status not in STATUSES:
        raise ValueError("Unknown check status: " + str(status))
    return {"id": id, "status": status, "reason": reason, **evidence}


def error_detail(exc, stage="execution"):
    if isinstance(exc, CheckRunnerError):
        return dict(exc.detail)
    return {"stage": stage, "code": type(exc).__name__, "message": str(exc)[:800]}


def result(tool, checks, errors=None, *, fatal=False, meaning=None, **extra):
    """Known hard failures dominate late runner errors; observations are never discarded."""
    errors = list(errors or [])
    states = [c["status"] for c in checks]
    hard = [c for c in checks if c["status"] == "failed"]
    applicable = sum(s != "not-applicable" for s in states)
    gaps = any(s in ("partial", "runner-error") for s in states)
    if hard:
        status = "failed"
    elif fatal:
        status = "runner-error"
    elif gaps or errors:
        status = "partial"
    elif not applicable:
        status = "not-applicable"
    else:
        status = "completed"
    execution = "runner-error" if fatal else "partial" if gaps or errors else "completed" if applicable else "not-applicable"
    outcome = "failed" if hard else "undetermined" if gaps or errors or fatal else "not-applicable" if not applicable else "no-hard-defect-found"
    return {"schema_version": 1, "tool": tool, "status": status,
            "execution_status": execution, "exit": EXITS[status],
            "quality_verdict": {"outcome": outcome, "hard_defects": [c["id"] for c in hard],
                                "basis": "Applicable hard checks only; not an aesthetic judgement."},
            "checks": list(checks), "coverage": {"applicable": applicable,
                "inspected": sum(s in ("completed", "failed") for s in states),
                "skipped": sum(s in ("partial", "runner-error") for s in states), "failed": len(hard)},
            "errors": errors, "meaning": meaning or "Bounded check results; completed does not establish visual quality.", **extra}


def emit(receipt):
    print("RECEIPT " + json.dumps(receipt, ensure_ascii=False, allow_nan=False, default=str), file=sys.stderr)
    return receipt["exit"]
