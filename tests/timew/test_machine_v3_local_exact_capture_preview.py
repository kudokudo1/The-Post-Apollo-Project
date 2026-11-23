#!/usr/bin/env python3
"""TimeW M4 read-only local capture preview; disposable data-only regression."""
from __future__ import annotations

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

from MachineV2ExactLogicalGeometry import (
    PHASE_CURRENT, PHASE_PENDING, capture_value,
)
from MachineV3LocalExactCaptureStore import (
    DB_NAME, LocalExactCaptureStore,
)
from MachineV3LocalExactCapturePreview import (
    KIND, PreviewRefused, _render_entry, main, preview, unavailable,
)

CHECKPOINT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
checks = 0


def check(condition, name):
    global checks
    assert condition, name
    checks += 1


def refused(func, name):
    global checks
    try:
        func()
    except PreviewRefused:
        checks += 1
    else:
        raise AssertionError("accepted " + name)


def assert_hold(result):
    check(result["kind"] == KIND, "preview kind")
    check(result["read_only"] is True, "read-only")
    check(result["data_origin"] == "CALLER_SUPPLIED_LOCAL_UNTRUSTED",
          "untrusted local origin")
    check(type(result["entries"]) is list, "entries")
    check(result["count"] == len(result["entries"]), "count")
    check(result["safe_actions"] == [], "no native action list")
    for name in (
        "source_authenticated", "operator_selection_verified",
        "c5_spent_verified", "native_receipt_verified",
        "exact_restore_verified", "restore_allowed",
        "native_action_allowed", "retry_allowed", "undo_allowed",
    ):
        check(result[name] is False, "authority denied " + name)
    for entry in result["entries"]:
        check(entry["local_data_untrusted"] is True, "entry untrusted")
        check(entry["selected_window_identity_verified"] is False,
              "no selected native identity")
        check(entry["source_authenticated"] is False, "entry source denied")
        check(entry["settled_frame_verified"] is False, "no settled frame")
        check(entry["action_allowed"] is False, "no move/resize")
        check(entry["observed_phase"] == "CURRENT_VALUE_ONLY",
              "CURRENT is not a native receipt")


def exact(*, y=92.5):
    return capture_value(
        PHASE_CURRENT, x=259.0, y=y, width=1402.0, height=872.0)


def call(db, checkpoint, *args):
    return subprocess.run(
        [sys.executable, "-B", "-I", str(SERVICE / "MachineV3LocalExactCapturePreview.py"),
         "preview", str(db), checkpoint, *args],
        capture_output=True, timeout=12, check=False, text=True,
    )


