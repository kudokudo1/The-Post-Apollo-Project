#!/usr/bin/env python3
"""TimeW Scope A untrusted fractional observation candidate denials.

No window commands, local persistence, source enrollment, or trusted receipts.
"""
from dataclasses import replace
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))

import MachineGeometryV2 as legacy_projection
import MachineGeometryStoreV2 as legacy_store
import MachineV2GeometryJournal as legacy_journal
from MachineV2ExactLogicalGeometry import (
    PHASE_PENDING, PHASE_CURRENT, capture_value,
)
from MachineV2FractionalObservationReview import (
    FractionalObservationRefused, KIND, REVIEW_REVISION,
    review_untrusted_candidate,
)

checks = 0


def check(condition, label):
    global checks
    assert condition, label
    checks += 1


def refuses(call, label):
    global checks
    try:
        call()
    except FractionalObservationRefused:
        checks += 1
    else:
        raise AssertionError(label + " incorrectly accepted")


def make(phase, *, x, y, width, height):
    return capture_value(phase, x=x, y=y, width=width, height=height)


def current(x, y, width, height):
    return make(PHASE_CURRENT, x=x, y=y, width=width, height=height)


def pending(x, y, width, height):
    return make(PHASE_PENDING, x=x, y=y, width=width, height=height)


def review(**changes):
    values = {
        "before_current": current(259, 92.5, 1402, 872),
        "target_pending": pending(100.125, 60.5, 1000.25, 700.75),
        "post_resize_current": current(460.0, 178.5, 1000.25, 700.75),
        "final_current": current(100.125, 60.5, 1000.25, 700.75),
        "resize_stage": "READY_REPORTED",
        "move_stage": "READY_REPORTED",
    }
    values.update(changes)
    return review_untrusted_candidate(**values)


def deny_result(result, status):
    check(type(result) is dict and result["kind"] == KIND, "result kind")
    check(result["review_revision"] == REVIEW_REVISION, "local review revision")
    check(result["status"] == status, "expected HOLD: " + status)
    check(result["read_only"] is True, "read-only invariant")
    for flag in (
        "restore_allowed", "native_action_allowed",
        "selected_surface_authenticated", "compositor_source_authenticated",
        "configure_ack_verified", "final_frame_settled",
        "c5_consent_spent_verified",
    ):
        check(result[flag] is False, "no positive authority: " + flag)
    check(result["no_automatic_retry"] is True, "no replay")
    check(result["no_automatic_undo"] is True, "no undo")
    check(result["safe_actions"] == [], "empty safe actions")


# Real fractional y=92.5 and a re-centered post-resize observation.
# An identical-looking CURRENT value can be copied by compositor timeout.
deny_result(review(), "MATCHED_VALUES_UNTRUSTED_HOLD")
deny_result(review(resize_stage="TIMEOUT_FORCED"), "UNKNOWN_HOLD")
deny_result(review(move_stage="TIMEOUT_FORCED"), "UNKNOWN_HOLD")
deny_result(review(resize_stage="TIMEOUT_FORCED", move_stage="READY_REPORTED"),
            "UNKNOWN_HOLD")
deny_result(review(resize_stage="UNKNOWN"), "UNKNOWN_HOLD")
deny_result(review(move_stage="UNKNOWN"), "UNKNOWN_HOLD")
deny_result(review(post_resize_current=None), "UNKNOWN_HOLD")
deny_result(review(final_current=None), "UNKNOWN_HOLD")
deny_result(review(post_resize_current=None, move_stage="TIMEOUT_FORCED"),
            "UNKNOWN_HOLD")

# CURRENT after timeout is not an ACK, even with perfect final bits.
# Changed x/y after resize MUST NOT be assumed to equal initial x/y.
post_resize_changed_origin = current(460.0, 178.5, 1000.25, 700.75)
check(post_resize_changed_origin.x_bits != current(
    259.0, 92.5, 1000.25, 700.75).x_bits, "resize can shift x")
check(post_resize_changed_origin.y_bits != current(
    259.0, 92.5, 1000.25, 700.75).y_bits, "resize can shift y")

# Exactly one ULP of final-position or post-resize-size drift must not match.
one_ulp = math.nextafter(60.5, math.inf)
deny_result(review(final_current=current(100.125, one_ulp, 1000.25, 700.75)),
            "GEOMETRY_MISMATCH_HOLD")
deny_result(review(post_resize_current=current(
    460.0, 178.5, math.nextafter(1000.25, math.inf), 700.75)),
    "GEOMETRY_MISMATCH_HOLD")
