#!/usr/bin/env python3
"""M12d: CI-only, signed-snapshot-to-sealed-disposable-owner boundary.

Reads EXACTLY one JSON request via stdin from an isolated Node test. It
never reads Quickshell dataDir or any production TASKS file, nor imports QML.
The signed test key and test checkout are NOT an independent production root.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[3]
TESTS = ROOT / "tests/tasks/fixtures"
SPEC = importlib.util.spec_from_file_location(
    "m12d_existing_disposable_probe", TESTS / "TaskBoundJournalProbeM11w.py")
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)

HOST_FIXTURE = TESTS / "TaskBoundJournalChildM11w.py"
MODE_SET = ("NEW_RESERVE", "EXISTING_CHECK")
MAX_INPUT = 420000
TOKEN = re.compile(r"M12D-SYNTHETIC-INTERPRETER-SHA256:([0-9a-f]{64})\n\Z")


class SignedBoundaryRefusal(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SignedBoundaryRefusal(message)


def exact(value, fields):
    return type(value) is dict and set(value) == set(fields)


def safe_root(folder):
    require(type(folder) is str and os.path.isabs(folder),
            "DISPOSABLE_ROOT_ONLY")
    path = Path(folder)
    require(".." not in path.parts and path.name == "m11l-tasks-copy"
            and path.parent.name.startswith("m12d-root-")
            and len(path.parent.name) < 85
            and path.parent.parent == Path("/tmp"),
            "DISPOSABLE_ROOT_ONLY")
    for entry in (path.parent, path):
        st = entry.lstat()
        require(stat.S_ISDIR(st.st_mode) and
                st.st_uid == os.geteuid() and
                stat.S_IMODE(st.st_mode) == 0o700,
                "DISPOSABLE_DIR_UNSAFE")
    return path


def expected_source():
    # Hard-coded synthetic *test data*, never derived from actual user data.
    task = {"id": "t1", "title": "M11W_TEST_0", "done": False,
            "createdAtMs": 1000, "updatedAtMs": 1000,
            "priority": "none", "description": "", "dueDate": None,
            "projectId": None}
    body = {"version": 3, "nextId": 2, "nextProjectId": 1,
            "projects": [], "tasks": [task]}
    return (json.dumps(body, indent=2) + "\n").encode("utf-8")


def read_artifacts(request):
    require(exact(request, ["mode", "folder", "signedSnapshots", "signatureVerified"]),
            "SIGNED_SNAPSHOT_REQUEST_INVALID")
    require(request["mode"] in MODE_SET and
            request["signatureVerified"] is True and
            exact(request["signedSnapshots"], ["host", "owner", "interpreter"]),
            "SIGNED_SNAPSHOT_REQUEST_INVALID")
    snapshots = {}
    for key in ("host", "owner", "interpreter"):
        value = request["signedSnapshots"][key]
        require(type(value) is str and 0 < len(value) <= 180000,
                "SIGNED_SNAPSHOT_REQUEST_INVALID")
        try:
            raw = base64.b64decode(value, validate=True)
            require(base64.b64encode(raw).decode("ascii") == value,
                    "SIGNED_SNAPSHOT_REQUEST_INVALID")
        except (ValueError, base64.binascii.Error):
            raise SignedBoundaryRefusal("SIGNED_SNAPSHOT_REQUEST_INVALID") from None
        snapshots[key] = raw
    # A candidate signed by the *test* signer is NOT necessarily reviewed
    # or permitted code. Compare to exact checked-in synthetic fixture.
    require(snapshots["host"] == HOST_FIXTURE.read_bytes()
            and snapshots["owner"] == probe.M11L.read_bytes(),
            "SIGNED_ARTIFACT_OUTSIDE_TEST_FIXTURES")
    descriptor = snapshots["interpreter"].decode("ascii")
    matched = TOKEN.fullmatch(descriptor)
    require(matched is not None, "SIGNED_INTERPRETER_DESCRIPTOR_INVALID")
    return snapshots, matched.group(1)


def execute(request):
    folder = safe_root(request.get("folder") if type(request) is dict else None)
    snapshots, interpreter_hash = read_artifacts(request)
    try:
        raw = probe.m11v.capsule.capture_synthetic_script
        # Reconstruct the already captured signed bytes directly. Do not
        # reopen the release artifact pathname after signature verification.
        snap = probe.m11v.capsule.SyntheticSnapshot(
            script=snapshots["host"],
            sha256=hashlib.sha256(snapshots["host"]).hexdigest())
        interpreter = probe.m11v.pinned_interpreter(interpreter_hash)
        source = probe.m11v.capsule  # fixture marker is enforced in attach()
        require(snap.script.startswith(source.MARKER),
                "UNREVIEWED_SYNTHETIC_SCRIPT")
        prior = probe.m11v.capsule  # No real task path is imported here.
        del raw, prior
        current = probe.m11v.capsule
        del current
        # Existing M11l stable source and schema, plus exact test seed.
        baseline = probe.M11L  # location of test-checked-out OWNER source only
        del baseline
        file = folder / "todo-copy.json"
        require(file.is_file() and not file.is_symlink(),
                "SYNTHETIC_SOURCE_MISSING")
        spec = importlib.util.spec_from_file_location(
            "m12d_schema_check", probe.M11L)
        owner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(owner)
        original = owner.stable_source(file)
        require(original == expected_source(), "SYNTHETIC_SOURCE_NOT_SEED")
        instance = probe.attach_synthetic(
            folder,
            "NEW" if request["mode"] == "NEW_RESERVE" else "EXISTING",
            snap, interpreter, snapshots["owner"],
            hashlib.sha256(snapshots["owner"]).hexdigest())
        try:
            row = probe.durable_row(folder)
            require(row["writer"] == "m11w-" + instance.session,
                    "SYNTHETIC_DURABLE_OWNER_MISMATCH")
            if request["mode"] == "NEW_RESERVE":
                require(instance.phase == "JSON_ACTIVE" and instance.epoch == 0,
                        "SYNTHETIC_NEW_OWNER_PHASE")
                state = instance.send("status")
                require(state["pending"] is False, "SYNTHETIC_UNEXPECTED_PENDING")
                reserved = instance.send("reserve")
                require(reserved["pending"] is True,
                        "SYNTHETIC_RESERVATION_REFUSED")
                row = probe.durable_row(folder)
                require(row["pending_stage"] is not None and
                        row["epoch"] == 0, "SYNTHETIC_STAGE_NOT_PERSISTED")
            else:
                require(instance.phase == "RECOVERY_REVIEW" and instance.epoch == 1,
                        "SYNTHETIC_RECOVERY_REQUIRED")
                state = instance.send("status")
                require(state["pending"] is True, "SYNTHETIC_PENDING_LOST")
                refusal = instance.send("reserve")
                require(refusal["status"] == "RECOVERY_REVIEW_REQUIRED",
                        "SYNTHETIC_RECOVERY_RESERVE_ACCEPTED")
            require(owner.stable_source(file) == original and
                    owner.stable_source(folder / "source-before-gate.bak") == original,
                    "SYNTHETIC_DATA_CHANGED")
            return {"status": "SYNTHETIC_SIGNED_OWNER_BOUND",
                    "phase": instance.phase, "epoch": instance.epoch,
                    "pending": row["pending_stage"] is not None,
                    "sourceUnchanged": True, "backupVerified": True,
                    "processObservedByKernel": True,
                    "signedSnapshotsUsedWithoutPathReopen": True,
                    "productionWriterAuthorized": False,
                    "realTaskDataAccess": False}
        finally:
            instance.close()
    except (OSError, ValueError, TypeError,
            UnicodeError, AttributeError):
        raise SignedBoundaryRefusal("SYNTHETIC_BOUNDARY_REFUSED") from None


def main():
    try:
        payload = sys.stdin.buffer.read(MAX_INPUT + 1)
        require(len(payload) <= MAX_INPUT, "SIGNED_SNAPSHOT_REQUEST_INVALID")
        request = json.loads(payload.decode("utf-8"),
                             object_pairs_hook=unique)
        reply = execute(request)
    except (ValueError, OSError, TypeError, UnicodeError,
            AttributeError):
        reply = {"status": "REFUSED", "productionWriterAuthorized": False,
                 "realTaskDataAccess": False}
    sys.stdout.write(json.dumps(reply, sort_keys=True) + "\n")
    return 0 if reply.get("status") == "SYNTHETIC_SIGNED_OWNER_BOUND" else 2


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_SIGNED_SNAPSHOT_KEY")
        result[key] = value
    return result


if __name__ == "__main__":
    sys.exit(main())
