#!/usr/bin/env python3
"""Install the separate marker host ONLY inside a verified disposable trial.

Requires existing transport and focus registrations with the same extension.
Never updates ordinary XDG, Quickshell, a running browser or existing hosts.
"""
from __future__ import annotations

import json
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveDisposableTrial import (
    TrialError, _validate_root, _existing_manifest_dir,
    _read_regular, _write_exclusive,
)
from MachineBraveFocusTrial import verify_focus
from MachineBraveNativeTitleManifest import generate, HOST_NAME

MODULES = ("MachineBraveNativeTitleMarker.py", "MachineBraveTitleMarkerWitness.py")
HOST = MODULES[0]
MANIFEST = HOST_NAME + ".json"
MAX_SOURCE = 65536


def _source(name):
    if name not in MODULES:
        raise TrialError("INVALID SOURCE")
    data = Path(__file__).resolve().with_name(name).read_bytes()
    if not data or len(data) > MAX_SOURCE:
        raise TrialError("INVALID SOURCE")
    if name == HOST and not data.startswith(b"#!/usr/bin/env python3\n"):
        raise TrialError("INVALID HOST")
    return data


def verify(root_path):
    root = _validate_root(root_path)
    focus = verify_focus(str(root))
    if focus["status"] != "disposable_focus_observation_registration_verified":
        raise TrialError("UNVERIFIED FOCUS DEPENDENCY")
    for name in MODULES:
        target = root / name
        if _read_regular(target, MAX_SOURCE) != _source(name):
            raise TrialError("SOURCE MISMATCH")
        if stat.S_IMODE(target.stat().st_mode) != (
                0o700 if name == HOST else 0o600):
            raise TrialError("INVALID SOURCE MODE")
    meta = _existing_manifest_dir(root) / MANIFEST
    if stat.S_IMODE(meta.stat().st_mode) != 0o600:
        raise TrialError("INVALID MANIFEST MODE")
    try:
        parsed = json.loads(_read_regular(meta, 4096))
    except (ValueError, TypeError) as exc:
        raise TrialError("INVALID MANIFEST") from exc
    ext_id = parsed.get("allowed_origins", [None])[0]
    prefix = "chrome-extension://"
    if not isinstance(ext_id, str) or not ext_id.startswith(prefix):
        raise TrialError("INVALID ORIGIN")
    suffix = ext_id[len(prefix):].removesuffix("/")
    if parsed != generate(suffix, str(root / HOST)):
        raise TrialError("INVALID MANIFEST")
    return {
        "status": "disposable_title_marker_registration_verified",
        "trial_root": str(root),
        "exact_extension_id": suffix,
        "extension_origin_authenticated": False,
        "sway_title_marker_observed_live": False,
        "persistent_identity_verified": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def register(root_path, extension_id):
    root = _validate_root(root_path)
    focus = verify_focus(str(root))
    if focus["status"] != "disposable_focus_observation_registration_verified":
        raise TrialError("UNVERIFIED FOCUS HOST")
    manifest_path = _existing_manifest_dir(root) / MANIFEST
    # verify transport's real allowed origin rather than trusting the arg.
    focus_manifest = (_existing_manifest_dir(root)
                      / "org.postapollo.machine_brave_focus_observe.json")
    current = json.loads(_read_regular(focus_manifest, 4096))
    if current.get("allowed_origins") != [
            "chrome-extension://" + extension_id + "/"]:
        raise TrialError("EXTENSION DOES NOT MATCH")
    proposed = generate(extension_id, str(root / HOST))
    files = {root / name: _source(name) for name in MODULES}
    files[manifest_path] = (json.dumps(proposed, sort_keys=True, indent=2) + "\n").encode()
    for target in files:
        if target.exists() or target.is_symlink():
            raise TrialError("MARKER HOST ALREADY PRESENT")
    created = []
    try:
        for target, data in files.items():
            _write_exclusive(target, data, 0o700 if target.name == HOST else 0o600)
            created.append(target)
        return verify(str(root))
    except Exception:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        raise


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) == 3 and args[0] == "register":
            result = register(args[1], args[2])
        elif len(args) == 2 and args[0] == "verify":
            result = verify(args[1])
        else:
            return 2
    except (TrialError, OSError, ValueError, TypeError):
        print(json.dumps({"status": "refused", "safe_actions": []}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
