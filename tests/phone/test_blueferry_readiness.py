"""The PHONE readiness probe must never activate or read phone content."""
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
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
        self.assertEqual(observed["backendObservation"], "NOT_RUNNING")
        self.assertIsNone(observed["mapSessionActive"])
        self.assertIsNone(observed["pbapSessionActive"])
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
        self.assertEqual(observed["backendObservation"], "NOT_RUNNING")
        self.assertEqual(observed["phoneLink"], "UNVERIFIED")


    def test_daemon_inactive_never_opens_session_bus(self):
        api = mock.Mock()
        result = module._backend_profile_observation(
            "inactive", dbus_api=api, bus_address="unix:path=/test"
        )
        self.assertEqual(result["backendObservation"], "NOT_RUNNING")
        self.assertIsNone(result["mapSessionActive"])
        api.SessionBus.assert_not_called()

    def test_no_session_bus_address_never_imports_dbus(self):
        api = mock.Mock()
        result = module._backend_profile_observation(
            "active", dbus_api=api, bus_address=""
        )
        self.assertEqual(result["backendObservation"], "UNAVAILABLE")
        api.SessionBus.assert_not_called()

    @staticmethod
    def backend_api(status, *, owner=":1.111", present=True):
        bus = mock.Mock()
        bus.name_has_owner.return_value = present
        bus.get_name_owner.return_value = owner
        proxy = object()
        bus.get_object.return_value = proxy
        iface = mock.Mock()
        iface.GetStatus.return_value = status
        api = SimpleNamespace(
            SessionBus=mock.Mock(return_value=bus),
            Interface=mock.Mock(return_value=iface),
        )
        return api, bus, proxy, iface

    def test_active_daemon_whitelists_only_profile_booleans(self):
        api, bus, proxy, iface = self.backend_api(
            '{"api_version":2,"daemon":true,"map":true,"pbap":false,'
            '"phone":"SECRET","contacts":["PRIVATE"],"message":"PRIVATE"}'
        )
        result = module._backend_profile_observation(
            "active", dbus_api=api, bus_address="unix:path=/test"
        )
        self.assertEqual(result, {
            "backendObservation": "REPORTED",
            "mapSessionActive": True,
            "pbapSessionActive": False,
        })
        api.SessionBus.assert_called_once_with(private=True)
        bus.name_has_owner.assert_called_once_with("io.weirdware.BlueFerry")
        bus.get_object.assert_called_once_with(
            ":1.111", "/io/weirdware/BlueFerry", introspect=False
        )
        iface.GetStatus.assert_called_once_with(timeout=3)
        self.assertNotIn("SECRET", str(result))
        self.assertNotIn("PRIVATE", str(result))

    def test_absent_backend_never_gets_an_activatable_proxy(self):
        api, bus, _, iface = self.backend_api("{}", present=False)
        result = module._backend_profile_observation(
            "active", dbus_api=api, bus_address="unix:path=/test"
        )
        self.assertEqual(result["backendObservation"], "NO_OWNER")
        bus.get_object.assert_not_called()
        iface.GetStatus.assert_not_called()

    def test_invalid_or_raced_unique_owner_is_not_queried(self):
        for owner in ("io.weirdware.BlueFerry", ":broken", "", ":1.ABC"):
            with self.subTest(owner=owner):
                api, bus, _, _ = self.backend_api("{}", owner=owner)
                result = module._backend_profile_observation(
                    "active", dbus_api=api, bus_address="unix:path=/test"
                )
                self.assertEqual(result["backendObservation"], "UNAVAILABLE")
                bus.get_object.assert_not_called()

    def test_incompatible_or_malformed_status_fails_closed(self):
        payloads = [
            "{}",
            '{"api_version":1,"daemon":true,"map":true,"pbap":true}',
            '{"api_version":2,"daemon":true,"map":"yes","pbap":true}',
            '{"api_version":2,"daemon":false,"map":true,"pbap":true}',
            "x" * 32769,
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:70]):
                api, _, _, _ = self.backend_api(payload)
                result = module._backend_profile_observation(
                    "active", dbus_api=api, bus_address="unix:path=/test"
                )
                self.assertEqual(result["backendObservation"], "UNAVAILABLE")
                self.assertIsNone(result["mapSessionActive"])
                self.assertIsNone(result["pbapSessionActive"])

    def test_dbus_error_is_redacted(self):
        api, _, _, iface = self.backend_api("{}")
        iface.GetStatus.side_effect = RuntimeError("PRIVATE-PHONE-ID")
        result = module._backend_profile_observation(
            "active", dbus_api=api, bus_address="unix:path=/test"
        )
        self.assertEqual(result["backendObservation"], "UNAVAILABLE")
        self.assertNotIn("PRIVATE", str(result))


if __name__ == "__main__":
    unittest.main()
