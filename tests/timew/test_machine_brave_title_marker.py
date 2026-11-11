#!/usr/bin/env python3
"""MACHINE: synthetic title-marker observation, refusal, native framing."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveTitleMarkerWitness import (
    inspect_marker, TITLE_PREFIX, MarkerWitnessError, _challenge
)
from MachineBraveNativeTitleMarker import (
    handle, MarkerHostError, REQUEST_KIND, RESPONSE_KIND
)
from MachineBraveNativeTitleManifest import generate, HOST_NAME

TOKEN = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ORIGIN = "chrome-extension://" + "a"*32 + "/"


def tree(*, title_suffix=" - Brave", focused=10, app="brave-browser",
         duplicate=False, output="DP-3", workspace="1"):
    label = TITLE_PREFIX + TOKEN + title_suffix
    children = [
        {"type": "con", "id": 10, "focused": focused == 10,
         "name": label, "pid": 1313, "app_id": app,
         "nodes": [], "floating_nodes": []},
        {"type": "con", "id": 20, "focused": focused == 20,
         "name": label if duplicate else "PRIVATE FINANCE SESSION",
         "pid": 4141, "app_id": "brave-browser",
         "nodes": [], "floating_nodes": []},
    ]
    return {"type": "root", "nodes": [
        {"type": "output", "name": output, "nodes": [
            {"type": "workspace", "name": workspace, "nodes": children,
             "floating_nodes": []}], "floating_nodes": []}],
        "floating_nodes": []}


class Runner:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.commands = []
    def __call__(self, command, **kwargs):
        assert command == ["swaymsg", "-r", "-t", "get_tree"]
        assert kwargs == {"check":True, "capture_output":True,
                          "timeout":3, "shell":False}
        self.commands.append(command)
        return SimpleNamespace(stdout=json.dumps(next(self.frames)).encode())


def witness(frames):
    run = Runner(frames)
    result = inspect_marker(TOKEN, runner=run)
    # Malformed first frames fail closed before a second read; valid input
    # uses exactly two snapshots and no other Sway commands.
    assert 1 <= len(run.commands) <= 2
    return result


expected = {"sway_container_id":10, "output":"DP-3", "workspace":"1"}
assert witness([tree(), tree()]) == expected
assert witness([tree(title_suffix=""), tree(title_suffix="")]) == expected
for frames in (
    [tree(duplicate=True), tree(duplicate=True)],
    [tree(focused=20), tree(focused=20)],
    [tree(app="kitty"), tree(app="kitty")],
    [tree(), tree(focused=20)],
    [tree(), tree(output="DP-5")],
    [tree(), tree(workspace="2")],
    [tree(title_suffix="x"), tree(title_suffix="x")],
    [tree(title_suffix=" - Fake"), tree(title_suffix=" - Fake")],
    [{"type":"root","nodes":[]}, {"type":"root","nodes":[]}],
    ["not a tree", "not a tree"],
):
    assert witness(frames) is None

for bad in (None, True, 123, "", TOKEN.upper(),
            "00000000-0000-0000-0000", "private data"):
    try:
        _challenge(bad)
    except MarkerWitnessError:
        pass
    else:
        raise AssertionError("bad marker accepted")

request = {"kind": REQUEST_KIND, "challenge": TOKEN}
run = Runner([tree(), tree()])
success = handle(request, origin=ORIGIN, runner=run)
assert success == {
    "kind": RESPONSE_KIND,
    "status": "transient_title_marker_observed",
    "challenge": TOKEN, "read_only_host": True,
    "marker_unique_and_stable": True,
    "sway_container_id":10, "output":"DP-3", "workspace":"1",
    "browser_window_id":None,
    "extension_origin_authenticated":False,
    "host_private_window_exclusion_verified":False,
    "persistent_window_identity_verified":False,
    "session_capture_allowed":False, "restore_allowed":False,
    "safe_actions":[],
}
assert "PRIVATE FINANCE" not in json.dumps(success)
assert '"pid"' not in json.dumps(success)
no_match = handle(request, origin=ORIGIN, runner=Runner([
    tree(focused=20), tree(focused=20)]))
assert no_match["status"] == "marker_not_observed"
assert no_match["sway_container_id"] is None
assert no_match["restore_allowed"] is False

for field, val in (
    ("url","https://private.example"), ("window_id",512),
    ("tabs",["banking"]), ("sway_id",10), ("restore",True),
    ("source_authenticated", True), ("incognito",False)
):
    bad = dict(request, **{field: val})
    try:
        handle(bad, origin=ORIGIN, runner=Runner([tree(),tree()]))
    except MarkerHostError:
        pass
    else:
        raise AssertionError("unexpected marker request accepted")

assert HOST_NAME == "org.postapollo.machine_brave_title_marker"
manifest = generate("a"*32, "/tmp/trial/MachineBraveNativeTitleMarker.py")
assert manifest["allowed_origins"] == [ORIGIN]
assert manifest["path"] == "/tmp/trial/MachineBraveNativeTitleMarker.py"
for args in (("bad", "/tmp/trial/MachineBraveNativeTitleMarker.py"),
             ("a"*32, "/etc/passwd"), ("a"*32, "relative")):
    try:
        generate(*args)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe manifest accepted")

# A subprocess missing Sway availability returns a clean, non-authorizing
# framed reply without leaking its environment or stderr.
host = ROOT / "services/time/MachineBraveNativeTitleMarker.py"
payload = json.dumps(request).encode()
proc = subprocess.run(
    [sys.executable, "-B", "-I", str(host), ORIGIN],
    input=struct.pack("=I", len(payload))+payload,
    capture_output=True, timeout=8, check=False, env={
        "PATH":"/usr/bin:/bin", "HOME":"/nonexistent",
        "XDG_CONFIG_HOME":"/nonexistent",
    })
assert proc.returncode == 0 and not proc.stderr
(length,) = struct.unpack("=I", proc.stdout[:4])
assert len(proc.stdout)-4 == length
result = json.loads(proc.stdout[4:])
assert result["status"] == "marker_not_observed"
assert result["safe_actions"] == []
print("MACHINE title marker witness // unique, focused, private-safe, no actions PASS")
