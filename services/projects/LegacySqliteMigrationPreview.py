#!/usr/bin/env python3
"""M10m pure, byte-aware legacy TASKS -> SQLite-v2 migration PREVIEW.

No file paths, no database I/O, no backup writer, no Quickshell connection,
and no remote sync. This module requires explicit caller-supplied bytes.
The operator's live JSON remains the sole source of truth.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / "tests/tasks/fixtures/legacy_to_sqlite_v2_oracle.cjs"
VALIDATOR = ROOT / "services/projects/ExperimentalTaskSqliteStore.py"
MAX_SOURCE_BYTES = 1048576


class PreviewRejected(ValueError):
    pass


def _duplicate_check(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreviewRejected("DUPLICATE_LEGACY_JSON_KEY")
        result[key] = value
    return result


def _reject_constant(value):
    raise PreviewRejected("NONFINITE_JSON_VALUE")


def _read_validator():
    spec = importlib.util.spec_from_file_location("m10m_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise PreviewRejected("VALIDATOR_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preview(source_bytes: bytes):
    if type(source_bytes) is not bytes or not 0 < len(source_bytes) <= MAX_SOURCE_BYTES:
        raise PreviewRejected("INVALID_SOURCE_BYTES")
    try:
        raw = source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise PreviewRejected("INVALID_SOURCE_UTF8") from exc
    try:
        json.loads(raw, object_pairs_hook=_duplicate_check,
                   parse_constant=_reject_constant)
    except PreviewRejected:
        raise
    except (TypeError, ValueError) as exc:
        raise PreviewRejected("INVALID_SOURCE_JSON") from exc
    try:
        run = subprocess.run(
            ["node", str(ORACLE)], cwd=ROOT, input=source_bytes,
            capture_output=True, timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreviewRejected("MIGRATION_ORACLE_UNAVAILABLE") from exc
    if run.returncode != 0 or len(run.stdout) > 2 * MAX_SOURCE_BYTES:
        raise PreviewRejected("MIGRATION_ORACLE_FAILED")
    try:
        converted = json.loads(run.stdout,
            object_pairs_hook=_duplicate_check, parse_constant=_reject_constant)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PreviewRejected("INVALID_ORACLE_OUTPUT") from exc
    if not isinstance(converted, dict) or converted.get("ok") is not True:
        reason = (converted.get("reason", "REJECTED") if isinstance(converted, dict)
                  else "INVALID_RESULT")
        raise PreviewRejected("LEGACY_CONVERSION_" + str(reason)[:100])
    if (converted.get("writeReady") is not False
            or converted.get("migrationPerformed") is not False
            or converted.get("remoteWriteAuthorized") is not False):
        raise PreviewRejected("UNSAFE_PREVIEW_FLAGS")
    candidate = converted.get("candidate")
    baseline = converted.get("compatibilityV3")
    if type(candidate) is not dict or type(baseline) is not dict:
        raise PreviewRejected("INCOMPLETE_PREVIEW")
    verifier = _read_validator()
    try:
        verifier.validate(candidate)
    except (verifier.StoreError, ValueError, TypeError) as exc:
        raise PreviewRejected("INVALID_SQLITE_V2_CANDIDATE") from exc
    if (candidate["version"] != 2 or candidate["revision"] != 0
            or candidate["nextOperationId"] != 1
            or candidate["operations"] != []
            or any(p["family"] != "normal" or p["remote"] is not None
                   for p in candidate["projects"])
            or any(t["remote"] is not None or t["values"] != {}
                   for t in candidate["tasks"])):
        raise PreviewRejected("UNSUPPORTED_ACTIVE_OR_REMOTE_DATA")
    if converted.get("counts") != {
        "projects":len(candidate["projects"]), "tasks":len(candidate["tasks"])
    }:
        raise PreviewRejected("COUNT_MISMATCH")
    return {
        "ok": True,
        "sourceVersion": converted["sourceVersion"],
        "originalBytes": len(source_bytes),
        "originalSha256": hashlib.sha256(source_bytes).hexdigest(),
        "candidate": candidate,
        "compatibilityV3": baseline,
        "counts": converted["counts"],
        "writeReady": False,
        "migrationPerformed": False,
        "remoteWriteAuthorized": False,
    }
