"""MACHINE V2: signed pair + signed one-use consent, disposable rehearsal.

No installed signer, trusted Brave extension, logind/seat or C5 service is
created here. Existing V2 geometry runner stays CI-only and injection-only.
External signers must independently attest live browser/compositor identity
and human authorization before this could ever leave an isolated test.
"""
from __future__ import annotations

import os
from pathlib import Path

from MachineV2FloatingPilot import (
    APPROVAL_KIND, RehearsalRefused, prepare, execute_disposable,
)
from MachineV2GeometryJournal import GeometryJournal
from MachineV2PairConsent import (
    AdmissionRefused, OneUseSpendLedger, verify_pair_and_consent, _ms,
)


def refuse():
    raise AdmissionRefused("V2 SIGNED GEOMETRY OPERATION REFUSED")


def execute_fixture(*, checkpoint_id, window_key, live_con_id,
                    pairing, consent, pair_key, consent_key,
                    expected_session_id, expected_seat_id,
                    active_seat_guard, clock_ms,
                    spend_ledger, geometry_journal, read_runner, command_runner,
                    legacy_reader, geometry_reader):
    """No defaults for signer keys, seat, clock, storage or native runners.

    Exactly one grant is irrevocably spent before invoking the existing
    two-command pilot. A crash after spend but before journaling burns that
    grant and never automatically retries. Later production authority would
    require a separately installed independently verified issuer/seat service.
    """
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("CI") != "true":
        refuse()
    if (type(spend_ledger) is not OneUseSpendLedger
            or type(geometry_journal) is not GeometryJournal
            or not callable(active_seat_guard) or not callable(clock_ms)
            or not callable(read_runner) or not callable(command_runner)
            or not callable(legacy_reader) or not callable(geometry_reader)):
        refuse()
    # Both ledgers must be under one private fixture root; no caller can
    # inject an arbitrary different grant DB as a means of double spending.
    if spend_ledger.path.parent != geometry_journal.path.parent:
        refuse()
    if active_seat_guard() is not True:
        refuse()
    now = _ms(clock_ms())
    request = {
        "checkpoint_id": checkpoint_id,
        "checkpoint_window_key": window_key,
        "live_con_id": live_con_id,
        "operator_selected": True,
        "execution_approved": True,
        "approval_kind": APPROVAL_KIND,
    }
    try:
        proposal = prepare(request, legacy_reader=legacy_reader,
                           geometry_reader=geometry_reader,
                           read_runner=read_runner)
    except (RehearsalRefused, ValueError, KeyError, TypeError):
        refuse()
    target, live = proposal["target"], proposal["current"]
    intent = {
        "checkpoint_id": checkpoint_id,
        "window_key": target["window_key"],
        "live_con_id": live_con_id, "app_id": target["app_id"],
        "output": target["output"], "workspace": target["workspace"],
        "before_rect": live["rect"], "target_rect": target["rect"],
        "session_id": expected_session_id,
    }
    grant = verify_pair_and_consent(
        pairing=pairing, consent=consent, intent=intent,
        pair_key=pair_key, consent_key=consent_key,
        expected_session_id=expected_session_id,
        expected_seat_id=expected_seat_id, now_ms=now)
    # No stale signed assertions may outlive current logind/seat visibility.
    # This is a separately injected fixture guard, NOT production C5 consent.
    if active_seat_guard() is not True or clock_ms() >= grant["expires_ms"]:
        refuse()
    spend_at = _ms(clock_ms())
    if spend_at < now or spend_at >= grant["expires_ms"]:
        refuse()
    spend_ledger.spend(grant, now_ms=spend_at)
    # Consuming is irreversible even if the subsequent operation refuses.
    # This prevents a crash/restart from replaying a previously spent permit.
    last_time = spend_at
    def still_valid():
        nonlocal last_time
        try:
            current = _ms(clock_ms())
            if (current < last_time or current >= grant["expires_ms"]
                    or active_seat_guard() is not True):
                return False
            last_time = current
            return True
        except Exception:
            return False
    try:
        outcome = execute_disposable(
            request, read_runner=read_runner, command_runner=command_runner,
            journal=geometry_journal, legacy_reader=legacy_reader,
            geometry_reader=geometry_reader, authority_guard=still_valid)
    except (RehearsalRefused, ValueError, TypeError, KeyError):
        refuse()
    return {
        "kind": "machine-v2-one-use-disposable-admission-result-v1",
        "status": outcome["status"],
        "dispatched_commands": outcome["dispatched_commands"],
        "grant_id": grant["grant_id"],
        "consent_spent": True,
        "no_automatic_retry": True,
        "production_authorized": False,
        "persistent_brave_identity_verified": False,
        "browser_tabs_restorable": False,
        "manual_recovery_required": outcome["manual_recovery_required"],
    }
