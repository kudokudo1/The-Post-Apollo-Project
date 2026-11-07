"""P21 remembered Personal read preference, synthetic phone/Unix UID only.

No live Fedora, iPhone, BlueFerry, Identity Center or organization grants.
All thread bodies and contact values in this suite are invented.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from threading import Event, Thread
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhoneRememberedRead as remembered  # noqa: E402

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"
OWNER = ":1.111"


def device(profile=PROFILE, state="BLUETOOTH_CONNECTED"):
    return {
        "schema": "post-apollo.phone.device-observation.v0",
        "execution": "READ_ONLY_DEVICE_OBSERVATION",
        "state": state,
        "profileId": profile,
        "bluetoothLink": "CONNECTED",
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }


def threads():
    return [{
        "key": "address:phone:15551112222", "name": "Synthetic Chat",
        "is_group": False, "reply_ready": False, "unread": False,
        "messages_truncated": False,
        "messages": [{
            "handle": "msg-one", "body": "INVENTED SECRET BODY",
            "timestamp": "2026-11-06T17:00:00Z",
            "outgoing": False, "read": True, "sender": "",
        }],
    }]


def contacts():
    return {
        "total": 1, "offset": 0, "query": "",
        "contacts": [{
            "id": "contact-one", "name": "Synthetic Person",
            "organization": "", "primary": "fake@example.invalid",
            "phone_count": 0, "email_count": 1, "has_photo": False,
        }],
    }


class FakeSource:
    def __init__(self):
        self.current_owner = OWNER
        self.status_data = {
            "api_version": 2, "daemon": True,
            "phone_profile_id": PROFILE, "map": True, "pbap": True,
            "contact_card_count": 1, "contact_card_epoch": 7,
        }
        self.calls = []
        self.on_fetch = None

    def owner(self):
        self.calls.append("owner")
        return self.current_owner

    def status(self, owner):
        self.calls.append("status")
        return dict(self.status_data)

    def threads(self, owner):
        self.calls.append("threads")
        if self.on_fetch is not None:
            self.on_fetch()
        return threads()

    def contact_cards(self, owner):
        self.calls.append("contacts")
        if self.on_fetch is not None:
            self.on_fetch()
        return contacts()


class RememberedPersonalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "post-apollo" / "permission.json"
        self.source = FakeSource()
        self.observed = device()

    def action(self, *args):
        return remembered.action(
            list(args), observer=lambda: self.observed,
            source_factory=lambda: self.source,
            location=self.path,
        )

    def assert_public(self, value):
        self.assertEqual(value["schema"], remembered.SCHEMA)
        self.assertEqual(value["execution"],
                         "LOCAL_USER_PREFERENCE_NOT_AUTHORITY")
        self.assertEqual(value["ownerKind"], "PERSONAL")
        self.assertFalse(value["organizationAccess"])
        self.assertFalse(value["sendingEnabled"])

    def test_no_implicit_consent_and_load_returns_visible_reason(self):
        status = self.action("--status")
        self.assert_public(status)
        self.assertEqual(status["state"], "APPROVAL_REQUIRED")
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "APPROVAL_REQUIRED")
        self.assertEqual(self.action("--read", "contacts.read")["state"],
                         "APPROVAL_REQUIRED")
        self.assertFalse(self.path.exists())
        self.assertEqual(self.source.calls, [])

    def test_approve_once_persists_both_capabilities_across_read_invocations(self):
        approved = self.action("--approve", "b")
        self.assert_public(approved)
        self.assertEqual(approved["state"], "APPROVED")
        self.assertTrue(approved["messagesAllowed"])
        self.assertTrue(approved["contactsAllowed"])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)

        first = self.action("--read", "messages.read")
        self.assertEqual(first["state"], "SNAPSHOT")
        self.assertEqual(first["operation"], "messages.read")
        self.assertEqual(first["projection"]["messageSets"][0]["messages"][0]["body"],
                         "INVENTED SECRET BODY")
        self.assertEqual(first["projection"]["authorization"], "NOT_EVALUATED")
        self.assertEqual(first["profileId"], PROFILE)
        self.assertGreater(first["epoch"], approved["epoch"])
        self.assertEqual(first["sequence"], 1)

        second = self.action("--read", "contacts.read")
        self.assertEqual(second["state"], "SNAPSHOT")
        self.assertEqual(second["projection"]["contacts"][0]["displayNameInProfile"],
                         "Synthetic Person")
        self.assertEqual(second["contextKey"], first["contextKey"])
        self.assertGreater(second["epoch"], first["epoch"])
        self.assertEqual(second["sequence"], 1)

        next_message = self.action("--read", "messages.read")
        self.assertEqual(next_message["sequence"], 2)
        self.assertGreater(next_message["epoch"], second["epoch"])
        current = self.action("--status")
        self.assertEqual(current["state"], "APPROVED")
        self.assertEqual(current["epoch"], next_message["epoch"])
        self.assertEqual(current["contextKey"], first["contextKey"])

        raw = self.path.read_text()
        self.assertNotIn("INVENTED SECRET BODY", raw)
        self.assertNotIn("Synthetic Person", raw)
        self.assertNotIn("fake@example.invalid", raw)
        self.assertNotIn("15551112222", raw)
        self.assertEqual(self.action("--revoke")["state"], "REVOKED")
        self.assertEqual(self.action("--status")["state"], "APPROVAL_REQUIRED")
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "APPROVAL_REQUIRED")
        self.assertEqual(self.action("--read", "contacts.read")["state"],
                         "APPROVAL_REQUIRED")

    def test_reapprove_after_revoke_invalidates_previous_view_generation(self):
        a = self.action("--approve", "b")
        self.assertEqual(a["state"], "APPROVED")
        self.assertEqual(self.action("--revoke")["state"], "REVOKED")
        b = self.action("--approve", "b")
        self.assertEqual(b["state"], "APPROVED")
        self.assertNotEqual(a["contextKey"], b["contextKey"])
        self.assertGreater(b["epoch"], a["epoch"])
        self.assertEqual(self.action("--read", "messages.read")["state"], "SNAPSHOT")

    def test_message_and_contact_approval_independent(self):
        self.assertEqual(self.action("--approve", "m")["state"], "APPROVED")
        self.assertEqual(self.action("--read", "contacts.read")["state"],
                         "NOT_CONSENTED")
        self.assertEqual(self.action("--read", "messages.read")["state"], "SNAPSHOT")
        self.assertNotIn("contacts", self.source.calls)
        self.assertEqual(self.action("--approve", "c")["state"], "APPROVED")
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "NOT_CONSENTED")
        self.assertEqual(self.action("--read", "contacts.read")["state"], "SNAPSHOT")

    def test_disconnected_device_fails_closed_then_same_profile_can_resume(self):
        self.assertEqual(self.action("--approve", "b")["state"], "APPROVED")
        self.observed = device(state="PAIRED_OFFLINE")
        self.assertEqual(self.action("--status")["state"], "DEVICE_UNAVAILABLE")
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "DEVICE_UNAVAILABLE")
        self.observed = device()
        self.assertEqual(self.action("--status")["state"], "APPROVED")
        self.assertEqual(self.action("--read", "messages.read")["state"], "SNAPSHOT")

    def test_phone_switch_never_inherits_old_consent(self):
        self.assertEqual(self.action("--approve", "b")["state"], "APPROVED")
        self.observed = device(profile=OTHER)
        self.source.status_data["phone_profile_id"] = OTHER
        self.assertEqual(self.action("--status")["state"], "DEVICE_UNAVAILABLE")
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "DEVICE_UNAVAILABLE")
        self.assertEqual(self.action("--approve", "m")["state"], "APPROVED")
        self.assertEqual(self.action("--read", "contacts.read")["state"],
                         "NOT_CONSENTED")
        self.assertEqual(self.action("--read", "messages.read")["state"], "SNAPSHOT")
        self.observed = device(profile=PROFILE)
        self.source.status_data["phone_profile_id"] = PROFILE
        self.assertEqual(self.action("--status")["state"], "DEVICE_UNAVAILABLE")

    def test_provider_name_or_capability_change_fails_to_expose_content(self):
        self.assertEqual(self.action("--approve", "b")["state"], "APPROVED")
        self.source.current_owner = ""
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "PROVIDER_UNAVAILABLE")
        self.source.current_owner = OWNER
        self.source.status_data["map"] = False
        answer = self.action("--read", "messages.read")
        self.assertEqual(answer["state"], "READ_UNAVAILABLE")
        self.assertNotIn("INVENTED SECRET BODY", str(answer))
        self.source.status_data["map"] = True
        self.source.status_data["contact_card_epoch"] = None
        self.assertEqual(self.action("--read", "contacts.read")["state"],
                         "READ_UNAVAILABLE")

    def test_disconnect_during_fetch_discards_snapshot(self):
        self.assertEqual(self.action("--approve", "m")["state"], "APPROVED")
        self.source.on_fetch = lambda: setattr(
            self, "observed", device(state="PAIRED_OFFLINE")
        )
        reply = self.action("--read", "messages.read")
        self.assertIn(reply["state"], ("READ_UNAVAILABLE", "DEVICE_UNAVAILABLE"))
        self.assertNotIn("INVENTED SECRET BODY", str(reply))

    def test_revoke_still_works_when_phone_is_disconnected(self):
        self.assertEqual(self.action("--approve", "m")["state"], "APPROVED")
        self.observed = device(state="PAIRED_OFFLINE")
        self.assertEqual(self.action("--revoke")["state"], "REVOKED")
        self.assertEqual(self.action("--status")["state"], "APPROVAL_REQUIRED")

    def test_unapproved_requests_cannot_claim_organization_line_or_send(self):
        for invalid in (
            ["--approve", "ALL"],
            ["--approve", "b", "--organization", "org"],
            ["--read", "messages.send"],
            ["--read", "contacts.write"],
            ["--read", "messages.read", "--device", OTHER],
            ["--read"],
            ["--serve"],
            [],
        ):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.action(*invalid)["state"], "REFUSED")
        self.assertFalse(self.path.exists())

    def test_unsafe_files_and_symlink_fail_closed(self):
        self.assertEqual(self.action("--approve", "b")["state"], "APPROVED")
        os.chmod(self.path, 0o644)
        self.assertEqual(self.action("--status")["state"], "STORAGE_UNAVAILABLE")
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "STORAGE_UNAVAILABLE")
        os.chmod(self.path, 0o600)
        original = self.path.read_text()
        self.path.unlink()
        another = self.path.parent / "elsewhere"
        another.write_text(original)
        self.path.symlink_to(another)
        self.assertEqual(self.action("--status")["state"], "STORAGE_UNAVAILABLE")
        self.assertEqual(self.action("--approve", "b")["state"], "STORAGE_UNAVAILABLE")

    def test_invalid_record_cannot_be_trusted_even_when_owner_only(self):
        self.assertEqual(self.action("--approve", "b")["state"], "APPROVED")
        original = json.loads(self.path.read_text())
        for bad in (
            {"allowed": ["messages.send"]},
            {"approved": False},
            {"sequences": {"contacts.read": True, "messages.read": 0}},
            {"profileId": "spoof"},
            {"contextKey": "short"},
            {"epoch": 0},
            {"tenantId": "userTypedTenant"},
        ):
            change = dict(original)
            change.update(bad)
            self.path.write_text(json.dumps(change))
            with self.subTest(fields=bad):
                self.assertEqual(self.action("--status")["state"],
                                 "STORAGE_UNAVAILABLE")
        self.path.write_text(json.dumps(original))
        self.assertEqual(self.action("--status")["state"], "APPROVED")

    def test_partial_storage_failure_never_releases_private_content(self):
        self.assertEqual(self.action("--approve", "b")["state"], "APPROVED")
        with mock.patch.object(remembered, "_write", return_value=False):
            reply = self.action("--read", "messages.read")
        self.assertEqual(reply["state"], "STORAGE_UNAVAILABLE")
        self.assertNotIn("INVENTED SECRET BODY", str(reply))

    def test_atomic_revoke_orders_after_in_flight_local_read(self):
        self.assertEqual(self.action("--approve", "b")["state"], "APPROVED")
        entered, proceed = Event(), Event()
        def blocking_fetch():
            entered.set()
            self.assertTrue(proceed.wait(3))
        self.source.on_fetch = blocking_fetch
        reads, revocations = [], []
        a = Thread(target=lambda: reads.append(self.action("--read", "messages.read")))
        b = Thread(target=lambda: revocations.append(self.action("--revoke")))
        a.start()
        self.assertTrue(entered.wait(2))
        b.start()
        self.assertEqual(revocations, [], "revoke bypassed exclusive preference lock")
        proceed.set()
        a.join(4)
        b.join(4)
        self.assertFalse(a.is_alive())
        self.assertFalse(b.is_alive())
        self.assertEqual(reads[0]["state"], "SNAPSHOT")
        self.assertEqual(revocations[0]["state"], "REVOKED")
        self.assertEqual(self.action("--read", "messages.read")["state"],
                         "APPROVAL_REQUIRED")

    def test_no_background_service_audio_changes_or_private_content_storage(self):
        content = (ROOT / "services/phone/PhoneRememberedRead.py").read_text()
        for forbidden in (
            "subprocess.Popen(", "socket.listen(", "SendToThread(",
            "MarkThreadRead(", "GetContactPhoto(", "SetPhoneAudioRoute(",
            "bluetoothctl pair", "systemctl start", "os.environ['DBUS_SESSION_BUS_ADDRESS']",
            "identity_center_signed_grant",
        ):
            self.assertNotIn(forbidden, content)
        self.assertIn("fcntl.LOCK_EX", content)
        self.assertIn("os.O_NOFOLLOW", (ROOT / "services/phone/PhoneNickname.py").read_text())
        self.assertIn('ownerKind": "PERSONAL"', content)
        self.assertIn('"organizationAccess": False', content)


if __name__ == "__main__":
    unittest.main()
