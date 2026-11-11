#!/usr/bin/env python3
"""MACHINE: install/verify the focus-only host inside an EXISTING marked trial.

No normal Brave profile or ordinary XDG paths are accepted. The transport
probe's registration remains untouched; the new focus host and four-module
dependency set are created exclusively inside the private /tmp trial.
Operator approval is required before any actual workstation registration.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveDisposableTrial import (
    TrialError, _validate_root, _existing_manifest_dir,
    _read_regular, _write_exclusive, verify_trial,
)
from MachineBraveNativeFocusManifest import generate, HOST_NAME

HOST = "MachineBraveNativeFocusObserve.py"
REQUIRED_MODULES = (
    HOST, "MachineBraveFocusWitness.py",
    "MachineSwayRead.py", "MachineCheckpointModel.py",
)
MANIFEST_FILE = HOST_NAME + ".json"
MAX_SOURCE = 65536


def _source(name):
    if name not in REQUIRED_MODULES:
        raise TrialError("UNSUPPORTED MODULE")
    source = Path(__file__).resolve().with_name(name).read_bytes()
    if len(source) == 0 or len(source) > MAX_SOURCE:
        raise TrialError("SOURCE SIZE INVALID")
    if name == HOST and not source.startswith(b"#!/usr/bin/env python3\n"):
        raise TrialError("UNEXPECTED HOST SOURCE")
    return source


def register_focus(root_path, extension_id):
    """One-shot, no overwrite, with rollback restricted to this invocation."""
    root = _validate_root(root_path)
    current = verify_trial(str(root))
    if current["exact_extension_id"] != extension_id:
        raise TrialError("EXTENSION ID DIFFERS FROM EXISTING PROBE")
    destination = _existing_manifest_dir(root)
    host = root / HOST
    manifest_path = destination / MANIFEST_FILE
    proposed = generate(extension_id, str(host))
    files = {root / name: _source(name) for name in REQUIRED_MODULES}
    files[manifest_path] = (
        json.dumps(proposed, sort_keys=True, indent=2) + "\n").encode()
    for name in files:
        if name.exists() or name.is_symlink():
            raise TrialError("FOCUS TRIAL ALREADY PRESENT")

    created = []
    try:
        for name, body in files.items():
            _write_exclusive(name, body, 0o700 if name == host else 0o600)
            created.append(name)
        return verify_focus(str(root))
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


def verify_focus(root_path):
    """Read-only, fail-closed exact-source/permission manifest review."""
    root = _validate_root(root_path)
    current = verify_trial(str(root))
    host = root / HOST
    for name in REQUIRED_MODULES:
        target = root / name
        content = _read_regular(target, MAX_SOURCE)
        mode = stat.S_IMODE(target.stat().st_mode)
        expected = 0o700 if name == HOST else 0o600
        if content != _source(name) or mode != expected:
            raise TrialError("FOCUS MODULE MISMATCH")

    target = _existing_manifest_dir(root) / MANIFEST_FILE
    body = _read_regular(target, 4096)
    if stat.S_IMODE(target.stat().st_mode) != 0o600:
        raise TrialError("FOCUS MANIFEST MODE MISMATCH")
    try:
        parsed = json.loads(body)
    except (ValueError, TypeError) as exc:
        raise TrialError("INVALID FOCUS MANIFEST") from exc
    if parsed != generate(current["exact_extension_id"], str(host)):
        raise TrialError("FOCUS MANIFEST MISMATCH")
    return {
        "status": "disposable_focus_observation_registration_verified",
        "trial_root": str(root),
        "extension_id_matches_transport_probe": True,
        "host_sources_match_repo": True,
        "registration_scoped_to_disposable_trial": True,
        "browser_launched_by_tool": False,
        "sway_focus_observed_live": False,
        "browser_to_sway_identity_verified": False,
        "session_capture_allowed": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) == 3 and args[0] == "register":
            result = register_focus(args[1], args[2])
        elif len(args) == 2 and args[0] == "verify":
            result = verify_focus(args[1])
        else:
            return 2
    except (TrialError, OSError, ValueError, TypeError):
        print(json.dumps({"status": "refused", "safe_actions": []}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
