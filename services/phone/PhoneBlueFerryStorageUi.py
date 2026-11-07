#!/usr/bin/env python3
"""BlueFerry encrypted local storage: read-only status + explicit wallet unlock.

This is a narrow PHONE UI bridge to an already-running BlueFerry daemon.
--status never changes storage or asks for a keyring prompt.
--unlock calls ONLY BlueFerry's UnlockStorage after the user clicks the PHONE
button. It does NOT reset storage, clear history, change retention/encryption,
install/start a service, pair a device or access message/contact content.

No passwords, key material, detailed keyring errors, BlueFerry owner names,
device identifiers, message bodies or contacts are printed.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable

from BlueFerryHostReadPort import UniqueOwnerBlueFerrySource, _owner_valid

SCHEMA = "post-apollo.phone.blueferry-storage-ui.v0"
EXECUTION = "EXPLICIT_BLUEFERRY_STORAGE_UNLOCK"
MAX_UNLOCK_RESPONSE = 8192
STATES = frozenset({"READY", "LOCKED", "NO_RETENTION",
                    "UNAVAILABLE", "PROVIDER_UNAVAILABLE",
                    "UNLOCK_FAILED", "UNLOCK_UNAVAILABLE"})
POLICIES = frozenset({"encrypted", "plaintext", "none"})


def _answer(state: str, policy: str = "unknown") -> dict[str, object]:
    # Only public enum metadata, no backend error messages or private data.
    return {"schema": SCHEMA, "execution": EXECUTION,
            "state": state, "storagePolicy": policy if policy in POLICIES
            else "unknown", "contentsIncluded": False,
            "credentialsIncluded": False}


def _state(status: object) -> tuple[str, str]:
    if (type(status) is not dict
            or type(status.get("api_version")) is not int
            or status.get("api_version") != 2
            or status.get("daemon") is not True):
        return ("UNAVAILABLE", "unknown")
    policy = status.get("storage_policy")
    state = status.get("storage_state")
    if type(policy) is not str or policy not in POLICIES:
        return ("UNAVAILABLE", "unknown")
    if type(state) is not str:
        return ("UNAVAILABLE", policy)
    if policy == "none":
        return ("NO_RETENTION", policy)
    if policy == "plaintext":
        return ("READY", policy) if state in {"ready", "plaintext", "unlocked"} else ("UNAVAILABLE", policy)
    if state in {"ready", "unlocked"}:
        return ("READY", policy)
    if state == "locked":
        return ("LOCKED", policy)
    return ("UNAVAILABLE", policy)


def action(
    operation: str, *,
    source_factory: Callable[[], Any] = UniqueOwnerBlueFerrySource,
) -> dict[str, object]:
    if type(operation) is not str or operation not in ("--status", "--unlock"):
        return _answer("UNAVAILABLE")
    try:
        source = source_factory()
        owner = source.owner()
        if not _owner_valid(owner):
            return _answer("PROVIDER_UNAVAILABLE")
        state, policy = _state(source.status(owner))
        if operation == "--status":
            return _answer(state, policy)

        # Explicit user action only. Never try a keyring prompt on ordinary
        # status checks or reopen, and never change the retention policy.
        if state == "READY" or state == "NO_RETENTION":
            return _answer(state, policy)
        if state != "LOCKED" or policy != "encrypted":
            return _answer("UNLOCK_UNAVAILABLE", policy)
        # Pin both method calls to the same already-running unique owner.
        # This is BlueFerry's existing asynchronous UnlockStorage D-Bus method,
        # not a direct request for a password or cryptographic material.
        raw = source._iface(owner).UnlockStorage(timeout=30)
        result = source._json(raw, bound=MAX_UNLOCK_RESPONSE, kind=dict)
        outcome, new_policy = _state({
            "api_version": 2, "daemon": True, **result,
        })
        if source.owner() != owner:
            return _answer("UNLOCK_FAILED", policy)
        after, after_policy = _state(source.status(owner))
        if (outcome == "READY" and new_policy == "encrypted"
                and after == "READY" and after_policy == "encrypted"):
            return _answer("READY", "encrypted")
        return _answer("UNLOCK_FAILED", after_policy)
    except Exception:
        # Never print BlueFerry's raw D-Bus or wallet errors.
        return _answer("UNLOCK_FAILED" if operation == "--unlock"
                       else "PROVIDER_UNAVAILABLE")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    operation = args[0] if len(args) == 1 else ""
    reply = action(operation)
    print(json.dumps(reply, sort_keys=True))
    return 0 if operation in ("--status", "--unlock") else 2


if __name__ == "__main__":
    raise SystemExit(main())
