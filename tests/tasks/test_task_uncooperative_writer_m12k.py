#!/usr/bin/env python3
"""M12k: test uncooperative same-UID writer against M12h disposable receipts.

This intentionally demonstrates a SECURITY LIMIT, not its solution.
All writes occur in fresh private /tmp/m12k-*/m11e-fileview-test fixtures.
A separate subprocess ignores the cooperative M10p flock; never touch real
TASKS JSON, the user's running Quickshell, or production QML/source.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase, main, mock


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/tasks/fixtures"
MANIFEST = FIXTURES / "task_native_receipt_external_writer_m12k.json"
SPEC = importlib.util.spec_from_file_location(
    "m12k_existing_disposable_receipt",
    FIXTURES / "TaskStageSourceReceiptM12h.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


def seed(counter=0):
    return (json.dumps({
        "fixture": "M11E_SYNTHETIC_ONLY",
        "revision": counter, "counter": counter, "marker": "sample"
    }, separators=(",", ":")) + "\n").encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


# This is purposefully a separate real OS process with the same effective UID.
# It never acquires M10p's "handoff-test.lock". It validates the exact
# temporary path and the synthetic-only source schema before writing.
OUTSIDE_PROCESS = r'''
import json, os, pathlib, stat, sys, uuid
p = pathlib.Path(sys.argv[1])
assert p.is_absolute() and ".." not in p.parts
assert p.name == "fixture-only.json"
assert p.parent.name == "m11e-fileview-test"
assert p.parent.parent.name.startswith("m12k-")
assert p.parent.parent.parent == pathlib.Path("/tmp")
for d in (p.parent.parent, p.parent):
    s = d.lstat()
    assert stat.S_ISDIR(s.st_mode) and not d.is_symlink()
    assert s.st_uid == os.geteuid()
    assert stat.S_IMODE(s.st_mode) == 0o700
s = p.lstat()
assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
assert s.st_uid == os.geteuid() and s.st_nlink == 1
assert stat.S_IMODE(s.st_mode) == 0o600
raw = sys.stdin.buffer.read(2049)
assert 0 < len(raw) <= 2048
doc = json.loads(raw)
assert type(doc) is dict and set(doc) == {"fixture","revision","counter","marker"}
assert doc["fixture"] == "M11E_SYNTHETIC_ONLY" and doc["marker"] == "sample"
assert type(doc["counter"]) is int and 0 <= doc["counter"] <= 1000000
assert doc["revision"] == doc["counter"]
temp = p.parent / (".m12k-uncooperative-" + uuid.uuid4().hex)
fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    with os.fdopen(fd, "wb") as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temp, p)
    dir_fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(dir_fd)
    finally: os.close(dir_fd)
finally:
    if temp.exists(): temp.unlink()
'''


class UncooperativeWriterBoundary(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m12k-", dir="/tmp")
        self.folder = Path(self.tmp.name) / "m11e-fileview-test"
        self.folder.mkdir(mode=0o700)
        self.source = self.folder / "fixture-only.json"
        self.db = self.folder / "handoff-test.db"
        fd = os.open(self.source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(seed(0))
            f.flush()
            os.fsync(f.fileno())

    def tearDown(self):
        self.tmp.cleanup()

    def owner(self):
        return lab.DisposableStageReceipt(
            self.db, "m12k-owned-fixture-0001", bootstrap=True)

    def outsider(self, data):
        proc = subprocess.run(
            [sys.executable, "-B", "-I", "-c",
             OUTSIDE_PROCESS, str(self.source)],
            input=data, capture_output=True, timeout=10, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertEqual(self.source.read_bytes(), data)

    def test_uncooperative_process_can_replace_source_while_owner_holds_flock(self):
        with self.owner() as owner:
            self.assertEqual(owner.snapshot()["phase"], "JSON_ACTIVE")
            self.outsider(seed(9))
            # Flock still lets cooperating authority inspect its own lock.
            self.assertEqual(owner.snapshot()["phase"], "JSON_ACTIVE")
            self.assertEqual(self.source.read_bytes(), seed(9))
            self.assertEqual(owner.snapshot()["receipts"], [])

    def test_unexpected_outside_bytes_before_reservation_are_refused(self):
        with self.owner() as owner:
            self.outsider(seed(7))
            with self.assertRaisesRegex(
                lab.AdmissionError, "EXTERNAL_SOURCE_BEFORE_RESERVE"):
                owner.reserve("m12k-stage-000001")
            self.assertIsNone(owner.snapshot()["pendingStage"])
            self.assertEqual(owner.snapshot()["receipts"], [])

    def test_wrong_outside_bytes_after_reservation_force_durable_review(self):
        with self.owner() as owner:
            r = owner.reserve("m12k-stage-000001")
            self.assertEqual(r["expectedSha256"], sha(seed(1)))
            self.outsider(seed(2))
            result = owner.settle_after_independent_readback(
                r["stageId"], r["epoch"])
            self.assertFalse(result["settled"])
            self.assertEqual(result["status"], "READBACK_REVIEW_REQUIRED")
            snap = owner.snapshot()
            self.assertEqual(snap["phase"], "RECOVERY_REVIEW")
            self.assertEqual(snap["pendingStage"], r["stageId"])
            self.assertEqual(snap["receipts"][0]["receiptState"], "REVIEW_REQUIRED")
            self.assertEqual(snap["receipts"][0]["actualSha256"], sha(seed(2)))

    def test_exact_expected_bytes_from_outsider_can_forge_byte_consistent_receipt(self):
        # Important *negative* finding: this test did not invoke FileView.
        # The bytes match, so the cooperative host settles, without knowing
        # that an untrusted subprocess supplied the content.
        with self.owner() as owner:
            r = owner.reserve("m12k-stage-000001")
            self.outsider(r["payload"])
            result = owner.settle_after_independent_readback(
                r["stageId"], r["epoch"])
            self.assertTrue(result["settled"])
            self.assertFalse(result["independentNativeStageAttributionProven"])
            receipt = owner.snapshot()["receipts"][0]
            self.assertEqual(receipt["receiptState"], "SETTLED_UNACKNOWLEDGED")
            self.assertEqual(receipt["expectedSha256"], receipt["actualSha256"])
            # Thus digest equality does NOT prove WHICH process performed save.
            self.assertEqual(self.source.read_bytes(), seed(1))

    def test_outside_replacement_after_settlement_refused_at_next_reservation(self):
        with self.owner() as owner:
            r = owner.reserve("m12k-stage-000001")
            # Stand-in for a cooperating FileView write in this test only.
            self.outsider(r["payload"])
            self.assertTrue(owner.settle_after_independent_readback(
                r["stageId"], r["epoch"])["settled"])
            self.outsider(seed(8))
            with self.assertRaisesRegex(
                    lab.AdmissionError, "EXTERNAL_SOURCE_BEFORE_RESERVE"):
                owner.reserve("m12k-stage-000002")
            # The existing receipt still describes earlier bytes. Rechecking
            # on NEXT reservation is not continuous post-settlement fencing.
            row = owner.snapshot()["receipts"][0]
            self.assertEqual(row["actualSha256"], sha(seed(1)))
            self.assertNotEqual(row["actualSha256"], sha(self.source.read_bytes()))

    def test_outsider_race_after_final_readback_can_leave_stale_settled_receipt(self):
        # Deterministic TOCTOU injection exactly after the second stable_file
        # read and before the M12h SQLite commit; no production code patched.
        with self.owner() as owner:
            r = owner.reserve("m12k-stage-000001")
            self.outsider(r["payload"])
            real = lab.host.stable_file
            count = [0]

            def read_then_change(path):
                result = real(path)
                count[0] += 1
                if count[0] == 2:
                    self.outsider(seed(9))
                return result

            with mock.patch.object(lab.host, "stable_file",
                                   side_effect=read_then_change):
                settled = owner.settle_after_independent_readback(
                    r["stageId"], r["epoch"])
            self.assertEqual(count[0], 2)
            self.assertTrue(settled["settled"])
            snap = owner.snapshot()
            self.assertEqual(snap["receipts"][0]["receiptState"],
                             "SETTLED_UNACKNOWLEDGED")
            self.assertNotEqual(snap["receipts"][0]["actualSha256"],
                                sha(self.source.read_bytes()))
            # This is a documented production BLOCKER, not a feature pass.
            self.assertFalse(snap["nativeCallbackStageProven"])

    def test_checkpoint_is_redacted_and_all_production_authority_still_open(self):
        record = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(record["milestone"], "M12k")
        m12j = record["nativeCheckpoint"]
        self.assertFalse(m12j["privateFixturePathIncluded"])
        self.assertFalse(m12j["rawScreenshotsIncluded"])
        self.assertEqual(m12j["observedNativeSaveCount"], 2)
        self.assertEqual(m12j["observedSettledReceiptCount"], 2)
        self.assertTrue(all(m12j["sqliteChecks"].values()))
        self.assertFalse(m12j["recovery"]["independentNativeCallbackOriginProven"])
        self.assertTrue(all(value is False
                            for value in record["authority"].values()))
        self.assertTrue(all(value == "OPEN"
                            for value in record["decisionsStillOpen"].values()))
        manifest = MANIFEST.read_text(encoding="utf-8")
        for sensitive in ("pa-m12j-GWX", "/var/home/", "/home/mapple",
                          "PRIVATE_KEY", "m12j-recovery-owner"):
            self.assertNotIn(sensitive, manifest)

    def test_production_store_and_separate_test_path_still_untouched(self):
        production = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        fixture = (FIXTURES / "TaskStageSourceReceiptM12h.py").read_text()
        self.assertIn("readonly property bool guardedWriterEnabled: false",
                      production)
        self.assertEqual(production.count("FileView {"), 1)
        self.assertEqual(production.count("return stage(TodoPolicy."), 9)
        self.assertNotIn("TaskNativeReceiptExternalWriterM12k",
                         shell + production)
        self.assertNotIn("Quickshell.dataDir", fixture)
        self.assertNotIn("apollo-hub-todo-v1.json", fixture)


if __name__ == "__main__":
    main(verbosity=2)
