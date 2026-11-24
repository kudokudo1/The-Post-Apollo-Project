#!/usr/bin/env python3
"""M10: actual ordinary/fractional databases, interrupted coordinated Save."""
import copy
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "time"
sys.path.insert(0, str(SERVICE))
import MachineCheckpointStore as legacy
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import TABLE as GEO_TABLE, save_pair, load_geometry
import MachineV3OriginalSaveIdentity as original
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore, suggested_path as exact_path
from MachineV3LocalFractionalAttemptJournal import (
    LocalFractionalAttemptJournal, suggested_path as journal_path, PREPARED, MARKED,
)
from MachineV2ExactLogicalGeometry import capture_value, PHASE_CURRENT
from MachineV3CoordinatedLocalSave import TABLE, CoordinatedSaveRefused, recover, save_once

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
exact = [
    dict(window_key=w["window_key"], app_id=w["app_id"], output_id=w["output"],
         workspace_id=w["workspace"], value=capture_value(
             PHASE_CURRENT, x=12.125, y=math.nextafter(92.5, math.inf),
             width=700.5, height=600.25))
    for w in geo["windows"]
]

def owners():
    return LocalFractionalAttemptJournal(journal_path()), LocalExactCaptureStore(exact_path())

def save(cid, obs=exact, **kwargs):
    journal, store = owners()
    return save_once(identity=cid, v1_document=old, geometry_document=geo,
                     observations=obs, journal=journal, store=store, **kwargs)

if len(sys.argv) == 4 and sys.argv[1] == "child":
    stage, cid = sys.argv[2:4]
    def stop(point):
        if point == stage:
            os._exit(73)
    save(cid, stage_hook=stop)
    assert stage == "after_reply"
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
    except CoordinatedSaveRefused as exc:
        assert str(exc) == "TIMEW COORDINATED LOCAL SAVE REFUSED"
        checks += 1
    else:
        raise AssertionError("accepted: " + why)

def outcome(cid, status, ordinary=None, fractional=None, linked=None):
    journal, store = owners()
    result = recover(cid, journal=journal, store=store)
    check(result["status"] == status, repr(result))
    check(result["checkpoint_id"] == cid, "original id")
    if ordinary is not None:
        check(result["ordinary_status"] == ordinary, repr(result))
    if fractional is not None:
        check(result["fractional_status"] == fractional, repr(result))
    if linked is not None:
        check(bool(result["fractional_attempt_id"]) == linked, "exact link state")
    check(result["read_only"] and result["manual_review_required"], "local inspection")
    for flag in ("protected_attempt_verified", "source_authenticated",
                 "operator_selection_verified", "c5_spent_verified",
                 "native_receipt_verified", "production_restore_allowed",
                 "automatic_retry_allowed", "automatic_undo_allowed",
                 "cross_database_atomic", "dispatch_execution_verified"):
        check(result[flag] is False, "deny " + flag)
    check(result["safe_actions"] == [], "no executable action")
    return result

def child(stage, cid):
    p = subprocess.run([sys.executable, "-B", "-I", __file__, "child", stage, cid],
                       capture_output=True, timeout=35)
    check(p.returncode == 73, repr(p.stderr))

def counts(cid):
    with sqlite3.connect(legacy.db_path()) as c:
        v1 = c.execute("SELECT COUNT(*) FROM checkpoints WHERE id=?", (cid,)).fetchone()[0]
        table = c.execute("SELECT 1 FROM sqlite_master WHERE name=?", (GEO_TABLE,)).fetchone()
        v2 = 0 if table is None else c.execute(
            f"SELECT COUNT(*) FROM {GEO_TABLE} WHERE checkpoint_id=?", (cid,)).fetchone()[0]
    return v1, v2, len(owners()[1].for_checkpoint(cid))

UNKNOWN = "COORDINATED_SAVE_UNKNOWN_HOLD"
ORD_HOLD = "ORDINARY_SAVE_UNRESOLVED_HOLD"
UNLINKED = "ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD"
PARTIAL = "ORDINARY_OBSERVED_FRACTIONAL_UNRESOLVED_HOLD"
MATCH = "COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED"
ORD = "LOCAL_ORIGINAL_PAIR_OBSERVED_UNTRUSTED"
ABSENT = "LEGACY_MATCH_LOCAL_EXACT_ABSENT"
BOTH = "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED"

