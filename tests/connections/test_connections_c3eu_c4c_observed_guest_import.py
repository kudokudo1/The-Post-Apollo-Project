#!/usr/bin/env python3
"""C3e-U: strict compatibility with merged *real C4c guest producer source*.

The positive report fixture matches the actual C4c emitted-field AST, but is
still synthetic test data: no claim that an independently authenticated C4c
UART artifact was retrieved. This consumer explicitly REFUSES production use.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eUObservedGuestImport.py"
C4C = ROOT / "tests/connections/c4b_silverblue/guest_confined_runtime.sh"
Q = ROOT / "tests/connections/c3e_release_trust/C3eQSignedGuestEvidence.py"
SPEC = importlib.util.spec_from_file_location("c3eu", SOURCE)
assert SPEC and SPEC.loader
U = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(U)


class C3eUC4cImportContract(unittest.TestCase):
    def setUp(self):
        self.rpm, self.script, self.python = "a"*64, "b"*64, "c"*64
        self.report = {
            "schema": U.SCHEMA,
            "signed_rpm_sha256": self.rpm,
            "signed_script_sha256": self.script,
            "running_script_sha256": self.script,
            "interpreter_sha256": self.python,
            "service_pid": 9881,
            "dbus_owner_pid": 9881,
            "process_start_ticks": "111337",
            "service_uid": 997,
            "service_gid": 997,
            "systemd_unit": U.UNIT,
            "selinux_enforcing": True,
            "signedGuestOriginAuthenticated": False,
            "evidenceCryptographicallyAttested": False,
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }
        self.pins = {
            "independent_signed_rpm_sha256": self.rpm,
            "independent_signed_script_sha256": self.script,
            "independent_interpreter_sha256": self.python,
            "expected_service_pid": 9881,
            "expected_start_ticks": "111337",
            "expected_service_uid": 997,
            "expected_service_gid": 997,
        }

    def line(self, *, value=None, raw=None):
        if raw is not None:
            return raw
        value = self.report if value is None else value
        return U.PREFIX + json.dumps(value, sort_keys=True,
                                      separators=(",", ":")).encode() + b"\n"

    def check(self, *, value=None, raw=None, **pins):
        return U.inspect(
            report_line=self.line(value=value, raw=raw),
            **{**self.pins, **pins})

    def refuse(self, reason, *, value=None, raw=None, **pins):
        with self.assertRaises(U.Refused) as ex:
            self.check(value=value, raw=raw, **pins)
        self.assertEqual(str(ex.exception), reason)

    def test_01_merged_c4c_embedded_python_exact_emitted_field_contract(self):
        text = C4C.read_text()
        marker = "import grp, hashlib, json, os, pwd, re, stat, subprocess, sys\n"
        self.assertEqual(text.count(marker), 1)
        code = marker + text.split(marker, 1)[1].split(
            "\nC4B_RUNNING_HOST_PROBE", 1)[0]
        tree = ast.parse(code)
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "observe"]
        self.assertEqual(len(functions), 1)
        receipts = [node.value for node in ast.walk(functions[0])
                    if isinstance(node, ast.Return)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "dict"]
        self.assertEqual(len(receipts), 1)
        actual = receipts[0]
        keys = {kw.arg for kw in actual.keywords}
        self.assertEqual(keys, U.FIELDS)
        schema = next(kw.value for kw in actual.keywords
                      if kw.arg == "schema")
        self.assertIsInstance(schema, ast.Constant)
        self.assertEqual(schema.value, U.SCHEMA)
        self.assertIn('print("C4B_OBSERVED // " + json.dumps(observe()', text)
        self.assertLess(text.index('C3B_OS_ORIGIN_VERIFICATION_BEGIN'),
                        text.index('SIGNED_C3D_RUNNING_HOST_MEASUREMENT_BEGIN'))
        self.assertLess(text.index('SIGNED_C3D_RUNNING_HOST_MEASUREMENT_BEGIN'),
                        text.index('stage EXPLICIT_SIGNED_SERVICE_STOP_BEGIN'))
        for guard in (
            'signed_rpm_sha256=package_sha',
            'hash_root_file(name, mode, 128 * 1024)',
            'GetConnectionUnixProcessID', 'GetConnectionUnixUser',
            'rpmkeys', 'POST_APOLLO_C4B_TEST_GUEST=1',
        ):
            self.assertIn(guard, text)
        self.assertEqual(set(self.report), U.FIELDS)

    def test_02_exact_schema_and_independent_diagnostic_pins(self):
        result = self.check()
        self.assertTrue(result["c4cSchemaCompatible"])
        self.assertTrue(result["reportMatchesSuppliedIndependentPins"])
        self.assertEqual(result["observedServicePid"], 9881)
        self.assertTrue(result["reportSourceIsGuestSelfObservation"])
        self.assertFalse(result["installedGuestMeasured"])
        for k in U.DENY_FLAGS:
            self.assertIs(result[k], False)

    def test_03_wrong_signed_rpm_pin_refused(self):
        self.refuse("C4C_SIGNED_ARTIFACT_OR_RUNNING_BYTES_PIN_MISMATCH",
                    independent_signed_rpm_sha256="d"*64)

    def test_04_wrong_signed_python_payload_refused(self):
        self.refuse("C4C_SIGNED_ARTIFACT_OR_RUNNING_BYTES_PIN_MISMATCH",
                    independent_signed_script_sha256="d"*64)

    def test_05_wrong_interpreter_reference_refused(self):
        self.refuse("C4C_SIGNED_ARTIFACT_OR_RUNNING_BYTES_PIN_MISMATCH",
                    independent_interpreter_sha256="d"*64)

    def test_06_signed_rpm_script_mismatch_in_report_refused(self):
        x = {**self.report, "running_script_sha256": "d"*64}
        self.refuse("C4C_SIGNED_ARTIFACT_OR_RUNNING_BYTES_PIN_MISMATCH", value=x)

    def test_07_wrong_systemd_dbus_process_refused(self):
        x = {**self.report, "dbus_owner_pid": 9882}
        self.refuse("C4C_SYSTEMD_DBUS_PROCESS_PIN_MISMATCH", value=x)
        self.refuse("C4C_SYSTEMD_DBUS_PROCESS_PIN_MISMATCH",
                    expected_service_pid=9882)

    def test_08_wrong_start_and_account_refused(self):
        for k,v in (("expected_start_ticks","111338"),
                    ("expected_service_uid",998),
                    ("expected_service_gid",998)):
            with self.subTest(k=k):
                self.refuse("C4C_SYSTEMD_DBUS_PROCESS_PIN_MISMATCH",
                            **{k:v})

    def test_09_signed_claim_of_approval_or_attestation_refused(self):
        for k in U.DENY_FLAGS:
            with self.subTest(k=k):
                self.refuse("C4C_CLAIMED_UNAUTHORIZED_AUTHORITY",
                            value={**self.report, k:True})

    def test_10_invalid_selinux_or_systemd_unit_refused(self):
        for k,v in (("selinux_enforcing",False),
                    ("systemd_unit","not-protected.service"),
                    ("schema","postapollo.connections.fake")):
            with self.subTest(k=k):
                self.refuse("C4C_ROLE_OR_SELINUX_REFUSED",
                            value={**self.report,k:v})

    def test_11_duplicate_or_extra_fields_refused(self):
        x = {**self.report,"approvalToken":"unauthorized"}
        self.refuse("C4C_REPORT_SHAPE_REFUSED",value=x)
        raw = self.line().rstrip(b"\n")
        duplicate = raw[:-1] + b',"service_pid":9881}\n'
        self.refuse("DUPLICATE_C4C_FIELD",raw=duplicate)

    def test_12_missing_or_unbounded_report_refused(self):
        x=deepcopy(self.report)
        del x["interpreter_sha256"]
        self.refuse("C4C_REPORT_SHAPE_REFUSED",value=x)
        self.refuse("C4C_LINE_SIZE_REFUSED",raw=b"A"*4097)

    def test_13_header_wrong_or_multiple_lines_refused(self):
        self.refuse("C4C_LINE_PREFIX_OR_DELIMITER_REFUSED",
                    raw=b"FAKE_OBSERVED // {}\n")
        self.refuse("C4C_LINE_PREFIX_OR_DELIMITER_REFUSED",
                    raw=self.line()+self.line())

    def test_14_integer_bool_and_noncanonical_process_fields_refused(self):
        self.refuse("C4C_PROCESS_FIELD_INVALID",
                    value={**self.report,"service_pid":True})
        self.refuse("C4C_START_FIELD_INVALID",
                    value={**self.report,"process_start_ticks":"000111337"})
        self.refuse("INDEPENDENT_PROCESS_PIN_INVALID",
                    expected_service_pid=False)
        self.refuse("INDEPENDENT_HASH_PIN_INVALID",
                    independent_signed_rpm_sha256="A"*64)

    def test_15_self_observation_is_not_c3eq_verified_signed_envelope(self):
        # The actual C4c JSON is not C3e-Q's challenge-bound message.
        spec = importlib.util.spec_from_file_location("c3eu_q", Q)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with self.assertRaises(mod.Refused) as ctx:
            mod.exact_json(self.line()[len(U.PREFIX):])
        self.assertEqual(str(ctx.exception),"EVIDENCE_SHAPE_REFUSED")
        self.assertNotIn("challenge_sha256", self.report)

    def test_16_cli_accepts_only_bounded_one_line_and_refuses_wrong_pin(self):
        args=[sys.executable,"-B",str(SOURCE),
              "--rpm-sha256",self.rpm,
              "--script-sha256",self.script,
              "--interpreter-sha256",self.python,
              "--service-pid","9881","--start-ticks","111337",
              "--service-uid","997","--service-gid","997"]
        positive=subprocess.run(args,input=self.line(),capture_output=True,timeout=8)
        self.assertEqual(positive.returncode,0,positive.stderr)
        payload=json.loads(positive.stdout)
        self.assertTrue(payload["c4cSchemaCompatible"])
        self.assertFalse(payload["hostAuthenticated"])
        bad=args[:]
        bad[bad.index(self.rpm)]="d"*64
        negative=subprocess.run(bad,input=self.line(),capture_output=True,timeout=8)
        self.assertEqual(negative.returncode,3,negative.stderr)
        self.assertEqual(json.loads(negative.stdout)["refused"],
                         "C4C_SIGNED_ARTIFACT_OR_RUNNING_BYTES_PIN_MISMATCH")

    def test_17_no_admission_or_production_broker_calls(self):
        result=self.check()
        self.assertNotIn("allow",result)
        self.assertNotIn("authenticated",result)
        self.assertIs(result["signedGuestOriginAuthenticated"],False)
        broker=ROOT/"services/connections/ConnectionsBroker.qml"
        status=ROOT/"services/connections/ConnectionsRequestStatus.qml"
        self.assertIn("readonly property bool credentialActionsEnabled: false",broker.read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",status.read_text())
        src=SOURCE.read_text()
        for forbidden in ("subprocess.run", "subprocess.Popen", "socket.",
                          "rpm --install", "GenUI.", "signedGuestOriginAuthenticated\": True"):
            self.assertNotIn(forbidden,src)

    def test_18_source_contract_does_not_claim_real_output_artifact(self):
        # Does NOT assert that real #42638232336 exported its UART JSON.
        self.assertEqual(self.report["schema"], U.SCHEMA)
        self.assertIs(self.check()["installedGuestMeasured"],False)
        self.assertFalse(self.check()["evidenceCryptographicallyAttested"])


if __name__=="__main__":
    unittest.main(verbosity=2)
