"""MACHINE M1n: isolated, memory-only, one-action approval lifecycle.

There is NO production operator identity, trusted UI, live Sway runner or CLI.
Approval objects live for one process, one checkpoint and one exact move only.
Their tokens are never written to the SQLite journal or logged.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
import uuid

from MachineCheckpointStore import StoreError, validate

APPROVAL_TTL_SECONDS = 90


class ApprovalError(ValueError):
    pass


def _checkpoint_id(value):
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ApprovalError("INVALID CHECKPOINT ID") from exc
    if str(parsed) != value:
        raise ApprovalError("CHECKPOINT ID MUST BE CANONICAL")
    return str(parsed)


def _digest(checkpoint_id, saved_document, request):
    if not isinstance(request, dict):
        raise ApprovalError("INVALID REQUEST")
    needed = frozenset(("intent", "approved", "app_id", "con_id",
                        "from_workspace", "to_workspace"))
    if set(request) != needed or type(request["approved"]) is not bool:
        raise ApprovalError("INVALID REQUEST SHAPE")
    try:
        cleaned = validate(saved_document)
    except StoreError as exc:
        raise ApprovalError("INVALID SAVED CHECKPOINT") from exc
    data = {
        "checkpoint_id": _checkpoint_id(checkpoint_id),
        "document": cleaned,
        "request": {k: request[k] for k in sorted(request) if k != "approved"},
    }
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode("utf-8")).hexdigest()


class MoveApprovalGate:
    """Single use; requests must be revalidated by executor before consumption."""

    def __init__(self, *, clock=None, nonce_factory=None):
        self._clock = clock if clock is not None else time.monotonic
        self._nonce_factory = nonce_factory if nonce_factory is not None else (
            lambda: secrets.token_urlsafe(32))
        self._lock = threading.Lock()
        self._ticket = None

    def review(self, saved_document, request, *, checkpoint_id, read_runner):
        # A review never dispatches a command. It uses existing one-shot
        # preflight so only viable target placements receive a challenge.
        from MachineWindowMovePilot import preview_one
        if not isinstance(request, dict) or request.get("approved") is not False:
            raise ApprovalError("REVIEW MUST BE UNAPPROVED")
        source = preview_one(saved_document, request, read_runner=read_runner)
        before = source["before"]
        digest = _digest(checkpoint_id, saved_document, request)
        summary = {
            "app_id": before["app_id"],
            "con_id": before["con_id"],
            "from_workspace": before["workspace"],
            "to_workspace": before["target_workspace"],
        }
        challenge = ("MOVE " + summary["app_id"] + " FROM "
                     + summary["from_workspace"] + " TO "
                     + summary["to_workspace"])
        with self._lock:
            review_id = str(uuid.uuid4())
            self._ticket = {
                "id": review_id, "digest": digest,
                "expires_at": float(self._clock()) + APPROVAL_TTL_SECONDS,
                "challenge": challenge, "token": None,
                "state": "review",
            }
        return {
            "kind": "machine-single-move-approval-review",
            "review_id": review_id, "state": "awaiting_confirmation",
            "action": summary, "confirmation_text": challenge,
            "expires_in_seconds": APPROVAL_TTL_SECONDS,
            "executable": False, "single_use": True,
        }

    def approve(self, *, review_id, checkpoint_id, saved_document,
                request, confirmation_text):
        digest = _digest(checkpoint_id, saved_document, request)
        with self._lock:
            ticket = self._ticket
            if ticket is None or ticket["id"] != review_id:
                raise ApprovalError("REVIEW REPLACED OR UNKNOWN")
            if self._clock() >= ticket["expires_at"]:
                self._ticket = None
                raise ApprovalError("REVIEW EXPIRED")
            if ticket["state"] != "review":
                raise ApprovalError("REVIEW ALREADY HANDLED")
            if not hmac.compare_digest(ticket["digest"], digest):
                raise ApprovalError("ACTION OR CHECKPOINT CHANGED")
            if (not isinstance(confirmation_text, str)
                    or not hmac.compare_digest(ticket["challenge"], confirmation_text)):
                raise ApprovalError("EXACT ACTION CONFIRMATION REQUIRED")
            entropy = self._nonce_factory()
            if not isinstance(entropy, str) or len(entropy) < 32:
                raise ApprovalError("INVALID APPROVAL NONCE")
            # Even with an injected deterministic test entropy source, tokens
            # remain distinct across review IDs. Production uses secure random.
            token = hashlib.sha256((ticket["id"] + ":" + entropy).encode(
                "utf-8")).hexdigest()
            ticket["token"] = token
            ticket["state"] = "approved"
            return {"kind": "machine-single-move-approval",
                    "approval_token": token, "single_use": True,
                    "expires_at_monotonic": ticket["expires_at"]}

    def consume(self, *, approval_token, checkpoint_id, saved_document, request):
        digest = _digest(checkpoint_id, saved_document, request)
        with self._lock:
            ticket = self._ticket
            if ticket is None or ticket["state"] != "approved":
                raise ApprovalError("NO UNUSED APPROVAL")
            if self._clock() >= ticket["expires_at"]:
                self._ticket = None
                raise ApprovalError("APPROVAL EXPIRED")
            if not hmac.compare_digest(ticket["digest"], digest):
                raise ApprovalError("ACTION OR CHECKPOINT CHANGED")
            if (not isinstance(approval_token, str)
                    or not hmac.compare_digest(ticket["token"], approval_token)):
                raise ApprovalError("INVALID APPROVAL TOKEN")
            # Consume before journal creation, dispatch or further IO; on crash
            # or failure, old token cannot ever authorize an automatic replay.
            self._ticket = None
