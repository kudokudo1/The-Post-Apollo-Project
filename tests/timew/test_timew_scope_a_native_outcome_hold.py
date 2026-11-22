#!/usr/bin/env python3
"""TimeW native outcome contract rehearsal: no commands, no issuer, no C5."""
from __future__ import annotations

import copy
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

if (sys.platform != "linux" or os.environ.get("CI") != "true"
        or os.environ.get("GITHUB_ACTIONS") != "true"):
    raise SystemExit("TIMEW_SCOPE_A_OUTCOME_FIXTURE_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
sys.path.insert(0, str(ROOT / "tests/timew"))
from MachineV2GeometryJournal import GeometryJournal, DB_NAME
import TimeWScopeAOutcomeHoldPreflight as H

def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}

before = rect(100, 200, 401, 300)
target = rect(300, 80, 600, 401)
expected_hint = rect(1, 150, 600, 401)
# C signed /2 truncates toward zero. Odd positive delta of 199
# shifts left by 99 rather than Python's negative floor behavior.
assert H.centered_pending_hint(before, width=600, height=401) == expected_hint
# Odd negative deltas must truncate toward zero too (not Python // floor).
assert H.centered_pending_hint(
    rect(100, 200, 601, 501), width=500, height=400) == rect(150,250,500,400)
assert H.centered_pending_hint(before, width=401, height=300) == before
assert H.centered_pending_hint(
    rect(-30, 0, 101, 101), width=100, height=100) == rect(-30,0,100,100)

checkpoint = str(uuid.uuid4())
window_key = str(uuid.uuid5(uuid.UUID(checkpoint), "brave-saved-window"))
surface = {
    "compositor_epoch": str(uuid.uuid4()),
    "surface_lifetime_id": str(uuid.uuid4()),
    "surface_generation": 4,
    "live_con_id": 407,
    "seat_id": "seat0",
    "session_id": str(uuid.uuid4()),
    "output": "DP-3",
    "workspace": "1",
}
summary = {
    "checkpoint_id": checkpoint, "window_key": window_key,
    "app_id": "brave", "live_con_id": 407,
    "before_rect": before, "target_rect": target,
}
denied = 0
def refuses(fn):
    global denied
    try:
        fn()
    except H.FixtureHold:
        denied += 1
        return
    raise AssertionError("Expected malformed fixture to be refused")

