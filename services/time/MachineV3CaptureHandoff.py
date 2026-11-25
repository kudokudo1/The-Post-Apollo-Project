"""M12a: proposed in-process TimeW consumer for a complete SwayPX capture.

No installed producer, IPC, log parsing, storage, command or UI hook. The
caller supplies two independently acquired batches under the proposed source
contract. Agreement is a local consistency check, not authenticated origin,
atomic live capture, source freshness or permission to Restore.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid

from MachineCaptureSaveV2 import _legacy_from_geometry
from MachineGeometryV2 import project_geometry, MAX_WINDOWS
from MachineGeometryStoreV2 import validate_pair, _raw
from MachineV2ExactLogicalGeometry import (
    ExactLogicalRect, VALUE_VERSION, PHASE_CURRENT, read_value,
)
from MachineV3LocalSaveRecovery import _canonical_candidates
from MachineV3LocalExactCaptureStore import _id, _text

KIND = "swaypx-local-capture-proposal-v1"
MAX_REVISION = (1 << 64) - 1
HEX = re.compile(r"[0-9a-f]{16}\Z", re.ASCII)
BATCH = {"kind", "epoch", "revision", "pending_transaction",
         "queued_transaction", "outputs", "workspaces", "tree", "windows"}
ROW = {"con_id", "lifetime", "app_id", "output_id", "workspace_id",
       "phase", "current_bits"}


class CaptureHandoffRefused(ValueError):
    pass


def _refuse():
    raise CaptureHandoffRefused("TIMEW FRACTIONAL CAPTURE HANDOFF REFUSED") from None


def _snapshot(batch, identity):
    if type(batch) is not dict or set(batch) != BATCH or batch["kind"] != KIND:
        _refuse()
    # Take a bounded independent copy of the JSON-compatible input, not
    # caller-owned lists retained into the returned Save bundle.
    frozen = json.loads(_raw(batch))
    epoch = _id(frozen["epoch"], version=4)
    revision = frozen["revision"]
    if (type(revision) is not int or not 0 <= revision <= MAX_REVISION
            or frozen["pending_transaction"] is not False
            or frozen["queued_transaction"] is not False):
        _refuse()
    rows = frozen["windows"]
    if type(rows) is not list or not 1 <= len(rows) <= MAX_WINDOWS:
        _refuse()
    keys, lifetimes, candidates = {}, set(), []
    continuity = []
    for row in rows:
        if type(row) is not dict or set(row) != ROW:
            _refuse()
        cid = row["con_id"]
        lifetime = _id(row["lifetime"], version=4)
        if (type(cid) is not int or not 1 <= cid <= MAX_REVISION
                or cid in keys or lifetime in lifetimes
                or row["phase"] != "CURRENT"):
            _refuse()
        bits = row["current_bits"]
        if (type(bits) is not list or len(bits) != 4
                or any(type(b) is not str or not HEX.fullmatch(b) for b in bits)):
            _refuse()
        value = ExactLogicalRect(VALUE_VERSION, PHASE_CURRENT,
                                 *(int(b, 16) for b in bits))
        read_value(value)
        # Checkpoint-local UUIDs, never reuse a raw con_id as long-term identity.
        key = str(uuid.uuid5(uuid.UUID(identity), f"{epoch}:{cid}:{lifetime}"))
        keys[cid] = key
        lifetimes.add(lifetime)
        continuity.append((cid, lifetime, key))
        candidates.append({
            "window_key": key, "app_id": _text(row["app_id"]),
            "output_id": _text(row["output_id"]), "workspace_id": _text(row["workspace_id"]),
            "value": value,
        })

    # Existing V2 projector requires the transient ID map to match *all*
    # tracked windows in the ordinary frame. Do not silently skip tiled,
    # Xwayland, unsupported or temporarily unobservable windows.
    geometry = project_geometry(frozen["outputs"], frozen["workspaces"],
                                frozen["tree"], window_keys=keys)
    canonical = _canonical_candidates(candidates)
    expected = sorted((w["window_key"], w["app_id"], w["output"], w["workspace"])
                      for w in geometry["windows"])
    if [row[:4] for row in canonical] != expected:
        _refuse()
    return (epoch, revision, sorted(continuity), geometry, canonical,
            sorted(candidates, key=lambda row: row["window_key"]))


def prepare_local_capture(*, identity, first, second, label, captured_at):
    """Return ordinary documents + exact observations for a future M10 caller.

    Require two separate input objects. This cannot prove two acquisition
    events; producer-owned snapshot/epoch/lifetime semantics remain open.
    The current binary64 fields and the ordinary IPC rect are intentionally
    not converted into one another (their exact correspondence is a source
    contract obligation). No native/source/consent proof is returned.
    """
    try:
        identity = _id(identity, version=4)
        if first is second:
            _refuse()
        if (type(label) is not str or len(label) > 48
                or any(ord(c) < 32 or ord(c) == 127 for c in label)
                or type(captured_at) is not dt.datetime
                or captured_at.tzinfo is None or captured_at.utcoffset() is None):
            _refuse()
        a = _snapshot(first, identity)
        b = _snapshot(second, identity)
        if a[:5] != b[:5]:
            _refuse()
        legacy = _legacy_from_geometry(
            a[3], label=label,
            captured_at=captured_at.astimezone(dt.timezone.utc).isoformat(),
        )
        old, geometry = validate_pair(legacy, a[3])
        return {
            "status": "LOCAL_CAPTURE_CANDIDATES_UNTRUSTED",
            "identity": identity,
            "v1_document": old,
            "geometry_document": geometry,
            "observations": a[5],
            "read_only": True,
            "local_data_only": True,
            "source_authenticated": False,
            "snapshot_atomic_verified": False,
            "native_receipt_verified": False,
            "operator_selection_verified": False,
            "c5_spent_verified": False,
            "production_restore_allowed": False,
            "automatic_retry_allowed": False,
            "safe_actions": [],
        }
    except (ValueError, TypeError, KeyError, AttributeError,
            OverflowError, RecursionError, UnicodeError):
        _refuse()
