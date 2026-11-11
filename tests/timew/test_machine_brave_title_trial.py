#!/usr/bin/env python3
"""MACHINE disposable title marker: no ordinary host install or source overwrite."""
import json
from pathlib import Path
import shutil
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveDisposableTrial import init_trial, register_trial, TrialError
from MachineBraveFocusTrial import register_focus, verify_focus
from MachineBraveTitleTrial import (
    register, verify, MODULES, HOST, MANIFEST
)
import MachineBraveTitleTrial as mark

EXT = "a"*32
roots = []


def make():
    path = Path(init_trial()["trial_root"])
    roots.append(path)
    register_trial(str(path), EXT)
    register_focus(str(path), EXT)
    return path


def refuse(fn):
    try:
        fn()
    except (TrialError, ValueError, OSError):
        return
    raise AssertionError("unsafe registration accepted")


try:
    root = make()
    dir = root / "xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    transport = dir / "org.postapollo.machine_brave_probe.json"
    focus = dir / "org.postapollo.machine_brave_focus_observe.json"
    original = (transport.read_bytes(), focus.read_bytes())
    result = register(str(root), EXT)
    assert result["status"] == "disposable_title_marker_registration_verified"
    assert result["restore_allowed"] is False
    assert result["persistent_identity_verified"] is False
    assert verify(str(root)) == result
    assert (transport.read_bytes(), focus.read_bytes()) == original
    marker = dir / MANIFEST
    meta = json.loads(marker.read_text())
    assert meta["allowed_origins"] == ["chrome-extension://"+EXT+"/"]
    assert meta["path"] == str(root / HOST)
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    for name in MODULES:
        target = root / name
        assert stat.S_IMODE(target.stat().st_mode) == (
            0o700 if name == HOST else 0o600)
    refuse(lambda: register(str(root), EXT))
    refuse(lambda: register(str(root), "b"*32))
    refuse(lambda: register(str(Path.home()), EXT))

    target = root / MODULES[1]
    old = target.read_bytes()
    target.write_bytes(b"changed")
    refuse(lambda: verify(str(root)))
    target.write_bytes(old)
    assert verify(str(root)) == result

    symlink_trial = make()
    (symlink_trial / HOST).symlink_to("/etc/passwd")
    refuse(lambda: register(str(symlink_trial), EXT))
    assert not (symlink_trial / MODULES[1]).exists()
    assert not (symlink_trial / "xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts" / MANIFEST).exists()

    rollback_trial = make()
    previous_write = mark._write_exclusive
    def fail_manifest(path, data, mode):
        if path.name == MANIFEST:
            raise OSError("injected manifest write failure")
        return previous_write(path, data, mode)
    try:
        mark._write_exclusive = fail_manifest
        refuse(lambda: register(str(rollback_trial), EXT))
    finally:
        mark._write_exclusive = previous_write
    assert not (rollback_trial / HOST).exists()
    assert not (rollback_trial / MODULES[1]).exists()
    assert not (rollback_trial / "xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts" / MANIFEST).exists()
finally:
    for root in roots:
        assert root.parent == Path("/tmp")
        assert root.name.startswith("postapollo-machine-brave-trial-")
        shutil.rmtree(root)

print("MACHINE title marker isolated registration // rollback and no overwrite PASS")
