#!/usr/bin/env python3
"""MACHINE M1q: one explicitly confirmed existing-window move.

Development bridge, not an automatic restore service. Only an operator action
supplying the exact current phrase can enter this path; a fresh Sway preflight,
one-use approval and durable journal are mandatory. No process launches, focus
changes, automatic retries, undo or checkpoint rewrites.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineCheckpointStore import load as load_checkpoint, validate
from MachineMoveApproval import MoveApprovalGate
from MachineMoveJournal import MoveJournal, suggested_path
from MachineMoveReviewRead import _candidate_request
from MachineWindowMovePilot import execute_one

MAX_REQUEST_BYTES = 262144
FIELDS = frozenset(("checkpoint_id", "document", "candidate", "confirmation_text"))


class ApplyError(ValueError):
    pass


def apply_one(payload, *, read_runner, command_runner,
              checkpoint_loader=load_checkpoint, journal_factory=MoveJournal):
    """Injectable seam; no compositor commands before checked confirmation."""
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        raise ApplyError("INVALID APPLY REQUEST")
    checkpoint_id = payload["checkpoint_id"]
    if not isinstance(checkpoint_id, str) or len(checkpoint_id) != 36:
        raise ApplyError("INVALID CHECKPOINT ID")
    confirmation = payload["confirmation_text"]
    if (not isinstance(confirmation, str) or not 1 <= len(confirmation) <= 256
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in confirmation)):
        raise ApplyError("INVALID CONFIRMATION")

    # Never execute against a caller-supplied unsaved/altered checkpoint.
    stored = checkpoint_loader(checkpoint_id)
    if (not isinstance(stored, dict) or stored.get("status") != "loaded"
            or not isinstance(stored.get("checkpoint"), dict)
            or stored["checkpoint"].get("id") != checkpoint_id
            or validate(payload["document"]) != stored.get("document")):
        raise ApplyError("CHECKPOINT NOT CURRENTLY STORED")
    document = stored["document"]
    request = _candidate_request({
        "checkpoint_id": checkpoint_id,
        "document": document,
        "candidate": payload["candidate"],
    })
    gate = MoveApprovalGate()
    review = gate.review(document, request, checkpoint_id=checkpoint_id,
                         read_runner=read_runner)
    if confirmation != review["confirmation_text"]:
        raise ApplyError("EXACT CURRENT ACTION PHRASE REQUIRED")

    # Approval lives only in this process and is bound to this exact action.
    grant = gate.approve(
        review_id=review["review_id"], checkpoint_id=checkpoint_id,
        saved_document=document, request=request,
        confirmation_text=confirmation)
    approved_request = dict(request, approved=True)
    result = execute_one(
        document, approved_request, read_runner=read_runner,
        command_runner=command_runner,
        journal=journal_factory(suggested_path()),
        approval_gate=gate, approval_token=grant["approval_token"],
        checkpoint_id=checkpoint_id)
    return {
        "kind": "machine-m1q-single-window-result",
        "status": result["status"],
        "operation_id": result["operation_id"],
        "app_id": result["before"]["app_id"],
        "from_workspace": result["before"]["workspace"],
        "to_workspace": result["before"]["target_workspace"],
        "observed_workspace": result["observed_workspace"],
        "no_automatic_retry": True,
        "no_automatic_undo": True,
    }


def main(argv=None, *, read_runner=subprocess.run,
         command_runner=subprocess.run,
         checkpoint_loader=load_checkpoint, journal_factory=MoveJournal):
    args = sys.argv[1:] if argv is None else argv
    if args != ["apply-one"]:
        print(json.dumps({"status": "error", "reason": "UNSUPPORTED ACTION"}))
        return 2
    try:
        raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
        if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
            raise ApplyError("INVALID REQUEST SIZE")
        payload = json.loads(raw)
        outcome = apply_one(
            payload, read_runner=read_runner, command_runner=command_runner,
            checkpoint_loader=checkpoint_loader, journal_factory=journal_factory)
    except Exception:
        # Intentionally never echo raw Sway response, private document or token.
        print(json.dumps({"status": "error", "reason": "MOVE REFUSED OR NEEDS REVIEW"}))
        return 1
    print(json.dumps(outcome, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
