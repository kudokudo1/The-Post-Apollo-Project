#!/usr/bin/env python3
"""MACHINE v2 explicitly invoked SAVE / CUSTOMIZE bridge for TimeW.

- `inspect`: read-only double-observed Sway geometry, no storage.
- `save`: bounded single JSON request on stdin. Full SAVE needs no preview.
  Custom SAVE requires the selected window keys plus an exact frame digest and
  capture namespace produced by `inspect`.
The returned review has *no* compositor IDs, titles, PIDs, URLs, commands or
browser contents. Preview data is never written to disk. Any changed layout,
transient ID, missing window or monitor refuses a custom SAVE before storage.

The digest is a freshness guard, not a secret or authentication proof. Sway
queries are sequential, not an atomic compositor transaction. No restore,
browser manipulation, shell execution or background work here.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

# TimeW launches this CLI with Python -I. Isolated mode deliberately excludes
# the script's own directory from sys.path, so sibling imports must be
# explicitly bound to this trusted, resolved service directory first.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from MachineCaptureSaveV2 import (
    CaptureError, stable_geometry, geometry_digest, capture_and_save)
from MachineCaptureSelectionV2 import SelectionError
from MachineSwayRead import PreviewError
from MachineGeometryV2 import GeometryError
from MachineGeometryStoreV2 import GeometryStoreError, load_geometry
from MachineCheckpointStore import StoreError, load as load_legacy

MAX_REQUEST_BYTES = 65536
MAX_RESPONSE_BYTES = 262144
SAFE_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class BridgeError(ValueError):
    pass


def inspect(*, read_runner=subprocess.run, namespace_factory=uuid.uuid4):
    nonce = namespace_factory()
    if not isinstance(nonce, uuid.UUID) or nonce.version != 4:
        raise BridgeError("INSPECTION NONCE UNAVAILABLE")
    namespace = str(nonce)
    geometry = stable_geometry(read_runner=read_runner, namespace=namespace)
    return {
        "status": "ready", "kind": "machine-save-review-v2",
        "review": {"namespace": namespace, "digest": geometry_digest(geometry)},
        "outputs": [
            {"connector": x["connector"], "rect": x["rect"]}
            for x in geometry["outputs"]],
        "workspaces": [
            {"name": x["name"], "output": x["output"]}
            for x in geometry["workspaces"]],
        "windows": [
            {"window_key": x["window_key"], "app_id": x["app_id"],
             "workspace": x["workspace"], "output": x["output"],
             "floating": x["floating"], "rect": x["rect"]}
            for x in geometry["windows"]],
        "counts": {
            "outputs": len(geometry["outputs"]),
            "workspaces": len(geometry["workspaces"]),
            "windows": len(geometry["windows"]),
        },
        "read_only": True,
        "restorable_identity_verified": False,
    }


def _verified_receipt(saved, *, geometry_reader=load_geometry,
                      legacy_reader=load_legacy):
    """Read both committed rows through independent, read-only owners.

    A failed read-back does NOT undo a committed transaction. Report the
    checkpoint ID and an explicit unknown verification result so the UI
    does not encourage blind duplicate saves.
    """
    if (not isinstance(saved, dict) or saved.get("status") != "saved"
            or not isinstance(saved.get("checkpoint"), dict)
            or not isinstance(saved["checkpoint"].get("id"), str)):
        raise BridgeError("SAVE RESULT INVALID")
    checkpoint = saved["checkpoint"]
    checkpoint_id = checkpoint["id"]
    try:
        geometry = geometry_reader(checkpoint_id)
        original = legacy_reader(checkpoint_id)
        if (not isinstance(geometry, dict) or geometry.get("status") != "loaded"
                or geometry.get("geometry_available") is not True
                or geometry.get("checkpoint_id") != checkpoint_id
                or geometry.get("read_only") is not True
                or not isinstance(original, dict)
                or original.get("status") != "loaded"
                or original.get("read_only") is not True
                or original.get("checkpoint", {}).get("id") != checkpoint_id
                or original["checkpoint"] != checkpoint):
            raise BridgeError("READBACK RECORDS DO NOT MATCH")
        data = geometry["geometry"]
        actual = {"outputs": len(data["outputs"]),
                  "workspaces": len(data["workspaces"]),
                  "windows": len(data["windows"])}
        if actual != checkpoint["counts"]:
            raise BridgeError("READBACK COUNTS DO NOT MATCH")
        return dict(saved, verification={
            "status": "readback_verified", "counts": actual,
            "geometry": True, "legacy": True,
        })
    except (BridgeError, GeometryStoreError, StoreError, sqlite3.Error,
            OSError, ValueError, TypeError, KeyError):
        return dict(saved, status="saved_unverified", verification={
            "status": "readback_unavailable",
        })


def save_request(request, *, read_runner=subprocess.run,
                 store_adapter=None, key_factory=None,
                 geometry_reader=load_geometry, legacy_reader=load_legacy):
    """Single explicit SAVE call; no confirmation click or preview required."""
    if not isinstance(request, dict) or set(request) != {
            "label", "review", "selection"}:
        raise BridgeError("INVALID SAVE REQUEST")
    label = request["label"]
    if (not isinstance(label, str) or not 1 <= len(label) <= 48
            or any(ord(c) < 32 or ord(c) == 127 for c in label)):
        raise BridgeError("INVALID SAVE LABEL")
    review = request["review"]
    selection = request["selection"]
    if (review is None and selection is not None
            or review is not None and selection is None):
        raise BridgeError("CUSTOMIZE REVIEW REQUIRED")
    if review is not None:
        if (not isinstance(review, dict)
                or set(review) != {"namespace", "digest"}
                or not isinstance(review["namespace"], str)
                or not isinstance(review["digest"], str)
                or not SAFE_DIGEST.fullmatch(review["digest"])):
            raise BridgeError("INVALID CUSTOMIZE REVIEW")
        try:
            nonce = uuid.UUID(review["namespace"])
        except (ValueError, AttributeError) as exc:
            raise BridgeError("INVALID CUSTOMIZE REVIEW") from exc
        if nonce.version != 4 or str(nonce) != review["namespace"]:
            raise BridgeError("INVALID CUSTOMIZE REVIEW")
        if not isinstance(selection, dict) or not set(selection).issubset(
                {"outputs", "workspaces", "windows"}):
            raise BridgeError("INVALID CUSTOMIZE SELECTION")
    options = {"label": label, "review_binding": review,
               "selection": selection, "read_runner": read_runner}
    if store_adapter is not None:
        options["store_adapter"] = store_adapter
    if key_factory is not None:
        options["key_factory"] = key_factory
    saved = capture_and_save(**options)
    return _verified_receipt(saved, geometry_reader=geometry_reader,
                             legacy_reader=legacy_reader)


def _decode_request():
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if (not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n")):
        raise BridgeError("INVALID OR OVERSIZED SAVE REQUEST")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise BridgeError("INVALID SAVE REQUEST") from exc


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv not in (["inspect"], ["save"]):
        print(json.dumps({"status": "error", "reason": "INVALID ACTION"}))
        return 1
    try:
        if argv == ["inspect"]:
            result = inspect()
        else:
            result = save_request(_decode_request())
        raw = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        if len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise BridgeError("RESPONSE TOO LARGE")
        print(raw)
        return 0
    except (BridgeError, CaptureError, SelectionError) as exc:
        # These exceptions contain only bounded app-authored status values.
        print(json.dumps({"status": "error", "reason": str(exc)}))
        return 1
    except PreviewError:
        print(json.dumps({"status": "error", "reason": "SWAY READ UNAVAILABLE"}))
        return 1
    except GeometryError:
        print(json.dumps({"status": "error", "reason": "SWAY GEOMETRY UNSUPPORTED"}))
        return 1
    except (StoreError, GeometryStoreError, sqlite3.Error):
        print(json.dumps({"status": "error", "reason": "CHECKPOINT STORE UNAVAILABLE"}))
        return 1
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        # Do not echo raw Sway payloads, paths, private titles or SQL errors.
        print(json.dumps({"status": "error", "reason": "SAVE BACKEND UNAVAILABLE"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
