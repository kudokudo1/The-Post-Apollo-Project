"""BG1-B2B9 installed Clock role trust preflight, fixture and deny-only."""
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

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

BASE = Path(__file__).resolve().parents[2]
MODULE = BASE/"services/time/AlarmInstalledRoleTrustPreflight.py"
spec = importlib.util.spec_from_file_location("clock_b2b9_test", MODULE)
Trust = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = Trust
spec.loader.exec_module(Trust)
Role = Trust.Role

CLIENT = '''
import socket,sys,time
conn=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
conn.connect(sys.argv[1])
conn.sendall(b"R")
time.sleep(60)
'''


class ClockB2B9InstalledRoleTrustTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="clock-b2b9-ci-")
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.directory=self.base/"bg1-installed-role-fixture"
        self.directory.mkdir(mode=0o700)
        self.entrypoint=self.base/"old-clock-bridge-test.py"
        self.entrypoint.write_text(CLIENT,encoding="utf-8")
        self.entrypoint.chmod(0o600)
        self.interpreter=os.path.realpath(sys.executable)
        self.sock=str(self.base/"signed-clock-origin.sock")
        self.listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.bind(self.sock)
        self.listener.listen(1)
        self.listener.settimeout(5)
        self.argv=[self.interpreter,"-I","-B",str(self.entrypoint),self.sock]
        self.proc=subprocess.Popen(
            self.argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        self.addCleanup(self.stop)
        self.connection,_=self.listener.accept()
        self.addCleanup(self.connection.close)
        self.assertEqual(self.connection.recv(1),b"R")
        self.witness=Role._Peer.capture(self.connection,self.interpreter)
        self.addCleanup(Role._Peer.close,self.witness)
        self.issuer=Ed25519PrivateKey.generate()
        self.root_bytes=self.issuer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.pin=hashlib.sha256(self.root_bytes).hexdigest()
        self.root_path=self.directory/Trust.ROOT_NAME
        self.policy_path=self.directory/"clock-clock-ui-bridge-origin-v1.json"
        self.sig_path=self.directory/"clock-clock-ui-bridge-origin-v1.sig"
        self.policy={
            "schema":Role.SCHEMA,
            "purpose":Role.PURPOSE,
            "role":"clock-ui-bridge",
            "releaseEpoch":5,
            "releaseSequence":12,
            "entrypointPath":str(self.entrypoint),
            "entrypointSha256":hashlib.sha256(self.entrypoint.read_bytes()).hexdigest(),
            "interpreterPath":self.interpreter,
            "argv":self.argv,
            "uid":os.getuid(),
            "gid":os.getgid()
        }
        self.write_policy()

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)

    def write_policy(self, *, policy=None, signer=None, root=None):
        body=Role.canonical(self.policy if policy is None else policy)
        signing_key=self.issuer if signer is None else signer
        for path,data in (
            (self.root_path,self.root_bytes if root is None else root),
            (self.policy_path,body),
            (self.sig_path,signing_key.sign(Role.DOMAIN+body))):
            path.write_bytes(data)
            path.chmod(0o600)

    def loader(self, *, pin=None, role="clock-ui-bridge",
               floor=(5,12), disposable=True,directory=None):
        return Trust.ClockInstalledRoleTrustPreflight(
            trust_directory=self.directory if directory is None else directory,
            pinned_root_sha256=self.pin if pin is None else pin,
            expected_role=role,
            minimum_epoch=floor[0],
            minimum_sequence=floor[1],
            disposable_test_mode=disposable)

    def inspect(self,loader=None,pid=None,ticks=None):
        return (self.loader() if loader is None else loader).inspect(
            self.connection,self.witness,
            expected_pid=self.proc.pid if pid is None else pid,
            expected_start_ticks=self.witness["ticks"] if ticks is None else ticks)

    def refused(self,callback,code):
        with self.assertRaises(Trust.Refused) as caught:
            callback()
        self.assertEqual(str(caught.exception),code)

    def test_actual_af_unix_pidfd_and_independent_signed_bundle_still_deny(self):
        observed=self.inspect()
        self.assertTrue(observed["originObserved"])
        self.assertTrue(observed["rootFingerprintMatched"])
        self.assertTrue(observed["signedRoleMatched"])
        self.assertTrue(observed["processMatched"])
        self.assertTrue(observed["fixtureOnly"])
        self.assertEqual(observed["observedPid"],self.proc.pid)
        self.assertEqual((observed["releaseEpoch"],observed["releaseSequence"]),(5,12))
        for flag in ("roleAuthenticated","writerStopped","releaseAcknowledged",
                     "ownsRealAlarmFile","canTransferOwnership","canRing",
                     "canNotify"):
            self.assertIs(observed[flag],False)

    def test_unpinned_and_wrong_root_refuse(self):
        self.refused(lambda:self.loader(pin="f"*64).inspect(
            self.connection,self.witness,expected_pid=self.proc.pid,
            expected_start_ticks=self.witness["ticks"]),
            "UNTRUSTED_CLOCK_RELEASE_ROOT")
        self.refused(lambda:self.loader(pin="nothex"),
                     "INDEPENDENT_CLOCK_TRUST_PIN_REQUIRED")
        self.refused(lambda:self.loader(pin=True),
                     "INDEPENDENT_CLOCK_TRUST_PIN_REQUIRED")
        other=Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.write_policy(root=other)
        self.refused(lambda:self.inspect(),"UNTRUSTED_CLOCK_RELEASE_ROOT")

    def test_wrong_signature_from_other_root_refuses(self):
        self.write_policy(signer=Ed25519PrivateKey.generate())
        self.refused(lambda:self.inspect(),"UNTRUSTED_CLOCK_SIGNED_ROLE")

    def test_release_rollback_and_role_mismatch_refuse(self):
        self.refused(lambda:self.inspect(self.loader(floor=(5,13))),
                     "CLOCK_RELEASE_FLOOR_ROLLBACK")
        self.refused(lambda:self.inspect(self.loader(floor=(6,1))),
                     "CLOCK_RELEASE_FLOOR_ROLLBACK")
        wrong=dict(self.policy,role="clock-background-worker")
        self.write_policy(policy=wrong)
        self.refused(lambda:self.inspect(),"WRONG_INSTALLED_CLOCK_ROLE")
        self.assertFalse((BASE/"services/time/AlarmManagerService.qml").read_text().
                         __contains__("AlarmInstalledRoleTrustPreflight"))

    def test_root_and_policy_symlink_refuse(self):
        bogus=self.base/"bogus-root"
        bogus.write_bytes(self.root_bytes)
        self.root_path.unlink()
        self.root_path.symlink_to(bogus)
        self.refused(lambda:self.inspect(),"TRUST_FILE_UNAVAILABLE_OR_LINKED")
        self.root_path.unlink()
        self.write_policy()
        other=self.base/"substitute"
        other.mkdir(mode=0o700)
        self.directory.rename(other/"old")
        self.directory.symlink_to(other/"old")
        self.refused(lambda:self.loader(),"UNSAFE_DISPOSABLE_TRUST_DIRECTORY")

    def test_group_world_writable_files_or_directory_refuse(self):
        for target in (self.root_path,self.sig_path,self.policy_path):
            with self.subTest(target=target.name):
                target.chmod(0o666)
                self.refused(lambda:self.inspect(),"UNSAFE_CLOCK_TRUST_FILE")
                target.chmod(0o600)
        self.directory.chmod(0o755)
        self.refused(lambda:self.loader(),"UNSAFE_DISPOSABLE_TRUST_DIRECTORY")

    def test_entrypoint_tampering_and_kernel_peer_exit_refuse(self):
        self.assertTrue(self.inspect()["originObserved"])
        self.entrypoint.write_text(CLIENT+"\n# tampered\n",encoding="utf-8")
        self.refused(lambda:self.inspect(),"INSTALLED_CLOCK_PROCESS_NOT_VERIFIED")
        self.entrypoint.write_text(CLIENT,encoding="utf-8")
        self.stop()
        self.refused(lambda:self.inspect(),"INSTALLED_CLOCK_PROCESS_NOT_VERIFIED")

    def test_independently_pinned_pid_and_start_ticks_are_required(self):
        self.refused(lambda:self.inspect(pid=self.proc.pid+1),
                     "INSTALLED_CLOCK_PROCESS_NOT_VERIFIED")
        self.refused(lambda:self.inspect(ticks=self.witness["ticks"]+1),
                     "INSTALLED_CLOCK_PROCESS_NOT_VERIFIED")
        self.refused(lambda:self.inspect(pid=True),
                     "INDEPENDENT_PROCESS_PIN_REQUIRED")
        self.refused(lambda:self.inspect(ticks=0),
                     "INDEPENDENT_PROCESS_PIN_REQUIRED")

    def test_protected_real_path_cannot_be_bypassed_by_fixture(self):
        self.refused(lambda:self.loader(disposable=False),
                     "INSTALLED_CLOCK_TRUST_PATH_REQUIRED")
        self.refused(lambda:self.loader(directory=self.base),
                     "DISPOSABLE_TRUST_DIRECTORY_REQUIRED")
        self.refused(lambda:self.loader(role="identity-gateway"),
                     "INDEPENDENT_CLOCK_TRUST_PIN_REQUIRED")
        self.refused(lambda:self.loader(floor=(True,1)),
                     "INDEPENDENT_CLOCK_TRUST_PIN_REQUIRED")

    def test_unknown_fields_or_wrong_signing_domain_refuse(self):
        forged=dict(self.policy,extraOwnerAuthority=True)
        self.write_policy(policy=forged)
        self.refused(lambda:self.inspect(),"INVALID_INSTALLED_CLOCK_ROLE_POLICY")
        self.write_policy()
        # Signed by the right issuer but under the wrong application domain.
        self.sig_path.write_bytes(self.issuer.sign(
            b"postapollo.identity.gateway.release\x00"+self.policy_path.read_bytes()))
        self.refused(lambda:self.inspect(),"UNTRUSTED_CLOCK_SIGNED_ROLE")

    def test_role_bundle_rechecked_after_process_measurement(self):
        from unittest.mock import patch
        loader=self.loader()
        original=loader._load_bundle
        calls=[0]
        def changed():
            calls[0]+=1
            if calls[0]==2:
                old=self.policy_path.read_bytes()
                altered=dict(self.policy,releaseSequence=13)
                self.write_policy(policy=altered)
                assert self.policy_path.read_bytes()!=old
            return original()
        with patch.object(loader,"_load_bundle",side_effect=changed):
            self.refused(lambda:self.inspect(loader),
                         "CLOCK_ROLE_POLICY_CHANGED_DURING_PROBE")

    def test_no_user_desktop_changes_or_unapproved_install(self):
        live=(BASE/"services/time/AlarmManagerService.qml").read_text()
        code=MODULE.read_text()
        assert 'alarmWriterBarrierPhase: "ACTIVE"' in live
        assert "AlarmInstalledRoleTrustPreflight" not in live
        for forbidden in ("setText(", "systemctl","notify-send",
                          "subprocess.Popen(", "os.replace(", "canRing=True"):
            self.assertNotIn(forbidden,code)
        self.assertIn('"roleAuthenticated": False',code)
        self.assertIn('"canTransferOwnership": False',code)
        self.assertIn('"canRing": False',code)


if __name__=="__main__":
    unittest.main()
