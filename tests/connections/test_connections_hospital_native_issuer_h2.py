#!/usr/bin/env python3
"""H2 native issuer source security contracts and actual PX v12 signature frame.

All keys/peers/sessions are synthetic disposable test fixtures. Production
runtime deliberately has NO CI bypass or root-key generation. The success
test exercises the real native step with mocked OS callbacks, not a claim of
installed Polkit, protected PX database or verified user-presence.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "services/connections/hospital"
sys.path.insert(0, str(HERE))
import HospitalNativeIssuerCore as C
import HospitalNativeIssuerService as S

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("PINNED_PX_VERIFIER_SOURCE_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

PX_SOURCE = os.environ.get("C5H_PX_AUTH_SOURCE", "")
if not PX_SOURCE or not Path(PX_SOURCE).is_absolute():
    raise RuntimeError("EXACT_PX_OWNER_SOURCE_CHECKOUT_REQUIRED")
PX = load("c5h2_px_signed_lifecycle", Path(PX_SOURCE))

class NativeIssuerSecurity(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.now = int(time.time())
        self.policy = {
            "schema": C.RUNTIME_POLICY_SCHEMA,
            "operatorUid": 1000,
            "clientExecutableSha256": "a"*64,
            "pxWriterUid": 987,
            "pxWriterExecutableSha256": "b"*64,
            "hostId": "c"*64,
            "minimumPolicyGeneration": 9,
            "expiresAt": self.now + 3600,
        }
        self.request = {
            "schema": C.REQUEST_SCHEMA,
            "action": "TRASH", "roomId": "hospital-room-01",
        }
        self.nonce = C.b64(bytes(range(32)))
        self.prepared = {
            "schema": C.PREPARED_SCHEMA, "requestNonce": self.nonce,
            "action": "TRASH", "roomId": "hospital-room-01",
            "patientId": "patient-01",
            "repository": "kudokudo1/The-Post-Apollo-Project",
            "expectedRevision": 12,
            "expectedDigest": "d"*64,
            "state": "ACTIVE", "blockers": [],
            "canTrash": True, "canRestore": False,
            "retentionApproved": True, "legalHold": False,
            "policyGeneration": 9,
            "writerInstance": "protected-px-001",
            "expiresAt": self.now + 28,
        }
        self.signer_args = {
            "request": self.request, "prepared": self.prepared,
            "operator_uid":1000, "seat_id":"logind-seat0-c1",
            "host_id":"c"*64, "private_key":self.key,
            "nonce_bytes":bytes(range(32)),
            "approval_bytes":bytes(range(18)),
            "now":self.now,
        }

    def signed(self, **changes):
        return C.sign_px_grant(**{**self.signer_args, **changes})

    def denied(self, fn, *args, **kwargs):
        with self.assertRaises(C.Refused):
            fn(*args, **kwargs)

    def test_01_real_px_v12_verifier_checks_native_issuer_signature(self):
        self.assertEqual(PX.DOMAIN, C.PX_DOMAIN)
        self.assertEqual(PX.SCHEMA, C.PX_SCHEMA)
        self.assertEqual(PX.AUDIENCE, C.PX_AUDIENCE)
        wire=self.signed()
        found=PX._verify_bytes(wire, self.key.public_key(), now=self.now)
        self.assertEqual(found.body["roomId"], self.request["roomId"])
        self.assertEqual(found.body["action"], "TRASH")
        self.assertEqual(found.body["operatorId"], "uid:1000")
        self.assertEqual(found.body["seatId"], "logind-seat0-c1")
        self.assertEqual(found.body["hostId"], self.policy["hostId"])
        self.assertTrue(found.body["retentionApproved"])
        self.assertLessEqual(found.body["expiresAt"]-found.body["issuedAt"],30)

    def test_02_same_key_cannot_sign_different_action_without_changing_body(self):
        frame=json.loads(self.signed())
        frame["body"]["action"]="RESTORE"
        with self.assertRaises(PX.GrantRefused):
            PX._verify_bytes(C.canonical(frame),self.key.public_key(),now=self.now)

    def test_03_wrong_px_root_refuses_real_signature(self):
        with self.assertRaises(PX.GrantRefused):
            PX._verify_bytes(self.signed(),
                Ed25519PrivateKey.generate().public_key(),now=self.now)

    def test_04_missing_private_key_fails(self):
        self.denied(self.signed,private_key=None)

    def test_05_missing_operator_uid_fails(self):
        self.denied(self.signed,operator_uid=0)

    def test_06_invalid_active_seat_fails(self):
        self.denied(self.signed,seat_id="seat0")

    def test_07_wrong_host_identity_format_fails(self):
        self.denied(self.signed,host_id="host-claim")

    def test_08_expired_source_review_never_signed(self):
        self.prepared["expiresAt"]=self.now
        self.denied(self.signed)

    def test_09_source_preview_challenge_fields_required(self):
        self.denied(C.validate_prepared,C.canonical({
            k:v for k,v in self.prepared.items() if k!="policyGeneration"
        }),self.request,self.nonce,self.policy,self.now)

    def test_10_px_retention_denial_blocks_signature(self):
        self.prepared["retentionApproved"]=False
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_11_active_legal_hold_blocks_authorization(self):
        self.prepared["legalHold"]=True
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_12_px_revoked_policy_floor_refused(self):
        self.prepared["policyGeneration"]=8
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_13_wrong_room_source_refused(self):
        self.prepared["roomId"]="hospital-room-99"
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_14_wrong_request_nonce_source_refused(self):
        self.prepared["requestNonce"]=C.b64(bytes(range(31,-1,-1)))
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_15_source_is_not_eligible_due_to_active_session(self):
        self.prepared["blockers"]=["SESSION_NOT_PROVEN_TERMINAL"]
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_16_ineligible_restore_is_not_trash(self):
        self.request["action"]="RESTORE"
        self.prepared["action"]="RESTORE"
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_17_actual_restore_allowed_only_trashed_and_preserved(self):
        self.request["action"]="RESTORE"
        self.prepared.update(action="RESTORE",state="TRASHED",
                             canTrash=False,canRestore=True)
        self.assertEqual(C.validate_prepared(C.canonical(self.prepared),
            self.request,self.nonce,self.policy,self.now)["action"],"RESTORE")
        out=self.signed()
        self.assertEqual(PX._verify_bytes(
            out,self.key.public_key(),now=self.now).body["action"],"RESTORE")

    def test_18_duplicate_request_json_field_rejected(self):
        self.denied(C.validate_request,b'{"action":"TRASH","action":"RESTORE","roomId":"x","schema":"'+
                    C.REQUEST_SCHEMA.encode()+b'"}')

    def test_19_noncanonical_request_refused(self):
        self.denied(C.validate_request,b" "+C.canonical(self.request))

    def test_20_unsigned_or_tasks_actions_refused(self):
        self.denied(C.validate_request,C.canonical({
            **self.request,"action":"CAPTURE",
        }))

    def test_21_boolean_revision_in_protected_source_refused(self):
        self.prepared["expectedRevision"]=True
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_22_unsigned_success_receipt_is_not_enough_if_grant_digest_wrong(self):
        grant=self.signed()
        receipt=self.receipt(grant)
        receipt["grantDigest"]="f"*64
        self.denied(C.validate_commit_receipt,C.canonical(receipt),
                    request=self.request,prepared=self.prepared,
                    nonce=self.nonce,signed_grant=grant)

    def receipt(self,grant):
        body=json.loads(grant)["body"]
        return {
            "schema":C.RECEIPT_SCHEMA,"requestNonce":self.nonce,
            "roomId":self.request["roomId"],"action":self.request["action"],
            "revisionAfter":self.prepared["expectedRevision"]+1,
            "grantDigest":hashlib.sha256(C.PX_DOMAIN+C.canonical(body)).hexdigest(),
            "state":"TRASHED" if self.request["action"]=="TRASH" else "ACTIVE",
            "originalPreserved":True,"burnAllowed":False,
        }

    def test_23_valid_protected_writer_receipt_is_minimal(self):
        out=C.validate_commit_receipt(C.canonical(self.receipt(self.signed())),
            request=self.request,prepared=self.prepared,nonce=self.nonce,
            signed_grant=self.signed())
        self.assertEqual(out["status"],"COMMITTED")
        self.assertFalse(out["burnAllowed"])
        self.assertNotIn("signedGrant",out)
        self.assertNotIn("signature",out)

    def test_24_false_burn_or_data_loss_receipt_refused(self):
        grant=self.signed()
        for k,v in (("burnAllowed",True),("originalPreserved",False),
                    ("revisionAfter",999)):
            receipt=self.receipt(grant)
            receipt[k]=v
            with self.subTest(key=k):
                self.denied(C.validate_commit_receipt,C.canonical(receipt),
                    request=self.request,prepared=self.prepared,
                    nonce=self.nonce,signed_grant=grant)

    def test_25_native_service_direct_cli_always_holds(self):
        with patch.dict(os.environ,{"LISTEN_FDS":"","LISTEN_PID":"",
                                  "INVOCATION_ID":""}):
            self.assertEqual(S.main(),2)

    def test_26_owner_root_and_public_path_fixed(self):
        self.assertEqual(C.KEY_PATH,"/etc/post-apollo/hospital/issuer.key")
        self.assertEqual(C.PUBLIC_PATH,
                         "/etc/post-apollo/hospital/room-lifecycle-issuer.pub")
        self.assertEqual(C.WRITER_SOCKET,
                         "/run/post-apollo/hospital/px-writer.sock")

    def test_27_unknown_frame_or_wrong_source_version_denied(self):
        self.denied(C.validate_request,C.canonical({
            **self.request,"schema":"another-schema"}))
        self.prepared["schema"]="another-schema"
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_28_duplicate_px_source_fields_refused(self):
        raw=C.canonical(self.prepared).replace(
            b'"action":',b'"action":"RESTORE","action":',1)
        self.denied(C.validate_prepared,raw,
                    self.request,self.nonce,self.policy,self.now)

    def test_29_source_review_expired_fails(self):
        self.prepared["expiresAt"]=self.now
        self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)

    def test_30_source_wrong_repo_or_patient_blocks_px_schema(self):
        for field,value in (("patientId","bad value"),("repository","has whitespace")):
            old=self.prepared[field]
            self.prepared[field]=value
            with self.subTest(field=field):
                self.denied(C.validate_prepared,C.canonical(self.prepared),
                    self.request,self.nonce,self.policy,self.now)
            self.prepared[field]=old

    def test_31_native_step_sequenced_actual_polkit_px_writer_and_signing(self):
        """Exercise the real orchestration with OS-boundaries mocked for CI."""
        peer=(4321,1000,1000,54321)
        calls=[]
        class FakeClient:
            pass
        client=FakeClient()
        prepared=C.canonical(self.prepared)
        def writer(policy,data):
            calls.append(("writer",data["kind"]))
            if data["kind"]=="prepare":
                self.assertEqual(data["requestNonce"],self.nonce)
                return prepared
            self.assertEqual(data["kind"],"commit")
            self.assertIn('"signature":',data["signedGrant"])
            return C.canonical(self.receipt(data["signedGrant"].encode("ascii")))
        def polkit(request,prepared,peer,seat):
            calls.append(("polkit",request["action"]))
        with patch.object(S,"_peer",return_value=peer), \
             patch.object(S,"_same_peer",return_value=peer), \
             patch.object(S,"_packet_recv",return_value=C.canonical(self.request)), \
             patch.object(S,"_active_seat",return_value="logind-seat0-c1"), \
             patch.object(S,"_writer_exchange",side_effect=writer), \
             patch.object(S,"_polkit_approve",side_effect=polkit), \
             patch.object(C,"host_fingerprint",return_value="c"*64), \
             patch.object(C,"load_installed_key",return_value=self.key), \
             patch.object(S.os,"urandom",side_effect=lambda n:bytes(range(n))):
            # _native_step generates its own nonce before calling PX.
            out=S._native_step(client,self.policy)
        self.assertEqual(out["status"],"COMMITTED")
        self.assertEqual(calls,[("writer","prepare"),("polkit","TRASH"),
                                ("writer","commit")])

    def test_32_native_wrong_operator_refused_before_polkit(self):
        with patch.object(S,"_peer",return_value=(1234,1001,1001,10)),\
             patch.object(S,"_polkit_approve") as polkit:
            self.denied(S._native_step,object(),self.policy)
            polkit.assert_not_called()

    def test_33_native_no_polkit_means_no_signature_or_commit(self):
        peer=(4321,1000,1000,54321)
        with patch.object(S,"_peer",return_value=peer),\
             patch.object(S,"_same_peer",return_value=peer),\
             patch.object(S,"_packet_recv",return_value=C.canonical(self.request)),\
             patch.object(S,"_active_seat",return_value="logind-seat0-c1"),\
             patch.object(S,"_writer_exchange",return_value=C.canonical(self.prepared)),\
             patch.object(S,"_polkit_approve",side_effect=C.Refused("DENIED")) as auth,\
             patch.object(C,"host_fingerprint",return_value="c"*64),\
             patch.object(C,"load_installed_key") as keys,\
             patch.object(S.os,"urandom",side_effect=lambda n:bytes(range(n))):
            self.denied(S._native_step,object(),self.policy)
            auth.assert_called_once()
            keys.assert_not_called()

    def test_34_native_wrong_px_prepare_no_polkit_or_key(self):
        peer=(4321,1000,1000,54321)
        broken=dict(self.prepared,legalHold=True)
        with patch.object(S,"_peer",return_value=peer),\
             patch.object(S,"_same_peer",return_value=peer),\
             patch.object(S,"_packet_recv",return_value=C.canonical(self.request)),\
             patch.object(S,"_active_seat",return_value="logind-seat0-c1"),\
             patch.object(S,"_writer_exchange",return_value=C.canonical(broken)),\
             patch.object(S,"_polkit_approve") as auth,\
             patch.object(C,"host_fingerprint",return_value="c"*64),\
             patch.object(C,"load_installed_key") as keys,\
             patch.object(S.os,"urandom",side_effect=lambda n:bytes(range(n))):
            self.denied(S._native_step,object(),self.policy)
            auth.assert_not_called()
            keys.assert_not_called()

    def test_35_native_changed_seat_after_polkit_denies_before_sign(self):
        peer=(4321,1000,1000,54321)
        with patch.object(S,"_peer",return_value=peer),\
             patch.object(S,"_same_peer",return_value=peer),\
             patch.object(S,"_packet_recv",return_value=C.canonical(self.request)),\
             patch.object(S,"_active_seat",side_effect=[
                "logind-seat0-c1","logind-seat0-c1","logind-seat1-c2"]),\
             patch.object(S,"_writer_exchange",return_value=C.canonical(self.prepared)),\
             patch.object(S,"_polkit_approve") as auth,\
             patch.object(C,"host_fingerprint",return_value="c"*64),\
             patch.object(C,"load_installed_key") as keys,\
             patch.object(S.os,"urandom",side_effect=lambda n:bytes(range(n))):
            self.denied(S._native_step,object(),self.policy)
            auth.assert_called_once()
            keys.assert_not_called()

    def test_36_no_synthetic_runtime_override_hidden_in_service(self):
        source=(HERE/"HospitalNativeIssuerService.py").read_text()
        self.assertNotIn("POST_APOLLO_CI",source)
        self.assertNotIn("GITHUB_ACTIONS",source)
        self.assertNotIn("Ed25519PrivateKey.generate",source)
        self.assertIn("socket.SO_PEERCRED",source)
        self.assertIn("MessageBus(bus_type=BusType.SYSTEM)",source)
        self.assertIn("--allow-user-interaction",source)
        self.assertIn("POLKIT_ACTIONS[action]",source)
        self.assertIn("C.load_installed_key()",source)
        self.assertNotIn("exec(",source)

    def test_37_source_only_policy_disallows_implicit_active_or_cached_auth(self):
        pol=(HERE/"native/org.postapollo.hospital.policy").read_text()
        self.assertIn("<allow_any>no</allow_any>",pol)
        self.assertIn("<allow_inactive>no</allow_inactive>",pol)
        self.assertEqual(pol.count("<allow_active>auth_self</allow_active>"),2)
        self.assertNotIn("auth_self_keep",pol)
        self.assertNotIn("auth_admin_keep",pol)

    def test_39_real_kernel_packet_credentials_match_receiving_process(self):
        import socket
        import contextlib
        with contextlib.ExitStack() as stack:
            tx,rx=socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            stack.enter_context(tx)
            stack.enter_context(rx)
            rx.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            tx.send(b"native-packet")
            actual=(os.getpid(),os.getuid(),os.getgid())
            self.assertEqual(S._packet_recv(rx,expected_sender=actual),b"native-packet")

    def test_40_forwarded_or_different_sender_pid_cannot_pass_packet_gate(self):
        import socket
        import contextlib
        with contextlib.ExitStack() as stack:
            tx,rx=socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            stack.enter_context(tx)
            stack.enter_context(rx)
            rx.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            tx.send(b"other-process-packet")
            forged=(os.getpid()+1,os.getuid(),os.getgid())
            self.denied(S._packet_recv,rx,expected_sender=forged)

    def test_41_packet_gate_rejects_no_trusted_expected_peer(self):
        import socket
        import contextlib
        with contextlib.ExitStack() as stack:
            tx,rx=socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            stack.enter_context(tx)
            stack.enter_context(rx)
            tx.send(b"native-packet")
            self.denied(S._packet_recv,rx,expected_sender=None)

    def test_38_native_units_have_no_install_or_auto_activation(self):
        sock=(HERE/"native/post-apollo-hospital-issuer.socket").read_text()
        unit=(HERE/"native/post-apollo-hospital-issuer.service").read_text()
        self.assertIn("ListenSequentialPacket=",sock)
        self.assertIn("SocketMode=0660",sock)
        self.assertIn("User=root",unit)
        self.assertIn("ProtectSystem=strict",unit)
        self.assertNotIn("\n[Install]\n",sock)
        self.assertNotIn("\n[Install]\n",unit)

if __name__=="__main__":
    unittest.main(verbosity=2)
