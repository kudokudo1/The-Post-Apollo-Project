"""BG1-B2B8: durable pidfd-exit evidence after signed old-writer reply.

Real disposable Linux process + SQLite ledger; NEVER real Clock authority.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import unittest

ROOT=Path(__file__).resolve().parents[2]
B2B7=ROOT/"tests/time/test_clock_bg1_b2b7_role_bound_release.py"
SOURCE=ROOT/"services/time/AlarmWriterExitFenceFixture.py"

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

Harness=load(B2B7,"b2b8_test_fixture").ClockB2B7RoleBoundRelease
Exit=load(SOURCE,"b2b8_exit_fixture")


class ClockB2B8DurableExit(unittest.TestCase):
    def setUp(self):
        # Reuse the exact B2B7 real AF_UNIX peer + two independently signed
        # fixture policies so the test cannot substitute made-up evidence.
        self.h=Harness(methodName="test_one_real_pid_signed_enrollment_and_signed_reply_still_deny")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        self.f=Exit.DurableExitObservationFixture(self.h.chain,synthetic_only=True)
        self.digest=hashlib.sha256(self.h.source.read_bytes()).hexdigest()
        self.original=self.h.source.read_bytes()

    def issue(self):
        return self.f.prepare(
            self.h.conn,self.h.peer,
            expected_source_digest=self.digest,old_epoch=5,new_epoch=6)

    def reply(self,req):
        body,sig=self.h.answer(req)
        return self.f.observe_signed_reply(
            self.h.conn,self.h.peer,signed_reply=body,signature=sig),body,sig

    def refused(self,fn,reason):
        with self.assertRaises(Exit.Refused) as ctx:
            fn()
        self.assertEqual(str(ctx.exception),reason)

    def test_actual_exited_pidfd_is_durable_and_old_epoch_fenced_on_restart(self):
        req=self.issue()
        self.assertEqual(self.f.inspect()["state"],"PREPARED")
        signed,body,sig=self.reply(req)
        self.assertEqual(signed["state"],"SIGNED_REPLY_OBSERVED")
        self.assertFalse(signed["writerExitObserved"])
        self.assertFalse(signed["canTransferOwnership"])
        self.h.stop()
        observed=self.f.observe_process_exit(self.h.peer)
        self.assertEqual(observed["state"],"PROCESS_EXIT_OBSERVED")
        self.assertTrue(observed["writerExitObserved"])
        self.assertFalse(observed["oldWriterRestartPrevented"])
        self.assertFalse(observed["releaseAcknowledged"])
        self.assertFalse(observed["canRing"])
        self.assertEqual(observed["retiredEpoch"],5)
        self.assertEqual(self.h.source.read_bytes(),self.original)
        # Fresh fixture object reopens the *durable* database after exit.
        fresh=Exit.DurableExitObservationFixture(
            self.h.make_chain(),synthetic_only=True)
        self.assertTrue(fresh.inspect()["writerExitObserved"])
        for epoch in (1,4,5):
            self.refused(lambda e=epoch:fresh.refuse_old_epoch(e),
                         "RETIRED_SYNTHETIC_WRITER_EPOCH")
        candidate=fresh.refuse_old_epoch(6)
        self.assertTrue(candidate["fixtureOnly"])
        self.assertFalse(candidate["canTransferOwnership"])
        self.assertFalse(candidate["canRing"])

    def test_signed_reply_does_not_prove_exit_while_process_lives(self):
        req=self.issue()
        self.reply(req)
        self.refused(lambda:self.f.observe_process_exit(self.h.peer),
                     "OLD_WRITER_STILL_RUNNING")
        self.assertEqual(self.f.inspect()["state"],"SIGNED_REPLY_OBSERVED")
        self.assertFalse(self.f.inspect()["writerExitObserved"])
        self.refused(lambda:self.f.refuse_old_epoch(5),
                     "WRITER_EXIT_NOT_DURABLY_OBSERVED")

    def test_exit_before_signed_reply_cannot_skip_signature(self):
        self.issue()
        self.h.stop()
        self.refused(lambda:self.f.observe_process_exit(self.h.peer),
                     "SIGNED_REPLY_REQUIRED_BEFORE_EXIT")
        self.assertEqual(self.f.inspect()["state"],"PREPARED")
        self.assertFalse(self.f.inspect()["writerExitObserved"])

    def test_wrong_signature_does_not_advance_to_exit(self):
        req=self.issue()
        body,sig=self.h.answer(req)
        self.refused(lambda:self.f.observe_signed_reply(
            self.h.conn,self.h.peer,
            signed_reply=body,signature=b"\x00"*64),
            "SIGNED_OLD_WRITER_REPLY_REFUSED")
        self.assertEqual(self.f.inspect()["state"],"PREPARED")
        # Signed valid reply still admissible after a forged attempt.
        result=self.f.observe_signed_reply(
            self.h.conn,self.h.peer,signed_reply=body,signature=sig)
        self.assertEqual(result["state"],"SIGNED_REPLY_OBSERVED")
        self.assertFalse(result["writerExitObserved"])

    def test_changed_source_refuses_exit_after_real_reply(self):
        req=self.issue()
        self.reply(req)
        self.h.source.write_text(
            json.dumps({"version":2,"nextId":1,"alarms":[],
                        "other":"external change"})+"\n")
        self.h.source.chmod(0o600)
        changed=self.h.source.read_bytes()
        self.h.stop()
        self.refused(lambda:self.f.observe_process_exit(self.h.peer),
                     "ALARM_SOURCE_CHANGED_BEFORE_EXIT")
        self.assertEqual(self.f.inspect()["state"],"SIGNED_REPLY_OBSERVED")
        self.assertEqual(self.h.source.read_bytes(),changed)

    def test_reply_replay_and_second_prepare_refuse(self):
        req=self.issue()
        self.refused(lambda:self.issue(),
                     "EXISTING_EXIT_ATTEMPT_OR_RETIRED_EPOCH")
        _,body,sig=self.reply(req)
        self.refused(lambda:self.f.observe_signed_reply(
            self.h.conn,self.h.peer,signed_reply=body,signature=sig),
            "SIGNED_REPLY_ATTEMPT_NOT_PREPARED")

    def test_wrong_pid_or_start_ticks_refused_on_exit(self):
        req=self.issue()
        self.reply(req)
        self.h.stop()
        forged=dict(self.h.peer,ticks=self.h.peer["ticks"]+1)
        self.refused(lambda:self.f.observe_process_exit(forged),
                     "WRITER_PROCESS_WITNESS_MISMATCH")
        self.assertEqual(self.f.inspect()["state"],"SIGNED_REPLY_OBSERVED")

    def test_symlinked_or_world_readable_replay_ledger_denied(self):
        # A ledger must not follow a symlink or accept permissive mode.
        path=self.f.path
        other=self.h.base/"other-ledger"
        other.write_text("untrusted")
        path.symlink_to(other)
        self.refused(lambda:self.f.inspect(),"UNSAFE_EXIT_LEDGER")
        path.unlink()
        self.f.inspect()  # creates 0600 ledger
        path.chmod(0o644)
        self.refused(lambda:self.f.inspect(),"UNSAFE_EXIT_LEDGER")
        path.chmod(0o600)

    def test_untrusted_user_inputs_do_not_enable_real_writer_rights(self):
        self.refused(lambda:Exit.DurableExitObservationFixture(
            self.h.chain,synthetic_only=False),
            "DISPOSABLE_EXIT_OBSERVER_ONLY")
        self.refused(lambda:Exit.DurableExitObservationFixture(
            {"signed":True},synthetic_only=True),
            "DISPOSABLE_EXIT_OBSERVER_ONLY")
        self.refused(lambda:self.f.refuse_old_epoch(True),
                     "INVALID_EPOCH_QUERY")
        self.refused(lambda:self.f.refuse_old_epoch(0),
                     "INVALID_EPOCH_QUERY")
        self.assertEqual(self.f.inspect()["state"],"NONE")
        for key in ("releaseAcknowledged","canTransferOwnership",
                    "ownsRealAlarmFile","canRing","canNotify",
                    "oldWriterRestartPrevented"):
            self.assertFalse(self.f.inspect()[key])

    def test_two_concurrent_prepares_cannot_create_two_exit_attempts(self):
        barrier=threading.Barrier(2)
        outcomes=[]
        lock=threading.Lock()
        def run():
            barrier.wait()
            try:
                self.issue()
                state="issued"
            except Exit.Refused:
                state="refused"
            with lock:
                outcomes.append(state)
        a=threading.Thread(target=run)
        b=threading.Thread(target=run)
        a.start();b.start()
        a.join(timeout=8);b.join(timeout=8)
        self.assertFalse(a.is_alive())
        self.assertFalse(b.is_alive())
        self.assertEqual(sorted(outcomes),["issued","refused"])
        self.assertEqual(self.f.inspect()["state"],"PREPARED")

    def test_no_live_quickshell_change_or_installed_authority(self):
        source=SOURCE.read_text()
        qml=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        broker=(ROOT/"services/time/AlarmOwnershipBroker.py").read_text()
        self.assertNotIn("AlarmWriterExitFenceFixture",qml)
        self.assertNotIn("AlarmWriterExitFenceFixture",broker)
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',qml)
        for forbidden in ("alarmFile.setText","notify-send","systemctl",
                          "os.replace(","subprocess.Popen(","canRing=True"):
            self.assertNotIn(forbidden,source)
        self.assertIn('"oldWriterRestartPrevented": False',source)
        self.assertIn('"releaseAcknowledged": False',source)


if __name__=="__main__":
    unittest.main()
