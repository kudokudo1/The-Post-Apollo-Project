"""P1 offline KDE Connect presence discovery; no phone, D-Bus or CLI needed."""
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "phone"))
import KdeConnectPresence as presence  # noqa: E402


class PresenceTests(unittest.TestCase):
    def test_empty_list_does_not_claim_capability(self):
        out = presence.summarize("", 0)
        self.assertEqual(out["state"], "NO_PAIRED_REACHABLE_DEVICES")
        self.assertFalse(out["routeEligible"])
        self.assertEqual(out["sms"], "NOT_CHECKED")

    def test_two_devices_report_count_without_device_identifiers(self):
        raw = "phoneA00000001\nphoneB00000002\n"
        out = presence.summarize(raw, 0)
        self.assertEqual(out["pairedReachableCount"], 2)
        self.assertEqual(out["state"], "PAIRED_REACHABLE_REPORTED")
        self.assertNotIn("phoneA", str(out))
        self.assertNotIn("phoneB", str(out))
        self.assertEqual(out["transport"], "UNVERIFIED")
        self.assertEqual(out["devicePlatform"], "UNVERIFIED")
        self.assertFalse(out["routeEligible"])

    def test_no_implicit_network_or_bluetooth_assumption(self):
        out = presence.summarize("androidFakeA000000\n", 0)
        self.assertEqual(out["transport"], "UNVERIFIED")
        self.assertFalse(out["routeEligible"])
        for key in ("sms", "contacts", "notifications", "callAudio"):
            self.assertEqual(out[key], "NOT_CHECKED")

    def test_invalid_outputs_rejected_without_echoing(self):
        invalid = [
            "a\n", "phoneA00000001\nphoneA00000001\n",
            "phoneA00000001\n--pair\n",
            "phoneA00000001\nother id\n",
            ("phoneA00000001\n" * 33),
            "a" * 8193,
            "phoneA00000001\n\n",
        ]
        for raw in invalid:
            with self.subTest(raw=raw[:30]):
                out = presence.summarize(raw, 0)
                self.assertEqual(out["state"], "INVALID_RESPONSE")
                self.assertEqual(out["pairedReachableCount"], 0)
                self.assertNotIn("raw", out)

    def test_nonzero_status_fails_closed(self):
        out = presence.summarize("phoneA00000001\n", 1)
        self.assertEqual(out["state"], "CLIENT_ERROR")
        self.assertFalse(out["routeEligible"])

    def test_invalid_return_code_fails_closed(self):
        for value in (True, "0", None):
            self.assertEqual(presence.summarize("", value)["state"], "CLIENT_ERROR")

    def test_invalid_data_type_fails_closed(self):
        self.assertEqual(presence.summarize(b"phoneA00000001\n", 0)["state"], "INVALID_RESPONSE")

    def test_missing_executable_never_spawns(self):
        called = []
        def never_runner(*args, **kwargs):
            called.append(args)
            raise AssertionError("must never run")
        out = presence.probe(find_executable=lambda name: None, runner=never_runner)
        self.assertEqual(out["state"], "CLIENT_NOT_INSTALLED")
        self.assertFalse(called)

    def test_only_fixed_discovery_command_is_executed(self):
        called = []
        def fake_runner(argv, **kwargs):
            called.append((argv, kwargs))
            return SimpleNamespace(returncode=0, stdout="phoneA00000001\n")
        out = presence.probe(
            find_executable=lambda name: "/usr/bin/kdeconnect-cli",
            runner=fake_runner)
        self.assertEqual(out["state"], "PAIRED_REACHABLE_REPORTED")
        self.assertEqual(len(called), 1)
        argv, opts = called[0]
        self.assertEqual(argv, [
            "/usr/bin/kdeconnect-cli", "--list-available", "--id-only"])
        self.assertIs(opts["shell"] if "shell" in opts else False, False)
        self.assertFalse(opts["check"])
        self.assertTrue(opts["capture_output"])
        self.assertTrue(opts["text"])
        self.assertEqual(opts["timeout"], 5)
        self.assertFalse(set(argv) & {
            "--refresh", "--pair", "--unpair", "--ping", "--send-sms",
            "--list-notifications", "--share", "--ring", "--mount",
            "--execute-command", "--enable-backend", "--disable-backend",
        })

    def test_timeout_fails_closed_without_private_output(self):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("kdeconnect-cli", 5, output="private-id")
        out = presence.probe(find_executable=lambda name: "/bin/kdeconnect-cli", runner=timeout)
        self.assertEqual(out["state"], "CLIENT_TIMEOUT")
        self.assertNotIn("private-id", str(out))

    def test_os_error_fails_closed(self):
        def failing(*args, **kwargs):
            raise OSError("private details")
        out = presence.probe(find_executable=lambda name: "/bin/kdeconnect-cli", runner=failing)
        self.assertEqual(out["state"], "CLIENT_ERROR")
        self.assertNotIn("private details", str(out))

    def test_no_secret_or_contact_fields_in_summary(self):
        out = presence.summarize("phoneA00000001\n", 0)
        self.assertEqual(set(out), {
            "schema", "provider", "execution", "state", "pairedReachableCount",
            "devicePlatform", "transport", "sms", "contacts", "notifications",
            "callAudio", "routeEligible",
        })
        self.assertNotIn("messages", str(out))
        self.assertNotIn("phoneA00000001", str(out))

    def test_nonzero_exit_does_not_trust_stale_stdout(self):
        def failing(*args, **kwargs):
            return SimpleNamespace(returncode=2, stdout="phoneA00000001\n", stderr="secret")
        out = presence.probe(find_executable=lambda name: "/bin/kdeconnect-cli", runner=failing)
        self.assertEqual(out["pairedReachableCount"], 0)
        self.assertEqual(out["state"], "CLIENT_ERROR")


if __name__ == "__main__":
    unittest.main()
