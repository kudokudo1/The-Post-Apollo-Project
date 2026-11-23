#!/usr/bin/env python3
"""TimeW M5 UI bridge: only a user-click-driven, non-writing M4 JSON preview."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "time"
sys.path.insert(0, str(SERVICE))
from MachineV2ExactLogicalGeometry import PHASE_CURRENT, capture_value
from MachineV3LocalExactCaptureStore import DB_NAME, LocalExactCaptureStore

CHECKPOINT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
BRIDGE = SERVICE / "MachineV3LocalPreviewUiRead.py"
checks = 0


def check(condition, msg):
    global checks
    assert condition, msg
    checks += 1


def invoke(base, argv=None):
    env = dict(os.environ, XDG_DATA_HOME=str(base))
    req = argv if argv is not None else ["preview", CHECKPOINT]
    p = subprocess.run(
        [sys.executable, "-B", "-I", str(BRIDGE), *req],
        env=env, capture_output=True, text=True, timeout=12, check=False,
    )
    try:
        body = json.loads(p.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError("invalid bridge JSON") from exc
    return p, body


def deny(body):
    check(body["kind"] == "timew-v3-local-exact-capture-preview-v1",
          "M4 body identity")
    check(body["read_only"] is True
          and body["data_origin"] == "CALLER_SUPPLIED_LOCAL_UNTRUSTED",
          "ordinary local data only")
    check(body["safe_actions"] == [], "no actions")
    for flag in ("source_authenticated", "operator_selection_verified",
                 "c5_spent_verified", "native_receipt_verified",
                 "exact_restore_verified", "restore_allowed",
                 "native_action_allowed", "retry_allowed", "undo_allowed"):
        check(body[flag] is False, "no authority via " + flag)


with tempfile.TemporaryDirectory(prefix="timew-m5-widget-bridge-") as temp:
    data_home = Path(temp) / "isolated-data"
    data_home.mkdir(mode=0o700)
    db = data_home / "post-apollo" / "machine" / DB_NAME

    # Button-scoped absent DB is a normal empty result. No auto-save, path
    # creation, desktop subscription or operator XDG access is exercised.
    p, body = invoke(data_home)
    check(p.returncode == 0, "absent data is not an error")
    deny(body)
    check(body["status"] == "NO_LOCAL_CAPTURES"
          and body["entries"] == [], "absent capture is empty")
    check(not db.parent.exists(), "read-only click created no DB or directory")

    store = LocalExactCaptureStore(db)
    capture = store.save(
        checkpoint_id=CHECKPOINT,
        window_key=str(uuid.uuid4()),
        app_id="kitty", output_id="DP-1", workspace_id="3",
        value=capture_value(
            PHASE_CURRENT, x=259, y=92.5, width=1402, height=872),
    )
    store.save(
        checkpoint_id=OTHER,
        window_key=str(uuid.uuid4()),
        app_id="other", output_id="DP-2", workspace_id="private",
        value=capture_value(
            PHASE_CURRENT, x=0, y=10, width=900, height=500),
    )
    file_before = db.stat()
    p, body = invoke(data_home)
    check(p.returncode == 0 and p.stderr == "", "local widget read")
    deny(body)
    check(body["checkpoint_id"] == CHECKPOINT and body["count"] == 1,
          "only selected stored checkpoint")
    check(body["entries"][0]["capture_id"] == capture,
          "correct selected local capture")
    check(body["entries"][0]["app_id"] == "kitty",
          "correct app display")
    check(body["entries"][0]["geometry"]["y"]["decimal"] == "92.5",
          "exact decimal display")
    check(body["entries"][0]["geometry"]["y"]["binary64_hex"] ==
          (92.5).hex(), "binary64 hex retained")
    check("other" not in p.stdout and "private" not in p.stdout,
          "no other checkpoint disclosure")
    check(str(data_home) not in p.stdout + p.stderr,
          "no raw XDG path disclosure")
    check(db.stat().st_mtime_ns == file_before.st_mtime_ns
          and db.stat().st_size == file_before.st_size,
          "preview reads without modifying SQLite")

    # The bridge does not take any caller-supplied DB path, Save/Restore mode
    # or wildcard enumeration, including an extra command line switch.
    invalid = [
        [], ["restore", CHECKPOINT], ["preview", OTHER.upper()],
        ["preview", "not-a-uuid"], ["preview", CHECKPOINT, "--write"],
        ["preview", CHECKPOINT, str(db)], ["list-all", CHECKPOINT],
    ]
    for args in invalid:
        p, body = invoke(data_home, args)
        check(p.returncode == 1, "invalid CLI refused")
        deny(body)
        check(body["status"] == "UNAVAILABLE_HOLD"
              and body["checkpoint_id"] is None
              and body["entries"] == [], "fixed, no-leak refusal")
        check(str(data_home) not in p.stdout + p.stderr,
              "no diagnostic path leak")

    # Valid local bit replacements are not protected tamper evidence.
    updated = math.nextafter(92.5, math.inf)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE exact_captures SET y_bits=? WHERE id=?",
                     (format(capture_value(
                         PHASE_CURRENT, x=259, y=updated,
                         width=1402, height=872).y_bits, "016x"), capture))
    p, body = invoke(data_home)
    check(p.returncode == 0, "valid-bit edit still ordinary local data")
    deny(body)
    check(body["entries"][0]["geometry"]["y"]["binary64_hex"] ==
          updated.hex(), "one ULP is preserved without tamper detection")

    # Corrupt source causes total refusal, never partial-window records.
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE exact_captures SET y_bits=? WHERE id=?",
                     ("nothex", capture))
    p, body = invoke(data_home)
    check(p.returncode == 1, "corrupted record refuses preview")
    deny(body)
    check(body["status"] == "UNAVAILABLE_HOLD"
          and body["entries"] == [], "no partial result")

    # Permissions and schema downgrade are still enforced by M3/M4.
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE exact_captures SET y_bits=? WHERE id=?",
                     (format(capture_value(
                         PHASE_CURRENT, x=259, y=92.5,
                         width=1402, height=872).y_bits, "016x"), capture))
        conn.execute("PRAGMA user_version=99")
    p, body = invoke(data_home)
    check(p.returncode == 1 and body["status"] == "UNAVAILABLE_HOLD",
          "future schema refused")
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA user_version=3")
    os.chmod(db, 0o644)
    p, body = invoke(data_home)
    check(p.returncode == 1 and body["status"] == "UNAVAILABLE_HOLD",
          "unsafe permission refused")
    os.chmod(db, 0o600)

# Scope isolation. Any runtime import of this new bridge is only for read-only
# invocation from a new explicit STORED button, not from Save/Restore.
bridge = BRIDGE.read_text()
for forbidden in (
    "MachineRestoreCheckpoint", "MachineSaveBridgeV2",
    "MachineV2GeometryJournal", "Ed25519PrivateKey", "swaymsg",
    "import socket", "import subprocess", "exec(", "UPDATE ",
    "INSERT ", "DELETE ", "CREATE TABLE",
):
    check(forbidden not in bridge, "UI bridge has no native writes: " + forbidden)

print("TIMEW M5 WIDGET UI BRIDGE // " + str(checks)
      + " read-only checks PASS; NATIVE RESTORE HOLD")
