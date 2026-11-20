#!/usr/bin/env python3
"""Disposable real Linux SO_PEERPIDFD + per-packet credential C3e/TimeW tests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

if sys.platform!="linux" or os.environ.get("GITHUB_ACTIONS")!="true" or os.environ.get("CI")!="true":
    raise SystemExit("C3E_TIMEW_KERNEL_PEER_CI_ONLY")
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tests/connections/c3e_timew"))
sys.path.insert(0,str(ROOT/"tests/connections"))
import TimeWKernelPeerEvidencePreflight as K
import test_connections_c3e_timew_window_identity_preflight as FixtureModule


class TimeWKernelPeerEvidenceTests(unittest.TestCase):
    def setUp(self):
        f=FixtureModule.TimeWWindowIdentityTests(
            "test_01_timew_original_pair_schema_and_ci_grants_false")
        f.setUp()
        self.fixture=f
        self.challenge=b"C"*32
        self.pair_args=dict(f.params)
        self.digest=hashlib.sha256(K.Window.TimeW._json(f.pair)).hexdigest()
        self.packet=K.make_packet_ci_only(
            challenge=self.challenge,pair_payload_sha256=self.digest)

    def setup_sockets(self,*,packet=None,passcred=True,socket_type=socket.SOCK_SEQPACKET):
        receiver,sender=socket.socketpair(socket.AF_UNIX,socket_type)
        self.addCleanup(receiver.close)
        self.addCleanup(sender.close)
        receiver.settimeout(2)
        if passcred:
            receiver.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
        if packet is not None:
            sender.sendall(packet)
        return receiver,sender

    def check(self,receiver,**changed):
        args=dict(receiver=receiver,independently_expected_uid=os.getuid(),
                  independently_issued_challenge=self.challenge,
                  pairing_inputs=self.pair_args)
        args.update(changed)
        return K.inspect_kernel_peer_ci_only(**args)

    def refused(self,reason,receiver,**changed):
        with self.assertRaisesRegex(K.PeerRefused,reason):
            self.check(receiver,**changed)

    def test_01_real_kernel_peer_and_pair_still_grants_nothing(self):
        a,b=self.setup_sockets(packet=self.packet)
        out=self.check(a)
        self.assertTrue(out["actualKernelPeerCredentialsAndPidfdObservedInCI"])
        self.assertTrue(out["actualPacketSenderMatchesSocketPeerInCI"])
        self.assertEqual(out["sourceOnlyPid"],os.getpid())
        self.assertEqual(out["sourceOnlyUid"],os.getuid())
        for k in (*K.DENIED,*K.Window.DENIED):
            self.assertIs(out[k],False,k)

    def test_02_wrong_independent_uid_refused(self):
        a,b=self.setup_sockets(packet=self.packet)
        self.refused("KERNEL_PEER_NOT_ENROLLED_IN_CI",
                     a,independently_expected_uid=os.getuid()+1)

    def test_03_changed_external_challenge_refused(self):
        a,b=self.setup_sockets(packet=self.packet)
        self.refused("CHANGED_OR_NONCANONICAL_PACKET",a,
                     independently_issued_challenge=b"Z"*32)

    def test_04_wrong_signed_pair_digest_refused(self):
        frame=K.make_packet_ci_only(challenge=self.challenge,
                                   pair_payload_sha256="f"*64)
        a,b=self.setup_sockets(packet=frame)
        self.refused("PACKET_BOUND_TO_DIFFERENT_SIGNED_PAIR",a)

    def test_05_replayed_pair_with_new_signed_payload_refused(self):
        a,b=self.setup_sockets(packet=self.packet)
        self.fixture.pair["browser_window_ref"]=FixtureModule.uid()
        self.fixture.re_sign()
        selected=dict(self.fixture.selected, browser_window_ref=self.fixture.pair["browser_window_ref"])
        data=dict(self.fixture.params,selected_window=selected)
        self.refused("PACKET_BOUND_TO_DIFFERENT_SIGNED_PAIR",a,pairing_inputs=data)

    def test_06_duplicate_json_field_refused(self):
        packet=self.packet.replace(b'"kind":',b'"kind":"fake","kind":',1)
        a,b=self.setup_sockets(packet=packet)
        self.refused("NONCANONICAL_PACKET",a)

    def test_07_noncanonical_json_whitespace_refused(self):
        a,b=self.setup_sockets(packet=b" "+self.packet)
        self.refused("CHANGED_OR_NONCANONICAL_PACKET",a)

    def test_08_unknown_schema_refused(self):
        obj=json.loads(self.packet);obj["schema"]="native-issuer-production"
        a,b=self.setup_sockets(packet=json.dumps(obj,sort_keys=True,separators=(",",":")).encode())
        self.refused("CHANGED_OR_NONCANONICAL_PACKET",a)

    def test_09_unknown_kind_refused(self):
        obj=json.loads(self.packet);obj["kind"]="consent-authorized"
        a,b=self.setup_sockets(packet=json.dumps(obj,sort_keys=True,separators=(",",":")).encode())
        self.refused("CHANGED_OR_NONCANONICAL_PACKET",a)

    def test_10_extra_grant_field_refused(self):
        obj=json.loads(self.packet);obj["canRestoreBrave"]=True
        a,b=self.setup_sockets(packet=json.dumps(obj,sort_keys=True,separators=(",",":")).encode())
        self.refused("UNEXPECTED_PACKET_FIELDS",a)

    def test_11_missing_packet_field_refused(self):
        obj=json.loads(self.packet);obj.pop("challengeSha256")
        a,b=self.setup_sockets(packet=json.dumps(obj,sort_keys=True,separators=(",",":")).encode())
        self.refused("UNEXPECTED_PACKET_FIELDS",a)

    def test_12_malformed_ascii_packet_refused(self):
        a,b=self.setup_sockets(packet=b"\xff\xfe")
        self.refused("NONCANONICAL_PACKET",a)

    def test_13_oversized_packet_refused(self):
        a,b=self.setup_sockets(packet=b"X"*(K.MAX_PACKET+1))
        self.refused("PACKET_TRUNCATED_OVERSIZED_OR_WRONG_ORIGIN",a)

    def test_14_empty_packet_refused(self):
        a,b=self.setup_sockets()
        b.shutdown(socket.SHUT_WR)
        # EOF is not a valid authenticated packet.
        self.refused("PACKET_TRUNCATED_OVERSIZED_OR_WRONG_ORIGIN",a)

    def test_15_missing_per_packet_credentials_refused(self):
        a,b=self.setup_sockets(packet=self.packet,passcred=False)
        self.refused("INHERITED_FD_OR_MISSING_PACKET_CREDENTIALS",a)

    def test_16_wrong_socket_type_refused(self):
        a,b=self.setup_sockets(packet=self.packet,socket_type=socket.SOCK_STREAM)
        self.refused("UNEXPECTED_SOCKET_TYPE",a)

    def test_17_forked_inherited_socket_sender_refused(self):
        a,b=self.setup_sockets(packet=None)
        pid=os.fork()
        if pid==0:
            try:
                a.close()
                b.sendall(self.packet)
                b.close()
            finally:
                os._exit(0)
        b.close()
        try:
            self.refused("INHERITED_FD_OR_MISSING_PACKET_CREDENTIALS",a)
        finally:
            waited,status=os.waitpid(pid,0)
            self.assertEqual(waited,pid)
            self.assertEqual(status,0)

    def test_18_expired_or_unavailable_pidfd_refused(self):
        a,b=self.setup_sockets(packet=self.packet)
        with patch.object(K.Lease,"_pidfd_alive",return_value=False):
            self.refused("KERNEL_CUSTODY_UNAVAILABLE",a)

    def test_19_wrong_caller_process_snapshot_refused(self):
        a,b=self.setup_sockets(packet=self.packet)
        changed=dict(self.fixture.proc,start_ticks=self.fixture.proc["start_ticks"]+1)
        self.refused("SYNTHETIC_PAIR_REFUSED",a,
                     pairing_inputs=dict(self.pair_args,process_snapshot=changed))

    def test_20_duplicate_brave_surface_refused_even_with_real_peer(self):
        a,b=self.setup_sockets(packet=self.packet)
        second=dict(self.fixture.live,con_id=111,snapshot_generation=26)
        data=dict(self.pair_args,compositor_windows=[self.fixture.live,second])
        self.refused("SYNTHETIC_PAIR_REFUSED",a,pairing_inputs=data)

    def test_21_different_native_peer_pid_is_not_brave_pid(self):
        a,b=self.setup_sockets(packet=self.packet)
        out=self.check(a)
        self.assertIsInstance(out["sourceOnlyPid"],int)
        # Even accidental numeric PID equality would not prove browser identity.
        self.assertFalse(out["nativePeerIsBraveWindowProven"])
        self.assertFalse(out["braveWaylandSurfaceBindingVerified"])

    def test_22_a_fake_root_key_pin_still_never_grants(self):
        a,b=self.setup_sockets(packet=self.packet)
        out=self.check(a)
        self.assertTrue(out["testOnlyTimeWPairSignatureMatchesCallerPin"])
        self.assertFalse(out["rootEnrolledNativePeerVerified"])
        self.assertFalse(out["canSignNativePairing"])

    def test_23_bad_input_types_refused_before_kernel_read(self):
        for value in (None,True,"1000",-1):
            with self.subTest(value=value):
                a,b=self.setup_sockets(packet=self.packet)
                self.refused("UNTRUSTED_PEER_POLICY",a,
                             independently_expected_uid=value)
        a,b=self.setup_sockets(packet=self.packet)
        self.refused("EXTERNAL_CHALLENGE_REQUIRED",a,
                     independently_issued_challenge=b"short")

    def test_24_no_native_timew_witness_entrypoint(self):
        with self.assertRaisesRegex(K.PeerRefused,"NATIVE_WAYLAND_BRAVE_PAIRING_NOT_IMPLEMENTED"):
            K.run_native_browser_window_issuer(operatorApproved=True)


if __name__=="__main__":
    unittest.main(verbosity=2)
