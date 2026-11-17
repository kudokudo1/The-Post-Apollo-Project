#!/usr/bin/env python3
"""U9: real GIO Trash -> Trash++ restore, with disposable CI-runner data ONLY.

This intentionally does not test the operator workstation, Camera owner ingress,
any Media library file, Burn, trash --empty or protected Archive. It refuses to
run outside GitHub Actions and uses a private RUNNER_TEMP sandbox for HOME/XDG.
The CI-only guard prevents accidental use, not a hostile actor forging CI vars.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile

SCHEMA = "post-apollo.trash-gio-roundtrip.u9"
TIMEOUT = 25


class RoundTripError(Exception):
    pass


def ci_runner_temp(environ: dict[str, str]) -> Path:
    """Fail closed unless a recognized, owned CI temporary directory exists."""
    if environ.get("GITHUB_ACTIONS") != "true" or environ.get("CI") != "true":
        raise RoundTripError("CI_ONLY")
    raw = environ.get("RUNNER_TEMP", "")
    if not raw or not os.path.isabs(raw):
        raise RoundTripError("RUNNER_TEMP_REQUIRED")
    path = Path(raw)
    try:
        info = path.lstat()
    except OSError as exc:
        raise RoundTripError("RUNNER_TEMP_UNAVAILABLE") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise RoundTripError("RUNNER_TEMP_NOT_PRIVATE")
    resolved = path.resolve()
    if resolved == Path("/") or resolved == Path.cwd().resolve():
        raise RoundTripError("UNSAFE_RUNNER_TEMP")
    return resolved


def isolated_environment(root: Path, inherited: dict[str, str]) -> dict[str, str]:
    """Keep only necessary process environment; never use operator HOME."""
    home = root / "home"
    data = home / ".local" / "share"
    config = home / ".config"
    cache = home / ".cache"
    runtime = root / "runtime"
    for directory in (home, data, config, cache, runtime):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
    return {
        "HOME": str(home),
        "XDG_DATA_HOME": str(data),
        "XDG_CONFIG_HOME": str(config),
        "XDG_CACHE_HOME": str(cache),
        "XDG_RUNTIME_DIR": str(runtime),
        "PATH": inherited.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIO_USE_VFS": "local",
    }


def command(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv, env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=TIMEOUT, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RoundTripError("COMMAND_EXECUTION_OR_TIMEOUT") from exc


def json_response(process: subprocess.CompletedProcess, expected_ok: bool) -> dict:
    try:
        data = json.loads(process.stdout)
    except (ValueError, TypeError) as exc:
        raise RoundTripError("BACKEND_JSON_INVALID") from exc
    if not isinstance(data, dict) or data.get("ok") is not expected_ok:
        raise RoundTripError("BACKEND_RESULT_UNEXPECTED")
    if (process.returncode == 0) is not expected_ok:
        raise RoundTripError("BACKEND_EXIT_UNEXPECTED")
    return data


def assert_empty_index(index: dict) -> None:
    if (index.get("ok") is not True or index.get("complete") is not True
            or index.get("total") != 0 or index.get("items") != []):
        raise RoundTripError("SANDBOX_TRASH_NOT_EMPTY")


def reviewed_item(index: dict, original: Path) -> dict:
    """Require exact single freshly inventoried original path before Restore."""
    rows = index.get("items")
    if (index.get("ok") is not True or index.get("complete") is not True
            or index.get("total") != 1 or not isinstance(rows, list)
            or len(rows) != 1):
        raise RoundTripError("ISOLATED_ITEM_NOT_UNIQUE")
    item = rows[0]
    if not isinstance(item, dict):
        raise RoundTripError("INVALID_ITEM")
    uri = item.get("uri")
    if (item.get("original") != str(original) or not isinstance(uri, str)
            or not uri.startswith("trash:///") or len(uri) > 8192
            or not isinstance(item.get("reviewId"), str)
            or len(item["reviewId"]) != 64):
        raise RoundTripError("ITEM_IDENTITY_MISMATCH")
    return item


def run_roundtrip(root: Path, inherited: dict[str, str]) -> dict:
    env = isolated_environment(root, inherited)
    gio = shutil.which("gio", path=env["PATH"])
    if not gio:
        raise RoundTripError("GIO_NOT_INSTALLED")
    backend = Path(__file__).resolve().with_name("trash_cli.py")
    if not backend.is_file():
        raise RoundTripError("TRASH_BACKEND_MISSING")
    original = root / "home" / "U9-disposable-gio-restore-only.txt"
    payload = b"POST_APOLLO_DISPOSABLE_U9:" + secrets.token_bytes(32)
    original.write_bytes(payload)
    original.chmod(0o600)
    digest = hashlib.sha256(payload).hexdigest()

    def index() -> dict:
        return json_response(command(
            [sys.executable, "-I", "-B", str(backend), "index"], env
        ), True)

    # This gate runs before any file is moved. Never touch an existing trash.
    assert_empty_index(index())

    moved = command([gio, "trash", str(original)], env)
    if moved.returncode != 0:
        raise RoundTripError("GIO_TRASH_FAILED")
    if original.exists() or original.is_symlink():
        raise RoundTripError("GIO_DID_NOT_MOVE_SOURCE")
    item = reviewed_item(index(), original)
    uri = item["uri"]

    # Existing-destination refusal must leave both entries unchanged.
    collision = b"U9_DISPOSABLE_COLLISION_SENTINEL"
    original.write_bytes(collision)
    refusal = json_response(command(
        [sys.executable, "-I", "-B", str(backend), "restore",
         uri, str(original)], env
    ), False)
    if refusal.get("error") != "RESTORE_TARGET_EXISTS":
        raise RoundTripError("EXISTING_TARGET_NOT_REFUSED")
    if original.read_bytes() != collision:
        raise RoundTripError("COLLISION_TARGET_CHANGED")
    reviewed_item(index(), original)
    original.unlink()  # Only the sentinel created inside private runner sandbox.

    receipt = json_response(command(
        [sys.executable, "-I", "-B", str(backend), "restore",
         uri, str(original)], env
    ), True)
    if receipt.get("kind") != "restore" or receipt.get("message") != "RESTORED":
        raise RoundTripError("RESTORE_RECEIPT_UNEXPECTED")
    if not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest() != digest:
        raise RoundTripError("RESTORED_BYTES_CHANGED")
    assert_empty_index(index())

    # A prior row must not be restored twice.
    stale = json_response(command(
        [sys.executable, "-I", "-B", str(backend), "restore",
         uri, str(original)], env
    ), False)
    if stale.get("error") != "STALE_OR_UNKNOWN_TRASH_ITEM":
        raise RoundTripError("STALE_RESTORE_NOT_DENIED")
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest:
        raise RoundTripError("POST_RESTORE_FILE_CHANGED")

    return {
        "schema": SCHEMA,
        "ok": True,
        "scope": "ephemeral-github-runner-only",
        "gioReal": True,
        "trashIngress": "gio trash (one disposable file)",
        "restoreAdapter": "scripts/trash/trash_cli.py",
        "initialInventoryEmpty": True,
        "exactOneItemIndexed": True,
        "collisionDenied": True,
        "restoredBytesVerified": True,
        "staleReplayDenied": True,
        "postRestoreInventoryEmpty": True,
        "fileBurnUsed": False,
        "emptyTrashUsed": False,
        "hostAcceptance": False,
        "cameraIngressAcceptance": False,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(json.dumps({"ok": False, "error": "NO_ARGUMENTS_ALLOWED"}))
        return 2
    try:
        runner_temp = ci_runner_temp(dict(os.environ))
        # TemporaryDirectory is under GH-provided runner scratch space ONLY.
        # Its cleanup cannot touch any source file or operator workstation.
        with tempfile.TemporaryDirectory(prefix="trashpp-u9-", dir=runner_temp) as tmp:
            result = run_roundtrip(Path(tmp), dict(os.environ))
    except RoundTripError as exc:
        result = {"schema": SCHEMA, "ok": False, "error": str(exc)}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": SCHEMA, "ok": False, "error": "FIXTURE_FAILURE_" + type(exc).__name__}
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
