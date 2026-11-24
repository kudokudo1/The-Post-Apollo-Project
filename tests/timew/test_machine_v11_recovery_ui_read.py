#!/usr/bin/env python3
"""M11: real disposable local Save recovery CLI and strict response boundary."""
import copy
import json
import math
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
import MachineV3OriginalSaveIdentity as original
import MachineV3CoordinatedLocalSave as coordinated
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore, suggested_path as exact_path
from MachineV3LocalFractionalAttemptJournal import LocalFractionalAttemptJournal, suggested_path as journal_path
from MachineV2ExactLogicalGeometry import capture_value, PHASE_CURRENT
from MachineV3CoordinatedLocalSave import save_once
import MachineV3LocalSaveRecoveryUiRead as ui

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


checks = 0

def check(ok, why):
    global checks
    assert ok, why
    checks += 1

def cli(mode, cid=None, status=None):
    request = str(uuid.uuid4())
    args = [mode, request] + ([] if cid is None else [cid])
    p = subprocess.run([sys.executable, "-B", "-I", str(SERVICE / "MachineV3LocalSaveRecoveryUiRead.py"), *args],
                       capture_output=True, timeout=25)
    check(p.returncode == 0 and not p.stderr, repr(p.stderr))
    check(len(p.stdout) <= ui.MAX_BYTES + 1, "bounded packet")
    result = json.loads(p.stdout)
    check(result["kind"] == ui.KIND and result["request_id"] == request, "correlated packet")
    check(result["mode"] == mode and result["checkpoint_id"] == cid, "correlated selection")
    check(result["read_only"] is True and result["local_data_only"] is True
          and result["manual_review_required"] is True, "display only")
    for field in ui.DENIALS:
        check(result[field] is False, "deny " + field)
    check(result["safe_actions"] == [], "no actions")
    if status is not None:
        check(result["status"] == status, repr(result))
    for forbidden in ("pair_sha256", "candidate_sha256", "document_json", "PRIVATE TITLE", "Exact work layout"):
        check(forbidden not in p.stdout.decode(), "no private material")
    return result

def stop_at(stage):
    def stop(point):
        if point == stage:
            raise ValueError("private exception")
    return stop

with tempfile.TemporaryDirectory(prefix="timew-m11-ui-read-") as root:
    prior = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = root
    try:
        parent = Path(root) / "post-apollo"
        check(cli("list", status="NO_LOCAL_INTENTS_OBSERVED")["intent_ids"] == [], "empty")
        cid = original.new_identity()
        cli("inspect", cid, "COORDINATED_SAVE_UNKNOWN_HOLD")
        check(not parent.exists(), "read only does not create parent")
        for args in ([], ["save", cid], ["list", "bad"], ["inspect", cid, "bad"],
                     ["list", cid, "extra"], ["inspect", cid, cid.upper()]):
            p = subprocess.run([sys.executable, "-B", "-I", str(SERVICE / "MachineV3LocalSaveRecoveryUiRead.py"), *args],
                               capture_output=True, timeout=25)
            check(p.returncode != 0 and not p.stdout and not p.stderr, "invalid invocation refused")
        parent.mkdir(mode=0o700)
        no_pair = original.new_identity()
        save(no_pair, stage_hook=stop_at("after_reserve"))
        check(cli("list", status="LOCAL_INTENTS_OBSERVED")["intent_ids"] == [no_pair],
              "discover attempt with no checkpoint")
        a = cli("inspect", no_pair, "ORDINARY_SAVE_UNRESOLVED_HOLD")
        check(a["ordinary_status"] == original.PREPARED and a["fractional_status"] is None,
              "ordinary unresolved")
        unlinked = original.new_identity()
        save(unlinked, stage_hook=stop_at("after_fractional_prepare"))
        cli("inspect", unlinked, "ORDINARY_OBSERVED_FRACTIONAL_UNLINKED_HOLD")
        partial = original.new_identity()
        save(partial, stage_hook=stop_at("after_fractional_marker"))
        a = cli("inspect", partial, "ORDINARY_OBSERVED_FRACTIONAL_UNRESOLVED_HOLD")
        check(a["fractional_status"] == "LEGACY_MATCH_LOCAL_EXACT_ABSENT", "no observed fractional rows")
        complete = original.new_identity()
        check(save(complete)["status"] == "COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED", "local fixture")
        a = cli("inspect", complete, "COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED")
        check(a["fractional_status"] == coordinated.EXACT_MATCH, "local rows observed")
        check(cli("list", status="LOCAL_INTENTS_OBSERVED")["intent_ids"] ==
              sorted([no_pair, unlinked, partial, complete]), "bounded UUID-only discovery")
        # Ordinary pre-M9 checkpoint is not an original coordinated attempt.
        from MachineGeometryStoreV2 import save_pair
        normal = save_pair(old, geo)["checkpoint"]["id"]
        check(normal not in cli("list")["intent_ids"], "no adoption of ordinary Save")
        cli("inspect", normal, "COORDINATED_SAVE_UNKNOWN_HOLD")

        # Valid response must not be accepted against a different UUID or
        # carry authority, arbitrary fields, or contradictory status tuples.
        j,s = owners()
        raw = coordinated.recover(complete, journal=j, store=s)
        token = str(uuid.uuid4())
        check(ui._project(raw, complete, token)["request_id"] == token, "project valid response")
        changes = [{"checkpoint_id": partial}, {"status": "SAVED"},
                   {"ordinary_status": original.MARKED}, {"fractional_status": None},
                   {"fractional_attempt_id": None}, {"safe_actions": ["restore"]},
                   {"manual_review_required": False}, {"read_only": 1},
                   {"reason": "private path"}]
        changes += [{k: True} for k in ui.DENIALS]
        for change in changes:
            try:
                ui._project(dict(raw, **change), complete, token)
            except ui.RecoveryReadRefused:
                check(True, "forged response rejected")
            else:
                raise AssertionError("forged response accepted: " + repr(change))

        path = legacy.db_path()
        with sqlite3.connect(path) as conn:
            conn.execute(f"UPDATE {coordinated.TABLE} SET fractional_attempt_id=? WHERE id=?",
                         (original.new_identity(), complete))
        cli("inspect", complete, "FRACTIONAL_LINK_CONFLICT_HOLD")
        before = (path.read_bytes(), j.path.read_bytes(), s.path.read_bytes())
        cli("list")
        cli("inspect", complete)
        check((path.read_bytes(), j.path.read_bytes(), s.path.read_bytes()) == before,
              "inspection never changes retained main files")
        path.chmod(0o644)
        cli("list", status="UNAVAILABLE_HOLD")
        cli("inspect", complete, "COORDINATED_SAVE_UNKNOWN_HOLD")
        path.chmod(0o600)

        # A dangling coordinated table must not be displayed as an empty list.
        with sqlite3.connect(path) as conn:
            conn.execute(f"DELETE FROM {original.TABLE} WHERE id=?", (no_pair,))
        cli("list", status="UNAVAILABLE_HOLD")
        cli("inspect", no_pair, "COORDINATED_SAVE_UNKNOWN_HOLD")
    finally:
        if prior is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = prior

for p in (ROOT / "widgets/TimeW.qml", SERVICE / "MachineSaveBridgeV2.py"):
    check("MachineV3LocalSaveRecoveryUiRead" not in p.read_text(), "no active bridge")
print("TIMEW M11 RECOVERY UI READ // " + str(checks) + " read-only and response checks PASS")
