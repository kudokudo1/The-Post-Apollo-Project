"""Clock B2B20: actual disposable writer exit, durable hold and V2 final sync.

Tests run two OS processes and real SQLite/fcntl/fsync on temporary paths.
No live Quickshell, systemd, installed keys, user alarm data or ringing.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "services/time/AlarmNativeCutoverController.py"
QML = ROOT / "services/time/AlarmManagerService.qml"

spec = importlib.util.spec_from_file_location("clock_bg1_full_fixture_cutover", PATH)
Cutover = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = Cutover
spec.loader.exec_module(Cutover)

CHILD = """import socket,sys
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.connect(sys.argv[1])
print("READY",flush=True)
sys.stdin.buffer.read(1)
s.close()
"""


class NativeCutoverRealKernelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clock-offline-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / Cutover.FIXTURE_NAME
        self.root.mkdir(mode=0o700)
        self.source_dir = self.parent / Cutover.Final.DISPOSABLE_PARENT
        self.source_dir.mkdir(mode=0o700)
        self.source = self.source_dir / Cutover.Final.SOURCE_NAME
        self.raw = (json.dumps({"version": 2, "nextId": 2,
                                "alarms": [{"id": 1, "name": "PRIVATE TEST"}]},
                               sort_keys=True) + "\n").encode()
        self.source.write_bytes(self.raw)
        self.source.chmod(0o600)
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.sockpath = str(self.root / "old.sock")
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(self.sockpath)
        self.listener.listen(1)
        self.listener.settimeout(4)
        self.addCleanup(self.listener.close)
        self.child = None
        self.conn = None
        self.controller = None
        self.addCleanup(self.stop_process)

    def stop_process(self):
        if self.controller is not None:
            self.controller.close()
            self.controller = None
        if self.conn is not None:
            self.conn.close()
            self.conn = None
        if self.child is not None:
            if self.child.poll() is None:
                self.child.kill()
            self.child.communicate(timeout=4)
            self.child = None

    def refuse(self, cb, reason):
        with self.assertRaises(Cutover.Refused) as found:
            cb()
        self.assertEqual(str(found.exception), reason)

    def launch(self):
        journal = Cutover.CutoverLedger(self.root)
        try:
            self.assertEqual(journal.read_only_state(), "FREE")
            journal.reserve_old_writer_launch()
            self.refuse(journal.reserve_old_writer_launch,
                        "OLD_WRITER_LAUNCH_FENCED")
            self.child = subprocess.Popen(
                [sys.executable, "-I", "-u", "-c", CHILD, self.sockpath],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            self.conn, _ = self.listener.accept()
            self.assertEqual(self.child.stdout.readline(), b"READY\n")
            self.ticks = Cutover.Peer._start_ticks(self.child.pid)
            journal.attach_writer_identity(self.child.pid, self.ticks)
            self.assertEqual(journal.read_only_state(), "LAUNCH_RESERVED")
        finally:
            journal.close()

    def controller_for_old(self):
        self.controller = Cutover.ClockOfflineCutover(
            root=self.root, old_socket=self.conn,
            old_pid=self.child.pid, old_ticks=self.ticks,
            old_executable=sys.executable, final_path=self.source,
            final_digest=self.digest, final_uid=os.getuid(),
            synthetic_only=True)
        return self.controller

    def exit_writer(self):
        self.child.stdin.write(b"x")
        self.child.stdin.flush()
        self.child.wait(timeout=3)

    def check_denied_authority(self, report):
        for k, expected in Cutover.NO_AUTHORITY.items():
            self.assertEqual(report[k], expected, k)
        self.assertTrue(report["fixtureOnly"])
        self.assertNotIn(self.digest, str(report))
        self.assertNotIn("PRIVATE TEST", str(report))

    def test_real_kernel_writer_exit_and_final_fsync_to_fixture_selection(self):
        self.launch()
        c = self.controller_for_old()
        report = c.request_shutdown()
        self.assertEqual(report["phase"], "HOLD_PENDING")
        self.check_denied_authority(report)
        self.refuse(c.witness_exit, "OLD_WRITER_STILL_RUNNING")
        self.exit_writer()
        report = c.witness_exit()
        self.assertTrue(report["oldWriterKernelExitObserved"])
        report = c.witness_final_sync()
        self.assertTrue(report["finalFileSyncObserved"])
        self.assertFalse(report["syntheticNativeSelected"])
        report = c.select_fixture_native()
        self.assertEqual(report["phase"], "FIXTURE_NATIVE_SELECTED")
        self.assertTrue(report["syntheticNativeSelected"])
        self.check_denied_authority(report)
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_gates_stay_durable_after_shutdown_and_controller_crash(self):
        self.launch()
        c = self.controller_for_old()
        c.request_shutdown()
        probe = Cutover.CutoverLedger(self.root)
        try:
            self.refuse(probe.reserve_old_writer_launch, "CUTOVER_GATE_BUSY")
        finally:
            probe.close()
        c.close()  # simulate controller crash: no reset or replay
        self.controller = None
        other = Cutover.CutoverLedger(self.root)
        try:
            self.assertEqual(other.read_only_state(), "HOLD_PENDING")
            self.refuse(other.reserve_old_writer_launch,
                        "OLD_WRITER_LAUNCH_FENCED")
        finally:
            other.close()

    def test_interrupted_launch_reservation_refuses_implicit_restart(self):
        journal = Cutover.CutoverLedger(self.root)
        journal.reserve_old_writer_launch()
        journal.close()  # crash before spawning a writer or attaching pidfd
        fresh = Cutover.CutoverLedger(self.root)
        try:
            self.assertEqual(fresh.read_only_state(), "LAUNCH_RESERVED")
            self.refuse(fresh.reserve_old_writer_launch,
                        "OLD_WRITER_LAUNCH_FENCED")
        finally:
            fresh.close()

    def test_final_sync_before_old_writer_exit_is_refused(self):
        self.launch()
        c = self.controller_for_old()
        c.request_shutdown()
        self.refuse(c.witness_final_sync, "OLD_WRITER_EXIT_REQUIRED")
        self.refuse(c.select_fixture_native, "FINAL_SYNC_REQUIRED_FOR_TEST_NATIVE")

    def test_modified_source_after_old_exit_refuses_selection(self):
        self.launch()
        c = self.controller_for_old()
        c.request_shutdown()
        self.exit_writer()
        c.witness_exit()
        self.source.write_bytes(b'{"version":2,"nextId":1,"alarms":[]}\n')
        self.source.chmod(0o600)
        self.refuse(c.witness_final_sync, "FINAL_SOURCE_NOT_SYNCHRONIZED")
        journal = Cutover.CutoverLedger(self.root)
        self.assertEqual(journal.read_only_state(), "OLD_WRITER_EXITED")
        self.refuse(journal.reserve_old_writer_launch, "CUTOVER_GATE_BUSY")
        journal.close()

    def test_changed_source_after_final_sync_refuses_fixture_selection(self):
        self.launch()
        c = self.controller_for_old()
        c.request_shutdown()
        self.exit_writer()
        c.witness_exit()
        c.witness_final_sync()
        self.source.write_bytes(b'{"version":2,"nextId":1,"alarms":[]}\n')
        self.source.chmod(0o600)
        self.refuse(c.select_fixture_native, "FINAL_SOURCE_CHANGED_AFTER_SYNC")

    def test_old_writer_wrong_kernel_identity_fails_before_hold(self):
        self.launch()
        self.refuse(lambda: Cutover.ClockOfflineCutover(
            root=self.root, old_socket=self.conn,
            old_pid=self.child.pid, old_ticks=1,
            old_executable=sys.executable, final_path=self.source,
            final_digest=self.digest, final_uid=os.getuid(),
            synthetic_only=True), "OLD_WRITER_LAUNCH_RECEIPT_REQUIRED")
        fresh = Cutover.CutoverLedger(self.root)
        self.assertEqual(fresh.read_only_state(), "LAUNCH_RESERVED")
        fresh.close()

    def test_missing_or_invalid_native_authority_never_enables_production(self):
        self.refuse(lambda: Cutover.ClockOfflineCutover(
            root="/tmp/not-applicable", old_socket=None, old_pid=0,
            old_ticks=0, old_executable="", final_path="/etc/passwd",
            final_digest="", final_uid=os.getuid(), synthetic_only=False),
            "PRODUCTION_CUTOVER_NOT_INSTALLED")

    def test_ledger_rejects_unsafe_permissions_and_symlinks(self):
        journal = Cutover.CutoverLedger(self.root)
        journal.close()
        db = self.root / "cutover.sqlite3"
        db.chmod(0o644)
        self.refuse(lambda: Cutover.CutoverLedger(self.root),
                    "CUTOVER_JOURNAL_UNSAFE")
        db.chmod(0o600)
        db.rename(self.root / "real.sqlite3")
        db.symlink_to(self.root / "real.sqlite3")
        self.refuse(lambda: Cutover.CutoverLedger(self.root),
                    "CUTOVER_JOURNAL_UNSAFE")

    def test_concurrent_launch_ledger_gate_lock_refuses(self):
        one = Cutover.CutoverLedger(self.root)
        two = Cutover.CutoverLedger(self.root)
        one._lock()
        try:
            self.refuse(two.reserve_old_writer_launch, "CUTOVER_GATE_BUSY")
        finally:
            one.close()
            two.close()

    def test_existing_qml_alarm_file_and_tick_authority_untouched(self):
        qml = QML.read_text(encoding="utf-8")
        self.assertIn('readonly property string alarmWriterBarrierPhase: "ACTIVE"', qml)
        self.assertIn('readonly property bool nativeWriterDrainBridgeInstalled: false',qml)
        self.assertIn("function requestAlarmWriterPause()",qml)
        self.assertEqual(qml.count("alarmFile.setText("), 1)


if __name__ == "__main__":
    unittest.main()
