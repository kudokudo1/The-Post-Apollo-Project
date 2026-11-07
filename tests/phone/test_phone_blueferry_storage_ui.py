"""P23 BlueFerry storage state and explicit keyring unlock bridge tests.

All providers are fake. The real iPhone, wallet, keyring, audio and BlueFerry
daemon are never queried or modified by this test suite.
"""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))

import PhoneBlueFerryStorageUi as storage_ui  # noqa: E402

OWNER = ":1.235"


class FakeDbusString(str):
    pass


class FakeInterface:
    def __init__(self, owner_source):
        self.source = owner_source

    def UnlockStorage(self, **kwargs):
        self.source.calls.append(("UnlockStorage", kwargs))
        if self.source.fail:
            raise RuntimeError("Fake keyring secret 1234")
        if self.source.switch_owner:
            self.source.current_owner = ":1.236"
        if self.source.unlock_result is None:
            self.source.status_data["storage_state"] = "ready"
            self.source.status_data["storage_detail"] = "Fake data ready"
            return FakeDbusString(json.dumps({
                "storage_policy": "encrypted",
                "storage_state": "ready",
                "storage_detail": "Fake data ready",
            }))
        return self.source.unlock_result


class FakeSource:
    def __init__(self, state="locked", policy="encrypted"):
        self.current_owner = OWNER
        self.status_data = {
            "api_version": 2, "daemon": True,
            "storage_policy": policy, "storage_state": state,
            "storage_detail": "Fake private wallet data",
        }
        self.calls = []
        self.fail = False
        self.switch_owner = False
        self.unlock_result = None

    def owner(self):
        self.calls.append(("owner", None))
        return self.current_owner

    def status(self, owner):
        self.calls.append(("status", owner))
        return dict(self.status_data)

    def _iface(self, owner):
        self.calls.append(("iface", owner))
        if owner != self.current_owner:
            raise ValueError("fake owner mismatch")
        return FakeInterface(self)

    @staticmethod
    def _json(raw, *, bound, kind):
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > bound:
            raise ValueError("invalid response")
        value = json.loads(raw)
        if type(value) is not kind:
            raise ValueError("bad shape")
        return value