with tempfile.TemporaryDirectory(prefix="timew-m4-preview-") as folder:
    root = Path(folder)
    db = root / "post-apollo" / "machine" / DB_NAME
    store = LocalExactCaptureStore(db)

    # A read-only preview cannot cause the first write, even if the DB
    # does not exist yet. Both programmatic and CLI paths are scoped.
    empty = preview(CHECKPOINT, store=store)
    assert_hold(empty)
    check(empty["status"] == "NO_LOCAL_CAPTURES", "empty status")
    check(empty["checkpoint_id"] == CHECKPOINT, "empty checkpoint")
    check(not db.exists(), "pure missing-db read")
    child = call(db, CHECKPOINT)
    check(child.returncode == 0, "missing DB is not a bad request")
    check(json.loads(child.stdout)["status"] == "NO_LOCAL_CAPTURES",
          "missing DB CLI status")
    check(not db.exists(), "missing CLI does not create DB")
    check(not db.parent.exists(), "missing CLI creates no directory")

    one = store.save(
        checkpoint_id=CHECKPOINT,
        window_key=str(uuid.uuid4()),
        app_id="brave", output_id="DP-1", workspace_id="2",
        value=exact(),
    )
    second_y = math.nextafter(92.5, math.inf)
    two = store.save(
        checkpoint_id=CHECKPOINT,
        window_key=str(uuid.uuid4()),
        app_id="kitty", output_id="HDMI-A-1", workspace_id="3",
        value=exact(y=second_y),
    )
    other = store.save(
        checkpoint_id=OTHER,
        window_key=str(uuid.uuid4()),
        app_id="unrelated", output_id="DP-2", workspace_id="private",
        value=exact(y=101.25),
    )
    stat_before = db.stat()
    output = preview(CHECKPOINT, store=store)
    assert_hold(output)
    check(output["status"] == "LOCAL_CAPTURES_UNTRUSTED_HOLD",
          "nonempty remains HOLD")
    check(output["count"] == 2, "scoped count")
    check({x["capture_id"] for x in output["entries"]} == {one, two},
          "only requested checkpoint entries")
    check(all(x["app_id"] != "unrelated" for x in output["entries"]),
          "other checkpoint private data not exposed")
    check(all(x["checkpoint_window_key"] != other
              for x in output["entries"]), "no external capture ID")
    check(len({x["checkpoint_window_key"] for x in output["entries"]}) == 2,
          "two distinct window labels")
    check(all("url" not in x and "title" not in x
              for x in output["entries"]), "no browsing contents")
    by_app = {x["app_id"]: x for x in output["entries"]}
    check(by_app["brave"]["geometry"]["y"]["decimal"] == "92.5",
          "human readable fractional decimal")
    check(by_app["brave"]["geometry"]["y"]["binary64_hex"] ==
          (92.5).hex(), "bit exact hex floating-point view")
    check(by_app["kitty"]["geometry"]["y"]["binary64_hex"] ==
          second_y.hex(), "one-ULP survives preview")
    check(by_app["brave"]["geometry"]["y"]["binary64_hex"] !=
          by_app["kitty"]["geometry"]["y"]["binary64_hex"],
          "one-ULP not rounded")
    check(set(by_app["brave"]["geometry"]) == {"x", "y", "width", "height"},
          "geometry has exactly four axes")
    check(set(by_app["brave"]["geometry"]["x"]) ==
          {"decimal", "binary64_hex"}, "exact preview fields")

    cli = call(db, CHECKPOINT)
    check(cli.returncode == 0, "CLI invocation success")
    check(cli.stderr == "", "no debug or private path in stderr")
    from_cli = json.loads(cli.stdout)
    check(from_cli == output, "child CLI equals API snapshot")
    assert_hold(from_cli)
    check(db.stat().st_size == stat_before.st_size,
          "preview does not enlarge DB")
    check(db.stat().st_mtime_ns == stat_before.st_mtime_ns,
          "preview does not modify DB")

    # Revalidate all imported v3 flags, not only the geometry bits.
    trusted_looking = store.for_checkpoint(CHECKPOINT)[0]
    for flag in ("source_authenticated", "operator_selection_verified",
                 "c5_spent_verified", "terminal_receipt_verified",
                 "production_restore_allowed", "automatic_retry_allowed",
                 "automatic_undo_allowed"):
        forged = dict(trusted_looking, **{flag: True})
        refused(lambda forged=forged: _render_entry(forged, CHECKPOINT),
                "forged authority " + flag)
    refused(lambda: _render_entry(
        dict(trusted_looking, safe_actions=["move"]), CHECKPOINT),
        "forged safe action")
    refused(lambda: _render_entry(
        dict(trusted_looking, local_capture_only=False), CHECKPOINT),
        "forged local-only flag")
    refused(lambda: _render_entry(
        dict(trusted_looking, checkpoint_id=OTHER), CHECKPOINT),
        "cross-checkpoint item")
    refused(lambda: _render_entry(
        dict(trusted_looking, permission="yes"), CHECKPOINT),
        "additional schema field")
    refused(lambda: _render_entry(
        dict(trusted_looking, value=replace(exact(), phase=PHASE_PENDING)),
        CHECKPOINT), "PENDING not CURRENT")
    refused(lambda: _render_entry(
        dict(trusted_looking, value=replace(exact(), y_bits=-1)),
        CHECKPOINT), "forged bits")
    refused(lambda: preview(CHECKPOINT, store=None), "no fake reader")
    for invalid in (OTHER.upper(), "not-uuid", "", 42, None, True):
        refused(lambda invalid=invalid: preview(invalid, store=store),
                "invalid checkpoint")
    different = preview(OTHER, store=store)
    assert_hold(different)
    check(different["count"] == 1 and
          different["entries"][0]["app_id"] == "unrelated",
          "other checkpoint only by exact request")

    # Bad CLI arguments/unsupported enumeration are fixed generic refusals,
    # never a traceback, native command, or a silent fallback to XDG path.
    requests = (
        ["restore", str(db), CHECKPOINT],
        ["preview", str(db)],
        ["preview", str(db), "not-uuid"],
        ["preview", str(db), CHECKPOINT, "--write"],
        ["preview", "--all", CHECKPOINT],
    )
    for args in requests:
        rejected = subprocess.run(
            [sys.executable, "-B", "-I",
             str(SERVICE / "MachineV3LocalExactCapturePreview.py"), *args],
            capture_output=True, text=True, timeout=12, check=False)
        check(rejected.returncode == 1, "bad argument denied")
        refusal = json.loads(rejected.stdout)
        assert_hold(refusal)
        check(refusal["status"] == "UNAVAILABLE_HOLD" and
              refusal["checkpoint_id"] is None, "fixed generic error")
        check(str(db) not in rejected.stdout + rejected.stderr,
              "no path leak")
    check(unavailable()["status"] == "UNAVAILABLE_HOLD",
          "unavailable always HOLD")

    # Tampered local DB: old same-UID attacker may swap *valid* bit values,
    # so the preview must remain explicitly untrusted even when readable.
    with sqlite3.connect(db) as sql:
        sql.execute("UPDATE exact_captures SET y_bits=? WHERE id=?",
                    (format(exact(y=101.25).y_bits, "016x"), one))
    changed = preview(CHECKPOINT, store=store)
    assert_hold(changed)
    check(next(x for x in changed["entries"]
               if x["capture_id"] == one)["geometry"]["y"]["decimal"] ==
          "101.25", "valid tampering is readable but NOT detected")
    check(changed["status"] == "LOCAL_CAPTURES_UNTRUSTED_HOLD",
          "no integrity claim")

    with sqlite3.connect(db) as sql:
        sql.execute("UPDATE exact_captures SET y_bits='bad' WHERE id=?",
                    (one,))
    failed = call(db, CHECKPOINT)
    check(failed.returncode == 1, "invalid record refuses preview")
    refusal = json.loads(failed.stdout)
    assert_hold(refusal)
    check(refusal["status"] == "UNAVAILABLE_HOLD",
          "invalid stored geometry does not leak partial snapshot")
    check(refusal["entries"] == [] and
          str(db) not in failed.stdout + failed.stderr,
          "no partial rows or path leak")

