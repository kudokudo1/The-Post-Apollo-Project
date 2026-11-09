#!/usr/bin/env python3
"""Read-only Sway focus witness + conservative cross-source Brave review."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import uuid
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/time"))
from MachineBraveFocusWitness import (
    FocusWitnessError, _focused_leaf, inspect_focus)
from MachineBraveHostPairingReview import (
    PairingReviewError, review_independent_observations)


def uid(number):
    return uuid.UUID(int=number)


def tree(focused=101, *, app="brave-browser", private_marker=False):
    one = {
        "type": "con", "id": 101, "focused": focused == 101,
        "app_id": app, "name": "PRIVATE EXCLUDED TAB",
        "pid": 123456, "nodes": [], "floating_nodes": [],
    }
    two = {
        "type": "con", "id": 102, "focused": focused == 102,
        "app_id": "brave-browser", "name": "SENSITIVE BANK WINDOW",
        "pid": 789101, "nodes": [], "floating_nodes": [],
    }
    if private_marker:
        one["incognito"] = True  # Sway cannot authenticate this browser flag
    return {
        "type": "root", "nodes": [{
            "type": "output", "name": "DP-3", "nodes": [{
                "type": "workspace", "name": "1", "nodes": [one, two],
                "floating_nodes": [],
            }], "floating_nodes": [],
        }], "floating_nodes": [],
    }


class FakeRunner:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.calls = []

    def __call__(self, argv, **kwargs):
        assert argv == ["swaymsg", "-r", "-t", "get_tree"]
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is True
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 3
        self.calls.append(tuple(argv))
        return SimpleNamespace(stdout=json.dumps(next(self.frames)).encode())


def refuses(fn, exc_class):
    try:
        fn()
    except exc_class:
        return
    raise AssertionError("unsafe witness or correlation accepted")


def browser_frame(window_count=17):
    return {
        "kind": "machine-brave-window-topology-readonly-v1",
        "status": "ready", "read_only": True,
        "capture_scope": "browser_window_counts_only",
        "private_windows_included": False,
        "title_url_contents_included": False,
        "temporary_ids_only": True,
        "sway_window_binding_verified": False,
        "restart_session_identity_verified": False,
        "tabs_restorable": False, "safe_restore_actions": [],
        "counts": {
            "browser_windows": window_count,
            "tabs": window_count * 4,
            "pinned_tabs": window_count,
        },
        "windows": [{
            "temporary_browser_window_id": 400 + i,
            "current_browser_window": i == 6,
            "tab_count": 4, "pinned_tab_count": 1, "active_tab_index": 1,
        } for i in range(window_count)],
    }


runner = FakeRunner([tree(), tree()])
proof = inspect_focus(runner=runner, new_id=lambda: uid(2048))
assert len(runner.calls) == 2
assert proof == {
    "kind": "machine-sway-brave-focus-witness-v1",
    "status": "brave_focus_observed",
    "read_only": True,
    "browser_window_id": None,
    "sway_window_binding_verified": False,
    "browser_session_identity_verified": False,
    "private_window_exclusion_verified": False,
    "session_restorable": False,
    "action_allowed": False,
    "safe_actions": [],
    "observation_id": str(uid(2048)),
    "reported_app_id": "brave-browser",
    "output": "DP-3", "workspace": "1",
    "same_focused_client_in_two_reads": True,
}
assert "PRIVATE EXCLUDED TAB" not in json.dumps(proof)
assert "SENSITIVE BANK WINDOW" not in json.dumps(proof)
for private in ("pid", "con_id", "incognito", "title", "url", "window_id"):
    assert '"' + private + '"' not in json.dumps(proof), private

browser = browser_frame()
before = copy.deepcopy(browser)
review = review_independent_observations(browser, proof)
assert browser == before
assert review == {
    "kind": "machine-brave-host-observation-review-v1",
    "status": "unverified_focus_candidate",
    "read_only": True,
    "browser_windows": 17,
    "browser_current_window_reported": True,
    "host_focused_brave_reported": True,
    "candidate_browser_window_id": 406,
    "host_observation_id": str(uid(2048)),
    "observation_only": True,
    "browser_to_sway_identity_verified": False,
    "operator_confirmation_is_identity_proof": False,
    "private_window_exclusion_verified_by_host": False,
    "restart_session_identity_verified": False,
    "exact_session_match": False,
    "action_allowed": False,
    "safe_actions": [],
}
assert "SENSITIVE BANK WINDOW" not in json.dumps(review)
assert "DP-3" not in json.dumps(review)  # placement stays on the host witness
assert "brave-browser" not in json.dumps(review)
assert review["safe_actions"] == []

# Focus changed mid-observation; one stable client was not witnessed.
changed = inspect_focus(
    runner=FakeRunner([tree(focused=101), tree(focused=102)]))
assert changed["status"] == "focus_changed"
assert "observation_id" not in changed
assert review_independent_observations(browser, changed)["status"] == "unbound"
missing = inspect_focus(runner=FakeRunner([tree(focused=None), tree(focused=None)]))
assert missing["status"] == "no_focused_client"
non_brave = inspect_focus(runner=FakeRunner([
    tree(app="kitty"), tree(app="kitty")]))
assert non_brave["status"] == "not_brave_focused"
assert review_independent_observations(browser, non_brave)["status"] == "unbound"

# Incognito is not reliably visible to Sway. No proof of private-window
# exclusion is EVER emitted, even with an explicit mock flag.
private = inspect_focus(runner=FakeRunner([
    tree(private_marker=True), tree(private_marker=True)]))
assert private["private_window_exclusion_verified"] is False
assert review_independent_observations(browser, private)[
    "private_window_exclusion_verified_by_host"] is False

# Xwayland Brave class is allowed, but still observational only.
class_based = tree()
class_based["nodes"][0]["nodes"][0]["nodes"][0]["app_id"] = None
class_based["nodes"][0]["nodes"][0]["nodes"][0]["window_properties"] = {
    "class": "Brave-browser", "title": "SECRET", "instance": "private"}
xwin = inspect_focus(runner=FakeRunner([class_based, class_based]))
assert xwin["reported_app_id"] == "Brave-browser"
assert xwin["sway_window_binding_verified"] is False

# Ambiguity, malformed inputs, unbounded nesting and read failures refuse.
amb = tree()
amb["nodes"][0]["nodes"][0]["nodes"][1]["focused"] = True
refuses(lambda: _focused_leaf(amb), FocusWitnessError)
bad = tree()
bad["nodes"][0]["nodes"][0]["nodes"][0]["id"] = "fake"
refuses(lambda: _focused_leaf(bad), FocusWitnessError)
huge = {"type": "root", "nodes": [{"type": "root", "nodes": []}
          for _ in range(513)]}
refuses(lambda: _focused_leaf(huge), FocusWitnessError)
refuses(lambda: _focused_leaf("not tree"), FocusWitnessError)
def failed_runner(argv, **options):
    raise OSError("/var/home/PRIVATE/sway.sock")
refuses(lambda: inspect_focus(runner=failed_runner), FocusWitnessError)

# Browser identity / title / URL impersonation, mismatched count and
# unsupported permission/security claims all fail without an action.
for field, value in [
    ("sway_window_binding_verified", True),
    ("restart_session_identity_verified", True),
    ("tabs_restorable", True),
    ("private_windows_included", True),
    ("safe_restore_actions", ["move"]),
]:
    forged = copy.deepcopy(browser)
    forged[field] = value
    refuses(lambda data=forged: review_independent_observations(
        data, proof), PairingReviewError)

for modifier in (
    lambda d: d["windows"][1].update(temporary_browser_window_id=400),
    lambda d: d["windows"][1].update(current_browser_window=True),
    lambda d: d["windows"][0].update(url="https://private.invalid"),
    lambda d: d["windows"][0].update(active_tab_index=99),
    lambda d: d["counts"].update(tabs=1),
    lambda d: d["counts"].update(tabs=True),
    lambda d: d["counts"].update(pinned_tabs=True),
    lambda d: d.update(cookie="PRIVATE"),
):
    forged = copy.deepcopy(browser)
    modifier(forged)
    refuses(lambda data=forged: review_independent_observations(
        data, proof), PairingReviewError)

for modifier in (
    lambda d: d.update(sway_window_binding_verified=True),
    lambda d: d.update(private_window_exclusion_verified=True),
    lambda d: d.update(browser_window_id=406),
    lambda d: d.update(session_restorable=True),
    lambda d: d.update(action_allowed=True),
    lambda d: d.update(observation_id="BAD"),
    lambda d: d.update(output="DP-3\\nSECRET"),
    lambda d: d.update(workspace="1\\tPRIVATE"),
    lambda d: d.update(pid=1234),
    lambda d: d.update(safe_actions=["restore"]),
):
    forged = copy.deepcopy(proof)
    modifier(forged)
    refuses(lambda data=forged: review_independent_observations(
        browser, data), PairingReviewError)

unfocused_browser = copy.deepcopy(browser)
unfocused_browser["windows"][6]["current_browser_window"] = False
unbound = review_independent_observations(unfocused_browser, proof)
assert unbound["status"] == "unbound"
assert unbound["host_focused_brave_reported"]
assert unbound["candidate_browser_window_id"] is None

# The explicit CLI, when given unsupported action, rejects before any Sway
# IPC, and avoids echoing private environment or filesystem details.
cli = Path(__file__).resolve().parents[2] / "services/time/MachineBraveFocusWitness.py"
bad_action = subprocess.run(
    ["python3", "-B", "-I", str(cli), "restore"],
    capture_output=True, timeout=6)
assert bad_action.returncode == 1
assert json.loads(bad_action.stdout) == {
    "status": "error", "reason": "INVALID ACTION"}
assert not bad_action.stderr

print("MACHINE Brave focus // Sway read-only witness + unverified pairing boundary PASS")
