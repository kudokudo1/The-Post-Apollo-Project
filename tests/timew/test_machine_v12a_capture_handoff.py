#!/usr/bin/env python3
"""M12a proposed capture handoff; synthetic inputs, actual local M10 stores."""
import copy
import datetime as dt
import math
import os
from pathlib import Path
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineGeometryV2 import project_geometry
from MachineV2ExactLogicalGeometry import capture_value, PHASE_CURRENT
from MachineV3LocalSaveRecovery import _canonical_candidates
from MachineV3CaptureHandoff import KIND, prepare_local_capture, CaptureHandoffRefused
from MachineV3CoordinatedLocalSave import save_once, recover
from MachineV3LocalFractionalAttemptJournal import LocalFractionalAttemptJournal, suggested_path as journal_path
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore, suggested_path as exact_path

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
    return outputs, workspaces, tree


identity = "55555555-5555-4555-8555-555555555555"
epoch = "66666666-6666-4666-8666-666666666666"
now = dt.datetime(2026, 11, 25, 4, 0, tzinfo=dt.timezone.utc)
outputs, workspaces, tree = fixture()
geo = project_geometry(outputs, workspaces, tree, window_keys={101: KEY_A, 102: KEY_B, 103: KEY_C})
ids = {KEY_A: 101, KEY_B: 102, KEY_C: 103}
base = dict(kind=KIND, epoch=epoch, revision=5, pending_transaction=False,
            queued_transaction=False, outputs=outputs, workspaces=workspaces, tree=tree, windows=[])
for n, w in enumerate(geo["windows"]):
    # Fixture bits deliberately distinguish the two same-app windows by one ULP.
    value = capture_value(PHASE_CURRENT,
                          x=12.125 if n == 0 else math.nextafter(12.125, math.inf),
                          y=92.125, width=700.5, height=600.25)
    base["windows"].append(dict(con_id=ids[w["window_key"]],
        lifetime=str(uuid.uuid4()), app_id=w["app_id"], output_id=w["output"],
        workspace_id=w["workspace"], phase="CURRENT", current_bits=[
            format(getattr(value, k), "016x") for k in
            ("x_bits","y_bits","width_bits","height_bits")]))
checks = 0

def check(ok, reason):
    global checks
    assert ok, reason
    checks += 1

def prepare(a=None, b=None, **kw):
    a = copy.deepcopy(base) if a is None else a
    b = copy.deepcopy(base) if b is None else b
    args = dict(identity=identity, first=a, second=b, label="Fixture", captured_at=now)
    args.update(kw)
    return prepare_local_capture(**args)

def reject(a=None, b=None, **kw):
    try:
        prepare(a,b,**kw)
    except CaptureHandoffRefused as exc:
        check(str(exc) == "TIMEW FRACTIONAL CAPTURE HANDOFF REFUSED", "safe refusal")
    else:
        raise AssertionError("invalid handoff accepted")

def change(fn, both=False):
    b=copy.deepcopy(base)
    fn(b)
    reject(copy.deepcopy(b) if both else copy.deepcopy(base), b)

