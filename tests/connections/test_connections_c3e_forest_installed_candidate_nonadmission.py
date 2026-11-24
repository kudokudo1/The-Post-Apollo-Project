#!/usr/bin/env python3
"""DOC 1: C3e evaluates actual installed B5c public HOLD, never a Forest grant."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import traceback
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "c3e_release_trust/C3eForestInstalledCandidateNonAdmissionCI.py"
HOST = Path("/usr/libexec/post-apollo/forest-ci/forest-host")
PYTHON = "/usr/bin/python3"
TEST_SHA = "a9" * 32

spec = importlib.util.spec_from_file_location("c3e_forest_b5c_nonadmission", SOURCE)
if spec is None or spec.loader is None:
    raise RuntimeError("C3E_FOREST_CUSTODIAN_SOURCE_UNAVAILABLE")
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)

HOLD = {
    "schema": M.SOURCE_SCHEMA,
    "status": "UNKNOWN_HOLD",
    "sourceAuthenticated": False,
    "recipientAuthenticated": False,
    "permissionGranted": False,
    "productionAuthority": False,
    "privateBytesSubmitted": 0,
    "revocationFencedAck": False,
    "safeActions": [],
}


def packet(reply=None):
    return json.dumps(HOLD if reply is None else reply, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=True).encode("ascii")


class StrictPublicHoldNotForestCustody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_FOREST_TEST_GITHUB_HOSTED_ONLY")

    def inspect(self, wire=None, sha=TEST_SHA):
        return M.inspect_public_hold_ci_only(
            packet() if wire is None else wire,
            controller_expected_source_sha256=sha)

    def deny_flags(self, result):
        self.assertEqual(result["schema"], M.SCHEMA)
        self.assertEqual(result["status"], M.STATUS)
        self.assertEqual(result["next"],
                         "HOLD_NO_INDEPENDENT_FOREST_CUSTODIAN_OR_PRIVATE_DATA")
        self.assertEqual(result["safeActions"], [])
        self.assertIsNone(result["winner"])
        self.assertEqual(result["originalStatus"], "UNKNOWN_HOLD")
        self.assertFalse(result["packageDigestIsOperatorEnrollment"])
        for key in M.AUTHORITY_FALSE:
            self.assertIs(result[key], False, key)
        self.assertEqual(set(result), {
            "schema", "status", "publicPacketSha256",
            "controllerTestSourceSha256", "packageDigestIsOperatorEnrollment",
            "originalStatus", "next", "safeActions", "winner",
            *M.AUTHORITY_FALSE,
        })

    def test_01_correct_public_hold_packet_still_no_enrollment(self):
        result = self.inspect()
        self.deny_flags(result)
        self.assertEqual(result["publicPacketSha256"],
                         hashlib.sha256(packet()).hexdigest())
        self.assertEqual(result["controllerTestSourceSha256"], TEST_SHA)

    def test_02_missing_ack_is_unknown_no_retry(self):
        with self.assertRaisesRegex(M.UnknownHold, "UNKNOWN_HOLD_NO_RETRY"):
            self.inspect(b"")

    def test_03_wrong_schema_refused(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, schema="postapollo.identity")))

    def test_04_private_title_field_cannot_enter_public_response(self):
        with self.assertRaisesRegex(M.Refused, "UNEXPECTED_FIELDS_OR_PRIVATE"):
            self.inspect(packet(dict(HOLD, privateTitle="example private")))

    def test_05_list_sessions_positive_grant_refused(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, permissionGranted=True)))

    def test_06_forged_enrolled_source_refused(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, sourceAuthenticated=True)))

    def test_07_forged_recipient_refused(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, recipientAuthenticated=True)))

    def test_08_forged_revocation_ack_refused(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, revocationFencedAck=True)))

    def test_09_forged_production_authority_refused(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, productionAuthority=True)))

    def test_10_private_bytes_never_recognized_as_public(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, privateBytesSubmitted=1)))

    def test_11_boolean_zero_private_bytes_is_not_integer(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, privateBytesSubmitted=False)))

    def test_12_forged_safe_actions_refused(self):
        with self.assertRaisesRegex(M.Refused, "AUTHORITY_CLAIM"):
            self.inspect(packet(dict(HOLD, safeActions=["LIST_SESSIONS"])))

    def test_13_signed_identity_unavailable_is_not_forest(self):
        with self.assertRaisesRegex(M.Refused, "UNEXPECTED_FIELDS_OR_PRIVATE"):
            self.inspect(packet({
                "schema": "postapollo.connections.c3e-custodian-denial-candidate-ci-v1",
                "status": "UNAVAILABLE", "signatureB64url": "a" * 86,
            }))

    def test_14_duplicate_fields_refused(self):
        raw = packet()
        with self.assertRaisesRegex(M.Refused, "DUPLICATE_JSON_KEY"):
            self.inspect(b'{"status":"COMMITTED",' + raw[1:])

    def test_15_trailing_json_refused(self):
        with self.assertRaisesRegex(M.Refused, "INVALID_UTF8_JSON"):
            self.inspect(packet() + b"{}")

    def test_16_nonfinite_number_refused(self):
        with self.assertRaisesRegex(M.Refused, "NONFINITE_JSON"):
            self.inspect(packet().replace(b'"privateBytesSubmitted":0',
                                           b'"privateBytesSubmitted":NaN'))

    def test_17_oversized_packet_refused(self):
        with self.assertRaisesRegex(M.Refused, "OVERSIZE"):
            self.inspect(packet() + b"X" * 2000)

    def test_18_caller_supplied_source_digest_does_not_enroll_root(self):
        self.deny_flags(self.inspect(sha="f" * 64))
        with self.assertRaisesRegex(M.Refused, "CONTROLLER_TEST_DIGEST_REQUIRED"):
            self.inspect(sha="not-operator-enrolled")

    def test_19_cannot_run_as_self_hosted_evidence(self):
        with mock.patch.dict(os.environ, {"RUNNER_ENVIRONMENT": "self-hosted"}):
            with self.assertRaisesRegex(M.Refused, "GITHUB_HOSTED_CI_ONLY"):
                self.inspect()

    def test_20_no_production_authorization_entrypoint(self):
        self.deny_flags(self.inspect())
        with self.assertRaisesRegex(M.Refused, "NOT_PROTECTED_OR_ENROLLED"):
            M.protected_forest_admission()

    def test_25_malformed_utf8_json_and_deep_input_have_no_decoder_chain(self):
        marker = b"PRIVATE_FIXTURE_NOT_FOR_DIAGNOSTICS"
        for raw in (b'{"title":"' + marker,
                    b'{"title":"' + marker + b'\xff"}',
                    b"[" * M.MAX_FRAME):
            with self.subTest(length=len(raw)):
                with self.assertRaisesRegex(M.Refused, "INVALID_UTF8_JSON") as caught:
                    self.inspect(raw)
                error = caught.exception
                self.assertIsNone(error.__cause__)
                self.assertIsNone(error.__context__)
                self.assertNotIn(marker.decode("ascii"),
                                 "".join(traceback.format_exception(error)))

    def test_26_hook_refusals_keep_fixed_codes_without_chains(self):
        marker = b"PRIVATE_FIXTURE_NOT_FOR_DIAGNOSTICS"
        for raw, code in (
            (b'{"' + marker + b'":0,"' + marker + b'":1}', "DUPLICATE_JSON_KEY"),
            (b'{"' + marker + b'":NaN}', "NONFINITE_JSON"),
        ):
            with self.subTest(code=code):
                with self.assertRaisesRegex(M.Refused, code) as caught:
                    self.inspect(raw)
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)
                self.assertNotIn(marker.decode("ascii"),
                                 "".join(traceback.format_exception(caught.exception)))

    def test_27_valid_result_mutation_does_not_change_next_refusal_diagnostic(self):
        result = self.inspect()
        result["productionSignInAllowed"] = True
        result["safeToRetry"] = True
        result["safeActions"].append("LIST_SESSIONS")
        self.deny_flags(self.inspect())
        with self.assertRaisesRegex(M.Refused, "NOT_PROTECTED_OR_ENROLLED"):
            M.protected_forest_admission()


@unittest.skipUnless(os.environ.get("FOREST_B5C_INSTALLED") == "true",
                     "Requires separate disposable Fedora RPM-installed B5c test")
class ActuallyInstalledForestHostStillUntrusted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (os.getuid() == 0 or os.geteuid() == 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_FOREST_INSTALLED_UNPRIVILEGED_CI_ONLY")
        cls.expected = os.environ.get("EXPECTED_SOURCE_SHA", "")
        if M.SHA256_HEX.fullmatch(cls.expected) is None:
            raise RuntimeError("C3E_FOREST_INSTALLED_EXPECTED_DIGEST_MISSING")

    def launch(self):
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        parent.settimeout(5)
        self.addCleanup(parent.close)
        self.addCleanup(child.close)
        fd = child.fileno()
        inode = os.fstat(fd).st_ino
        command = [PYTHON, "-I", "-B", str(HOST),
                   "--disposable-test-fd", str(fd)]
        process = subprocess.Popen(
            command, pass_fds=(fd,), cwd="/",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.addCleanup(self.reap, process)
        child.close()
        return parent, process, fd, inode, command

    @staticmethod
    def reap(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def finish(self, process, expected_code):
        out, err = process.communicate(timeout=5)
        self.assertEqual(process.returncode, expected_code)
        self.assertEqual((out, err), (b"", b""))

    def test_21_actual_installed_source_is_exact_controller_test_bytes(self):
        info = HOST.lstat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual((info.st_uid, info.st_gid), (0, 0))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o555)
        self.assertEqual(hashlib.sha256(HOST.read_bytes()).hexdigest(),
                         self.expected)
        owner = subprocess.run(["rpm", "-qf", str(HOST)],
                               capture_output=True, text=True, timeout=5)
        self.assertEqual(owner.returncode, 0)
        self.assertTrue(owner.stdout.strip().startswith(
            "post-apollo-forest-host-ci-"))

    def test_22_actual_installed_child_public_packet_does_not_enroll_c3e(self):
        channel, process, fd, inode, command = self.launch()
        self.assertNotEqual(process.pid, os.getpid())
        self.assertEqual(os.readlink(f"/proc/{process.pid}/fd/{fd}"),
                         f"socket:[{inode}]")
        cmdline = (Path(f"/proc/{process.pid}/cmdline").read_bytes()
                   .rstrip(b"\0").split(b"\0"))
        self.assertEqual(cmdline, [x.encode() for x in command])
        channel.sendall(b"STATUS")
        raw = channel.recv(4096)
        outcome = M.inspect_public_hold_ci_only(
            raw, controller_expected_source_sha256=self.expected)
        self.assertEqual(outcome["status"], M.STATUS)
        self.assertIsNone(outcome["winner"])
        self.assertEqual(outcome["safeActions"], [])
        for key in M.AUTHORITY_FALSE:
            self.assertIs(outcome[key], False, key)
        self.assertEqual(channel.recv(4096), b"")
        self.finish(process, 0)

    def test_23_actual_protected_controls_always_hold(self):
        controls = (
            b"LIST_SESSIONS", b"DISCLOSE_SESSION_TITLES",
            b"READ_SESSION", b"GENERATE", b"DISCLOSE_PROVISIONAL",
            b"COMMIT_GENERATE", b"SEND", b"VOICE",
        )
        for token in controls:
            with self.subTest(token=token):
                channel, process, _, _, _ = self.launch()
                channel.sendall(token)
                result = M.inspect_public_hold_ci_only(
                    channel.recv(4096),
                    controller_expected_source_sha256=self.expected)
                self.assertEqual(result["status"], M.STATUS)
                self.assertIs(result["forestListSessionsAllowed"], False)
                self.assertIs(result["forestPrivateTitleDisclosureAllowed"], False)
                self.assertIs(result["forestProvisionalEgressAllowed"], False)
                self.assertEqual(channel.recv(4096), b"")
                self.finish(process, 0)

    def test_24_bad_private_command_has_no_response_or_retry(self):
        channel, process, _, _, _ = self.launch()
        channel.sendall(b"LIST_SESSIONS private-title")
        raw = channel.recv(4096)
        with self.assertRaisesRegex(M.UnknownHold, "UNKNOWN_HOLD_NO_RETRY"):
            M.inspect_public_hold_ci_only(
                raw, controller_expected_source_sha256=self.expected)
        self.finish(process, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
