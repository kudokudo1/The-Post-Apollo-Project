"""BG1-B2B7: real Linux process signed origin AND signed one-use reply.

Every successful result remains deny-only; this is disposable CI evidence,
not a running Quickshell writer, installed identity or writer-release proof.
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

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/time/AlarmRoleBoundReleasePreflight.py"
spec = importlib.util.spec_from_file_location("clock_b2b7_test_chain", SOURCE)
Chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Chain)
Role = Chain.Role
Receipt = Chain.Receipt

CHILD = r'''
import json, os, socket, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
seed=bytes.fromhex(sys.stdin.readline().strip())
signer=Ed25519PrivateKey.from_private_bytes(seed)
peer=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
peer.connect(sys.argv[1])
peer.sendall(b"R")
for line in peer.makefile("rb"):
    msg=json.loads(line)
    start=int(open("/proc/self/stat").read().rsplit(") ",1)[1].split()[19])
    reply={"schema":"postapollo.clock.bg1-b2b5-synthetic-release-receipt.v1",
           "challenge":msg["challenge"],"sourceDigest":msg["sourceDigest"],
           "oldEpoch":msg["oldEpoch"],"newEpoch":msg["newEpoch"],
           "peerPid":os.getpid(),"peerStartTicks":start}
    body=json.dumps(reply,sort_keys=True,separators=(",",":"),
                    ensure_ascii=True).encode("ascii")
    signature=signer.sign(
        b"postapollo.clock.bg1-b2b5-synthetic-release.v1\x00"+body)
    peer.sendall(json.dumps({"body":body.hex(),"sig":signature.hex()},
                          separators=(",",":")).encode()+b"\n")
'''


class ClockB2B7RoleBoundRelease(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="clock-b2b7-ci-")
        self.addCleanup(temp.cleanup)
        self.base=Path(temp.name)
        self.synthetic=self.base / "synthetic-quickshell"
        self.synthetic.mkdir(mode=0o700)
        self.fixture_dir=self.base / "bg1-signed-release-fixture"
        self.fixture_dir.mkdir(mode=0o700)
        self.source=self.synthetic / "time-alarms-v2.json"
        self.source.write_text(json.dumps({
            "version":2,"nextId":1,"alarms":[]})+"\n",encoding="utf8")
        self.source.chmod(0o600)
        self.original_source=self.source.read_bytes()

        self.old_key=Ed25519PrivateKey.generate()
        self.origin_root=Ed25519PrivateKey.generate()
        self.reply_root=Ed25519PrivateKey.generate()
        self.interpreter=os.path.realpath(sys.executable)
        self.script=self.base / "clock-ci-old-writer.py"
        self.script.write_text(CHILD, encoding="utf8")
        self.script.chmod(0o600)
        self.socket_path=str(self.base / "role-release.sock")
        self.listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.bind(self.socket_path)
        self.listener.listen(1)
        self.listener.settimeout(5)
        self.argv=[self.interpreter,"-I","-B",str(self.script),self.socket_path]
        self.proc=subprocess.Popen(
            self.argv,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,text=True)
        self.addCleanup(self.stop)
        secret=self.old_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption())
        self.proc.stdin.write(secret.hex()+"\n")
        self.proc.stdin.flush()
        self.conn,_=self.listener.accept()
        self.addCleanup(self.conn.close)
        self.conn.settimeout(5)
        self.assertEqual(self.conn.recv(1),b"R")
        self.peer=Receipt.Peer.capture(self.conn,self.interpreter)
        self.addCleanup(Receipt.Peer.close,self.peer)
        self.assertEqual(self.peer["pid"],self.proc.pid)
        self.clock=[1794408000000]
        self.origin_policy={
            "schema":Role.SCHEMA,"purpose":Role.PURPOSE,
            "role":"clock-ui-bridge",
            "releaseEpoch":5,"releaseSequence":14,
            "entrypointPath":str(self.script),
            "entrypointSha256":hashlib.sha256(self.script.read_bytes()).hexdigest(),
            "interpreterPath":self.interpreter,"argv":self.argv,
            "uid":os.getuid(),"gid":os.getgid()
        }
        self.release_policy={
            "schema":Receipt.POLICY_SCHEMA,"purpose":Receipt.POLICY_PURPOSE,
            "role":"clock-ui-bridge",
            "releaseEpoch":5,"releaseSequence":14,
            "sourceScope":Receipt._source_scope(self.source),
            "interpreterPath":self.interpreter,
            "oldSignerSha256":Receipt._public_digest(self.old_key.public_key()),
            "uid":os.getuid(),"gid":os.getgid()
        }
        self.chain=self.make_chain()

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)
        if self.proc.stdin and not self.proc.stdin.closed:
            self.proc.stdin.close()

    def probe(self, policy=None, *, pid=None, ticks=None, root=None):
        policy=self.origin_policy if policy is None else policy
        signer=self.origin_root if root is None else root
        raw=Role.canonical(policy)
        return Role.SignedClockRoleProbe(
            signed_policy=raw,
            policy_signature=signer.sign(Role.DOMAIN+raw),
            pinned_release_root=self.origin_root.public_key(),
            expected_role=policy["role"],
            minimum_epoch=5, minimum_sequence=14,
            expected_pid=self.proc.pid if pid is None else pid,
            expected_start_ticks=self.peer["ticks"] if ticks is None else ticks,
            disposable_test_mode=True)

    def receipt_fixture(self, policy=None, *, signer=None, pid=None, ticks=None):
        policy=self.release_policy if policy is None else policy
        raw=Receipt._json_bytes(policy)
        signer=self.old_key if signer is None else signer
        return Receipt.SignedWriterReleaseFixture(
            self.fixture_dir,self.source,
            signed_policy=raw,
            policy_signature=self.reply_root.sign(Receipt.AUTH_DOMAIN+raw),
            independent_authority=self.reply_root.public_key(),
            independent_old_signer=signer.public_key(),
            expected_peer_pid=self.proc.pid if pid is None else pid,
            expected_peer_ticks=self.peer["ticks"] if ticks is None else ticks,
            minimum_epoch=5,minimum_sequence=14,synthetic_only=True,
            clock=lambda:self.clock[0])

    def make_chain(self, *, role_policy=None, release_policy=None,
                   probe=None, receipt=None):
        return Chain.RoleBoundReleasePreflight(
            role_probe=probe if probe is not None else self.probe(role_policy),
            signed_receipt_fixture=receipt if receipt is not None
                else self.receipt_fixture(release_policy),
            synthetic_only=True)

    def issue(self, chain=None):
        return (chain or self.chain).issue_observation(
            self.conn,self.peer,
            expected_source_digest=hashlib.sha256(
                self.source.read_bytes()).hexdigest(),
            old_epoch=5,new_epoch=6)

    def answer(self, request):
        self.conn.sendall((json.dumps(request,separators=(",",":"))+"\n").encode())
        response=json.loads(self.conn.makefile("rb").readline())
        return bytes.fromhex(response["body"]),bytes.fromhex(response["sig"])

    def consume(self, body,signature,chain=None):
        return (chain or self.chain).observe_reply(
            self.conn,self.peer,signed_reply=body,signature=signature)

    def refused(self, action, reason):
        with self.assertRaises(Chain.Refused) as caught:
            action()
        self.assertEqual(str(caught.exception),reason)

    def test_one_real_pid_signed_enrollment_and_signed_reply_still_deny(self):
        req=self.issue()
        self.assertTrue(req["signedRoleObserved"])
        self.assertFalse(req["releaseAcknowledged"])
        self.assertFalse(req["canTransferOwnership"])
        body,signature=self.answer(req)
        result=self.consume(body,signature)
        self.assertTrue(result["signedRoleObserved"])
        self.assertTrue(result["signatureObserved"])
        self.assertTrue(result["sameKernelPeer"])
        for field in ("roleAuthenticated","writerStopped",
                      "releaseAcknowledged","canTransferOwnership",
                      "ownsRealAlarmFile","canRing","canNotify"):
            self.assertIs(result[field],False)
        self.assertEqual(self.source.read_bytes(),self.original_source)
        self.refused(lambda:self.consume(body,signature),
                     "SIGNED_RELEASE_REPLY_REFUSED")

    def test_different_signed_epoch_or_sequence_never_compose(self):
        for fields in [
            {"releaseEpoch":6},
            {"releaseSequence":15},
            {"role":"clock-background-worker"},
            {"uid":os.getuid()+1},
        ]:
            with self.subTest(fields=fields):
                policy=dict(self.origin_policy,**fields)
                self.refused(lambda:self.make_chain(role_policy=policy),
                             "SIGNED_ROLE_RELEASE_PINS_MISMATCH")

    def test_different_release_signed_pins_never_compose(self):
        for fields in [
            {"releaseEpoch":6},
            {"releaseSequence":15},
            {"gid":os.getgid()+1},
        ]:
            with self.subTest(fields=fields):
                policy=dict(self.release_policy,**fields)
                self.refused(lambda:self.make_chain(release_policy=policy),
                             "SIGNED_ROLE_RELEASE_PINS_MISMATCH")
        # B2B5 independently refuses a background-worker receipt before
        # B2B7 can compose it; this is the stronger upstream refusal.
        background=dict(self.release_policy,role="clock-background-worker")
        with self.assertRaises(Receipt.Refused) as caught:
            self.make_chain(release_policy=background)
        self.assertEqual(str(caught.exception),
                         "WRONG_SIGNED_CLOCK_RELEASE_POLICY")

    def test_process_pin_mismatch_rejected_before_any_challenge(self):
        self.refused(lambda:self.make_chain(
            probe=self.probe(pid=self.proc.pid+1)),
            "SIGNED_ROLE_RELEASE_PINS_MISMATCH")
        self.refused(lambda:self.make_chain(
            receipt=self.receipt_fixture(ticks=self.peer["ticks"]+1)),
            "SIGNED_ROLE_RELEASE_PINS_MISMATCH")
        self.assertFalse((self.fixture_dir / "signed-release-replay-v1.sqlite3").exists())

    def test_cannot_use_forged_probe_or_non_disposable_chain(self):
        self.refused(lambda:Chain.RoleBoundReleasePreflight(
            role_probe={"role":"clock-ui-bridge","role_authenticated":True},
            signed_receipt_fixture=self.receipt_fixture(),
            synthetic_only=True),
            "DISPOSABLE_SIGNED_ROLE_CHAIN_ONLY")
        self.refused(lambda:Chain.RoleBoundReleasePreflight(
            role_probe=self.probe(),
            signed_receipt_fixture=self.receipt_fixture(),
            synthetic_only=False),
            "DISPOSABLE_SIGNED_ROLE_CHAIN_ONLY")

    def test_wrong_root_and_old_signer_rejected(self):
        with self.assertRaises(Role.Refused):
            self.probe(root=Ed25519PrivateKey.generate())
        with self.assertRaises(Receipt.Refused):
            self.receipt_fixture(signer=Ed25519PrivateKey.generate())

    def test_signed_origin_entrypoint_modified_after_issue_denied(self):
        req=self.issue()
        body,signature=self.answer(req)
        self.script.write_text(CHILD+"\n# changed\n",encoding="utf8")
        self.refused(lambda:self.consume(body,signature),
                     "SIGNED_ORIGIN_LIFETIME_REFUSED")
        self.assertEqual(self.source.read_bytes(),self.original_source)

    def test_source_bytes_changed_after_issue_denied(self):
        req=self.issue()
        body,signature=self.answer(req)
        self.source.write_text(json.dumps({
            "version":2,"nextId":1,"alarms":[],
            "newMetadata":"unsaved local external change"})+"\n")
        self.source.chmod(0o600)
        changed=self.source.read_bytes()
        self.refused(lambda:self.consume(body,signature),
                     "SIGNED_RELEASE_REPLY_REFUSED")
        self.assertEqual(self.source.read_bytes(),changed)

    def test_exited_peer_cannot_complete_signed_response(self):
        req=self.issue()
        body,signature=self.answer(req)
        self.stop()
        self.refused(lambda:self.consume(body,signature),
                     "SIGNED_ORIGIN_LIFETIME_REFUSED")

    def test_replay_after_restart_and_expiry_denied(self):
        req=self.issue()
        body,signature=self.answer(req)
        success=self.consume(body,signature)
        self.assertTrue(success["signatureObserved"])
        new=self.make_chain()
        self.refused(lambda:self.consume(body,signature,new),
                     "SIGNED_RELEASE_REPLY_REFUSED")
        req2=self.issue(new)
        body2,sig2=self.answer(req2)
        self.clock[0]+=Receipt.CHALLENGE_TTL_MS+1
        self.refused(lambda:self.consume(body2,sig2,new),
                     "SIGNED_RELEASE_REPLY_REFUSED")

    def test_no_production_clocks_activated_or_private_content_logged(self):
        source=SOURCE.read_text()
        live=(ROOT/"services/time/AlarmManagerService.qml").read_text()
        broker=(ROOT/"services/time/AlarmOwnershipBroker.py").read_text()
        assert "AlarmRoleBoundReleasePreflight" not in live
        assert "AlarmRoleBoundReleasePreflight" not in broker
        for forbidden in ("notify-send","systemctl","quickshell -c",
                          "alarmFile.setText","subprocess.Popen",
                          "SoundEffect","/var/home/"):
            self.assertNotIn(forbidden,source)
        self.assertIn("canTransferOwnership",source)
        self.assertIn("synthetic_only",source)
        self.assertIn('alarmWriterBarrierPhase: "ACTIVE"',live)


if __name__ == "__main__":
    unittest.main()
