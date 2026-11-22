"""Forest B4a // HOST-INJECTED synthetic admission, NOT a production authenticator.

No listener, socket opener, identity issuer, tokens, signing keys or live UI.
The caller's identity is NEVER taken from the request JSON. All peer proof
and permission decisions MUST come from a separate trusted host. In-process
Python objects are forgeable and cannot replace real process attestation.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from ollama_chat_transport import _model_name
from session_journal_v0 import ForestSessionJournal, JournalRefusal, _key
from turn_bridge_b3 import BridgeRefusal, ForestTurnBridge

SCHEMA = "post-apollo.forest.host-intent.experimental-b4a"
_MAX_REQUEST_BYTES = 1536
_MAX_LEASE_MS = 300000
_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{16,96}\Z", re.ASCII)


class AdmissionRefusal(Exception):
    """Stable refusal, never a credential, prompt or private session detail."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class KernelPeer:
    """Supplied by a future host from kernel SO_PEERCRED, NOT wire JSON."""
    pid: int
    uid: int
    gid: int


@dataclass(frozen=True, slots=True)
class VerifiedCaller:
    """Host-only synthetic verification result, NOT a cryptographic grant."""
    owner_key: str
    peer_pid: int
    peer_uid: int
    valid_until_ms: int


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise AdmissionRefusal("DUPLICATE_FIELD")
        output[key] = value
    return output


def decode_intent(wire: object) -> dict[str, Any]:
    if type(wire) is not bytes or not 0 < len(wire) <= _MAX_REQUEST_BYTES:
        raise AdmissionRefusal("INVALID_WIRE")
    try:
        intent = json.loads(
            wire.decode("utf-8"), object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                AdmissionRefusal("INVALID_JSON")),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AdmissionRefusal("INVALID_JSON") from exc
    if type(intent) is not dict:
        raise AdmissionRefusal("INVALID_INTENT")
    action = intent.get("action")
    keys = {"schema", "action", "requestId", "sessionId"}
    if action == "GENERATE":
        keys |= {"model", "expectedRevision"}
    if action not in ("READ_SESSION", "GENERATE") or set(intent) != keys:
        raise AdmissionRefusal("INVALID_INTENT")
    if intent["schema"] != SCHEMA:
        raise AdmissionRefusal("INVALID_SCHEMA")
    rid = intent["requestId"]
    if type(rid) is not str or _REQUEST_ID.fullmatch(rid) is None:
        raise AdmissionRefusal("INVALID_REQUEST_ID")
    try:
        _key(intent["sessionId"])
    except JournalRefusal as exc:
        raise AdmissionRefusal("INVALID_SESSION_ID") from exc
    if action == "GENERATE":
        rev = intent["expectedRevision"]
        if type(rev) is not int or not 0 <= rev <= 2**63 - 2:
            raise AdmissionRefusal("INVALID_REVISION")
        try:
            _model_name(intent["model"])
        except (ValueError, TypeError, Exception) as exc:
            # The model is a selection, NOT a source of authority.
            raise AdmissionRefusal("INVALID_MODEL") from exc
    return intent


