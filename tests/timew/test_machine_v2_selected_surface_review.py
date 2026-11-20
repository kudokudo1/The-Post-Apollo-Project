#!/usr/bin/env python3
"""Scope A: synthetic same-session manually selected live surface only.

No compositor hook, C3e signer, C5 grant, production trust, Sway commands,
host socket, local workstation, browser tabs or live desktop integration.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from MachineCaptureSaveV2 import _legacy_from_geometry
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import save_pair, load_geometry
from MachineCheckpointStore import load as load_legacy
import MachineV2SelectedSurfaceReview as scope
from MachineV2PairConsent import PAIR_SCHEMA, AUDIENCE as BRAVE_AUDIENCE

KEY_A = str(uuid.uuid4())
KEY_B = str(uuid.uuid4())
SESSION = str(uuid.uuid4())
SEAT = "seat0"
EPOCH = str(uuid.uuid4())
LIFE_A = str(uuid.uuid4())
LIFE_B = str(uuid.uuid4())
CHALLENGE = "d" * 64
NOW = 1763625600000


def rect(x, y, width, height):
    return {"x": x, "y": y, "width": width, "height": height}


def leaf(cid, box):
    return {
        "type": "floating_con", "id": cid, "app_id": "brave",
        "rect": box, "layout": "none", "floating": "user_on",
        "percent": None, "fullscreen_mode": 0,
        "nodes": [], "floating_nodes": [], "pid": 123456,
        "name": "A PRIVATE BRAVE TITLE NOT TO EXPOSE",
    }


def frame(saved=False):
    a, b = ((rect(100, 80, 620, 410), rect(850, 120, 520, 430))
            if saved else
            (rect(220, 250, 480, 320), rect(960, 260, 400, 310)))
    one, two = ((11, 12) if saved else (110, 111))
    outputs = [{"name": "DP-3", "active": True,
                "rect": rect(0, 0, 1920, 1080),
                "scale": 1.0, "transform": "normal"}]
    workspaces = [{"name": "1", "output": "DP-3"}]
    tree = {"type": "root", "nodes": [{
        "type": "output", "name": "DP-3", "nodes": [{
            "type": "workspace", "name": "1", "layout": "splith",
            "rect": rect(0, 0, 1920, 1080),
            "nodes": [], "floating_nodes": [
                leaf(one, a), leaf(two, b),
            ],
        }],
    }]}
    return outputs, workspaces, tree


class FakeReadOnlySway:
    def __init__(self):
        self.state = frame()
        self.read_calls = 0

    def read(self, argv, **kw):
        assert argv[:3] == ["swaymsg", "-r", "-t"]
        assert kw == {"check": True, "capture_output": True,
                      "timeout": 3, "shell": False}
        index = {"get_outputs": 0, "get_workspaces": 1, "get_tree": 2}[argv[3]]
        self.read_calls += 1
        return SimpleNamespace(stdout=json.dumps(self.state[index]).encode(),
                               returncode=0)


def observation(cid, *, life, generation=1, box):
    return {
        "live_con_id": cid, "compositor_epoch": EPOCH,
        "surface_lifetime_id": life, "surface_generation": generation,
        "app_id": "brave", "output": "DP-3", "workspace": "1",
        "rect": copy.deepcopy(box),
        "floating": True, "fullscreen_mode": 0,
    }


def denies(fn):
    try:
        fn()
    except (scope.ScopeARefused, ValueError):
        return
    raise AssertionError("SCOPE A SHOULD REFUSE THE ALTERED EVIDENCE")


old_xdg = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="timew-scope-a-review-") as home:
        os.environ["XDG_DATA_HOME"] = home
        saved = project_geometry(
            *frame(saved=True), window_keys={11: KEY_A, 12: KEY_B})
        v1 = _legacy_from_geometry(
            saved, label="Selected floating window geometry",
            captured_at="2026-11-20T09:00:00+00:00")
        checkpoint_id = save_pair(v1, saved)["checkpoint"]["id"]
        assert load_geometry(checkpoint_id)["status"] == "loaded"

        cur = frame()
        current_a = cur[2]["nodes"][0]["nodes"][0]["floating_nodes"][0]["rect"]
        current_b = cur[2]["nodes"][0]["nodes"][0]["floating_nodes"][1]["rect"]
        target_a = saved["windows"][0]["rect"]
        target_b = saved["windows"][1]["rect"]
        # Two Brave-like windows share app_id, fake PID, and workstation.
        # Protected explicit selection will eventually be a SwayPX owner
        # assertion, but here both selected and observed arrays are untrusted.
        sample = FakeReadOnlySway()
        request = {
            "checkpoint_id": checkpoint_id,
            "window_key": KEY_A,
            "live_con_id": 110,
        }
        selection = {
            "schema": scope.SCHEMA,
            "audience": scope.AUDIENCE,
            "challenge_sha256": CHALLENGE,
            "selection_id": str(uuid.uuid4()),
            "compositor_epoch": EPOCH,
            "surface_lifetime_id": LIFE_A,
            "surface_generation": 1,
            "live_con_id": 110,
            "app_id": "brave", "output": "DP-3", "workspace": "1",
            "floating": True, "fullscreen_mode": 0,
            "before_rect": current_a, "target_rect": target_a,
            "checkpoint_id": checkpoint_id, "window_key": KEY_A,
            "seat_id": SEAT, "session_id": SESSION,
            "issued_ms": NOW, "expires_ms": NOW + 4000,
        }
        observed = [
            observation(110, life=LIFE_A, box=current_a),
            observation(111, life=LIFE_B, box=current_b),
        ]

        def call(*, req=None, token=None, obs=None, time=NOW,
                 session=SESSION, seat=SEAT, challenge=CHALLENGE, reader=None):
            return scope.review_selected_fixture(
                request=request if req is None else req,
                selection=selection if token is None else token,
                observed_surfaces=observed if obs is None else obs,
                now_ms=time, expected_session_id=session,
                expected_seat_id=seat,
                expected_challenge_sha256=challenge,
                read_runner=(reader or sample).read,
                legacy_reader=load_legacy, geometry_reader=load_geometry,
            )

        result = call()
        assert result["status"] == "fixture_consistent_only"
        assert result["scope"] == "selected_live_surface_geometry_only"
        assert result["read_only"] is True
        assert result["restore_allowed"] is False
        assert result["production_authorized"] is False
        assert result["source_origin_verified"] is False
        assert result["compositor_surface_lifetime_verified"] is False
        assert result["active_seat_verified"] is False
        assert result["c5_operator_consent_verified"] is False
        assert result["one_use_grant_spent"] is False
        assert result["brave_window_identity_verified"] is False
        assert result["persistent_brave_identity_verified"] is False
        assert result["browser_tabs_restorable"] is False
        assert result["safe_actions"] == []
        assert result["checkpoint_id"] == checkpoint_id
        assert result["window_key"] == KEY_A
        assert sample.read_calls == 6, "double Sway sampling must read 3 IPC types twice"
        assert not hasattr(scope, "main")
        assert not hasattr(scope, "execute")
        assert not hasattr(scope, "authorize")

        # Scope A deliberately does not try to map the two same-app Brave
        # windows using their same process, title, app_id or focus. Only one
        # selected CURRENT surface may be paired to one saved geometry target.
        second_selection = copy.deepcopy(selection)
        second_selection.update(
            selection_id=str(uuid.uuid4()),
            surface_lifetime_id=LIFE_B,
            live_con_id=111, window_key=KEY_B,
            before_rect=current_b, target_rect=target_b)
        second_request = dict(request, window_key=KEY_B, live_con_id=111)
        result_b = call(req=second_request, token=second_selection)
        assert result_b["status"] == "fixture_consistent_only"
        assert result_b["restore_allowed"] is False

        def changed(token=None, observed_now=None, req=None, **fields):
            t = copy.deepcopy(selection if token is None else token)
            t.update(fields)
            denies(lambda: call(token=t, obs=observed_now, req=req))

        # The purported proof is still untrusted. Even internally
        # contradictory inputs must be rejected before any potential future
        # compositor/consent admission design.
        changed(schema=PAIR_SCHEMA)
        changed(audience=BRAVE_AUDIENCE)
        changed(browser_window_ref=str(uuid.uuid4()))
        changed(selection_id="non-uuid")
        changed(compositor_epoch=str(uuid.uuid4()))
        changed(surface_lifetime_id=str(uuid.uuid4()))
        changed(surface_generation=2)
        changed(surface_generation=True)
        changed(live_con_id=111)
        changed(live_con_id=True)
        changed(app_id="kitty")
        changed(output="HDMI-A-1")
        changed(workspace="2")
        changed(floating=False)
        changed(fullscreen_mode=1)
        changed(fullscreen_mode=True)
        changed(before_rect=rect(222, 250, 480, 320))
        changed(target_rect=rect(101, 80, 620, 410))
        changed(checkpoint_id=str(uuid.uuid4()))
        changed(window_key=KEY_B)
        changed(seat_id="seat1")
        changed(session_id=str(uuid.uuid4()))
        changed(challenge_sha256="a" * 64)
        changed(issued_ms=NOW+5000)
        changed(expires_ms=NOW+5001)
        changed(expires_ms=NOW+50001)
        changed(issued_ms=True)

        denies(lambda: call(time=NOW-1))
        denies(lambda: call(time=NOW+4000))
        denies(lambda: call(session=str(uuid.uuid4())))
        denies(lambda: call(seat="seat1"))
        denies(lambda: call(challenge="a" * 64))
        denies(lambda: call(req={**request, "window_key": KEY_B}))
        denies(lambda: call(req={**request, "live_con_id": 111}))
        denies(lambda: call(req={**request, "operator_selected": True}))
        denies(lambda: call(obs=[]))
        denies(lambda: call(obs=observed+observed[:1]))
        denies(lambda: call(obs=observed[1:]))
        denies(lambda: call(obs={}))
        denies(lambda: call(obs=observed*300))

        duplicate_lifetime = copy.deepcopy(observed)
        duplicate_lifetime[1]["surface_lifetime_id"] = LIFE_A
        denies(lambda: call(obs=duplicate_lifetime))
        stale_generation = copy.deepcopy(observed)
        stale_generation[0]["surface_generation"] = 2
        denies(lambda: call(obs=stale_generation))
        swapped_con_id = copy.deepcopy(observed)
        swapped_con_id[0]["live_con_id"] = 111
        swapped_con_id[1]["live_con_id"] = 110
        denies(lambda: call(obs=swapped_con_id))
        old_epoch = copy.deepcopy(observed)
        old_epoch[0]["compositor_epoch"] = str(uuid.uuid4())
        denies(lambda: call(obs=old_epoch))
        shifted_rect = copy.deepcopy(observed)
        shifted_rect[0]["rect"]["x"] += 1
        denies(lambda: call(obs=shifted_rect))
        shifted_output = copy.deepcopy(observed)
        shifted_output[0]["output"] = "HDMI-A-1"
        denies(lambda: call(obs=shifted_output))
        shifted_seat = copy.deepcopy(observed)
        shifted_seat[0]["workspace"] = "2"
        denies(lambda: call(obs=shifted_seat))
        not_floating = copy.deepcopy(observed)
        not_floating[0]["floating"] = False
        denies(lambda: call(obs=not_floating))

        # Any change in fresh double Sway sampling must refuse: old approved
        # geometry and compositor state are never sufficient for dispatch.
        moved_sway = FakeReadOnlySway()
        moved_sway.state[2]["nodes"][0]["nodes"][0]["floating_nodes"][0][
            "rect"]["x"] += 1
        denies(lambda: call(reader=moved_sway))

        out = json.dumps(result, sort_keys=True)
        for secret in ("PRIVATE BRAVE TITLE", "123456", "password", "tab_url",
                       "browser_window_ref", LIFE_A, EPOCH, "pid"):
            assert secret not in out
        assert "restore_allowed" in out and '"restore_allowed": false' in out
finally:
    if old_xdg is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = old_xdg

print("TIMEW SCOPE A // DENY-ONLY SELECTED LIVE SURFACE CONTRACT + HOSTILE FIXTURES PASS")
