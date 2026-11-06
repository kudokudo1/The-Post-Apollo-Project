"""P18a BlueFerry conversion uses synthetic records only; no private D-Bus."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
projection = importlib.import_module("BlueFerrySocialProjection")
A = "123e4567-e89b-42d3-a456-426614174000"
B = "223e4567-e89b-42d3-a456-426614174000"
EARLY = "2026-11-06T10:00:00+00:00"
LATE = "2026-11-06T10:01:00Z"


def message(handle="msg-1", body="hello", timestamp=EARLY,
            outgoing=False, read=True, **more):
    return {"handle": handle, "body": body, "timestamp": timestamp,
            "outgoing": outgoing, "read": read, "sender": "", **more}


def thread(key="address:phone:15551111111", name="Alex", messages=None, **more):
    value = {"key": key, "name": name, "is_group": False, "reply_ready": True,
             "unread": False, "messages_truncated": False,
             "messages": [message()] if messages is None else messages}
    value.update(more)
    return value


def page():
    return {"total": 2, "offset": 0, "query": "",
            "contacts": [
                {"id": "card-one", "name": "Alex", "organization": "",
                 "primary": "+15551111111", "phone_count": 2,
                 "email_count": 1, "has_photo": False},
                {"id": "card-two", "name": "Taylor", "organization": "Studio",
                 "primary": "", "phone_count": 0, "email_count": 1,
                 "has_photo": True},
            ]}


class ThreadProjectionTests(unittest.TestCase):
    def locked(self, view):
        self.assertEqual(view["schema"], projection.SCHEMA)
        self.assertEqual(view["execution"], "OFFLINE_PROJECTION_ONLY")
        self.assertEqual(view["authorization"], "NOT_EVALUATED")
        self.assertIs(view["routeEligible"], False)
        self.assertEqual(view["serviceId"], "blueferry")
        self.assertNotIn("contentAccessEnabled", view)

    def test_normalize_real_upstream_thread_fields_in_stable_oldest_first_order(self):
        view = projection.normalize_threads([thread(messages=[
            message("m2", "second", LATE, outgoing=True),
            message("m1", "first", EARLY),
        ])], profile_id=A)
        self.locked(view)
        self.assertEqual(len(view["conversations"]), 1)
        conversation = view["conversations"][0]
        self.assertEqual(conversation["id"], f"{A}:address:phone:15551111111")
        self.assertEqual(conversation["lastMessage"], "second")
        self.assertEqual(conversation["type"], "direct")
        self.assertEqual(conversation["unreadCount"], 0)
        self.assertTrue(conversation["unreadCountExact"])
        self.assertEqual([m["body"] for m in view["messageSets"][0]["messages"]],
                         ["first", "second"])
        self.assertEqual([m["direction"] for m in view["messageSets"][0]["messages"]],
                         ["incoming", "outgoing"])
        self.assertEqual([m["timestampUnit"] for m in view["messageSets"][0]["messages"]],
                         ["iso8601-offset", "iso8601-offset"])
        self.assertEqual(view["messageSets"][0]["messages"][0]["id"],
                         f"{conversation['id']}:message:m1")
        self.assertEqual(conversation["providerReplyReady"], True)
        self.assertNotIn("sendEnabled", conversation)

    def test_exact_duplicate_handle_dedup_and_conflicting_data_refused(self):
        original = message(handle="h")
        result = projection.normalize_threads(
            [thread(messages=[original, dict(original)])], profile_id=A)
        self.assertEqual(len(result["messageSets"][0]["messages"]), 1)
        invalid = [original, message(handle="h", body="DIFFERENT")]
        with self.assertRaisesRegex(ValueError, "unsupported BlueFerry projection input"):
            projection.normalize_threads([thread(messages=invalid)], profile_id=A)

    def test_unread_is_exact_only_for_complete_history(self):
        unread = message("unread", "unread", read=False)
        complete = thread(messages=[unread], unread=True)
        view = projection.normalize_threads([complete], profile_id=A)
        self.assertEqual(view["conversations"][0]["unreadCount"], 1)
        self.assertTrue(view["conversations"][0]["unreadCountExact"])
        partial = thread(messages=[message()], unread=True, messages_truncated=True)
        v = projection.normalize_threads([partial], profile_id=A)
        self.assertEqual(v["conversations"][0]["unreadCount"], 1)
        self.assertFalse(v["conversations"][0]["unreadCountExact"])
        with self.assertRaises(ValueError):
            projection.normalize_threads([thread(messages=[unread])], profile_id=A)

    def test_group_sender_and_read_only_provider_reply_are_distinct_from_send_authority(self):
        incoming = message(handle="inbound", body="hi")
        incoming["sender"] = "Alex"
        row = thread(key="group:named:friends", is_group=True,
                     reply_ready=False, name="Friends", messages=[incoming])
        result = projection.normalize_threads([row], profile_id=A)
        self.locked(result)
        self.assertEqual(result["conversations"][0]["type"], "group")
        self.assertIs(result["conversations"][0]["providerReplyReady"], False)
        self.assertEqual(result["messageSets"][0]["messages"][0]["senderId"], "Alex")

    def test_profile_scoping_prevents_colliding_native_threads(self):
        inputs = [thread()]
        first = projection.normalize_threads(inputs, profile_id=A)
        second = projection.normalize_threads(inputs, profile_id=B)
        self.assertNotEqual(first["conversations"][0]["id"],
                            second["conversations"][0]["id"])
        self.assertNotEqual(first["messageSets"][0]["messages"][0]["id"],
                            second["messageSets"][0]["messages"][0]["id"])

    def test_missing_handles_or_timezones_are_not_silently_fabricated(self):
        for bad in (
            message(handle=""),
            message(timestamp="2026-11-06T10:00:00"),
            message(timestamp="not a timestamp"),
            message(outgoing=1),
            message(read=0),
            message(body="x" * (projection.MAX_BODY + 1)),
            message(body="bad\x00body"),
        ):
            with self.subTest(invalid=str(list(bad.keys()))):
                with self.assertRaises(ValueError):
                    projection.normalize_threads([thread(messages=[bad])], profile_id=A)

    def test_mixed_duplicate_or_invalid_threads_fail_closed_without_content_in_errors(self):
        private_body = "PRIVATE-SMS-DATA-MUST-NOT-LEAK"
        invalid = [
            "wrong collection",
            [thread(), thread()],
            [thread(key="same"), thread(key="same")],
            [thread(is_group="yes")],
            [thread(messages=[message(body=private_body, handle="")])],
            [thread(name="\x00")],
            [thread(messages_truncated=1)],
            [thread(messages="bad")],
            [thread(key="")],
        ]
        # Two actual *different* threads are valid.
        valid = projection.normalize_threads([thread(key="a"), thread(key="b")], profile_id=A)
        self.assertEqual(len(valid["conversations"]), 2)
        for item in invalid:
            if item == [thread(), thread()]:
                pass
            with self.subTest(item_type=type(item).__name__):
                try:
                    projection.normalize_threads(item, profile_id=A)
                except ValueError as error:
                    self.assertNotIn(private_body, str(error))
                else:
                    self.fail("Invalid native snapshot was accepted")

    def test_empty_snapshot_is_not_the_same_as_permission_or_connection(self):
        view = projection.normalize_threads([], profile_id=A)
        self.locked(view)
        self.assertEqual(view["conversations"], [])
        self.assertEqual(view["messageSets"], [])


class ContactsProjectionTests(unittest.TestCase):
    def test_paged_cards_names_and_epoch_scoped_ids(self):
        result = projection.normalize_contact_page(page(), profile_id=A, daemon_epoch=42)
        self.assertEqual(result["authorization"], "NOT_EVALUATED")
        self.assertEqual(result["daemonEpoch"], "42")
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["contacts"]), 2)
        self.assertEqual(result["contacts"][0]["displayNameInProfile"], "Alex")
        self.assertEqual(result["contacts"][1]["organization"], "Studio")
        self.assertEqual(result["contacts"][0]["nativeCardId"], "card-one")
        self.assertEqual(result["contacts"][0]["id"], f"{A}:42:card-one")
        other = projection.normalize_contact_page(page(), profile_id=A, daemon_epoch=43)
        self.assertNotEqual(result["contacts"][0]["id"], other["contacts"][0]["id"])
        other_phone = projection.normalize_contact_page(page(), profile_id=B, daemon_epoch=42)
        self.assertNotEqual(result["contacts"][0]["id"], other_phone["contacts"][0]["id"])
        self.assertNotIn("conversations", result)

    def test_contact_page_does_not_generate_messages_or_live_access(self):
        view = projection.normalize_contact_page(page(), profile_id=A, daemon_epoch="e-1")
        self.assertEqual(view["execution"], "OFFLINE_PROJECTION_ONLY")
        self.assertFalse(view["routeEligible"])
        self.assertNotIn("contentAccessEnabled", view)
        self.assertNotIn("messages", view)

    def test_wrong_epoch_card_or_page_metadata_refused(self):
        bad = page()
        bad["contacts"].append(dict(bad["contacts"][0]))
        candidates = [bad, {**page(), "contacts": "not a list"},
                      {**page(), "total": 1}, {**page(), "total": True},
                      {**page(), "offset": -1}, {**page(), "query": None}]
        for data in candidates:
            with self.subTest(keys=list(data)):
                with self.assertRaises(ValueError):
                    projection.normalize_contact_page(data, profile_id=A, daemon_epoch=42)
        for epoch in ("", "x" * 65, -1, True):
            with self.assertRaises(ValueError):
                projection.normalize_contact_page(page(), profile_id=A, daemon_epoch=epoch)

    def test_no_side_effect_imports_or_direct_messaging_access(self):
        source = (ROOT / "services/phone/BlueFerrySocialProjection.py").read_text()
        for forbidden in ("import dbus", "import subprocess", "import socket", "os.", "sqlite3",
                          "open(", "Path(", "SendToThread(", "dbus.Interface(",
                          "GetContact(", "print("):
            self.assertNotIn(forbidden, source)
        self.assertIn('"authorization": "NOT_EVALUATED"', source)
        self.assertIn('"routeEligible": False', source)


if __name__ == "__main__":
    unittest.main()
