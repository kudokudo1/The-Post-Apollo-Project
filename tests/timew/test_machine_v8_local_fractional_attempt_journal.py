#!/usr/bin/env python3
"""M8: actual disposable SQLite attempt custody and abrupt child exit."""
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "time"
sys.path.insert(0, str(SERVICE))
import MachineCheckpointStore as legacy
from MachineGeometryStoreV2 import save_pair, load_geometry
from MachineGeometryV2 import project_geometry
from MachineV2ExactLogicalGeometry import PHASE_CURRENT, PHASE_PENDING, capture_value
from MachineV3LocalExactCaptureStore import DB_NAME as CAPTURE_DB, LocalExactCaptureStore
from MachineV3LocalCheckpointAdmission import admit_checkpoint
from MachineV3LocalSaveRecovery import prepare_binding
from MachineV3LocalFractionalAttemptJournal import (
    DB_NAME, PREPARED, MARKED, MAX_ATTEMPTS, AttemptRefused,
    LocalFractionalAttemptJournal, suggested_path,
)

checks = 0

def check(ok, label):
    global checks
    assert ok, label
    checks += 1

def reject(fn, label):
    global checks
    try:
        fn()
    except AttemptRefused as exc:
        assert str(exc) == "TIMEW LOCAL FRACTIONAL ATTEMPT REFUSED"
        checks += 1
    else:
        raise AssertionError("accepted: " + label)

def rect(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


KEYS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
)


def leaf(ident, app, rectangle):
    return {
        "type": "con", "id": ident, "app_id": app,
        "rect": rectangle, "percent": 0.5, "layout": "none",
        "floating": "auto_off", "nodes": [], "floating_nodes": [],
        "window_rect": None, "deco_rect": None, "geometry": None,
        "fullscreen_mode": 0, "title": "DO NOT STORE PRIVATE TITLE",
        "pid": 999,
    }


def fixture():
    outputs = [{
        "name": "DP-1", "active": True, "rect": rect(0, 0, 2560, 1440),
        "scale": 1.0, "transform": "normal",
    }]
    workspaces = [{"name": "1", "output": "DP-1"}]
    tree = {"type": "root", "nodes": [{
        "type": "output", "name": "DP-1", "nodes": [{
            "type": "workspace", "name": "1", "layout": "splith",
            "rect": rect(0, 0, 2560, 1440),
            "nodes": [
                leaf(101, "brave", rect(0, 0, 1280, 1440)),
                leaf(102, "kitty", rect(1280, 0, 1280, 1440)),
            ],
            "floating_nodes": [],
        }],
    }]}
    geo = project_geometry(
        outputs, workspaces, tree,
        window_keys={101: KEYS[0], 102: KEYS[1]},
    )
    old = {
        "schema_version": 1,
        "kind": "sway-layout-selection-preview",
        "preview_only": True,
        "label": "M6 local batch",
        "captured_at_utc": "2026-11-23T19:00:00+00:00",
        "outputs": [
            {"connector": x["connector"], "rect": x["rect"]}
            for x in geo["outputs"]],
        "workspaces": [
            {"name": x["name"], "output": x["output"]}
            for x in geo["workspaces"]],
        "windows": [
            {"app_id": x["app_id"], "workspace": x["workspace"],
             "floating": x["floating"]}
            for x in geo["windows"]],
    }
    return old, geo


def candidate(window, *, y=92.5):
    return {
        "window_key": window["window_key"],
        "app_id": window["app_id"],
        "output_id": window["output"],
        "workspace_id": window["workspace"],
        "value": capture_value(
            PHASE_CURRENT, x=259.125, y=y, width=1402.5, height=872.25),
    }




# Deliberately terminate without normal Python shutdown, after the committed
# prepare or marker call. The first child never returns its attempt ID.
CHILD = """
import os, sys, math
sys.path.insert(0, sys.argv[1])
from MachineV3LocalFractionalAttemptJournal import LocalFractionalAttemptJournal, suggested_path
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore, suggested_path as capture_path
from MachineGeometryStoreV2 import load_geometry
from MachineV2ExactLogicalGeometry import capture_value, PHASE_CURRENT
from MachineV3LocalCheckpointAdmission import admit_checkpoint
journal = LocalFractionalAttemptJournal(suggested_path())
store = LocalExactCaptureStore(capture_path())
mode, key = sys.argv[2:4]
if mode == "prepare":
    windows = load_geometry(key)["geometry"]["windows"]
    obs = []
    for i, w in enumerate(windows):
        obs.append(dict(window_key=w["window_key"], app_id=w["app_id"],
                        output_id=w["output"], workspace_id=w["workspace"],
                        value=capture_value(PHASE_CURRENT, x=259.125,
                          y=92.5 if i == 0 else math.nextafter(92.5, math.inf),
                          width=1402.5,height=872.25)))
    journal.prepare(checkpoint_id=key, observations=obs, store=store)
elif mode == "mark":
    journal.record_dispatch_marker(key, store=store)
elif mode == "commit":
    attempt = journal.get(key)
    admit_checkpoint(checkpoint_id=attempt.binding.checkpoint_id,
                     observations=attempt.observations(), store=store)
else:
    raise AssertionError("bad test mode")
os._exit(73)
"""

