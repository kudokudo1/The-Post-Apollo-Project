"""Offline mocks for opt-in KDE Connect D-Bus metadata probe.

No busctl subprocess, KDE Connect daemon, contacts, phone, or network.
"""
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import KdeConnectDbusProbe as probe  # noqa: E402

DEVICE = "abcdef1234567890"


def response(value: str):
    return SimpleNamespace(returncode=0, stdout=value)


class FakeBus:
    def __init__(self, *, active=True, devices=None, properties=None, failure=None):
        self.calls = []
        self.active = active
        self.devices = devices if devices is not None else [DEVICE]
        self.properties = dict(properties or {})
        self.failure = failure

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if self.failure is not None:
            return self.failure(argv, kwargs)
        args = argv[len(probe.BASE) + 2:]
        if args[:4] == [probe.DBUS_SERVICE, probe.DBUS_OBJECT,
                        probe.DBUS_SERVICE, "NameHasOwner"]:
            return response("b true" if self.active else "b false")
        if args[:4] == [probe.BUS_NAME, probe.BUS_OBJECT,
                        probe.BUS_INTERFACE, "devices"]:
            return response("as " + str(len(self.devices))
                            + "".join(' "' + device + '"' for device in self.devices))
        if len(args) == 7 and args[2:6] == [
            "org.freedesktop.DBus.Properties", "Get", "ss", probe.DEVICE_INTERFACE
        ]:
            prop = args[-1]
            defaults = {
                "isPaired": "v b true",
                "isReachable": "v b true",
                "type": 'v s "phone"',
                "supportedPlugins": 'v as 3 "kdeconnect_sms" "kdeconnect_contacts" "kdeconnect_telephony"',
                "activeProviderNames": 'v as 1 "LanLinkProvider"',
            }
            return response(self.properties.get(prop, defaults[prop]))
        if len(args) == 4 and args[2:] == [
            probe.DEVICE_INTERFACE, "loadedPlugins"
        ]:
            return response(self.properties.get("loadedPlugins",
                           'as 3 "kdeconnect_sms" "kdeconnect_contacts" "kdeconnect_telephony"'))
        raise AssertionError("Unexpected D-Bus invocation: " + repr(args))


def run(bus):
    return probe.probe(find_executable=lambda exe: "/usr/bin/busctl",
                       runner=bus)


