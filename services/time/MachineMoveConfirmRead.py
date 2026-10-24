#!/usr/bin/env python3
"""MACHINE M1p: operator phrase validation *rehearsal*, read only.

A fresh one-shot Sway read revalidates the proposed move, and the typed phrase
must match that exact action. This adapter never produces an approval ticket,
token, persistent grant, journal write or window movement. It cannot activate
the M1k executor and is NOT equivalent to trusted live authorization.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineMoveReviewRead import (
    _candidate_request, review_candidate, ReviewError, MAX_REQUEST_BYTES,
)
from MachineMoveApproval import ApprovalError
from MachineWindowMovePilot import MoveRefused

MAX_CONFIRMATION_LENGTH = 256


class ConfirmationError(ValueError):
    pass


def required_phrase(action):
    if not isinstance(action, dict) or set(action) != {
            "app_id", "con_id", "from_workspace", "to_workspace"}:
        raise ConfirmationError("INVALID ACTION")
    words = (action["app_id"], action["from_workspace"], action["to_workspace"])
    if any(not isinstance(x, str) or not x or
           any(ord(ch) < 32 or ord(ch) == 127 for ch in x) for x in words):
        raise ConfirmationError("INVALID ACTION FIELDS")
    if type(action["con_id"]) is not int or action["con_id"] < 1:
        raise ConfirmationError("INVALID CONTAINER")
    return "MOVE " + words[0] + " FROM " + words[1] + " TO " + words[2]


def confirm_preview(payload, *, read_runner):
    if not isinstance(payload, dict) or set(payload) != {
            "checkpoint_id", "document", "candidate", "confirmation_text"}:
        raise ConfirmationError("INVALID REQUEST")
    entered = payload["confirmation_text"]
    if (not isinstance(entered, str)
            or not 1 <= len(entered) <= MAX_CONFIRMATION_LENGTH
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in entered)):
        raise ConfirmationError("INVALID CONFIRMATION")
    proposed = {key: payload[key]
                for key in ("checkpoint_id", "document", "candidate")}
    # Revalidate against the current compositor; a prior review is never
    # an executable capability or trusted proof of current placement.
    validated = review_candidate(proposed, read_runner=read_runner)
    actual = validated["action"]
    phrase = required_phrase(actual)
    if entered != phrase:
        raise ConfirmationError("EXACT CONFIRMATION REQUIRED")
    return {
        "kind": "machine-m1p-confirmation-dry-run",
        "status": "phrase_validated_read_only",
        "read_only": True,
        "executable": False,
        "approval_issued": False,
        "confirmation_persisted": False,
        "requires_new_approval_to_execute": True,
        "action": actual,
    }


def main(*, read_runner=subprocess.run):
    if sys.argv[1:] != ["confirm-preview"]:
        print(json.dumps({"status": "error", "reason": "UNSUPPORTED ACTION"}))
        return 2
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
        print(json.dumps({"status": "error", "reason": "INVALID REQUEST"}))
        return 1
    try:
        payload = json.loads(raw)
        result = confirm_preview(payload, read_runner=read_runner)
    except (ConfirmationError, ApprovalError, MoveRefused, ReviewError,
            ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError):
        print(json.dumps({"status": "error", "reason": "CONFIRMATION NOT VALIDATED"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
