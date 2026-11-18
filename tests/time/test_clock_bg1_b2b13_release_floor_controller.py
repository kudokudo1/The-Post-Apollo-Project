"""Clock BG1-B2B13: privileged-contract source with real disposable signed peer.

These tests exercise actual Linux AF_UNIX/pidfd + signed installed Clock-role
fixture, SQLite synchronous FULL floor, atomic one-session publication and
B2B12 independent read-back. NO root signing key or systemd unit is installed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
HARNESS_FILE = ROOT/"tests/time/test_clock_bg1_b2b9_installed_role_trust.py"
CONTROLLER_FILE = ROOT/"services/time/AlarmClockReleaseFloorController.py"


def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    component=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=component
    spec.loader.exec_module(component)
    return component


Fixture=load(HARNESS_FILE,"clock_b2b13_original_kernel_fixture")
Controller=load(CONTROLLER_FILE,"clock_b2b13_controller")
Session=Controller.Session


class ClockB2B13ControllerTests(unittest.TestCase):
    def setUp(self):
        self.h=Fixture.ClockB2B9InstalledRoleTrustTests(
            methodName="test_actual_af_unix_pidfd_and_independent_signed_bundle_still_deny")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        self.state=self.h.base/Controller.DISPOSABLE_STATE
        self.state.mkdir(mode=0o700)
        self.enrollment=self.h.base/Session.TEST_ENROLLMENT_NAME
        self.enrollment.mkdir(mode=0o700)
        self.controller=self.make()

    def make(self, *, key=None, pin=None, floor=(5,12),
             state=None, enrollment=None, synthetic=True):
        return Controller.ClockReleaseFloorController(
            state_directory=self.state if state is None else state,
            enrollment_directory=self.enrollment if enrollment is None
                else enrollment,
            trust_directory=self.h.directory,
            pinned_root_sha256=self.h.pin if pin is None else pin,
            minimum_epoch=floor[0],
            minimum_sequence=floor[1],
            signing_key=self.h.issuer if key is None else key,
            synthetic_only=synthetic)

    def refused(self,call,reason):
        with self.assertRaises(Controller.Refused) as error:
            call()
        self.assertEqual(str(error.exception),reason)

    def issue(self,controller=None):
        return (self.controller if controller is None else controller).issue(
            self.h.connection)

    def reader(self, floor=(5,12)):
        return Session.ClockProtectedSessionEnrollment(
            enrollment_directory=self.enrollment,
            trust_directory=self.h.directory,
            pinned_root_sha256=self.h.pin,
            minimum_epoch=floor[0],
            minimum_sequence=floor[1],
            synthetic_only=True)

    def reissue_with_new_process(self, epoch, sequence):
        # The same signing root and program entrypoint are retained.
        # Terminate the old kernel identity and start a new signed instance.
        self.h.stop()
        self.h.connection.close()
        self.h.policy=dict(self.h.policy, releaseEpoch=epoch,
                           releaseSequence=sequence)
        self.h.write_policy()
        self.h.proc=subprocess.Popen(
            self.h.argv,stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.h.connection,_=self.h.listener.accept()
        self.h.connection.settimeout(5)
        self.assertEqual(self.h.connection.recv(1),b"R")
        self.h.addCleanup(self.h.connection.close)
        self.h.witness=Fixture.Role._Peer.capture(
            self.h.connection,self.h.interpreter)
        self.h.addCleanup(Fixture.Role._Peer.close,self.h.witness)
        return self.make()

    def test_real_signed_process_issues_b2b12_reader_compatible_session(self):
        issued=self.issue()
        self.assertTrue(issued["signedSessionPublished"])
        self.assertTrue(issued["fixtureOnly"])
        self.assertEqual((issued["latestEpoch"],issued["latestSequence"]),(5,12))
        for flag in Controller.DENIED:
            self.assertIs(issued[flag],False)
        self.assertEqual(stat.S_IMODE(self.controller.ledger_path.stat().st_mode),
                         0o600)
        self.assertEqual(self.controller.inspect_floor()["floorRecorded"],True)
        value=self.reader().inspect(self.h.connection)
        self.assertTrue(value["sameKernelPeer"])
        self.assertTrue(value["signedSessionObserved"])
        self.assertFalse(value["releaseAcknowledged"])
        self.assertFalse(value["canTransferOwnership"])
        self.assertFalse(value["canRing"])

    def test_single_use_signed_release_version_replay_denied_after_reopen(self):
        self.issue()
        self.refused(self.issue,"MONOTONIC_CLOCK_RELEASE_REPLAY")
        reopened=self.make()
        self.assertEqual((reopened.inspect_floor()["latestEpoch"],
                          reopened.inspect_floor()["latestSequence"]),(5,12))
        self.refused(lambda:self.issue(reopened),
                     "MONOTONIC_CLOCK_RELEASE_REPLAY")
        self.assertTrue(self.reader().inspect(self.h.connection)[
            "signedSessionObserved"])

    def test_new_signed_sequence_on_same_process_is_not_new_enrollment(self):
        self.issue()
        self.h.policy=dict(self.h.policy,releaseSequence=13)
        self.h.write_policy()
        newer=self.make()
        self.refused(lambda:self.issue(newer),
                     "OLD_CLOCK_PROCESS_ALREADY_ENROLLED")
        self.assertEqual(self.controller.inspect_floor()["latestSequence"],12)

    def test_higher_signed_version_requires_distinct_real_pidfd_process(self):
        self.issue()
        old_pid=self.h.proc.pid
        successor=self.reissue_with_new_process(5,13)
        self.assertNotEqual(self.h.proc.pid,old_pid)
        issued=self.issue(successor)
        self.assertEqual((issued["latestEpoch"],issued["latestSequence"]),(5,13))
        self.assertTrue(self.reader((5,13)).inspect(self.h.connection)[
            "signedSessionObserved"])
        self.assertFalse(issued["roleAuthenticated"])
        self.assertFalse(issued["canTransferOwnership"])

    def test_stale_minimum_release_floor_refused(self):
        self.refused(lambda:self.make(floor=(5,13)),
                     "CLOCK_ISSUER_ROOT_NOT_APPROVED")
        self.issue()
        self.refused(lambda:self.issue(self.make(floor=(5,12))),
                     "MONOTONIC_CLOCK_RELEASE_REPLAY")

    def test_unmatched_signer_or_self_pinned_root_refused(self):
        self.refused(lambda:self.make(key=Ed25519PrivateKey.generate()),
                     "CLOCK_SIGNER_DOES_NOT_MATCH_INSTALLED_ROOT")
        self.refused(lambda:self.make(pin="e"*64),
                     "CLOCK_ISSUER_ROOT_NOT_APPROVED")
        self.refused(lambda:self.make(pin=True),
                     "CLOCK_ISSUER_ROOT_NOT_APPROVED")
        self.refused(lambda:self.make(key="not a key"),
                     "TRUSTED_CLOCK_ISSUER_INPUT_REQUIRED")

    def test_lifetime_exit_and_changed_executable_refuse_issue(self):
        self.h.entrypoint.write_text(
            self.h.entrypoint.read_text()+"\n# modified\n")
        self.refused(self.issue,"CONTROLLER_SIGNED_PROCESS_REFUSED")
        self.assertFalse(self.controller.inspect_floor()["floorRecorded"])
        self.h.entrypoint.write_text(Fixture.CLIENT)
        self.h.stop()
        self.refused(self.issue,"CONTROLLER_PEER_OR_SIGNED_ROLE_REFUSED")
        self.assertFalse(self.controller.inspect_floor()["floorRecorded"])

    def test_crash_after_floor_commit_cannot_reissue_same_version(self):
        with patch.object(Controller,"_durable_publish",
                          side_effect=Controller.Refused(
                              "CLOCK_SESSION_WRITE_FAILED")):
            self.refused(self.issue,"CLOCK_SESSION_WRITE_FAILED")
        self.assertEqual(self.controller.inspect_floor()["latestEpoch"],5)
        self.assertFalse(
            (self.enrollment/Session.SIGNATURE_FILE).exists())
        self.refused(self.issue,"MONOTONIC_CLOCK_RELEASE_REPLAY")

    def test_symlinked_ledger_or_permissive_dir_fails_closed(self):
        foreign=self.h.base/"untrusted-floor"
        foreign.write_text("must remain")
        self.controller.ledger_path.symlink_to(foreign)
        self.refused(self.controller.inspect_floor,
                     "CLOCK_FLOOR_LEDGER_SYMLINK")
        self.assertEqual(foreign.read_text(),"must remain")
        self.controller.ledger_path.unlink()
        self.controller.inspect_floor()
        self.controller.ledger_path.chmod(0o644)
        self.refused(self.controller.inspect_floor,
                     "UNSAFE_CLOCK_FLOOR_LEDGER")
        self.controller.ledger_path.chmod(0o600)
        self.enrollment.chmod(0o755)
        self.refused(self.issue,
                     "UNSAFE_DISPOSABLE_CONTROLLER_DIRECTORY")
        self.enrollment.chmod(0o700)

    def test_existing_enrollment_symlink_never_overwritten(self):
        other=self.h.base/"untrusted-target"
        other.write_text("preserve")
        (self.enrollment/Session.SESSION_FILE).symlink_to(other)
        self.refused(self.issue,"UNSAFE_EXISTING_SESSION_FILE")
        self.assertEqual(other.read_text(),"preserve")
        # Floor was already durably advanced, no same-version recovery.
        self.refused(self.issue,"MONOTONIC_CLOCK_RELEASE_REPLAY")

    def test_two_contending_issuers_cannot_both_publish_same_version(self):
        gate=threading.Barrier(2)
        results=[]
        lock=threading.Lock()
        def run():
            gate.wait()
            try:
                self.issue(self.make())
                outcome="issued"
            except Controller.Refused:
                outcome="refused"
            with lock:
                results.append(outcome)
        a=threading.Thread(target=run)
        b=threading.Thread(target=run)
        a.start();b.start()
        a.join(timeout=8);b.join(timeout=8)
        self.assertFalse(a.is_alive())
        self.assertFalse(b.is_alive())
        self.assertEqual(sorted(results),["issued","refused"])
        self.assertTrue(self.controller.inspect_floor()["floorRecorded"])

    def test_untrusted_user_cannot_invoke_protected_controller_paths(self):
        self.refused(lambda:self.make(synthetic=False),
                     "PROTECTED_CONTROLLER_DIRECTORY_REQUIRED")
        self.refused(lambda:self.make(state=self.h.base),
                     "DISPOSABLE_CONTROLLER_DIRECTORY_REQUIRED")
        self.refused(lambda:self.make(enrollment=self.h.base),
                     "DISPOSABLE_CONTROLLER_DIRECTORY_REQUIRED")
        self.refused(lambda:self.make(floor=(True,1)),
                     "TRUSTED_CLOCK_ISSUER_INPUT_REQUIRED")
        self.assertEqual(str(Controller.PROTECTED_STATE),
                         "/var/lib/post-apollo/clock/controller-v1")

    def test_existing_b2b12_native_supervisor_remains_unprovisioned(self):
        source=CONTROLLER_FILE.read_text()
        server=(ROOT/"services/time/AlarmNativeClockSupervisor.py").read_text()
        qml=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        self.assertIn("APPROVED_CLOCK_RELEASE_ROOT_SHA256 = None",server)
        self.assertIn("APPROVED_CLOCK_RELEASE_FLOOR = None",server)
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',qml)
        self.assertNotIn("AlarmClockReleaseFloorController",qml)
        for dangerous in ("notify-send","systemctl --user enable",
                          "alarmFile.setText","SoundEffect","canRing=True"):
            self.assertNotIn(dangerous,source)
        self.assertIn('"canTransferOwnership": False',source)
        self.assertIn('"canRing": False',source)


if __name__=="__main__":
    unittest.main()
