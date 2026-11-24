#!/usr/bin/env python3
"""C5 local signed-permission / real socket ordering experiment. CI ONLY.

No private data, external socket, native issuer, production authority, or
Forest runtime import path. Test keys and state are deliberately local and
rollbackable. The only possible output is one immutable public marker.
"""
from __future__ import annotations

import concurrent.futures
import json
import secrets
import socket
import threading
import time
import unittest
from pathlib import Path
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from services.connections.forest import ForestC5AuthorityBoundary as C

AUDIENCE = "postapollo.forest.c5-list-title-egress-ci-only"
LIST = "LIST_SESSIONS"
TITLE = "DISCLOSE_SESSION_TITLES"
PUBLIC_MARKER = b"PUBLIC_TEST_MARKER_NO_PRIVATE_METADATA"
FENCED = "LOCAL_TEST_FENCED_NO_NEW_SUBMITS"
UNKNOWN = "UNKNOWN_HOLD"


class Refused(Exception):
    """Fixed local test denial."""


class _LocalTestGate:
    """One-use signed test pair, serialized with a real kernel submission.

    The harness supplies a disposable public key, not an enrolled root.
    The lock protects only this object's own sends, not a remote issuer,
    other processes, recipient display, filesystem or independent history.
    """
    def __init__(self, test_public, *, lease_ns=10_000_000_000,
                 byte_budget=len(PUBLIC_MARKER)):
        self._public = test_public
        self._lock = threading.Lock()
        self._sender, self._receiver = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self._sender.setblocking(False)
        self._receiver.settimeout(1)
        self._request = secrets.token_hex(16)
        self._recipient = secrets.token_hex(16)
        self._deadline = time.monotonic_ns() + lease_ns
        self._budget = byte_budget
        self._epoch = 1
        self._state = "READY"
        self._submitted = 0

    def close(self):
        with self._lock:
            self._sender.close()
            self._receiver.close()
            if self._state == "READY":
                self._state = "CLOSED"

    def test_message(self, operation):
        # Fixed synthetic scope; no data, DB path, or actual principal input.
        # These exact bytes are an experiment, NOT a proposed native wire.
        return json.dumps({
            "audience": AUDIENCE,
            "operation": operation,
            "principal": "SYNTHETIC_OWNER",
            "tree": "SYNTHETIC_TREE",
            "request": self._request,
            "recipient": self._recipient,
            "epoch": 1,
            "deadline": self._deadline,
            "byteBudget": self._budget,
        }, sort_keys=True, separators=(",", ":")).encode("ascii")

    def _check(self, operation, signature):
        if type(signature) is not bytes or len(signature) != 64:
            raise Refused("MISSING_OR_INVALID_TEST_SIGNATURE")
        try:
            self._public.verify(signature, self.test_message(operation))
        except (InvalidSignature, ValueError):
            raise Refused("WRONG_TEST_SCOPE_OR_SIGNATURE") from None

    def submit_public_marker_once(self, list_signature, title_signature):
        with self._lock:
            if self._state != "READY" or self._epoch != 1:
                raise Refused("TEST_FENCE_CLOSED_OR_ALREADY_SPENT")
            # LIST and TITLE are independent operation-specific signatures.
            self._check(LIST, list_signature)
            self._check(TITLE, title_signature)
            if time.monotonic_ns() >= self._deadline:
                raise Refused("TEST_LEASE_EXPIRED")
            if self._budget < len(PUBLIC_MARKER):
                raise Refused("TEST_BYTE_BUDGET_EXCEEDED")
            # Consume both before attempting the only possible syscall.
            # A failed/ambiguous send cannot be retried or presumed unsent.
            self._state = "SPENT_UNKNOWN"
            try:
                sent = self._sender.send(PUBLIC_MARKER)
            except OSError:
                return UNKNOWN
            if sent != len(PUBLIC_MARKER):
                return UNKNOWN
            self._submitted = sent
            self._state = "SPENT_SUBMITTED"
            return "PUBLIC_MARKER_SUBMITTED_TEST_ONLY"

    def revoke_test_only(self):
        with self._lock:
            self._epoch = 2
            if self._state == "SPENT_UNKNOWN":
                # Close further local submission but do not settle uncertainty.
                self._sender.close()
                return UNKNOWN
            self._state = "REVOKED"
            self._sender.close()
            return FENCED

    def read_marker(self):
        return self._receiver.recv(128)

    def disconnect_test_recipient(self):
        self._receiver.close()

    def status(self):
        with self._lock:
            return {
                "testState": self._state,
                "testEpoch": self._epoch,
                "publicBytesSubmittedTestOnly": self._submitted,
                "privateBytesSubmitted": 0,
                "revocationFencedAck": False,
                "safeActions": [],
                **dict(C.NO_AUTHORITY),
            }


