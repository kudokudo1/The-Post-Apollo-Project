"""The PHONE readiness probe must never activate or read phone content."""
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[2] / "services" / "phone" / "BlueFerryReadiness.py"
SPEC = importlib.util.spec_from_file_location("blueferry_readiness", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ProbeTests(unittest.TestCase):
    @mock.patch.object(module.Path, "is_file", return_value=True)
    @mock.patch.object(module.subprocess, "run")
    def test_reports_only_local_readiness(self, run, is_file):
        responses = {
            ("rpm", "-q", "blueferry-backend"): (0, "blueferry-backend-0.9.1\n"),
            ("bluetoothctl", "show"): (0, "Controller private\n Powered: yes\n"),
            ("systemctl", "is-active", "bluetooth.service"): (0, "active\n"),
            ("systemctl", "--user", "is-active", "blueferry.service"): (3, "inactive\n"),
        }

        def fake(argv, **kwargs):
            self.assertEqual(kwargs["timeout"], 3)
            self.assertTrue(kwargs["capture_output"])
            self.assertTrue(kwargs["text"])
            self.assertFalse(kwargs["check"])
            return mock.Mock(
                returncode=responses[tuple(argv)][0],
                stdout=responses[tuple(argv)][1],
            )

        run.side_effect = fake
        observed = module.readiness()
        self.assertEqual(observed["schema"], module.SCHEMA)
        self.assertEqual(observed["execution"], "READ_ONLY")
        self.assertTrue(observed["blueferryInstalled"])
        self.assertEqual(observed["bluetoothService"], "active")
        self.assertTrue(observed["controllerPowered"])
        self.assertTrue(observed["configurationPresent"])
        self.assertEqual(observed["backendService"], "inactive")
        self.assertEqual(observed["phoneLink"], "UNVERIFIED")
        self.assertFalse(observed["contentAuthorized"])
        self.assertEqual(len(run.call_args_list), 4)
        self.assertNotIn("private", str(observed))
        self.assertNotIn("blueferry pair-setup", str(observed))

    @mock.patch.object(module.Path, "is_file", return_value=False)
    @mock.patch.object(module.subprocess, "run", side_effect=OSError("unavailable"))
    def test_missing_tools_fail_closed(self, run, is_file):
        observed = module.readiness()
        self.assertFalse(observed["blueferryInstalled"])
        self.assertIsNone(observed["controllerPowered"])
        self.assertEqual(observed["bluetoothService"], "unknown")
        self.assertEqual(observed["backendService"], "unknown")
        self.assertFalse(observed["configurationPresent"])
        self.assertFalse(observed["contentAuthorized"])
        self.assertEqual(observed["phoneLink"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
