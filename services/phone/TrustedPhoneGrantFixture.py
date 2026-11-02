"""Synthetic, in-memory Phone Bridge access-grant contract (P1).

NO authenticated identity, real token verification, authorization gateway,
phone permission, connection, persistence, IPC or production access.
Test-only seeding/revocation does NOT represent a secure external endpoint.
All grant matches are expressly NOT permission to read private phone data.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

SCHEMA = "post-apollo.phone.synthetic-access-grant.v0"
EXECUTION = "FIXTURE_ONLY"
ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
OPERATIONS = frozenset({
    "messages.receive", "messages.read", "contacts.read",
    "notifications.receive", "messages.send",
    "calls.dial", "calls.answer", "calls.audio", "calls.hangup",
})
OWNER_KINDS = frozenset({"PERSONAL", "ORGANIZATION"})
MAX_GRANTS = 128
MAX_MEMBERSHIPS = 64
MAX_GRANT_SECONDS = 900
REQUEST_FIELDS = frozenset({
    "schema", "sessionRef", "deviceId", "lineId",
    "ownerKind", "organizationId", "operation",
})


def _id(value: object) -> str:
    if type(value) is not str or not ID.fullmatch(value):
        raise ValueError("opaque identifier required")
    return value


def _scope(owner_kind: object, organization_id: object) -> tuple[str, str | None]:
    if type(owner_kind) is not str or owner_kind not in OWNER_KINDS:
        raise ValueError("unsupported phone owner scope")
    if owner_kind == "PERSONAL":
        if organization_id is not None:
            raise ValueError("personal phone grant cannot inherit an organization")
        return owner_kind, None
    return owner_kind, _id(organization_id)


@dataclass(frozen=True, slots=True)
class HostVerifiedPhoneContext:
    """Only a future authenticated, privileged host can assert this safely.

    This dataclass can be fabricated by arbitrary Python code and is NOT
    itself a security token, verified session, organization membership proof,
    or permission to read a phone.
    """
    principal_id: str
    session_ref: str
    expires_at: int
    authorized_organizations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _FixtureGrant:
    grant_id: str
    principal_id: str
    device_id: str
    line_id: str
    owner_kind: str
    organization_id: str | None
    operations: frozenset[str]
    issued_at: int
    expires_at: int


class TrustedPhoneGrantFixture:
    """Offline behavioral model. Not a trusted access control component.

    Both callbacks MUST eventually belong to a privileged host, not QML or a
    phone adapter. This class remains intentionally unsuitable for production.
    Seed/revoke are harness methods, not callable authorization endpoints.
    """

    def __init__(
        self, *,
        resolve_session: Callable[[str, int], HostVerifiedPhoneContext | None],
        clock: Callable[[], int],
    ) -> None:
        if not callable(resolve_session) or not callable(clock):
            raise ValueError("host-owned callbacks required")
        self._resolve = resolve_session
        self._clock = clock
        self._grants: dict[str, _FixtureGrant] = {}
        self._last_time: int | None = None

    def seed_fixture_grant(
        self, *,
        grant_id: str, principal_id: str, device_id: str, line_id: str,
        owner_kind: str, organization_id: str | None,
        operations: list[str], issued_at: int, expires_at: int,
    ) -> None:
        """TEST-ONLY grant creation, never an API, consent or provisioning."""
        grant = _FixtureGrant(
            grant_id=_id(grant_id), principal_id=_id(principal_id),
            device_id=_id(device_id), line_id=_id(line_id),
            owner_kind=_scope(owner_kind, organization_id)[0],
            organization_id=_scope(owner_kind, organization_id)[1],
            operations=self._operations(operations),
            issued_at=issued_at, expires_at=expires_at,
        )
        if (type(issued_at) is not int or type(expires_at) is not int
                or issued_at < 0 or expires_at <= issued_at
                or expires_at - issued_at > MAX_GRANT_SECONDS
                or grant_id in self._grants
                or len(self._grants) >= MAX_GRANTS):
            raise ValueError("invalid, duplicate or excessive fixture grant")
        self._grants[grant_id] = grant

    @staticmethod
    def _operations(value: object) -> frozenset[str]:
        if (type(value) is not list or not value
                or len(value) > len(OPERATIONS)
                or any(type(op) is not str or op not in OPERATIONS for op in value)
                or len(set(value)) != len(value)):
            raise ValueError("explicit unique operation allowlist required")
        return frozenset(value)

    def revoke_fixture_grant(self, grant_id: str) -> bool:
        """TEST-ONLY mutation; revoked grants cannot be used on a later check."""
        if type(grant_id) is not str or not ID.fullmatch(grant_id):
            return False
        return self._grants.pop(grant_id, None) is not None

    @staticmethod
    def _denied() -> dict[str, object]:
        # No principal IDs, organization IDs, line refs, grant IDs, session
        # handles, phone numbers, or backend capability claims escape.
        return {
            "schema": SCHEMA, "execution": EXECUTION,
            "state": "DENIED", "routeEligible": False,
            "contentAccessEnabled": False,
        }

    def check(self, request: object) -> dict[str, object]:
        """Non-authoritative mock decision, rechecked for EACH event/action."""
        denied = self._denied()
        if type(request) is not dict or set(request) != REQUEST_FIELDS:
            return denied
        try:
            if request["schema"] != SCHEMA:
                return denied
            session = _id(request["sessionRef"])
            device, line = _id(request["deviceId"]), _id(request["lineId"])
            kind, org = _scope(request["ownerKind"], request["organizationId"])
            operation = request["operation"]
            if type(operation) is not str or operation not in OPERATIONS:
                return denied
            now = self._clock()
            if type(now) is not int or now < 0 or (
                self._last_time is not None and now < self._last_time
            ):
                return denied
            self._last_time = now

            verified = self._resolve(session, now)
            if type(verified) is not HostVerifiedPhoneContext:
                return denied
            if (verified.session_ref != session
                    or _id(verified.principal_id) != verified.principal_id
                    or type(verified.expires_at) is not int
                    or verified.expires_at <= now
                    or type(verified.authorized_organizations) is not tuple
                    or len(verified.authorized_organizations) > MAX_MEMBERSHIPS
                    or len(set(verified.authorized_organizations))
                       != len(verified.authorized_organizations)):
                return denied
            for membership in verified.authorized_organizations:
                _id(membership)
            if kind == "ORGANIZATION" and org not in verified.authorized_organizations:
                return denied

            matching = [
                grant for grant in self._grants.values()
                if grant.principal_id == verified.principal_id
                and grant.device_id == device and grant.line_id == line
                and grant.owner_kind == kind and grant.organization_id == org
                and operation in grant.operations
                and grant.issued_at <= now < grant.expires_at
            ]
            if len(matching) != 1:
                return denied
            # This remains hypothetical even on a matching fixture. A trusted
            # provider, live grant store, session verifier, phone permissions and
            # transport attestation are NOT connected.
            return {
                **denied, "state": "MATCHED_FIXTURE_ONLY",
            }
        except Exception:
            # Fail closed, no untrusted exception details in output.
            return denied
