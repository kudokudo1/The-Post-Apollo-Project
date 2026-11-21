#!/usr/bin/env python3
"""Scope A continuity across two *hypothetical* commands, CI fixture only."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
import MachineV2SurfaceContinuityReview as continuity
from MachineV2SelectedSurfaceReview import AUDIENCE, SCHEMA, ScopeARefused
from MachineV2PairConsent import AUDIENCE as BRAVE_AUDIENCE, PAIR_SCHEMA

def uid():
    return str(uuid.uuid4())

SESSION, SEAT, EPOCH = uid(), "seat0", uid()
SELECT, LIFE_A, LIFE_B, LIFE_C, LIFE_D = uid(), uid(), uid(), uid(), uid()
CKPT, WINDOW, CHALLENGE = uid(), uid(), "a" * 64

def rect(x, y, width, height):
    return {"x": x, "y": y, "width": width, "height": height}

BEFORE = rect(110, 120, 420, 310)
RESIZED = rect(110, 120, 680, 530)
TARGET = rect(340, 190, 680, 530)
selection = {
    "schema": SCHEMA, "audience": AUDIENCE,
    "challenge_sha256": CHALLENGE,
    "selection_id": SELECT, "compositor_epoch": EPOCH,
    "surface_lifetime_id": LIFE_A, "surface_generation": 1,
    "live_con_id": 42, "app_id": "brave",
    "output": "DP-3", "workspace": "1",
    "floating": True, "fullscreen_mode": 0,
    "before_rect": BEFORE, "target_rect": TARGET,
    "checkpoint_id": CKPT, "window_key": WINDOW,
    "seat_id": SEAT, "session_id": SESSION,
    "issued_ms": 1000, "expires_ms": 4500,
}

def window(cid, life, rect_value, *, app="brave", floating=True,
           fullscreen=0, generation=1):
    return {
        "live_con_id": cid, "compositor_epoch": EPOCH,
        "surface_lifetime_id": life, "surface_generation": generation,
        "app_id": app, "output": "DP-3", "workspace": "1",
        "rect": copy.deepcopy(rect_value),
        "floating": floating, "fullscreen_mode": fullscreen,
    }

def sample(phase, when, chosen):
    return {
        "phase": phase, "now_ms": when,
        "observed_surfaces": [
            window(42, LIFE_A, chosen),  # selected current Brave surface
            window(43, LIFE_B, rect(900, 100, 430, 320)),  # second same-app
            window(44, LIFE_C, rect(100, 650, 750, 380),
                   app="kitty", floating=False),
            window(45, LIFE_D, rect(0, 0, 1920, 1080),
                   app="obsidian", floating=False, fullscreen=1),
        ],
    }

phases = [
    sample("before_resize", 1100, BEFORE),
    sample("after_resize", 1700, RESIZED),
    sample("after_move", 2100, TARGET),
]

def inspect(*, chosen=None, stages=None, session=SESSION, seat=SEAT,
            challenge=CHALLENGE):
    return continuity.inspect_fixture(
        selection=selection if chosen is None else chosen,
        samples=phases if stages is None else stages,
        expected_session_id=session,
        expected_seat_id=seat,
        expected_challenge_sha256=challenge,
    )

counter = 0

def denies(fn):
    global counter
    try:
        fn()
    except ScopeARefused:
        counter += 1
        return
    raise AssertionError("Untrusted altered selected-surface fixture should refuse")

result = inspect()
assert result["kind"] == continuity.KIND
assert result["status"] == "fixture_continuity_only"
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
assert result["no_automatic_retry"] is True
assert result["requires_native_recheck_before_each_command"] is True

# A read-only static fixture has NO replay defense or permission. Repeating
# it cannot imply safe retry, consent consumption or native verification.
assert inspect() == result

def altered_selection(**kwargs):
    value = copy.deepcopy(selection)
    value.update(kwargs)
    denies(lambda: inspect(chosen=value))

def altered_phase(index, *, surface=0, **changes):
    value = copy.deepcopy(phases)
    value[index]["observed_surfaces"][surface].update(changes)
    denies(lambda: inspect(stages=value))

# Never accept the Brave PAIR v1 schema/audience for current-surface geometry.
altered_selection(schema=PAIR_SCHEMA)
altered_selection(audience=BRAVE_AUDIENCE)
altered_selection(browser_window_ref=uid())
altered_selection(challenge_sha256="b" * 64)
altered_selection(compositor_epoch=uid())
altered_selection(surface_lifetime_id=uid())
altered_selection(surface_generation=2)
altered_selection(surface_generation=True)
altered_selection(live_con_id=43)
altered_selection(live_con_id=True)
altered_selection(app_id="kitty")
altered_selection(output="HDMI-A-1")
altered_selection(workspace="3")
altered_selection(floating=False)
altered_selection(fullscreen_mode=1)
altered_selection(fullscreen_mode=True)
altered_selection(seat_id="seat1")
altered_selection(session_id=uid())
altered_selection(selection_id="not-uuid")
altered_selection(checkpoint_id="not-uuid")
altered_selection(before_rect=rect(112, 120, 420, 310))
altered_selection(target_rect=rect(341, 190, 680, 530))
altered_selection(issued_ms=5000)
altered_selection(expires_ms=5001)
altered_selection(expires_ms=50000)
altered_selection(issued_ms=True)

denies(lambda: inspect(session=uid()))
denies(lambda: inspect(seat="seat1"))
denies(lambda: inspect(challenge="b" * 64))
denies(lambda: inspect(challenge=True))
denies(lambda: inspect(stages=[]))
denies(lambda: inspect(stages=phases[:2]))
denies(lambda: inspect(stages=phases * 2))
denies(lambda: inspect(stages={}))
denies(lambda: inspect(stages="before_resize"))

# Same geometry, same con_id but a destroyed/recreated native surface or
# replaced compositor epoch MUST refuse. No focus/title/app/PID fallback.
for index in range(3):
    altered_phase(index, surface_lifetime_id=uid())
    altered_phase(index, surface_generation=2)
    altered_phase(index, surface_generation=True)
    altered_phase(index, compositor_epoch=uid())
    altered_phase(index, live_con_id=43)
    altered_phase(index, app_id="kitty")
    altered_phase(index, output="HDMI-A-1")
    altered_phase(index, workspace="2")
    altered_phase(index, floating=False)
    altered_phase(index, fullscreen_mode=1)
    altered_phase(index, fullscreen_mode=True)

# Unexpected resize, early move, incomplete geometry and positional drift.
altered_phase(0, rect=RESIZED)
altered_phase(1, rect=BEFORE)
altered_phase(1, rect=TARGET)
altered_phase(1, rect=rect(110, 120, 679, 530))
altered_phase(1, rect=rect(111, 120, 680, 530))
altered_phase(2, rect=BEFORE)
altered_phase(2, rect=RESIZED)
altered_phase(2, rect=rect(341, 190, 680, 530))

# Other app windows may be tiled and fullscreen but cannot mutate, vanish,
# become duplicates or be silently replaced during this strict model.
altered_phase(1, surface=1, surface_lifetime_id=uid())
altered_phase(1, surface=2, rect=rect(101, 650, 750, 380))
altered_phase(2, surface=3, fullscreen_mode=0)
altered_phase(0, surface=3, fullscreen_mode=True)
altered_phase(2, surface=1, live_con_id=42)
altered_phase(2, surface=1, surface_lifetime_id=LIFE_A)
altered_phase(1, surface=2, compositor_epoch=uid())

for index in range(3):
    changed = copy.deepcopy(phases)
    changed[index]["observed_surfaces"].pop(0)
    denies(lambda c=changed: inspect(stages=c))
    changed = copy.deepcopy(phases)
    changed[index]["observed_surfaces"].append(
        copy.deepcopy(changed[index]["observed_surfaces"][0]))
    denies(lambda c=changed: inspect(stages=c))
    changed = copy.deepcopy(phases)
    changed[index]["observed_surfaces"].append(
        {"unknown": "outside frozen schema"})
    denies(lambda c=changed: inspect(stages=c))
    changed = copy.deepcopy(phases)
    changed[index]["observed_surfaces"] = {}
    denies(lambda c=changed: inspect(stages=c))

# Exact stage names/order/clock monotonicity and expiry checked even when
# every geometric field matches.
for index, other in ((0, "after_resize"), (1, "after_move"),
                     (2, "before_resize")):
    changed = copy.deepcopy(phases)
    changed[index]["phase"] = other
    denies(lambda c=changed: inspect(stages=c))
for index, time in ((0, 999), (0, True), (1, 1000), (1, 4500),
                    (2, 1700), (2, 4500), (2, 5000)):
    changed = copy.deepcopy(phases)
    changed[index]["now_ms"] = time
    if index == 1 and time == 1000:  # backwards clock
        pass
    denies(lambda c=changed: inspect(stages=c))

result["safe_actions"].append("forged-after-return")
assert inspect()["safe_actions"] == [], "review output must be fresh and non-shared"

encoded = json.dumps(inspect(), sort_keys=True)
for private in (LIFE_A, EPOCH, CHALLENGE, "pid", "browser_window_ref",
                "private_title", "tab_url", "source_signer_key"):
    assert private not in encoded, "review must not return untrusted source identity"
assert '"restore_allowed": false' in encoded
assert '"production_authorized": false' in encoded

print("TIMEW SCOPE A CONTINUITY //", counter,
      "hostile fixture refusals, NO authority, PASS")
