#!/usr/bin/env python3
"""M7 recovery: disposable actual SQLite stores; no desktop or source authority."""
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "time"
sys.path.insert(0, str(SERVICE))
import MachineCheckpointStore as legacy
from MachineGeometryStoreV2 import save_pair, load_geometry
from MachineGeometryV2 import project_geometry
from MachineV2ExactLogicalGeometry import PHASE_CURRENT, PHASE_PENDING, capture_value
from MachineV3LocalExactCaptureStore import DB_NAME, LocalExactCaptureStore
from MachineV3LocalCheckpointAdmission import AdmissionRefused, admit_checkpoint
from MachineV3LocalSaveRecovery import (
    BindingRefused, prepare_binding, inspect_outcome,
)

checks = 0

def check(ok, why):
    global checks
    assert ok, why
    checks += 1

def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


KEYS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
)


def leaf(ident, app, rectangle):
    return {
        "type": "con", "id": ident, "app_id": app,
        "rect": rectangle, "percent": 0.5, "layout": "none",
        "floating": "auto_off", "nodes": [], "floating_nodes": [],
        "window_rect": None, "deco_rect": None, "geometry": None,
        "fullscreen_mode": 0, "title": "DO NOT STORE PRIVATE TITLE",
        "pid": 999,
    }


def fixture():
    outputs = [{
        "name": "DP-1", "active": True, "rect": rect(0, 0, 2560, 1440),
        "scale": 1.0, "transform": "normal",
    }]
    workspaces = [{"name": "1", "output": "DP-1"}]
    tree = {"type": "root", "nodes": [{
        "type": "output", "name": "DP-1", "nodes": [{
            "type": "workspace", "name": "1", "layout": "splith",
            "rect": rect(0, 0, 2560, 1440),
            "nodes": [
                leaf(101, "brave", rect(0, 0, 1280, 1440)),
                leaf(102, "kitty", rect(1280, 0, 1280, 1440)),
            ],
            "floating_nodes": [],
        }],
    }]}
    geo = project_geometry(
        outputs, workspaces, tree,
        window_keys={101: KEYS[0], 102: KEYS[1]},
    )
    old = {
        "schema_version": 1,
        "kind": "sway-layout-selection-preview",
        "preview_only": True,
        "label": "M6 local batch",
        "captured_at_utc": "2026-11-23T19:00:00+00:00",
        "outputs": [
            {"connector": x["connector"], "rect": x["rect"]}
            for x in geo["outputs"]],
        "workspaces": [
            {"name": x["name"], "output": x["output"]}
            for x in geo["workspaces"]],
        "windows": [
            {"app_id": x["app_id"], "workspace": x["workspace"],
             "floating": x["floating"]}
            for x in geo["windows"]],
    }
    return old, geo


def candidate(window, *, y=92.5):
    return {
        "window_key": window["window_key"],
        "app_id": window["app_id"],
        "output_id": window["output"],
        "workspace_id": window["workspace"],
        "value": capture_value(
            PHASE_CURRENT, x=259.125, y=y, width=1402.5, height=872.25),
    }



