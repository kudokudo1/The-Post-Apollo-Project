#!/usr/bin/env python3
"""MACHINE save bridge: duplicate browser windows, guarded custom review and v1/v2 storage.

All reads synthetic; SQLite confined to temporary XDG_DATA_HOME.
"""
import copy
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/time"))
from MachineSaveBridgeV2 import inspect, save_request, BridgeError
from MachineCaptureSaveV2 import CaptureError
from MachineGeometryStoreV2 import load_geometry
import MachineCheckpointStore as legacy


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def node(con, app, box, floating=False):
    return {
        "type": "floating_con" if floating else "con",
        "id": con, "app_id": app, "rect": box, "layout": "none",
        "percent": None, "floating": "user_on" if floating else "auto_off",
        "fullscreen_mode": 0, "nodes": [], "floating_nodes": [],
        "name": "PRIVATE BROWSER TITLE", "pid": 4567,
    }


def fixture():
    outputs = [{"name": "DP-3", "active": True,
                "rect": rect(0, 0, 2560, 1440), "scale": 1.0,
                "transform": "normal", "serial": "PRIVATE SERIAL"},
               {"name": "HDMI-A-1", "active": True,
                "rect": rect(2560, 0, 1360, 768), "scale": 1.0,
                "transform": "normal"}]
    workspaces = [{"name": "1", "output": "DP-3"},
                  {"name": "2", "output": "HDMI-A-1"}]
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [
            {"type": "workspace", "name": "1", "layout": "splith",
             "rect": rect(0, 0, 2560, 1440),
             "nodes": [node(101, "brave", rect(0, 0, 1280, 1440)),
                       node(102, "brave", rect(1280, 0, 1280, 1440))],
             "floating_nodes": []}]},
        {"type": "output", "name": "HDMI-A-1", "nodes": [
            {"type": "workspace", "name": "2", "layout": "splith",
             "rect": rect(2560, 0, 1360, 768),
             "nodes": [], "floating_nodes": [
                 node(103, "kitty", rect(2700, 40, 750, 650), True)]}]},
    ]}
    return [outputs, workspaces, tree]


