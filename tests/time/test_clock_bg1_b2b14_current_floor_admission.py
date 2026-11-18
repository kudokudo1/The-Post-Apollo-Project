"""Clock BG1-B2B14 signed BLOCKED/CURRENT floor and native admission tests.

Disposable independent Ed25519 Clock issuer + real Linux AF_UNIX old
process. No root-owned host files or alarm services are touched.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parents[2]
HARNESS=ROOT/"tests/time/test_clock_bg1_b2b13_release_floor_controller.py"
FLOOR_PATH=ROOT/"services/time/AlarmCurrentFloorWitness.py"


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


Harness=load(HARNESS,"clock_b2b14_real_controller_fixture")
Controller=Harness.Controller
Session=Controller.Session
Floor=Controller.Floor


class ClockB2B14SignedFloorTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness.ClockB2B13ControllerTests(
            methodName="test_real_signed_process_issues_b2b12_reader_compatible_session")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        self.c=self.h.controller
        self.old_writer=self.h.h

    def witness(self, floor=(5,12), pin=None):
        return Floor.ClockCurrentFloorWitness(
            enrollment_directory=self.h.enrollment,
            trust_directory=self.old_writer.directory,
            pinned_root_sha256=self.old_writer.pin if pin is None else pin,
            minimum_epoch=floor[0],minimum_sequence=floor[1],
            synthetic_only=True)

    def refused(self,fn,code,kind=Floor.Refused):
        with self.assertRaises(kind) as e:
            fn()
        self.assertEqual(str(e.exception),code)

    def raw_session(self):
        return (self.h.enrollment/Session.SESSION_FILE).read_bytes()

    def signed_snapshot(self,data):
        raw=Floor.canonical(data)
        signature=self.old_writer.issuer.sign(Floor.DOMAIN+raw)
        for name,blob in ((Floor.MANIFEST_FILE,raw),
                          (Floor.SIGNATURE_FILE,signature)):
            Controller._durable_publish(
                self.h.enrollment,name,blob,synthetic=True)

    def test_real_controller_to_readonly_floor_to_b2b12_kernel_peer(self):
        result=self.h.issue()
        self.assertTrue(result["signedSessionPublished"])
        view=self.witness()
        current=view.inspect_current()
        self.assertTrue(current["floorSignatureVerified"])
        self.assertEqual((current["releaseEpoch"],current["releaseSequence"]),(5,12))
        self.assertTrue(view.compare_session(self.raw_session())["current"])
        verified=self.h.reader().inspect(self.old_writer.connection)
        self.assertTrue(verified["signedSessionObserved"])
        for flag in Floor.AUTHORITY_FLAGS:
            self.assertIs(current[flag],False)
        self.assertFalse(verified["canTransferOwnership"])

    def test_missing_floor_rejects_even_when_b2b12_signature_valid(self):
        self.h.issue()
        self.assertTrue(self.h.reader().inspect(self.old_writer.connection)[
            "signedSessionObserved"])
        (self.h.enrollment/Floor.MANIFEST_FILE).unlink()
        self.refused(lambda:self.witness().inspect_current(),
                     "CURRENT_FLOOR_FILE_UNVERIFIED")

    def test_signed_blocked_state_denies_an_existing_valid_session(self):
        self.h.issue()
        current=self.witness().read_signed()
        blocked=dict(current,state="BLOCKED")
        self.signed_snapshot(blocked)
        self.refused(lambda:self.witness().compare_session(
            self.raw_session()),"CONTROLLER_ISSUANCE_BLOCKED")
        self.assertFalse(self.h.reader().inspect(
            self.old_writer.connection)["canRing"])

    def test_controller_publish_after_higher_signed_epoch_supersedes_old(self):
        self.h.issue()
        old=self.raw_session()
        successor=self.h.reissue_with_new_process(5,13)
        self.assertTrue(self.h.issue(successor)["signedSessionPublished"])
        view=self.witness(floor=(5,13))
        self.refused(lambda:view.compare_session(old),
                     "SIGNED_SESSION_NOT_CURRENT_FLOOR")
        self.assertTrue(view.compare_session(self.raw_session())["current"])
        self.assertTrue(self.h.reader((5,13)).inspect(
            self.old_writer.connection)["signedSessionObserved"])

    def test_current_floor_signature_wrong_key_and_domain_refuse(self):
        self.h.issue()
        manifest=self.h.enrollment/Floor.MANIFEST_FILE
        sig=self.h.enrollment/Floor.SIGNATURE_FILE
        signed=manifest.read_bytes()
        sig.write_bytes(Ed25519PrivateKey.generate().sign(
            Floor.DOMAIN+signed))
        self.refused(lambda:self.witness().inspect_current(),
                     "FLOOR_SIGNATURE_NOT_TRUSTED")
        sig.write_bytes(self.old_writer.issuer.sign(
            b"postapollo.identity.current-floor\x00"+signed))
        self.refused(lambda:self.witness().inspect_current(),
                     "FLOOR_SIGNATURE_NOT_TRUSTED")
        # The pin is syntactically valid, but B2B9 refuses its mismatch
        # when reading the independently installed Clock public key.
        self.refused(lambda:self.witness(pin="e"*64).inspect_current(),
                     "CLOCK_FLOOR_ROLE_NOT_VERIFIED")

    def test_floor_malformed_duplicate_bool_and_noncanonical_refuse(self):
        self.h.issue()
        payload=self.witness().read_signed()
        for wrong in (
            b'{"releaseEpoch":5,"releaseEpoch":6}',
            b'{"state":"CURRENT", "schema":"x"}',
            b"[]",b'{"releaseEpoch":NaN}',
            Floor.canonical(dict(payload,releaseEpoch=True)),
            Floor.canonical(dict(payload,ownerGranted=True)),
        ):
            with self.subTest(raw=wrong[:70]):
                with self.assertRaises(Floor.Refused):
                    Floor.validate(wrong)

    def test_signed_previous_boot_or_role_version_is_refused(self):
        self.h.issue()
        previous=self.witness().read_signed()
        self.signed_snapshot(dict(
            previous,bootId="11111111-1111-1111-1111-111111111111"))
        self.refused(lambda:self.witness().inspect_current(),
                     "SIGNED_FLOOR_WRONG_BOOT")
        self.signed_snapshot(dict(previous,releaseSequence=13))
        self.refused(lambda:self.witness().inspect_current(),
                     "CURRENT_FLOOR_ROLE_VERSION_MISMATCH")

    def test_torn_floor_pair_unsafe_symlink_and_permissions_refuse(self):
        self.h.issue()
        snap=self.h.enrollment/Floor.MANIFEST_FILE
        original=snap.read_bytes()
        snap.write_bytes(original+b" ")
        self.refused(lambda:self.witness().inspect_current(),
                     "FLOOR_SIGNATURE_NOT_TRUSTED")
        snap.unlink()
        victim=self.old_writer.base/"do-not-touch"
        victim.write_text("protected")
        snap.symlink_to(victim)
        self.refused(lambda:self.witness().inspect_current(),
                     "CURRENT_FLOOR_FILE_UNVERIFIED")
        self.assertEqual(victim.read_text(),"protected")
        snap.unlink()
        snap.write_bytes(original)
        snap.chmod(0o666)
        self.refused(lambda:self.witness().inspect_current(),
                     "CURRENT_FLOOR_FILE_UNVERIFIED")

    def test_blocked_pair_published_before_sql_commit_refuses_on_crash(self):
        orig=Controller._durable_publish
        def interrupt(directory,name,raw,*,synthetic):
            orig(directory,name,raw,synthetic=synthetic)
            if name==Floor.SIGNATURE_FILE and (
                    Floor.validate((directory/Floor.MANIFEST_FILE).
                                   read_bytes())["state"]=="BLOCKED"):
                raise Controller.Refused("TEST_FAIL_AFTER_BLOCKED")
        with patch.object(Controller,"_durable_publish",
                          side_effect=interrupt):
            self.refused(self.h.issue,"TEST_FAIL_AFTER_BLOCKED",
                         Controller.Refused)
        self.assertFalse(self.c.inspect_floor()["floorRecorded"])
        self.refused(lambda:self.witness().inspect_current(),
                     "CONTROLLER_ISSUANCE_BLOCKED")
        self.refused(self.h.issue,"PRIOR_SIGNED_FLOOR_VERSION_REPLAY",
                     Controller.Refused)

    def test_sql_commit_before_current_publication_still_denies(self):
        orig=Controller._durable_publish
        def interrupt(directory,name,raw,*,synthetic):
            if name==Floor.MANIFEST_FILE and (
                    Floor.validate(raw)["state"]=="CURRENT"):
                raise Controller.Refused("TEST_FAIL_AFTER_SQL")
            return orig(directory,name,raw,synthetic=synthetic)
        with patch.object(Controller,"_durable_publish",
                          side_effect=interrupt):
            self.refused(self.h.issue,"TEST_FAIL_AFTER_SQL",
                         Controller.Refused)
        self.assertTrue(self.c.inspect_floor()["floorRecorded"])
        self.refused(lambda:self.witness().inspect_current(),
                     "CONTROLLER_ISSUANCE_BLOCKED")
        self.refused(self.h.issue,"MONOTONIC_CLOCK_RELEASE_REPLAY",
                     Controller.Refused)

    def test_current_snapshot_before_new_session_publication_denies_old(self):
        self.h.issue()
        old=self.raw_session()
        successor=self.h.reissue_with_new_process(5,13)
        orig=Controller._durable_publish
        def fail_new_session(directory,name,raw,*,synthetic):
            if name==Session.SESSION_FILE:
                raise Controller.Refused("TEST_NEW_SESSION_NOT_PUBLISHED")
            return orig(directory,name,raw,synthetic=synthetic)
        with patch.object(Controller,"_durable_publish",
                          side_effect=fail_new_session):
            self.refused(lambda:self.h.issue(successor),
                         "TEST_NEW_SESSION_NOT_PUBLISHED",Controller.Refused)
        self.refused(lambda:self.witness((5,13)).compare_session(old),
                     "SIGNED_SESSION_NOT_CURRENT_FLOOR")
        self.assertEqual(successor.inspect_floor()["latestSequence"],13)

    def test_issuer_refuses_legacy_db_without_signed_floor_pair(self):
        self.h.issue()
        (self.h.enrollment/Floor.MANIFEST_FILE).unlink()
        (self.h.enrollment/Floor.SIGNATURE_FILE).unlink()
        successor=self.h.reissue_with_new_process(5,13)
        self.refused(lambda:self.h.issue(successor),
                     "PRIOR_SIGNED_FLOOR_UNVERIFIED",
                     Controller.Refused)
        self.assertEqual(self.c.inspect_floor()["latestSequence"],12)

    def test_floor_change_after_first_observation_detected(self):
        self.h.issue()
        witness=self.witness()
        old=witness.compare_session(self.raw_session())
        expected=(old["releaseEpoch"],old["releaseSequence"],
                  old["sessionSha256"])
        successor=self.h.reissue_with_new_process(5,13)
        self.h.issue(successor)
        with self.assertRaises(Floor.Refused):
            witness.compare_session(self.raw_session(),expected=expected)

    def test_native_installed_path_requires_floor_and_remains_deny_only(self):
        native=(ROOT/"services/time/AlarmNativeClockSupervisor.py").read_text()
        qml=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        self.assertIn("CurrentFloor.ClockCurrentFloorWitness",native)
        self.assertIn("witness.compare_session(bundle[0])",native)
        self.assertIn("witness.compare_session(after[0],expected=expected)",native)
        self.assertIn("APPROVED_CLOCK_RELEASE_ROOT_SHA256 = None",native)
        self.assertIn("APPROVED_CLOCK_RELEASE_FLOOR = None",native)
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',qml)
        self.assertNotIn("ClockCurrentFloorWitness",qml)
        for source in (FLOOR_PATH.read_text(),
                       (ROOT/"services/time/AlarmClockReleaseFloorController.py").
                       read_text()):
            for forbidden in ("alarmFile.setText", "notify-send",
                              "systemctl --user enable","canRing=True"):
                self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
