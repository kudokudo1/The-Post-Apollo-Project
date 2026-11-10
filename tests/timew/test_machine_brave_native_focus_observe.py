#!/usr/bin/env python3
"""MACHINE Brave native focus: bounded, non-authorizing, privacy-redacted."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveNativeFocusObserve import (
    HOST_NAME, REQUEST_KIND, RESPONSE_KIND, FocusObserveError, handle,
)
from MachineBraveNativeFocusManifest import generate

HOST = ROOT / "services/time/MachineBraveNativeFocusObserve.py"
ORIGIN = "chrome-extension://" + "a"*32 + "/"
CHALLENGE = str(uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"))
REQUEST = {"kind": REQUEST_KIND, "challenge": CHALLENGE}


def tree(focused=10, app="brave-browser"):
    return {
        "type": "root",
        "nodes": [{"type": "output", "name": "DP-3",
          "nodes": [{"type": "workspace", "name": "1",
            "nodes": [
                {"type": "con", "id": 10, "app_id": app,
                 "focused": focused == 10, "pid": 9991,
                 "name": "PRIVATE BANKING TAB", "nodes": [], "floating_nodes": []},
                {"type": "con", "id": 11, "app_id": "brave-browser",
                 "focused": focused == 11, "pid": 9992,
                 "name": "PRIVATE INCOGNITO TITLE", "nodes": [], "floating_nodes": []},
            ], "floating_nodes": [],
          }], "floating_nodes": [],
        }], "floating_nodes": [],
    }


class Runner:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.commands = []

    def __call__(self, argv, **kwargs):
        assert argv == ["swaymsg", "-r", "-t", "get_tree"]
        assert kwargs == {
            "check": True, "capture_output": True,
            "timeout": 3, "shell": False
        }
        self.commands.append(argv)
        return SimpleNamespace(stdout=json.dumps(next(self.frames)).encode())


def no_authority(reply):
    assert reply["browser_window_id"] is None
    assert reply["extension_origin_argument_observed"] is True
    for field in (
        "extension_origin_authenticated", "browser_to_sway_identity_verified",
        "private_window_exclusion_verified_by_host",
        "restart_session_identity_verified", "session_capture_allowed",
        "restore_allowed",
    ):
        assert reply[field] is False, field
    assert reply["read_only"] is True
    assert reply["safe_actions"] == []
    encoded = json.dumps(reply)
    for secret in (
        "PRIVATE BANKING", "PRIVATE INCOGNITO", "9991", "9992",
        '"id": 10', '"id": 11', '"pid"', '"title"', '"url"',
        '"tabs"', '"profile"', '"private_contents"',
    ):
        assert secret not in encoded, secret


run = Runner([tree(), tree()])
ok = handle(REQUEST, origin=ORIGIN, runner=run)
assert len(run.commands) == 2
assert ok["kind"] == RESPONSE_KIND and ok["challenge"] == CHALLENGE
assert ok["status"] == "host_brave_focus_observed_unverified"
assert ok["host_brave_focus_observed"] is True
assert ok["host_focus_stable_two_reads"] is True
assert ok["observed_output"] == "DP-3"
assert ok["observed_workspace"] == "1"
no_authority(ok)

for frames in (
    [tree(10), tree(11)],
    [tree(10, "kitty"), tree(10, "kitty")],
    [tree(None), tree(None)],
):
    failed = handle(REQUEST, origin=ORIGIN, runner=Runner(frames))
    assert failed["status"] == "no_host_focus_candidate"
    assert failed["host_brave_focus_observed"] is False
    assert failed["host_focus_stable_two_reads"] is False
    assert failed["observed_output"] is None
    assert failed["observed_workspace"] is None
    no_authority(failed)


def failed_runner(*args, **kwargs):
    raise OSError("Private WAYLAND socket path")


failure = handle(REQUEST, origin=ORIGIN, runner=failed_runner)
assert failure["status"] == "no_host_focus_candidate"
no_authority(failure)

for bad in (
    None, {}, [], {"kind": "restore", "challenge": CHALLENGE},
    {"kind": REQUEST_KIND, "challenge": CHALLENGE.upper()},
    {"kind": REQUEST_KIND, "challenge": "bad"},
    dict(REQUEST, window_id=99),
    dict(REQUEST, url="https://private.example"),
    dict(REQUEST, tabs=[{"title": "do not read"}]),
    dict(REQUEST, restore=True),
    dict(REQUEST, authenticated=True),
    dict(REQUEST, output="DP-3"),
):
    try:
        handle(bad, origin=ORIGIN, runner=Runner([tree(), tree()]))
    except FocusObserveError:
        pass
    else:
        raise AssertionError("Unsafe native request accepted")

for origin in ("", "https://site/", "chrome-extension://bad/",
               "chrome-extension://" + "a"*32, "chrome-extension://"+"z"*32+"/"):
    try:
        handle(REQUEST, origin=origin, runner=Runner([tree(), tree()]))
    except FocusObserveError:
        pass
    else:
        raise AssertionError("Untrusted caller format accepted")

assert HOST_NAME == "org.postapollo.machine_brave_focus_observe"
manifest = generate("a"*32, "/tmp/disposable/MachineBraveNativeFocusObserve.py")
assert manifest == {
    "name": HOST_NAME,
    "description": "MACHINE separate opt-in read-only Sway focus observation; no pairing or restoration",
    "path": "/tmp/disposable/MachineBraveNativeFocusObserve.py",
    "type": "stdio",
    "allowed_origins": [ORIGIN],
}
for args in (("bad", manifest["path"]), ("a"*32, "/etc/passwd"),
             ("a"*32, "MachineBraveNativeFocusObserve.py")):
    try:
        generate(*args)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe native manifest accepted")


def framed(request):
    data = json.dumps(request).encode()
    return struct.pack("=I", len(data)) + data


env = dict(os.environ)
for key in ("SWAYSOCK", "I3SOCK", "WAYLAND_DISPLAY"):
    env.pop(key, None)
for raw, expected_code in ((framed(REQUEST), 0),
                            (framed(dict(REQUEST, restore=True)), 1),
                            (struct.pack("=I", 8192), 1)):
    child = subprocess.run(
        [sys.executable, "-B", "-I", str(HOST), ORIGIN],
        input=raw, capture_output=True, timeout=8, env=env)
    assert child.returncode == expected_code
    assert not child.stderr
    assert len(child.stdout) >= 4
    length = struct.unpack("=I", child.stdout[:4])[0]
    assert length == len(child.stdout) - 4
    reply = json.loads(child.stdout[4:])
    assert reply["kind"] == RESPONSE_KIND
    assert reply["restore_allowed"] is False
    if expected_code == 0:
        assert reply["status"] == "no_host_focus_candidate"
        no_authority(reply)
    else:
        assert reply["status"] == "request_rejected"
        assert reply["safe_actions"] == []

print("MACHINE Brave native co-observation // bounded Sway and zero authority PASS")
