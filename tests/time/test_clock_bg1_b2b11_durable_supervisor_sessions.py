"""Clock BG1-B2B11: real supervisor session epoch and pidfd exit fencing.

All newly persisted session evidence is synthetic-only. Production has no
installed roster/issuer and cannot pause, release, take over or ring alarms.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[2]
HARNESS=ROOT/"tests/time/test_clock_bg1_b2b10_native_supervisor.py"

def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

B2B10=load(HARNESS,"clock_b2b11_test_harness")
Server=B2B10.Supervisor
Session=Server.Session


class ClockB2B11DurableSupervisorSessionTests(unittest.TestCase):
    def setUp(self):
        self.h=B2B10.ClockNativeSupervisorTests(
            methodName="test_real_af_unix_signed_client_is_only_observed_never_authorized")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        # Keep the signed test peer alive long enough to test the
        # "still running" branch deterministically on loaded CI hosts.
        self.h.script.write_text(
            self.h.script.read_text().replace("time.sleep(.5)",
                                              "time.sleep(1.5)"),
            encoding="utf-8")
        self.server=self.h.server
        self.ledger=self.server._session_ledger
        self.assertIsNotNone(self.ledger)

    def refused(self,fn,reason,exception=Session.Refused):
        with self.assertRaises(exception) as caught:
            fn()
        self.assertEqual(str(caught.exception),reason)

    def observe(self):
        return self.h.exchange(B2B10.request("INSPECT_ORIGIN"))

    def exit_old(self):
        self.h.child.wait(timeout=4)
        return self.server.observe_synthetic_session_exit(self.h.child.pid)

    def start_new(self, epoch, *, signed_epoch=None, minimum=None):
        signed_epoch=epoch if signed_epoch is None else signed_epoch
        minimum=epoch if minimum is None else minimum
        argv=[self.h.exe,"-I","-B",str(self.h.script),
              str(self.server.socket_path)]
        self.h.write_trust(argv,policy_updates={
            "releaseEpoch": signed_epoch})
        child=subprocess.Popen(argv,stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.h.child=child
        self.h.addCleanup(self.h.stop_child)
        pin=Server.SyntheticSessionPin(
            pid=child.pid,ticks=Server.Peer._start_ticks(child.pid),
            interpreter=self.h.exe,role="clock-ui-bridge",
            trust_directory=str(self.h.trust),
            pinned_root_sha256=self.h.fingerprint,
            minimum_epoch=minimum,minimum_sequence=12,
            epoch=epoch)
        self.server.add_synthetic_session(pin)
        child.stdin.write(B2B10.request("INSPECT_ORIGIN"))
        child.stdin.flush()
        evidence=self.server.serve_once(timeout=4)
        self.assertEqual(json.loads(child.stdout.readline()),evidence)
        for flag in ("roleAuthenticated","writerStopped",
                     "releaseAcknowledged","canTransferOwnership",
                     "canRing","canNotify"):
            self.assertIs(evidence[flag],False,flag)
        return evidence

    def test_real_signed_socket_session_durably_persisted(self):
        first=self.observe()
        self.assertTrue(first["originObserved"])
        entry=self.ledger.inspect()
        self.assertEqual(entry["state"],"SIGNED_PROCESS_OBSERVED")
        self.assertEqual(entry["observedEpoch"],5)
        self.assertTrue(entry["sameBoot"])
        self.assertTrue(entry["fixtureOnly"])
        reopened=Session.ClockSessionLedger(
            self.server.directory,synthetic_only=True)
        self.assertEqual(reopened.inspect(),entry)
        for flag in ("roleAuthenticated","writerStopped",
                     "releaseAcknowledged","oldWriterRestartPrevented",
                     "ownsRealAlarmFile","canTransferOwnership",
                     "canRing","canNotify"):
            self.assertIs(entry[flag],False)
        self.assertEqual(self.h.server._test_pins[self.h.child.pid].epoch,5)

    def test_witnessed_real_kernel_process_exit_is_not_release_authority(self):
        self.observe()
        pid=self.h.child.pid
        self.assertIn(pid,self.server._test_pidfds)
        result=self.exit_old()
        self.assertEqual(result["state"],"PIDFD_EXIT_OBSERVED")
        self.assertEqual(result["observedEpoch"],5)
        self.assertFalse(result["oldWriterRestartPrevented"])
        self.assertFalse(result["releaseAcknowledged"])
        self.assertNotIn(pid,self.server._test_pidfds)
        self.assertNotIn(pid,self.server._test_pins)
        self.refused(lambda:self.server.observe_synthetic_session_exit(pid),
                     "NO_SUPERVISED_TEST_PROCESS_WITNESS",Server.Refused)

    def test_exit_observation_refuses_still_running_process(self):
        self.observe()
        # The signed client is normally alive until after it sends reply.
        self.refused(lambda:self.server.observe_synthetic_session_exit(
            self.h.child.pid),"SIGNED_SESSION_PROCESS_STILL_RUNNING",
            Server.Refused)
        self.assertEqual(self.ledger.inspect()["state"],
                         "SIGNED_PROCESS_OBSERVED")

    def test_after_observed_exit_same_epoch_cannot_reenroll(self):
        self.observe()
        self.exit_old()
        denied=self.start_new(5)
        self.assertFalse(denied["originObserved"])
        self.assertEqual(denied["reason"],
                         "NO_INSTALLED_CLOCK_SESSION_AUTHORITY")
        self.assertEqual(self.ledger.inspect()["state"],
                         "PIDFD_EXIT_OBSERVED")

    def test_after_real_exit_higher_new_signed_epoch_can_be_observed(self):
        self.observe()
        self.exit_old()
        accepted=self.start_new(6)
        self.assertTrue(accepted["originObserved"])
        self.assertEqual(accepted["reason"],
                         "OBSERVED_ONLY_NOT_AUTHORIZED")
        self.assertEqual(self.ledger.inspect()["observedEpoch"],6)
        self.assertEqual(self.ledger.inspect()["state"],
                         "SIGNED_PROCESS_OBSERVED")
        self.assertFalse(accepted["canTransferOwnership"])

    def test_signed_epoch_mismatch_cannot_be_laundered_by_session_pin(self):
        rejected=self.start_new(6,signed_epoch=5,minimum=5)
        self.assertFalse(rejected["originObserved"])
        self.assertEqual(self.ledger.inspect()["state"],"NONE")
        self.assertEqual(rejected["reason"],
                         "NO_INSTALLED_CLOCK_SESSION_AUTHORITY")

    def test_unretired_writer_blocks_replacement_even_after_server_restart(self):
        self.observe()
        # A crash/restart loses the in-memory pidfd, not the 0600
        # SQLite record. No unsafe PID lookup can recover that witness.
        self.h.child.wait(timeout=4)
        self.server.close()
        restored=Server.ClockNativeSupervisor(
            self.h.runtime,synthetic_only=True)
        restored.bind()
        self.h.addCleanup(restored.close)
        self.server=restored
        self.ledger=restored._session_ledger
        self.h.server=restored
        result=self.start_new(6)
        self.assertFalse(result["originObserved"])
        self.assertEqual(self.ledger.inspect()["observedEpoch"],5)
        self.assertEqual(self.ledger.inspect()["state"],
                         "SIGNED_PROCESS_OBSERVED")
        self.refused(lambda:self.server.observe_synthetic_session_exit(
            self.h.child.pid),"NO_SUPERVISED_TEST_PROCESS_WITNESS",
            Server.Refused)

    def test_kernel_fd_must_be_original_pidfd_not_arbitrary_regular_file(self):
        self.observe()
        self.h.child.wait(timeout=4)
        fd=os.open("/dev/null",os.O_RDONLY)
        try:
            self.refused(lambda:self.ledger.observe_exited_pidfd(
                pid=self.h.child.pid,
                ticks=self.server._test_pins[self.h.child.pid].ticks,
                epoch=5,pidfd=fd),"ORIGINAL_KERNEL_PIDFD_UNVERIFIED")
        finally:
            os.close(fd)
        self.assertEqual(self.ledger.inspect()["state"],
                         "SIGNED_PROCESS_OBSERVED")

    def test_invalid_ledger_symlink_or_permissive_modes_fail_closed(self):
        path=self.ledger.path
        other=self.h.root/"user-ledger"
        other.write_text("do not replace")
        path.symlink_to(other)
        self.refused(self.ledger.inspect,"SESSION_LEDGER_SYMLINK")
        self.assertEqual(other.read_text(),"do not replace")
        path.unlink()
        self.ledger.inspect()
        path.chmod(0o644)
        self.refused(self.ledger.inspect,"UNSAFE_SESSION_LEDGER")
        path.chmod(0o600)

    def test_unexpected_boot_identity_requires_independent_recovery(self):
        self.observe()
        with sqlite3.connect(self.ledger.path) as db:
            db.execute("UPDATE clock_sessions SET boot_id=?",
                       ("11111111-1111-1111-1111-111111111111",))
        self.assertFalse(self.ledger.inspect()["sameBoot"])
        pin=self.server._test_pins[self.h.child.pid]
        self.refused(lambda:self.ledger.observe_signed_process(
            pid=pin.pid,ticks=pin.ticks,epoch=pin.epoch,
            release_root_sha256=pin.pinned_root_sha256),
            "PREVIOUS_BOOT_SESSION_REQUIRES_RECOVERY")

    def test_new_process_cannot_enter_before_kernel_observed_exit(self):
        self.observe()
        rejected=self.start_new(6)
        self.assertFalse(rejected["originObserved"])
        self.assertEqual(self.ledger.inspect()["observedEpoch"],5)
        self.assertEqual(self.ledger.inspect()["state"],
                         "SIGNED_PROCESS_OBSERVED")

    def test_concurrent_candidate_observations_allow_only_one_process(self):
        barrier=threading.Barrier(2)
        results=[]
        guard=threading.Lock()
        def compete(pid):
            barrier.wait()
            try:
                self.ledger.observe_signed_process(
                    pid=pid,ticks=123,epoch=8,
                    release_root_sha256=self.h.fingerprint)
                outcome="observed"
            except Session.Refused:
                outcome="denied"
            with guard:
                results.append(outcome)
        a=threading.Thread(target=compete,args=(500001,))
        b=threading.Thread(target=compete,args=(500002,))
        a.start();b.start();a.join(8);b.join(8)
        self.assertFalse(a.is_alive())
        self.assertFalse(b.is_alive())
        self.assertEqual(sorted(results),["denied","observed"])
        self.assertEqual(self.ledger.inspect()["observedEpoch"],8)
        # This tests only transaction serialization, not signed admission.
        self.assertFalse(self.ledger.inspect()["canTransferOwnership"])

    def test_untrusted_fixture_cannot_claim_installed_role_permissions(self):
        self.refused(lambda:Session.ClockSessionLedger(
            self.server.directory,synthetic_only=False),
            "DISPOSABLE_SESSION_LEDGER_ONLY")
        self.refused(lambda:self.ledger.observe_signed_process(
            pid=True,ticks=1,epoch=5,
            release_root_sha256=self.h.fingerprint),
            "INVALID_INDEPENDENT_SESSION_PINS")
        self.refused(lambda:self.ledger.observe_signed_process(
            pid=5000,ticks=1,epoch=True,
            release_root_sha256=self.h.fingerprint),
            "INVALID_INDEPENDENT_SESSION_PINS")
        self.assertFalse(Server._response("DENY")["ok"])
        live=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',live)
        self.assertNotIn("AlarmSupervisorSessionLedger",live)
        for code in (
            (ROOT/"services/time/AlarmSupervisorSessionLedger.py").read_text(),
            (ROOT/"services/time/AlarmNativeClockSupervisor.py").read_text()):
            for word in ("notify-send","alarmFile.setText",
                         "systemctl --user enable","canRing=True"):
                self.assertNotIn(word,code)



if __name__=="__main__":
    unittest.main()
