#!/usr/bin/env python3
"""M9: local original Save identity, real transaction and process-exit tests."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "time"
sys.path.insert(0, str(SERVICE))
import MachineCheckpointStore as legacy
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import TABLE as GEO_TABLE, save_pair, load_geometry
from MachineV3OriginalSaveIdentity import (
    TABLE, PREPARED, MARKED, COMMITTED, OriginalSaveRefused,
    new_identity, prepare, dispatch_once, inspect,
)

KEY_A = "11111111-1111-4111-8111-111111111111"
KEY_B = "22222222-2222-4222-8222-222222222222"
KEY_C = "33333333-3333-4333-8333-333333333333"


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def leaf(con, app, rectangle, *, floating=False):
    return {
        "type": "con", "id": con, "app_id": app,
        "rect": rectangle, "percent": 0.5 if app == "brave" else None,
        "layout": "none", "floating": "user_on" if floating else "auto_off",
        "nodes": [], "floating_nodes": [],
        "window_rect": None, "deco_rect": None, "geometry": None,
        "fullscreen_mode": 0, "title": "PRIVATE TITLE",
        "pid": 7700,
    }


def fixture():
    outputs = [
        {"name": "DP-3", "active": True, "rect": rect(0, 0, 2560, 1440),
         "scale": 1.0, "transform": "normal"},
        {"name": "HDMI-A-1", "active": True,
         "rect": rect(2560, 0, 1360, 768), "scale": 1.0,
         "transform": "normal"},
    ]
    workspaces = [{"name": "1", "output": "DP-3"},
                  {"name": "2", "output": "HDMI-A-1"}]
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [{
            "type": "workspace", "name": "1", "layout": "splith",
            "rect": rect(0, 0, 2560, 1440),
            "nodes": [leaf(101, "brave", rect(0, 0, 1280, 1440)),
                      leaf(102, "brave", rect(1280, 0, 1280, 1440))],
            "floating_nodes": [],
        }]},
        {"type": "output", "name": "HDMI-A-1", "nodes": [{
            "type": "workspace", "name": "2", "layout": "splith",
            "rect": rect(2560, 0, 1360, 768), "nodes": [],
            "floating_nodes": [
                leaf(103, "kitty", rect(2790, 40, 700, 600), floating=True)],
        }]},
    ]}
    geometry = project_geometry(
        outputs, workspaces, tree,
        window_keys={101: KEY_A, 102: KEY_B, 103: KEY_C})
    legacy_doc = {
        "schema_version": 1, "kind": "sway-layout-selection-preview",
        "preview_only": True, "label": "Exact work layout",
        "captured_at_utc": "2026-11-09T17:48:00+00:00",
        "outputs": [
            {"connector": item["connector"], "rect": item["rect"]}
            for item in geometry["outputs"]],
        "workspaces": [
            {"name": item["name"], "output": item["output"]}
            for item in geometry["workspaces"]],
        "windows": [
            {"app_id": item["app_id"], "workspace": item["workspace"],
             "floating": item["floating"]}
            for item in geometry["windows"]],
    }
    return legacy_doc, geometry


old, geo = fixture()

def reserve(cid, a=old, b=geo):
    return prepare(identity=cid, v1_document=a, geometry_document=b)

def dispatch(cid, a=old, b=geo, **kwargs):
    return dispatch_once(identity=cid, v1_document=a, geometry_document=b, **kwargs)

# Separate process using only the original caller-known ID and retained pair.
# Terminate abruptly at a selected stage, or discard the committed reply.
if len(sys.argv) == 4 and sys.argv[1] == "child":
    mode, cid = sys.argv[2:4]
    if mode == "prepare":
        reserve(cid)
    else:
        def hook(stage):
            if stage == mode:
                os._exit(73)
        dispatch(cid, stage_hook=hook)
        assert mode == "after_commit"
    os._exit(73)

checks = 0

def check(ok, why):
    global checks
    assert ok, why
    checks += 1

def reject(fn, why):
    global checks
    try:
        fn()
    except OriginalSaveRefused as exc:
        assert str(exc) == "TIMEW ORIGINAL LOCAL SAVE REFUSED"
        checks += 1
    else:
        raise AssertionError("unexpected acceptance: " + why)

def outcome(cid, status):
    r = inspect(cid)
    check(r["status"] == status, repr(r))
    check(r["checkpoint_id"] == cid, "original UUID retained")
    check(r["read_only"] is True and r["local_data_only"] is True,
          "local-only observation")
    for k in ("protected_attempt_verified", "source_authenticated",
              "operator_selection_verified", "c5_spent_verified",
              "native_receipt_verified", "production_restore_allowed",
              "automatic_retry_allowed", "automatic_undo_allowed"):
        check(r[k] is False, "deny " + k)
    check(r["safe_actions"] == [], "no actions")
    return r

def child(mode, cid):
    p = subprocess.run([sys.executable, "-B", "-I", __file__, "child", mode, cid],
                       capture_output=True, timeout=30)
    check(p.returncode == 73, repr(p.stderr))

def count_rows(cid):
    with sqlite3.connect(legacy.db_path()) as c:
        old_n = c.execute("SELECT COUNT(*) FROM checkpoints WHERE id=?", (cid,)).fetchone()[0]
        present = c.execute("SELECT 1 FROM sqlite_master WHERE name=?", (GEO_TABLE,)).fetchone()
        geo_n = 0 if present is None else c.execute(
            f"SELECT COUNT(*) FROM {GEO_TABLE} WHERE checkpoint_id=?", (cid,)).fetchone()[0]
        return old_n, geo_n

with tempfile.TemporaryDirectory(prefix="timew-m9-original-") as root:
    previous = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = root
    try:
        cid = new_identity()
        path = legacy.db_path()
        check(uuid.UUID(cid).version == 4, "caller preallocates UUID")
        outcome(cid, "ORIGINAL_SAVE_UNKNOWN_HOLD")
        reject(lambda: dispatch(cid), "unreserved id")
        bad = copy.deepcopy(old)
        bad["private_title"] = "refuse"
        reject(lambda: reserve(cid, bad), "invalid original pair")
        reject(lambda: reserve(cid.upper()), "noncanonical id")
        check(not path.exists(), "no database for absent read or invalid pair")
        (Path(root) / "post-apollo").mkdir(mode=0o700)

        # Caller knows original ID even if preparation itself loses its reply.
        child("prepare", cid)
        outcome(cid, PREPARED)
        check(count_rows(cid) == (0, 0), "reservation writes no checkpoint")
        reject(lambda: reserve(cid), "duplicate reserve")
        changed = copy.deepcopy(old)
        changed["label"] = "changed original"
        reject(lambda: dispatch(cid, changed), "different original pair")
        outcome(cid, PREPARED)

        # Actual post-commit response loss; original ID locates both rows.
        child("after_commit", cid)
        outcome(cid, "LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED")
        check(count_rows(cid) == (1, 1), "one original pair")
        check(legacy.load(cid)["document"] == legacy.validate(old), "legacy read intact")
        check(load_geometry(cid)["geometry"] == geo, "geometry read intact")
        reject(lambda: dispatch(cid), "no replay after commit")
        reject(lambda: reserve(cid), "no overwrite")
        outcome(cid, "LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED")

        # Existing ordinary Save path stays compatible; same label is not
        # sufficient to resolve an original attempt.
        other = save_pair(old, geo)["checkpoint"]["id"]
        check(other != cid and count_rows(other) == (1, 1), "normal save intact")
        outcome(other, "ORIGINAL_SAVE_UNKNOWN_HOLD")
        reject(lambda: reserve(other), "cannot claim existing legacy id")

        for stage in ("after_dispatch_marker", "after_v1_insert",
                      "after_geometry_insert", "after_association"):
            original = new_identity()
            reserve(original)
            child(stage, original)
            outcome(original, MARKED)
            check(count_rows(original) == (0, 0), "atomic rollback at " + stage)
            reject(lambda: dispatch(original), "marked attempt cannot replay")
            reject(lambda: reserve(original), "no new reservation for original id")
        check(count_rows(cid) == (1, 1) and count_rows(other) == (1, 1),
              "earlier saved pairs preserved")

        # Competing ordinary local data at original ID must not be adopted.
        conflict = new_identity()
        reserve(conflict)
        with sqlite3.connect(path) as conn:
            conn.execute("""INSERT INTO checkpoints
                SELECT ?,schema_version,label,saved_at_utc,captured_at_utc,document_json
                FROM checkpoints WHERE id=?""", (conflict, cid))
        outcome(conflict, "ORIGINAL_SAVE_CONFLICT_HOLD")
        reject(lambda: dispatch(conflict), "existing row refused")

        # Change a committed row independently; never promote stale record.
        with sqlite3.connect(path) as conn:
            conn.execute("UPDATE checkpoints SET label=? WHERE id=?", ("other", cid))
        outcome(cid, "ORIGINAL_SAVE_CONFLICT_HOLD")
        with sqlite3.connect(path) as conn:
            conn.execute("UPDATE checkpoints SET label=? WHERE id=?", (old["label"], cid))
        outcome(cid, "LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED")

        # A real missing half is a conflict, even when association remains.
        with sqlite3.connect(path) as conn:
            conn.execute(f"DELETE FROM {GEO_TABLE} WHERE checkpoint_id=?", (cid,))
        outcome(cid, "ORIGINAL_SAVE_CONFLICT_HOLD")
        reject(lambda: dispatch(cid), "missing half cannot trigger repair")
        check(count_rows(cid) == (1, 0), "no repair on inspection")

        path.chmod(0o644)
        outcome(cid, "ORIGINAL_SAVE_UNKNOWN_HOLD")
        reject(lambda: reserve(new_identity()), "unsafe database")
        check(path.stat().st_mode & 0o077 != 0, "no automatic chmod")
        path.chmod(0o600)
        with sqlite3.connect(path) as conn:
            check(conn.execute("PRAGMA user_version").fetchone()[0] == 1,
                  "legacy schema version unchanged")
            check(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                  "integrity")
            check(conn.execute(f"SELECT phase FROM {TABLE} WHERE id=?", (cid,)).fetchone()[0]
                  == COMMITTED, "commit association retained")
            check(conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] == 6,
                  "one retained record per actual reservation")
    finally:
        if previous is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = previous

for p in (ROOT / "widgets/TimeW.qml", SERVICE / "MachineSaveBridgeV2.py",
          SERVICE / "MachineCaptureSaveV2.py"):
    check("MachineV3OriginalSaveIdentity" not in p.read_text(), "no live path")
print("TIMEW M9 ORIGINAL SAVE IDENTITY // " + str(checks) +
      " local atomicity, lost reply and no-replay checks PASS")