class ForestHostAdmission:
    """Contract fixture; only a separately attested host may own callbacks.

    Peer verifier must confirm installed process identity, active session/seat,
    and current principal binding. Policy callback independently checks
    operation-specific permission and model approval (including consent).
    Neither callback is supplied by a QML client or read from request bytes.
    """

    def __init__(self, journal: ForestSessionJournal,
                 bridge: ForestTurnBridge, *,
                 clock_ms: Callable[[], int],
                 verified_peer: Callable[[KernelPeer, int], VerifiedCaller | None],
                 approved_intent: Callable[[VerifiedCaller, str, str, str | None, int], bool]):
        if (type(journal) is not ForestSessionJournal
                or type(bridge) is not ForestTurnBridge
                or bridge.journal is not journal
                or not all(map(callable, (clock_ms, verified_peer, approved_intent)))):
            raise AdmissionRefusal("HOST_DEPENDENCY_MISSING")
        self._journal = journal
        self._bridge = bridge
        self._clock = clock_ms
        self._verify = verified_peer
        self._approve = approved_intent

    def _authorize(self, peer: KernelPeer, intent: dict) -> VerifiedCaller:
        if (type(peer) is not KernelPeer
                or any(type(value) is not int for value in
                       (peer.pid, peer.uid, peer.gid))
                or peer.pid <= 0 or peer.uid < 0 or peer.gid < 0):
            raise AdmissionRefusal("PEER_EVIDENCE_REQUIRED")
        try:
            now = self._clock()
        except Exception as exc:
            raise AdmissionRefusal("TRUST_UNAVAILABLE") from exc
        if type(now) is not int or not 0 < now <= 2**63 - 1:
            raise AdmissionRefusal("TRUST_UNAVAILABLE")
        try:
            principal = self._verify(peer, now)
        except Exception as exc:
            raise AdmissionRefusal("TRUST_UNAVAILABLE") from exc
        if (type(principal) is not VerifiedCaller
                or type(principal.peer_pid) is not int
                or type(principal.peer_uid) is not int
                or principal.peer_pid != peer.pid
                or principal.peer_uid != peer.uid
                or type(principal.valid_until_ms) is not int
                or not now < principal.valid_until_ms <= now + _MAX_LEASE_MS):
            raise AdmissionRefusal("CALLER_UNVERIFIED")
        try:
            _key(principal.owner_key)
        except JournalRefusal as exc:
            raise AdmissionRefusal("CALLER_UNVERIFIED") from exc
        try:
            permitted = self._approve(
                principal, intent["action"], intent["sessionId"],
                intent.get("model"), now)
        except Exception as exc:
            raise AdmissionRefusal("POLICY_UNAVAILABLE") from exc
        if permitted is not True:
            raise AdmissionRefusal("NOT_AUTHORIZED")
        return principal

    def read_session(self, wire: bytes, *, peer: KernelPeer) -> dict[str, Any]:
        intent = decode_intent(wire)
        if intent["action"] != "READ_SESSION":
            raise AdmissionRefusal("INVALID_ACTION")
        principal = self._authorize(peer, intent)
        try:
            record = self._journal.session(principal.owner_key,
                                           intent["sessionId"])
        except JournalRefusal as exc:
            # Owner isolation: don't reveal whether another user's session exists.
            raise AdmissionRefusal("SESSION_UNAVAILABLE") from exc
        return {
            "schema": SCHEMA,
            "requestId": intent["requestId"],
            "status": "READ_ONLY",
            "session": {
                "session_id": record["session_id"],
                "tree_key": record["tree_key"],
                "state": record["state"],
                "revision": record["revision"],
            },
        }

    def generate(self, wire: bytes, *, peer: KernelPeer
                 ) -> Iterator[dict[str, Any]]:
        """Host-approved *fixture* generation; no real listener or activation.

        Revocation during an in-flight model stream is NOT yet guaranteed.
        The production host must add trusted pre-COMMIT reauthorization,
        cancellation, and durable receipt/seat checks before any real use.
        """
        intent = decode_intent(wire)
        if intent["action"] != "GENERATE":
            raise AdmissionRefusal("INVALID_ACTION")
        principal = self._authorize(peer, intent)
        try:
            with_stream = self._bridge.exchange(
                owner=principal.owner_key,
                session_id=intent["sessionId"],
                expected_revision=intent["expectedRevision"],
                model=intent["model"],
            )
            try:
                for event in with_stream:
                    yield {"requestId": intent["requestId"], **event}
            finally:
                with_stream.close()
        except (BridgeRefusal, JournalRefusal) as exc:
            raise AdmissionRefusal("TURN_UNAVAILABLE") from exc