class ForestC5SignedPublicEgressRaceTests(unittest.TestCase):
    def setUp(self):
        # Ephemeral TEST key stays in this unittest process. No key file.
        self.issuer = Ed25519PrivateKey.generate()
        self.gate = self.make_gate()

    def make_gate(self, **kwargs):
        gate = _LocalTestGate(self.issuer.public_key(), **kwargs)
        self.addCleanup(gate.close)
        return gate

    def pair(self, gate=None):
        g = self.gate if gate is None else gate
        return tuple(self.issuer.sign(g.test_message(op)) for op in (LIST, TITLE))

    def assert_no_authority(self, gate=None):
        g = self.gate if gate is None else gate
        status = g.status()
        self.assertEqual(status["privateBytesSubmitted"], 0)
        self.assertFalse(status["revocationFencedAck"])
        self.assertEqual(status["safeActions"], [])
        for key in C.NO_AUTHORITY:
            self.assertIs(status[key], False, key)

    def assert_no_packet(self, gate=None):
        g = self.gate if gate is None else gate
        # Receiver remains local and test-owned. EOF is not an ACK.
        g._receiver.setblocking(False)
        try:
            try:
                self.assertEqual(g.read_marker(), b"")
            except BlockingIOError:
                pass
        finally:
            g._receiver.settimeout(1)

    def test_01_two_signed_test_permissions_submit_only_public_marker(self):
        self.assertEqual(self.gate.submit_public_marker_once(*self.pair()),
                         "PUBLIC_MARKER_SUBMITTED_TEST_ONLY")
        self.assertEqual(self.gate.read_marker(), PUBLIC_MARKER)
        self.assertEqual(self.gate.status()["publicBytesSubmittedTestOnly"],
                         len(PUBLIC_MARKER))
        self.assert_no_authority()

    def test_02_list_alone_or_same_signature_cannot_disclose_titles(self):
        listing, _ = self.pair()
        for title in (None, listing):
            with self.subTest(title_present=title is not None):
                with self.assertRaises(Refused):
                    self.gate.submit_public_marker_once(listing, title)
        self.assert_no_packet()
        self.assert_no_authority()

    def test_03_title_alone_or_swapped_pair_refused(self):
        listing, title = self.pair()
        for pair in ((None, title), (title, listing)):
            with self.assertRaises(Refused):
                self.gate.submit_public_marker_once(*pair)
        self.assert_no_packet()

    def test_04_commit_or_other_operation_signature_refused(self):
        listing, _ = self.pair()
        other = self.issuer.sign(self.gate.test_message("COMMIT_GENERATE"))
        with self.assertRaises(Refused):
            self.gate.submit_public_marker_once(listing, other)
        self.assert_no_packet()

    def test_05_wrong_signer_refused(self):
        impostor = Ed25519PrivateKey.generate()
        pair = tuple(impostor.sign(self.gate.test_message(op))
                     for op in (LIST, TITLE))
        with self.assertRaises(Refused):
            self.gate.submit_public_marker_once(*pair)
        self.assert_no_packet()

    def test_06_request_and_recipient_replacement_refused(self):
        other = self.make_gate()
        with self.assertRaises(Refused):
            other.submit_public_marker_once(*self.pair())
        self.assert_no_packet(other)

    def test_07_one_use_pair_cannot_submit_twice(self):
        pair = self.pair()
        self.gate.submit_public_marker_once(*pair)
        self.assertEqual(self.gate.read_marker(), PUBLIC_MARKER)
        with self.assertRaises(Refused):
            self.gate.submit_public_marker_once(*pair)
        self.assert_no_packet()

    def test_08_revocation_first_refuses_even_valid_test_pair(self):
        pair = self.pair()
        self.assertEqual(self.gate.revoke_test_only(), FENCED)
        with self.assertRaises(Refused):
            self.gate.submit_public_marker_once(*pair)
        self.assert_no_packet()
        self.assert_no_authority()

    def test_09_send_first_then_revoke_does_not_recall_queued_bytes(self):
        pair = self.pair()
        self.gate.submit_public_marker_once(*pair)
        self.assertEqual(self.gate.revoke_test_only(), FENCED)
        # Real kernel-queued public bytes survive the local revoke.
        self.assertEqual(self.gate.read_marker(), PUBLIC_MARKER)
        with self.assertRaises(Refused):
            self.gate.submit_public_marker_once(*pair)
        self.assertEqual(self.gate.read_marker(), b"")
        self.assert_no_authority()

    def test_10_expired_lease_refuses(self):
        gate = self.make_gate(lease_ns=-1)
        with self.assertRaisesRegex(Refused, "TEST_LEASE_EXPIRED"):
            gate.submit_public_marker_once(*self.pair(gate))
        self.assert_no_packet(gate)

    def test_11_byte_budget_refuses_before_syscall(self):
        gate = self.make_gate(byte_budget=len(PUBLIC_MARKER)-1)
        with self.assertRaisesRegex(Refused, "TEST_BYTE_BUDGET_EXCEEDED"):
            gate.submit_public_marker_once(*self.pair(gate))
        self.assert_no_packet(gate)

    def test_12_disconnected_recipient_keeps_spent_unknown_no_retry(self):
        pair = self.pair()
        self.gate.disconnect_test_recipient()
        self.assertEqual(self.gate.submit_public_marker_once(*pair), UNKNOWN)
        self.assertEqual(self.gate.revoke_test_only(), UNKNOWN)
        with self.assertRaises(Refused):
            self.gate.submit_public_marker_once(*pair)
        self.assertEqual(self.gate.status()["testState"], "SPENT_UNKNOWN")
        self.assert_no_authority()

    def test_13_real_concurrent_send_revoke_race(self):
        # Both threads start together. Either serialized order is legal;
        # a local fence followed by another submission is not.
        for _ in range(16):
            gate = self.make_gate()
            pair = self.pair(gate)
            barrier = threading.Barrier(2, timeout=2)

            def send():
                barrier.wait()
                try:
                    return gate.submit_public_marker_once(*pair)
                except Refused:
                    return "REFUSED"

            def revoke():
                barrier.wait()
                return gate.revoke_test_only()

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                send_future = pool.submit(send)
                revoke_future = pool.submit(revoke)
                sent = send_future.result(timeout=3)
                self.assertEqual(revoke_future.result(timeout=3), FENCED)
            packet = gate.read_marker()
            self.assertIn(sent, ("REFUSED", "PUBLIC_MARKER_SUBMITTED_TEST_ONLY"))
            self.assertEqual(packet, PUBLIC_MARKER if sent != "REFUSED" else b"")
            if packet:
                self.assertEqual(gate.read_marker(), b"")
            with self.assertRaises(Refused):
                gate.submit_public_marker_once(*pair)
            self.assert_no_authority(gate)

    def test_14_concurrent_replay_can_submit_at_most_once(self):
        pair = self.pair()
        barrier = threading.Barrier(2, timeout=2)

        def send():
            barrier.wait()
            try:
                return self.gate.submit_public_marker_once(*pair)
            except Refused:
                return "REFUSED"

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(send) for _ in range(2)]
            results = [f.result(timeout=3) for f in futures]
        self.assertCountEqual(results, ["REFUSED", "PUBLIC_MARKER_SUBMITTED_TEST_ONLY"])
        self.assertEqual(self.gate.read_marker(), PUBLIC_MARKER)
        self.assert_no_packet()

    def test_15_real_c5_authority_remains_deny_only_after_lab_success(self):
        self.gate.submit_public_marker_once(*self.pair())
        self.assertEqual(self.gate.read_marker(), PUBLIC_MARKER)
        for mode in (C.MODE_REFERENCE, C.MODE_PROTECTED):
            authority = C.ForestC5AuthorityBoundary(required_mode=mode)
            for operation in ("authorize_list_sessions",
                              "authorize_disclose_session_titles"):
                with self.assertRaises(C.ForestC5Hold):
                    getattr(authority, operation)(self.gate.status())
            self.assertEqual(authority.status()["safeActions"], [])
        self.assert_no_authority()


if __name__ == "__main__":
    unittest.main()
