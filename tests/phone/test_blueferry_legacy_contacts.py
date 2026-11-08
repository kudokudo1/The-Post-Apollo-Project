"""P24 // BlueFerry 0.9.1 legacy cached contact reader compatibility.

Synthetic data only. No real contacts, BlueFerry daemon, iPhone, keyring,
Audio/HFP, or local Fedora files are accessed by this suite.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
port = importlib.import_module("BlueFerryHostReadPort")
projection = importlib.import_module("BlueFerrySocialProjection")

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"
OWNER = ":1.913"


def legacy_status(**changes):
    result = {
        "api_version": 2, "daemon": True,
        "phone_profile_id": PROFILE, "map": True, "pbap": True,
        # Older BlueFerry reports *neither* contact-card metadata field.
        "contacts": 141, "storage_state": "ready",
    }
    result.update(changes)
    return result


def older_rows():
    return [
        {"name": "Synthetic Person", "phones": ["+15550001001", "+15550001002"],
         "emails": ["fake@example.invalid"]},
        {"name": "Another Example", "phones": [], "emails": ["x@example.invalid"]},
    ]


class FakeLegacySource:
    def __init__(self, *, before=None, after=None, records=None):
        self.owner_now = OWNER
        self.before = legacy_status() if before is None else before
        self.after = legacy_status() if after is None else after
        self.records = older_rows() if records is None else records
        self.calls = []
        self.change_owner_on_read = False

    def owner(self):
        self.calls.append("owner")
        return self.owner_now

    def status(self, owner):
        self.calls.append("status")
        if self.calls.count("status") == 1:
            return self.before
        return self.after

    def legacy_contacts(self, owner):
        self.calls.append("legacy_contacts")
        if self.change_owner_on_read:
            self.owner_now = ":1.914"
        return self.records

    def contact_cards(self, owner):
        self.calls.append("UNEXPECTED_CONTACT_CARD_READ")
        raise AssertionError("modern ListContactCards must not be called")


class LegacyContactProjectionTest(unittest.TestCase):
    def test_legacy_person_records_are_display_only_not_chat_conversations(self):
        result = projection.normalize_legacy_contact_page(
            older_rows(), profile_id=PROFILE, read_epoch="read-abc123",
        )
        self.assertTrue(result["legacyReadOnly"])
        self.assertFalse(result["historyPartial"])
        self.assertFalse(result["routeEligible"])
        self.assertEqual(result["authorization"], "NOT_EVALUATED")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["daemonEpoch"], "read-abc123")
        self.assertEqual(len(result["contacts"]), 2)
        first = result["contacts"][0]
        self.assertEqual(first["id"], f"{PROFILE}:read-abc123:legacy-row-0")
        self.assertEqual(first["displayNameInProfile"], "Synthetic Person")
        self.assertEqual(first["primary"], "+15550001001")
        self.assertEqual(first["phoneCount"], 2)
        self.assertEqual(first["emailCount"], 1)
        self.assertFalse(first["hasPhoto"])
        self.assertNotIn("conversations", result)
        self.assertNotIn("messages", result)
        self.assertNotIn("phoneNumbers", first)  # No raw address list stored.
        self.assertNotIn("sendEnabled", first)

    def test_new_read_epoch_makes_all_legacy_ids_ephemeral(self):
        a = projection.normalize_legacy_contact_page(
            older_rows(), profile_id=PROFILE, read_epoch="read-a",
        )
        b = projection.normalize_legacy_contact_page(
            older_rows(), profile_id=PROFILE, read_epoch="read-b",
        )
        self.assertNotEqual(a["contacts"][0]["id"], b["contacts"][0]["id"])
        self.assertNotEqual(a["daemonEpoch"], b["daemonEpoch"])

    def test_legacy_bounded_page_never_claims_full_phonebook(self):
        rows = [{"name": "Fake", "phones": [], "emails": []}
                for _ in range(projection.MAX_CARDS)]
        result = projection.normalize_legacy_contact_page(
            rows, profile_id=PROFILE, read_epoch="this-view",
        )
        self.assertTrue(result["historyPartial"])
        self.assertEqual(result["total"], projection.MAX_CARDS)
        with self.assertRaises(ValueError):
            projection.normalize_legacy_contact_page(
                rows + [rows[0]], profile_id=PROFILE, read_epoch="this-view",
            )

    def test_malformed_private_rows_fail_with_content_free_error(self):
        private = "PRIVATE CONTACT THAT MUST NOT BE LOGGED"
        invalid = [
            "not a page",
            [{"name": private, "phones": None, "emails": []}],
            [{"name": private, "phones": "not-a-list", "emails": []}],
            [{"name": private, "phones": ["\x00"], "emails": []}],
            [{"name": private, "phones": [], "emails": [4]}],
            [{"name": private, "phones": [True], "emails": []}],
            [{"name": private, "phones": [private] * 65, "emails": []}],
            [{"name": "\x00", "phones": [], "emails": []}],
            [{"name": private * 20, "phones": [], "emails": []}],
            [False],
        ]
        for payload in invalid:
            with self.subTest(variant=type(payload).__name__):
                with self.assertRaises(ValueError) as exc:
                    projection.normalize_legacy_contact_page(
                        payload, profile_id=PROFILE, read_epoch="read-a",
                    )
                self.assertNotIn(private, str(exc.exception))


class LegacyHostPortTest(unittest.TestCase):
    def invoke(self, src):
        released = Mock(return_value=True)
        guard = Mock(return_value=True)
        result = port.read_for_trusted_host(
            operation="contacts.read", profile_id=PROFILE, source=src,
            host_guard=guard, host_release=released,
        )
        self.assertNotIn("Synthetic Person", str(result))
        self.assertFalse(result["contentInResponse"])
        return result, guard, released

    def test_0_9_1_without_card_metadata_releases_legacy_snapshot(self):
        src = FakeLegacySource()
        result, guard, release = self.invoke(src)
        self.assertEqual(result["state"], "HOST_HANDOFF_REPORTED")
        self.assertEqual(src.calls, [
            "owner", "status", "legacy_contacts", "owner", "status"
        ])
        self.assertEqual(guard.call_count, 2)
        self.assertEqual(release.call_count, 1)
        view = release.call_args.args[3]
        self.assertTrue(view["legacyReadOnly"])
        self.assertEqual(len(view["contacts"]), 2)
        self.assertEqual(len(view["daemonEpoch"]), 32)
        int(view["daemonEpoch"], 16)  # Hex-only random per-read namespace.

    def test_legacy_refresh_uses_new_random_scoped_ids(self):
        first = FakeLegacySource()
        second = FakeLegacySource()
        a = self.invoke(first)[2].call_args.args[3]
        b = self.invoke(second)[2].call_args.args[3]
        self.assertNotEqual(a["daemonEpoch"], b["daemonEpoch"])
        self.assertNotEqual(a["contacts"][0]["id"], b["contacts"][0]["id"])

    def test_no_legacy_fallback_for_bad_or_half_modern_metadata(self):
        bad = [
            legacy_status(pbap=False),
            legacy_status(contact_card_count=3),
            legacy_status(contact_card_epoch=3),
            legacy_status(contact_card_count=None, contact_card_epoch=None),
            legacy_status(contact_card_count=3, contact_card_epoch=True),
            legacy_status(phone_profile_id=OTHER),
        ]
        for before in bad:
            with self.subTest(keys=before):
                src = FakeLegacySource(before=before)
                result, _, release = self.invoke(src)
                self.assertEqual(result["state"], "PROVIDER_UNAVAILABLE")
                release.assert_not_called()
                self.assertNotIn("legacy_contacts", src.calls)

    def test_mode_change_or_phone_change_during_read_blocks_release(self):
        changed = [
            legacy_status(contact_card_count=2, contact_card_epoch=4),
            legacy_status(pbap=False),
            legacy_status(phone_profile_id=OTHER),
        ]
        for after in changed:
            with self.subTest(after=after):
                src = FakeLegacySource(after=after)
                result, _, release = self.invoke(src)
                self.assertEqual(result["state"], "PROVIDER_CHANGED")
                release.assert_not_called()
        src = FakeLegacySource()
        src.change_owner_on_read = True
        result, _, release = self.invoke(src)
        self.assertEqual(result["state"], "PROVIDER_CHANGED")
        release.assert_not_called()

    def test_invalid_legacy_payload_is_not_released(self):
        src = FakeLegacySource(records=[{"name": "private", "phones": "bad", "emails": []}])
        result, _, release = self.invoke(src)
        self.assertEqual(result["state"], "PROVIDER_UNAVAILABLE")
        release.assert_not_called()
        self.assertNotIn("private", str(result))

    def test_host_denial_never_reads_contacts(self):
        src = FakeLegacySource()
        release = Mock(return_value=True)
        response = port.read_for_trusted_host(
            operation="contacts.read", profile_id=PROFILE,
            source=src, host_guard=lambda *args: False,
            host_release=release,
        )
        self.assertEqual(response["state"], "HOST_DENIED")
        release.assert_not_called()
        self.assertNotIn("legacy_contacts", src.calls)

    def test_actual_dbus_legacy_method_uses_unique_owner_and_bounded_reply(self):
        class DbusString(str):
            pass

        class FakeBus:
            def name_has_owner(self, service):
                return service == port.SERVICE
            def get_name_owner(self, _):
                return OWNER
            def get_object(self, owner, object_path, introspect=False):
                self_assert.assertEqual(owner, OWNER)
                self_assert.assertEqual(object_path, port.OBJECT)
                self_assert.assertFalse(introspect)
                return "proxy"

        class FakeIface:
            def ListContacts(self, offset, limit, **kwargs):
                self_assert.assertEqual(offset, 0)
                self_assert.assertEqual(limit, projection.MAX_CARDS)
                self_assert.assertEqual(kwargs["timeout"], 10)
                return DbusString(json.dumps(older_rows()))

        class Dbus:
            @staticmethod
            def UInt32(v):
                return v
            @staticmethod
            def Interface(proxy, interface):
                self_assert.assertEqual(interface, port.INTERFACE)
                return FakeIface()

        self_assert = self
        src = port.UniqueOwnerBlueFerrySource(
            dbus_api=Dbus, session_bus=FakeBus()
        )
        self.assertEqual(src.legacy_contacts(OWNER), older_rows())
        with self.assertRaises(ValueError):
            src.legacy_contacts(":1.987")


if __name__ == "__main__":
    unittest.main()
