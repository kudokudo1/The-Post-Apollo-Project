"""P25 CALLS local Personal workspace source tests using synthetic iPhone data.

Never instantiates a real BlueFerry session bus, dials a phone number,
installs oFono, or changes audio, pairing or actual user data.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhoneCallWorkspace as cw  # noqa: E402

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"


def observation(profile=PROFILE, state="BLUETOOTH_CONNECTED"):
    return {
        "schema": "post-apollo.phone.device-observation.v0",
        "execution": "READ_ONLY_DEVICE_OBSERVATION",
        "state": state, "profileId": profile,
        "bluetoothLink": "CONNECTED",
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }


def card(cid="call:1", state="incoming", name="Invented Person",
         number="+15551234567"):
    return {
        "call_id": cid, "state": state, "direction": "incoming",
        "contact_name": name, "number": number,
        "multiparty": False, "emergency": False,
    }


class FakeSource:
    def __init__(self, status=None, calls=None):
        self.current_owner = ":1.191"
        self.status_value = {
            "api_version": 2, "daemon": True,
            "phone_profile_id": PROFILE,
            "calls_enabled": True,
            "calls_state": "ready",
        }
        if status:
            self.status_value.update(status)
        self.calls_value = {"state": "ready", "calls": [card()]} if calls is None else calls
        self.calls_made = []
        self.switch_owner_on_action = False
        self.change_profile_on_action = False
        self.failed = False

    def owner(self):
        return self.current_owner

    def status(self, _owner):
        return dict(self.status_value)

    def calls(self, _owner):
        return self.calls_value

    def perform(self, owner, action, argument):
        assert owner == ":1.191"
        self.calls_made.append((action, argument))
        if self.failed:
            raise RuntimeError("private call detail +15551234567")
        if self.switch_owner_on_action:
            self.current_owner = ":1.192"
        if self.change_profile_on_action:
            self.status_value["phone_profile_id"] = OTHER


class CallWorkspaceTests(unittest.TestCase):
    def run_cmd(self, src, *argv, observed=None):
        return cw.run(list(argv), source_factory=lambda: src,
                      observer=lambda: observation() if observed is None else observed)

    def test_status_returns_actual_safe_call_view_not_fake_dial_actions(self):
        src = FakeSource()
        result = self.run_cmd(src, "--status")
        self.assertEqual(result["state"], "READY")
        self.assertEqual(result["schema"], cw.SCHEMA)
        self.assertEqual(result["scope"], "PERSONAL_LOCAL_USER_ONLY")
        self.assertFalse(result["organizationGrant"])
        self.assertFalse(result["faceTimeEnabled"])
        self.assertFalse(result["smsReplyEnabled"])
        self.assertFalse(result["autoCallingEnabled"])
        self.assertEqual(result["calls"][0]["peer"], "Invented Person")
        self.assertEqual(result["calls"][0]["state"], "incoming")
        self.assertNotIn("+15551234567", str(result))
        self.assertEqual(src.calls_made, [])

    def test_unknown_caller_has_only_masked_last_four(self):
        src = FakeSource(calls={"state": "ready", "calls": [card(name="")]})
        result = self.run_cmd(src, "--status")
        self.assertEqual(result["state"], "READY")
        self.assertEqual(result["calls"][0]["peer"], "•••• 4567")
        self.assertNotIn("+15551234567", str(result))

    def test_backend_disabled_or_not_ready_never_discloses_caller(self):
        for status, expected in (
            ({"calls_enabled": False}, "DISABLED"),
            ({"calls_enabled": True, "calls_state": "searching"}, "SEARCHING"),
            ({"calls_state": "unavailable"}, "UNAVAILABLE"),
            ({"calls_state": "bluez_conflict"}, "BLUEZ_CONFLICT"),
            ({"calls_state": "connecting"}, "CONNECTING"),
            ({"calls_state": "bad"}, "UNSUPPORTED"),
            ({"calls_enabled": "yes"}, "UNSUPPORTED"),
        ):
            with self.subTest(status=status):
                src = FakeSource(status=status)
                answer = self.run_cmd(src, "--status")
                self.assertEqual(answer["state"], expected)
                self.assertNotIn("calls", answer)
                self.assertEqual(src.calls_made, [])

    def test_device_offline_or_switched_blocks_access(self):
        src = FakeSource()
        for value in (observation(state="PAIRED_OFFLINE"), observation(OTHER)):
            result = self.run_cmd(src, "--status", observed=value)
            self.assertEqual(result["state"], "DEVICE_UNAVAILABLE")
            self.assertNotIn("calls", result)
        self.assertEqual(
            self.run_cmd(src, "--action", "answer", "call:1",
                         observed=observation(OTHER))["state"],
            "DEVICE_UNAVAILABLE",
        )
        self.assertEqual(src.calls_made, [])

    def test_direct_answer_and_decline_require_ringing_call_id(self):
        src = FakeSource()
        answer = self.run_cmd(src, "--action", "answer", "call:1")
        self.assertEqual(answer["state"], "ACTION_SUBMITTED")
        self.assertEqual(src.calls_made[-1], ("answer", "call:1"))
        declined = self.run_cmd(src, "--action", "decline", "call:1")
        self.assertEqual(declined["state"], "ACTION_SUBMITTED")
        self.assertEqual(src.calls_made[-1], ("decline", "call:1"))
        unknown = self.run_cmd(src, "--action", "answer", "other-call")
        self.assertEqual(unknown["state"], "ACTION_REFUSED")
        src.calls_value = {"state": "ready", "calls": [card(state="active")]}
        invalid = self.run_cmd(src, "--action", "decline", "call:1")
        self.assertEqual(invalid["state"], "ACTION_REFUSED")

    def test_hangup_is_per_call_only(self):
        src = FakeSource(calls={"state": "ready", "calls": [card(state="active")]})
        self.assertEqual(
            self.run_cmd(src, "--action", "hangup", "call:1")["state"],
            "ACTION_SUBMITTED",
        )
        self.assertIn(("hangup", "call:1"), src.calls_made)
        self.assertEqual(
            self.run_cmd(src, "--action", "hangup", "wrong")["state"],
            "ACTION_REFUSED",
        )
        self.assertEqual(
            self.run_cmd(src, "--action", "hangup-all")["state"], "REFUSED",
        )

    def test_dial_accepts_only_plain_numbers_backend_confirms(self):
        src = FakeSource(calls={"state": "ready", "calls": []})
        self.assertEqual(
            self.run_cmd(src, "--action", "dial", "+15559876543")["state"],
            "ACTION_SUBMITTED",
        )
        self.assertEqual(src.calls_made, [("dial", "+15559876543")])
        for bad in ("911", "112", "+911", "000", "*21#", "12", "",
                    "555 123 4567", "123;sh -c x", "+", "+1" * 12):
            with self.subTest(dial=bad):
                answer = self.run_cmd(src, "--action", "dial", bad)
                self.assertEqual(answer["state"], "ACTION_REFUSED")
        self.assertEqual(src.calls_made, [("dial", "+15559876543")])

    def test_dtmf_swap_and_hold_answer_have_exact_preconditions(self):
        src = FakeSource(calls={"state": "ready", "calls": [
            card("active.1", "active"),
            card("held.2", "held"),
            card("wait.3", "waiting"),
        ]})
        for action, arg in (("tones", "active.1\t12#"),
                            ("swap", ""), ("hold-answer", "")):
            args = ("--action", action, arg) if arg else ("--action", action)
            self.assertEqual(self.run_cmd(src, *args)["state"], "ACTION_SUBMITTED")
        for action, arg in (("tones", "held.2\t123"),
                            ("tones", "active.1\t123abc"),
                            ("tones", "bad\t123"),
                            ("answer", "active.1")):
            self.assertEqual(self.run_cmd(src, "--action", action, arg)["state"],
                             "ACTION_REFUSED")
        src.calls_value = {"state": "ready", "calls": [card("active.1", "active")]}
        self.assertEqual(self.run_cmd(src, "--action", "swap")["state"], "ACTION_REFUSED")
        self.assertEqual(self.run_cmd(src, "--action", "hold-answer")["state"],
                         "ACTION_REFUSED")

    def test_malformed_snapshot_cannot_trigger_or_display_calls(self):
        bad = [
            {"state": "ready", "calls": [card(), card()]},
            {"state": "ready", "calls": [card(state="fake-state")]},
            {"state": "ready", "calls": [card(number="x", name="\x00")]},
            {"state": "ready", "calls": [card(cid="call id whitespace")]},
            {"state": "ready", "calls": [card(name="X" * 500)]},
            {"state": "ready", "calls": ["not a call"]},
            {"state": "ready", "calls": [card()] * 9},
            {"state": "disabled", "calls": [card()]},
        ]
        for payload in bad:
            with self.subTest(p=payload):
                src = FakeSource(calls=payload)
                view = self.run_cmd(src, "--status")
                # Sanitized source refuses ambiguous/malformed batches.
                self.assertIn(view["state"], ("BACKEND_UNAVAILABLE", "READY"))
                self.assertEqual(src.calls_made, [])
                action = self.run_cmd(src, "--action", "answer", "call:1")
                if view["state"] != "READY":
                    self.assertNotEqual(action["state"], "ACTION_SUBMITTED")
        # A long/unsafe name is suppressed, never echoed as an error.
        src = FakeSource(calls={"state": "ready", "calls": [card(name="bad\nname")]})
        value = self.run_cmd(src, "--status")
        self.assertEqual(value["state"], "READY")
        self.assertEqual(value["calls"][0]["peer"], "•••• 4567")

    def test_owner_and_profile_changes_after_action_are_not_confirmed(self):
        for attr in ("switch_owner_on_action", "change_profile_on_action"):
            with self.subTest(attr=attr):
                src = FakeSource()
                setattr(src, attr, True)
                result = self.run_cmd(src, "--action", "answer", "call:1")
                self.assertEqual(result["state"], "DEVICE_UNAVAILABLE")
                self.assertEqual(src.calls_made, [("answer", "call:1")])

    def test_provider_failures_do_not_leak_private_information(self):
        src = FakeSource()
        src.failed = True
        result = self.run_cmd(src, "--action", "answer", "call:1")
        self.assertEqual(result["state"], "ACTION_FAILED")
        self.assertNotIn("+15551234567", str(result))

    def test_invalid_commands_are_not_routed_to_provider(self):
        src = FakeSource()
        for argv in ((), ("--enable",), ("--status", "--action"),
                     ("--action", "face-time", "call:1"),
                     ("--action", "reply-text", "call:1"),
                     ("--action", "transfer", "call:1"),
                     ("--action", "conference", "call:1"),
                     ("--action", "answer"),
                     ("--action", "answer", "call:1", "extra")):
            with self.subTest(argv=argv):
                self.assertEqual(self.run_cmd(src, *argv)["state"], "REFUSED")
        self.assertEqual(src.calls_made, [])

    def test_backend_has_no_autostart_service_command_or_debug_logging(self):
        content = (ROOT / "services/phone/PhoneCallWorkspace.py").read_text()
        for forbidden in (
            "subprocess.Popen(", "systemctl start", "bluetoothctl pair",
            "SetCallsEnabled(", "HangupAll(", "SendToThread(",
            "CallHistory1", "Facetime(", "FaceTime(",
        ):
            self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