with tempfile.TemporaryDirectory(prefix="timew-m8-attempt-") as temp:
    prior = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = temp
    try:
        parent = Path(temp) / "post-apollo"
        parent.mkdir(mode=0o700)
        old, geo = fixture()
        journal = LocalFractionalAttemptJournal(suggested_path())
        path = journal.path
        store = LocalExactCaptureStore(path.parent / CAPTURE_DB)
        exact = [candidate(geo["windows"][0]),
                 candidate(geo["windows"][1], y=math.nextafter(92.5, math.inf))]
        def new():
            return save_pair(old, geo)["checkpoint"]["id"]

        def prepare(cid, obs=exact):
            return journal.prepare(checkpoint_id=cid, observations=obs, store=store)

        def child(mode, key):
            result = subprocess.run([sys.executable, "-B", "-I", "-c", CHILD,
                                     str(SERVICE), mode, key],
                                    capture_output=True, timeout=30)
            check(result.returncode == 73, repr(result.stderr))

        def recover(aid, phase, status):
            result = journal.recover(aid, store=store)
            check(result["journal_phase"] == phase and result["status"] == status,
                  repr(result))
            check(result["attempt_id"] == aid, "retained attempt id")
            check(result["read_only"] and result["manual_review_required"],
                  "read only hold")
            for flag in ("save_attempt_verified", "dispatch_execution_verified",
                         "source_authenticated", "operator_selection_verified",
                         "cross_database_atomic", "c5_spent_verified",
                         "native_receipt_verified", "production_restore_allowed",
                         "automatic_retry_allowed", "automatic_undo_allowed"):
                check(result[flag] is False, "deny " + flag)
            check(result["safe_actions"] == [], "no action")
            return result

        cid = new()
        missing = str(uuid.uuid4())
        check(journal.get(missing) is None and journal.list_ids() == [],
              "absent read")
        reject(lambda: journal.record_dispatch_marker(missing, store=store),
               "missing marker")
        reject(lambda: journal.recover(missing, store=store), "missing recovery")
        reject(lambda: prepare(cid, exact[:1]), "incomplete original set")
        reject(lambda: prepare(cid, [dict(exact[0], grant=True), exact[1]]),
               "extra authority")
        check(not path.exists() and not store.path.exists(),
              "no files created by refused preparation or absent reads")
        old_pair = legacy.load(cid), load_geometry(cid)

        # Lost prepare reply: reopen journal and discover its retained UUID.
        child("prepare", cid)
        ids = journal.list_ids()
        check(len(ids) == 1, "lost prepare response recovered")
        aid = ids[0]
        attempt = journal.get(aid)
        check(attempt.phase == PREPARED, "prepared only")
        check(attempt.binding == prepare_binding(checkpoint_id=cid, observations=exact),
              "original M7 binding")
        check(attempt.observations() == exact, "all original exact bits restored")
        edited = attempt.observations()
        edited[0]["app_id"] = "changed"
        check(attempt.observations() == exact, "retained tuple not mutated")
        check(path.stat().st_mode & 0o077 == 0, "private file")
        check(not store.path.exists(), "preparation does not write v3")
        recover(aid, PREPARED, "LEGACY_MATCH_LOCAL_EXACT_ABSENT")
        reject(lambda: prepare(cid), "one attempt per checkpoint")
        check(journal.list_ids() == ids, "duplicate no new attempt")

        # Crash after the marker but before any M6 operation.
        child("mark", aid)
        check(journal.get(aid).phase == MARKED, "durable dispatch marker")
        check(journal.get(aid).binding == attempt.binding, "binding immutable")
        recover(aid, MARKED, "LEGACY_MATCH_LOCAL_EXACT_ABSENT")
        reject(lambda: journal.record_dispatch_marker(aid, store=store),
               "no repeat marker after loss")
        check(not store.path.exists(), "marker did not dispatch")
        reject(lambda: prepare(cid), "no second attempt after marker")

        # Explicit test-only M6 dispatch, then loss of the successful response.
        child("commit", aid)
        before = path.read_bytes(), store.path.read_bytes()
        recover(aid, MARKED, "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED")
        recover(aid, MARKED, "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED")
        check((path.read_bytes(), store.path.read_bytes()) == before,
              "recovery makes no writes")
        check((legacy.load(cid), load_geometry(cid)) == old_pair,
              "legacy pair unchanged")
        check(len(store.for_checkpoint(cid)) == 2, "no duplicate fractional rows")
        reject(lambda: prepare(cid), "no overwrite after observed matching write")

        # A competing writer can prepopulate v3; never treat it as our dispatch.
        other = new()
        other_aid = prepare(other)
        admit_checkpoint(checkpoint_id=other, observations=exact, store=store)
        reject(lambda: journal.record_dispatch_marker(other_aid, store=store),
               "already existing matching records do not permit mark")
        recover(other_aid, PREPARED, "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED")

        # Changed checkpoint before marker is held.
        stale = new()
        stale_aid = prepare(stale)
        with sqlite3.connect(legacy.db_path()) as conn:
            conn.execute("UPDATE checkpoints SET label=? WHERE id=?", ("changed", stale))
        reject(lambda: journal.record_dispatch_marker(stale_aid, store=store),
               "changed checkpoint cannot mark")
        check(journal.get(stale_aid).phase == PREPARED, "stale stays prepared")
        recover(stale_aid, PREPARED, "LOCAL_SAVE_OUTCOME_UNKNOWN_HOLD")

        # A partial external local write is a conflict, never an auto repair.
        partial = new()
        partial_aid = prepare(partial)
        store.save(checkpoint_id=partial, **exact[0])
        recover(partial_aid, PREPARED, "LOCAL_EXACT_CONFLICT_HOLD")
        reject(lambda: journal.record_dispatch_marker(partial_aid, store=store),
               "partial local rows prevent mark")

        # Reject accidental cross-context usage and unsafe journal permissions.
        alternate = LocalExactCaptureStore(Path(temp) / "other" / "post-apollo" /
                                          "machine" / CAPTURE_DB)
        reject(lambda: journal.recover(aid, store=alternate), "different store root")
        reject(lambda: LocalFractionalAttemptJournal(path.with_name("other.db")),
               "wrong file")
        path.chmod(0o644)
        reject(lambda: journal.get(aid), "unsafe mode")
        reject(lambda: journal.prepare(checkpoint_id=new(), observations=exact, store=store),
               "no automatic permission repair")
        check(path.stat().st_mode & 0o077 != 0, "refusal preserves permissions")
        path.chmod(0o600)

        # Schema and stored-content integrity checks (ordinary local checks).
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE unexpected (value TEXT)")
        reject(lambda: journal.get(aid), "unknown schema object")
        with sqlite3.connect(path) as conn:
            conn.execute("DROP TABLE unexpected")
            original = conn.execute("SELECT payload,payload_sha256 FROM attempts WHERE id=?",
                                    (aid,)).fetchone()
            conn.execute("UPDATE attempts SET payload=? WHERE id=?", ("{}", aid))
        reject(lambda: journal.get(aid), "corrupt payload")
        with sqlite3.connect(path) as conn:
            conn.execute("UPDATE attempts SET payload=?,payload_sha256=? WHERE id=?",
                         (*original, aid))
        recover(aid, MARKED, "BOTH_LOCAL_RECORDS_OBSERVED_UNTRUSTED")
        check(journal.get(aid).observations() == exact, "original values retained")
        check(len(journal.list_ids()) == 4, "no extra attempt from failed paths")

        # Bounded append-only ledger. No silent eviction.
        for _ in range(MAX_ATTEMPTS - 4):
            prepare(new())
        check(len(journal.list_ids()) == MAX_ATTEMPTS, "journal capacity")
        reject(lambda: prepare(new()), "capacity refusal")
        check(len(journal.list_ids()) == MAX_ATTEMPTS, "no eviction")
        check(journal.get(aid).phase == MARKED, "original survives capacity")
    finally:
        if prior is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = prior

src = (SERVICE / "MachineV3LocalFractionalAttemptJournal.py").read_text()
for forbidden in ("save_pair(", "save_many(", "admit_checkpoint(", "swaymsg",
                  "import subprocess", "import socket", "def main(", "exec("):
    check(forbidden not in src, "no writer/dispatch path: " + forbidden)
for p in (ROOT / "widgets/TimeW.qml", SERVICE / "MachineSaveBridgeV2.py"):
    check("MachineV3LocalFractionalAttemptJournal" not in p.read_text(),
          "no active UI or Save integration")
print("TIMEW M8 LOCAL FRACTIONAL ATTEMPT JOURNAL // " + str(checks)
      + " durability and deny-only checks PASS")
