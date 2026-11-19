#!/usr/bin/env python3
"""C4b 1B: real forked nonroot Unix witness mock ↔ root controller in CI.

This is a deliberately disposable transport peer, NOT a production
independent witness. Root can impersonate/replace the same-machine peer;
caller pins, nonce and signing keys are CI fixtures.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import socket
import struct
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c4b_witness_transport_consumer_ci as T
import c4b_root_owned_controller_ledger_ci as L
import test_c4b_signed_external_checkpoint_ci as WTest

NOBODY = 65534


class WitnessUnixPeerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = WTest.ExternalControllerCheckpointTests(
            "test_01_separate_signed_fresh_checkpoint_matches_root_owned_state")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.sockdir = Path(tempfile.mkdtemp(
            prefix=T.SOCKET_DIR_PREFIX, dir="/run"))
        os.chown(self.sockdir, NOBODY, NOBODY)
        self.sockdir.chmod(0o700)
        self.sockpath = self.sockdir / "current-checkpoint.sock"
        self.addCleanup(lambda: shutil.rmtree(self.sockdir))
        self.server_pid = None

    def _cleanup_child(self):
        if self.server_pid is None:
            return
        try:
            waited, _ = os.waitpid(self.server_pid, os.WNOHANG)
            if waited == 0:
                os.kill(self.server_pid, signal.SIGTERM)
                os.waitpid(self.server_pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
        self.server_pid = None

    def server(self, mode="valid"):
        self.assertIsNone(self.server_pid, "one peer per fixture")
        pid = os.fork()
        if pid == 0:
            try:
                # For one adversarial case the root server deliberately
                # chowns its socket to nobody; SO_PEERCRED must still catch
                # that the actual listener process has root credentials.
                spoof = mode == "root_peer_spoofs_socket_owner"
                if not spoof:
                    os.setgroups([])
                    os.setgid(NOBODY)
                    os.setuid(NOBODY)
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                    server.bind(str(self.sockpath))
                    if spoof:
                        os.chown(self.sockpath, NOBODY, NOBODY)
                    os.chmod(self.sockpath, 0o600)
                    server.listen(1)
                    server.settimeout(4.0)
                    conn, _ = server.accept()
                    with conn:
                        conn.settimeout(3.0)
                        if mode == "timeout":
                            time.sleep(3.0)
                            os._exit(0)
                        header = self._read(conn, 4)
                        frame_size = struct.unpack("!I", header)[0]
                        assert 0 < frame_size < T.MAX_REQUEST
                        request = json.loads(self._read(conn, frame_size))
                        assert set(request) == {
                            "schema", "hostId", "challengeSha256"}
                        assert request["schema"] == T.REQUEST_SCHEMA

                        proof = self.fixture.raw
                        signature = self.fixture.sig
                        if mode == "bad_sig":
                            signature = bytes(64)
                        envelope = {
                            "schema": T.RESPONSE_SCHEMA,
                            "signedCheckpointHex": proof.hex(),
                            "checkpointSignatureHex": signature.hex(),
                        }
                        payload = T._canonical(envelope)
                        if mode == "extra_field":
                            envelope["grant"] = True
                            payload = T._canonical(envelope)
                        elif mode == "bad_schema":
                            envelope["schema"] = "production-auth"
                            payload = T._canonical(envelope)
                        elif mode == "duplicate_field":
                            payload = payload.replace(
                                b'"schema":', b'"schema":"forged","schema":', 1)
                        elif mode == "noncanonical":
                            payload = json.dumps(envelope, indent=2).encode()
                        elif mode == "malformed":
                            payload = b"{bad"
                        elif mode == "truncated":
                            conn.sendall(struct.pack("!I", len(payload) + 7))
                            conn.sendall(payload)
                            os._exit(0)
                        elif mode == "oversized":
                            conn.sendall(struct.pack("!I", T.MAX_FRAME + 1))
                            os._exit(0)
                        conn.sendall(struct.pack("!I", len(payload)) + payload)
            except (BaseException):
                os._exit(3)
            os._exit(0)
        self.server_pid = pid
        self.addCleanup(self._cleanup_child)
        for _ in range(200):
            if self.sockpath.exists():
                return
            time.sleep(0.005)
        self.fail("disposable nonroot Unix witness did not bind")

    @staticmethod
    def _read(conn, size):
        data = bytearray()
        while len(data) < size:
            chunk = conn.recv(size - len(data))
            if not chunk:
                raise EOFError("unexpected peer EOF")
            data.extend(chunk)
        return bytes(data)

    def args(self, **overrides):
        params = {
            "socket_path": self.sockpath,
            "controller_state": self.fixture._state(),
            "fresh_challenge": self.fixture.challenge,
            "separately_pinned_peer_uid": NOBODY,
            "separately_pinned_peer_gid": NOBODY,
            "separately_pinned_peer_pid": self.server_pid,
            "separately_pinned_witness_root": self.fixture.witness.public_key(),
            "separately_pinned_witness_sha256":
                self.fixture.external()["independently_pinned_witness_sha256"],
        }
        params.update(overrides)
        return params

    def check(self, **overrides):
        return T.fetch_current_witness_ci_only(**self.args(**overrides))

    def refused(self, **overrides):
        with self.assertRaises(T.Refused):
            self.check(**overrides)

    def test_01_nonroot_real_socket_peer_and_signed_witness_match(self):
        self.server()
        checked = self.check()
        self.assertTrue(checked["unixPeerPidUidGidMatchedCallerPinsInCI"])
        self.assertTrue(checked["externalSignedCheckpointMatchedControllerInCI"])
        self.assertTrue(all(v is False for v in T.NEGATIVE.values()))
        self.assertEqual(self.fixture._state()["transitionSequence"], 4)

    def test_02_valid_peer_witness_can_feed_root_owned_ci_rotation(self):
        self.server()
        verified = self.check()
        self.fixture.base.stage()
        result = L.verify_and_commit_rotation_with_checkpoint_ci_only(
            self.fixture.base.root,
            signed_external_checkpoint=verified["witnessInputs"],
            **self.fixture.base.args(),
        )
        self.assertTrue(result["singlePrivilegedTestIntentConsumedInCi"])
        self.assertEqual(self.fixture.base.current()["transitionSequence"], 5)

    def test_03_kernel_detects_spoofed_server_uid_despite_socket_owner(self):
        self.server("root_peer_spoofs_socket_owner")
        self.refused()

    def test_04_wrong_independently_pinned_server_pid_refuses(self):
        self.server()
        self.refused(separately_pinned_peer_pid=self.server_pid + 1)

    def test_05_wrong_independently_pinned_server_gid_refuses(self):
        self.server()
        self.refused(separately_pinned_peer_gid=NOBODY - 1)

    def test_06_invalid_guest_signature_refuses(self):
        self.server("bad_sig")
        self.refused()

    def test_07_extra_production_grant_field_refuses(self):
        self.server("extra_field")
        self.refused()

    def test_08_wrong_response_schema_refuses(self):
        self.server("bad_schema")
        self.refused()

    def test_09_duplicate_json_fields_refuse(self):
        self.server("duplicate_field")
        self.refused()

    def test_10_noncanonical_response_refuses(self):
        self.server("noncanonical")
        self.refused()

    def test_11_malformed_json_response_refuses(self):
        self.server("malformed")
        self.refused()

    def test_12_truncated_payload_refuses(self):
        self.server("truncated")
        self.refused()

    def test_13_unbounded_length_prefix_refuses_before_allocation(self):
        self.server("oversized")
        self.refused()

    def test_14_new_challenge_cannot_use_old_signed_witness_response(self):
        self.server()
        self.refused(fresh_challenge=b"x" * 32)

    def test_15_old_witness_state_refuses_after_successful_rotation(self):
        # Advance local controller through its separately verified old state,
        # then query a peer whose signed bytes still describe that old state.
        self.fixture.base.stage()
        self.fixture.commit()
        self.server()
        self.refused()

    def test_16_missing_socket_or_wrong_directory_refuses(self):
        self.refused(separately_pinned_peer_pid=2048)
        self.refused(socket_path=Path("/tmp/current-checkpoint.sock"),
                     separately_pinned_peer_pid=2048)

    def test_17_socket_symlink_or_directory_mode_refuses(self):
        self.server()
        alias = self.sockdir / "alias"
        alias.symlink_to(self.sockpath)
        self.addCleanup(alias.unlink)
        self.refused(socket_path=alias)
        self.sockdir.chmod(0o777)
        self.addCleanup(self.sockdir.chmod, 0o700)
        self.refused()

    def test_18_rejects_wrong_signed_witness_root_pin(self):
        self.server()
        self.refused(separately_pinned_witness_sha256="f" * 64)

    def test_19_rejects_wrong_caller_host_identity(self):
        self.server()
        bad = self.fixture._state()
        bad["hostId"] = "postapollo-identity-ci@different-host"
        self.refused(controller_state=bad)

    def test_20_wrong_caller_input_types_fail_without_network(self):
        self.refused(fresh_challenge=b"x", separately_pinned_peer_pid=2048)
        self.refused(separately_pinned_peer_pid=True)
        self.refused(socket_path="/run/test", separately_pinned_peer_pid=2048)

    def test_21_transport_has_no_native_permission_or_signing_key(self):
        src = Path(T.__file__).read_text()
        for forbidden in ("Ed25519PrivateKey.generate(", "systemctl start",
                          "rpm-ostree install", '"hostAuthenticated": True',
                          '"productionAuthority": True'):
            self.assertNotIn(forbidden, src)
        self.assertTrue(all(v is False for v in T.NEGATIVE.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
