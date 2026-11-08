"""Telegram M1 // synthetic sign-out transaction, NOT production authority.

Test-only seam for the Telegram provider owner and a future protected Connections
host. Cannot import into production UI, bridge, or adapter. It models an
irreversible log_out() which, per Telethon 1.x, ALSO deletes the session file.
It NEVER receives a real session path, Telethon client, key, or credentials.
An in-process synthetic reviewer is NOT authenticated human consent.
"""
from __future__ import annotations

import inspect
import re
import secrets
from typing import Any

TEST_MARKER = "CPU_PLUS_TELEGRAM_FAKE_REVOKE_ONLY"
OPERATION = "telegram.session.revoke"
IDENTITY = re.compile(r"identity-[1-9][0-9]{0,8}\Z", re.ASCII)
NONCE = re.compile(r"fake-session-[A-Za-z0-9_-]{1,40}\Z", re.ASCII)
DENY = {
    "hostAuthenticated": False,
    "callerAuthenticated": False,
    "operatorConsentAuthenticated": False,
    "credentialActionsEnabled": False,
    "realSessionRevocationAuthorized": False,
    "providerRevocationConfirmed": False,
    "localSessionWriteAuthorized": False,
    "productionReady": False,
}
MAX_REQUESTS = 16
TTL_MS = 30000


def report(status: str, *, synthetic=False, request_id=None) -> dict:
    reply = {"status": status, "syntheticStepAccepted": bool(synthetic), **DENY}
    if request_id is not None:
        reply["requestId"] = request_id
    return reply


def exact(value: Any, fields: set[str]) -> bool:
    return type(value) is dict and set(value) == fields


def valid_target(target: object, identity: object) -> bool:
    return (type(target) is str and type(identity) is str
            and ((target == "shared" and identity == "")
                 or (target == "private" and IDENTITY.fullmatch(identity) is not None)))


def valid_receipt(r: object, target: str, identity: str, *, authorized=True) -> bool:
    # All values are synthetic fixture evidence. No session paths or secrets.
    return (exact(r, {"target", "identity", "epoch", "nonce",
                      "authorized", "operationBusy"})
            and r["target"] == target and r["identity"] == identity
            and type(r["epoch"]) is int and r["epoch"] > 0
            and type(r["nonce"]) is str and NONCE.fullmatch(r["nonce"]) is not None
            and r["authorized"] is authorized
            and r["operationBusy"] is False)


