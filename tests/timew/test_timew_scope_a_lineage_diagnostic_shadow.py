#!/usr/bin/env python3
"""Source-only synthetic SwayPX #178 lineage compatibility negative matrix."""
from copy import deepcopy
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "timew"))

from TimeWScopeALineageDiagnosticShadow import (
    FIELDS, KIND, SHADOW_REVISION, _valid, inspect_untrusted_lineage,
)

checks = 0


def check(condition, label):
    global checks
    assert condition, label
    checks += 1


def bits(number):
    return struct.unpack("=Q", struct.pack("=d", number))[0]


def make(**changes):
    sample = {
        "boot_a": 11,
        "boot_b": 22,
        "lifetime_sequence": 1,
        "transaction_sequence": 1,
        "seat_epoch": 5,
        "session_epoch": 9,
        "output_epoch": 10,
        "workspace_epoch": 12,
        "output_scale_bits": bits(1.25),
        "output_transform": 0,
    }
    sample.update(changes)
    return sample


def shadow(**changes):
    values = {
        "original": make(), "observed": make(),
        "timeout_seen": False, "revocation_seen": False,
        "process_exit_seen": False, "surface_alive_reported": True,
        "seat_unlocked_reported": True, "output_valid_reported": True,
    }
    values.update(changes)
    return inspect_untrusted_lineage(**values)


def deny(result, status):
    check(result["kind"] == KIND and
          result["shadow_revision"] == SHADOW_REVISION, "shadow identity")
    check(result["status"] == status, "must HOLD: " + status)
    check(result["read_only"] is True, "read-only")
    for flag in (
        "source_authenticated", "operator_selection_authenticated",
        "active_seat_authenticated", "transaction_commit_bound",
        "configure_ack_verified", "final_frame_settled",
        "native_receipt_verified", "protected_c5_spent_verified",
        "restore_allowed", "resize_allowed", "move_allowed",
        "retry_allowed", "undo_allowed",
    ):
        check(result[flag] is False, "no authority via " + flag)
    check(result["safe_actions"] == [], "no executable actions")


# Even exactly correlated process-local tag and epochs remains untrusted.
deny(shadow(), "MATCHED_DIAGNOSTIC_UNTRUSTED_HOLD")
check(_valid(make()) is True, "realistic #178 diagnostic fields")

# A timeout can have CURRENT copied and SCENE arranged (SwayPX #176).
# Even synthetic caller-supplied matching tags cannot authorize MOVE.
for flag in ("timeout_seen", "revocation_seen", "process_exit_seen"):
    deny(shadow(**{flag: True}), "AMBIGUOUS_OR_REVOKED_HOLD")
for flag in ("surface_alive_reported", "seat_unlocked_reported",
             "output_valid_reported"):
    deny(shadow(**{flag: False}), "OBSERVATION_CONTINUITY_LOST_HOLD")
for flag in ("timeout_seen", "revocation_seen", "process_exit_seen",
             "surface_alive_reported", "seat_unlocked_reported",
             "output_valid_reported"):
    for invalid in (None, 0, 1, "true", [], {}):
        deny(shadow(**{flag: invalid}), "INVALID_OBSERVATION_FLAG_HOLD")
deny(shadow(original=None), "MISSING_LINEAGE_UNKNOWN_HOLD")
deny(shadow(observed=None), "MISSING_LINEAGE_UNKNOWN_HOLD")

# Every field in SwayPX's diagnostic correlation matters to continuity,
# but NONE is a source signature. Never import native pointer addresses.
check(set(make()) == FIELDS, "strict field set")
for field in FIELDS:
    if field == "output_scale_bits":
        changed = bits(math.nextafter(1.25, math.inf))
    elif field == "output_transform":
        changed = 1
    else:
        changed = make()[field] + 1
    deny(shadow(observed=make(**{field: changed})),
         "LINEAGE_DRIFT_UNKNOWN_HOLD")
    deny(shadow(original=make(**{field: changed})),
         "LINEAGE_DRIFT_UNKNOWN_HOLD")

