#!/usr/bin/env python3
"""MACHINE // exact request+peer binding for future owner-supplied admission.

A binding is NOT a signed C3e process witness or C5 consent. No accepted
receipt grammar, key, issuer, one-use ledger, service unit or positive admission
exists here. This code produces deterministic, bounded intent bytes and a
domain-separated digest for a future separately reviewed trust integration.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

import MachineBraveSealedVault as vault

DOMAIN = "machine.archive.metadata.intent.v1"
AUDIENCE = "machine.protected-archive-metadata-broker"
PURPOSE = "machine.archive.metadata.read"
REQUEST_KIND = "machine-protected-archive-metadata-request-v1"
LIST = "LIST_METADATA"
INSPECT = "INSPECT_METADATA"
MAX_RAW = 4096


class IntentRefusal(ValueError):
    pass


def refuse():
    raise IntentRefusal("MACHINE ARCHIVE INTENT REFUSED")


@dataclass(frozen=True)
class ArchiveIntent:
    canonical_bytes: bytes
    intent_sha256: str
    request_sha256: str
    challenge: str
    action: str
    record_id: str | None
    peer_pid: int
    peer_uid: int
    peer_gid: int
    admission_allowed: bool = False


def bind_request(raw: bytes, *, peer_pid: int, peer_uid: int,
                 peer_gid: int) -> ArchiveIntent:
    """Bind independently captured kernel peer values to exact socket bytes.

    Caller must use SO_PEERCRED, not a JSON claim. This function is NOT an
    authentication verifier, and its output never permits data access.
    """
    if (type(raw) is not bytes or not 1 <= len(raw) <= MAX_RAW or
        type(peer_pid) is not int or peer_pid <= 1 or
        type(peer_uid) is not int or peer_uid < 0 or
        type(peer_gid) is not int or peer_gid < 0):
        refuse()
    try:
        request = vault.strict_json(raw)
        if type(request) is not dict or request.get("kind") != REQUEST_KIND:
            refuse()
        action = request.get("action")
        if action == LIST:
            vault.exact_keys(request, ("kind", "action", "challenge"))
            record_id = None
        elif action == INSPECT:
            vault.exact_keys(request, ("kind", "action", "challenge", "record_id"))
            record_id = vault._id(request["record_id"])
        else:
            refuse()
        challenge = vault._id(request["challenge"])
    except (ValueError, TypeError, KeyError) as exc:
        raise IntentRefusal("MACHINE ARCHIVE INTENT REFUSED") from exc

    request_sha256 = hashlib.sha256(raw).hexdigest()
    subject: dict[str, Any] = {
        "kind": DOMAIN,
        "audience": AUDIENCE,
        "purpose": PURPOSE,
        "action": action,
        "challenge": challenge,
        "record_id": record_id,
        "request_sha256": request_sha256,
        "peer_pid": peer_pid,
        "peer_uid": peer_uid,
        "peer_gid": peer_gid,
    }
    encoded = json.dumps(subject, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("ascii")
    return ArchiveIntent(
        canonical_bytes=encoded,
        intent_sha256=hashlib.sha256(encoded).hexdigest(),
        request_sha256=request_sha256,
        challenge=challenge,
        action=action,
        record_id=record_id,
        peer_pid=peer_pid, peer_uid=peer_uid, peer_gid=peer_gid,
        admission_allowed=False,
    )


def external_authority_available() -> bool:
    """Unconditionally refuse until independently reviewed C3e+C5 adapters exist."""
    return False


def may_read_metadata(intent: ArchiveIntent, *, claimed_receipt=None) -> bool:
    """Claims such as signed:true/consented:true are not security evidence.

    This method intentionally cannot return true. A future change requires
    owner-specified C3e process/seat provenance, C5 one-use authorization,
    separate issuer custody, replay-resilient consumption and review.
    """
    return False


if __name__ == "__main__":
    raise SystemExit(1)
