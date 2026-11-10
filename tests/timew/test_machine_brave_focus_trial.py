#!/usr/bin/env python3
"""Isolated /tmp trial register/verify: no normal-profile or overwrite rights."""
import json
import os
from pathlib import Path
import shutil
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineBraveDisposableTrial import init_trial, register_trial, TrialError
from MachineBraveFocusTrial import (
    register_focus, verify_focus, REQUIRED_MODULES, MANIFEST_FILE
)

EXT_ID = "a" * 32
created = []


def trial():
    result = init_trial()
    root = Path(result["trial_root"])
    assert str(root).startswith("/tmp/postapollo-machine-brave-trial-")
    created.append(root)
    register_trial(str(root), EXT_ID)
    return root


def refuses(action):
    try:
        action()
    except (TrialError, ValueError):
        return
    raise AssertionError("Unsafe focus installation accepted")


try:
    root = trial()
    probe_before = (root / "MachineBraveNativeProbe.py").read_bytes()
    registry = root / "xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
    original = registry / "org.postapollo.machine_brave_probe.json"
    probe_manifest_before = original.read_bytes()

    expected = register_focus(str(root), EXT_ID)
    assert expected["status"] == "disposable_focus_observation_registration_verified"
    assert expected["extension_id_matches_transport_probe"] is True
    assert expected["browser_to_sway_identity_verified"] is False
    assert expected["sway_focus_observed_live"] is False
    assert expected["restore_allowed"] is False
    assert verify_focus(str(root)) == expected
    assert original.read_bytes() == probe_manifest_before
    assert (root / "MachineBraveNativeProbe.py").read_bytes() == probe_before
    assert (root / "profile").is_dir()

    focus_manifest = registry / MANIFEST_FILE
    manifest = json.loads(focus_manifest.read_text())
    assert manifest["name"] == "org.postapollo.machine_brave_focus_observe"
    assert manifest["allowed_origins"] == ["chrome-extension://" + EXT_ID + "/"]
    assert manifest["path"] == str(root / "MachineBraveNativeFocusObserve.py")
    assert stat.S_IMODE(focus_manifest.stat().st_mode) == 0o600
    for name in REQUIRED_MODULES:
        file = root / name
        assert stat.S_IMODE(file.stat().st_mode) == (
            0o700 if name == "MachineBraveNativeFocusObserve.py" else 0o600)
    refuses(lambda: register_focus(str(root), EXT_ID))
    refuses(lambda: register_focus(str(root), "b" * 32))
    refuses(lambda: register_focus(os.path.expanduser("~/.config/BraveSoftware"), EXT_ID))
    refuses(lambda: verify_focus("/tmp/unmarked-regular-folder"))

    # A changed source file, wrong mode or altered manifest must fail closed.
    target = root / "MachineBraveFocusWitness.py"
    old_mode = stat.S_IMODE(target.stat().st_mode)
    target.chmod(0o644)
    refuses(lambda: verify_focus(str(root)))
    target.chmod(old_mode)
    target.write_bytes(b"forged")
    refuses(lambda: verify_focus(str(root)))

    symlink_root = trial()
    link = symlink_root / "MachineBraveNativeFocusObserve.py"
    link.symlink_to("/etc/passwd")
    refuses(lambda: register_focus(str(symlink_root), EXT_ID))
    assert not (registry / "irrelevant").exists()
    assert not (symlink_root / "MachineSwayRead.py").exists()

finally:
    for path in created:
        # Only CI-created roots from init_trial() are cleaned up.
        assert path.parent == Path("/tmp")
        assert path.name.startswith("postapollo-machine-brave-trial-")
        shutil.rmtree(path)

print("MACHINE focus host disposable registration // strict isolation PASS")