class DbusProbeTests(unittest.TestCase):
    def test_service_not_running_cannot_autostart_or_query_devices(self):
        bus = FakeBus(active=False)
        out = run(bus)
        self.assertEqual(out["state"], "SERVICE_NOT_RUNNING")
        self.assertEqual(len(bus.calls), 1)
        self.assertFalse(out["routeEligible"])

    def test_no_busctl_never_calls_process(self):
        bus = FakeBus()
        out = probe.probe(find_executable=lambda name: None, runner=bus)
        self.assertEqual(out["state"], "BUSCTL_NOT_INSTALLED")
        self.assertEqual(bus.calls, [])

    def test_empty_device_list(self):
        bus = FakeBus(devices=[])
        out = run(bus)
        self.assertEqual(out["state"], "NO_PAIRED_REACHABLE_DEVICES")
        self.assertEqual(out["reportedPairedReachableCount"], 0)
        self.assertEqual(len(bus.calls), 2)

    def test_one_reachable_phone_yields_only_local_plugin_counts(self):
        bus = FakeBus()
        out = run(bus)
        self.assertEqual(out["state"], "METADATA_REPORTED")
        self.assertEqual(out["reportedPairedReachableCount"], 1)
        self.assertEqual(out["localSmsPluginCount"], 1)
        self.assertEqual(out["localContactsPluginCount"], 1)
        self.assertEqual(out["localTelephonyPluginCount"], 1)
        self.assertEqual(out["transport"], "UNVERIFIED")
        self.assertEqual(out["devicePlatform"], "UNVERIFIED")
        self.assertEqual(out["smsPermission"], "NOT_CHECKED")
        self.assertEqual(out["callAudio"], "NOT_CHECKED")
        self.assertFalse(out["routeEligible"])
        self.assertNotIn(DEVICE, str(out))

    def test_two_devices_aggregate_without_device_ids(self):
        bus = FakeBus(devices=[DEVICE, "bbbbbbbbbbbbbbbb"])
        out = run(bus)
        self.assertEqual(out["state"], "METADATA_REPORTED")
        self.assertEqual(out["reportedPairedReachableCount"], 2)
        self.assertEqual(out["localSmsPluginCount"], 2)
        self.assertNotIn("bbbbbbbbbbbbbbbb", str(out))

    def test_all_invocations_explicitly_no_autostart_and_no_shell(self):
        bus = FakeBus()
        run(bus)
        self.assertEqual(len(bus.calls), 8)
        for argv, kw in bus.calls:
            self.assertEqual(argv[0], "/usr/bin/busctl")
            self.assertEqual(argv[1:1 + len(probe.BASE)], list(probe.BASE))
            self.assertEqual(argv[1 + len(probe.BASE)], "call")
            self.assertFalse(kw.get("shell", False))
            self.assertIs(kw["check"], False)
            self.assertIs(kw["capture_output"], True)
            self.assertIs(kw["text"], True)
            self.assertEqual(kw["timeout"], 3)
            self.assertNotIn("sendSms", argv)
            self.assertNotIn("requestAllConversations", argv)
            self.assertNotIn("setPluginEnabled", argv)
            self.assertNotIn("synchronizeRemoteWithLocal", argv)
            self.assertNotIn("requestPairing", argv)

    def test_device_path_is_lowercase_devices_as_in_source(self):
        bus = FakeBus()
        run(bus)
        paths = [a[0][2 + len(probe.BASE)] for a in bus.calls[2:]]
        self.assertTrue(all(p == f"/modules/kdeconnect/devices/{DEVICE}"
                            for p in paths))

    def test_invalid_device_id_is_not_interpolated(self):
        for device in ["../bad", "short", "bad-name-with-dash", "b" * 81]:
            with self.subTest(device=device):
                bus = FakeBus(devices=[device])
                out = run(bus)
                self.assertEqual(out["state"], "METADATA_UNAVAILABLE")
                self.assertEqual(len(bus.calls), 2)
                self.assertNotIn(device, str(out))

    def test_reject_more_than_four_devices_and_duplicates(self):
        for values in [[DEVICE] * 2, ["a" * 8] * 5]:
            with self.subTest(values=values):
                bus = FakeBus(devices=values)
                self.assertEqual(run(bus)["state"], "METADATA_UNAVAILABLE")

    def test_bad_dbus_array_format_fails_closed(self):
        samples = ["as five", "as 2 one", "as 1 one two", "v as 1 bad"]
        for sample in samples:
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    probe._strings(sample)

    def test_variants_have_exact_expected_signature(self):
        self.assertEqual(probe._strings('v as 2 "one" "two"', variant=True),
                         ["one", "two"])
        self.assertEqual(probe._strings('as 0'), [])
        self.assertEqual(probe._string('v s "phone"', variant=True), "phone")
        self.assertTrue(probe._boolean("v b true", variant=True))
        self.assertFalse(probe._boolean("b false"))
        for invalid in ["v b 1", "b TRUE", "s true", "v as 2 one"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    probe._boolean(invalid) if "true" in invalid else probe._strings(invalid)

    def test_reject_malformed_boolean_from_dbus(self):
        for value in ["b 1", "v b TRUE", "v s true", "v b", "v b true false"]:
            bus = FakeBus(properties={"isPaired": value})
            self.assertEqual(run(bus)["state"], "METADATA_UNAVAILABLE")

    def test_no_exported_property_fails_safely_without_claims(self):
        def fail(argv, kw):
            if "activeProviderNames" in argv:
                return SimpleNamespace(returncode=1, stdout="secret", stderr="private")
            return FakeBus().__call__(argv, **kw)
        out = run(FakeBus(failure=fail))
        self.assertEqual(out["state"], "METADATA_UNAVAILABLE")
        self.assertNotIn("private", str(out))

    def test_timeout_never_leaks_exception_body(self):
        def fail(argv, kw):
            raise subprocess.TimeoutExpired(argv, 3, output="device_private")
        out = run(FakeBus(failure=fail))
        self.assertEqual(out["state"], "BUS_TIMEOUT")
        self.assertNotIn("device_private", str(out))

    def test_os_error_never_leaks_exception(self):
        def fail(argv, kw):
            raise OSError("private dbus connection")
        out = run(FakeBus(failure=fail))
        self.assertEqual(out["state"], "METADATA_UNAVAILABLE")
        self.assertNotIn("private", str(out))

    def test_unpaired_race_avoids_plugin_readiness(self):
        out = run(FakeBus(properties={"isPaired": "v b false"}))
        self.assertEqual(out["state"], "METADATA_UNAVAILABLE")
        self.assertEqual(out["localSmsPluginCount"], 0)

    def test_inconsistent_loaded_plugin_fails(self):
        out = run(FakeBus(properties={"supportedPlugins": "v as 0"}))
        self.assertEqual(out["state"], "METADATA_UNAVAILABLE")

    def test_active_link_cannot_certify_wifi_or_android(self):
        out = run(FakeBus(properties={
            "activeProviderNames": 'v as 1 "BluetoothLinkProvider"'
        }))
        self.assertEqual(out["transport"], "UNVERIFIED")
        self.assertEqual(out["devicePlatform"], "UNVERIFIED")
        self.assertFalse(out["routeEligible"])

    def test_explicit_flag_required_no_command_execution(self):
        # main() omits the call to probe() when not given exactly --probe.
        self.assertEqual(probe.main([]), 2)
        self.assertEqual(probe.main(["--help"]), 2)
        self.assertEqual(probe.main(["--probe", "--pair"]), 2)

    def test_replies_never_include_user_device_identifiers_or_messages(self):
        out = run(FakeBus())
        self.assertEqual(set(out), {
            "schema", "execution", "provider", "state",
            "reportedPairedReachableCount", "localSmsPluginCount",
            "localContactsPluginCount", "localTelephonyPluginCount",
            "devicePlatform", "transport", "smsPermission",
            "contactsPermission", "callAudio", "routeEligible",
        })
        for private in [DEVICE, "LanLinkProvider", "kdeconnect_sms", "phone-number"]:
            self.assertNotIn(private, str(out))

    def test_dbus_error_and_oversized_data_fail_closed(self):
        def error(argv, kw):
            return SimpleNamespace(returncode=7, stdout='b true', stderr="sensitive")
        self.assertEqual(run(FakeBus(failure=error))["state"], "METADATA_UNAVAILABLE")
        self.assertEqual(probe.probe(
            find_executable=lambda exe: "/bin/busctl",
            runner=lambda *a, **kw: response("b " + "a" * 8200)
        )["state"], "METADATA_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
