"""P18d: in-process, host-only release/revoke *model* for phone reads.

This is an isolated composition seam for BlueFerryHostReadPort. No CLI, IPC,
OIDC/session verification, real consent, trusted grants, BlueZ or D-Bus calls.
The host must supply an authenticated scope and an authoritative evaluator;
a caller can fabricate both today. This file MUST NOT be wired into QML
or mistaken for a production security boundary.

One lock orders release against cancel/replace only *within this instance*.
An external grant's revocation and actual UI purge require a future owner-run,
durable authority and delivery system. The code never stores a snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from threading import RLock
from typing import Callable

from BlueFerrySocialProjection import (
    MAX_CARDS, MAX_THREADS, PROFILE, SCHEMA as PROJECTION_SCHEMA,
)

SCHEMA = "post-apollo.phone.host-release-gate-model.v0"
EXECUTION = "IN_PROCESS_MODEL_ONLY"
ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
OWNER = re.compile(r"^:[0-9]+\.[0-9]+$")
OPERATIONS = frozenset({"messages.read", "contacts.read"})
OWNER_KINDS = frozenset({"PERSONAL", "ORGANIZATION"})


def _valid_id(value: object) -> bool:
    return type(value) is str and ID.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class HostAssertedPhoneScope:
    """Unforgeability is NOT provided by this dataclass.

    Every value must originate from a future authenticated, privileged host.
    A caller-supplied desktop selector or organization label is never enough.
    """
    principal_id: str
    session_id: str
    device_binding_id: str
    line_binding_id: str
    profile_id: str
    provider_owner: str
    owner_kind: str
    organization_id: str | None
    operation: str
    grant_generation: int
    context_generation: int

    def __post_init__(self) -> None:
        if any(not _valid_id(item) for item in (
            self.principal_id, self.session_id, self.device_binding_id,
            self.line_binding_id,
        )):
            raise ValueError("unsupported host scope")
        if (type(self.profile_id) is not str
                or PROFILE.fullmatch(self.profile_id) is None
                or type(self.provider_owner) is not str
                or OWNER.fullmatch(self.provider_owner) is None
                or self.owner_kind not in OWNER_KINDS
                or type(self.owner_kind) is not str
                or self.operation not in OPERATIONS
                or type(self.operation) is not str
                or type(self.grant_generation) is not int
                or type(self.context_generation) is not int
                or self.grant_generation < 1
                or self.context_generation < 1):
            raise ValueError("unsupported host scope")
        if self.owner_kind == "PERSONAL":
            if self.organization_id is not None:
                raise ValueError("unsupported host scope")
        elif not _valid_id(self.organization_id):
            raise ValueError("unsupported host scope")


@dataclass(frozen=True, slots=True)
class BoundReadCallbacks:
    """Transient callbacks for ONE host-owned read attempt, not a grant.

    Never publish these callbacks or this model to Social/QML or a public IPC.
    """
    guard: Callable[[str, str, str], bool]
    release: Callable[[str, str, str, dict[str, object]], bool]


def _snapshot_matches(snapshot: object, scope: HostAssertedPhoneScope) -> bool:
    """Validate P18a identity tags before invoking a host's content sink.

    P18a already validates native provider records. This is a separate
    cross-device/operation assertion to protect a host composition mistake.
    It is not a signature, integrity proof, or permission check.
    """
    base = {
        "schema", "execution", "serviceId", "deviceProfileId",
        "authorization", "routeEligible",
    }
    if type(snapshot) is not dict:
        return False
    if (snapshot.get("schema") != PROJECTION_SCHEMA
            or snapshot.get("execution") != "OFFLINE_PROJECTION_ONLY"
            or snapshot.get("serviceId") != "blueferry"
            or snapshot.get("deviceProfileId") != scope.profile_id
            or snapshot.get("authorization") != "NOT_EVALUATED"
            or snapshot.get("routeEligible") is not False):
        return False
    if scope.operation == "messages.read":
        if (set(snapshot) != base | {"conversations", "messageSets"}
                or type(snapshot.get("conversations")) is not list
                or type(snapshot.get("messageSets")) is not list
                or len(snapshot["conversations"]) > MAX_THREADS
                or len(snapshot["messageSets"]) != len(snapshot["conversations"])):
            return False
        ids: set[str] = set()
        for conversation in snapshot["conversations"]:
            if (type(conversation) is not dict
                    or type(conversation.get("id")) is not str
                    or not conversation["id"].startswith(scope.profile_id + ":")
                    or conversation.get("serviceId") != "blueferry"
                    or conversation["id"] in ids):
                return False
            ids.add(conversation["id"])
        set_ids: set[str] = set()
        for group in snapshot["messageSets"]:
            if (type(group) is not dict
                    or type(group.get("conversationId")) is not str
                    or group["conversationId"] not in ids
                    or group["conversationId"] in set_ids
                    or type(group.get("messages")) is not list):
                return False
            set_ids.add(group["conversationId"])
            for message in group["messages"]:
                if (type(message) is not dict
                        or message.get("conversationId") != group["conversationId"]
                        or type(message.get("id")) is not str
                        or not message["id"].startswith(group["conversationId"] + ":message:")):
                    return False
        return ids == set_ids

    if (set(snapshot) != base |
            {"daemonEpoch", "offset", "total", "query", "contacts"}
            or type(snapshot.get("contacts")) is not list
            or len(snapshot["contacts"]) > MAX_CARDS
            or type(snapshot.get("daemonEpoch")) is not str
            or not snapshot["daemonEpoch"]):
        return False
    for contact in snapshot["contacts"]:
        if (type(contact) is not dict
                or contact.get("serviceId") != "blueferry"
                or contact.get("deviceProfileId") != scope.profile_id
                or type(contact.get("id")) is not str
                or not contact["id"].startswith(
                    scope.profile_id + ":" + snapshot["daemonEpoch"] + ":"
                )):
            return False
    return True


class HostReadReleaseGateModel:
    """One host-selected phone read scope at a time, no persistent snapshots.

    evaluator(scope) must be a host-owned fresh authenticated/grant/provider
    check; deliver(scope, projection) must be the host's privileged sink;
    purge(scope) must wipe any previously published content from that sink.
    All callbacks are mockable, so NONE of these claims hold in this module.
    """

    def __init__(
        self, *,
        evaluator: Callable[[HostAssertedPhoneScope], bool],
        deliver: Callable[[HostAssertedPhoneScope, dict[str, object]], bool],
        purge: Callable[[HostAssertedPhoneScope], bool],
    ) -> None:
        if not all(callable(x) for x in (evaluator, deliver, purge)):
            raise ValueError("host-owned callbacks required")
        self._evaluate = evaluator
        self._deliver = deliver
        self._purge = purge
        self._lock = RLock()
        self._epoch = 0
        self._active: HostAssertedPhoneScope | None = None
        self._sealed = False

    def _reply(self, state: str) -> dict[str, object]:
        # Public-like snapshots never contain identities or private data.
        return {
            "schema": SCHEMA,
            "execution": EXECUTION,
            "state": state,
            "epoch": self._epoch,
            "routeEligible": False,
            "contentAccessEnabled": False,
            "authorization": "NOT_IMPLEMENTED",
        }

    def _check(self, scope: HostAssertedPhoneScope) -> bool:
        try:
            return self._evaluate(scope) is True
        except Exception:
            return False

    def _cancel_locked(self) -> bool:
        old = self._active
        self._active = None
        self._epoch += 1
        if old is None:
            return not self._sealed
        try:
            wiped = self._purge(old) is True
        except Exception:
            wiped = False
        if not wiped:
            self._sealed = True
        return wiped and not self._sealed

    def cancel(self) -> dict[str, object]:
        """Modeled revoke/context switch: purge before a new scope can arm.

        The *real* authority must serialize its grant revocation with this
        barrier and ensure UI wipe acknowledgement before declaring success.
        """
        with self._lock:
            return self._reply(
                "CANCELLED_MODEL_ONLY" if self._cancel_locked()
                else "PURGE_UNCONFIRMED"
            )

    def begin(
        self, scope: HostAssertedPhoneScope,
    ) -> tuple[dict[str, object], BoundReadCallbacks | None]:
        """Host-only arm. A test evaluator returning True is NOT a grant."""
        with self._lock:
            if self._sealed:
                return self._reply("PURGE_UNCONFIRMED"), None
            if self._active is not None:
                return self._reply("EXPLICIT_CANCEL_REQUIRED"), None
            if type(scope) is not HostAssertedPhoneScope or not self._check(scope):
                return self._reply("HOST_DENIED"), None
            self._epoch += 1
            self._active = scope
            epoch = self._epoch

            def matches(operation: str, profile: str, owner: str) -> bool:
                return (
                    self._active == scope and self._epoch == epoch
                    and type(operation) is str and operation == scope.operation
                    and type(profile) is str and profile == scope.profile_id
                    and type(owner) is str and owner == scope.provider_owner
                )

            def guard(operation: str, profile: str, owner: str) -> bool:
                with self._lock:
                    if not matches(operation, profile, owner):
                        return False
                    if self._check(scope):
                        return True
                    self._cancel_locked()
                    return False

            def release(
                operation: str, profile: str, owner: str,
                snapshot: dict[str, object],
            ) -> bool:
                with self._lock:
                    if not matches(operation, profile, owner):
                        return False
                    if not self._check(scope) or not _snapshot_matches(snapshot, scope):
                        self._cancel_locked()
                        return False
                    try:
                        delivered = self._deliver(scope, snapshot) is True
                    except Exception:
                        delivered = False
                    if not delivered:
                        # A sink may fail after a partial display update.
                        # Never allow a new scope until purge is confirmed.
                        self._cancel_locked()
                    return delivered

            return self._reply("ARMED_MODEL_ONLY"), BoundReadCallbacks(
                guard=guard, release=release,
            )