deny_result(review(final_current=current(100.125, 60.5, 1000.25, 700.5)),
            "GEOMETRY_MISMATCH_HOLD")

# 128 deterministic fractional scenarios. A *matching* observation is not
# a permission token and must remain HOLD for all numerically valid values.
for index in range(128):
    shift = index / 16.0
    before = current(259 + shift, 92.5 + shift, 1402, 872)
    target = pending(100.125 + shift, 60.5 + shift, 1000.25, 700.75)
    after_resize = current(460 + shift, 178.5 + shift, 1000.25, 700.75)
    final = current(100.125 + shift, 60.5 + shift, 1000.25, 700.75)
    result = review(
        before_current=before, target_pending=target,
        post_resize_current=after_resize, final_current=final)
    check(result["status"] == "MATCHED_VALUES_UNTRUSTED_HOLD",
          "source-free matching remains HOLD in sample " + str(index))
    check(result["restore_allowed"] is False
          and result["native_action_allowed"] is False
          and result["safe_actions"] == [], "no execution " + str(index))

# Unknown/forged stage types are refused: no invented PRESENT privilege.
for invalid in (None, True, False, 0, "", "READY", "PRESENT_REPORTED",
                "CURRENT_COPIED", "ACKED", "SETTLED", "TIMEOUT"):
    refuses(lambda v=invalid: review(resize_stage=v), "resize fake stage")
    refuses(lambda v=invalid: review(move_stage=v), "move fake stage")

# Reject wrong PENDING/CURRENT labels, stale versions, tampered raw bits,
# and impostor objects. A readable decimal is not bit-accurate authority.
wrong_before = pending(259, 92.5, 1402, 872)
wrong_target = current(100.125, 60.5, 1000.25, 700.75)
refuses(lambda: review(before_current=wrong_before), "before must be CURRENT")
refuses(lambda: review(target_pending=wrong_target), "target must be PENDING")
refuses(lambda: review(post_resize_current=wrong_before),
        "post-resize must be CURRENT")
refuses(lambda: review(final_current=wrong_target),
        "final must be CURRENT")
refuses(lambda: review(before_current={"phase": "CURRENT"}),
        "untyped map cannot become native record")
refuses(lambda: review(target_pending=replace(
    pending(100.125, 60.5, 1000.25, 700.75), version=2)),
    "future version refused")
refuses(lambda: review(final_current=replace(
    current(100.125, 60.5, 1000.25, 700.75),
    x_bits=struct.unpack("=Q", struct.pack("=d", float("nan")))[0])),
    "forged nonfinite bits refused")
refuses(lambda: review(post_resize_current=replace(
    current(460, 178.5, 1000.25, 700.75), x_bits=-1)),
    "forged negative bits refused")

# Legacy integer-only schema and operation journal must not accept fractions.
fraction = {"x": 259, "y": 92.5, "width": 1402, "height": 872}
for call, error, label in (
    (lambda: legacy_projection._rectangle(fraction),
     legacy_projection.GeometryError, "legacy projection"),
    (lambda: legacy_store._rect(fraction),
     legacy_store.GeometryStoreError, "legacy checkpoint"),
    (lambda: legacy_journal._rect(fraction),
     legacy_journal.GeometryJournalError, "legacy journal"),
):
    try:
        call()
    except error:
        checks += 1
    else:
        raise AssertionError(label + " silently widened")

# Import-only, no native runner, DB, signer, socket, UI or background effect.
path = ROOT / "services" / "time" / "MachineV2FractionalObservationReview.py"
code = path.read_text()
for forbidden in (
    "import socket", "import subprocess", "import sqlite3",
    "import os", "swaymsg", "command_runner", "Ed25519PrivateKey",
    "from MachineV2FloatingPilot", "from MachineV2GeometryJournal",
    "def main(", 'if __name__',
):
    check(forbidden not in code, "privileged dependency forbidden: " + forbidden)
for old_file in (
    ROOT / "widgets" / "TimeW.qml",
    ROOT / "services" / "time" / "MachineGeometryStoreV2.py",
    ROOT / "services" / "time" / "MachineV2GeometryJournal.py",
    ROOT / "services" / "time" / "MachineV2FloatingPilot.py",
):
    check("MachineV2FractionalObservationReview" not in old_file.read_text(),
          "no legacy or live entrypoint imports the candidate")

print("TIMEW FRACTIONAL OBSERVATION REVIEW // "
      + str(checks) + " deny-only checks PASS; native receipt NOT TESTED")
