#!/usr/bin/env python3
"""Disposable Brave native transport registration: real temp filesystem test."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveDisposableTrial import (
    TrialError, init_trial, register_trial, verify_trial, HOST_MANIFEST,
    HOST_FILE, MARKER,
)

import MachineBraveDisposableTrial as trial

EXT_ID = "a" * 32


def refused(callback):
    try:
        callback()
    except (TrialError, ValueError, OSError):
        return
    raise AssertionError("unsafe disposable-profile operation accepted")


def new_root():
    return Path(init_trial()["trial_root"])


def native_dir(root):
    return (root / "xdg-config" / "BraveSoftware" / "Brave-Browser"
            / "NativeMessagingHosts")


# Every write is in a unique, private /tmp fixture, not the user's profile.
# A caller-defined TMPDIR must never redirect trial writes into HOME.
old_tmp = os.environ.get("TMPDIR")
os.environ["TMPDIR"] = "/home/UNTRUSTED-NON-TEMP"
try:
    temp_override_root = new_root()
    assert temp_override_root.parent == Path("/tmp")
finally:
    if old_tmp is None:
        os.environ.pop("TMPDIR", None)
    else:
        os.environ["TMPDIR"] = old_tmp
    shutil.rmtree(temp_override_root)

root = new_root()
try:
    profile = root / "profile"
    assert root.stat().st_mode & 0o077 == 0
    assert profile.stat().st_mode & 0o077 == 0
    assert (root / "xdg-config").stat().st_mode & 0o077 == 0
    assert (root / MARKER).is_file()
    assert not native_dir(root).exists()
    refused(lambda: verify_trial(str(root)))
    for invalid in ("", "z" * 32, EXT_ID[:-1], "../" + EXT_ID,
                    EXT_ID + "\n", None, 123):
        refused(lambda identifier=invalid: register_trial(str(root), identifier))
        assert not native_dir(root).exists()
        assert not (root / HOST_FILE).exists()

    result = register_trial(str(root), EXT_ID)
    assert result["status"] == "disposable_trial_registration_verified"
    assert result["brave_user_data_dir"] == str(profile)
    assert result["registration_scoped_to_disposable_trial"] is True
    assert result["brave_xdg_config_home"] == str(root / "xdg-config")
    assert result["native_host_manifest"] == str(native_dir(root) / HOST_MANIFEST)
    assert result["host_source_matches_repo"] is True
    for key in ("browser_launched_by_tool", "local_transport_tested",
                "extension_origin_authenticated", "window_identity_verified",
                "session_capture_allowed", "restore_allowed"):
        assert result[key] is False
    assert result["safe_actions"] == []
    host = root / HOST_FILE
    native = native_dir(root)
    manifest_file = native / HOST_MANIFEST
    assert host.is_file() and os.access(host, os.X_OK)
    assert host.stat().st_mode & 0o077 == 0
    assert manifest_file.is_file()
    assert manifest_file.stat().st_mode & 0o077 == 0
    manifest = json.loads(manifest_file.read_text())
    assert manifest["allowed_origins"] == ["chrome-extension://" + EXT_ID + "/"]
    assert manifest["path"] == str(host)
    assert manifest["type"] == "stdio"
    assert verify_trial(str(root)) == result

    before = {str(p.relative_to(root)): p.read_bytes()
              for p in root.rglob("*") if p.is_file()}
    assert verify_trial(str(root)) == result
    after = {str(p.relative_to(root)): p.read_bytes()
             for p in root.rglob("*") if p.is_file()}
    assert before == after, "verify unexpectedly wrote profile data"
    refused(lambda: register_trial(str(root), "b" * 32))
    assert verify_trial(str(root)) == result, "duplicate registration mutated trial"

    # Verify validates the exact bytes, not merely plausible JSON.
    manifest_file.write_text(json.dumps(dict(manifest, path="/bin/sh")))
    refused(lambda: verify_trial(str(root)))
    manifest_file.write_text(json.dumps(manifest))
    assert verify_trial(str(root)) == result
    host.write_bytes(host.read_bytes() + b"\n# modified\n")
    refused(lambda: verify_trial(str(root)))
finally:
    shutil.rmtree(root)

# An interrupted O_EXCL write cannot leave a partially registered host.
root = new_root()
try:
    partial = root / "partially-written-native-host"
    original = trial.os.fdopen
    def fail_open(fd, mode):
        raise OSError("injected file-wrapper failure")
    trial.os.fdopen = fail_open
    try:
        refused(lambda: trial._write_exclusive(partial, b"partial", 0o600))
    finally:
        trial.os.fdopen = original
    assert not partial.exists()
finally:
    shutil.rmtree(root)

# A preexisting path, symlink, fake trial marker, or another directory
# must never be accepted, no matter how plausible the ID.
root = new_root()
try:
    other = root / "external"
    other.mkdir(mode=0o700)
    (root / "profile").rmdir()
    (root / "profile").symlink_to(other, target_is_directory=True)
    refused(lambda: register_trial(str(root), EXT_ID))
    assert not (other / "NativeMessagingHosts").exists()
    assert not native_dir(root).exists()
finally:
    shutil.rmtree(root)

root = new_root()
try:
    (root / MARKER).write_text('{"kind":"wrong","trial_id":"bad"}')
    refused(lambda: register_trial(str(root), EXT_ID))
    assert not (root / HOST_FILE).exists()
finally:
    shutil.rmtree(root)

root = new_root()
try:
    (root / HOST_FILE).symlink_to("/dev/null")
    refused(lambda: register_trial(str(root), EXT_ID))
    assert not native_dir(root).exists()
finally:
    shutil.rmtree(root)

# Refuse a symlinked nested XDG directory without writing outside trial.
root = new_root()
try:
    (root / "xdg-config" / "BraveSoftware").symlink_to(
        "/tmp", target_is_directory=True)
    refused(lambda: register_trial(str(root), EXT_ID))
    assert not (root / HOST_FILE).exists()
finally:
    shutil.rmtree(root)

# A browser may have created the first two XDG folders; honor private ones.
root = new_root()
try:
    existing = root / "xdg-config" / "BraveSoftware" / "Brave-Browser"
    existing.parent.mkdir(mode=0o700)
    existing.mkdir(mode=0o700)
    assert register_trial(str(root), EXT_ID)["status"] == "disposable_trial_registration_verified"
    assert native_dir(root).is_dir()
finally:
    shutil.rmtree(root)

# Abort a failed manifest write without leaving a half-registered native host.
root = new_root()
original_write = trial._write_exclusive
def fail_manifest(path, contents, mode):
    if path.name == HOST_MANIFEST:
        raise OSError("injected manifest write failure")
    return original_write(path, contents, mode)
try:
    trial._write_exclusive = fail_manifest
    refused(lambda: register_trial(str(root), EXT_ID))
    assert not (root / HOST_FILE).exists()
    assert not native_dir(root).exists()
    assert not (root / "xdg-config" / "BraveSoftware").exists()
finally:
    trial._write_exclusive = original_write
    shutil.rmtree(root)

# A nested, non-temp, or ordinary user profile path is out of scope.
refused(lambda: register_trial("/home/example/.config/BraveSoftware/Brave-Browser", EXT_ID))
refused(lambda: verify_trial("/tmp/other/BraveSoftware/Brave-Browser"))

# Real CLI (isolated Python interpreter): init -> register -> verify,
# no Brave/Sway launch and no storage beyond the generated trial root.
cli = ROOT / "services/time/MachineBraveDisposableTrial.py"
def cli_call(*args):
    return subprocess.run(["python3", "-B", "-I", str(cli), *args],
                          capture_output=True, timeout=7, check=False)

made = cli_call("init")
assert made.returncode == 0 and not made.stderr
created = json.loads(made.stdout)
cli_root = Path(created["trial_root"])
try:
    assert created["status"] == "disposable_trial_initialized"
    assert created["registration_present"] is False
    assert created["browser_launched_by_tool"] is False
    assert (cli_root / "xdg-config").is_dir()
    assert not native_dir(cli_root).exists()
    registered = cli_call("register", str(cli_root), EXT_ID)
    assert registered.returncode == 0 and not registered.stderr
    registered_data = json.loads(registered.stdout)
    assert registered_data["status"] == "disposable_trial_registration_verified"
    assert registered_data["native_host_manifest"] == str(native_dir(cli_root) / HOST_MANIFEST)
    assert native_dir(cli_root).is_dir()
    assert not (cli_root / "profile" / "NativeMessagingHosts").exists()
    verified = cli_call("verify", str(cli_root))
    assert verified.returncode == 0 and not verified.stderr
    assert json.loads(verified.stdout) == json.loads(registered.stdout)
    rejected = cli_call("register", str(cli_root), EXT_ID)
    assert rejected.returncode == 1
    assert json.loads(rejected.stdout) == {"status": "refused", "safe_actions": []}
    assert not rejected.stderr
finally:
    shutil.rmtree(cli_root)

manifest = json.loads((ROOT / "integrations/machine/brave-topology/manifest.json").read_text())
assert manifest["permissions"] == []
assert manifest["optional_permissions"] == ["nativeMessaging"]
assert manifest["host_permissions"] == []
assert manifest["incognito"] == "not_allowed"
assert "background" not in manifest
qml = (ROOT / "widgets/TimeW.qml").read_text()
assert "MachineBraveDisposableTrial" not in qml
native_host = (ROOT / "services/time/MachineBraveNativeProbe.py").read_text()
assert "swaymsg" not in native_host
assert "sqlite3" not in native_host
assert "MachineBraveDisposableTrial" not in native_host

print("MACHINE Brave // private disposable profile registration and read-only verification PASS")
