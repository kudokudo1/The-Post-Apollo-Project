#!/usr/bin/env python3
"""DOC 1: actual named AF_UNIX accept() peer identity is still not host trust."""
from __future__ import annotations

import importlib.util
import multiprocessing
import os
from pathlib import Path
import shutil
import socket
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_ACCEPTED_EXPECTED_SOURCE_MISSING")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


M = _load("c3e_accepted_path_socket_under_test",
          HERE / "C3eAcceptedUnixReadOnlyPeerCI.py")
F = _load("c3e_accepted_original_local_ledger_fixture",
          ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


def _client(path, inherited_listener_fd, raw, pipe, *,
            fork_sender=False, half_close=False, drop_uid=False):
    try:
        os.close(inherited_listener_fd)
        if drop_uid:
            os.setgroups([])
            os.setgid(65534)
            os.setuid(65534)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(6)
            conn.connect(str(path))
            if fork_sender:
                pid = os.fork()
                if pid > 0:
                    conn.close()
                    waited, status = os.waitpid(pid, 0)
                    if waited != pid or not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                        pipe.send({"error": "FORKED_SENDER_FAILED"})
                    return
            conn.sendall(raw)
            if half_close:
                conn.shutdown(socket.SHUT_WR)
            response = M.P._read(conn)
            remaining = conn.recv(1)
            pipe.send({"reply": response, "senderPid": os.getpid(),
                       "replyEnded": remaining == b""})
            if fork_sender:
                os._exit(0)
    except BaseException as exc:
        pipe.send({"error": f"{type(exc).__name__}: {exc}"})
        if fork_sender:
            os._exit(121)
    finally:
        pipe.close()


class AcceptedUnixReadOnlyPeerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
                or not hasattr(socket, "SO_PEERCRED")):
            raise RuntimeError("C3E_ACCEPTED_HOSTED_ROOT_LINUX_REQUIRED")
        cls.ctx = multiprocessing.get_context("fork")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = Path(tempfile.mkdtemp(prefix="c3es-ci-", dir="/run"))
        os.chmod(self.root, 0o700)
        self.addCleanup(shutil.rmtree, self.root)
        self.sockpath = self.root / M.SOCKET_NAME
        self.local = M.P.S.TrustBoundary(
            required_mode=M.P.S.LOCAL_DEVELOPMENT,
            local_adapter=M.P.S.LocalSQLiteTestAdapter(
                M.P.S.L.DevelopmentLedger(self.fixture.work)))
        self.protected = M.P.S.TrustBoundary(
            required_mode=M.P.S.PROTECTED_REQUIRED)
        self.request = {
            "schema": M.P.SCHEMA,
            "op": "SNAPSHOT",
            "requestNonce": "df" * 16,
        }

    def framed(self, request=None):
        return M.P.frame_ci_only(self.request if request is None else request)

    def start_one(self, *, raw=None, boundary=None, pid_override=None,
                  fork_sender=False, half_close=False):
        listener = M.bind_one_ci_only(self.root)
        self.assertTrue(self.sockpath.exists())
        self.assertEqual(self.sockpath.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        recv, send = self.ctx.Pipe(duplex=False)
        client = self.ctx.Process(
            target=_client,
            args=(self.sockpath, listener.fileno(),
                  self.framed() if raw is None else raw, send),
            kwargs={"fork_sender": fork_sender, "half_close": half_close})
        client.start()
        send.close()
        server = self.ctx.Process(
            target=M.serve_one_ci_only,
            args=(listener, self.root,
                  self.local if boundary is None else boundary),
            kwargs={"expected_connecting_pid":
                    client.pid if pid_override is None else pid_override})
        server.start()
        listener.close()
        try:
            self.assertTrue(recv.poll(9), "client did not complete")
            outcome = recv.recv()
            client.join(timeout=5)
            server.join(timeout=5)
            self.assertEqual(client.exitcode, 0, outcome)
            self.assertEqual(server.exitcode, 0, outcome)
            self.assertNotIn("error", outcome, outcome)
            outcome["connectingPid"] = client.pid
            self.assertTrue(outcome["replyEnded"])
            self.assertFalse(self.sockpath.exists(),
                             "exact one-request listener must unlink path")
            return outcome
        finally:
            recv.close()
            for process in (client, server):
                if process.is_alive():
                    process.kill()
                    process.join(timeout=3)

    def denied(self, reply):
        self.assertEqual(reply["schema"], M.P.REPLY_SCHEMA)
        for flag in M.P.S.DENIED:
            self.assertIs(reply[flag], False, flag)

    def refused(self, *, request=None, raw=None, boundary=None,
                pid_override=None, half_close=False):
        out = self.start_one(
            raw=(self.framed(request) if request is not None else raw),
            boundary=boundary, pid_override=pid_override,
            half_close=half_close)["reply"]
        self.denied(out)
        self.assertEqual(out["status"], M.P.REFUSAL_STATUS)
        self.assertNotIn("result", out)
        return out

    def test_01_actual_named_fresh_accept_local_snapshot_only(self):
        client = self.start_one()
        out = client["reply"]
        self.denied(out)
        self.assertEqual(out["status"], "IPC_CI_DIAGNOSTIC_ONLY")
        self.assertEqual(out["result"]["testSequence"], self.fixture.seq)

    def test_02_protected_mode_uses_original_custodian_hold_only(self):
        client = self.start_one(
            raw=self.framed({**self.request, "op": "CUSTODIAN_STATUS"}),
            boundary=self.protected)
        out = client["reply"]
        self.assertEqual(out["result"]["status"], M.P.S.STATUS_HOLD)
        self.denied(out)

    def test_03_protected_mode_rejects_local_snapshot_fallback(self):
        self.refused(boundary=self.protected)

    def test_04_original_local_challenge_is_issued_diagnostic_only(self):
        req = {**self.request, "op": "OUTCOME",
               "challengeHex": self.fixture.challenge.hex()}
        out = self.start_one(raw=self.framed(req))["reply"]
        self.assertEqual(out["result"]["testState"], "issued")
        self.denied(out)

    def test_05_local_consumed_history_is_not_protected_settlement(self):
        self.fixture.commit()
        req = {**self.request, "op": "OUTCOME",
               "challengeHex": self.fixture.challenge.hex()}
        out = self.start_one(raw=self.framed(req))["reply"]
        self.assertEqual(out["result"]["testState"], "consumed")
        self.assertIs(out["result"]["productionAuthority"], False)

    def test_06_wrong_connecting_pid_is_refused_before_parser(self):
        self.refused(pid_override=os.getpid())

    def test_07_fake_begin_signin_request_is_refused(self):
        self.refused(request={**self.request, "op": "BEGIN_SIGNIN"})

    def test_08_fake_commit_history_request_is_refused(self):
        self.refused(request={**self.request, "op": "COMMIT_SIGNED_HISTORY"})

    def test_09_extra_request_grant_field_is_refused(self):
        self.refused(request={**self.request, "canBeginSignIn": True})

    def test_10_duplicate_json_operation_is_refused(self):
        raw = (b'{"schema":"' + M.P.SCHEMA.encode() +
               b'","op":"SNAPSHOT","op":"BEGIN_SIGNIN",'
               b'"requestNonce":"' + b"aa"*16 + b'"}')
        self.refused(raw=struct.pack(">I", len(raw)) + raw)

    def test_11_incomplete_frame_then_eof_refuses(self):
        self.refused(raw=b"\x00\x00\x00\x20{}", half_close=True)

    def test_12_outcome_challenge_must_match_known_local(self):
        self.refused(request={**self.request, "op": "OUTCOME",
                              "challengeHex": "ff" * 32})

    def test_13_accepted_socket_vanished_after_one_request(self):
        self.start_one()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            with self.assertRaises((FileNotFoundError, ConnectionRefusedError)):
                conn.connect(str(self.sockpath))

    def test_14_existing_regular_path_cannot_be_replaced(self):
        self.sockpath.write_text("dont-replace-fixture")
        with self.assertRaisesRegex(M.Refused, "EXISTING_SOCKET_NODE"):
            M.bind_one_ci_only(self.root)
        self.assertEqual(self.sockpath.read_text(), "dont-replace-fixture")

    def test_15_existing_symlink_cannot_be_overwritten(self):
        self.sockpath.symlink_to(self.root / "target")
        with self.assertRaisesRegex(M.Refused, "EXISTING_SOCKET_NODE"):
            M.bind_one_ci_only(self.root)
        self.assertTrue(self.sockpath.is_symlink())

    def test_16_unsafe_root_mode_refused(self):
        os.chmod(self.root, 0o755)
        with self.assertRaisesRegex(M.Refused, "UNSAFE_ROOT_OWNER_OR_MODE"):
            M.bind_one_ci_only(self.root)

    def test_17_unsafe_root_path_refused(self):
        with self.assertRaisesRegex(M.Refused, "UNSAFE_ROOT_PATH"):
            M.bind_one_ci_only(Path("/var/tmp"))

    def test_18_nonroot_process_cannot_enter_socket_directory(self):
        listener = M.bind_one_ci_only(self.root)
        recv, send = self.ctx.Pipe(duplex=False)
        p = self.ctx.Process(
            target=_client,
            args=(self.sockpath, listener.fileno(), self.framed(), send),
            kwargs={"drop_uid": True})
        p.start()
        send.close()
        listener.close()
        try:
            self.assertTrue(recv.poll(5))
            result = recv.recv()
            p.join(5)
            self.assertIn("PermissionError", result.get("error", ""))
            self.assertEqual(p.exitcode, 0)
        finally:
            recv.close()
            self.sockpath.unlink(missing_ok=True)
            if p.is_alive():
                p.kill()
                p.join(3)

    def test_19_fd_inheritance_after_connect_breaks_sender_pid_claim(self):
        # Connector is root client A, but an inherited socket FD can be
        # written by forked B. SO_PEERCRED tracks A's connect(), not B's write.
        result = self.start_one(fork_sender=True)
        self.assertNotEqual(result["senderPid"], result["connectingPid"])
        self.assertEqual(result["reply"]["status"], "IPC_CI_DIAGNOSTIC_ONLY")
        self.assertIs(
            M.denial_only_observation_ci_only()
            ["originalMessageSenderAuthenticated"], False)

    def test_20_even_correct_accepted_peer_is_not_enrolled_host(self):
        self.start_one()
        report = M.denial_only_observation_ci_only()
        self.assertIs(report["acceptedPeerAuthenticatedAsHost"], False)
        self.assertIs(report["custodianRootIndependentlyEnrolled"], False)
        self.assertIs(report["safeToRetry"], False)

    def test_21_forged_host_authentication_in_observation_refused(self):
        original = M.denial_only_observation_ci_only()
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_INJECTION"):
            M.assert_accepted_observation_no_authority_ci_only(
                dict(original, acceptedPeerAuthenticatedAsHost=True))

    def test_22_extra_terminal_receipt_field_refused(self):
        original = M.denial_only_observation_ci_only()
        with self.assertRaisesRegex(M.Refused, "DIAGNOSTIC_FIELDS"):
            M.assert_accepted_observation_no_authority_ci_only(
                dict(original, signedTerminalReceipt="forged"))

    def test_23_no_production_admission(self):
        with self.assertRaisesRegex(M.Refused, "NO_ENROLLED_SOURCE"):
            M.protected_admission()
        self.refused(request={**self.request, "op": "ENABLE_CREDENTIALS"})

    def test_24_untrusted_status_cannot_be_relabelled_settled(self):
        out = M.denial_only_observation_ci_only()
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_INJECTION"):
            M.assert_accepted_observation_no_authority_ci_only(
                dict(out, status="PROTECTED_COMMITTED"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
