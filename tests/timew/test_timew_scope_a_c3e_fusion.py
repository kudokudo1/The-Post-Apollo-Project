#!/usr/bin/env python3
"""TimeW-only C3e purpose proof + selected window geometry continuity CI."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import uuid
from unittest.mock import patch

if (sys.platform != "linux" or os.environ.get("CI") != "true"
        or os.environ.get("GITHUB_ACTIONS") != "true"):
    raise SystemExit("TIMEW_C3E_FUSION_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/timew"))
sys.path.insert(0, str(ROOT / "tests/connections/c3e_integration"))
sys.path.insert(0, str(ROOT / "services/time"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import TimeWScopeAC3eFusionPreflight as Fusion
import ConnectionsPurposeBoundEvidencePreflight as C3e
import MachineV2SelectedSurfaceReview as ScopeA
import MachineV2SurfaceContinuityReview as Continuity
from MachineCaptureSaveV2 import _legacy_from_geometry
from MachineCheckpointStore import load as load_legacy
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import save_pair, load_geometry

def uid():
    return str(uuid.uuid4())

def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}

def leaf(cid, box, app="brave", floating=True, fullscreen=0):
    return {
        "type": "floating_con" if floating else "con",
        "id": cid, "app_id": app, "rect": box,
        "layout": "none", "floating": "user_on" if floating else "auto_off",
        "percent": None, "fullscreen_mode": fullscreen,
        "nodes": [], "floating_nodes": [], "pid": 5599,
        "name": "PRIVATE_TAB_TITLE_MUST_NOT_LEAK",
    }

def frame(saved):
    a, b = ((rect(90, 40, 600, 420), rect(960, 70, 390, 420))
            if saved else
            (rect(230, 150, 450, 320), rect(950, 260, 520, 330)))
    ids = (11, 12) if saved else (34, 35)
    out = [{"name": "DP-3", "active": True, "rect": rect(0, 0, 1920, 1080),
            "scale": 1.0, "transform": "normal"}]
    ws = [{"name": "1", "output": "DP-3"}]
    tiled = [] if saved else [
        leaf(36, rect(10, 600, 650, 350), "kitty", False),
        leaf(37, rect(0, 0, 1920, 1080), "obsidian", False, 1),
    ]
    tree = {"type": "root", "nodes": [
        {"type": "output", "name": "DP-3", "nodes": [
            {"type": "workspace", "name": "1", "layout": "splith",
             "rect": rect(0, 0, 1920, 1080),
             "nodes": tiled, "floating_nodes": [leaf(ids[0], a), leaf(ids[1], b)]}
        ]}
    ]}
    return out, ws, tree

class FakeSway:
    def __init__(self):
        self.state = frame(saved=False)
        self.calls = 0

    def read(self, args, **kw):
        assert args[:3] == ["swaymsg", "-r", "-t"]
        assert kw == {"check": True, "capture_output": True,
                      "timeout": 3, "shell": False}
        idx = {"get_outputs": 0, "get_workspaces": 1, "get_tree": 2}[args[3]]
        self.calls += 1
        return SimpleNamespace(stdout=json.dumps(self.state[idx]).encode(),
                               returncode=0)

def obs(cid, lifetime, box, app="brave", floating=True, fullscreen=0):
    return {
        "live_con_id": cid, "compositor_epoch": epoch,
        "surface_lifetime_id": lifetime, "surface_generation": 1,
        "app_id": app, "output": "DP-3", "workspace": "1",
        "rect": copy.deepcopy(box), "floating": floating,
        "fullscreen_mode": fullscreen,
    }

def fingerprint(private):
    return hashlib.sha256(private.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw)).hexdigest()

refusals = 0

def refuses(fn):
    global refusals
    try:
        fn()
    except Fusion.FusionHold:
        refusals += 1
        return
    raise AssertionError("Expected CI-only fusion to refuse altered source")

previous_xdg = os.environ.get("XDG_DATA_HOME")
try:
    with tempfile.TemporaryDirectory(prefix="timew-c3e-fusion-") as root:
        os.environ["XDG_DATA_HOME"] = root
        key_a, key_b = uid(), uid()
        saved = project_geometry(*frame(saved=True),
                                 window_keys={11: key_a, 12: key_b})
        v1 = _legacy_from_geometry(saved, label="Source-bound fixture",
                                   captured_at="2026-11-22T01:00:00+00:00")
        checkpoint = save_pair(v1, saved)["checkpoint"]["id"]
        assert load_geometry(checkpoint)["status"] == "loaded"
        current = frame(saved=False)
        original = current[2]["nodes"][0]["nodes"][0]["floating_nodes"][0]["rect"]
        target = saved["windows"][0]["rect"]
        later = dict(original, width=target["width"], height=target["height"])
        epoch, life_a, life_b, life_c, life_d = uid(), uid(), uid(), uid(), uid()
        seat, session, when, challenge = "seat0", uid(), 1763800000000, b"T" * 32
        request = {"checkpoint_id": checkpoint, "window_key": key_a,
                   "live_con_id": 34}
        selection = {
            "schema": ScopeA.SCHEMA, "audience": ScopeA.AUDIENCE,
            "challenge_sha256": hashlib.sha256(challenge).hexdigest(),
            "selection_id": uid(), "compositor_epoch": epoch,
            "surface_lifetime_id": life_a, "surface_generation": 1,
            "live_con_id": 34, "app_id": "brave",
            "output": "DP-3", "workspace": "1",
            "floating": True, "fullscreen_mode": 0,
            "before_rect": original, "target_rect": target,
            "checkpoint_id": checkpoint, "window_key": key_a,
            "seat_id": seat, "session_id": session,
            "issued_ms": when, "expires_ms": when + 2200,
        }
        def observed(chosen):
            return [
                obs(34, life_a, chosen), # selected current window
                obs(35, life_b, rect(950, 260, 520, 330)),
                obs(36, life_c, rect(10, 600, 650, 350), "kitty", False),
                obs(37, life_d, rect(0, 0, 1920, 1080), "obsidian", False, 1),
            ]
        initial = observed(original)
        phases = [
            {"phase": "before_resize", "now_ms": when+100,
             "observed_surfaces": observed(original)},
            {"phase": "after_resize", "now_ms": when+200,
             "observed_surfaces": observed(later)},
            {"phase": "after_move", "now_ms": when+300,
             "observed_surfaces": observed(target)},
        ]
        good_key, hospital_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        source = C3e.TimeW.make_packet_ci_only(
            selection=selection, challenge=challenge, now_ms=when)
        proof = {
            "schema": C3e.SCHEMA,
            "purpose": C3e.TIMEW_PURPOSE,
            "audience": C3e.TIMEW_AUDIENCE,
            "sourceSha256": hashlib.sha256(source).hexdigest(),
            "challengeSha256": hashlib.sha256(challenge).hexdigest(),
            "signerKeySha256": fingerprint(good_key),
            "hostId": "ci-untrusted-host",
            "releaseEpoch": 3, "releaseSequence": 5,
            "issuedMs": when, "expiresMs": when+1000,
        }
        signed_raw = C3e._canonical(proof)
        signature = good_key.sign(C3e.TIMEW_DOMAIN + signed_raw)
        pins = {
            "independently_pinned_signer_key": good_key.public_key(),
            "separately_expected_signer_sha256": fingerprint(good_key),
            "separately_expected_other_role_key_sha256": fingerprint(hospital_key),
            "revoked_signer_sha256": (),
            "expected_host_id": "ci-untrusted-host",
            "minimum_release_epoch": 3,
            "minimum_release_sequence": 5,
        }
        sway = FakeSway()

        def call(**different):
            args = {
                "request": request, "selection": selection,
                "observed_surfaces": initial, "samples": phases,
                "challenge": challenge, "signed_proof_raw": signed_raw,
                "signature": signature, **pins,
                "expected_session_id": session, "expected_seat_id": seat,
                "now_ms": when, "read_runner": sway.read,
                "legacy_reader": load_legacy, "geometry_reader": load_geometry,
            }
            args.update(different)
            return Fusion.inspect_ci_only(**args)

        result = call()
        assert result["kind"] == Fusion.KIND
        assert result["status"] == "SIGNED_TEST_SOURCE_AND_GEOMETRY_CONSISTENT_NO_AUTHORITY"
        assert result["proof_scope"] == ScopeA.AUDIENCE
        assert result["source_is_ci_only"] is True
        assert result["all_evidence_is_caller_supplied"] is True
        for name, value in Fusion.DENIED.items():
            assert result[name] == value, (name, result[name])
        assert result["safe_actions"] == []
        assert sway.calls == 6
        assert call() == result, "replayed signed CI fixture still never authorizes"
        # Inventory order is not identity; exact values and lifetime are.
        reordered = copy.deepcopy(phases)
        reordered[0]["observed_surfaces"].reverse()
        assert call(samples=reordered) == result
        # Boundary: the last hypothetical operation may finish just BEFORE
        # the signed fixture expiry, not at or after expiry.
        just_before_expiry = copy.deepcopy(phases)
        just_before_expiry[-1]["now_ms"] = when + 999
        assert call(samples=just_before_expiry) == result

        def changed_sel(**fields):
            s = copy.deepcopy(selection)
            s.update(fields)
            refuses(lambda: call(selection=s))

        def changed_phase(index, surface=0, **fields):
            samples = copy.deepcopy(phases)
            samples[index]["observed_surfaces"][surface].update(fields)
            refuses(lambda: call(samples=samples))

        changed_sel(browser_window_ref=uid())
        changed_sel(schema=C3e.SCHEMA)
        changed_sel(audience=C3e.HOSPITAL_AUDIENCE)
        changed_sel(checkpoint_id=uid())
        changed_sel(window_key=key_b)
        changed_sel(live_con_id=35)
        changed_sel(surface_lifetime_id=uid())
        changed_sel(surface_generation=2)
        changed_sel(compositor_epoch=uid())
        changed_sel(challenge_sha256=hashlib.sha256(b"S"*32).hexdigest())
        changed_sel(seat_id="seat1")
        changed_sel(session_id=uid())
        changed_sel(output="DP-2")
        changed_sel(before_rect=rect(231, 150, 450, 320))
        changed_sel(target_rect=rect(91, 40, 600, 420))
        changed_sel(floating=False)
        changed_sel(fullscreen_mode=1)

        refuses(lambda: call(challenge=b"S"*32))
        refuses(lambda: call(challenge=b"short"))
        refuses(lambda: call(request={**request, "window_key": key_b}))
        refuses(lambda: call(expected_seat_id="seat1"))
        refuses(lambda: call(expected_session_id=uid()))
        refuses(lambda: call(signed_proof_raw=b"{}"))
        refuses(lambda: call(signature=b"\x00"*64))
        refuses(lambda: call(signature=hospital_key.sign(
            C3e.HOSPITAL_DOMAIN + signed_raw)))
        refuses(lambda: call(separately_expected_signer_sha256=fingerprint(hospital_key)))
        refuses(lambda: call(separately_expected_other_role_key_sha256=fingerprint(good_key)))
        refuses(lambda: call(revoked_signer_sha256=(fingerprint(good_key),)))
        refuses(lambda: call(minimum_release_epoch=4))
        refuses(lambda: call(minimum_release_sequence=6))
        refuses(lambda: call(expected_host_id="ci-other-host"))
        refuses(lambda: call(now_ms=when+2200))
        refuses(lambda: call(now_ms=when-1))
        # Initial selected-surface preflight must precede the first sample.
        # Previously the separate validators allowed a first phase earlier
        # than the same call's preflight instant.
        refuses(lambda: call(now_ms=when+150))
        after_signed_expiry = copy.deepcopy(phases)
        after_signed_expiry[-1]["now_ms"] = when + 1000
        refuses(lambda: call(samples=after_signed_expiry))
        after_signed_expiry[-1]["now_ms"] = when + 1500
        refuses(lambda: call(samples=after_signed_expiry))
        for i in range(3):
            changed_phase(i, surface_lifetime_id=uid())
            changed_phase(i, surface_generation=2)
            changed_phase(i, compositor_epoch=uid())
            changed_phase(i, output="DP-2")
            changed_phase(i, workspace="2")
            changed_phase(i, live_con_id=35)
            changed_phase(i, floating=False)
        changed_phase(1, rect=original)
        changed_phase(1, rect=target)
        changed_phase(2, rect=later)
        changed_phase(2, surface=1, rect=rect(951,260,520,330))
        changed_phase(0, surface=2, surface_lifetime_id=life_a)
        for idx, name in enumerate(("after_move", "before_resize", "after_resize")):
            copy_phases = copy.deepcopy(phases)
            copy_phases[idx]["phase"] = name
            refuses(lambda s=copy_phases: call(samples=s))
        for invalid in ([], phases[:2], {}, "bad"):
            refuses(lambda s=invalid: call(samples=s))
        invalid = copy.deepcopy(initial)
        invalid[1]["live_con_id"] = 34
        refuses(lambda: call(observed_surfaces=invalid))
        invalid = copy.deepcopy(initial)
        invalid[0]["rect"]["x"] += 1
        refuses(lambda: call(observed_surfaces=invalid))
        # Existing selected preflight checks the chosen window, not every
        # unselected surface. A *stable but different* three-phase inventory
        # must no longer be accepted as the same initial desktop observation.
        initial_other = copy.deepcopy(initial)
        initial_other[1]["rect"]["x"] += 1
        refuses(lambda: call(observed_surfaces=initial_other))
        phases_other = copy.deepcopy(phases)
        for snapshot in phases_other:
            snapshot["observed_surfaces"][1]["rect"]["x"] += 1
        refuses(lambda: call(samples=phases_other))

        # A mathematically valid signature with a shorter fixture lease
        # cannot cover an after-move stage beyond its own expiry.
        short_proof = copy.deepcopy(proof)
        short_proof["expiresMs"] = when + 250
        short_raw = C3e._canonical(short_proof)
        refuses(lambda: call(signed_proof_raw=short_raw,
                             signature=good_key.sign(C3e.TIMEW_DOMAIN + short_raw)))
        altered = copy.deepcopy(proof)
        altered["purpose"] = C3e.HOSPITAL_PURPOSE
        proof_raw = C3e._canonical(altered)
        refuses(lambda: call(signed_proof_raw=proof_raw,
                             signature=good_key.sign(C3e.TIMEW_DOMAIN + proof_raw)))
        altered = copy.deepcopy(proof)
        altered["sourceSha256"] = "b"*64
        proof_raw = C3e._canonical(altered)
        refuses(lambda: call(signed_proof_raw=proof_raw,
                             signature=good_key.sign(C3e.TIMEW_DOMAIN + proof_raw)))

        # An injected C3e result claiming authority must never be accepted
        # even when the geometry fixture remains structurally consistent.
        original_c3e = C3e.inspect_timew_scope_a_ci_only
        def forged_c3e(**kwargs):
            good = original_c3e(**kwargs)
            return dict(good, nativeTimeWGeometryAllowed=True)
        with patch.object(C3e, "inspect_timew_scope_a_ci_only", forged_c3e):
            refuses(call)

        # Return objects are fresh; callers cannot mutate shared action data.
        result["safe_actions"].append("forged-restore")
        assert call()["safe_actions"] == []
        encoded = json.dumps(call(), sort_keys=True)
        for private in ("PRIVATE_TAB_TITLE", "ciSignerFingerprint", life_a,
                        epoch, "browser_window_ref", "pid", "tab_url"):
            assert private not in encoded

finally:
    if previous_xdg is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = previous_xdg

print("TIMEW C3E SOURCE + CONTINUITY FUSION //", refusals,
      "hostile denials, all production authority false, PASS")
