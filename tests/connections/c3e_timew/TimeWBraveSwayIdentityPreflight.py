#!/usr/bin/env python3
"""C3e ↔ TimeW single-live-window correlation preflight: CI / no authority.

Uses TimeW's real signed PAIR schema. Both 'independent' observations and the
root fingerprint are injected *CI fixtures*, not a protected Wayland/Brave
identity service. Matching them cannot authenticate a production browser
window, persistent Brave identity, native operator, or permission to restore.
"""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
import re
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

TIME_DIR = Path(__file__).resolve().parents[3] / "services" / "time"
if str(TIME_DIR) not in sys.path:
    sys.path.insert(0, str(TIME_DIR))
import MachineV2PairConsent as TimeW

SCHEMA = "postapollo.connections.c3e-timew-live-window-correlation.ci-v1"
STATUS = "PAIRING_AND_SYNTHETIC_SURFACE_CORRELATE_NOT_TRUSTED"
MAX_WINDOWS = 32
MAX_OBSERVATION_AGE_MS = 1500
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
SELECTION_FIELDS = frozenset((
    "checkpoint_id", "window_key", "live_con_id", "app_id",
    "workspace", "output", "session_id", "browser_window_ref",
    "pid", "start_ticks", "uid", "gid", "exe_sha256",
    "snapshot_generation", "selected_at_ms",
))
PROCESS_FIELDS = frozenset((
    "pid", "start_ticks", "uid", "gid", "exe_sha256",
    "session_id", "alive",
))
WINDOW_FIELDS = frozenset((
    "con_id", "pid", "app_id", "workspace", "output",
    "session_id", "floating", "snapshot_generation",
))
PAIR_SCOPE = frozenset((
    "checkpoint_id", "window_key", "live_con_id", "app_id",
    "workspace", "output", "session_id", "browser_window_ref",
))
DENIED = {
    "installedPairingIssuerVerified": False,
    "operatorEnrollmentRootCustodyVerified": False,
    "kernelPeerOrPidfdLeaseVerified": False,
    "rootSignedExecutableReleaseVerified": False,
    "independentSwaySessionVerified": False,
    "swayWindowIdentityVerified": False,
    "braveWindowInstanceAuthenticated": False,
    "persistentBraveIdentityVerified": False,
    "browserWindowReferenceAuthenticated": False,
    "activeUnlockedOperatorSeatVerified": False,
    "independentC5ConsentVerified": False,
    "canSignNativePairing": False,
    "canMoveWindow": False,
    "canRestoreBrave": False,
    "productionAuthority": False,
    "credentialActionsEnabled": False,
}


class Refused(ValueError):
    """Synthetic correlation not acceptable even for format diagnostics."""


def _deny(code):
    raise Refused("C3E_TIMEW_WINDOW_HOLD // " + code)


def _strict_int(value, low, high=2**63-1):
    return type(value) is int and low <= value <= high


def _uuid(value, version=None):
    try:
        return TimeW._uuid(value, version=version)
    except (TimeW.AdmissionRefused, ValueError, TypeError) as exc:
        raise Refused("C3E_TIMEW_WINDOW_HOLD // INVALID_UUID") from exc


def _text(value):
    try:
        return TimeW._field(value)
    except (TimeW.AdmissionRefused, ValueError, TypeError) as exc:
        raise Refused("C3E_TIMEW_WINDOW_HOLD // INVALID_SCOPE_FIELD") from exc


