#!/usr/bin/env python3
"""M13g: deterministic read-only bus probing, no secret-service calls."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

PATH = Path(__file__).parent / "fixtures" / "TaskSecretServiceProbeM13g.py"
spec = importlib.util.spec_from_file_location("m13g_probe", PATH)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def invoke(self, answer="(true,)", code=0, tools=None, error=None):
        calls = []

        def which(cmd):
            return None if cmd in (tools or set()) else "/dummy/" + cmd

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            if error:
                raise error
            return subprocess.CompletedProcess(argv, code, stdout=answer, stderr="secret-not-printed")

        result = probe.probe(which=which, run=run)
        return result, calls

    def test_acquired_is_read_only_not_unlocked(self):
        result, calls = self.invoke()
        self.assertEqual(result["status"], "SERVICE_ACQUIRED")
        self.assertTrue(result["owner_present"])
        self.assertFalse(result["authenticated_unlock_verified"])
        self.assertFalse(result["key_roundtrip_verified"])
        self.assertFalse(result["production_key_provider_selected"])
        self.assertEqual(len(calls), 1)
        args, kwargs = calls[0]
        self.assertEqual(args, probe.QUERY)
        self.assertEqual(args[4], "/org/freedesktop/DBus")
        self.assertEqual(args[-2], "org.freedesktop.DBus.NameHasOwner")
        self.assertEqual(args[-1], "org.freedesktop.secrets")
        self.assertLessEqual(kwargs["timeout"], 4)
        self.assertTrue(kwargs["capture_output"])

    def test_service_not_running_does_not_trigger_activation(self):
        result, calls = self.invoke("(false,)")
        self.assertEqual(result["status"], "SERVICE_NOT_RUNNING")
        self.assertFalse(result["owner_present"])
        self.assertEqual(calls[0][0], probe.QUERY)

    def test_unknown_response_does_not_guess(self):
        result, _ = self.invoke("('maybe',)")
        self.assertEqual(result["status"], "UNEXPECTED_DBUS_RESPONSE")

    def test_missing_gdbus_does_not_run_a_command(self):
        result, calls = self.invoke(tools={"gdbus"})
        self.assertEqual(result["status"], "DBUS_PROBE_TOOL_MISSING")
        self.assertEqual(calls, [])

    def test_unavailable_session_bus_never_echoes_errors(self):
        result, _ = self.invoke(code=1)
        self.assertEqual(result["status"], "SESSION_BUS_UNAVAILABLE")
        self.assertNotIn("secret-not-printed", str(result))
        result, _ = self.invoke(error=subprocess.TimeoutExpired("gdbus", 4))
        self.assertEqual(result["status"], "SESSION_BUS_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
