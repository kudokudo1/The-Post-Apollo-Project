#!/usr/bin/env python3
"""DOC 1: no read-only diagnostic or fixed refusal settles protected commands."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest

SRC = Path(__file__).resolve().parent / "c3e_release_trust"
FILE = SRC / "C3eIpcReceiptNonEvidenceCI.py"
spec = importlib.util.spec_from_file_location("c3e_ipc_nonsettlement", FILE)
if spec is None or spec.loader is None:
    raise RuntimeError("C3E_IPC_NONSETTLEMENT_SOURCE_MISSING")
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


class ReadOnlyIpcNonEvidenceTests(unittest.TestCase):
    NONCE = "ab" * 16
    HEAD = "12" * 32

    def frame(self, payload):
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return struct.pack(">I", len(raw)) + raw

    def diagnostic(self, op="SNAPSHOT"):
        if op == "SNAPSHOT":
            result = {"schema": M.P.S.SCHEMA, "status": M.P.S.STATUS_LOCAL,
                      "source": M.P.S.LOCAL_DEVELOPMENT,
                      "testHeadSha256": self.HEAD, "testSequence": 7,
                      **M.P.S.DENIED}
        elif op == "OUTCOME":
            result = {"schema": M.P.S.SCHEMA, "status": M.P.S.STATUS_LOCAL,
                      "source": M.P.S.LOCAL_DEVELOPMENT,
                      "testState": "issued", "testHeadSha256": None,
                      **M.P.S.DENIED}
        else:
            result = {"schema": M.P.S.SCHEMA, "status": M.P.S.STATUS_HOLD,
                      "source": M.P.S.PROTECTED_REQUIRED, **M.P.S.DENIED}
        return {"schema": M.P.REPLY_SCHEMA, "status": "IPC_CI_DIAGNOSTIC_ONLY",
                "requestNonce": self.NONCE, "result": result, **M.P.S.DENIED}

    def observe(self, op="SNAPSHOT", reply=None, delivery="COMPLETE_FRAME",
                nonce=None):
        if reply is None and delivery == "COMPLETE_FRAME":
            reply = self.frame(self.diagnostic(op))
        return M.observe_ci_only(
            operation=op,
            expected_request_nonce=self.NONCE if nonce is None else nonce,
            delivery_state=delivery,
            response_frame=reply,
        )

    def all_denied(self, out):
        self.assertEqual(out["schema"], M.SCHEMA)
        self.assertEqual(out["terminalStatus"], "PROTECTED_OUTCOME_UNPROVEN")
        self.assertEqual(
            out["next"], "HOLD_NO_AUTOMATIC_RETRY_REQUIRE_INDEPENDENT_CUSTODIAN")
        self.assertEqual(set(out), {"schema", "status", "terminalStatus",
                                    "next", *M.DENIED})
        for name in M.DENIED:
            self.assertIs(out[name], False, name)

    def test_01_snapshot_is_local_diagnostic_not_receipt(self):
        out = self.observe()
        self.assertEqual(out["status"], M.RECEIVED_DIAGNOSTIC)
        self.all_denied(out)

    def test_02_issued_local_nonce_does_not_prove_noncommit(self):
        out = self.observe("OUTCOME")
        self.assertEqual(out["status"], M.RECEIVED_DIAGNOSTIC)
        self.assertIs(out["protectedNonCommitVerified"], False)
        self.all_denied(out)

    def test_03_consumed_local_nonce_does_not_prove_protected_commit(self):
        payload = self.diagnostic("OUTCOME")
        payload["result"].update(testState="consumed", testHeadSha256=self.HEAD)
        out = self.observe("OUTCOME", self.frame(payload))
        self.assertEqual(out["status"], M.RECEIVED_DIAGNOSTIC)
        self.assertIs(out["protectedCommitVerified"], False)
        self.all_denied(out)

    def test_04_protected_custodian_hold_is_not_settlement(self):
        out = self.observe("CUSTODIAN_STATUS")
        self.assertEqual(out["status"], M.RECEIVED_DIAGNOSTIC)
        self.all_denied(out)

    def test_05_fixed_ipc_refusal_does_not_prove_any_earlier_noncommit(self):
        out = self.observe(reply=self.frame(dict(M.P.REFUSAL)))
        self.assertEqual(out["status"], M.RECEIVED_REFUSAL)
        self.assertIs(out["protectedNonCommitVerified"], False)
        self.all_denied(out)

    def test_06_fixed_refusal_has_no_request_nonce_or_receipt_identity(self):
        original = dict(M.P.REFUSAL)
        self.assertNotIn("requestNonce", original)
        self.assertNotIn("signedTerminalReceipt", original)
        self.all_denied(self.observe(reply=self.frame(original)))

    def test_07_timeout_even_with_fake_success_frame_stays_unknown(self):
        out = self.observe(reply=self.frame(self.diagnostic()),
                           delivery="TIMEOUT")
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_08_eof_stays_unknown(self):
        out = self.observe(reply=b"", delivery="EOF")
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_09_child_exit_stays_unknown(self):
        out = self.observe(reply=None, delivery="CHILD_EXIT")
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_10_send_error_stays_unknown(self):
        self.all_denied(self.observe(delivery="SEND_ERROR"))

    def test_11_truncated_transport_event_stays_unknown(self):
        self.all_denied(self.observe(delivery="TRUNCATED_FRAME"))

    def test_12_no_reply_stays_unknown(self):
        self.all_denied(self.observe(delivery="NO_REPLY"))

    def test_13_complete_event_with_no_frame_stays_unknown(self):
        out = M.observe_ci_only(
            operation="SNAPSHOT", expected_request_nonce=self.NONCE,
            delivery_state="COMPLETE_FRAME", response_frame=None)
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_14_truncated_length_header_stays_unknown(self):
        out = self.observe(reply=b"\x00\x00")
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_15_length_over_limit_stays_unknown(self):
        out = self.observe(reply=struct.pack(">I", M.P.MAX_FRAME + 1))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_16_trailing_data_stays_unknown(self):
        out = self.observe(reply=self.frame(self.diagnostic()) + b"payload")
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_17_duplicate_json_field_stays_unknown(self):
        raw = b'{"schema":"a","schema":"b"}'
        out = self.observe(reply=struct.pack(">I", len(raw)) + raw)
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_18_nonfinite_json_stays_unknown(self):
        raw = b'{"status":NaN}'
        out = self.observe(reply=struct.pack(">I", len(raw)) + raw)
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_19_extra_grant_key_blocks_diagnostic_interpretation(self):
        p = self.diagnostic()
        p["granted"] = True
        out = self.observe(reply=self.frame(p))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_20_nested_grant_blocks_diagnostic_interpretation(self):
        p = self.diagnostic()
        p["result"]["grant"] = {"production": True}
        out = self.observe(reply=self.frame(p))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_21_denied_flag_true_blocks_response(self):
        p = self.diagnostic()
        p["hostAuthenticated"] = True
        out = self.observe(reply=self.frame(p))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_22_mismatched_op_status_blocks_response(self):
        out = self.observe(op="SNAPSHOT",
                           reply=self.frame(self.diagnostic("CUSTODIAN_STATUS")))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_23_nonce_mismatch_blocks_response(self):
        p = self.diagnostic()
        p["requestNonce"] = "cd" * 16
        out = self.observe(reply=self.frame(p))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_24_wrong_reply_schema_blocks_response(self):
        p = self.diagnostic()
        p["schema"] = "postapollo.production-signed-receipt.v1"
        out = self.observe(reply=self.frame(p))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_25_forged_signed_receipt_field_not_accepted(self):
        p = self.diagnostic()
        p["signedTerminalReceipt"] = "not-a-receipt"
        out = self.observe(reply=self.frame(p))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_26_unknown_operation_refused_not_promoted(self):
        with self.assertRaisesRegex(M.Refused, "UNKNOWN_READ_ONLY_OPERATION"):
            self.observe(op="COMMIT_SIGNED_HISTORY")

    def test_27_invalid_request_nonce_refused(self):
        with self.assertRaisesRegex(M.Refused, "EXACT_REQUEST_NONCE"):
            self.observe(nonce="bad")

    def test_28_unknown_delivery_state_refused(self):
        with self.assertRaisesRegex(M.Refused, "INVALID_DELIVERY_STATE"):
            self.observe(delivery="SIGNED_SUCCESS")

    def test_29_refusal_with_extra_claim_is_not_valid_refusal(self):
        p = dict(M.P.REFUSAL, nonCommitVerified=True)
        out = self.observe(reply=self.frame(p))
        self.assertEqual(out["status"], M.NO_VERIFIED_FRAME)
        self.all_denied(out)

    def test_30_no_production_terminal_admission(self):
        with self.assertRaisesRegex(M.Refused, "NO_PROTECTED_RECEIPT"):
            M.protected_terminal_admission(self.diagnostic())
        self.all_denied(self.observe("OUTCOME"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
