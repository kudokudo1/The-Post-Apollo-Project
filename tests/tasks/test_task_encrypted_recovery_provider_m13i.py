#!/usr/bin/env python3
"""M13i read-only D-Bus provider-status adapter contract tests."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

HOST = Path(__file__).resolve().parents[2] / "services/hub/TaskRecoveryProviderHostM13i.py"
spec = importlib.util.spec_from_file_location("m13i_provider", HOST)
assert spec and spec.loader
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class ProviderHostTests(unittest.TestCase):
    def run_probe(self, observed="(true,)", returncode=0,
                  tool=True, failure=None):
        calls = []

        def which(name):
            return "/synthetic/gdbus" if tool and name == "gdbus" else None

        def run(argv, **options):
            calls.append((argv, options))
            if failure:
                raise failure
            return subprocess.CompletedProcess(
                argv, returncode, observed, "SECRET_DIAGNOSTIC_DO_NOT_EMIT"
            )
        return host.probe(which=which, run=run), calls

    def check_denied(self, status):
        self.assertEqual(status["protocol"], 1)
        self.assertEqual(status["kind"], "M13I_PROVIDER_STATUS")
        for field in (
            "keyringUnlocked", "recoveryEnabled", "writeAuthorized",
            "persistAuthorized", "decryptAuthorized", "productionActivation"
        ):
            self.assertIs(status[field], False, field)

    def test_present_only_proves_service_name_owner(self):
        result, calls = self.run_probe()
        self.assertEqual(result["status"], "SERVICE_ACQUIRED")
        self.assertTrue(result["providerPresent"])
        self.check_denied(result)
        self.assertEqual(len(calls), 1)
        command, kwargs = calls[0]
        self.assertEqual(command, host.QUERY)
        self.assertEqual(command[-2], "org.freedesktop.DBus.NameHasOwner")
        self.assertEqual(command[-1], "org.freedesktop.secrets")
        self.assertLessEqual(kwargs["timeout"], 4)
        self.assertTrue(kwargs["capture_output"])

    def test_absent_cannot_start_the_service(self):
        result, calls = self.run_probe("(false,)")
        self.assertEqual(result["status"], "SERVICE_NOT_RUNNING")
        self.assertFalse(result["providerPresent"])
        self.check_denied(result)
        self.assertEqual(calls[0][0], host.QUERY)

    def test_tool_missing_never_runs_subprocess(self):
        result, calls = self.run_probe(tool=False)
        self.assertEqual(result["status"], "PROBE_TOOL_MISSING")
        self.assertFalse(result["providerPresent"])
        self.check_denied(result)
        self.assertEqual(calls, [])

    def test_bus_failure_and_timeout_fail_closed(self):
        for failure, code in [(None, 1),
                              (subprocess.TimeoutExpired("gdbus", 4), 0),
                              (OSError("private reason"), 0)]:
            result, _ = self.run_probe(returncode=code, failure=failure)
            self.assertEqual(result["status"], "SESSION_BUS_UNAVAILABLE")
            self.assertFalse(result["providerPresent"])
            self.assertNotIn("private reason", str(result))
            self.assertNotIn("SECRET_DIAGNOSTIC", str(result))
            self.check_denied(result)

    def test_forged_or_unexpected_output_cannot_claim_presence(self):
        for raw in (
            "(secret,)", "(True,)", "true", "('true',)",
            "(true,)garbage", "M13I_PRIVATE_CONTENT", "(true, false)"
        ):
            result, _ = self.run_probe(observed=raw)
            self.assertEqual(result["status"], "UNEXPECTED_RESPONSE")
            self.assertFalse(result["providerPresent"])
            self.check_denied(result)


if __name__ == "__main__":
    unittest.main()