class PhoneStorageUiTests(unittest.TestCase):
    def run_action(self, src, operation):
        return storage_ui.action(operation, source_factory=lambda: src)

    def test_status_is_read_only_even_when_storage_locked(self):
        src = FakeSource()
        result = self.run_action(src, "--status")
        self.assertEqual(result["state"], "LOCKED")
        self.assertEqual(result["storagePolicy"], "encrypted")
        self.assertEqual(result["schema"], storage_ui.SCHEMA)
        self.assertFalse(result["contentsIncluded"])
        self.assertFalse(result["credentialsIncluded"])
        self.assertFalse(any(name == "UnlockStorage" for name, _ in src.calls))
        self.assertNotIn("Fake private wallet data", str(result))

    def test_explicit_unlock_invokes_existing_blueferry_method_once(self):
        src = FakeSource()
        result = self.run_action(src, "--unlock")
        self.assertEqual(result["state"], "READY")
        self.assertEqual(result["storagePolicy"], "encrypted")
        self.assertEqual(len([name for name, _ in src.calls
                              if name == "UnlockStorage"]), 1)
        self.assertEqual(src.status_data["storage_state"], "ready")
        self.assertEqual(self.run_action(src, "--status")["state"], "READY")
        self.assertFalse(result["contentsIncluded"])

    def test_ready_encrypted_keyring_does_not_unlock_again(self):
        src = FakeSource(state="ready")
        self.assertEqual(self.run_action(src, "--status")["state"], "READY")
        self.assertEqual(self.run_action(src, "--unlock")["state"], "READY")
        self.assertFalse(any(name == "UnlockStorage" for name, _ in src.calls))

    def test_no_retention_is_not_silently_switched_to_encrypted(self):
        src = FakeSource(policy="none", state="disabled")
        self.assertEqual(self.run_action(src, "--status")["state"],
                         "NO_RETENTION")
        self.assertEqual(self.run_action(src, "--unlock")["state"],
                         "NO_RETENTION")
        self.assertFalse(any(name == "UnlockStorage" for name, _ in src.calls))

    def test_plaintext_storage_policy_is_not_modified(self):
        src = FakeSource(policy="plaintext", state="plaintext")
        self.assertEqual(self.run_action(src, "--status")["state"], "READY")
        self.assertEqual(self.run_action(src, "--unlock")["state"], "READY")
        self.assertFalse(any(name == "UnlockStorage" for name, _ in src.calls))

    def test_provider_not_running_is_safe(self):
        src = FakeSource()
        src.current_owner = ""
        self.assertEqual(self.run_action(src, "--status")["state"],
                         "PROVIDER_UNAVAILABLE")
        self.assertEqual(self.run_action(src, "--unlock")["state"],
                         "PROVIDER_UNAVAILABLE")
        self.assertFalse(any(name == "UnlockStorage" for name, _ in src.calls))

    def test_invalid_status_never_triggers_unlock(self):
        for bad in (
            {"api_version": True}, {"api_version": 99},
            {"daemon": False}, {"storage_policy": "unexpected"},
            {"storage_state": None},
        ):
            with self.subTest(bad=bad):
                src = FakeSource()
                src.status_data.update(bad)
                self.assertEqual(self.run_action(src, "--unlock")["state"],
                                 "UNLOCK_UNAVAILABLE")
                self.assertFalse(any(name == "UnlockStorage"
                                     for name, _ in src.calls))

    def test_changed_unique_daemon_owner_fails_closed(self):
        src = FakeSource()
        src.switch_owner = True
        result = self.run_action(src, "--unlock")
        self.assertEqual(result["state"], "UNLOCK_FAILED")
        self.assertNotIn("Fake", str(result))

    def test_wrong_or_invalid_unlock_reply_does_not_claim_success(self):
        for reply in (
            "not-json",
            json.dumps(["unexpected"]),
            json.dumps({"storage_policy": "encrypted",
                        "storage_state": "locked"}),
            json.dumps({"storage_policy": "plaintext",
                        "storage_state": "ready"}),
            "x" * (storage_ui.MAX_UNLOCK_RESPONSE + 1),
        ):
            with self.subTest(prefix=reply[:28]):
                src = FakeSource()
                src.unlock_result = FakeDbusString(reply)
                result = self.run_action(src, "--unlock")
                self.assertEqual(result["state"], "UNLOCK_FAILED")

    def test_keyring_error_never_exposes_error_text(self):
        src = FakeSource()
        src.fail = True
        answer = self.run_action(src, "--unlock")
        self.assertEqual(answer["state"], "UNLOCK_FAILED")
        self.assertNotIn("Fake keyring secret", str(answer))

    def test_only_status_or_explicit_unlock_are_accepted(self):
        for operation in ("--reset", "--clear-history", "--policy",
                          "unlock", "", "--send"):
            self.assertEqual(self.run_action(FakeSource(), operation)["state"],
                             "UNAVAILABLE")

    def test_no_destructive_methods_audio_or_key_material(self):
        src = (ROOT / "services/phone/PhoneBlueFerryStorageUi.py").read_text()
        for forbidden in (
            "ResetStorage(", "SetStoragePolicy(", "ClearHistory(",
            "SendToThread(", "Pair(", "StartService(", "GetContact(",
            "SetPhoneAudioRoute(", "subprocess.Popen(", "password",
        ):
            with self.subTest(forbidden=forbidden):
                if forbidden == "password":
                    # Text explains absence of password handling; method
                    # signatures must still never request credentials.
                    self.assertNotIn("password: str", src)
                    continue
                self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
