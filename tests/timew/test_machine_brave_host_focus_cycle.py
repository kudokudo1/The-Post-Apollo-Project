#!/usr/bin/env python3
"""MACHINE host A/B/A: no browser/OS identity claim, no Sway actuation."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveHostFocusCycle import (
    HostCycleError, inspect_cycle, STEPS, STEP_SECONDS,
)


def frame(focused, *, focus_app="brave-browser"):
    def leaf(n):
        return {
            "type": "con",
            "id": n,
            "app_id": focus_app if n == focused else "brave-browser",
            "focused": n == focused,
            "name": "SENSITIVE SECRET TITLE",
            "pid": 99100 + n,
            "nodes": [],
            "floating_nodes": [],
        }
    return {
        "type": "root", "nodes": [{
            "type": "output", "name": "DP-3", "nodes": [{
                "type": "workspace", "name": "1", "nodes": [
                    leaf(101), leaf(102), leaf(103),
                ], "floating_nodes": [],
            }], "floating_nodes": [],
        }], "floating_nodes": [],
    }


class FakeSway:
    def __init__(self, trees):
        self.trees = iter(trees)
        self.commands = []

    def __call__(self, command, **kwargs):
        assert command == ["swaymsg", "-r", "-t", "get_tree"]
        assert kwargs == {
            "check": True, "capture_output": True, "timeout": 3,
            "shell": False,
        }
        self.commands.append(tuple(command))
        return SimpleNamespace(
            stdout=json.dumps(next(self.trees)).encode("utf-8")
        )


def frames(*focuses):
    return [frame(n) for n in focuses for _ in range(2)]


def inspect(trees):
    prompts, waits = [], []
    fake = FakeSway(trees)
    answer = inspect_cycle(
        runner=fake,
        pause=lambda secs: waits.append(secs),
        announce=lambda step: prompts.append(step),
    )
    assert prompts == list(STEPS)
    assert waits == [STEP_SECONDS] * 3
    assert len(fake.commands) == 6
    return answer


passed = inspect(frames(101, 102, 101))
assert passed == {
    "kind": "machine-sway-brave-host-focus-cycle-v1",
    "status": "consistent_unverified_host_focus_cycle",
    "observed_steps": 3,
    "read_only": True,
    "browser_window_id": None,
    "browser_to_sway_identity_verified": False,
    "extension_origin_authenticated": False,
    "private_window_exclusion_verified": False,
    "restart_session_identity_verified": False,
    "session_capture_allowed": False,
    "restore_allowed": False,
    "action_allowed": False,
    "safe_actions": [],
}
as_json = json.dumps(passed)
for secret in (
        "SENSITIVE SECRET TITLE", "99101", "99102", "101", "102",
        "brave-browser", "DP-3", "PRIVATE", "URL", "tab"):
    assert secret not in as_json, secret

for sequence in ((101, 101, 101), (101, 102, 103),
                 (102, 101, 103), (102, 102, 101)):
    answer = inspect(frames(*sequence))
    assert answer["status"] == "unbound_host_focus_cycle"
    assert answer["action_allowed"] is False

# A compositor client switching between the two reads cannot be correlated.
bad = FakeSway([
    frame(101), frame(102), frame(102), frame(102), frame(101), frame(101)
])
try:
    inspect_cycle(runner=bad, pause=lambda _: None)
except HostCycleError:
    pass
else:
    raise AssertionError("unstable focus accepted")

# The operator may accidentally select a terminal or a non-Brave app.
bad = frames(101, 102, 101)
bad[2] = frame(102, focus_app="kitty")
bad[3] = frame(102, focus_app="kitty")
try:
    inspect(bad)
except HostCycleError:
    pass
else:
    raise AssertionError("other application accepted")

# Separate CLI refuses every action besides an explicit opt-in 'inspect'.
cli = ROOT / "services/time/MachineBraveHostFocusCycle.py"
for args in ([], ["--help"], ["capture"], ["restore"], ["inspect", "--all"]):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(cli), *args],
        timeout=5, capture_output=True, check=False,
    )
    assert result.returncode == 1 and not result.stderr
    assert json.loads(result.stdout)["reason"] == "INVALID ACTION"

source = cli.read_text()
for forbidden in (
        "chrome.windows.update(", "swaymsg focus", "swaymsg move",
        "sendNativeMessage(", "Popen(", "os.system(", "sqlite3",
        ".write_text(", ".write_bytes(", "open(", "subprocess.call(",
        "restore_window(", "tabs.create("):
    assert forbidden not in source, forbidden
assert 'SWAY_TREE_CMD = ["swaymsg", "-r", "-t", "get_tree"]' in source
assert "private_window_exclusion_verified" in source
assert "browser_window_id\": None" in source

print("MACHINE host A/B/A focus continuity // no identity or actions PASS")
