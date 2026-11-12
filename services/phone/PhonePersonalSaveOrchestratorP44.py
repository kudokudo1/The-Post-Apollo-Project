"""P44 // Ordered PHONE Personal edit transactions in a disposable host fixture.

The real P35 AES-GCM vault and P34 candidate matching run in synthetic tests
via the existing P36 one-action coordinator. A two-change Favorite+Note draft
is split into two independent, nonce/revision-guarded operations. On any
failure, later operations STOP and no automatic retry occurs.

This is NOT a production PHONE host: P36 callbacks and keys are synthetic and
forgeable. No IPC, QML export, keyring provisioning, installed host, signer,
C5 consent issuer, anti-rollback ledger, or real note access.
"""
from __future__ import annotations

import re
from typing import Callable

import PhonePersonalEditIngressP43 as P43
import PhonePersonalHostGateP36 as P36

PLAN_SCHEMA = "post-apollo.phone.personal-save-plan.p44.v1"
RESULT_SCHEMA = "post-apollo.phone.personal-transaction-fixture.p44.v1"
NONCE = re.compile(r"^[0-9a-f]{32}$", re.ASCII)
MAX_ACTIONS = 2

BASE = {
    "schema": RESULT_SCHEMA,
    "fixtureOnly": True,
    "productionEnabled": False,
    "vaultWriteAuthorizedForProduction": False,
    "humanConsentVerified": False,
    "durableCommitProven": False,
    "retryAuthorized": False,
}
REFUSED = {**BASE, "status": "SYNTHETIC_PLAN_REFUSED", "completedActions": 0}
STOPPED = {**BASE, "status": "SYNTHETIC_SEQUENCE_STOPPED_UNCONFIRMED"}
DONE = {**BASE, "status": "SYNTHETIC_ACTIONS_APPLIED_NOT_PRODUCTION"}


class FixturePlanRefused(Exception):
    """Private input never appears in a public exception or result."""


def _deny() -> None:
    raise FixturePlanRefused("P44_FIXTURE_PLAN_REFUSED")


def _parse_plan(plan: object) -> tuple[P43.StagedEditorIntent, ...]:
    """Validate the *whole* multi-action draft before any action starts."""
    try:
        if (type(plan) is not dict
                or set(plan) != {"schema", "status", "operations"}
                or plan["schema"] != PLAN_SCHEMA
                or plan["status"] != "UNTRUSTED_REVIEW_ONLY"
                or type(plan["operations"]) is not list
                or not 1 <= len(plan["operations"]) <= MAX_ACTIONS):
            _deny()
        operations = tuple(
            P43.parse_untrusted_editor_intent(value)
            for value in plan["operations"]
        )
        # Link/Unlink are separate one-action human workflows. Never
        # silently link a contact merely because favorite/note was drafted.
        actions = tuple(op.action for op in operations)
        if actions not in (("FAVORITE",), ("NOTE",), ("FAVORITE", "NOTE")):
            _deny()
        if len(set(op.selected_contact_id for op in operations)) != 1:
            _deny()
        return operations
    except (FixturePlanRefused, P43.EditorIntentRefused, ValueError,
            TypeError, KeyError, OverflowError, RecursionError):
        _deny()


def run_disposable_plan(
    *, plan: object, coordinator: object,
    initial_revision: object, issue_nonce: object,
) -> dict[str, object]:
    """Run P43 -> P36 -> P34 -> P35 per-action CI fixtures, never real save.

    A real future host MUST replace the P36 fixture with independently
    authenticated installed Identity/C3e host evidence, externally held one-use
    challenge and C5 consent, protected key custody, and a lease held through
    each commit and readback. This function is not a permission boundary.
    """
    try:
        operations = _parse_plan(plan)
        if (type(coordinator) is not P36.FixtureCoordinator
                or type(initial_revision) is not int
                or not 0 <= initial_revision < 2**53 - MAX_ACTIONS
                or not callable(issue_nonce)):
            _deny()
    except FixturePlanRefused:
        return dict(REFUSED)

    used: set[str] = set()
    completed = 0
    revision = initial_revision
    for operation in operations:
        try:
            nonce = issue_nonce()
            if (type(nonce) is not str
                    or NONCE.fullmatch(nonce) is None
                    or nonce in used):
                return {**STOPPED, "completedActions": completed}
            used.add(nonce)
            one = P36.ActionFixture(
                action=operation.action,
                selected_row=operation.selected_contact_id,
                expected_revision=revision,
                nonce=nonce,
                favorite=operation.favorite, note=operation.note,
            )
            result = coordinator.apply(one)
            # P36's synthetic result is not a durable receipt. Compare only
            # the narrow fixture-specific acknowledgment, not a trusted grant.
            if (type(result) is not dict
                    or set(result) != {"status", "revision", "productionEnabled"}
                    or result["status"] != "SYNTHETIC_SEALED"
                    or result["productionEnabled"] is not False
                    or type(result["revision"]) is not int
                    or result["revision"] != revision + 1):
                return {**STOPPED, "completedActions": completed}
            revision += 1
            completed += 1
        except Exception:
            # A rename may already have happened before fsync failed. Do not
            # guess which action landed or retry/consume another token.
            return {**STOPPED, "completedActions": completed}
    return {**DONE, "completedActions": completed}


# No main(), service socket, QML transport, installation, trusted lease,
# production credentials or ability to authorize real PHONE writes.
