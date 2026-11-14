"""BG1-B2B5 real socket + Ed25519 one-use OLD writer receipt (TEST ONLY)."""
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
import threading
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/time/AlarmSignedWriterReleaseFixture.py"
QML = ROOT / "services/time/AlarmManagerService.qml"
BROKER = ROOT / "services/time/AlarmOwnershipBroker.py"

spec = importlib.util.spec_from_file_location("clock_bg1_b2b5_signed", MODULE)
Release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Release)
Peer = Release.Peer

CHILD_SOURCE = '''
import json,os,socket,sys,time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
seed=bytes.fromhex(sys.stdin.readline().strip())
key=Ed25519PrivateKey.from_private_bytes(seed)
connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
connection.connect(sys.argv[1])
connection.sendall(b"R")
req=json.loads(connection.makefile("rb").readline())
ticks=int(open("/proc/self/stat").read().rsplit(") ",1)[1].split()[19])
reply={"schema":"postapollo.clock.bg1-b2b5-synthetic-release-receipt.v1",
       "challenge":req["challenge"],"sourceDigest":req["sourceDigest"],
       "oldEpoch":req["oldEpoch"],"newEpoch":req["newEpoch"],
       "peerPid":os.getpid(),"peerStartTicks":ticks}
body=json.dumps(reply,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
signature=key.sign(b"postapollo.clock.bg1-b2b5-synthetic-release.v1\\x00"+body)
connection.sendall(json.dumps(
    {"signed":body.hex(),"signature":signature.hex()},
    separators=(",",":")).encode()+b"\\n")
time.sleep(20)
'''


