"""Serialized, synthetic Phone Bridge host lifecycle contract (P1).

This is NOT a security boundary, authenticated session host, live grant
service, phone message reader, network daemon, IPC server or Qt receiver.
No real content is accepted. The RLock orders ONLY operations using this
fixture instance; callbacks/OS/processes outside this lock are NOT secured.
"""
from __future__ import annotations

from threading import RLock
from typing import Callable

from PhoneSubscriptionLifecycleFixture import PhoneSubscriptionLifecycleFixture
from TrustedPhoneGrantFixture import (
    HostVerifiedPhoneContext, TrustedPhoneGrantFixture,
)


class SerializedPhoneHostFixture:
    """Test-only arbiter for grant seeding/revocation and receive-event lifecycle.

    A single lock orders check+synthetic consume relative to revocation,
    teardown, context reconciliation, and other operations *on this host*.
    It does NOT make a future cross-process provider delivery atomic.
    """

    def __init__(
        self, *,
        resolve_session: Callable[[str, int], HostVerifiedPhoneContext | None],
        clock: Callable[[], int],
    ) -> None:
        self._lock = RLock()
        self._grants = TrustedPhoneGrantFixture(
            resolve_session=resolve_session, clock=clock,
        )
        self._lifecycle = PhoneSubscriptionLifecycleFixture(
            check_grant=self._grants.check,
        )

    def seed_fixture_grant(self, **kwargs: object) -> None:
        """TEST HARNESS ONLY. Unauthenticated fixture mutation, not an API."""
        with self._lock:
            self._grants.seed_fixture_grant(**kwargs)

    def arm(self, request: object) -> dict[str, object]:
        with self._lock:
            return self._lifecycle.arm(request)

    def queue_synthetic_event(self, *, event_ref: object,
                              epoch: object) -> dict[str, object]:
        with self._lock:
            return self._lifecycle.queue_synthetic_event(
                event_ref=event_ref, epoch=epoch,
            )

    def consume_synthetic(self, *, epoch: object) -> dict[str, object]:
        """Atomic *model* check+consume vs host-owned revoke/cancel.

        Each returned count refers only to an invented fixture event. No
        user-visible body/recipient, asynchronous delivery or receipt exists.
        """
        with self._lock:
            return self._lifecycle.consume_synthetic(epoch=epoch)

    def revoke_fixture_grant(self, grant_id: str) -> dict[str, object]:
        """Same lock guards fixture revocation AND pending-queue cancellation."""
        with self._lock:
            self._grants.revoke_fixture_grant(grant_id)
            return self._lifecycle.reconcile()

    def reconcile(self) -> dict[str, object]:
        """Check for host callback changes; not an event notification service."""
        with self._lock:
            return self._lifecycle.reconcile()

    def cancel(self) -> dict[str, object]:
        with self._lock:
            return self._lifecycle.cancel()
