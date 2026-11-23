"""DOC 5 / TimeW C5 dual-source recovery RETURN comparison, CI ONLY.

Correlates two caller-provided, untrusted diagnostic RESULTS with the same
already-created immutable original-operation lookup plan (#2333).
NO provider calls, IPC, DB, root/key verification, human gesture, native
command, replay, or production authorization. No wire/API is standardized.
Even a perfectly matching "protected candidate" remains UNKNOWN/HOLD.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from TimeWC5CustodianBoundaryReference import (
    EVIDENCE_FIELDS, HEAD_FIELDS, LEDGER_STATES, SCHEMA as C5_SCHEMA,
    SOURCE_MODES, _head_shape,
)
from TimeWC5ReadOnlyRecoveryPlanReference import (
    RecoveryPlan, UntrustedLookupIntent, CUSTODIAN_LOOKUP, NATIVE_LOOKUP,
    CUSTODIAN_FIELDS, NATIVE_FIELDS, UNCERTAINTIES,
)

NATIVE_SCHEMA = "postapollo.connections.c5.timew.native-return-fixture.v1"
NATIVE_MODES = frozenset(("LOCAL_DIAGNOSTIC", "PROTECTED_CANDIDATE"))
OBSERVATIONS = frozenset((
    "NONE", "READY_ONLY", "TIMEOUT", "READY_AND_TIMEOUT",
    "CURRENT_SCENE", "OUTPUT_PRESENT",
))
NATIVE_RETURN_FIELDS = frozenset((
    "schema", "source_mode", "operation_id", "grant_id",
    "selection_sha256", "intent_sha256", "source_sha256",
    "session_id", "seat_id", "checkpoint_id", "window_key",
    "boot_epoch", "surface_generation", "output_id", "workspace_id",
    "output_scale_hex", "output_transform", "before_bits", "target_bits",
    "resize_observation", "move_observation",
    "output_present", "selected_xdg_frame_claimed",
    "head_sha256", "sequence",
))
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
UINT64 = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class Comparison:
    diagnostic: str
    production_authorized: bool = False
    external_custody_verified: bool = False
    current_head_verified: bool = False
    protected_spent_verified: bool = False
    operator_intent_verified: bool = False
    native_source_verified: bool = False
    configure_ack_verified: bool = False
    selected_frame_settled: bool = False
    terminal_receipt_verified: bool = False
    native_action_allowed: bool = False
    second_spend_allowed: bool = False
    move_allowed: bool = False
    retry_allowed: bool = False
    undo_allowed: bool = False
    safe_actions: tuple = ()


def _hold(code):
    return Comparison(code)


def _same(a, b):
    """Python bool is int: an exact identity binding must reject that alias."""
    return type(a) is type(b) and a == b


def _binding(intent, keys, *, expected_role, original_id, original_grant):
    if (type(intent) is not UntrustedLookupIntent
            or intent.role != expected_role
            or intent.original_operation_id != original_id
            or intent.original_grant_id != original_grant
            or type(intent.original_binding) is not tuple
            or any(type(x) is not tuple or len(x) != 2
                   or type(x[0]) is not str
                   or type(x[1]) not in (str, int)
                   for x in intent.original_binding)):
        return None
    names = [key for key, _ in intent.original_binding]
    if names != list(keys) or len(names) != len(set(names)):
        return None
    return dict(intent.original_binding)


def _valid_plan(plan):
    if (type(plan) is not RecoveryPlan
            or plan.diagnostic !=
            "UNTRUSTED_DUAL_READ_ONLY_LOOKUP_INTENTS_UNKNOWN_HOLD"
            or plan.uncertainty not in UNCERTAINTIES
            or type(plan.query_intents) is not tuple
            or len(plan.query_intents) != 2
            or any(getattr(plan, field) is not False for field in (
                "production_authorized", "protected_spent_verified",
                "custodian_current_head_verified",
                "original_human_consent_verified",
                "native_source_authenticated", "terminal_settlement_verified",
                "native_action_allowed", "automatic_second_spend_allowed",
                "move_continuation_allowed", "retry_allowed", "undo_allowed"))
            or plan.safe_actions != ()):
        return None
    c, n = plan.query_intents
    if (type(c) is not UntrustedLookupIntent
            or type(n) is not UntrustedLookupIntent
            or type(c.original_operation_id) is not str
            or type(c.original_grant_id) is not str):
        return None
    original_id, original_grant = c.original_operation_id, c.original_grant_id
    cb = _binding(c, CUSTODIAN_FIELDS, expected_role=CUSTODIAN_LOOKUP,
                  original_id=original_id, original_grant=original_grant)
    native_keys = NATIVE_FIELDS + tuple(
        f"{phase}_{name}" for phase in ("before", "target")
        for name in ("version", "phase", "x_bits", "y_bits",
                     "width_bits", "height_bits"))
    nb = _binding(n, native_keys, expected_role=NATIVE_LOOKUP,
                  original_id=original_id, original_grant=original_grant)
    if cb is None or nb is None:
        return None
    if (cb["operation_id"] != original_id
            or cb["grant_id"] != original_grant
            or nb["operation_id"] != original_id
            or any(not _same(cb[key], nb[key]) for key in (
                "selection_sha256", "intent_sha256", "source_sha256",
                "session_id", "seat_id"))):
        return None
    if (nb["before_version"] != 1 or nb["target_version"] != 1
            or nb["before_phase"] != 2 or nb["target_phase"] != 1
            or any(type(nb[f"{p}_{k}_bits"]) is not int
                   or not 0 <= nb[f"{p}_{k}_bits"] <= UINT64
                   for p in ("before", "target")
                   for k in ("x", "y", "width", "height"))):
        return None
    return cb, nb, original_id, original_grant


def _valid_c5_response(data, c):
    if type(data) is not dict or set(data) != EVIDENCE_FIELDS:
        return False
    if (data["schema"] != C5_SCHEMA
            or type(data["source_mode"]) is not str
            or data["source_mode"] not in SOURCE_MODES
            or type(data["ledger_state"]) is not str
            or data["ledger_state"] not in LEDGER_STATES
            or not _head_shape({k: data[k] for k in HEAD_FIELDS})
            or (data["terminal_receipt_sha256"] is not None
                and (type(data["terminal_receipt_sha256"]) is not str
                     or HEX64.fullmatch(data["terminal_receipt_sha256"])
                     is None))):
        return False
    return True


def _valid_native_response(data):
    if type(data) is not dict or set(data) != NATIVE_RETURN_FIELDS:
        return False
    if (data["schema"] != NATIVE_SCHEMA
            or type(data["source_mode"]) is not str
            or data["source_mode"] not in NATIVE_MODES
            or any(type(data[k]) is not str
                   or not 1 <= len(data[k]) <= 128
                   for k in (
                       "operation_id", "grant_id", "selection_sha256",
                       "intent_sha256", "source_sha256", "session_id", "seat_id",
                       "checkpoint_id", "window_key", "boot_epoch",
                       "output_id", "workspace_id", "output_scale_hex"))
            or type(data["surface_generation"]) is not int
            or not 1 <= data["surface_generation"] <= 9007199254740991
            or type(data["output_transform"]) is not int
            or not 0 <= data["output_transform"] <= 7
            or any(type(data[k]) is not str
                   or data[k] not in OBSERVATIONS
                   for k in ("resize_observation", "move_observation"))
            or type(data["output_present"]) is not bool
            or type(data["selected_xdg_frame_claimed"]) is not bool
            or not _head_shape({k: data[k] for k in HEAD_FIELDS})):
        return False
    for name in ("before_bits", "target_bits"):
        bits = data[name]
        if (type(bits) is not tuple or len(bits) != 4
                or any(type(v) is not int or not 0 <= v <= UINT64
                       for v in bits)):
            return False
    return True


def _prior_shape(prior):
    if prior is None:
        return True
    return (type(prior) is dict and set(prior) == {"c5", "native"}
            and all(prior[k] is None or _head_shape(prior[k])
                    for k in ("c5", "native")))


def _progression(prior, observation):
    if prior is None:
        return None
    old, new = prior, observation
    if new["sequence"] < old["sequence"]:
        return "PRIOR_HEAD_ROLLBACK_UNKNOWN_HOLD"
    if new["sequence"] == old["sequence"] and (
            new["head_sha256"] != old["head_sha256"]):
        return "PRIOR_HEAD_FORK_UNKNOWN_HOLD"
    if new["sequence"] > old["sequence"] and (
            new["head_sha256"] == old["head_sha256"]):
        return "UNSUPPORTED_HEAD_ADVANCE_UNKNOWN_HOLD"
    return None


def compare_untrusted_recovery_returns(*, plan, c5_return, native_return,
                                       last_seen=None):
    """Two read-only return snapshots, NO provider invocation or authority.

    A future independently authenticated current-head and signed-source
    consumer must be designed and accepted elsewhere. In particular, the
    "selected_xdg_frame_claimed" boolean is UNSIGNED caller input.
    """
    parsed = _valid_plan(plan)
    if parsed is None:
        return _hold("INVALID_ORIGINAL_RECOVERY_PLAN_UNKNOWN_HOLD")
    cb, nb, original_id, original_grant = parsed
    if not _prior_shape(last_seen):
        return _hold("INVALID_LOCAL_PRIOR_HEAD_UNKNOWN_HOLD")
    if c5_return is None:
        return _hold("MISSING_C5_HISTORY_UNKNOWN_HOLD")
    if not _valid_c5_response(c5_return, cb):
        return _hold("MALFORMED_C5_RESPONSE_UNKNOWN_HOLD")
    for k in CUSTODIAN_FIELDS:
        if not _same(c5_return[k], cb[k]):
            return _hold("C5_ORIGINAL_INTENT_MISMATCH_UNKNOWN_HOLD")
    if native_return is None:
        return _hold("MISSING_NATIVE_TERMINAL_UNKNOWN_HOLD")
    if not _valid_native_response(native_return):
        return _hold("MALFORMED_NATIVE_RESPONSE_UNKNOWN_HOLD")
    for k in NATIVE_FIELDS:
        if not _same(native_return[k], nb[k]):
            return _hold("NATIVE_ORIGINAL_WINDOW_MISMATCH_UNKNOWN_HOLD")
    if (not _same(native_return["grant_id"], original_grant)
            or not _same(native_return["operation_id"], original_id)):
        return _hold("NATIVE_ORIGINAL_GRANT_MISMATCH_UNKNOWN_HOLD")
    for phase in ("before", "target"):
        expected = tuple(nb[f"{phase}_{axis}_bits"]
                         for axis in ("x", "y", "width", "height"))
        if native_return[f"{phase}_bits"] != expected:
            return _hold("NATIVE_EXACT_GEOMETRY_MISMATCH_UNKNOWN_HOLD")

    if last_seen is not None:
        for key, data in (("c5", c5_return), ("native", native_return)):
            error = _progression(last_seen[key], data)
            if error:
                return _hold(key.upper() + "_" + error)

    if c5_return["ledger_state"] == "ACTIVE" and (
            native_return["resize_observation"] != "NONE"
            or native_return["move_observation"] != "NONE"):
        return _hold("NATIVE_EFFECT_WITHOUT_PROVEN_SPENT_UNKNOWN_HOLD")
    if c5_return["ledger_state"] == "REVOKED":
        return _hold("REVOCATION_NOT_A_TERMINAL_RECEIPT_UNKNOWN_HOLD")
    if c5_return["ledger_state"] == "UNKNOWN":
        return _hold("C5_UNKNOWN_HISTORY_UNKNOWN_HOLD")
    if native_return["resize_observation"] == "READY_AND_TIMEOUT":
        return _hold("CONTRADICTORY_RESIZE_UNKNOWN_HOLD")
    if native_return["move_observation"] == "READY_AND_TIMEOUT":
        return _hold("CONTRADICTORY_MOVE_UNKNOWN_HOLD")
    if (native_return["move_observation"] != "NONE"
            and native_return["resize_observation"] != "READY_ONLY"):
        return _hold("MOVE_WITHOUT_SETTLED_RESIZE_UNKNOWN_HOLD")
    if native_return["selected_xdg_frame_claimed"]:
        return _hold("CLAIMED_SELECTED_FRAME_NOT_VERIFIED_UNKNOWN_HOLD")
    if native_return["output_present"]:
        return _hold("OUTPUT_PRESENT_NOT_SELECTED_FRAME_UNKNOWN_HOLD")
    if (c5_return["source_mode"] == "LOCAL_DEVELOPMENT"
            or native_return["source_mode"] == "LOCAL_DIAGNOSTIC"):
        return _hold("LOCAL_DEVELOPMENT_EVIDENCE_UNKNOWN_HOLD")
    return _hold("MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD")