with tempfile.TemporaryDirectory(prefix="timew-m12a-") as root:
    prior=os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"]=root
    try:
        first,second=copy.deepcopy(base),copy.deepcopy(base)
        result=prepare(first,second)
        check(result["status"]=="LOCAL_CAPTURE_CANDIDATES_UNTRUSTED","local status")
        check(result["identity"]==identity and result["safe_actions"]==[],"bound id")
        for k in ("source_authenticated","snapshot_atomic_verified","native_receipt_verified",
                  "operator_selection_verified","c5_spent_verified","production_restore_allowed",
                  "automatic_retry_allowed"):
            check(result[k] is False,k)
        check(result["read_only"] and result["local_data_only"],"read only")
        expected={}
        for row in base["windows"]:
            key=str(uuid.uuid5(uuid.UUID(identity),f'{epoch}:{row["con_id"]}:{row["lifetime"]}'))
            expected[key]=tuple(row["current_bits"])
        observed=_canonical_candidates(result["observations"])
        check({r[0]:tuple(r[4:]) for r in observed}==expected,"exact original bit patterns")
        check(len(observed)==3 and len({r[0] for r in observed})==3,"distinct same app")
        check(len({r[4] for r in observed})==2,"one ULP retained")
        check(result["geometry_document"]["session_identity_verified"] is False,"no stable identity")
        check(prepare()["geometry_document"]==result["geometry_document"],"original namespace stable")
        check(prepare(identity=str(uuid.uuid4()))["geometry_document"]!=result["geometry_document"],
              "different save namespace")
        second["windows"].reverse()
        check(prepare(first,second)["observations"]==result["observations"],"row order irrelevant")
        first["windows"][0]["current_bits"][0]="0000000000000000"
        check(_canonical_candidates(result["observations"])==observed,"caller mutation not retained")
        reject(base,base)
        reject(identity="bad")
        reject(label="bad\n")
        reject(captured_at=dt.datetime(2026,11,25))
        for field,value in (("kind","future"),("epoch","bad"),("revision",True),("revision",-1),
                            ("revision",2**64),("pending_transaction",True),("queued_transaction",True),
                            ("pending_transaction",0),("source_authenticated",True)):
            change(lambda b,f=field,v=value:b.__setitem__(f,v),both=True)
        change(lambda b:b.__setitem__("epoch",str(uuid.uuid4())))
        change(lambda b:b.__setitem__("revision",6))
        change(lambda b:b["outputs"][0].__setitem__("scale",1.25))
        change(lambda b:b["outputs"][0]["rect"].__setitem__("width",2559))
        change(lambda b:b["tree"]["nodes"][0]["nodes"][0]["nodes"][0]["rect"].__setitem__("width",1279))
        change(lambda b:b["windows"][0].__setitem__("lifetime",str(uuid.uuid4())))
        change(lambda b:b["windows"][0]["current_bits"].__setitem__(0,format(
            int(b["windows"][0]["current_bits"][0],16)+1,"016x")))
        for field,value in (("con_id",True),("con_id",0),("con_id",999),("lifetime","bad"),
                            ("app_id","other"),("output_id","other"),("workspace_id","other"),
                            ("phase","PENDING"),("current_bits",[0,1,2,3]),
                            ("current_bits",["7ff0000000000000"]*4),
                            ("current_bits",["8000000000000000"]*4),
                            ("current_bits",["0000000000000000"]*4),
                            ("current_bits",["3ff0000000000000"]*3),
                            ("source_authenticated",True)):
            change(lambda b,f=field,v=value:b["windows"][0].__setitem__(f,v),both=True)
        change(lambda b:b["windows"].pop(),both=True)
        change(lambda b:b["windows"].append(copy.deepcopy(b["windows"][0])),both=True)
        change(lambda b:b["windows"][1].__setitem__("lifetime",b["windows"][0]["lifetime"]),both=True)
        change(lambda b:b["windows"].clear(),both=True)
        check(not (Path(root)/"post-apollo").exists(),"preparation and refusals do not create files")

        # Explicit development-only caller, not an active Save hook. Real M10
        # consumes the exact output unchanged. Native origin is not proven.
        (Path(root)/"post-apollo").mkdir(mode=0o700)
        journal,store=LocalFractionalAttemptJournal(journal_path()),LocalExactCaptureStore(exact_path())
        outcome=save_once(identity=identity, v1_document=result["v1_document"],
                          geometry_document=result["geometry_document"],
                          observations=result["observations"],journal=journal,store=store)
        check(outcome["status"]=="COORDINATED_LOCAL_RECORDS_OBSERVED_UNTRUSTED","real M10 integration")
        check(recover(identity,journal=journal,store=store)==outcome,"read-only recovery")
        check(len(store.for_checkpoint(identity))==3,"full exact rows persisted")
        for field in ("source_authenticated","production_restore_allowed","native_receipt_verified"):
            check(outcome[field] is False,"M10 denies authority")
    finally:
        if prior is None:
            os.environ.pop("XDG_DATA_HOME",None)
        else:
            os.environ["XDG_DATA_HOME"]=prior

for p in (ROOT/"widgets/TimeW.qml",ROOT/"services/time/MachineSaveBridgeV2.py"):
    check("MachineV3CaptureHandoff" not in p.read_text(),"no active Save hook")
print("TIMEW M12A CAPTURE HANDOFF // "+str(checks)+" proposed snapshot / actual local M10 checks PASS")
