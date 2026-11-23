#!/usr/bin/env python3
"""TimeW local-first v3 fractional snapshots: disposable SQLite-only tests."""
from dataclasses import replace
import math
import os
from pathlib import Path
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))

from MachineV2ExactLogicalGeometry import (
    PHASE_CURRENT, PHASE_PENDING, capture_value, read_value,
)
from MachineV3LocalExactCaptureStore import (
    DB_NAME, MAX_RECORDS, LocalCaptureRefused, LocalExactCaptureStore,
    SCHEMA_VERSION, suggested_path,
)

CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
WINDOW = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
checks = 0


def check(value, label):
    global checks
    assert value, label
    checks += 1


def reject(call, label):
    global checks
    try:
        call()
    except LocalCaptureRefused:
        checks += 1
    else:
        raise AssertionError(label + " improperly accepted")


def current(**changes):
    rect = {"x": 259.0, "y": 92.5, "width": 1402.0, "height": 872.0}
    rect.update(changes)
    return capture_value(PHASE_CURRENT, **rect)


def save(store, **changes):
    record = {
        "checkpoint_id": CID, "window_key": WINDOW,
        "app_id": "brave", "output_id": "DP-1",
        "workspace_id": "3", "value": current(),
    }
    record.update(changes)
    return store.save(**record)