class ClockB2B5SignedReleaseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="clock-b2b5-ci-")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.data = self.base / "synthetic-quickshell"
        self.data.mkdir(mode=0o700)
        self.root = self.base / "bg1-signed-release-fixture"
        self.root.mkdir(mode=0o700)
        self.source = self.data / "time-alarms-v2.json"
        self.doc = {"version": 2, "nextId": 2, "alarms": [{
            "id": 1, "name": "Private wake alarm", "note": "private details",
            "mode": "weekly", "date": "", "weekdays": [3],
            "hour": 6, "minute": 40, "pausedUntilDate": "",
            "enabled": True, "ringing": False, "completed": False,
            "lastFiredDay": "", "ringStartedAtMs": 0,
            "snoozeUntilMs": 0, "armedAtMs": 1794408000000,
            "lastProcessedDueMs": 0,
        }]}
        self.write_source()
        self.source_before = self.source.read_bytes()
        self.signer = Ed25519PrivateKey.generate()
        self.release_root = Ed25519PrivateKey.generate()
        self.script = self.base / "synthetic-old-writer.py"
        self.script.write_text(CHILD_SOURCE)
        self.script.chmod(0o600)
        self.sock = str(self.base / "private.sock")
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.bind(self.sock)
        self.listener.listen(1)
        self.listener.settimeout(5)
        self.proc = subprocess.Popen(
            [sys.executable, "-I", "-B", str(self.script), self.sock],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, text=True)
        self.addCleanup(self.stop)
        self.proc.stdin.write(self.signer.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()).hex() + "\n")
        self.proc.stdin.flush()
        self.conn, _ = self.listener.accept()
        self.addCleanup(self.conn.close)
        self.conn.settimeout(5)
        self.assertEqual(self.conn.recv(1), b"R")
        # In a real implementation this independent pinned identity comes
        # from an authorized supervisor. CI observes an ephemeral test child.
        self.supervised_pid = self.proc.pid
        self.supervised_ticks = Peer._start_ticks(self.supervised_pid)
        self.peer = Peer.capture(self.conn, sys.executable)
        self.addCleanup(Peer.close, self.peer)
        self.assertEqual(self.peer["pid"], self.supervised_pid)
        self.policy = {
            "schema": Release.POLICY_SCHEMA,
            "purpose": Release.POLICY_PURPOSE,
            "role": "clock-ui-bridge", "releaseEpoch": 3,
            "releaseSequence": 8,
            "sourceScope": Release._source_scope(self.source),
            "interpreterPath": os.path.realpath(sys.executable),
            "oldSignerSha256": Release._public_digest(self.signer.public_key()),
            "uid": os.getuid(), "gid": os.getgid()
        }
        self.now = [1794408000000]
        self.verifier = self.fixture()

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)
        if self.proc.stdin is not None and not self.proc.stdin.closed:
            self.proc.stdin.close()

    def write_source(self):
        self.source.write_text(json.dumps(self.doc) + "\n")
        self.source.chmod(0o600)

    def fixture(self, *, policy=None, authority=None, signer=None,
                minimum=(3, 8), pid=None, ticks=None,
                synthetic=True, signature=None):
        raw = Release._json_bytes(self.policy if policy is None else policy)
        issuer = self.release_root if authority is None else authority
        return Release.SignedWriterReleaseFixture(
            self.root, self.source,
            signed_policy=raw,
            policy_signature=issuer.sign(Release.AUTH_DOMAIN + raw)
                if signature is None else signature,
            independent_authority=self.release_root.public_key(),
            independent_old_signer=(
                self.signer if signer is None else signer).public_key(),
            expected_peer_pid=self.supervised_pid if pid is None else pid,
            expected_peer_ticks=self.supervised_ticks if ticks is None else ticks,
            minimum_epoch=minimum[0], minimum_sequence=minimum[1],
            synthetic_only=synthetic,
            clock=lambda: self.now[0],
        )

    def issue(self):
        return self.verifier.issue(
            self.conn, self.peer,
            expected_source_digest=hashlib.sha256(
                self.source.read_bytes()).hexdigest(),
            old_epoch=5, new_epoch=6)

    def send_to_client(self, issued):
        self.conn.sendall((json.dumps(issued) + "\n").encode())
        response = json.loads(self.conn.makefile("rb").readline())
        return bytes.fromhex(response["signed"]), bytes.fromhex(response["signature"])

    def refused(self, action, expected):
        with self.assertRaises(Release.Refused) as raised:
            action()
        self.assertEqual(str(raised.exception), expected)

    def test_actual_process_signed_receipt_and_durable_replay_fence(self):
        issued = self.issue()
        self.assertFalse(issued["releaseAcknowledged"])
        self.assertFalse(issued["writerStopped"])
        self.assertFalse(issued["canTransferOwnership"])
        body, signature = self.send_to_client(issued)
        result = self.verifier.observe_signed_reply(
            self.conn,self.peer,signed_reply=body,signature=signature)
        self.assertTrue(result["signatureObserved"])
        self.assertTrue(result["independentlyPinnedSignerMatched"])
        for right in ("writerStopped", "releaseAcknowledged",
                      "canTransferOwnership", "ownsRealAlarmFile",
                      "canRing", "canNotify"):
            self.assertIs(result[right], False)
        self.assertNotIn("Private wake", str(result))
        self.assertNotIn("private details", str(result))
        self.assertEqual(self.source.read_bytes(),self.source_before)
        # The second instance opens the same *durable* replay database.
        self.refused(lambda: self.fixture().observe_signed_reply(
            self.conn,self.peer,signed_reply=body,signature=signature),
            "RELEASE_CHALLENGE_REPLAY_OR_MISSING")

    def test_wrong_signature_cannot_consume_real_challenge(self):
        issued = self.issue()
        body, signature = self.send_to_client(issued)
        self.refused(lambda: self.verifier.observe_signed_reply(
            self.conn,self.peer,signed_reply=body,signature=b"\x00"*64),
            "UNTRUSTED_OLD_WRITER_SIGNATURE")
        good = self.verifier.observe_signed_reply(
            self.conn,self.peer,signed_reply=body,signature=signature)
        self.assertTrue(good["signatureObserved"])

    def test_source_changed_after_issue_refuses_even_signed_ack(self):
        issued = self.issue()
        body, signature = self.send_to_client(issued)
        self.doc["alarms"][0]["note"] = "New saved note"
        self.write_source()
        latest = self.source.read_bytes()
        self.refused(lambda: self.verifier.observe_signed_reply(
            self.conn,self.peer,signed_reply=body,signature=signature),
            "SOURCE_CHANGED_BEFORE_RELEASE_OBSERVATION")
        self.assertEqual(self.source.read_bytes(),latest)

    def test_released_session_cannot_be_replayed_after_process_exit(self):
        issued = self.issue()
        body, signature = self.send_to_client(issued)
        self.stop()
        self.refused(lambda: self.verifier.observe_signed_reply(
            self.conn,self.peer,signed_reply=body,signature=signature),
            "KERNEL_PEER_OR_EXECUTABLE_CHANGED")

    def test_signed_policy_wrong_root_key_role_scope_or_release_floor(self):
        self.refused(lambda: self.fixture(
            authority=Ed25519PrivateKey.generate()),
            "UNTRUSTED_CLOCK_RELEASE_ISSUER")
        self.refused(lambda: self.fixture(
            signer=Ed25519PrivateKey.generate()),
            "SIGNED_ENROLLMENT_SCOPE_MISMATCH")
        self.refused(lambda: self.fixture(minimum=(3,9)),
            "RELEASE_FLOOR_ROLLBACK")
        self.refused(lambda: self.fixture(minimum=(4,1)),
            "RELEASE_FLOOR_ROLLBACK")
        self.refused(lambda: self.fixture(pid=self.supervised_pid + 1).issue(
            self.conn,self.peer,
            expected_source_digest=hashlib.sha256(
                self.source.read_bytes()).hexdigest(), old_epoch=5,new_epoch=6),
            "UNENROLLED_PROCESS_WITNESS")
        self.refused(lambda: self.fixture(ticks=self.supervised_ticks + 1).issue(
            self.conn,self.peer,
            expected_source_digest=hashlib.sha256(
                self.source.read_bytes()).hexdigest(), old_epoch=5,new_epoch=6),
            "UNENROLLED_PROCESS_WITNESS")
        for change in [
            {"schema":"postapollo.identity.gateway-enrollment.experimental-v0"},
            {"purpose":"post-apollo.identity.native-command-gateway.v0"},
            {"role":"clock-background-worker"},
            {"role":["clock-ui-bridge"]},
            {"oldSignerSha256":"0"*64},
            {"sourceScope":"0"*64},
            {"releaseEpoch":False},
            {"releaseSequence":True},
            {"unexpectedAdmin":True},
        ]:
            with self.subTest(change=change):
                expected = ("SIGNED_FIELDS_INVALID"
                            if "unexpectedAdmin" in change else
                            "WRONG_SIGNED_CLOCK_RELEASE_POLICY"
                            if not ("sourceScope" in change or
                                    "oldSignerSha256" in change) else
                            "SIGNED_ENROLLMENT_SCOPE_MISMATCH")
                self.refused(lambda: self.fixture(
                    policy=dict(self.policy,**change)),expected)

    def test_stale_nonce_expiry_and_changed_epoch(self):
        issued=self.issue()
        body, signature=self.send_to_client(issued)
        self.now[0] += Release.CHALLENGE_TTL_MS + 1
        self.refused(lambda: self.verifier.observe_signed_reply(
            self.conn,self.peer,signed_reply=body,signature=signature),
            "STALE_OR_MISMATCHED_RELEASE_CHALLENGE")
        self.now[0] -= Release.CHALLENGE_TTL_MS + 1
        changed=json.loads(body)
        changed["newEpoch"]=999
        altered=Release._json_bytes(changed)
        # A valid signature under the OLD key but mismatched epoch fails.
        altered_signature=self.signer.sign(Release.RELEASE_DOMAIN + altered)
        self.refused(lambda: self.verifier.observe_signed_reply(
            self.conn,self.peer,signed_reply=altered,
            signature=altered_signature),
            "STALE_OR_MISMATCHED_RELEASE_CHALLENGE")

    def test_cross_process_cas_prevents_double_consumption(self):
        issued=self.issue()
        body,signature=self.send_to_client(issued)
        barrier=threading.Barrier(2)
        outcomes=[]
        lock=threading.Lock()
        def contender():
            verifier=self.fixture()
            barrier.wait()
            try:
                value=verifier.observe_signed_reply(
                    self.conn,self.peer,signed_reply=body,signature=signature)
                outcome=("ok",value["signatureObserved"])
            except Release.Refused as exc:
                outcome=("refused",str(exc))
            with lock:
                outcomes.append(outcome)
        a=threading.Thread(target=contender)
        b=threading.Thread(target=contender)
        a.start();b.start();a.join(timeout=8);b.join(timeout=8)
        self.assertFalse(a.is_alive())
        self.assertFalse(b.is_alive())
        self.assertEqual(sum(z[0]=="ok" for z in outcomes),1)
        self.assertEqual(sum(z==("refused",
            "RELEASE_CHALLENGE_REPLAY_OR_MISSING") for z in outcomes),1)

    def test_missing_nonce_unsafe_source_and_non_disposable_path(self):
        self.refused(lambda: self.fixture(synthetic=False),
            "DISPOSABLE_FIXTURE_REQUIRED")
        self.refused(lambda: self.verifier.issue(self.conn,self.peer,
            expected_source_digest="0"*64,old_epoch=5,new_epoch=6),
            "SOURCE_REVISION_MISMATCH")
        self.refused(lambda: self.verifier.issue(self.conn,self.peer,
            expected_source_digest=hashlib.sha256(
                self.source.read_bytes()).hexdigest(),old_epoch=6,new_epoch=6),
            "INVALID_RELEASE_REQUEST")
        self.source.chmod(0o644)
        self.refused(lambda: self.issue(),"SOURCE_RECORD_UNSAFE")
        self.source.chmod(0o600)
        self.source.unlink()
        other=self.base/"outside.json"
        other.write_bytes(self.source_before)
        self.source.symlink_to(other)
        self.refused(lambda: self.issue(),"SOURCE_LINK_REFUSED")

    def test_no_alarming_live_process_or_scoped_owner_mutations(self):
        code=MODULE.read_text()
        qml=QML.read_text()
        broker=BROKER.read_text()
        for forbidden in ("notify-send","SoundEffect","systemctl",
                          "Quickshell.dataDir","alarmFile.setText(",
                          "os.replace(", "subprocess.Popen("):
            self.assertNotIn(forbidden,code)
        self.assertNotIn("AlarmSignedWriterReleaseFixture",qml)
        self.assertNotIn("AlarmSignedWriterReleaseFixture",broker)
        self.assertIn("DISPOSABLE_FIXTURE_REQUIRED",code)
        self.assertIn('"canRing": False',code)
        self.assertIn('"releaseAcknowledged": False',code)


if __name__ == "__main__":
    unittest.main()