# Stale/ABA and context-reuse cases: new boot, changed lifetime or transaction
# generation, one-ULP scale drift, changed seat/output/workspace, and restart.
for updates in (
    {"boot_a": 23, "boot_b": 24},
    {"lifetime_sequence": 2},
    {"transaction_sequence": 2},
    {"seat_epoch": 6},
    {"session_epoch": 10},
    {"output_epoch": 11},
    {"workspace_epoch": 13},
    {"output_scale_bits": bits(math.nextafter(1.25, math.inf))},
    {"output_transform": 7},
):
    deny(shadow(observed=make(**updates)), "LINEAGE_DRIFT_UNKNOWN_HOLD")

# Strict syntax: no silent overflow, booleans pretending to be counters,
# nonfinite/negative-zero scales, extra fields or native pointer claims.
invalids = [
    make(boot_a=0, boot_b=0),
    make(lifetime_sequence=0),
    make(transaction_sequence=0),
    make(seat_epoch=0), make(session_epoch=0),
    make(output_epoch=0), make(workspace_epoch=0),
    make(boot_a=-1), make(boot_a=2**64),
    make(lifetime_sequence=True), make(boot_b=False),
    make(transaction_sequence="1"), make(output_epoch=1.0),
    make(output_transform=-1), make(output_transform=8),
    make(output_transform=True),
    make(output_scale_bits=bits(0.0)),
    make(output_scale_bits=bits(-0.0)),
    make(output_scale_bits=bits(-1.0)),
    make(output_scale_bits=bits(math.inf)),
    make(output_scale_bits=bits(-math.inf)),
    make(output_scale_bits=bits(math.nan)),
    make(output_scale_bits=2**64),
    make(output_scale_bits=True),
    {**make(), "native_view_ref": 0x1234},
    {key: value for key, value in make().items() if key != "seat_epoch"},
]
for raw in invalids:
    deny(shadow(observed=raw), "INVALID_LINEAGE_UNKNOWN_HOLD")
    deny(shadow(original=raw), "INVALID_LINEAGE_UNKNOWN_HOLD")

# 128 different locally consistent counters DO NOT grow into signed receipts
# or production permission. Two independent callers can forge all of these.
for index in range(1, 129):
    shared = make(
        boot_a=index + 1000, boot_b=index + 2000,
        lifetime_sequence=index, transaction_sequence=index,
        seat_epoch=index + 1, session_epoch=index + 2,
        output_epoch=index + 3, workspace_epoch=index + 4,
        output_scale_bits=bits(1.0 + index / 128.0),
    )
    original = deepcopy(shared)
    observed = deepcopy(shared)
    result = shadow(original=original, observed=observed)
    check(result["status"] == "MATCHED_DIAGNOSTIC_UNTRUSTED_HOLD",
          "exact diagnostic cannot authenticate " + str(index))
    check(not any(result[flag] for flag in (
        "restore_allowed", "native_receipt_verified",
        "protected_c5_spent_verified", "source_authenticated",
    )), "no authority sample " + str(index))
    changed = deepcopy(observed)
    changed["lifetime_sequence"] += 1
    check(shadow(original=original, observed=changed)["status"] ==
          "LINEAGE_DRIFT_UNKNOWN_HOLD", "lifetime drift " + str(index))

# Design hygiene: the reference is owned by tests, never a runtime importer.
source = (ROOT / "tests" / "timew" /
          "TimeWScopeALineageDiagnosticShadow.py").read_text()
for forbidden in (
    "import socket", "import sqlite3", "import subprocess", "import os",
    "swaymsg", "Ed25519PrivateKey", "command_runner", "native_move(",
    "from MachineV2FloatingPilot", "def main(", 'if __name__',
):
    check(forbidden not in source, "no privileged API: " + forbidden)
for live in (
    "widgets/TimeW.qml",
    "services/time/MachineV2FloatingPilot.py",
    "services/time/MachineV2GeometryJournal.py",
    "services/time/MachineV2FractionalObservationReview.py",
):
    check("TimeWScopeALineageDiagnosticShadow" not in
          (ROOT / live).read_text(), "no production import: " + live)

print("TIMEW SCOPE A DIAGNOSTIC LINEAGE // "
      + str(checks) + " deny-only checks PASS; native receipt NOT TESTED")