with tempfile.TemporaryDirectory(prefix="timew-v3-local-ci-") as temp:
    path = Path(temp) / "post-apollo" / "machine" / DB_NAME
    store = LocalExactCaptureStore(path)
    check(store.get(str(uuid.uuid4())) is None, "missing read returns None")
    check(store.for_checkpoint(CID) == [], "missing list is empty")
    check(not path.exists() and not path.parent.exists(),
          "no IO before explicit save")
    check(suggested_path().name == DB_NAME, "suggestion is no write")

    # Initial exact CURRENT save, without modifying the old machine.db.
    captured = save(store)
    check(type(captured) is str and len(captured) == 36,
          "generated local ID")
    check(path.exists(), "separate local DB created")
    check(stat.S_IMODE(path.stat().st_mode) == 0o600, "private DB file")
    check(stat.S_IMODE(path.parent.stat().st_mode) == 0o700, "private machine dir")
    check(stat.S_IMODE(path.parent.parent.stat().st_mode) == 0o700,
          "private post-apollo dir")
    check(not (path.parent / "machine.db").exists(),
          "old v1/v2 SQLite file unaffected")
    check(not (path.parent / "v2-geometry-operations.db").exists(),
          "operation journal unaffected")
    entry = store.get(captured)
    check(entry is not None and entry["id"] == captured,
          "local exact capture available")
    check(entry["checkpoint_id"] == CID and entry["window_key"] == WINDOW,
          "local capture window grouping")
    check(entry["app_id"] == "brave" and entry["workspace_id"] == "3",
          "ordinary layout metadata")
    check(read_value(entry["value"]) == (259, 92.5, 1402, 872),
          "fractional y exactly roundtrips")
    check(entry["value"].phase == PHASE_CURRENT, "CURRENT phase retained")
    for name in (
        "source_authenticated", "operator_selection_verified",
        "production_restore_allowed", "c5_spent_verified",
        "terminal_receipt_verified", "automatic_retry_allowed",
        "automatic_undo_allowed",
    ):
        check(entry[name] is False, "no auth from local save: " + name)
    check(entry["local_capture_only"] is True and entry["safe_actions"] == [],
          "capture only no commands")
    check([x["id"] for x in store.for_checkpoint(CID)] == [captured],
          "list by checkpoint")

    # A fresh process can read exactly the same bits. No app or compositor.
    code = """
import sys
sys.path.insert(0, sys.argv[1])
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore
from MachineV2ExactLogicalGeometry import read_value
item=LocalExactCaptureStore(sys.argv[2]).get(sys.argv[3])
assert read_value(item['value']) == (259.0,92.5,1402.0,872.0)
assert item['production_restore_allowed'] is False
assert item['c5_spent_verified'] is False
"""
    child = subprocess.run(
        [sys.executable, "-B", "-I", "-c", code,
         str(ROOT / "services/time"), str(path), captured],
        timeout=12, capture_output=True, check=False,
    )
    check(child.returncode == 0,
          "reopen from new process " + child.stderr.decode(errors="replace"))

    # Duplicates cannot silently rewrite an existing local snapshot.
    reject(lambda: save(store), "same checkpoint+window immutability")
    check(store.get(captured)["value"] == current(), "duplicate left data intact")
    reject(lambda: save(store, value=capture_value(
        PHASE_PENDING, x=259, y=92.5, width=1402, height=872)),
        "PENDING cannot masquerade as an observed CURRENT capture")
    reject(lambda: save(store, value=replace(current(), version=2)),
           "future value version is not local v3 compatible")
    reject(lambda: save(store, value=replace(current(), y_bits=-1)),
           "raw forged bits refused")
    reject(lambda: save(store, value={"x": 259, "y": 92.5}),
           "dictionary cannot become native evidence")
    reject(lambda: save(store, app_id="brave\nTITLE"),
           "reject title/control injection")
    reject(lambda: save(store, output_id=""), "empty output refused")
    reject(lambda: save(store, app_id="x" * 129), "oversized app id refused")
    reject(lambda: save(store, window_key="not-uuid"), "invalid window ID")
    reject(lambda: save(store, checkpoint_id=WINDOW),
           "wrong checkpoint UUID version")
    reject(lambda: save(store, workspace_id=True), "nonstring workspace refused")
    reject(lambda: save(store, operation_id="forbidden"),
           "refuse injected authorization field")

    # 128 distinct fractional samples are separate local data, not trusted.
    for i in range(128):
        value = current(
            x=259 + i / 8, y=92.5 + i / 16,
            width=1402 + i / 4, height=872 + i / 2,
        )
        ck = str(uuid.uuid4())
        wid = str(uuid.uuid4())
        identifier = save(store, checkpoint_id=ck, window_key=wid, value=value)
        row = store.get(identifier)
        check(row["value"] == value, "fraction exactly preserved " + str(i))
        check(row["production_restore_allowed"] is False
              and row["safe_actions"] == [],
              "local capture no native permissions " + str(i))
    ulu = math.nextafter(92.5, math.inf)
    check(current(y=ulu).y_bits != current().y_bits,
          "single-ULP storage candidate distinct")
    new_capture = save(store, checkpoint_id=str(uuid.uuid4()),
                       window_key=str(uuid.uuid4()), value=current(y=ulu))
    check(store.get(new_capture)["value"].y_bits == current(y=ulu).y_bits,
          "single-ULP persisted without rounding")

    with sqlite3.connect(path) as conn:
        check(conn.execute("PRAGMA user_version").fetchone()[0] ==
              SCHEMA_VERSION, "separate local schema 3")
        check(conn.execute("PRAGMA synchronous").fetchone()[0] == 2,
              "SQLite FULL synchronous")
        columns = [x[1] for x in conn.execute(
            "PRAGMA table_info(exact_captures)")]
        check("x_bits" in columns and "y_bits" in columns,
              "hex bit fields in local-only schema")
        for forbidden in (
            "consent", "grant", "spend", "permission", "secret",
            "signer", "browser_url", "title", "command", "receipt",
        ):
            check(forbidden not in columns, "no authority field: " + forbidden)
        stored = conn.execute(
            "SELECT y_bits FROM exact_captures WHERE id=?", (captured,)
        ).fetchone()[0]
        check(stored == format(current().y_bits, "016x"),
              "local-only bit storage exact")
    check(len(store.for_checkpoint(CID)) == 1, "separate scope checked")

    # Strict POSIX file/dir ownership and format validation. Disposable only.
    os.chmod(path, 0o644)
    reject(lambda: store.get(captured), "world-readable file")
    os.chmod(path, 0o600)
    os.chmod(path.parent, 0o755)
    reject(lambda: store.get(captured), "world-readable parent")
    os.chmod(path.parent, 0o700)
    os.chmod(path.parent.parent, 0o755)
    reject(lambda: store.get(captured), "world-readable post-apollo dir")
    os.chmod(path.parent.parent, 0o700)

    badbase = Path(temp) / "linked" / "post-apollo" / "machine"
    badbase.mkdir(parents=True, mode=0o700)
    linked_file = badbase / DB_NAME
    linked_file.symlink_to(path)
    reject(lambda: LocalExactCaptureStore(linked_file).get(captured),
           "symlinked DB cannot be read")
    linked_file.unlink()
    os.link(path, linked_file)
    reject(lambda: LocalExactCaptureStore(linked_file).get(captured),
           "hardlink cannot be read")
    linked_file.unlink()

    symlinked_parent = Path(temp) / "parent-link" / "post-apollo"
    symlinked_parent.parent.mkdir(mode=0o700)
    symlinked_parent.symlink_to(path.parent.parent, target_is_directory=True)
    reject(lambda: LocalExactCaptureStore(
        symlinked_parent / "machine" / DB_NAME).get(captured),
        "symlinked parent denied")

    reject(lambda: LocalExactCaptureStore("/tmp/foreign.db"),
           "path must be dedicated v3 basename")
    reject(lambda: LocalExactCaptureStore("post-apollo/machine/" + DB_NAME),
           "relative path denied")

    # A future schema or tampered value must refuse; no silent migration.
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=4")
    reject(lambda: store.get(captured), "future schema rejected")
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=3")
        conn.execute("UPDATE exact_captures SET y_bits=? WHERE id=?",
                     ("ffffffffffffffff", captured))
    reject(lambda: store.get(captured), "forged NaN bits rejected")
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE exact_captures SET y_bits=? WHERE id=?",
                     (format(current().y_bits, "016x"), captured))
        conn.execute("UPDATE exact_captures SET x_bits=? WHERE id=?",
                     ("not-a-hex-bit-pattern", captured))
    reject(lambda: store.get(captured), "malformed local bit field rejected")

# Source isolation: no live runtime, older persistence or guarded restore
# imports the new dormant local-only module.
candidate = (ROOT / "services/time/MachineV3LocalExactCaptureStore.py").read_text()
for forbidden in ("import subprocess", "import socket", "swaymsg",
                  "command_runner", "Ed25519PrivateKey", "def main(",
                  'if __name__', "native_restore(", "C5_SPENT_REPORTED"):
    check(forbidden not in candidate,
          "privileged symbol cannot occur in dormant store: " + forbidden)
for old in (
    "widgets/TimeW.qml",
    "services/time/MachineCheckpointStore.py",
    "services/time/MachineGeometryStoreV2.py",
    "services/time/MachineV2GeometryJournal.py",
    "services/time/MachineV2FloatingPilot.py",
    "services/time/MachineV2FractionalObservationReview.py",
):
    check("MachineV3LocalExactCaptureStore" not in (ROOT / old).read_text(),
          "no existing runtime imports local v3: " + old)

print("TIMEW LOCAL-FIRST EXACT CAPTURE // " + str(checks) +
      " isolated checks PASS; LOCAL DATA, NOT C5 CONSENT OR NATIVE RESTORE")