with tempfile.TemporaryDirectory(prefix="timew-m10-coordinated-") as root:
    prev = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = root
    try:
        cid = original.new_identity()
        outcome(cid, UNKNOWN)
        reject(lambda: save(cid, exact[:1]), "incomplete exact input")
        reject(lambda: save(cid, [dict(exact[0], c5_spent=True), *exact[1:]]),
               "forged authority field")
        reject(lambda: save(cid, [dict(exact[0], app_id="wrong"), *exact[1:]]),
               "wrong original window metadata")
        check(not legacy.db_path().exists(), "preflight no files")
        (Path(root) / "post-apollo").mkdir(mode=0o700)

        # Reservation commit survives a lost response, with no saved rows.
        child("after_reserve", cid)
        outcome(cid, ORD_HOLD, ordinary=original.PREPARED, linked=False)
        check(counts(cid) == (0, 0, 0), "reservation only")
        reject(lambda: save(cid), "no reentry for reserved identity")

        # Both ordinary rows persist, but no fractional attempt is linked.
        after_ordinary = original.new_identity()
        child("after_ordinary_commit", after_ordinary)
        outcome(after_ordinary, UNLINKED, ordinary=ORD, linked=False)
        check(counts(after_ordinary) == (1, 1, 0), "ordinary pair only")
        reject(lambda: save(after_ordinary), "no replay after ordinary commit")

        after_prepare = original.new_identity()
        child("after_fractional_prepare", after_prepare)
        outcome(after_prepare, UNLINKED, ordinary=ORD, linked=False)
        j, s = owners()
        matching = [j.get(i) for i in j.list_ids()
                    if j.get(i).binding.checkpoint_id == after_prepare]
        check(len(matching) == 1 and matching[0].phase == PREPARED, "unlinked M8 record exists")
        check(counts(after_prepare) == (1, 1, 0), "no unlinked dispatch")
        reject(lambda: save(after_prepare), "no silent adoption or replay")

        for stage, phase in (("after_link", PREPARED), ("after_fractional_marker", MARKED)):
            interrupted = original.new_identity()
            child(stage, interrupted)
            r = outcome(interrupted, PARTIAL, ordinary=ORD, fractional=ABSENT, linked=True)
            check(owners()[0].get(r["fractional_attempt_id"]).phase == phase, "retained phase")
            check(counts(interrupted) == (1, 1, 0), "no fractional rows")
            reject(lambda: save(interrupted), "no repeat marker or dispatch")

        completed = original.new_identity()
        child("after_fractional_commit", completed)
        r = outcome(completed, MATCH, ordinary=ORD, fractional=BOTH, linked=True)
        check(counts(completed) == (1, 1, 3), "all local rows")
        check(owners()[0].get(r["fractional_attempt_id"]).observations() == exact,
              "retained exact binary64 input")
        reject(lambda: save(completed), "no repeat committed save")
        outcome(completed, MATCH, ordinary=ORD, fractional=BOTH, linked=True)
        normal = original.new_identity()
        check(save(normal)["status"] == MATCH, "explicit whole local save")
        check(counts(normal) == (1, 1, 3), "normal coordinated result")

        # Induce a genuine second-row SQLite failure after fractional marker.
        j,s = owners()
        def break_second(stage):
            if stage == "after_fractional_marker":
                with sqlite3.connect(s.path) as conn:
                    conn.execute("""CREATE TRIGGER m10_abort_second BEFORE INSERT ON exact_captures
                        WHEN NEW.window_key='22222222-2222-4222-8222-222222222222'
                        BEGIN SELECT RAISE(ABORT,'fixture'); END""")
        failed = original.new_identity()
        check(save(failed, stage_hook=break_second)["status"] == PARTIAL,
              "ordinary saved / fractional write refused")
        outcome(failed, PARTIAL, ordinary=ORD, fractional=ABSENT, linked=True)
        check(counts(failed) == (1, 1, 0), "fractional transaction rolled back")
        with sqlite3.connect(s.path) as conn:
            conn.execute("DROP TRIGGER m10_abort_second")
        reject(lambda: save(failed), "no automatic fractional retry")

        # Existing regular checkpoints cannot be retroactively claimed.
        legacy_id = save_pair(old, geo)["checkpoint"]["id"]
        reject(lambda: save(legacy_id), "existing ordinary checkpoint")
        outcome(legacy_id, UNKNOWN)

        # Contradictory linked attempt is never adopted.
        with sqlite3.connect(legacy.db_path()) as conn:
            conn.execute(f"UPDATE {TABLE} SET fractional_attempt_id=? WHERE id=?",
                         (matching[0].id, completed))
        outcome(completed, "FRACTIONAL_LINK_CONFLICT_HOLD", ordinary=ORD, linked=True)
        check(counts(completed) == (1, 1, 3), "read-only conflict")

        # Changing ordinary data must not report coordinated success.
        with sqlite3.connect(legacy.db_path()) as conn:
            conn.execute("UPDATE checkpoints SET label=? WHERE id=?", ("changed", normal))
        outcome(normal, ORD_HOLD, ordinary="ORIGINAL_SAVE_CONFLICT_HOLD", linked=True)
        check(counts(normal) == (1, 1, 3), "no mutation by recovery")
    finally:
        if prev is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = prev

for path in (ROOT / "widgets/TimeW.qml", SERVICE / "MachineSaveBridgeV2.py",
             SERVICE / "MachineCaptureSaveV2.py"):
    check("MachineV3CoordinatedLocalSave" not in path.read_text(), "no live integration")
print("TIMEW M10 COORDINATED LOCAL SAVE // " + str(checks)
      + " orchestration, interruption and no-replay checks PASS")