def inspect_live_pairing_ci_only(
    *, signed_pairing: dict, pairing_public_key: Ed25519PublicKey,
    separately_expected_pairing_key_sha256: str,
    selected_window: dict, process_snapshot: dict,
    compositor_windows: list, observed_at_ms: int,
):
    """Compare TimeW signed PAIR to caller-owned fixture observations.

    No I/O, privileged reads, process assertions, key enrollment, permission
    grants, C5 consent, Sway command or window restore is performed.
    """
    if (not isinstance(pairing_public_key, Ed25519PublicKey)
            or type(separately_expected_pairing_key_sha256) is not str
            or HEX.fullmatch(separately_expected_pairing_key_sha256) is None):
        _deny("PAIRING_ROOT_PIN_REQUIRED")
    actual_pin = hashlib.sha256(pairing_public_key.public_bytes(
        Encoding.Raw, PublicFormat.Raw)).hexdigest()
    if not hmac.compare_digest(actual_pin, separately_expected_pairing_key_sha256):
        _deny("SUBSTITUTED_PAIRING_KEY")
    if (type(selected_window) is not dict or set(selected_window) != SELECTION_FIELDS
            or type(process_snapshot) is not dict or set(process_snapshot) != PROCESS_FIELDS):
        _deny("MISSING_OR_EXTRA_OBSERVATION_FIELDS")
    if (type(compositor_windows) is not list
            or not 1 <= len(compositor_windows) <= MAX_WINDOWS):
        _deny("UNBOUNDED_COMPOSITOR_SNAPSHOT")
    if (not _strict_int(observed_at_ms, 0, TimeW.MAX_CLOCK_MS)
            or not _strict_int(selected_window["selected_at_ms"], 0, TimeW.MAX_CLOCK_MS)):
        _deny("INVALID_OBSERVATION_TIME")
    if (observed_at_ms < selected_window["selected_at_ms"]
            or observed_at_ms - selected_window["selected_at_ms"] > MAX_OBSERVATION_AGE_MS):
        _deny("STALE_SELECTION")

    try:
        pair = TimeW._verify(signed_pairing, pairing_public_key, TimeW.PAIR_DOMAIN)
    except (TimeW.AdmissionRefused, TypeError, ValueError) as exc:
        raise Refused("C3E_TIMEW_WINDOW_HOLD // TIMEW_PAIR_SIGNATURE_REFUSED") from exc
    if (set(pair) != TimeW.PAIR_FIELDS
            or pair["schema"] != TimeW.PAIR_SCHEMA
            or pair["audience"] != TimeW.AUDIENCE):
        _deny("WRONG_TIMEW_PAIR_SCHEMA_OR_AUDIENCE")
    _uuid(pair["pair_id"], 4)
    _uuid(pair["checkpoint_id"], 4)
    _uuid(pair["window_key"])
    _uuid(pair["browser_window_ref"], 4)
    _uuid(pair["session_id"], 4)
    for field in ("app_id", "workspace", "output"):
        _text(pair[field])
    if not _strict_int(pair["live_con_id"], 1, TimeW.MAX_CLOCK_MS):
        _deny("INVALID_CONTAINER_ID")
    try:
        TimeW._period(pair, observed_at_ms)
    except TimeW.AdmissionRefused as exc:
        raise Refused("C3E_TIMEW_WINDOW_HOLD // EXPIRED_OR_FUTURE_PAIRING") from exc
    for key in PAIR_SCOPE:
        if type(selected_window[key]) is not type(pair[key]) or selected_window[key] != pair[key]:
            _deny("SIGNED_PAIR_SELECTION_DRIFT")

    for key in ("pid", "start_ticks", "uid", "gid", "snapshot_generation"):
        if not _strict_int(selected_window[key], 1 if key in ("pid","start_ticks","snapshot_generation") else 0):
            _deny("INVALID_SELECTED_PROCESS_OR_GENERATION")
    if (type(selected_window["exe_sha256"]) is not str
            or HEX.fullmatch(selected_window["exe_sha256"]) is None):
        _deny("INVALID_SELECTED_EXECUTABLE_DIGEST")

    for key in PROCESS_FIELDS - {"alive"}:
        if (type(process_snapshot[key]) is not type(selected_window[key])
                or process_snapshot[key] != selected_window[key]):
            _deny("STALE_OR_REUSED_PROCESS_IDENTITY")
    if process_snapshot["alive"] is not True:
        _deny("DEAD_OR_UNVERIFIED_PROCESS")
    if not _strict_int(process_snapshot["pid"], 1):
        _deny("INVALID_PROCESS_PID")

    selected_con = selected_window["live_con_id"]
    observed_ids = set()
    current = []
    matches_same_process = []
    for window in compositor_windows:
        if type(window) is not dict or set(window) != WINDOW_FIELDS:
            _deny("MALFORMED_COMPOSITOR_WINDOW")
        if (not _strict_int(window["con_id"], 1, TimeW.MAX_CLOCK_MS)
                or not _strict_int(window["pid"], 1)
                or not _strict_int(window["snapshot_generation"], 1)
                or window["con_id"] in observed_ids):
            _deny("DUPLICATE_OR_INVALID_COMPOSITOR_WINDOW")
        observed_ids.add(window["con_id"])
        for key in ("app_id", "workspace", "output"):
            _text(window[key])
        _uuid(window["session_id"], 4)
        if type(window["floating"]) is not bool:
            _deny("MALFORMED_COMPOSITOR_WINDOW")
        if window["con_id"] == selected_con:
            current.append(window)
        if (window["pid"] == process_snapshot["pid"]
                and window["app_id"] == selected_window["app_id"]
                and window["session_id"] == selected_window["session_id"]):
            matches_same_process.append(window)
    if len(current) != 1:
        _deny("NO_EXACT_LIVE_CONTAINER")
    live = current[0]
    if any(
        live[k] != selected_window[k]
        for k in ("app_id", "workspace", "output", "session_id",
                  "pid", "snapshot_generation")
    ) or live["floating"] is not True:
        _deny("REUSED_CONTAINER_OR_SCOPE_DRIFT")
    # A Brave process can own many windows. Without separately trusted
    # browser-window ↔ Sway-surface evidence we must not choose one by
    # title, app_id, claimed con_id, or foreground focus alone.
    if len(matches_same_process) != 1:
        _deny("AMBIGUOUS_BRAVE_WINDOWS_SAME_PROCESS")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "testOnlyTimeWPairSignatureMatchesCallerPin": True,
        "testOnlySingleFloatingWindowMatchesCallerSnapshots": True,
        "pairPayloadSha256": hashlib.sha256(TimeW._json(pair)).hexdigest(),
        "observedConIdInCI": selected_con,
        "observedAtMsInCI": observed_at_ms,
        **DENIED,
    }


def run_native_timew_window_witness(*_args, **_kwargs):
    _deny("REAL_NATIVE_BRAVE_SWAY_BINDING_NOT_IMPLEMENTED")
