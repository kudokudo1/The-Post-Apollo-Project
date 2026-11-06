"""Bounded local PHONE nicknames cannot grant access or modify pairing."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
nickname = importlib.import_module("PhoneNickname")
PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"


def observation(profile=PROFILE, state="BLUETOOTH_CONNECTED", **changes):
    report = {
        "schema": "post-apollo.phone.device-observation.v0",
        "execution": "READ_ONLY_DEVICE_OBSERVATION",
        "state": state, "profileId": profile,
        "bluetoothLink": ("CONNECTED" if state == "BLUETOOTH_CONNECTED"
                          else "PAIRED_OFFLINE" if state == "PAIRED_OFFLINE"
                          else "UNVERIFIED"),
        "trustedPhoneLink": "UNVERIFIED", "contentAccessEnabled": False,
    }
    report.update(changes)
    return report


class PhoneNicknameTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "post-apollo" / "social-phone-nicknames.json"

    def call(self, *args, observer=None):
        return nickname.action(
            list(args), observer=observer if observer is not None else observation,
            path=self.path,
        )

    def locked(self, result):
        self.assertEqual(result["schema"], nickname.SCHEMA)
        self.assertEqual(result["execution"], "LOCAL_DISPLAY_METADATA")
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertEqual(set(result), {
            "schema", "execution", "state", "profileId", "nickname",
            "trustedPhoneLink", "contentAccessEnabled",
        })
        self.assertNotIn("AA:BB:CC", str(result))

    def test_no_storage_created_just_by_reading(self):
        r = self.call("--read", PROFILE)
        self.locked(r)
        self.assertEqual(r["state"], "EMPTY")
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.parent.exists())

    def test_save_read_replace_and_clear_only_current_profile(self):
        for label in ("My iPhone", "Personal Phone"):
            result = self.call("--save", PROFILE, label)
            self.locked(result)
            self.assertEqual(result["state"], "SAVED")
            self.assertEqual(self.call("--read", PROFILE)["nickname"], label)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.call("--clear", PROFILE)["state"], "CLEARED")
        self.assertEqual(self.call("--read", PROFILE)["state"], "EMPTY")
        self.assertEqual(self.call("--clear", PROFILE)["state"], "CLEARED")

    def test_paired_offline_can_keep_nickname_but_not_wrong_profile(self):
        offline = lambda: observation(state="PAIRED_OFFLINE")
        self.assertEqual(
            self.call("--save", PROFILE, "Offline Phone", observer=offline)["state"],
            "SAVED",
        )
        self.assertEqual(
            self.call("--read", OTHER)["state"], "DEVICE_UNAVAILABLE"
        )
        self.assertEqual(
            self.call("--save", OTHER, "Wrong")["state"], "DEVICE_UNAVAILABLE"
        )
        self.assertEqual(self.call("--read", PROFILE)["nickname"], "Offline Phone")

    def test_incompatible_status_and_unpaired_device_refuse_before_writing(self):
        cases = (
            observation(state="PROFILE_ONLY"),
            observation(state="UNAVAILABLE"),
            observation(profile=OTHER),
            observation(contentAccessEnabled=True),
            observation(trustedPhoneLink="VERIFIED"),
            observation(execution="WRONG"),
            {},
            None,
        )
        for report in cases:
            with self.subTest(report=report):
                response = self.call("--save", PROFILE, "Nope",
                                     observer=lambda: report)
                self.locked(response)
                self.assertEqual(response["state"], "DEVICE_UNAVAILABLE")
        self.assertFalse(self.path.exists())

    def test_invalid_labels_and_commands_are_rejected(self):
        for value in ("", " ", " X", "X ", "a" * 41, "\nInjected", "A\u200bB"):
            with self.subTest(label=repr(value)):
                self.assertEqual(
                    self.call("--save", PROFILE, value)["state"],
                    "INVALID_NICKNAME",
                )
        for command in ((), ("--read",), ("--clear", OTHER, "extra"),
                        ("--delete-everything", PROFILE), ("--save", PROFILE)):
            self.assertEqual(self.call(*command)["state"], "REFUSED")
        self.assertFalse(self.path.exists())

    def test_writes_refuse_unsafe_existing_storage_not_overwrite(self):
        self.path.parent.mkdir(mode=0o700)
        self.path.write_text("not json", encoding="utf-8")
        self.path.chmod(0o600)
        self.assertEqual(
            self.call("--save", PROFILE, "New")["state"], "STORAGE_UNAVAILABLE"
        )
        self.assertEqual(self.path.read_text(), "not json")
        self.path.write_text("{}", encoding="utf-8")
        self.path.chmod(0o644)
        self.assertEqual(
            self.call("--save", PROFILE, "New")["state"], "STORAGE_UNAVAILABLE"
        )
        self.path.unlink()
        outside = self.path.parent / "outside"
        outside.write_text("secret")
        self.path.symlink_to(outside)
        self.assertEqual(
            self.call("--save", PROFILE, "New")["state"], "STORAGE_UNAVAILABLE"
        )
        self.assertEqual(outside.read_text(), "secret")

    def test_max_profiles_refuses_new_but_existing_can_rename(self):
        self.path.parent.mkdir(mode=0o700)
        data = {
            "schema": nickname.STORE_SCHEMA,
            "profiles": {
                f"{i:08x}-e89b-42d3-a456-426614174000": f"Phone {i}"
                for i in range(8)
            },
        }
        import json
        self.path.write_text(json.dumps(data), encoding="utf-8")
        self.path.chmod(0o600)
        self.assertEqual(
            self.call("--save", PROFILE, "Ninth")["state"], "STORAGE_FULL"
        )
        selected = next(iter(data["profiles"]))
        self.assertEqual(
            self.call("--save", selected, "Renamed",
                      observer=lambda: observation(profile=selected))["state"],
            "SAVED",
        )
        self.assertEqual(len(nickname._load(self.path)), 8)

    def test_profile_switch_during_lock_refuses_write(self):
        states = iter((observation(), observation(profile=OTHER)))
        result = self.call("--save", PROFILE, "Nope", observer=lambda: next(states))
        self.locked(result)
        self.assertEqual(result["state"], "DEVICE_UNAVAILABLE")
        self.assertFalse(self.path.exists())

    def test_source_has_no_bluetooth_or_content_operations(self):
        source = (ROOT / "services/phone/PhoneNickname.py").read_text()
        for forbidden in ("bluetoothctl pair", "bluetoothctl remove",
                          "ListContacts(", "ListThreads(", "SendToThread(",
                          "StartDiscovery(", "ConnectProfile(", "systemctl start",
                          "subprocess.Popen("):
            self.assertNotIn(forbidden, source)
        self.assertIn("os.O_RDONLY", source)
        self.assertIn("os.O_NOFOLLOW", source)
        self.assertIn("fcntl.flock(", source)
        self.assertIn("os.replace(", source)


if __name__ == "__main__":
    unittest.main()
