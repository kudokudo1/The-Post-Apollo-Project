"""Synthetic KDE Connect SMS message normalization tests, no phone content."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import KdeConnectSmsNormalize as sms  # noqa: E402

SCOPE = {"principal_ref": "person-a", "device_ref": "device-a", "line_ref": "line-a"}


def packet(**changes):
    out = {
        "event": 1, "body": "synthetic-test-message",
        "addresses": [{"address": "fixture-recipient"}],
        "date": "1762102000000", "type": 1, "read": True,
        "thread_id": 42, "_id": 71, "sub_id": -1,
    }
    out.update(changes)
    return out


class SmsNormalizationTests(unittest.TestCase):
    def test_inbound_message_matches_social_message_shape(self):
        x = sms.normalize_message(packet(), **SCOPE)
        self.assertEqual(x["serviceId"], "kdeconnect-sms")
        self.assertEqual(x["direction"], "incoming")
        self.assertEqual(x["nativeStatus"], "received")
        self.assertEqual(x["body"], "synthetic-test-message")
        self.assertEqual(x["sent_at"], 1762102000000)
        self.assertEqual(x["timestampUnit"], "unix_ms")
        self.assertEqual(x["id"], "person-a:device-a:line-a:42:71")
        self.assertEqual(x["conversationId"], "person-a:device-a:line-a:42")

    def test_outbound_sent_is_not_delivery_confirmation(self):
        x = sms.normalize_message(packet(type=2), **SCOPE)
        self.assertEqual((x["direction"], x["nativeStatus"]), ("outgoing", "sent"))
        self.assertNotIn("delivered", x)
        self.assertNotIn("sendSuccessSerial", x)

    def test_other_outbound_states_remain_distinct(self):
        for native, state in [(3, "draft"), (4, "outbox"), (5, "failed"), (6, "queued")]:
            with self.subTest(native=native):
                x = sms.normalize_message(packet(type=native), **SCOPE)
                self.assertEqual(x["direction"], "outgoing")
                self.assertEqual(x["nativeStatus"], state)

    def test_stable_provider_native_ids_across_refresh(self):
        a = sms.normalize_message(packet(), **SCOPE)
        b = sms.normalize_message(packet(), **SCOPE)
        self.assertEqual(a["id"], b["id"])

    def test_different_principals_devices_lines_and_threads_never_collide(self):
        ids = []
        for kwargs, native in [
            (SCOPE, packet()),
            ({**SCOPE, "principal_ref": "person-b"}, packet()),
            ({**SCOPE, "device_ref": "device-b"}, packet()),
            ({**SCOPE, "line_ref": "business-line"}, packet()),
            (SCOPE, packet(thread_id=43)),
            (SCOPE, packet(_id=72)),
        ]:
            ids.append(sms.normalize_message(native, **kwargs)["id"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_nontext_event_rejected_instead_of_fabricating_body(self):
        for event in [0, 2, 4, 5, 7, -1]:
            with self.subTest(event=event):
                with self.assertRaises(ValueError):
                    sms.normalize_message(packet(event=event), **SCOPE)

    def test_group_message_requires_real_multiple_participants(self):
        x = sms.normalize_message(packet(event=3, addresses=[
            {"address": "fixture-sender"}, {"address": "fixture-member"},
        ]), **SCOPE)
        self.assertTrue(x["isGroup"])
        self.assertNotIn("fixture-sender", str({k:v for k,v in x.items() if k!="body"}))
        with self.assertRaises(ValueError):
            sms.normalize_message(packet(event=3), **SCOPE)
        with self.assertRaises(ValueError):
            sms.normalize_message(packet(event=1, addresses=[
                {"address": "one"}, {"address": "two"},
            ]), **SCOPE)

    def test_address_contents_never_output(self):
        x = sms.normalize_message(packet(addresses=[
            {"address": "sensitive-fake-recipient@example.invalid"},
        ]), **SCOPE)
        self.assertNotIn("sensitive-fake-recipient", str(x))

    def test_attachment_content_ignored_even_if_present(self):
        x = sms.normalize_message(packet(attachments=[{
            "part_id": 2, "mime_type": "image/png",
            "encoded_thumbnail": "hidden-base64-fixture",
        }]), **SCOPE)
        self.assertTrue(x["hasAttachments"])
        self.assertNotIn("hidden-base64-fixture", str(x))
        self.assertNotIn("attachmentUrls", x)

    def test_read_state_accepts_bool_and_zero_one_only(self):
        for value, expected in [(True, True), (False, False), (1, True), (0, False)]:
            with self.subTest(value=value):
                self.assertEqual(sms.normalize_message(packet(read=value), **SCOPE)["read"], expected)
        for bad in [2, -1, "true", None, 0.0]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    sms.normalize_message(packet(read=bad), **SCOPE)

    def test_timestamp_accepts_decimal_string_or_int(self):
        self.assertEqual(
            sms.normalize_message(packet(date=1762102000000), **SCOPE)["sent_at"], 1762102000000
        )
        self.assertEqual(
            sms.normalize_message(packet(date="1762102000000"), **SCOPE)["sent_at"], 1762102000000
        )

    def test_malformed_native_numbers_fail_closed(self):
        for key in ["date", "thread_id", "_id"]:
            for bad in [True, 0, -1, "1.5", "01", "nan", 1.5, 2 ** 75]:
                with self.subTest(key=key, bad=bad):
                    with self.assertRaises(ValueError):
                        sms.normalize_message(packet(**{key: bad}), **SCOPE)

    def test_native_signed_integer_widths(self):
        for field, value in [
            ("date", 2 ** 63), ("thread_id", 2 ** 63), ("_id", 2 ** 31),
        ]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    sms.normalize_message(packet(**{field: value}), **SCOPE)

    def test_invalid_type_does_not_claim_incoming_or_outgoing(self):
        for bad in [0, 7, True, "sent", None]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    sms.normalize_message(packet(type=bad), **SCOPE)

    def test_untrusted_native_sim_id_never_changes_line_scope(self):
        a = sms.normalize_message(packet(sub_id=1), **SCOPE)
        b = sms.normalize_message(packet(sub_id=2), **SCOPE)
        self.assertEqual(a["conversationId"], b["conversationId"])
        self.assertNotIn("sub_id", a)
        for bad in ["invalid", 1.0, True]:
            with self.assertRaises(ValueError):
                sms.normalize_message(packet(sub_id=bad), **SCOPE)

    def test_empty_or_oversized_body_rejected(self):
        for body in ["", "x" * 16385, None, b"bytes"]:
            with self.subTest(body_type=str(type(body))):
                with self.assertRaises(ValueError):
                    sms.normalize_message(packet(body=body), **SCOPE)

    def test_reject_malformed_addresses_or_excessive_group(self):
        for addresses in [[], "value", [""], [{"raw": "other"}],
                          [{"address": ""}], [{"address": 1}],
                          [{"address": "a"}] * 25]:
            with self.subTest(category=str(type(addresses))):
                with self.assertRaises(ValueError):
                    sms.normalize_message(packet(addresses=addresses), **SCOPE)

    def test_reject_unknown_fields_including_fake_secrets(self):
        raw = packet(token="no-token", password="no-secret")
        with self.assertRaises(ValueError):
            sms.normalize_message(raw, **SCOPE)
        raw = packet()
        del raw["body"]
        with self.assertRaises(ValueError):
            sms.normalize_message(raw, **SCOPE)

    def test_invalid_scope_rejected_before_processing_private_message(self):
        for change in [
            {"principal_ref": "../other"}, {"device_ref": "wrong:device"},
            {"line_ref": ""}, {"principal_ref": None}
        ]:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    sms.normalize_message(packet(), **{**SCOPE, **change})

    def test_chronological_sort_when_packet_order_is_reversed(self):
        raw = [packet(_id=73, date=1762102003000),
               packet(_id=72, date=1762102002000),
               packet(_id=71, date=1762102001000)]
        out = sms.normalize_conversation(raw, **SCOPE)
        self.assertEqual([x["id"].split(":")[-1] for x in out], ["71", "72", "73"])
        self.assertEqual([x["sent_at"] for x in out], sorted(x["sent_at"] for x in out))

    def test_duplicate_exact_event_is_idempotent(self):
        raw = packet()
        out = sms.normalize_conversation([raw, deepcopy(raw)], **SCOPE)
        self.assertEqual(len(out), 1)

    def test_conflicting_message_ids_rejected_not_overwritten(self):
        with self.assertRaises(ValueError):
            sms.normalize_conversation([packet(body="first"), packet(body="second")], **SCOPE)

    def test_mixed_threads_rejected(self):
        with self.assertRaises(ValueError):
            sms.normalize_conversation([packet(thread_id=1), packet(thread_id=2)], **SCOPE)

    def test_collection_is_bounded(self):
        with self.assertRaises(ValueError):
            sms.normalize_conversation([packet(_id=i+1) for i in range(129)], **SCOPE)
        with self.assertRaises(ValueError):
            sms.normalize_conversation("not-a-list", **SCOPE)

    def test_empty_batch_is_not_an_error_or_connection_proof(self):
        self.assertEqual(sms.normalize_conversation([], **SCOPE), [])

    def test_no_io_logging_credential_or_send_methods(self):
        # The source deliberately has no side effects; this suite does not
        # run a backend, and returned messages are only synthetic fixtures.
        text = (ROOT / "services" / "phone" / "KdeConnectSmsNormalize.py").read_text()
        for forbidden in ["subprocess", "socket", "dbus", "logging.", "print(", "sendSms(", "open("]:
            with self.subTest(forbidden=forbidden):
                if forbidden != "dbus":  # docstrings mention QDBusArgument, intentionally
                    self.assertNotIn(forbidden, text)
        self.assertFalse(hasattr(sms, "sendMessage"))


if __name__ == "__main__":
    unittest.main()
