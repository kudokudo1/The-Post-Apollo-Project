#!/usr/bin/env python3
"""MACHINE // Opt-in disposable-profile setup for the transport-only Brave host.

CLI operations:
  init                  create a new private TEMPORARY trial directory
  register ROOT ID      register an exact-ID host under isolated XDG_CONFIG_HOME
  verify ROOT           read-only check of the trial's manifest and host

Never launch Brave, contact Sway, read normal Brave profiles, run a native host,
save tabs, modify checkpoints or register a host in the user's real XDG home.
Running init/register on an operator's machine is itself a local write and
requires separate explicit approval. Repo CI uses disposable fixture roots.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveNativeManifest import generate, HOST_NAME

PREFIX = "postapollo-machine-brave-trial-"
MARKER = ".postapollo-machine-trial.json"
MARKER_KIND = "machine-brave-disposable-trial-v1"
HOST_FILE = "MachineBraveNativeProbe.py"
HOST_MANIFEST = HOST_NAME + ".json"
XDG_COMPONENTS = ("BraveSoftware", "Brave-Browser", "NativeMessagingHosts")
ROOT_NAME = re.compile(r"postapollo-machine-brave-trial-[a-zA-Z0-9_-]{6,}\Z")
ORIGIN = re.compile(r"chrome-extension://([a-p]{32})/\Z")
MAX_MARKER = 1024
MAX_HOST = 32768


class TrialError(ValueError):
    pass


def _private_dir(path):
    if path.is_symlink():
        raise TrialError("SYMLINK DIRECTORY REFUSED")
    try:
        info = path.stat()
    except OSError as exc:
        raise TrialError("DIRECTORY UNAVAILABLE") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise TrialError("UNSAFE DIRECTORY")


def _read_regular(path, limit):
    if path.is_symlink():
        raise TrialError("SYMLINK FILE REFUSED")
    try:
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_size > limit):
            raise TrialError("UNSAFE FILE")
        return path.read_bytes()
    except OSError as exc:
        raise TrialError("FILE UNAVAILABLE") from exc


def _write_exclusive(path, contents, mode):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, mode)
    try:
        stream = os.fdopen(fd, "wb")
    except Exception:
        os.close(fd)
        path.unlink(missing_ok=True)
        raise
    try:
        with stream:
            stream.write(contents)
    except Exception:
        # Only this O_EXCL-created file is removed on an interrupted write.
        path.unlink(missing_ok=True)
        raise


def _base():
    # Ignore TMPDIR overrides: never silently create trials under HOME,
    # an existing browser profile, a worktree or another configured path.
    candidate = Path("/tmp")
    if candidate.is_symlink():
        raise TrialError("UNSAFE TEMP ROOT")
    try:
        base = candidate.resolve(strict=True)
    except OSError as exc:
        raise TrialError("TEMP ROOT UNAVAILABLE") from exc
    if base != candidate or not base.is_dir():
        raise TrialError("UNSUPPORTED TEMP ROOT")
    return base


def _validate_root(value):
    if not isinstance(value, str):
        raise TrialError("INVALID TRIAL PATH")
    root = Path(value)
    base = _base()
    if (not root.is_absolute() or root.is_symlink()
            or not ROOT_NAME.fullmatch(root.name)
            or root.parent.resolve() != base):
        raise TrialError("OUTSIDE DISPOSABLE TEMP ROOT")
    _private_dir(root)
    marker = json.loads(_read_regular(root / MARKER, MAX_MARKER))
    if (not isinstance(marker, dict)
            or set(marker) != {"kind", "trial_id"}
            or marker["kind"] != MARKER_KIND
            or not isinstance(marker["trial_id"], str)):
        raise TrialError("INVALID TRIAL MARKER")
    try:
        if str(uuid.UUID(marker["trial_id"])) != marker["trial_id"]:
            raise TrialError("INVALID TRIAL MARKER")
    except ValueError as exc:
        raise TrialError("INVALID TRIAL MARKER") from exc
    _private_dir(root / "profile")
    _private_dir(_xdg_home(root))
    return root


def _xdg_home(root):
    return root / "xdg-config"


def _manifest_dir(root):
    return _xdg_home(root).joinpath(*XDG_COMPONENTS)


def _existing_manifest_dir(root):
    current = _xdg_home(root)
    _private_dir(current)
    for segment in XDG_COMPONENTS:
        current = current / segment
        _private_dir(current)
    return current


def _create_manifest_dir(root):
    """Make ONLY missing private subfolders of the marked trial's XDG home.

    A browser may have created some subfolders before the extension ID is
    available. Never overwrite, chmod, or follow a pre-existing symlink.
    Return the exact new directories for safe reverse-order rollback.
    """
    current = _xdg_home(root)
    _private_dir(current)
    created = []
    for segment in XDG_COMPONENTS:
        current = current / segment
        if current.is_symlink():
            raise TrialError("SYMLINK XDG DIRECTORY REFUSED")
        if current.exists():
            _private_dir(current)
        else:
            current.mkdir(mode=0o700)
            created.append(current)
            _private_dir(current)
    return current, created


def _source_host():
    source = Path(__file__).resolve().with_name(HOST_FILE)
    contents = source.read_bytes()
    if not contents.startswith(b"#!/usr/bin/env python3\n") or len(contents) > MAX_HOST:
        raise TrialError("UNEXPECTED HOST SOURCE")
    return contents


def init_trial():
    """Only this explicit operation creates a fresh, random, private root."""
    base = _base()
    root = Path(tempfile.mkdtemp(prefix=PREFIX, dir=base))
    try:
        _private_dir(root)
        (root / "profile").mkdir(mode=0o700)
        _xdg_home(root).mkdir(mode=0o700)
        marker = {"kind": MARKER_KIND, "trial_id": str(uuid.uuid4())}
        _write_exclusive(root / MARKER,
                         (json.dumps(marker, sort_keys=True) + "\n").encode(),
                         0o600)
    except Exception:
        # Only files/directories created by this invocation are cleaned up.
        (root / MARKER).unlink(missing_ok=True)
        profile = root / "profile"
        if profile.is_dir() and not profile.is_symlink():
            profile.rmdir()
        xdg = _xdg_home(root)
        if xdg.is_dir() and not xdg.is_symlink():
            xdg.rmdir()
        root.rmdir()
        raise
    return {
        "status": "disposable_trial_initialized",
        "trial_root": str(root),
        "brave_user_data_dir": str(root / "profile"),
        "brave_xdg_config_home": str(_xdg_home(root)),
        "registration_present": False,
        "browser_launched_by_tool": False,
        "local_transport_tested": False,
        "window_identity_verified": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def register_trial(root_path, extension_id):
    """Explicitly register probe ONLY inside a marked trial's XDG home.

    Brave's native Linux host lookup uses the BraveSoftware XDG config
    path, not profile/NativeMessagingHosts. The operator's successfully
    isolated Fedora/Brave trial confirmed this lookup behavior.
    """
    root = _validate_root(root_path)
    host_path = root / HOST_FILE
    manifest = generate(extension_id, str(host_path))
    host_contents = _source_host()
    target_dir = _manifest_dir(root)
    target_file = target_dir / HOST_MANIFEST
    if (host_path.exists() or host_path.is_symlink()
            or target_file.exists() or target_file.is_symlink()):
        raise TrialError("TRIAL REGISTRATION ALREADY PRESENT")

    created_dirs = []
    created_host = False
    created_manifest = False
    try:
        # Registration must never spill into the user's real XDG config.
        host_dir, created_dirs = _create_manifest_dir(root)
        if host_dir != target_dir:
            raise TrialError("XDG PATH MISMATCH")
        _write_exclusive(host_path, host_contents, 0o700)
        created_host = True
        _write_exclusive(
            target_file,
            (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(),
            0o600,
        )
        created_manifest = True
    except Exception:
        if created_manifest:
            target_file.unlink()
        if created_host:
            host_path.unlink()
        for folder in reversed(created_dirs):
            folder.rmdir()
        raise
    return verify_trial(str(root))

def verify_trial(root_path):
    """Read-only structural checks; never claim an actual Brave roundtrip."""
    root = _validate_root(root_path)
    host = root / HOST_FILE
    host_dir = _existing_manifest_dir(root)
    contents = _read_regular(host, MAX_HOST)
    if contents != _source_host() or not (host.stat().st_mode & stat.S_IXUSR):
        raise TrialError("TRIAL HOST MISMATCH")
    try:
        manifest = json.loads(_read_regular(host_dir / HOST_MANIFEST, 4096))
    except (ValueError, TypeError) as exc:
        raise TrialError("INVALID TRIAL MANIFEST") from exc
    if not isinstance(manifest, dict):
        raise TrialError("INVALID TRIAL MANIFEST")
    origins = manifest.get("allowed_origins")
    if (not isinstance(origins, list) or len(origins) != 1
            or not isinstance(origins[0], str)):
        raise TrialError("INVALID TRIAL ORIGIN")
    match = ORIGIN.fullmatch(origins[0])
    if match is None or manifest != generate(match.group(1), str(host)):
        raise TrialError("TRIAL MANIFEST MISMATCH")
    return {
        "status": "disposable_trial_registration_verified",
        "trial_root": str(root),
        "brave_user_data_dir": str(root / "profile"),
        "brave_xdg_config_home": str(_xdg_home(root)),
        "native_host_manifest": str(host_dir / HOST_MANIFEST),
        "exact_extension_id": match.group(1),
        "registration_scoped_to_disposable_trial": True,
        "host_source_matches_repo": True,
        "browser_launched_by_tool": False,
        "local_transport_tested": False,
        "extension_origin_authenticated": False,
        "window_identity_verified": False,
        "session_capture_allowed": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ["init"]:
            result = init_trial()
        elif len(args) == 3 and args[0] == "register":
            result = register_trial(args[1], args[2])
        elif len(args) == 2 and args[0] == "verify":
            result = verify_trial(args[1])
        else:
            return 2
    except (TrialError, OSError, ValueError, TypeError, json.JSONDecodeError):
        # Do not echo possibly sensitive paths, profile contents or exceptions.
        print(json.dumps({"status": "refused", "safe_actions": []}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
