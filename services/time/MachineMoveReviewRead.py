#!/usr/bin/env python3
"""MACHINE M1o: one-shot read-only UI bridge for move / interruption review.

Only subcommands: preview, pending. No approve/execute/journal mutations.
Review confirms a candidate is still viable, then discards its in-memory
review challenge. An operator approval token is NEVER created.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineMoveApproval import MoveApprovalGate, ApprovalError
from MachineMoveJournal import MoveJournal, JournalError, suggested_path
from MachineMoveReconciliation import inspect_pending, ReconciliationError
from MachineWindowMovePilot import MoveRefused

MAX_REQUEST_BYTES = 262144
MAX_VISIBLE_PENDING = 40


class ReviewError(ValueError):
    pass


def _candidate_request(payload):
    if not isinstance(payload, dict) or set(payload) != {
            "checkpoint_id", "document", "candidate"}:
        raise ReviewError("INVALID PREVIEW REQUEST")
    candidate = payload["candidate"]
    required = {"app_id", "status", "reason", "target_workspace",
                "current_workspace", "live_con_id"}
    if not isinstance(candidate, dict) or set(candidate) != required:
        raise ReviewError("INVALID CANDIDATE")
    if candidate["status"] != "candidate":
        raise ReviewError("NOT AN ACTION CANDIDATE")
    return {
        "intent": "single-existing-window-workspace-move", "approved": False,
        "app_id": candidate["app_id"], "con_id": candidate["live_con_id"],
        "from_workspace": candidate["current_workspace"],
        "to_workspace": candidate["target_workspace"],
    }


def review_candidate(payload, *, read_runner):
    request = _candidate_request(payload)
    gate = MoveApprovalGate()
    result = gate.review(payload["document"], request,
                         checkpoint_id=payload["checkpoint_id"],
                         read_runner=read_runner)
    # Crucial boundary: never return confirmation text or a review ID that
    # could be mistaken for a still-live ticket. No approval is ever issued.
    return {
        "kind": "machine-m1o-action-review",
        "status": "review_only",
        "read_only": True,
        "executable": False,
        "approval_issued": False,
        "requires_fresh_revalidation": True,
        "action": result["action"],
    }


def review_interruptions(*, journal, read_runner):
    outcome = inspect_pending(journal, read_runner=read_runner)
    if not outcome.get("read_only") or outcome.get("executable") is not False:
        raise ReviewError("INVALID RECOVERY RESPONSE")
    records = outcome.get("items", [])
    if len(records) > MAX_VISIBLE_PENDING:
        raise ReviewError("PENDING LIMIT EXCEEDED")
    # Allowlisted public view, with no automatic reconciliation side effects.
    items = []
    for record in records:
        before = record["before"]
        items.append({
            "operation_id": record["operation_id"],
            "durable_phase": record["durable_phase"],
            "advisory_state": record["advisory_state"],
            "app_id": before["app_id"],
            "from_workspace": before["workspace"],
            "to_workspace": before["target_workspace"],
            "requires_manual_review": True,
        })
    return {
        "kind": "machine-m1o-interruption-review",
        "status": "pending_review" if items else "clear",
        "read_only": True,
        "executable": False,
        "approval_issued": False,
        "items": items,
        "no_automatic_retry": True,
        "no_automatic_undo": True,
    }


def main(argv=None, *, read_runner=subprocess.run, journal_factory=MoveJournal):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in ("preview", "pending"):
        print(json.dumps({"status": "error", "reason": "UNSUPPORTED READ ACTION"}))
        return 2
    try:
        if args[0] == "preview":
            raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
            if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
                raise ReviewError("INVALID REQUEST")
            data = json.loads(raw)
            out = review_candidate(data, read_runner=read_runner)
        else:
            journal = journal_factory(suggested_path())
            out = review_interruptions(journal=journal, read_runner=read_runner)
    except (ReviewError, ApprovalError, JournalError, ReconciliationError,
            MoveRefused, ValueError, TypeError, KeyError, OSError,
            subprocess.SubprocessError):
        print(json.dumps({"status": "error", "reason": "REVIEW UNAVAILABLE"}))
        return 1
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