def reader(first, second=None):
    calls = []
    frames = [copy.deepcopy(first), copy.deepcopy(first if second is None else second)]
    def run(command, **kwargs):
        assert command == ["swaymsg", "-r", "-t",
                           ("get_outputs", "get_workspaces", "get_tree")[len(calls) % 3]]
        assert kwargs == {"check": True, "capture_output": True, "timeout": 3, "shell": False}
        result = frames[len(calls) // 3][len(calls) % 3]
        calls.append(command)
        return SimpleNamespace(stdout=json.dumps(result).encode("utf-8"))
    return run, calls


NONCE = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
frame = fixture()
inspector, calls = reader(frame)
review = inspect(read_runner=inspector, namespace_factory=lambda: NONCE)
assert len(calls) == 6
assert review["status"] == "ready"
assert review["read_only"] and not review["restorable_identity_verified"]
assert review["counts"] == {"outputs": 2, "workspaces": 2, "windows": 3}
assert review["review"]["namespace"] == str(NONCE)
assert len(review["review"]["digest"]) == 64
assert [x["app_id"] for x in review["windows"]] == ["brave", "brave", "kitty"]
keys = [x["window_key"] for x in review["windows"]]
assert len(set(keys)) == 3
assert review["windows"][0]["rect"] != review["windows"][1]["rect"]
visible = json.dumps(review)
for private in ("PRIVATE BROWSER TITLE", "PRIVATE SERIAL", '"pid"', '"con_id"', '"title"', "4567"):
    assert private not in visible, private


def refuses(req, *, base=None, modified=None, message=None):
    runner, calls = reader(frame if base is None else base, modified)
    try:
        save_request(req, read_runner=runner)
    except (BridgeError, CaptureError) as exc:
        if message:
            assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError("bad/stale SAVE accepted")
    return calls


full_request = {"label": "Desktop check", "review": None, "selection": None}
custom_request = {
    "label": "Brave left",
    "review": review["review"],
    "selection": {"windows": [keys[0]]},
}
refuses({"label": "X", "selection": None}, message="INVALID SAVE REQUEST")
refuses({"label": "X", "review": None, "selection": {"windows": []}},
        message="CUSTOMIZE REVIEW REQUIRED")
refuses({"label": "X", "review": review["review"], "selection": None},
        message="CUSTOMIZE REVIEW REQUIRED")
refuses(dict(custom_request, review={"namespace": "bad", "digest": "0" * 64}),
        message="INVALID CUSTOMIZE REVIEW")
refuses(dict(custom_request, label="X" * 49), message="INVALID SAVE LABEL")

changed = copy.deepcopy(frame)
changed[2]["nodes"][0]["nodes"][0]["nodes"][0]["rect"]["width"] -= 1
replaced = copy.deepcopy(frame)
replaced[2]["nodes"][0]["nodes"][0]["nodes"][0]["id"] = 999

old_xdg = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="machine-ui-bridge-") as temp:
        os.environ["XDG_DATA_HOME"] = temp
        assert not legacy.db_path().exists()
        for modified in (changed, replaced):
            refuses(custom_request, modified=modified)
            assert not legacy.db_path().exists()

        # Even if Sway is stable *at save*, any movement since inspection
        # invalidates the digest before a database can be created.
        shifted = copy.deepcopy(frame)
        shifted[2]["nodes"][0]["nodes"][0]["nodes"][0]["rect"]["x"] += 10
        refuses(custom_request, base=shifted, message="CUSTOM SELECTION STALE")
        assert not legacy.db_path().exists()
        stale_id = copy.deepcopy(frame)
        stale_id[2]["nodes"][0]["nodes"][0]["nodes"][0]["id"] = 909
        refuses(custom_request, base=stale_id, message="CUSTOM SELECTION STALE")
        assert not legacy.db_path().exists()

        runner, calls = reader(frame)
        result = save_request(custom_request, read_runner=runner)
        assert len(calls) == 6
        assert result["status"] == "saved"
        assert result["verification"] == {
            "status": "readback_verified",
            "counts": {"outputs": 2, "workspaces": 2, "windows": 1},
            "geometry": True, "legacy": True,
        }
        assert result["checkpoint"]["counts"]["windows"] == 1
        saved_id = result["checkpoint"]["id"]
        geo = load_geometry(saved_id)["geometry"]
        assert geo["windows"][0]["window_key"] == keys[0]
        assert geo["windows"][0]["rect"] == rect(0, 0, 1280, 1440)
        assert geo["windows"][0]["app_id"] == "brave"
        assert legacy.load(saved_id)["document"]["windows"] == [
            {"app_id": "brave", "workspace": "1", "floating": False}]

        full, six = reader(frame)
        result_full = save_request(full_request, read_runner=full)
        assert len(six) == 6
        assert result_full["status"] == "saved"
        assert result_full["verification"]["status"] == "readback_verified"
        assert result_full["verification"]["counts"] == {
            "outputs": 2, "workspaces": 2, "windows": 3,
        }
        assert result_full["checkpoint"]["counts"]["windows"] == 3
        assert len(legacy.listing()["checkpoints"]) == 2
        assert load_geometry(saved_id)["geometry"] == geo

        # The actual commit already happened. An independent read-back error
        # must report the saved UUID as unverified, never fabricate failure
        # before storage or encourage a blind duplicate retry.
        def broken_readback(checkpoint_id):
            raise OSError("synthetic read-only lookup failure")
        before_unverified = len(legacy.listing()["checkpoints"])
        read_runner, _ = reader(frame)
        unverified = save_request(
            full_request, read_runner=read_runner,
            geometry_reader=broken_readback)
        assert unverified["status"] == "saved_unverified"
        assert unverified["verification"] == {"status": "readback_unavailable"}
        assert unverified["checkpoint"]["id"] != saved_id
        assert len(legacy.listing()["checkpoints"]) == before_unverified + 1
        # This synthetic failure does not damage or rewrite the actual data.
        assert load_geometry(unverified["checkpoint"]["id"])["status"] == "loaded"

        # Disagreeing read-back counts are likewise not advertised verified.
        real_readback = load_geometry
        def wrong_counts(checkpoint_id):
            record = copy.deepcopy(real_readback(checkpoint_id))
            record["geometry"]["windows"].pop()
            return record
        count_runner, _ = reader(frame)
        mismatch = save_request(
            full_request, read_runner=count_runner,
            geometry_reader=wrong_counts)
        assert mismatch["status"] == "saved_unverified"
        assert mismatch["verification"]["status"] == "readback_unavailable"
        assert load_geometry(mismatch["checkpoint"]["id"])["status"] == "loaded"

        # A stable desktop where the wrong monitor is selected is refused
        # before changing the user's persistent checkpoints.
        initial = legacy.listing()
        invalid_request = dict(custom_request, selection={"outputs": ["DP-3"], "windows": [keys[2]]})
        refuses(invalid_request, message="WINDOW IN EXCLUDED WORKSPACE")
        assert legacy.listing() == initial
finally:
    if old_xdg is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = old_xdg

print("MACHINE SAVE UI BRIDGE // one-click full, bound custom and stale refusal PASS")