class DisposableTelegramRevocation:
    """Private simulated reviewer and client entrypoints; no real grant."""

    def __init__(self, *, marker: str, provider: object, clock):
        if (marker != TEST_MARKER or not callable(clock)
                or not callable(getattr(provider, "inspect", None))
                or not callable(getattr(provider, "log_out", None))
                or not inspect.iscoroutinefunction(provider.log_out)):
            raise RuntimeError("TELEGRAM_REVOCATION_REFUSED_NON_DISPOSABLE_HOST")
        self._provider = provider
        self._clock = clock
        self._requests: dict[str, dict] = {}
        self._epoch = 0

    def _read(self, target, identity):
        try:
            candidate = self._provider.inspect(target, identity)
        except Exception:
            return None
        return candidate if valid_receipt(candidate, target, identity) else None

    def client_prepare(self, req):
        if (not exact(req, {"scope", "operation", "target", "identity"})
                or req["scope"] != OPERATION or req["operation"] != "log_out"
                or not valid_target(req["target"], req["identity"])):
            return report("INVALID_OPERATION_OR_SCOPE")
        if len(self._requests) >= MAX_REQUESTS:
            return report("REQUEST_LIMIT")
        receipt = self._read(req["target"], req["identity"])
        if receipt is None:
            return report("SESSION_NOT_INDEPENDENTLY_VERIFIED")
        when = self._clock()
        if type(when) not in (int, float) or when < 0:
            return report("INVALID_CLOCK")
        rid = secrets.token_hex(16)
        self._requests[rid] = {
            "target": req["target"], "identity": req["identity"],
            "receipt": dict(receipt), "scope": OPERATION,
            "operation": "log_out", "reviewEpoch": self._epoch,
            "deadline": when + TTL_MS / 1000, "state": "PENDING"
        }
        return report("SYNTHETIC_REVIEW_REQUIRED_NO_GRANT", request_id=rid)

    def synthetic_reviewer_approve(self, review):
        fields = {"requestId", "scope", "operation", "target", "identity",
                  "confirmRemoteRevocation", "confirmLocalSessionLoss"}
        if not exact(review, fields) or type(review["requestId"]) is not str:
            return report("INVALID_SYNTHETIC_REVIEW")
        request = self._requests.get(review["requestId"])
        if (request is None or request["state"] != "PENDING"
                or review["scope"] != request["scope"]
                or review["operation"] != request["operation"]
                or review["target"] != request["target"]
                or review["identity"] != request["identity"]
                or review["confirmRemoteRevocation"] is not True
                or review["confirmLocalSessionLoss"] is not True
                or request["reviewEpoch"] != self._epoch
                or self._clock() >= request["deadline"]):
            return report("SYNTHETIC_REVIEW_REFUSED")
        if self._read(request["target"], request["identity"]) != request["receipt"]:
            request["state"] = "STALE"
            return report("SESSION_CHANGED_BEFORE_REVIEW")
        request["state"] = "APPROVED"
        return report("SYNTHETIC_REVIEW_ACCEPTED_NO_REAL_GRANT")

    def synthetic_revoke(self):
        self._epoch += 1
        for request in self._requests.values():
            if request["state"] in ("PENDING", "APPROVED"):
                request["state"] = "REVOKED"
        return report("SYNTHETIC_REVOCATION_ONLY")

    async def client_execute(self, req):
        if (not exact(req, {"requestId", "scope", "operation", "target", "identity"})
                or type(req["requestId"]) is not str or req["scope"] != OPERATION
                or req["operation"] != "log_out"
                or not valid_target(req["target"], req["identity"])):
            return report("INVALID_EXECUTION")
        request = self._requests.get(req["requestId"])
        if (request is None or request["scope"] != req["scope"]
                or request["operation"] != req["operation"]
                or request["target"] != req["target"]
                or request["identity"] != req["identity"]):
            return report("REQUEST_BINDING_CHANGED")
        if request["state"] != "APPROVED":
            return report("NOT_APPROVED_OR_REPLAYED")
        # Consume before any callback: a thrown exception may still have
        # reached Telegram, so even an uncertain result must never replay.
        request["state"] = "CONSUMED"
        if request["reviewEpoch"] != self._epoch or self._clock() >= request["deadline"]:
            return report("REVOKED_OR_EXPIRED")
        receipt = self._read(request["target"], request["identity"])
        if receipt != request["receipt"]:
            return report("SESSION_CHANGED_BEFORE_REVOCATION")
        try:
            ack = await self._provider.log_out(request["target"], request["identity"])
        except Exception:
            return report("PROVIDER_RESULT_UNKNOWN_MANUAL_RECHECK_REQUIRED")
        # Ack must be exactly True; an unverified local missing file or
        # disconnect() is not sufficient to claim remote revocation.
        if ack is not True:
            return report("PROVIDER_RESULT_UNKNOWN_MANUAL_RECHECK_REQUIRED")
        try:
            after = self._provider.inspect(request["target"], request["identity"])
        except Exception:
            return report("POST_LOGOUT_STATUS_UNKNOWN")
        if (not exact(after, {"target", "identity", "epoch", "nonce",
                              "authorized", "operationBusy"})
                or after["target"] != request["target"]
                or after["identity"] != request["identity"]
                or after["authorized"] is not False):
            return report("POST_LOGOUT_STATUS_UNKNOWN")
        # Even when the fake provider acknowledges, this is NOT proof that
        # a production Telegram host authenticated anyone or revoked access.
        return report("SYNTHETIC_TELETHON_ACK_AND_LOCAL_STATUS_ONLY", synthetic=True)