# Static separation: no live desktop, old journal, C5 or other owners' files.
source = (SERVICE / "MachineV3LocalExactCapturePreview.py").read_text()
for forbidden in (
    "swaymsg", "import subprocess", "import socket", "import requests",
    "import sqlite3 as write", "Ed25519PrivateKey", "native_restore(",
    "MachineRestoreCheckpoint", "C5_SPENT_REPORTED", "os.environ",
    "suggested_path(", "websocket", "QProcess", "CREATE TABLE",
    "UPDATE exact_captures",
):
    check(forbidden not in source, "no command path: " + forbidden)
for existing in (
    "widgets/TimeW.qml",
    "services/time/MachineV3LocalExactCaptureStore.py",
    "services/time/MachineCheckpointStore.py",
    "services/time/MachineGeometryStoreV2.py",
    "services/time/MachineV2GeometryJournal.py",
    "services/time/MachineRestoreReviewV2.py",
):
    check("MachineV3LocalExactCapturePreview" not in
          (ROOT / existing).read_text(),
          "existing module remains unmodified/unlinked: " + existing)

print("TIMEW M4 LOCAL EXACT PREVIEW // "
      + str(checks) + " read-only checks PASS; "
      "NO SAVE, C5 CONSENT, NATIVE RESTORE OR TRUSTED RECEIPT")
