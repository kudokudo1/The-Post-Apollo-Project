"""BG1-B2B12: actual AF_UNIX kernel peer + independently signed enrollment.

The real installed path is READ-ONLY and unprovisioned. All signing keys,
manifest files, program files and sockets created in these tests are
disposable. No systemd, Quickshell or real alarm state is touched.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parents[2]
B2B9=ROOT/"tests/time/test_clock_bg1_b2b9_installed_role_trust.py"
ENROLL=ROOT/"services/time/AlarmProtectedSessionEnrollment.py"
SUPERVISOR=ROOT/"services/time/AlarmNativeClockSupervisor.py"


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=result
    spec.loader.exec_module(result)
    return result


Harness=load(B2B9,"clock_b2b12_original_fixture")
Session=load(ENROLL,"clock_b2b12_signed_session")
Server=load(SUPERVISOR,"clock_b2b12_native_server")


class ClockB2B12ProtectedEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness.ClockB2B9InstalledRoleTrustTests(
            methodName="test_actual_af_unix_pidfd_and_independent_signed_bundle_still_deny")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        self.directory=self.h.base/Session.TEST_ENROLLMENT_NAME
        self.directory.mkdir(mode=0o700)
        self.manifest_file=self.directory/Session.SESSION_FILE
        self.signature_file=self.directory/Session.SIGNATURE_FILE
        self.enrollment={
            "schema":Session.SCHEMA,
            "purpose":Session.PURPOSE,
            "role":"clock-ui-bridge",
            "bootId":Session._kernel_boot(),
            "pid":self.h.proc.pid,
            "startTicks":self.h.witness["ticks"],
            "uid":os.getuid(),
            "gid":os.getgid(),
            "releaseEpoch":5,
            "releaseSequence":12,
            "socketScope":Session.SOCKET_SCOPE,
        }
        self.write()

    def write(self, overrides=None, signer=None, raw=None):
        data=dict(self.enrollment)
        data.update(overrides or {})
        raw=Session.canonical(data) if raw is None else raw
        key=self.h.issuer if signer is None else signer
        for path,content in (
            (self.manifest_file,raw),
            (self.signature_file,key.sign(Session.DOMAIN+raw))):
            path.write_bytes(content)
            path.chmod(0o600)

    def loader(self, *, fingerprint=None, floor=(5,12),
               trust=None, directory=None, synthetic=True):
        return Session.ClockProtectedSessionEnrollment(
            enrollment_directory=self.directory if directory is None
                else directory,
            trust_directory=self.h.directory if trust is None else trust,
            pinned_root_sha256=self.h.pin if fingerprint is None else fingerprint,
            minimum_epoch=floor[0],minimum_sequence=floor[1],
            synthetic_only=synthetic)

    def refused(self,fn,reason):
        with self.assertRaises(Session.Refused) as caught:
            fn()
        self.assertEqual(str(caught.exception),reason)

    def test_signed_enrollment_links_original_kernel_pidfd_and_installed_role(self):
        value=self.loader().inspect(self.h.connection)
        self.assertTrue(value["originObserved"])
        self.assertTrue(value["signedSessionObserved"])
        self.assertTrue(value["sameKernelPeer"])
        self.assertTrue(value["sameReleaseEpoch"])
        self.assertTrue(value["bootMatched"])
        self.assertTrue(value["fixtureOnly"])
        for key in ("roleAuthenticated","writerStopped","releaseAcknowledged",
                    "oldWriterRestartPrevented","ownsRealAlarmFile",
                    "canTransferOwnership","canRing","canNotify"):
            self.assertIs(value[key],False,key)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode),0o700)

    def test_wrong_public_root_or_missing_independent_floor_denied(self):
        self.refused(lambda:self.loader(
            fingerprint="f"*64).inspect(self.h.connection),
            "CLOCK_ROLE_TRUST_NOT_VERIFIED")
        self.refused(lambda:self.loader(floor=(0,12)),
                     "INDEPENDENT_CLOCK_RELEASE_FLOOR_REQUIRED")
        self.refused(lambda:self.loader(floor=(True,12)),
                     "INDEPENDENT_CLOCK_RELEASE_FLOOR_REQUIRED")
        self.refused(lambda:self.loader(
            fingerprint="self-supplied-root"),
            "INDEPENDENT_CLOCK_TRUST_PIN_REQUIRED")

    def test_wrong_signed_session_key_and_cross_purpose_domain_rejected(self):
        self.write(signer=Ed25519PrivateKey.generate())
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "WRONG_CLOCK_SESSION_SIGNATURE")
        self.write()
        raw=self.manifest_file.read_bytes()
        self.signature_file.write_bytes(self.h.issuer.sign(
            b"postapollo.identity.session\x00"+raw))
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "WRONG_CLOCK_SESSION_SIGNATURE")

    def test_wrong_kernel_process_pid_or_ticks_are_denied(self):
        for update in (
            {"pid":self.h.proc.pid+1},
            {"startTicks":self.h.witness["ticks"]+1},
            {"uid":os.getuid()+1},
            {"gid":os.getgid()+1},
        ):
            with self.subTest(update=update):
                self.write(update)
                self.refused(lambda:self.loader().inspect(self.h.connection),
                             ("SESSION_AND_ROLE_CREDENTIALS_DIFFER"
                              if "uid" in update or "gid" in update else
                              "SIGNED_SESSION_AND_KERNEL_PEER_DIFFER"))
        self.write()

    def test_session_role_release_version_and_minimum_floor_enforced(self):
        for value in ({"releaseEpoch":6},{"releaseSequence":13}):
            with self.subTest(value=value):
                self.write(value)
                self.refused(lambda:self.loader().inspect(self.h.connection),
                             "SESSION_AND_INSTALLED_ROLE_RELEASE_DIFFER")
        self.write()
        self.refused(lambda:self.loader(floor=(5,13)).inspect(
            self.h.connection),"CLOCK_ROLE_TRUST_NOT_VERIFIED")
        self.write({"role":"clock-background-worker"})
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "INVALID_SIGNED_SESSION_POLICY")

    def test_previous_boot_manifest_is_never_recovered_by_pid_reuse(self):
        self.write({"bootId":"11111111-1111-1111-1111-111111111111"})
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "SIGNED_SESSION_PREVIOUS_BOOT")

    def test_manifest_rejects_duplicate_keys_noncanonical_and_bool_pid(self):
        cases=[
            b'{"pid":1,"pid":2}',
            b'{"role":"clock-ui-bridge", "pid":8}',
            b'[]',
            b'{"pid":NaN}',
            Session.canonical(dict(self.enrollment,pid=True)),
            Session.canonical(dict(self.enrollment,ownerGranted=True)),
            Session.canonical(dict(self.enrollment,
                                   socketScope="../clock-supervisor-v1.sock")),
        ]
        for raw in cases:
            with self.subTest(raw=raw[:50]):
                with self.assertRaises(Session.Refused):
                    Session._manifest(raw)

    def test_protected_file_symlink_permissions_and_directory_scopes(self):
        other=self.h.base/"untrusted-session"
        other.write_bytes(self.manifest_file.read_bytes())
        self.manifest_file.unlink()
        self.manifest_file.symlink_to(other)
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "SIGNED_SESSION_UNAVAILABLE_OR_LINKED")
        self.manifest_file.unlink()
        self.write()
        self.signature_file.chmod(0o666)
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "UNSAFE_SIGNED_SESSION_FILE")
        self.signature_file.chmod(0o600)
        self.directory.chmod(0o755)
        self.refused(lambda:self.loader(),"UNSAFE_DISPOSABLE_SESSION_DIRECTORY")
        self.directory.chmod(0o700)
        self.refused(lambda:self.loader(directory=self.h.base),
                     "DISPOSABLE_SESSION_DIRECTORY_REQUIRED")
        self.refused(lambda:self.loader(trust=self.h.base),
                     "DISPOSABLE_TRUST_DIRECTORY_REQUIRED")

    def test_no_user_path_can_pose_as_root_owned_production_enrollment(self):
        self.refused(lambda:self.loader(synthetic=False),
                     "INSTALLED_CLOCK_TRUST_PATH_REQUIRED")
        self.assertEqual(str(Session.INSTALL_ENROLLMENT_DIR),
                         "/run/post-apollo/clock/sessions-v1")
        self.assertEqual(str(Session.Origin.TRUST_DIR),
                         "/usr/share/post-apollo/clock/trust-v1")

    def test_changed_installed_executable_and_exited_peer_refuse(self):
        self.assertTrue(self.loader().inspect(self.h.connection)["originObserved"])
        self.h.entrypoint.write_text(
            self.h.entrypoint.read_text()+"\n# tampered\n",encoding="utf-8")
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "SIGNED_SESSION_PROCESS_ORIGIN_REFUSED")
        self.h.entrypoint.write_text(Harness.CLIENT,encoding="utf-8")
        self.h.stop()
        self.refused(lambda:self.loader().inspect(self.h.connection),
                     "SIGNED_SESSION_KERNEL_PEER_REFUSED")

    def test_signed_session_rechecked_for_changes_after_peer_inspection(self):
        origin=self.loader()
        original=origin._load
        invoked=[0]
        def swapped():
            invoked[0]+=1
            if invoked[0]==2:
                self.write({"startTicks":self.h.witness["ticks"]+1})
            return original()
        with patch.object(origin,"_load",side_effect=swapped):
            self.refused(lambda:origin.inspect(self.h.connection),
                         "SIGNED_SESSION_BUNDLE_CHANGED")
        self.assertEqual(invoked[0],2)

    def test_production_supervisor_has_no_issuer_or_enrollment_override(self):
        self.assertIsNone(Server.APPROVED_CLOCK_RELEASE_ROOT_SHA256)
        self.assertIsNone(Server.APPROVED_CLOCK_RELEASE_FLOOR)
        original=SUPERVISOR.read_text()
        qml=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',qml)
        self.assertIn("ProtectedEnrollment.ClockProtectedSessionEnrollment",
                      original)
        self.assertIn("self._observe_installed(conn)",original)
        self.assertNotIn("AlarmProtectedSessionEnrollment",qml)
        self.assertNotIn("APPROVED_CLOCK_RELEASE_ROOT_SHA256 = os.environ",
                         original)
        self.assertNotIn("APPROVED_CLOCK_RELEASE_FLOOR = os.environ",
                         original)
        self.assertIn('"canRing":False',ENROLL.read_text())
        self.assertIn('"canTransferOwnership":False',ENROLL.read_text())

    def test_read_only_no_host_mutation_or_alarm_actuation(self):
        text=ENROLL.read_text()
        for forbidden in (
            "subprocess.Popen(","os.replace(","write_text(","notify-send",
            "systemctl","alarmFile.setText(","canRing=True",
            "Ed25519PrivateKey.generate","chmod(","mkdir("):
            self.assertNotIn(forbidden,text)
        observed=self.loader().inspect(self.h.connection)
        self.assertFalse(observed["canRing"])
        self.assertFalse(observed["canTransferOwnership"])


if __name__=="__main__":
    unittest.main()
