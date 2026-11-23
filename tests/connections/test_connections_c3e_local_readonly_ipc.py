#!/usr/bin/env python3
"""DOC 1: separate disposable fork reads local diagnostics, never Sign-In."""
from __future__ import annotations

import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import socket
import struct
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_IPC_TEST_SOURCE_REQUIRED")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


M = _load("c3e_local_readonly_ipc_fixture", SRC / "C3eLocalReadOnlyIpcProbe.py")
F = _load("c3e_ipc_existing_local_tests",
          ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


def _recv_exact(sock, n):
    out = bytearray()
    while len(out) < n:
        data = sock.recv(n - len(out))
        if not data:
            raise RuntimeError("IPC_UNEXPECTED_CLOSE")
        out.extend(data)
    return bytes(out)


class LocalReadOnlyIpcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_IPC_DISPOSABLE_GITHUB_HOSTED_ROOT_REQUIRED")
        cls.fork = multiprocessing.get_context("fork")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        ledger = M.S.L.DevelopmentLedger(self.fixture.work)
        adapter = M.S.LocalSQLiteTestAdapter(ledger)
        self.local = M.S.TrustBoundary(
            required_mode=M.S.LOCAL_DEVELOPMENT,
            local_adapter=adapter,
        )
        self.protected = M.S.TrustBoundary(
            required_mode=M.S.PROTECTED_REQUIRED,
        )
        self.req = {
            "schema": M.SCHEMA,
            "op": "SNAPSHOT",
            "requestNonce": "a1" * 16,
        }

    def run_one(self, *, req=None, raw=None, mode="local", chunks=None,
                half_close=False):
        boundary = self.local if mode == "local" else self.protected
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        parent.settimeout(5)
        p = self.fork.Process(target=M.serve_one_ci_only,
                              args=(child, boundary))
        p.start()
        child.close()
        try:
            payload = (M.frame_ci_only(req if req is not None else self.req)
                       if raw is None else raw)
            if chunks is None:
                parent.sendall(payload)
            else:
                cursor = 0
                for step in chunks:
                    parent.sendall(payload[cursor:cursor + step])
                    cursor += step
                parent.sendall(payload[cursor:])
            if half_close:
                parent.shutdown(socket.SHUT_WR)
            n = struct.unpack(">I", _recv_exact(parent, 4))[0]
            self.assertLessEqual(n, M.MAX_FRAME)
            msg = json.loads(_recv_exact(parent, n).decode("ascii"))
            self.assertEqual(parent.recv(1), b"")  # child closes after one reply
        finally:
            parent.close()
            p.join(timeout=5)
            if p.is_alive():
                p.terminate()
                p.join(timeout=2)
        self.assertEqual(p.exitcode, 0)
        return msg

    def denied(self, reply):
        self.assertEqual(reply["schema"], M.REPLY_SCHEMA)
        for k in M.S.DENIED:
            self.assertIs(reply[k], False, k)

    def refused(self, *, req=None, raw=None, mode="local",
                half_close=False):
        out = self.run_one(req=req, raw=raw, mode=mode,
                           half_close=half_close)
        self.denied(out)
        self.assertEqual(out["status"], M.REFUSAL_STATUS)
        self.assertNotIn("result", out)
        return out

    def test_01_local_test_snapshot_in_real_child_is_diagnostic(self):
        out = self.run_one()
        self.denied(out)
        self.assertEqual(out["status"], "IPC_CI_DIAGNOSTIC_ONLY")
        self.assertEqual(out["requestNonce"], self.req["requestNonce"])
        self.assertEqual(out["result"]["status"], M.S.STATUS_LOCAL)
        self.assertEqual(out["result"]["testSequence"], self.fixture.seq)

    def test_02_protected_mode_status_is_hold(self):
        out = self.run_one(
            req={**self.req, "op": "CUSTODIAN_STATUS"}, mode="protected")
        self.denied(out)
        self.assertEqual(out["result"]["status"], M.S.STATUS_HOLD)
        for flag in M.S.DENIED:
            self.assertIs(out["result"][flag], False, flag)

    def test_03_protected_snapshot_has_no_local_fallback(self):
        self.refused(mode="protected")

    def test_04_protected_outcome_has_no_local_fallback(self):
        self.refused(mode="protected",
                     req={**self.req, "op": "OUTCOME",
                          "challengeHex": self.fixture.challenge.hex()})

    def test_05_protected_only_status_cannot_be_queried_in_local_mode(self):
        self.refused(req={**self.req, "op": "CUSTODIAN_STATUS"})

    def test_06_original_locally_issued_challenge_status_only(self):
        out = self.run_one(req={**self.req, "op": "OUTCOME",
                                "challengeHex": self.fixture.challenge.hex()})
        self.denied(out)
        self.assertEqual(out["result"]["testState"], "issued")
        self.assertIs(out["result"]["credentialActionsEnabled"], False)

    def test_07_local_consumed_history_visible_only_as_diagnostic(self):
        self.fixture.commit()
        out = self.run_one(req={**self.req, "op": "OUTCOME",
                                "challengeHex": self.fixture.challenge.hex()})
        self.denied(out)
        self.assertEqual(out["result"]["testState"], "consumed")
        self.assertIs(out["result"]["productionAuthority"], False)

    def test_08_local_signed_head_in_child_matches_original_test_state(self):
        self.fixture.commit()
        out = self.run_one()
        self.assertEqual(
            out["result"]["testHeadSha256"],
            self.fixture.ledger.snapshot()["previousHeadSha256"])
        self.denied(out)

    def test_09_invalid_request_schema_refused(self):
        self.refused(req={**self.req, "schema": "production"})

    def test_10_unknown_op_refused_even_if_named_commit(self):
        self.refused(req={**self.req, "op": "COMMIT_SIGNED_HISTORY"})

    def test_11_unknown_op_claiming_signin_refused(self):
        self.refused(req={**self.req, "op": "BEGIN_SIGNIN"})

    def test_12_extra_authority_flag_refused(self):
        self.refused(req={**self.req, "productionAuthority": True})

    def test_13_empty_nonce_refused(self):
        self.refused(req={**self.req, "requestNonce": ""})

    def test_14_boolean_nonce_refused(self):
        self.refused(req={**self.req, "requestNonce": True})

    def test_15_missing_nonce_refused(self):
        self.refused(req={"schema": M.SCHEMA, "op": "SNAPSHOT"})

    def test_16_duplicate_key_refused_without_trusting_last_value(self):
        raw = ('{"schema":"' + M.SCHEMA + '","op":"SNAPSHOT",'
               '"op":"BEGIN_SIGNIN","requestNonce":"' + "aa" * 16 + '"}')
        self.refused(raw=struct.pack(">I", len(raw)) + raw.encode("ascii"))

    def test_17_nonobject_request_refused(self):
        self.refused(raw=struct.pack(">I", 2) + b"[]")

    def test_18_malformed_json_refused(self):
        self.refused(raw=struct.pack(">I", 7) + b"{wrong}")

    def test_19_oversized_frame_rejected_before_reading_body(self):
        self.refused(raw=struct.pack(">I", M.MAX_FRAME + 1))

    def test_20_zero_length_frame_refused(self):
        self.refused(raw=struct.pack(">I", 0))

    def test_21_outcome_without_exact_challenge_refused(self):
        self.refused(req={**self.req, "op": "OUTCOME"})

    def test_22_invalid_challenge_hex_refused(self):
        self.refused(req={**self.req, "op": "OUTCOME",
                          "challengeHex": "zz" * 32})

    def test_23_outcome_wrong_challenge_refused(self):
        self.refused(req={**self.req, "op": "OUTCOME",
                          "challengeHex": "ff" * 32})

    def test_24_unused_challenge_field_refused(self):
        self.refused(req={**self.req,
                          "challengeHex": self.fixture.challenge.hex()})

    def test_25_nonfinite_number_refused(self):
        raw = ('{"schema":"' + M.SCHEMA + '","op":"SNAPSHOT",'
               '"requestNonce":"' + "aa" * 16 + '","extra":NaN}')
        self.refused(raw=struct.pack(">I", len(raw)) + raw.encode("ascii"))

    def test_26_fragmented_frame_works_without_length_confusion(self):
        out = self.run_one(chunks=(1, 2, 1, 9, 4))
        self.denied(out)
        self.assertEqual(out["result"]["status"], M.S.STATUS_LOCAL)

    def test_27_no_fallback_when_backend_missing(self):
        original = self.protected._local
        self.assertIsNone(original)
        self.refused(mode="protected")
        self.assertIsNone(self.protected._local)

    def test_28_no_production_endpoint_exists_in_test_transport(self):
        with self.assertRaisesRegex(M.Refused, "NO_REAL_SIGNIN"):
            M.production_admission()
        self.refused(req={**self.req, "op": "ENABLE_CREDENTIALS"})


    def reject_injected_result(self, value, *, method="read_current_snapshot",
                               mode="local", req=None):
        boundary = self.local if mode == "local" else self.protected
        with mock.patch.object(boundary, method, return_value=value):
            return self.refused(req=req, mode=mode)

    def test_29_extra_positive_grant_field_not_forwarded(self):
        malicious = dict(self.local.read_current_snapshot())
        malicious["authorizationGranted"] = True
        self.reject_injected_result(malicious)

    def test_30_nested_positive_authority_not_forwarded(self):
        malicious = dict(self.local.read_current_snapshot())
        malicious["nested"] = {"credentialActionsEnabled": True}
        self.reject_injected_result(malicious)

    def test_31_local_snapshot_cannot_claim_protected_hold_status(self):
        malicious = dict(self.local.read_current_snapshot())
        malicious["status"] = M.S.STATUS_HOLD
        self.reject_injected_result(malicious)

    def test_32_local_snapshot_cannot_claim_protected_source(self):
        malicious = dict(self.local.read_current_snapshot())
        malicious["source"] = M.S.PROTECTED_REQUIRED
        self.reject_injected_result(malicious)

    def test_33_bool_as_test_sequence_refused(self):
        malicious = dict(self.local.read_current_snapshot())
        malicious["testSequence"] = True
        self.reject_injected_result(malicious)

    def test_34_malformed_snapshot_head_refused(self):
        malicious = dict(self.local.read_current_snapshot())
        malicious["testHeadSha256"] = "0"
        self.reject_injected_result(malicious)

    def test_35_missing_denied_field_not_forwarded(self):
        malicious = dict(self.local.read_current_snapshot())
        malicious.pop("hostAuthenticated")
        self.reject_injected_result(malicious)

    def test_36_extra_outcome_claim_not_forwarded(self):
        malicious = dict(
            self.local.lookup_terminal_outcome(self.fixture.challenge))
        malicious["remoteGrant"] = {"enabled": True}
        self.reject_injected_result(
            malicious, method="lookup_terminal_outcome",
            req={**self.req, "op": "OUTCOME",
                 "challengeHex": self.fixture.challenge.hex()})

    def test_37_outcome_consumed_without_head_refused(self):
        malicious = dict(
            self.local.lookup_terminal_outcome(self.fixture.challenge))
        malicious["testState"] = "consumed"
        malicious["testHeadSha256"] = None
        self.reject_injected_result(
            malicious, method="lookup_terminal_outcome",
            req={**self.req, "op": "OUTCOME",
                 "challengeHex": self.fixture.challenge.hex()})

    def test_38_outcome_issued_with_head_refused(self):
        malicious = dict(
            self.local.lookup_terminal_outcome(self.fixture.challenge))
        malicious["testState"] = "issued"
        malicious["testHeadSha256"] = "f" * 64
        self.reject_injected_result(
            malicious, method="lookup_terminal_outcome",
            req={**self.req, "op": "OUTCOME",
                 "challengeHex": self.fixture.challenge.hex()})

    def test_39_protected_hold_with_extra_authority_refused(self):
        malicious = dict(self.protected.protected_required_status())
        malicious["grantToken"] = "fake"
        self.reject_injected_result(
            malicious, method="protected_required_status",
            mode="protected",
            req={**self.req, "op": "CUSTODIAN_STATUS"})

    def test_40_protected_hold_cannot_claim_local_status(self):
        malicious = dict(self.protected.protected_required_status())
        malicious["status"] = M.S.STATUS_LOCAL
        self.reject_injected_result(
            malicious, method="protected_required_status",
            mode="protected",
            req={**self.req, "op": "CUSTODIAN_STATUS"})

    def test_41_protected_hold_cannot_claim_enrolled_authority(self):
        malicious = dict(self.protected.protected_required_status())
        malicious["protectedCustodianReachable"] = True
        self.reject_injected_result(
            malicious, method="protected_required_status",
            mode="protected",
            req={**self.req, "op": "CUSTODIAN_STATUS"})

    def test_42_protected_snapshot_cannot_be_forged_as_local(self):
        forged = dict(self.local.read_current_snapshot())
        self.reject_injected_result(
            forged, method="read_current_snapshot", mode="protected")


    def test_43_partial_length_header_half_closed_returns_fixed_refusal(self):
        # The sender has finished writing, but the length header is truncated.
        self.refused(raw=b"\x00\x00", half_close=True)

    def test_44_partial_body_half_closed_returns_fixed_refusal(self):
        # Three bytes were promised; only one was transmitted.
        self.refused(raw=struct.pack(">I", 3) + b"{", half_close=True)

    def test_45_partial_length_header_left_open_times_out_to_refusal(self):
        # The sender neither completes the frame nor closes its write side.
        self.refused(raw=b"\x00")

    def test_46_partial_json_body_left_open_times_out_to_refusal(self):
        # A complete header with a body shorter than its advertised length.
        self.refused(raw=struct.pack(">I", 10) + b"{")



if __name__ == "__main__":
    unittest.main(verbosity=2)
