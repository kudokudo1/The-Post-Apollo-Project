"""Synthetic Phone Bridge receive-subscription lifecycle, no live phone access.

This is NOT a privileged host, real event subscriber, permission broker, IPC,
network transport or authorization service. It uses the non-authoritative
TrustedPhoneGrantFixture and accepts ONLY opaque invented event references.
Never submit a phone SMS body, participant, address or other real content.
"""
from __future__ import annotations

from collections import deque
from typing import Callable

from TrustedPhoneGrantFixture import REQUEST_FIELDS, SCHEMA as GRANT_SCHEMA

SCHEMA = "post-apollo.phone.synthetic-subscription-lifecycle.v0"
MAX_PENDING = 8


class PhoneSubscriptionLifecycleFixture:
    """Single-threaded offline fixture for revoke-safe synthetic receive events.

    A production counterpart must enforce serialized check/consume in a
    privileged host and cancel its real Qt D-Bus subscription on changes.
    These test callbacks are forgeable, and no result is production authority.
    """

    def __init__(self, *, check_grant: Callable[[object], dict[str, object]]) -> None:
        if not callable(check_grant):
            raise ValueError("host-side fixture grant checker required")
        self._check = check_grant
        self._request: dict[str, object] | None = None
        self._epoch = 0
        self._pending: deque[str] = deque()

    def _reply(self, state: str, count: int = 0) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "execution": "FIXTURE_ONLY",
            "state": state,
            "epoch": self._epoch,
            "syntheticDeliveredCount": count,
            "routeEligible": False,
            "contentAccessEnabled": False,
        }

    def _clear(self) -> None:
        self._request = None
        self._pending.clear()
        self._epoch += 1

    def cancel(self) -> dict[str, object]:
        """Explicit fixture teardown, also invalidates outstanding epochs."""
        self._clear()
        return self._reply("CLOSED")

    def _still_matched(self) -> bool:
        if self._request is None:
            return False
        try:
            decision = self._check(dict(self._request))
        except Exception:
            return False
        # An in-memory fixture match is intentionally not real permission.
        return (
            type(decision) is dict
            and decision.get("state") == "MATCHED_FIXTURE_ONLY"
            and decision.get("execution") == "FIXTURE_ONLY"
            and decision.get("routeEligible") is False
            and decision.get("contentAccessEnabled") is False
        )

    def arm(self, request: object) -> dict[str, object]:
        """Model explicit user-selected receive only; never auto-connect."""
        if self._request is not None:
            return self._reply("REJECTED")
        if (
            type(request) is not dict
            or set(request) != REQUEST_FIELDS
            or request.get("schema") != GRANT_SCHEMA
            or request.get("operation") != "messages.receive"
        ):
            return self._reply("REJECTED")
        self._request = dict(request)
        if not self._still_matched():
            self._clear()
            return self._reply("REJECTED")
        self._epoch += 1
        return self._reply("ARMED_FIXTURE_ONLY")

    def reconcile(self) -> dict[str, object]:
        """Caller-triggered sign-out/membership/line/permission reconciliation."""
        if self._request is None:
            return self._reply("CLOSED")
        if not self._still_matched():
            self._clear()
            return self._reply("CANCELLED")
        return self._reply("ARMED_FIXTURE_ONLY")

    def queue_synthetic_event(self, *, event_ref: object, epoch: object) -> dict[str, object]:
        """Accept only opaque fixture IDs; never actual message payloads."""
        if self._request is None:
            return self._reply("CLOSED")
        if not self._still_matched():
            self._clear()
            return self._reply("CANCELLED")
        if type(epoch) is not int or epoch != self._epoch:
            return self._reply("REJECTED")
        # References are test-only identities, not personal message IDs.
        if (
            type(event_ref) is not str or not (1 <= len(event_ref) <= 64)
            or not all(c.isascii() and (c.isalnum() or c in "_-") for c in event_ref)
        ):
            return self._reply("REJECTED")
        if event_ref in self._pending:
            return self._reply("REJECTED")
        if len(self._pending) >= MAX_PENDING:
            self._clear()
            return self._reply("CANCELLED")
        self._pending.append(event_ref)
        return self._reply("QUEUED_FIXTURE_ONLY")

    def consume_synthetic(self, *, epoch: object) -> dict[str, object]:
        """Revalidate AFTER queueing; only return count, never event content."""
        if self._request is None:
            return self._reply("CLOSED")
        if not self._still_matched():
            self._clear()
            return self._reply("CANCELLED")
        if type(epoch) is not int or epoch != self._epoch:
            return self._reply("REJECTED")
        if not self._pending:
            return self._reply("EMPTY")
        self._pending.popleft()
        return self._reply("CONSUMED_FIXTURE_ONLY", 1)
