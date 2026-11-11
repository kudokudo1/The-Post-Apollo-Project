"""V2o fixture-only AF_UNIX wire protocol, signed owner and kernel peer tests.

No production socket service or ArchiveStore. Keys are ephemeral in-memory
Ed25519 test fixtures. All paths and SQLite copies live in TemporaryDirectory.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from scripts.trash.archive_v2_fixture_socket import (
    WIRE_SCHEMA, MAX_WIRE_BYTES, FixtureWireError,
    decode_fixture_request, encode_fixture_frame,
    handle_fixture_connection,
)
from scripts.trash.archive_v2_owner_trust import (
    SCHEMA as OWNER_SCHEMA, canonical_authority,
)
from scripts.trash.archive_v2_peer_evidence import (
    _executable_digest, inspect_fixture_peer,
)
from scripts.trash.archive_v2_signed_capture import (
    SCHEMA as CLAIM_SCHEMA, AUDIENCE, PURPOSE, canonical_claim,
)
from scripts.trash.archive_v2_trust_history import (
    TestOwnerTrustHistory,
)

PAYLOAD = b"synthetic owner fixture; not a Weather or research source"
NOW = 1760000500000
CAPTURED = 1760000000000


def pub(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw)


def recv_exact(sock, n):
    chunks = bytearray()
    while len(chunks) < n:
        part = sock.recv(n - len(chunks))
        if not part:
            raise AssertionError("unexpected fixture socket close")
        chunks.extend(part)
    return bytes(chunks)


class V2oSocketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root_key = Ed25519PrivateKey.generate()
        self.owner_key = Ed25519PrivateKey.generate()
        self.pin = {
            "rootKeyId": "fixture-root",
            "publicKeyBytes": pub(self.root_key),
            "origin": "EXTERNALLY_PINNED_TEST_ROOT",
        }
        self.peer_policy = {
            "ownerId": "demo-scrape",
            "expectedUid": os.getuid(),
            "expectedGid": os.getgid(),
            "expectedExeSha256": _executable_digest(os.getpid()),
            "origin": "TEST_FIXTURE_ONLY",
        }
        self.manifest = {
            "schema": OWNER_SCHEMA,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "policyOrigin": "TEST_FIXTURE_ONLY",
            "rootKeyId": "fixture-root",
            "ownerId": "demo-scrape",
            "keyId": "fixture-source",
            "publicKeyB64": base64.b64encode(pub(self.owner_key)).decode(),
            "generation": 1,
            "issuedAtMs": 1760000400000,
            "validFromMs": 1750000000000,
            "validUntilMs": 1770000000000,
            "revoked": False,
            "previousManifestSha256": "",
        }
        self.claim = {
            "schema": CLAIM_SCHEMA,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "ownerId": "demo-scrape",
            "resourceId": "synthetic-page",
            "sourceRevision": "1"*64,
            "payloadSha256": hashlib.sha256(PAYLOAD).hexdigest(),
            "sourceCapturedAtMs": CAPTURED,
            "issuedAtMs": 1760000400000,
            "expiresAtMs": 1760000600000,
            "keyId": "fixture-source",
            "nonce": "a"*32,
        }
        self.ledger = TestOwnerTrustHistory(self.root)
        self.ledger.enroll(self.signed_manifest(),self.pin,now_ms=NOW)
        self.listener = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.socket_path = str(self.root/"v2o.sock")
        self.listener.bind(self.socket_path)
        self.listener.listen(2)

    def signed_manifest(self, manifest=None):
        m = self.manifest if manifest is None else manifest
        return {"manifest":m,"signatureB64":base64.b64encode(
            self.root_key.sign(canonical_authority(m))).decode("ascii")}

    def signed_claim(self, claim=None, signer=None):
        c = self.claim if claim is None else claim
        k = self.owner_key if signer is None else signer
        return {"claim":c,"signatureB64":base64.b64encode(
            k.sign(canonical_claim(c))).decode("ascii")}

    def packet(self, *, claim=None, manifest=None, payload=PAYLOAD):
        return {
            "schema":WIRE_SCHEMA,
            "ownerId":"demo-scrape",
            "resourceId":"synthetic-page",
            "sourceRevision":"1"*64,
            "sourceCapturedAtMs":CAPTURED,
            "payloadB64":base64.b64encode(payload).decode("ascii"),
            "signedManifest":self.signed_manifest(manifest),
            "signedClaim":self.signed_claim(claim),
        }

    def server(self, accepted, *, peer_policy=None, pinned=None):
        return handle_fixture_connection(
            accepted,
            peer_policy=self.peer_policy if peer_policy is None else peer_policy,
            pinned_test_root=self.pin if pinned is None else pinned,
            ledger=self.ledger,now_ms=NOW)

    def send(self, frame, *, peer_policy=None, pinned=None, close_write=False):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.settimeout(5)
            client.connect(self.socket_path)
            client.sendall(frame)
            if close_write:
                client.shutdown(socket.SHUT_WR)
            with self.listener.accept()[0] as accepted:
                result=self.server(accepted,peer_policy=peer_policy,pinned=pinned)
            length=struct.unpack("!I",recv_exact(client,4))[0]
            reply=json.loads(recv_exact(client,length).decode("ascii"))
            self.assertEqual(reply,result)
        return reply

    def test_real_framed_socket_and_signed_test_copy_recorded(self):
        receipt=self.send(encode_fixture_frame(self.packet()))
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["state"],"TEST_IPC_COPY_RECORDED_DENY_ONLY")
        self.assertTrue(receipt["syntheticCopyRecorded"])
        for flag in ("sourceProcessVerified","humanConsentVerified",
                     "archiveCopyAuthorized","captureAllowed",
                     "restoreAllowed","burnAllowed","productionAllowed"):
            self.assertFalse(receipt[flag])
        status=self.ledger.test_copy_status("demo-scrape")
        self.assertEqual((status["testCopies"],status["consumedNonces"]),(1,1))
        restored=self.ledger.inspect_test_admission(
            "demo-scrape","fixture-source","a"*32)
        self.assertEqual(restored["snapshotId"],receipt["receiptId"])
        self.assertEqual(restored["requestBindingSha256"],
                         receipt["requestBindingSha256"])
        self.assertTrue(restored["payloadIntegrityVerified"])
        self.assertNotIn("payload",str(receipt))
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())

    def test_process_peer_identity_from_distinct_client_process(self):
        # Child owns only pre-signed public fixture request bytes. No private
        # key is sent to, stored by or generated inside the child process.
        program = (
            "import socket,sys,struct\n"
            "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
            "s.connect(sys.argv[1]);s.sendall(sys.stdin.buffer.read())\n"
            "h=s.recv(4);n=struct.unpack('!I',h)[0]\n"
            "b=b''\n"
            "while len(b)<n:\n"
            " p=s.recv(n-len(b))\n"
            " if not p:break\n"
            " b+=p\n"
            "sys.stdout.buffer.write(b);s.close()\n"
        )
        child=subprocess.Popen(
            [sys.executable,"-I","-B","-c",program,self.socket_path],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        child.stdin.write(encode_fixture_frame(self.packet()))
        child.stdin.close()
        with self.listener.accept()[0] as accepted:
            kernel=inspect_fixture_peer(accepted,self.peer_policy)
            self.assertEqual(kernel["pid"],child.pid)
            self.assertEqual(kernel["uid"],os.getuid())
            receipt=self.server(accepted)
        payload=child.stdout.read()
        err=child.stderr.read()
        self.assertEqual(child.wait(timeout=10),0,err.decode("utf-8","replace"))
        decoded=json.loads(payload.decode())
        self.assertEqual(decoded,receipt)
        self.assertTrue(receipt["ok"])
        self.assertFalse(receipt["sourceProcessVerified"])

    def test_replay_refused_on_second_connection_even_with_valid_signature(self):
        self.send(encode_fixture_frame(self.packet()))
        second=self.send(encode_fixture_frame(self.packet()))
        self.assertEqual(second,{"ok":False,"error":"SOURCE_NONCE_ALREADY_CONSUMED"})
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],1)

    def test_wire_refuses_unsigned_added_path_and_unknown_fields(self):
        packet=self.packet()
        packet["sourcePath"]="/etc/shadow"
        with self.assertRaisesRegex(FixtureWireError,
                                    "BROKER_REQUEST_SCHEMA_INVALID"):
            encode_fixture_frame(packet)
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_partial_and_oversized_frames_refuse_without_consuming_nonce(self):
        bad_frames=[
            struct.pack("!I",MAX_WIRE_BYTES+1),
            struct.pack("!I",100)+b"short",
            struct.pack("!I",0),
        ]
        for frame in bad_frames:
            reply=self.send(frame,close_write=True)
            self.assertFalse(reply["ok"])
            self.assertIn(reply["error"],
                          ("BROKER_FRAME_LIMIT","BROKER_FRAME_TRUNCATED"))
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_noncanonical_json_duplicate_keys_and_wrong_type_refuse(self):
        packet=self.packet()
        raw=json.dumps(packet,sort_keys=False).encode("ascii")
        answer=self.send(struct.pack("!I",len(raw))+raw)
        self.assertEqual(answer["error"],"BROKER_WIRE_NONCANONICAL")
        canonical=json.dumps(packet,sort_keys=True,separators=(",",":")).encode()
        duplicate=canonical[:-1]+b',"schema":"another"}'
        answer=self.send(struct.pack("!I",len(duplicate))+duplicate)
        self.assertEqual(answer["error"],"BROKER_DUPLICATE_FIELD")
        packet["sourceCapturedAtMs"]=True
        raw=json.dumps(packet,sort_keys=True,separators=(",",":")).encode()
        answer=self.send(struct.pack("!I",len(raw))+raw)
        self.assertEqual(answer["error"],"BROKER_REQUEST_FIELDS_INVALID")
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_invalid_payload_encoding_and_digest_refuse_before_storage(self):
        packet=self.packet()
        packet["payloadB64"]="!!!"
        raw=json.dumps(packet,sort_keys=True,separators=(",",":")).encode()
        response=self.send(struct.pack("!I",len(raw))+raw)
        self.assertEqual(response["error"],"BROKER_PAYLOAD_INVALID")
        packet=self.packet(payload=b"changed synthetic payload")
        response=self.send(encode_fixture_frame(packet))
        self.assertEqual(response["error"],"CAPTURE_SOURCE_MISMATCH")
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_wrong_peer_uid_and_unprovisioned_policy_deny(self):
        wrong=dict(self.peer_policy,expectedUid=os.getuid()+1)
        rejected=self.send(encode_fixture_frame(self.packet()),
                           peer_policy=wrong)
        self.assertEqual(rejected["error"],"PEER_IDENTITY_MISMATCH")
        wrong=dict(self.peer_policy,origin="PRODUCTION_AUTHORITY")
        rejected=self.send(encode_fixture_frame(self.packet()),
                           peer_policy=wrong)
        self.assertEqual(rejected["error"],"PEER_TRUST_NOT_PROVISIONED")
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_wrong_root_signed_manifest_or_signer_refused(self):
        stranger=Ed25519PrivateKey.generate()
        wrong_pin=dict(self.pin,publicKeyBytes=pub(stranger))
        rejected=self.send(encode_fixture_frame(self.packet()),pinned=wrong_pin)
        self.assertEqual(rejected["error"],"SOURCE_AUTHORITY_SIGNATURE_REFUSED")
        packet=self.packet()
        packet["signedClaim"]=self.signed_claim(
            signer=Ed25519PrivateKey.generate())
        rejected=self.send(encode_fixture_frame(packet))
        self.assertEqual(rejected["error"],"CAPTURE_SIGNATURE_REFUSED")
        self.assertEqual(self.ledger.test_copy_status("demo-scrape")["testCopies"],0)

    def test_socket_contract_has_no_daemon_key_or_real_archive_access(self):
        from scripts.trash import archive_v2_fixture_socket as impl
        source=Path(impl.__file__).read_text(encoding="utf8")
        self.assertNotIn("ArchiveStore(",source)
        self.assertNotIn("from scripts.trash.archive_store_v2 import",source)
        self.assertNotIn("Ed25519PrivateKey",source)
        self.assertNotIn("Quickshell.dataDir",source)
        self.assertNotIn(".bind(",source)
        self.assertNotIn(".listen(",source)
        self.assertFalse(hasattr(impl,"main"))
        self.assertFalse(hasattr(impl,"serve_forever"))
        self.assertFalse((self.root/"trashpp-archive-v2.sqlite3").exists())


if __name__=="__main__":
    unittest.main()
