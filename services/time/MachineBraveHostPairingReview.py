"""MACHINE: conservative comparison of independent Brave and Sway readings.

No transport, no trusted browser origin and no authority to pair windows.
A simultaneous browser focus report and Sway focused window are *evidence
to review*, not proof that they refer to the same native window.
"""
from __future__ import annotations

import uuid

from MachineBraveFocusWitness import BRAVE_APP_IDS, MAX_NAME

MAX_BROWSER_WINDOWS = 64
MAX_TAB_COUNT = 2048
MAX_TOTAL_TABS = 8192


class PairingReviewError(ValueError):
    pass


def _fields(record, names):
    if not isinstance(record, dict) or set(record) != set(names):
        raise PairingReviewError("INVALID OBSERVATION STRUCTURE")


def _bool(value, expected):
    if value is not expected:
        raise PairingReviewError("UNSUPPORTED OBSERVATION CLAIM")


def _uuid(value):
    if not isinstance(value, str):
        raise PairingReviewError("INVALID OBSERVATION IDENTIFIER")
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError) as exc:
        raise PairingReviewError("INVALID OBSERVATION IDENTIFIER") from exc
    return value


def _id(value):
    if type(value) is not int or value <= 0:
        raise PairingReviewError("INVALID BROWSER WINDOW ID")
    return value


def _count(value, limit):
    if type(value) is not int or not 0 <= value <= limit:
        raise PairingReviewError("INVALID BROWSER COUNT")
    return value


def review_independent_observations(browser, host):
    """Compare strict redacted observations, never return a binding.

    Deliberately no accept/approve/restore method: the OS-to-browser
    window correspondence still needs a separate trusted mechanism.
    """
    _fields(browser, (
        "kind", "status", "read_only", "capture_scope",
        "private_windows_included", "title_url_contents_included",
        "temporary_ids_only", "sway_window_binding_verified",
        "restart_session_identity_verified", "tabs_restorable",
        "safe_restore_actions", "counts", "windows",
    ))
    if (browser["kind"] != "machine-brave-window-topology-readonly-v1"
            or browser["status"] != "ready"
            or browser["capture_scope"] != "browser_window_counts_only"):
        raise PairingReviewError("UNSUPPORTED BROWSER OBSERVATION")
    for key, value in (
        ("read_only", True), ("private_windows_included", False),
        ("title_url_contents_included", False), ("temporary_ids_only", True),
        ("sway_window_binding_verified", False),
        ("restart_session_identity_verified", False),
        ("tabs_restorable", False),
    ):
        _bool(browser[key], value)
    if browser["safe_restore_actions"] != []:
        raise PairingReviewError("UNAUTHORIZED BROWSER ACTION")
    _fields(browser["counts"], ("browser_windows", "tabs", "pinned_tabs"))
    windows = browser["windows"]
    if not isinstance(windows, list) or len(windows) > MAX_BROWSER_WINDOWS:
        raise PairingReviewError("INVALID BROWSER WINDOWS")
    if _count(browser["counts"]["browser_windows"], MAX_BROWSER_WINDOWS) != len(windows):
        raise PairingReviewError("BROWSER WINDOW COUNT MISMATCH")
    _count(browser["counts"]["tabs"], MAX_TOTAL_TABS)
    _count(browser["counts"]["pinned_tabs"], MAX_TOTAL_TABS)
    total, pinned, focused, ids = 0, 0, [], set()
    for window in windows:
        _fields(window, ("temporary_browser_window_id",
                         "current_browser_window", "tab_count",
                         "pinned_tab_count", "active_tab_index"))
        window_id = _id(window["temporary_browser_window_id"])
        if window_id in ids:
            raise PairingReviewError("DUPLICATE BROWSER WINDOW ID")
        ids.add(window_id)
        count = _count(window["tab_count"], MAX_TAB_COUNT)
        pins = _count(window["pinned_tab_count"], count)
        active = window["active_tab_index"]
        if active is not None:
            if type(active) is not int or active < 0 or active >= count:
                raise PairingReviewError("INVALID ACTIVE TAB INDEX")
        if type(window["current_browser_window"]) is not bool:
            raise PairingReviewError("INVALID FOCUS CLAIM")
        if window["current_browser_window"]:
            focused.append(window_id)
        total += count
        pinned += pins
    if (len(focused) > 1 or total > MAX_TOTAL_TABS
            or total != browser["counts"]["tabs"]
            or pinned != browser["counts"]["pinned_tabs"]):
        raise PairingReviewError("INCONSISTENT BROWSER INVENTORY")

    if not isinstance(host, dict):
        raise PairingReviewError("INVALID HOST OBSERVATION")
    base_keys = {
        "kind", "status", "read_only", "browser_window_id",
        "sway_window_binding_verified", "browser_session_identity_verified",
        "private_window_exclusion_verified", "session_restorable",
        "action_allowed", "safe_actions",
    }
    if host.get("status") == "brave_focus_observed":
        _fields(host, base_keys | {
            "observation_id", "reported_app_id", "output", "workspace",
            "same_focused_client_in_two_reads",
        })
    else:
        _fields(host, base_keys)
    if host["kind"] != "machine-sway-brave-focus-witness-v1":
        raise PairingReviewError("UNSUPPORTED HOST OBSERVATION")
    for key, value in (
        ("read_only", True), ("browser_window_id", None),
        ("sway_window_binding_verified", False),
        ("browser_session_identity_verified", False),
        ("private_window_exclusion_verified", False),
        ("session_restorable", False), ("action_allowed", False),
    ):
        _bool(host[key], value)
    if host["safe_actions"] != []:
        raise PairingReviewError("UNAUTHORIZED HOST ACTION")

    base = {
        "kind": "machine-brave-host-observation-review-v1",
        "status": "unbound",
        "read_only": True,
        "browser_windows": len(windows),
        "browser_current_window_reported": len(focused) == 1,
        "host_focused_brave_reported": False,
        "candidate_browser_window_id": None,
        "host_observation_id": None,
        "observation_only": True,
        "browser_to_sway_identity_verified": False,
        "operator_confirmation_is_identity_proof": False,
        "private_window_exclusion_verified_by_host": False,
        "restart_session_identity_verified": False,
        "exact_session_match": False,
        "action_allowed": False,
        "safe_actions": [],
    }

    if host["status"] != "brave_focus_observed":
        if host["status"] not in (
                "focus_changed", "no_focused_client", "not_brave_focused"):
            raise PairingReviewError("UNKNOWN HOST OBSERVATION STATUS")
        return base

    observation_id = _uuid(host["observation_id"])
    name = host["reported_app_id"]
    if (name not in BRAVE_APP_IDS
            or not isinstance(host["output"], str)
            or not isinstance(host["workspace"], str)
            or not 1 <= len(host["output"]) <= MAX_NAME
            or not 1 <= len(host["workspace"]) <= MAX_NAME
            or any(ord(c) < 32 or ord(c) == 127
                   for c in host["output"] + host["workspace"])
            or host["same_focused_client_in_two_reads"] is not True):
        raise PairingReviewError("INVALID FOCUSED BRAVE OBSERVATION")
    base["host_focused_brave_reported"] = True
    if len(focused) == 1:
        # A correlation *candidate* only: Linux nativeMessaging reports
        # extension origin, not the calling native window handle.
        base.update(
            status="unverified_focus_candidate",
            candidate_browser_window_id=focused[0],
            host_observation_id=observation_id,
        )
    return base
