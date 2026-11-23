#!/usr/bin/env python3
"""TimeW M6: private temp-database atomic local exact admission regression."""
from __future__ import annotations

from dataclasses import replace
import copy
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
from MachineV2ExactLogicalGeometry import (
    PHASE_CURRENT, PHASE_PENDING, capture_value, read_value,
)
from MachineV3LocalExactCaptureStore import (
    DB_NAME, LocalExactCaptureStore, LocalCaptureRefused,
)
from MachineV3LocalCheckpointAdmission import (
    AdmissionRefused, admit_checkpoint,
)

count = 0


def check(value, msg):
    global count
    assert value, msg
    count += 1


def refused(func, msg):
    global count
    try:
        func()
    except AdmissionRefused:
        count += 1
    else:
        raise AssertionError("wrongly admitted: " + msg)


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


with tempfile.TemporaryDirectory(prefix="timew-m6-admission-") as temp:
    prior = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = temp
    try:
        # V1/V2 may create intermediate parents with ambient umask. The
        # local v3 store correctly refuses a non-private post-apollo parent.
        # Prepare a 0700 parent for the valid integration fixture, rather
        # than weakening privacy checks or changing the legacy writer.
        parent = Path(temp) / "post-apollo"
        parent.mkdir(mode=0o700)
        old, geo = fixture()
        checkpoint = save_pair(old, geo)["checkpoint"]["id"]
        db = Path(temp) / "post-apollo" / "machine" / DB_NAME
        store = LocalExactCaptureStore(db)
        integer_path = legacy.db_path()
        before_legacy = legacy.load(checkpoint)
        before_geometry = load_geometry(checkpoint)
        exact = [
            candidate(geo["windows"][0]),
            candidate(geo["windows"][1], y=math.nextafter(92.5, math.inf)),
        ]
        check(len(exact) == 2 and len({x["window_key"] for x in exact}) == 2,
              "two independent mapped identifiers")
        check(before_geometry["geometry"]["windows"][0]["rect"]["y"] == 0,
              "v2 saved rectangle remains integer-only")
        check(exact[0]["value"].y_bits != exact[1]["value"].y_bits,
              "independent exact input contains one ULP difference")
        check(not db.exists(), "admission never runs at import")

        def call(items=exact, *, cid=checkpoint, **extra):
            return admit_checkpoint(
                checkpoint_id=cid, observations=items, store=store, **extra)

        # Every invalid set is refused before touching local v3 DB.
        refused(lambda: call([]), "empty batch")
        refused(lambda: call(None), "absent list")
        refused(lambda: call(tuple(exact)), "tuple not an approved bundle")
        refused(lambda: call([exact[0]]), "incomplete checkpoint window set")
        refused(lambda: call(exact, cid=KEYS[0].upper()),
                "noncanonical checkpoint UUID")
        refused(lambda: call(exact, cid="not-uuid"), "invalid checkpoint")
        refused(lambda: call(exact, cid=str(uuid.uuid4())),
                "nonexistent checkpoint")
        refused(lambda: call([exact[0], exact[0]]), "duplicate window")
        refused(lambda: call([dict(exact[0], signature="forged"), exact[1]]),
                "forged native signature field")
        refused(lambda: call([dict(exact[0], c5_spent_verified=True), exact[1]]),
                "forged protected consent claim")
        refused(lambda: call([dict(exact[0], app_id="different"), exact[1]]),
                "window app mismatch")
        refused(lambda: call([dict(exact[0], output_id="HDMI-A-1"), exact[1]]),
                "window output mismatch")
        refused(lambda: call([dict(exact[0], workspace_id="2"), exact[1]]),
                "window workspace mismatch")
        refused(lambda: call([dict(exact[0], window_key=str(uuid.uuid4())),
                              exact[1]]), "unrelated window")
        refused(lambda: call([dict(exact[0], window_key="not-uuid"),
                              exact[1]]), "invalid window")
        refused(lambda: call([dict(exact[0], value=rect(2, 3, 4, 5)),
                              exact[1]]), "raw integer rect is not exact source")
        refused(lambda: call([dict(exact[0], value=replace(
            exact[0]["value"], phase=PHASE_PENDING)), exact[1]]),
                "PENDING is not captured CURRENT")
        refused(lambda: call([dict(exact[0], value=replace(
            exact[0]["value"], y_bits=-1)), exact[1]]),
                "forged invalid binary64")
        refused(lambda: call(exact, geometry_reader=lambda _: {
            "status": "legacy_only", "checkpoint_id": checkpoint,
            "geometry_available": False, "read_only": True}),
                "legacy-only lacks checkpoint window set")
        refused(lambda: call(exact, legacy_reader=lambda _: {
            **before_legacy, "signed": True}), "forged legacy identity")
        refused(lambda: call(exact, geometry_reader=lambda _: {
            **before_geometry, "source_authenticated": True}),
                "forged geometry source")
        refused(lambda: call(exact, geometry_reader=lambda _: {
            **before_geometry, "session_identity_verified": True}),
                "forged native selected session")
        refused(lambda: call(exact, legacy_reader=lambda _: {
            **before_legacy, "checkpoint": {
                **before_legacy["checkpoint"],
                "counts": {"outputs": 1, "workspaces": 1, "windows": 3},
            }}), "count mismatch")
        def broken_sqlite(_):
            raise sqlite3.OperationalError("private absolute path must not leak")
        def broken_filesystem(_):
            raise OSError("private absolute path must not leak")
        refused(lambda: call(exact, geometry_reader=broken_sqlite),
                "read error refused without SQLite detail")
        refused(lambda: call(exact, legacy_reader=broken_filesystem),
                "read error refused without local path detail")
        check(not db.exists(), "invalid admission cannot create v3 DB")

        # Unsafe *existing* parent directories are a preflight blocker,
        # not permission to chmod a user's directories behind their back.
        parent.chmod(0o755)
        refused(lambda: call(), "world-readable intermediate parent refuses")
        check(parent.stat().st_mode & 0o077 != 0,
              "refusal did not silently fix local directory permissions")
        check(not db.exists(), "unsafe parent left no v3 database")
        parent.chmod(0o700)

        result = call()
        check(result["status"] == "LOCAL_EXACT_CAPTURE_RECORDED_UNTRUSTED",
              "local-only status")
        check(result["checkpoint_id"] == checkpoint and result["count"] == 2,
              "checkpoint and complete window count")
        check(len(set(result["capture_ids"])) == 2, "distinct capture IDs")
        check(result["safe_actions"] == [] and result["local_capture_only"] is True,
              "no action fields")
        for flag in (
            "source_authenticated", "operator_selection_verified",
            "c5_spent_verified", "native_receipt_verified",
            "production_restore_allowed", "automatic_retry_allowed",
            "automatic_undo_allowed",
        ):
            check(result[flag] is False, "local bundle has no trust " + flag)
        found = store.for_checkpoint(checkpoint)
        check(len(found) == 2, "atomic bundle has two rows")
        check({x["window_key"] for x in found} == set(KEYS),
              "checkpoint window keys bound")
        check({x["value"].y_bits for x in found} ==
              {x["value"].y_bits for x in exact},
              "one ULP retained across atomic commit")
        check(all(x["production_restore_allowed"] is False
                  and x["safe_actions"] == [] for x in found),
              "no native permissions in rows")
        check(legacy.load(checkpoint) == before_legacy
              and load_geometry(checkpoint) == before_geometry,
              "V1/V2 stores never mutated by admission")
        refused(lambda: call(), "cannot replace complete existing local bundle")
        check(len(store.for_checkpoint(checkpoint)) == 2,
              "duplicate attempt never changes bundle")
        check(db.name == DB_NAME and db != integer_path,
              "separate local v3 database")
        with sqlite3.connect(db) as conn:
            check(conn.execute(
                "SELECT COUNT(DISTINCT checkpoint_id) FROM exact_captures"
            ).fetchone()[0] == 1, "batch stays scoped to one checkpoint")

        # A triggered second INSERT error must undo the first; never expose
        # an apparently complete partially committed capture bundle.
        other_ck = save_pair(old, geo)["checkpoint"]["id"]
        with sqlite3.connect(db) as conn:
            conn.execute("""CREATE TRIGGER reject_second_m6
                BEFORE INSERT ON exact_captures
                WHEN NEW.window_key='22222222-2222-4222-8222-222222222222'
                BEGIN SELECT RAISE(ABORT,'synthetic second-window failure'); END""")
        refused(lambda: call(cid=other_ck), "second insert must roll back first")
        check(store.for_checkpoint(other_ck) == [],
              "triggered error leaves zero local rows for new checkpoint")
        check(len(store.for_checkpoint(checkpoint)) == 2,
              "previous checkpoint remains intact after aborted batch")
        with sqlite3.connect(db) as conn:
            conn.execute("DROP TRIGGER reject_second_m6")

        # Already partially populated checkpoints are never silently extended.
        prior_ck = save_pair(old, geo)["checkpoint"]["id"]
        store.save(checkpoint_id=prior_ck, **exact[0])
        refused(lambda: call(cid=prior_ck), "no extending a partial bundle")
        check(len(store.for_checkpoint(prior_ck)) == 1,
              "partial preexisting local row is preserved, not overwritten")
    finally:
        if prior is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = prior

# Source-scope contract: neither UI nor running Save bridge was modified.
qml = (ROOT / "widgets/TimeW.qml").read_text()
save_bridge = (SERVICE / "MachineSaveBridgeV2.py").read_text()
admission = (SERVICE / "MachineV3LocalCheckpointAdmission.py").read_text()
for old_file in (qml, save_bridge):
    check("MachineV3LocalCheckpointAdmission" not in old_file,
          "no live Save/UI admission hook")
for forbidden in ("swaymsg", "import subprocess", "import socket", "machineRestore",
                  "Ed25519", "CREATE TABLE", "exec(", "def main("):
    check(forbidden not in admission, "admission has no native/CLI command: "+forbidden)
check("save_many(" in admission and "validate_pair(" in admission,
      "strict local metadata and single batch boundary")

print("TIMEW M6 LOCAL EXACT CHECKPOINT ADMISSION // "
      + str(count) + " atomic, deny-only and V1/V2 isolation checks PASS")