with tempfile.TemporaryDirectory(prefix="timew-m7-recovery-") as temp:
    prior = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = temp
    try:
        parent = Path(temp) / "post-apollo"
        parent.mkdir(mode=0o700)
        old, geo = fixture()
        db = parent / "machine" / DB_NAME
        store = LocalExactCaptureStore(db)
        exact = [candidate(geo["windows"][0]),
                 candidate(geo["windows"][1], y=math.nextafter(92.5, math.inf))]
        def new():
            cid = save_pair(old, geo)["checkpoint"]["id"]
            binding = prepare_binding(checkpoint_id=cid, observations=exact)
            return cid, binding

        def inspect(binding, expected, *, items=exact, **kw):
            result = inspect_outcome(binding=binding, observations=items, store=store, **kw)
            check(result["status"] == expected, repr(result))
            check(result["checkpoint_id"] == binding.checkpoint_id, "original key retained")
            check(result["read_only"] is True and result["local_data_only"] is True,
                  "ordinary read-only result")
            for flag in ("cross_database_atomic", "save_attempt_verified",
                         "source_authenticated", "operator_selection_verified",
                         "c5_spent_verified", "native_receipt_verified",
                         "production_restore_allowed", "automatic_retry_allowed",
                         "automatic_undo_allowed"):
                check(result[flag] is False, "no authority from " + flag)
            check(result["safe_actions"] == [], "no executable action")
            return result

        cid, binding = new()
        inspect(binding, "LEGACY_MATCH_LOCAL_EXACT_ABSENT")
        check(not db.exists(), "read-only inspection creates no database")
        check(binding == prepare_binding(checkpoint_id=cid, observations=list(reversed(exact))),
              "canonical order independent binding")
        for bad in ([], exact[:1], [exact[0], exact[0]],
                    [dict(exact[0], c5_spent_verified=True), exact[1]],
                    [dict(exact[0], value=replace(exact[0]["value"],phase=PHASE_PENDING)),exact[1]]):
            try:
                prepare_binding(checkpoint_id=cid, observations=bad)
            except BindingRefused:
                check(True, "malformed binding refused")
            else:
                raise AssertionError("invalid candidate admitted")
        inspect(binding, "CANDIDATE_CONFLICT_HOLD",
                items=[candidate(geo["windows"][0], y=92.75), exact[1]])
        check(not db.exists(), "candidate conflict does not create database")

        # Deliberate explicit M6 call, outside M7. Discard its success
        # response as if the client lost it. M7 must only observe readback.
        admit_checkpoint(checkpoint_id=cid, observations=exact, store=store)
        rows = store.for_checkpoint(cid)
        check(len(rows) == 2, "complete M6 commit")
        before = db.read_bytes()
        inspect(binding, "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED")
        inspect(binding, "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED",
                items=list(reversed(exact)))
        check(db.read_bytes() == before, "no writes during repeated recovery")
        check(len(store.for_checkpoint(cid)) == 2, "no duplicate write")

        # Real failure after ordinary checkpoint save: second insert aborts.
        failed, failed_binding = new()
        with sqlite3.connect(db) as conn:
            conn.execute("""CREATE TRIGGER fail_second_m7 BEFORE INSERT ON exact_captures
                WHEN NEW.window_key='22222222-2222-4222-8222-222222222222'
                BEGIN SELECT RAISE(ABORT,'test failure'); END""")
        try:
            admit_checkpoint(checkpoint_id=failed, observations=exact, store=store)
        except AdmissionRefused:
            check(True, "explicit M6 attempt refused")
        else:
            raise AssertionError("forced failure did not abort")
        inspect(failed_binding, "LEGACY_MATCH_LOCAL_EXACT_ABSENT")
        check(len(legacy.listing()["checkpoints"]) == 2, "ordinary save preserved, no retry")
        check(store.for_checkpoint(failed) == [], "partial rows rolled back")
        with sqlite3.connect(db) as conn:
            conn.execute("DROP TRIGGER fail_second_m7")

        # Partial pre-existing record, and conflicting exact values.
        partial, partial_binding = new()
        store.save(checkpoint_id=partial, **exact[0])
        inspect(partial_binding, "LOCAL_EXACT_CONFLICT_HOLD")
        conflict, conflict_binding = new()
        admit_checkpoint(checkpoint_id=conflict, observations=[
            candidate(geo["windows"][0], y=93.5), exact[1]], store=store)
        inspect(conflict_binding, "LOCAL_EXACT_CONFLICT_HOLD")

        # The old checkpoint's label changes while a complete local
        # v3 bundle exists. Ordinary consistency does not imply authority.
        def changed_reader(key):
            data = legacy.load(key)
            data["document"]["label"] = "changed"
            data["checkpoint"]["label"] = "changed"
            return data
        inspect(binding, "CHECKPOINT_CHANGED_HOLD", legacy_reader=changed_reader)

        calls = 0
        def changed_during_read(key):
            global calls
            calls += 1
            return legacy.load(key) if calls == 1 else changed_reader(key)
        inspect(binding, "CHECKPOINT_CHANGED_HOLD", legacy_reader=changed_during_read)

        # Actual deletion between the two checkpoint observations.
        vanished, vanished_binding = new()
        reads = 0
        def deleting_reader(key):
            global reads
            reads += 1
            if reads == 2:
                with sqlite3.connect(legacy.db_path()) as conn:
                    conn.execute("DELETE FROM checkpoints WHERE id=?", (key,))
            return legacy.load(key)
        inspect(vanished_binding, "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD", legacy_reader=deleting_reader)
        inspect(vanished_binding, "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD")
        check(store.for_checkpoint(vanished) == [], "deleted checkpoint not recreated")

        # Real read error (unsafe local file permissions) must not claim absence.
        db.chmod(0o644)
        inspect(binding, "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD")
        db.chmod(0o600)
        inspect(binding, "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED")

        # Changed input and source errors are never interpreted as a safe retry.
        def broken_reader(_):
            raise sqlite3.OperationalError("private path")
        r = inspect(binding, "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD", legacy_reader=broken_reader)
        check("private path" not in json.dumps(r), "diagnostic detail not exposed")
        check(len(store.for_checkpoint(cid)) == 2, "all prior captures unchanged")
    finally:
        if prior is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = prior

src = (SERVICE / "MachineV3LocalSaveRecovery.py").read_text()
for forbidden in ("save_pair(", "save_many(", "admit_checkpoint(", "swaymsg",
                  "import subprocess", "import socket", "def main(", "exec("):
    check(forbidden not in src, "recovery has no writer or native call: " + forbidden)
for path in (ROOT / "widgets/TimeW.qml", SERVICE / "MachineSaveBridgeV2.py"):
    check("MachineV3LocalSaveRecovery" not in path.read_text(), "no live wiring")
print("TIMEW M7 LOCAL SAVE RECOVERY // " + str(checks) + " read-only checks PASS")
