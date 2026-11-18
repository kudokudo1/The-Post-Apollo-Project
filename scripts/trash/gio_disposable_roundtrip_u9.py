#!/usr/bin/env python3
"""U9: real GIO Trash -> Trash++ restore, with disposable CI-runner data ONLY.

This intentionally does not test the operator workstation, Camera owner ingress,
any Media library file, Burn, trash --empty or protected Archive. It refuses to
run outside GitHub Actions and uses a private RUNNER_TEMP sandbox for HOME/XDG.
The CI-only guard prevents accidental use, not a hostile actor forging CI vars.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch

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
        "GIO_USE_VFS": "gvfs",
        **({"DBUS_SESSION_BUS_ADDRESS": inherited["DBUS_SESSION_BUS_ADDRESS"]}
           if inherited.get("DBUS_SESSION_BUS_ADDRESS") else {}),
    }


def command(argv: list[str], env: dict[str, str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv, env=env, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RoundTripError("COMMAND_EXECUTION_OR_TIMEOUT") from exc


def json_response(process: subprocess.CompletedProcess, expected_ok: bool, phase: str = "UNIT") -> dict:
    try:
        data = json.loads(process.stdout)
    except (ValueError, TypeError) as exc:
        raise RoundTripError("BACKEND_JSON_INVALID") from exc
    if not isinstance(data, dict) or data.get("ok") is not expected_ok:
        raw_code = str(data.get("error", "")) if isinstance(data, dict) else ""
        match = re.match(r"[A-Z][A-Z_]{2,60}", raw_code)
        safe_code = match.group(0) if match else "UNSPECIFIED"
        raise RoundTripError("BACKEND_RESULT_UNEXPECTED_" + phase + "_" + safe_code)
    if (process.returncode == 0) is not expected_ok:
        raise RoundTripError("BACKEND_EXIT_UNEXPECTED_" + phase)
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

    def index(phase: str) -> dict:
        return json_response(command(
            [sys.executable, "-I", "-B", str(backend), "index"], env
        ), True, phase)

    # This gate runs before any file is moved. Never touch an existing trash.
    assert_empty_index(index("INITIAL"))

    moved = command([gio, "trash", str(original)], env)
    if moved.returncode != 0:
        raise RoundTripError("GIO_TRASH_FAILED")
    if original.exists() or original.is_symlink():
        raise RoundTripError("GIO_DID_NOT_MOVE_SOURCE")
    reviewed_index = index("AFTER_TRASH")
    item = reviewed_item(reviewed_index, original)
    uri = item["uri"]
    revision = reviewed_index.get("revision")
    review_id = item["reviewId"]
    if (not isinstance(revision, str)
            or re.fullmatch(r"[0-9a-f]{64}", revision) is None):
        raise RoundTripError("REVIEWED_INVENTORY_REVISION_INVALID")

    # Existing-destination refusal must leave both entries unchanged.
    collision = b"U9_DISPOSABLE_COLLISION_SENTINEL"
    original.write_bytes(collision)
    refusal = json_response(command(
        [sys.executable, "-I", "-B", str(backend), "restore-reviewed",
         uri, str(original), revision, review_id], env
    ), False, "COLLISION")
    if refusal.get("error") != "RESTORE_TARGET_EXISTS":
        raise RoundTripError("EXISTING_TARGET_NOT_REFUSED")
    if original.read_bytes() != collision:
        raise RoundTripError("COLLISION_TARGET_CHANGED")
    reviewed_item(index("AFTER_COLLISION"), original)
    original.unlink()  # Only the sentinel created inside private runner sandbox.

    # U10b // Inject an occupied destination only AFTER the actual reviewed
    # backend's last Python lexists() call, immediately before its REAL GIO
    # restore command. This proves no-force GIO preserves the collision.
    spec = importlib.util.spec_from_file_location("u10b_real_trash_cli", backend)
    target = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(target)
    raw_run = target._run
    late_sentinel = b"U10B_LATE_COLLISION_MUST_NOT_BE_OVERWRITTEN"
    reached_move = False

    def inject_late_collision(argv, timeout=20):
        nonlocal reached_move
        if len(argv) == 4 and argv[1:3] == ["trash", "--restore"] and argv[3] == uri:
            if reached_move or original.exists() or original.is_symlink():
                raise RoundTripError("LATE_COLLISION_FIXTURE_ALREADY_OCCUPIED")
            original.write_bytes(late_sentinel)
            reached_move = True
        return raw_run(argv, timeout=timeout)

    with patch.object(target, "_run", side_effect=inject_late_collision):
        try:
            target.restore_reviewed(uri, str(original), revision, review_id)
        except target.TrashError as exc:
            if not str(exc).startswith("GIO_RESTORE_FAILED"):
                raise RoundTripError("LATE_COLLISION_WRONG_BACKEND_REFUSAL") from exc
        else:
            raise RoundTripError("LATE_COLLISION_RESTORE_UNEXPECTEDLY_SUCCEEDED")
    if not reached_move or not original.is_file() or original.read_bytes() != late_sentinel:
        raise RoundTripError("LATE_COLLISION_SENTINEL_LOST")
    reviewed_item(index("AFTER_LATE_COLLISION"), original)
    original.unlink()  # Only the injected disposable runner sentinel.

    receipt = json_response(command(
        [sys.executable, "-I", "-B", str(backend), "restore-reviewed",
         uri, str(original), revision, review_id], env
    ), True, "RESTORE")
    if (receipt.get("kind") != "restore"
            or receipt.get("message") != "RESTORED"
            or receipt.get("verified") is not True
            or receipt.get("metadataWitness") not in ("observed", "unavailable")
            or type(receipt.get("secondaryIdentityObserved")) is not bool):
        raise RoundTripError("RESTORE_RECEIPT_UNEXPECTED")
    if not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest() != digest:
        raise RoundTripError("RESTORED_BYTES_CHANGED")
    assert_empty_index(index("AFTER_RESTORE"))

    # A prior row must not be restored twice.
    stale = json_response(command(
        [sys.executable, "-I", "-B", str(backend), "restore-reviewed",
         uri, str(original), revision, review_id], env
    ), False, "REPLAY")
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
        "reviewedRestoreRevisionChecked": True,
        "initialInventoryEmpty": True,
        "exactOneItemIndexed": True,
        "collisionDenied": True,
        "lateCollisionPreserved": True,
        "metadataCompatibilityMode": receipt["metadataWitness"],
        "secondaryIdentityObserved": receipt["secondaryIdentityObserved"],
        "restoredBytesVerified": True,
        "staleReplayDenied": True,
        "postRestoreInventoryEmpty": True,
        "fileBurnUsed": False,
        "emptyTrashUsed": False,
        "hostAcceptance": False,
        "cameraIngressAcceptance": False,
    }


def validated_child_root(raw: str, runner_temp: Path,
                         inherited: dict[str, str]) -> Path:
    """Never accept a child fixture directory outside this CI scratch root."""
    if not inherited.get("DBUS_SESSION_BUS_ADDRESS"):
        raise RoundTripError("PRIVATE_DBUS_SESSION_REQUIRED")
    if not raw or not os.path.isabs(raw):
        raise RoundTripError("CHILD_ROOT_INVALID")
    path = Path(raw)
    try:
        info = path.lstat()
    except OSError as exc:
        raise RoundTripError("CHILD_ROOT_NOT_FOUND") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or not path.name.startswith("trashpp-u9-")
            or path.resolve().parent != runner_temp.resolve()):
        raise RoundTripError("CHILD_ROOT_OUTSIDE_RUNNER")
    return path.resolve()


def main(argv: list[str]) -> int:
    if len(argv) != 1 and not (len(argv) == 3 and argv[1] == "--ci-child"):
        print(json.dumps({"ok": False, "error": "NO_ARGUMENTS_ALLOWED"}))
        return 2
    try:
        inherited = dict(os.environ)
        runner_temp = ci_runner_temp(inherited)
        if len(argv) == 3:
            root = validated_child_root(argv[2], runner_temp, inherited)
            result = run_roundtrip(root, inherited)
        else:
            # DBus and the GVfs trash service are launched *after* the private
            # HOME and XDG storage exist. Activated daemons inherit the same
            # private paths; they must not observe the generic runner's HOME.
            with tempfile.TemporaryDirectory(prefix="trashpp-u9-", dir=runner_temp) as tmp:
                root = Path(tmp)
                env = isolated_environment(root, inherited)
                env["GITHUB_ACTIONS"] = "true"
                env["CI"] = "true"
                env["RUNNER_TEMP"] = str(runner_temp)
                proc = command(
                    ["dbus-run-session", "--", sys.executable, "-I", "-B",
                     str(Path(__file__).resolve()), "--ci-child", str(root)],
                    env, timeout=210
                )
                try:
                    result = json.loads(proc.stdout)
                except (ValueError, TypeError) as exc:
                    raise RoundTripError("DBUS_CHILD_OUTPUT_INVALID") from exc
                if not isinstance(result, dict) or ((proc.returncode == 0) is not (result.get("ok") is True)):
                    raise RoundTripError("DBUS_CHILD_RESULT_MISMATCH")
    except RoundTripError as exc:
        result = {"schema": SCHEMA, "ok": False, "error": str(exc)}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": SCHEMA, "ok": False, "error": "FIXTURE_FAILURE_" + type(exc).__name__}
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
