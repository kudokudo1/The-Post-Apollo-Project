#!/usr/bin/env python3
"""Real Linux kernel origin diagnostics over disposable Sway-like IPC streams."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
import threading
import unittest
from unittest.mock import patch

if sys.platform != "linux" or os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
    raise SystemExit("C3E_TIMEW_SWAY_KERNEL_PEER_TEST_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/connections/c3e_timew"))
import TimeWSwayIpcKernelPeerPreflight as S
import TimeWSwayIpcTreeReadPreflight as T


def dummy_tree(*, two=False):
    leaves = [
        {"type": "con", "id": 10, "app_id": "brave-browser", "pid": 777,
         "nodes": [], "floating_nodes": []}
    ]
    if two:
        leaves.append({"type": "con", "id": 11,
                       "app_id": "brave-browser", "pid": 777})
    return {"type": "root", "id": 1, "nodes": [
        {"type": "output", "id": 2, "name": "HDMI-A-1", "nodes": [
            {"type": "workspace", "id": 3, "name": "1", "nodes": leaves}
        ]}
    ]}


class PeerTests(unittest.TestCase):
    def make_server(self, *, two=False, bad_type=False):
        client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(client.close)
        client.settimeout(0.5)
        errors = []
        def respond():
            try:
                server.settimeout(0.8)
                buf = b""
                while len(buf) < T.HEADER.size:
                    part = server.recv(T.HEADER.size-len(buf))
                    if not part:
                        break
                    buf += part
                if buf:
                    if buf != T.HEADER.pack(T.MAGIC, 0, T.GET_TREE):
                        errors.append("non-GET_TREE command")
                    reply = json.dumps(dummy_tree(two=two), separators=(",", ":")).encode()
                    server.sendall(T.HEADER.pack(T.MAGIC, len(reply),
                                                 2 if bad_type else T.GET_TREE)+reply)
            except (OSError, TimeoutError):
                pass
            finally:
                server.close()
        worker = threading.Thread(target=respond, daemon=True)
        worker.start()
        self.addCleanup(lambda: worker.join(1))
        return client, errors

    def original(self, client):
        creds = S.CREDENTIALS.unpack(client.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, S.CREDENTIALS.size))
        self.assertEqual(creds[0], os.getpid())
        identity = S.Lease._identity(*creds)
        return dict(connection=client, expected_uid=creds[1],
                    expected_start_ticks=identity.start_ticks)

    def denied(self, label, **changes):
        client, err = self.make_server()
        args=self.original(client)
        args.update(changes)
        with self.assertRaisesRegex(S.PeerRefused, label):
            S.inspect_original_sway_socket_peer_ci_only(**args)
        self.assertFalse(err)

    def test_01_real_kernel_original_peer_cannot_grant_restore(self):
        client, errors = self.make_server()
        out = S.inspect_original_sway_socket_peer_ci_only(**self.original(client))
        self.assertEqual(out["sourceOnlyOriginalPeerPid"], os.getpid())
        self.assertTrue(out["actualOriginalUnixStreamPeerPidfdSeenInCi"])
        self.assertTrue(out["testOnlySwayTreeWireObserved"])
        for k in (*S.DENIED, *T.DENIED):
            self.assertIs(out[k], False, k)
        self.assertFalse(errors)

    def test_02_wrong_uid_refused(self):
        self.denied("KERNEL_PEER_DIFFERS_FROM_TEST_EXPECTATION",
                    expected_uid=os.getuid()+1)

    def test_03_wrong_original_process_birth_refused(self):
        client, errors = self.make_server()
        args = self.original(client)
        args["expected_start_ticks"] += 1
        with self.assertRaisesRegex(S.PeerRefused,
                                    "ORIGINAL_PROCESS_IDENTITY_CHANGED"):
            S.inspect_original_sway_socket_peer_ci_only(**args)
        self.assertFalse(errors)

    def test_04_same_pid_two_brave_windows_not_authentic(self):
        client, errors = self.make_server(two=True)
        out = S.inspect_original_sway_socket_peer_ci_only(**self.original(client))
        self.assertTrue(out["testOnlyAmbiguousSamePidBrave"])
        self.assertFalse(out["braveWindowToWaylandSurfaceBound"])
        self.assertFalse(errors)

    def test_05_bad_sway_response_type_refused(self):
        client, errors = self.make_server(bad_type=True)
        with self.assertRaisesRegex(S.PeerRefused,
                                    "KERNEL_OR_READONLY_TREE_UNAVAILABLE"):
            S.inspect_original_sway_socket_peer_ci_only(**self.original(client))
        self.assertFalse(errors)

    def test_06_pidfd_lifetime_failure_refused(self):
        client, errors = self.make_server()
        with patch.object(S.Lease, "_pidfd_alive", return_value=False):
            with self.assertRaisesRegex(S.PeerRefused,
                                        "KERNEL_OR_READONLY_TREE_UNAVAILABLE"):
                S.inspect_original_sway_socket_peer_ci_only(**self.original(client))
        self.assertFalse(errors)

    def test_07_bad_types_fail_before_kernel_read(self):
        client, errors = self.make_server()
        args = self.original(client)
        for value in (None, True, "1000", -1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(S.PeerRefused,
                                            "UNTRUSTED_TEST_POLICY"):
                    S.inspect_original_sway_socket_peer_ci_only(
                        **dict(args, expected_uid=value))
        self.assertFalse(errors)

    def test_08_unbounded_socket_timeout_refused(self):
        client, errors = self.make_server()
        args = self.original(client)
        client.settimeout(None)
        with self.assertRaisesRegex(S.PeerRefused,
                                    "KERNEL_OR_READONLY_TREE_UNAVAILABLE"):
            S.inspect_original_sway_socket_peer_ci_only(**args)
        self.assertFalse(errors)

    def test_09_socket_type_refused(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        with self.assertRaisesRegex(S.PeerRefused, "UNEXPECTED_SOCKET_TYPE"):
            S.inspect_original_sway_socket_peer_ci_only(
                connection=a, expected_uid=os.getuid(),
                expected_start_ticks=1)

    def test_10_no_native_issuer_even_if_caller_claims_approval(self):
        with self.assertRaisesRegex(S.PeerRefused,
                                    "REAL_COMPOSITOR_OR_BRAVE_WINDOW_TRUST_NOT_IMPLEMENTED"):
            S.run_native_sway_ipc_attested_window_issuer(
                operatorApproved=True, browserWindowAuthenticated=True,
                canRestore=True)

    def test_11_no_protected_sway_socket_enrollment(self):
        client, errors = self.make_server()
        out = S.inspect_original_sway_socket_peer_ci_only(**self.original(client))
        self.assertFalse(out["protectedSwaySocketPathAuthenticated"])
        self.assertFalse(out["installedSwayPxSignedReleaseVerified"])
        self.assertFalse(out["actualSwayIpcReplySenderProven"])
        self.assertFalse(errors)

    def test_12_no_signed_browser_window_reference(self):
        client, errors = self.make_server()
        out = S.inspect_original_sway_socket_peer_ci_only(**self.original(client))
        self.assertFalse(out["braveWindowReferenceAuthenticated"])
        self.assertFalse(out["timewPairingIssuerAvailable"])
        self.assertFalse(errors)


    def test_13_inherited_stream_reply_does_not_prove_sender(self):
        """Kernel socket origin stays the parent even when child writes data."""
        client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(client.close)
        client.settimeout(0.8)
        args = self.original(client)
        original_pid = os.getpid()
        child_pid = os.fork()
        if child_pid == 0:
            try:
                client.close()
                server.settimeout(0.8)
                request = b""
                while len(request) < T.HEADER.size:
                    part = server.recv(T.HEADER.size - len(request))
                    if not part:
                        break
                    request += part
                if request != T.HEADER.pack(T.MAGIC, 0, T.GET_TREE):
                    os._exit(2)
                data = json.dumps(dummy_tree(), separators=(",", ":")).encode()
                server.sendall(T.HEADER.pack(T.MAGIC, len(data), T.GET_TREE) + data)
                server.close()
                os._exit(0)
            except (OSError, TimeoutError, ValueError):
                os._exit(3)
        server.close()
        try:
            observed = S.inspect_original_sway_socket_peer_ci_only(**args)
            self.assertEqual(observed["sourceOnlyOriginalPeerPid"], original_pid)
            self.assertNotEqual(child_pid, original_pid)
            self.assertFalse(observed["actualSwayIpcReplySenderProven"])
            self.assertFalse(observed["canRestoreBrave"])
        finally:
            waited, status = os.waitpid(child_pid, 0)
            self.assertEqual(waited, child_pid)
            self.assertEqual(status, 0)



if __name__=="__main__":
    unittest.main(verbosity=2)
