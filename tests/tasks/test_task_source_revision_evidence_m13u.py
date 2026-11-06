#!/usr/bin/env python3
"""M13u real disposable SQLite and filesystem revision evidence integration.

Only test-owned /tmp/m13u-* directories; no Fedora TASKS file, keyring or QML.
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
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/tasks/fixtures"
spec = importlib.util.spec_from_file_location(
    "m13u_probe_test", FIXTURES / "TaskSourceRevisionEvidenceM13u.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def seed(revision=0):
    return (json.dumps({
        "fixture": "M11E_SYNTHETIC_ONLY",
        "revision": revision,
        "counter": revision,
        "marker": "sample",
    }, separators=(",", ":")) + "\n").encode("utf8")


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m13u-")
        self.base = Path(self.temp.name)
        self.folder = self.base / "m11e-fileview-test"
        self.folder.mkdir(mode=0o700)
        self.db = self.folder / "handoff-test.db"
        self.source = self.folder / "fixture-only.json"
        fd = os.open(self.source, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(seed())
            out.flush()
            os.fsync(out.fileno())
        self.owner_id = "m13u-disposable-owner-0001"

    def tearDown(self):
        self.temp.cleanup()

    def new_owner(self, *, bootstrap=False, owner_id=None):
        return probe._m12h.DisposableStageReceipt(
            self.db, owner_id or self.owner_id, bootstrap=bootstrap)

    def replace(self, content):
        # Simulate FileView atomic replacement ONLY inside disposable test.
        tmp = self.folder / (".m13u-temp-" + uuid.uuid4().hex)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, self.source)
        dfd = os.open(self.folder, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def commit(self, owner, index):
        proposed = owner.reserve(f"m13u-stage-{index:06d}")
        self.replace(proposed["payload"])
        accepted = owner.settle_after_independent_readback(
            proposed["stageId"], proposed["epoch"])
        self.assertTrue(accepted["settled"])
        return accepted

    def assert_no_authority(self, result):
        for name, enabled in probe.NO_POWER.items():
            self.assertIs(enabled, False, name)
            self.assertIs(result[name], False, name)
        self.assertNotIn("payload", result)
        self.assertNotIn("draft", result)
        self.assertNotIn("key", result)

    def test_bootstrap_without_settlement_never_invents_revision_zero(self):
        with self.new_owner(bootstrap=True) as owner:
            result = probe.inspect(owner)
            self.assertEqual(result["status"], "NO_DURABLE_SETTLED_REVISION")
            self.assert_no_authority(result)

    def test_monotonic_receipt_with_two_commits_and_stale_cas(self):
        with self.new_owner(bootstrap=True) as owner:
            self.commit(owner, 1)
            first = probe.inspect(owner)
            self.assertEqual(
                first["status"], "SYNTHETIC_CURRENT_SOURCE_REVISION_OBSERVED")
            self.assertEqual(first["receipt"]["revision"], 1)
            self.assertEqual(first["receipt"]["sourceSha256"],
                             hashlib.sha256(seed(1)).hexdigest())
            self.assert_no_authority(first)
            self.commit(owner, 2)
            latest = probe.inspect(owner)
            self.assertEqual(latest["receipt"]["revision"], 2)
            self.assertEqual(latest["receipt"]["sourceSha256"],
                             hashlib.sha256(seed(2)).hexdigest())
            self.assertEqual(
                probe.inspect(owner, first["receipt"])["status"],
                "STALE_REVISION_OR_OWNER_EPOCH")
            self.assertEqual(
                probe.inspect(owner, latest["receipt"])["status"],
                "SYNTHETIC_CURRENT_SOURCE_REVISION_OBSERVED")
            self.assert_no_authority(latest)

    def test_external_rollback_or_outside_edit_refuses_even_when_json_valid(self):
        with self.new_owner(bootstrap=True) as owner:
            self.commit(owner, 1)
            self.commit(owner, 2)
            current = probe.inspect(owner)["receipt"]
            self.replace(seed(1))  # valid older source, stale journal generation
            bad = probe.inspect(owner, current)
            self.assertEqual(bad["status"], "SOURCE_JOURNAL_REVISION_MISMATCH")
            self.assert_no_authority(bad)
            self.replace(seed(2))
            self.assertEqual(probe.inspect(owner, current)["sourceMatched"], True)
            # A same-UID outsider could still change bytes AFTER this check.

    def test_unsettled_or_uncertain_stage_never_reports_current(self):
        with self.new_owner(bootstrap=True) as owner:
            self.commit(owner, 1)
            proposed = owner.reserve("m13u-stage-000002")
            self.assertEqual(
                probe.inspect(owner)["status"], "UNSETTLED_STAGE_REVIEW_REQUIRED")
            self.assertEqual(owner.snapshot()["pendingStage"], proposed["stageId"])

    def test_tampered_chain_missing_file_or_unsafe_symlink_refuse(self):
        with self.new_owner(bootstrap=True) as owner:
            self.commit(owner, 1)
            self.commit(owner, 2)
            con = owner.owner._guard()
            con.execute(
                "UPDATE stage_receipts_m12h SET baseline_sha256=? WHERE stage_id=?",
                ("0"*64, "m13u-stage-000002"))
            self.assertEqual(probe.inspect(owner)["status"], "JOURNAL_CHAIN_INVALID")
            con.execute(
                "UPDATE stage_receipts_m12h SET baseline_sha256=? WHERE stage_id=?",
                (hashlib.sha256(seed(1)).hexdigest(), "m13u-stage-000002"))
            self.source.unlink()
            self.assertEqual(
                probe.inspect(owner)["status"], "SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")
            self.source.symlink_to(self.folder / "missing-file")
            self.assertEqual(
                probe.inspect(owner)["status"], "SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE")

    def test_forged_or_wrong_epoch_pin_is_refused(self):
        with self.new_owner(bootstrap=True) as owner:
            self.commit(owner, 1)
            pin = probe.inspect(owner)["receipt"]
            for forged in (
                {"revision":1},
                {**pin, "scope":"tasks.draft.preview.unlocked"},
                {**pin, "revision":True},
                {**pin, "sourceSha256":"not-a-sha"},
                {**pin, "ownerEpoch": pin["ownerEpoch"]+1},
                {**pin, "stageId":"m13u-stage-999999"},
            ):
                result=probe.inspect(owner,forged)
                self.assertNotEqual(
                    result["status"], "SYNTHETIC_CURRENT_SOURCE_REVISION_OBSERVED")
                self.assert_no_authority(result)
            self.assertEqual(
                probe.inspect(object())["status"],
                "REFUSED_NOT_EXISTING_DISPOSABLE_OWNER")

    def test_fresh_process_sees_history_but_requires_review(self):
        with self.new_owner(bootstrap=True) as owner:
            self.commit(owner,1)
        # Real independent interpreter reload, not the same Python instance.
        runner = r'''
import importlib.util, json, pathlib, sys
path=pathlib.Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("m13u_new_process",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with module._m12h.DisposableStageReceipt(
    pathlib.Path(sys.argv[2]),"m13u-fresh-owner-00002",bootstrap=False
) as owner:
    print(json.dumps(module.inspect(owner),sort_keys=True))
'''
        child = subprocess.run(
            [sys.executable, "-B", "-I", "-c", runner,
             str(FIXTURES / "TaskSourceRevisionEvidenceM13u.py"), str(self.db)],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(child.returncode,0,child.stderr)
        result=json.loads(child.stdout)
        self.assertEqual(result["status"],"OWNER_REVIEW_REQUIRED")
        self.assertEqual(result["lastObservedRevision"],1)
        self.assertNotIn("receipt",result)
        self.assert_no_authority(result)

    def test_production_writer_and_broker_untouched(self):
        src=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        broker=(ROOT/"services/connections/ConnectionsBroker.qml").read_text()
        inspector=(FIXTURES/"TaskSourceRevisionEvidenceM13u.py").read_text()
        self.assertEqual(src.count("todoFile.setText("),1)
        self.assertEqual(src.count("FileView {"),1)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false",src)
        self.assertIn("readonly property bool ticketProducerEnabled: false",src)
        self.assertIn("readonly property bool credentialActionsEnabled: false",broker)
        self.assertNotIn("TaskSourceRevisionEvidenceM13u",src+broker)
        self.assertNotIn("secret-tool",inspector)
        self.assertNotIn("os.replace(",inspector)
        self.assertNotIn("sqlite3.connect(",inspector)

if __name__=="__main__":
    unittest.main()