with tempfile.TemporaryDirectory(prefix="timew-scopea-outcome-") as temp:
    db = Path(temp) / "post-apollo" / "machine" / DB_NAME
    journal = GeometryJournal(db)
    op = journal.begin(summary)
    prepared = journal.get(op)
    assert prepared["phase"] == "prepared"
    assert prepared["manual_review_required"] is True

    def inspect(view, **changes):
        args = {
            "journal_view": view,
            "c5_spend_claim": "absent",
            "resize_receipt_claim": "not_seen",
            "move_receipt_claim": "not_seen",
            "post_resize": None,
            "final_observed": None,
            "selected_identity": surface,
            "observed_identity": None,
            "source_claim_active": True,
        }
        args.update(changes)
        result = H.inspect_ci_only(**args)
        assert result["kind"] == H.KIND
        for name in (
            "protected_source_verified", "protected_c5_spend_verified",
            "native_receipts_verified", "restore_allowed",
            "production_authorized", "automatic_retry_allowed",
            "automatic_undo_allowed", "native_geometry_dispatch_allowed",
        ):
            assert result[name] is False, (name, result[name])
        assert result["safe_actions"] == []
        assert result["manual_review_required"] is True
        assert result["read_only"] is True
        assert result["local_journal_is_not_protected_c5_spend"] is True
        return result

    assert inspect(prepared)["status"] == "UNTRUSTED_PRE_ACTION_HOLD"
    # C5's protected SPENT history is independently held, so loss of local
    # DISPATCHING cannot be interpreted as unspent, or authorize any retry.
    assert inspect(prepared, c5_spend_claim="spent")["status"] == "UNKNOWN_HOLD"
    assert inspect(prepared, c5_spend_claim="unknown")["status"] == "UNKNOWN_HOLD"
    assert inspect(prepared, c5_spend_claim="spent",
                   resize_receipt_claim="claimed_ok")["status"] == "UNKNOWN_HOLD"

    # Reopen the actual SQLite journal with an independent connection.
    restarted = GeometryJournal(db)
    assert restarted.get(op)["phase"] == "prepared"
    assert inspect(restarted.get(op), c5_spend_claim="spent")["status"] == "UNKNOWN_HOLD"
    assert len(restarted.pending()) == 1
    assert db.exists()

    journal.dispatching(op)
    dispatching = GeometryJournal(db).get(op)
    assert dispatching["phase"] == "dispatching"
    assert dispatching["production_restore_allowed"] is False
    assert inspect(dispatching)["status"] == "UNKNOWN_HOLD"

    complete_claims = {
        "c5_spend_claim": "spent",
        "resize_receipt_claim": "claimed_ok",
        "move_receipt_claim": "claimed_ok",
        "post_resize": expected_hint,
        "final_observed": target,
        "observed_identity": surface,
        "source_claim_active": True,
    }
    consistent = inspect(dispatching, **complete_claims)
    assert consistent["status"] == "COMPLETE_UNTRUSTED_FIXTURE_ONLY"
    assert consistent["centered_resize_hint_matches_observation"] is True
    assert consistent["same_surface_claims_match"] is True

    # Production must use actual compositor observation, not a center
    # formula. Simulated post-resize x/y may differ, while size is correct.
    shifted = dict(complete_claims, post_resize=rect(2, 151, 600, 401))
    mismatch = inspect(dispatching, **shifted)
    assert mismatch["status"] == "COMPLETE_UNTRUSTED_FIXTURE_ONLY"
    assert mismatch["centered_resize_hint_matches_observation"] is False
    assert mismatch["restore_allowed"] is False

    # Every combination of replayable C5, local journal and claimed receipts
    # must be permanently non-authorizing. The only "complete" label is
    # explicitly tagged UNTRUSTED_FIXTURE_ONLY.
    matrix_cases = 0
    for c5, resize_receipt, move_receipt in itertools.product(
            sorted(H.C5_CLAIMS), sorted(H.RECEIPT_CLAIMS),
            sorted(H.RECEIPT_CLAIMS)):
        for view in (prepared, dispatching):
            out = inspect(view, **dict(complete_claims,
                c5_spend_claim=c5, resize_receipt_claim=resize_receipt,
                move_receipt_claim=move_receipt))
            assert out["safe_actions"] == []
            assert out["automatic_retry_allowed"] is False
            matrix_cases += 1
    assert matrix_cases == 128

    for broken in (
        dict(complete_claims, c5_spend_claim="unknown"),
        dict(complete_claims, c5_spend_claim="absent"),
        dict(complete_claims, c5_spend_claim="refused"),
        dict(complete_claims, resize_receipt_claim="lost"),
        dict(complete_claims, move_receipt_claim="lost"),
        dict(complete_claims, move_receipt_claim="ambiguous"),
        dict(complete_claims, final_observed=None),
        dict(complete_claims, final_observed=expected_hint),
        dict(complete_claims, post_resize=None),
        dict(complete_claims, post_resize=rect(0, 150, 599, 401)),
        dict(complete_claims, source_claim_active=False),
        dict(complete_claims, observed_identity=None),
        dict(complete_claims, observed_identity={
            **surface, "surface_lifetime_id": str(uuid.uuid4())}),
        dict(complete_claims, observed_identity={
            **surface, "compositor_epoch": str(uuid.uuid4())}),
        dict(complete_claims, observed_identity={
            **surface, "seat_id": "seat1"}),
    ):
        assert inspect(dispatching, **broken)["status"] == "UNKNOWN_HOLD"

    # Local journal "verified_fixture_placement" is not native C5/source
    # proof. A finished disposable journal cannot upgrade this result.
    journal.finish(op, "verified_fixture_placement")
    terminal = GeometryJournal(db).get(op)
    assert terminal["phase"] == "verified_fixture_placement"
    assert inspect(terminal, **complete_claims)["status"] == "UNKNOWN_HOLD"
    assert GeometryJournal(db).pending() == []

    # Invalid source claims, mismatched con id, positive native authority
    # forged into a local row, missing/unrecognized phases, unknown inputs.
    for key, bad in (
        ("c5_spend_claim", "approved"),
        ("c5_spend_claim", True),
        ("resize_receipt_claim", "success"),
        ("move_receipt_claim", "success"),
        ("source_claim_active", "true"),
        ("selected_identity", {**surface, "live_con_id": 408}),
        ("selected_identity", {**surface, "surface_generation": True}),
        ("selected_identity", {**surface, "app_id": "brave"}),
        ("post_resize", {"x": 1}),
        ("final_observed", rect(0, 0, -1, 401)),
    ):
        refuses(lambda k=key,v=bad: inspect(dispatching, **dict(complete_claims, **{k:v})))
    for forged in (
        {"production_restore_allowed": True},
        {"automatic_retry_allowed": True},
        {"automatic_undo_allowed": True},
        {"persistent_identity_verified": True},
        {"phase": "new"},
        {"summary": {**summary, "target_rect": rect(300,80,0,401)}},
    ):
        refuses(lambda v=forged: inspect({**dispatching, **v}, **complete_claims))
    refuses(lambda: H.run_native_restore())

    # No authority, operation id, private window identity or raw surface data
    # is ever emitted. Results cannot be turned into a shared mutable grant.
    out = inspect(dispatching, **complete_claims)
    encoded = json.dumps(out, sort_keys=True)
    for secret in (checkpoint, window_key, surface["surface_lifetime_id"],
                   surface["compositor_epoch"], "PRIVATE_TAB_TITLE", "pid",
                   "browser_window_ref", "grant_id"):
        assert secret not in encoded, secret
    out["safe_actions"].append("forged-native-resize")
    assert inspect(dispatching, **complete_claims)["safe_actions"] == []

print("TIMEW SCOPE A NATIVE OUTCOME MATRIX //", matrix_cases,
      "C5/receipt/journal combinations +", denied,
      "malformed refusals, NO authority, PASS")
