#!/usr/bin/env python3
"""MACHINE Brave focus-cycle: privacy, ambiguity, and no-action regression."""
import copy
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveFocusSequenceReview import (
    FocusSequenceError, review_focus_sequence,
)


def baseline():
    return {
        "kind": "machine-brave-focus-sequence-input-v1",
        "challenge": str(uuid.UUID(int=42)),
        "gesture": "operator_initiated_diagnostic_only",
        "browser_private_windows_excluded": True,
        "host_private_exclusion_verified": False,
        "transport_origin_authenticated": False,
        "samples": [
            {"step": "A1", "temporary_browser_window_id": 401,
             "focused_host_container_id": 101, "host_app_id": "brave-browser",
             "host_stable_two_reads": True, "requested_at_ms": 1000,
             "observed_at_ms": 1100},
            {"step": "B1", "temporary_browser_window_id": 402,
             "focused_host_container_id": 102, "host_app_id": "Brave-browser",
             "host_stable_two_reads": True, "requested_at_ms": 2000,
             "observed_at_ms": 2100},
            {"step": "A2", "temporary_browser_window_id": 401,
             "focused_host_container_id": 101, "host_app_id": "brave-browser",
             "host_stable_two_reads": True, "requested_at_ms": 3000,
             "observed_at_ms": 3100},
        ],
    }


def denied(mutator):
    case = baseline()
    mutator(case)
    try:
        review_focus_sequence(case)
    except FocusSequenceError:
        return
    raise AssertionError("forged or stale observation accepted")


good = baseline()
original = copy.deepcopy(good)
result = review_focus_sequence(good)
assert good == original
assert result == {
    "kind": "machine-brave-focus-sequence-review-v1",
    "status": "consistent_unverified_focus_pattern",
    "sample_count": 3,
    "observation_only": True,
    "browser_to_sway_identity_verified": False,
    "extension_origin_authenticated": False,
    "host_private_window_exclusion_verified": False,
    "restart_session_identity_verified": False,
    "session_capture_allowed": False,
    "restore_allowed": False,
    "action_allowed": False,
    "safe_actions": [],
}
# No raw Sway container IDs, browser temporary IDs, private data, UUIDs,
# host path, website titles or session metadata are exposed.
as_json = json.dumps(result)
for forbidden in ("101", "102", "401", "402", str(uuid.UUID(int=42)),
                  "URL", "cookie", "window_id", "private.invalid"):
    assert forbidden not in as_json, forbidden

# The finite cycle is not a secure proof: even valid A/B/A can be forged
# by an untrusted local process, and is *always* only a diagnostic.
for browser_id in range(403, 418):
    alt = baseline()
    alt["samples"][1]["temporary_browser_window_id"] = browser_id
    assert review_focus_sequence(alt)["browser_to_sway_identity_verified"] is False

for patch in (
    lambda d: d["samples"][2].update(focused_host_container_id=103),
    lambda d: d["samples"][1].update(focused_host_container_id=101),
    lambda d: d["samples"][2].update(temporary_browser_window_id=403),
    lambda d: d["samples"][1].update(temporary_browser_window_id=401),
):
    variant = baseline()
    patch(variant)
    answer = review_focus_sequence(variant)
    assert answer["status"] == "unbound_focus_pattern"
    assert answer["safe_actions"] == []
    assert answer["restore_allowed"] is False

for patch in (
    lambda d: d.update(private_url="https://private.invalid"),
    lambda d: d.update(kind="machine-brave-verified-session-v1"),
    lambda d: d.update(challenge="BAD"),
    lambda d: d.update(challenge=str(uuid.UUID(int=42)).upper()),
    lambda d: d.update(gesture="automatic_background_run"),
    lambda d: d.update(browser_private_windows_excluded=False),
    lambda d: d.update(host_private_exclusion_verified=True),
    lambda d: d.update(transport_origin_authenticated=True),
    lambda d: d["samples"].append(copy.deepcopy(d["samples"][0])),
    lambda d: d["samples"].pop(),
    lambda d: d["samples"].reverse(),
    lambda d: d["samples"][0].update(url="https://private.invalid"),
    lambda d: d["samples"][0].update(focused_host_container_id=True),
    lambda d: d["samples"][0].update(temporary_browser_window_id=False),
    lambda d: d["samples"][0].update(host_stable_two_reads=False),
    lambda d: d["samples"][0].update(host_app_id="kitty"),
    lambda d: d["samples"][0].update(host_app_id=["brave-browser"]),
    lambda d: d["samples"][0].update(host_app_id={"value": "brave-browser"}),
    lambda d: d["samples"][0].update(host_app_id=True),
    lambda d: d["samples"][0].update(requested_at_ms=-1),
    lambda d: d["samples"][0].update(requested_at_ms=1.1),
    lambda d: d["samples"][0].update(observed_at_ms=3200),
    lambda d: d["samples"][1].update(requested_at_ms=1090),
    lambda d: d["samples"][2].update(observed_at_ms=11000),
    lambda d: d["samples"][2].update(observed_at_ms=10**20),
):
    denied(patch)

# Verify the pure review never widens the installed Brave pilot or runtime.
manifest = json.loads((ROOT / "integrations/machine/brave-topology/manifest.json").read_text())
assert manifest["permissions"] == []
assert manifest["host_permissions"] == []
assert manifest["optional_permissions"] == ["nativeMessaging"]
assert manifest["incognito"] == "not_allowed"
assert "background" not in manifest
qml = (ROOT / "widgets/TimeW.qml").read_text()
assert "MachineBraveFocusSequenceReview" not in qml
host = (ROOT / "services/time/MachineBraveNativeProbe.py").read_text()
assert "MachineBraveFocusSequenceReview" not in host
code = (ROOT / "services/time/MachineBraveFocusSequenceReview.py").read_text()
for dangerous in ("swaymsg", "subprocess.run", "chrome.windows.update",
                  "sendNativeMessage", "sqlite3", "open(", "write_text(",
                  "chmod(", "os.system(", "eval(", "exec("):
    assert dangerous not in code, dangerous

print("MACHINE Brave focus sequence // A-B-A diagnostic only, fail-closed PASS")
