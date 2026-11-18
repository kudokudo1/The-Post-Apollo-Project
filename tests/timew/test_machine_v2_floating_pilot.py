#!/usr/bin/env python3
"""MACHINE disposable V2 floating-window placement: two Brave windows, two outputs.

Synthetic command execution only. The fake controller changes in-memory Sway
JSON; never calls the user's compositor or reads browser data.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineCaptureSaveV2 import _legacy_from_geometry
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import save_pair, load_geometry
import MachineCheckpointStore as legacy
import MachineV2FloatingPilot as pilot

KEY_A = "11111111-1111-4111-8111-111111111111"
KEY_B = "22222222-2222-4222-8222-222222222222"


def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def leaf(i, r, app="brave"):
    return {
        "type": "floating_con", "id": i, "app_id": app, "rect": r,
        "layout": "none", "floating": "user_on", "percent": None,
        "fullscreen_mode": 0, "nodes": [], "floating_nodes": [],
        "title": "PRIVATE BROWSER TITLE", "pid": 70123,
    }


def frame(ids=(11, 12), boxes=None):
    if boxes is None:
        boxes = (rect(100, 100, 800, 500),
                 rect(2100, 130, 700, 520))
    outputs = [
        {"name": "DP-3", "active": True, "rect": rect(0, 0, 1920, 1080),
         "scale": 1.0, "transform": "normal"},
        {"name": "HDMI-A-1", "active": True,
         "rect": rect(1920, 0, 1920, 1080),
         "scale": 1.0, "transform": "normal"}]
    workspaces = [{"name": "1", "output": "DP-3"},
                  {"name": "2", "output": "HDMI-A-1"}]
    tree = {
        "type": "root", "nodes": [
            {"type": "output", "name": "DP-3", "nodes": [
                {"type": "workspace", "name": "1", "layout": "splith",
                 "rect": rect(0, 0, 1920, 1080), "nodes": [],
                 "floating_nodes": [leaf(ids[0], boxes[0])]}]},
            {"type": "output", "name": "HDMI-A-1", "nodes": [
                {"type": "workspace", "name": "2", "layout": "splith",
                 "rect": rect(1920, 0, 1920, 1080), "nodes": [],
                 "floating_nodes": [leaf(ids[1], boxes[1])]}]},
        ]}
    return outputs, workspaces, tree


class FakeSway:
    def __init__(self):
        self.state = frame((110, 111),
                           (rect(30, 80, 510, 360),
                            rect(2220, 190, 560, 410)))
        self.commands = []
        self.reads = 0
        self.fail_command = None
        self.no_effect = False
        self.change_on_read = None

    def win(self, ident):
        for output in self.state[2]["nodes"]:
            for ws in output["nodes"]:
                for win in ws["floating_nodes"]:
                    if win["id"] == ident:
                        return win
        return None

    def read(self, argv, **kw):
        assert kw == {"check": True, "capture_output": True,
                      "timeout": 3, "shell": False}
        assert argv[:3] == ["swaymsg", "-r", "-t"]
        assert argv[3] in ("get_outputs", "get_workspaces", "get_tree")
        if self.change_on_read is not None and self.reads == self.change_on_read:
            self.win(110)["rect"]["x"] += 1
        idx = {"get_outputs": 0, "get_workspaces": 1, "get_tree": 2}[argv[3]]
        self.reads += 1
        return SimpleNamespace(stdout=json.dumps(self.state[idx]).encode("utf-8"),
                               returncode=0)

    def command(self, argv, **kw):
        assert kw == {"check": False, "capture_output": True,
                      "timeout": 3, "shell": False}
        assert argv[:4] == ["swaymsg", "-r", "-t", "command"]
        assert len(argv) == 5
        cmd = argv[4]
        self.commands.append(cmd)
        n = len(self.commands)
        if self.fail_command == n:
            return SimpleNamespace(stdout=b'[{"success":false}]', returncode=0)
        size = re.fullmatch(
            r"\[con_id=([1-9][0-9]*)\] resize set ([1-9][0-9]*) px ([1-9][0-9]*) px",
            cmd)
        place = re.fullmatch(
            r"\[con_id=([1-9][0-9]*)\] move absolute position ([0-9]+) px ([0-9]+) px",
            cmd)
        assert size or place, cmd
        found = size or place
        win = self.win(int(found.group(1)))
        assert win is not None
        if not self.no_effect:
            if size:
                win["rect"]["width"], win["rect"]["height"] = (
                    int(size.group(2)), int(size.group(3)))
            else:
                win["rect"]["x"], win["rect"]["y"] = (
                    int(place.group(2)), int(place.group(3)))
        return SimpleNamespace(stdout=b'[{"success":true}]', returncode=0)


class FixtureJournal:
    def __init__(self):
        self.phases = []
        self.active = False

    def begin(self, summary):
        assert not self.active
        assert set(summary) == {
            "checkpoint_id", "window_key", "app_id", "live_con_id",
            "before_rect", "target_rect"}
        self.active = True
        self.phases.append(("begin", summary["live_con_id"]))
        return "fixture-id"

    def dispatching(self, operation):
        assert self.active and operation == "fixture-id"
        self.phases.append(("dispatching", operation))

    def finish(self, operation, status):
        assert self.active and operation == "fixture-id"
        self.phases.append(("finish", status))
        # A questionable result stays unresolved in a real durable journal.
        self.active = status == "uncertain_requires_review"


def rejects(fn):
    try:
        fn()
    except (pilot.RehearsalRefused, ValueError, KeyError, TypeError):
        return
    raise AssertionError("unsafe V2 floating fixture was accepted")


old_env = {k: os.environ.get(k) for k in ("XDG_DATA_HOME", "CI", "GITHUB_ACTIONS")}
try:
    with tempfile.TemporaryDirectory(prefix="machine-v2-floating-fixture-") as home:
        os.environ["XDG_DATA_HOME"] = home
        saved = frame()
        saved_geo = project_geometry(*saved,
                                    window_keys={11: KEY_A, 12: KEY_B})
        old = _legacy_from_geometry(
            saved_geo, label="Two floating Brave windows",
            captured_at="2026-11-18T00:00:00+00:00")
        result = save_pair(old, saved_geo)
        cid = result["checkpoint"]["id"]
        assert load_geometry(cid)["geometry"] == saved_geo
        request_a = {
            "checkpoint_id": cid, "checkpoint_window_key": KEY_A,
            "live_con_id": 110,
            "operator_selected": True, "execution_approved": True,
            "approval_kind": pilot.APPROVAL_KIND}
        request_b = dict(request_a, checkpoint_window_key=KEY_B,
                         live_con_id=111)

        sway = FakeSway()
        first = pilot.prepare(request_a, read_runner=sway.read)
        assert first["status"] == "manual_fixture_candidate"
        assert first["production_restore_allowed"] is False
        assert first["persistent_identity_verified"] is False
        assert first["browser_tabs_restorable"] is False
        assert first["target"]["rect"] == rect(100, 100, 800, 500)
        assert first["current"]["rect"] == rect(30, 80, 510, 360)
        assert sway.commands == []

        # CUSTOMIZE SAVE uses per-capture UUIDv5 window keys, unlike
        # ordinary UUIDv4 SAVE. They are still only checkpoint-local keys.
        namespace = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
        v5_a = str(uuid.uuid5(namespace, "11"))
        v5_b = str(uuid.uuid5(namespace, "12"))
        custom_geo = project_geometry(*saved, window_keys={
            11: v5_a, 12: v5_b})
        custom_old = _legacy_from_geometry(
            custom_geo, label="Two selected Brave windows",
            captured_at="2026-11-18T00:01:00+00:00")
        custom_id = save_pair(custom_old, custom_geo)["checkpoint"]["id"]
        custom_request = dict(
            request_a, checkpoint_id=custom_id, checkpoint_window_key=v5_a)
        custom_review = pilot.prepare(custom_request, read_runner=sway.read)
        assert custom_review["status"] == "manual_fixture_candidate"
        assert custom_review["persistent_identity_verified"] is False

        for bad in (
            dict(request_a, operator_selected=False),
            dict(request_a, execution_approved=False),
            dict(request_a, approval_kind="production"),
            dict(request_a, live_con_id=0),
            dict(request_a, live_con_id=999),
            dict(request_a, checkpoint_window_key="99999999-9999-4999-8999-999999999999"),
            dict(request_a, untrusted_url="https://private.example"),
        ):
            rejects(lambda bad=bad: pilot.prepare(bad, read_runner=sway.read))
        assert sway.commands == []
        # A different Brave instance on another output remains blocked:
        # manual selection cannot silently override monitor boundaries.
        # Neither same-app identity nor historical correctness is verified.
        rejects(lambda: pilot.prepare(dict(request_a, live_con_id=111),
                                      read_runner=sway.read))

        # Ordinary local/dev invocation does not enable a live dispatcher.
        os.environ.pop("CI", None)
        os.environ.pop("GITHUB_ACTIONS", None)
        rejects(lambda: pilot.execute_disposable(
            request_a, read_runner=sway.read, command_runner=sway.command,
            journal=FixtureJournal()))
        assert sway.commands == []
        os.environ["CI"] = "true"
        os.environ["GITHUB_ACTIONS"] = "true"
        rejects(lambda: pilot.execute_disposable(
            request_a, read_runner=sway.read, command_runner=sway.command,
            journal=None))
        assert sway.commands == []

        # A stale/changed output or an unstable two-read frame cannot dispatch.
        invalid_output = FakeSway()
        invalid_output.state[0][0]["scale"] = 1.25
        rejects(lambda: pilot.execute_disposable(
            request_a, read_runner=invalid_output.read,
            command_runner=invalid_output.command, journal=FixtureJournal()))
        assert invalid_output.commands == []
        unstable = FakeSway()
        unstable.change_on_read = 3  # second round first field
        rejects(lambda: pilot.prepare(request_a, read_runner=unstable.read))
        assert unstable.commands == []

        # Genuine command path under injected Sway runner: two same-app
        # Brave windows manually selected by separate current con_id.
        journal_a = FixtureJournal()
        placed_a = pilot.execute_disposable(
            request_a, read_runner=sway.read,
            command_runner=sway.command, journal=journal_a)
        assert placed_a["status"] == "verified_fixture_placement", placed_a
        assert placed_a["dispatched_commands"] == 2
        assert placed_a["production_restore_allowed"] is False
        assert placed_a["persistent_identity_verified"] is False
        assert placed_a["no_automatic_retry"] is True
        assert journal_a.phases[0][0] == "begin"
        assert journal_a.phases[1][0] == "dispatching"
        assert journal_a.phases[2] == ("finish", "verified_fixture_placement")
        assert sway.win(110)["rect"] == rect(100, 100, 800, 500)
        assert sway.win(111)["rect"] == rect(2220, 190, 560, 410)
        assert sway.commands == [
            "[con_id=110] resize set 800 px 500 px",
            "[con_id=110] move absolute position 100 px 100 px"]
        no_op = pilot.execute_disposable(
            request_a, read_runner=sway.read, command_runner=sway.command,
            journal=FixtureJournal())
        assert no_op["status"] == "already_observed"
        assert len(sway.commands) == 2

        journal_b = FixtureJournal()
        placed_b = pilot.execute_disposable(
            request_b, read_runner=sway.read,
            command_runner=sway.command, journal=journal_b)
        assert placed_b["status"] == "verified_fixture_placement"
        assert sway.win(111)["rect"] == rect(2100, 130, 700, 520)
        assert sway.commands[-2:] == [
            "[con_id=111] resize set 700 px 520 px",
            "[con_id=111] move absolute position 2100 px 130 px"]

        # False-positive IPC success is not accepted without exact postflight.
        phantom = FakeSway()
        phantom.no_effect = True
        receipt = FixtureJournal()
        failed = pilot.execute_disposable(
            request_a, read_runner=phantom.read,
            command_runner=phantom.command, journal=receipt)
        assert failed["status"] == "uncertain_requires_review"
        assert failed["manual_recovery_required"] is True
        assert receipt.active is True
        assert failed["dispatched_commands"] == 2
        assert len(phantom.commands) == 2

        # Midway failure halts. A resize may have happened; never
        # automatically rerun or rollback the non-atomic pair of commands.
        broken = FakeSway()
        broken.fail_command = 2
        receipt = FixtureJournal()
        interrupted = pilot.execute_disposable(
            request_a, read_runner=broken.read,
            command_runner=broken.command, journal=receipt)
        assert interrupted["status"] == "uncertain_requires_review"
        assert receipt.active
        assert len(broken.commands) == 2

        # A journal failure prevents any compositor IPC, rather than
        # falling back to untracked commands.
        class RejectJournal(FixtureJournal):
            def dispatching(self, operation):
                raise ValueError("fixture persistence failed")
        denied = FakeSway()
        rejects(lambda: pilot.execute_disposable(
            request_a, read_runner=denied.read,
            command_runner=denied.command, journal=RejectJournal()))
        assert denied.commands == []

        # Output is never browser data, a recovery grant or a real identity.
        visible = json.dumps(placed_a) + json.dumps(placed_b)
        for private in ("PRIVATE BROWSER TITLE", "70123", "https://",
                        "password", "browser_window_id"):
            assert private not in visible
        assert not hasattr(pilot, "main")
finally:
    for key, value in old_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

print("MACHINE V2 floating selected-window rehearsal // two Brave windows synthetic PASS")
