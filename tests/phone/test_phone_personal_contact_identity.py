"""P34: synthetic fail-closed Personal contact match / metadata policy tests.

No disk, BlueFerry, real contacts, contact notes, keyring, wallet, QML, calls,
messages or provider mutation. No stable BlueFerry IDs are persisted.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalContactIdentity as identity

PROFILE_A = "123e4567-e89b-42d3-a456-426614174000"
PROFILE_B = "223e4567-e89b-42d3-a456-426614174000"
SECRET_A = b"1" * 32
SECRET_B = b"2" * 32


def card(name="Jordan Test", phones=None, emails=None, profile=PROFILE_A,
         epoch="epoch-one", provider_id="legacy-row-0"):
    phones = ["+1 (555) 000-1001"] if phones is None else phones
    emails = ["jordan@example.invalid"] if emails is None else emails
    return {
        "id": f"{profile}:{epoch}:{provider_id}",
        "deviceProfileId": profile,
        "serviceId": "blueferry",
        "displayNameInProfile": name,
        "hasAddressDetails": True,
        "phoneNumbers": phones,
        "emailAddresses": emails,
        "phoneCount": len(phones),
        "emailCount": len(emails),
    }


class ContactIdentityTests(unittest.TestCase):
    def setUp(self):
        self.first = card()
        self.all_cards = [self.first]
        self.doc = identity.empty_document()

    def assess(self, item=None, rows=None, profile=PROFILE_A, secret=SECRET_A):
        item = self.first if item is None else item
        return identity.assess(item, self.all_cards if rows is None else rows,
                               profile, secret)

    def make_link(self):
        return identity.link(
            self.doc, self.first, self.all_cards, PROFILE_A, SECRET_A,
            user_confirmed=True, create_id=lambda: uuid.UUID(int=1)
        )

    def test_new_document_is_empty_and_schema_strict(self):
        self.assertTrue(identity.valid_document(self.doc))
        self.assertEqual(self.doc["entries"], [])
        self.assertEqual(self.doc["revision"], 0)
        for change in (
            lambda x: x.update(schema="unknown"),
            lambda x: x.update(version=1),
            lambda x: x.update(revision=True),
            lambda x: x.update(unknown="extra"),
            lambda x: x.update(entries="no"),
            lambda x: x.update(revision=-1),
        ):
            other = deepcopy(self.doc)
            change(other)
            self.assertFalse(identity.valid_document(other))

    def test_address_order_formatting_and_fresh_epoch_do_not_change_candidate(self):
        first = card(phones=["+1 (555) 000-1001", "+15550001002"],
                     emails=["jordan@example.invalid", "work@EXAMPLE.invalid"])
        second = card(name="  JORDAN  TEST  ",
                      phones=["+15550001002", "+1-555-000-1001"],
                      emails=["work@example.invalid", "jordan@example.invalid"],
                      epoch="another-epoch", provider_id="legacy-row-82")
        a = identity.assess(first, [first], PROFILE_A, SECRET_A)
        b = identity.assess(second, [second], PROFILE_A, SECRET_A)
        self.assertTrue(a["ok"])
        self.assertEqual(a["matchProof"], b["matchProof"])
        self.assertNotIn(first["id"], json.dumps(a))
        self.assertNotIn(first["phoneNumbers"][0], json.dumps(a))

    def test_profile_secret_name_and_address_changes_must_not_auto_link(self):
        original = self.assess()
        self.assertTrue(original["ok"])
        for item, profile, secret in (
            (card(profile=PROFILE_B), PROFILE_B, SECRET_A),
            (self.first, PROFILE_A, SECRET_B),
            (card(name="Jordan Different"), PROFILE_A, SECRET_A),
            (card(phones=["+15550009999"]), PROFILE_A, SECRET_A),
        ):
            other = identity.assess(item, [item], profile, secret)
            self.assertTrue(other["ok"])
            self.assertNotEqual(original["matchProof"], other["matchProof"])

    def test_no_details_or_no_addresses_never_get_durable_identity(self):
        for value in (
            {**self.first, "hasAddressDetails": False},
            card(phones=[], emails=[]),
            {**self.first, "phoneCount": 8},
            {**self.first, "deviceProfileId": PROFILE_B},
            {**self.first, "serviceId": "telegram"},
            {**self.first, "emailAddresses": ["bad-address"]},
            card(phones=["+15550001", "+1 5550001"]),
            card(emails=["a@example.invalid", "a@EXAMPLE.invalid"]),
        ):
            result = identity.assess(value, [value], PROFILE_A, SECRET_A)
            self.assertEqual(result["ok"], False)
            self.assertNotIn("phoneNumbers", result)
            self.assertNotIn("emailAddresses", result)

    def test_ambiguous_candidates_fail_closed_in_current_snapshot(self):
        duplicate = card(epoch="new-snapshot", provider_id="legacy-row-6")
        self.assertEqual(
            self.assess(rows=[self.first, duplicate])["reason"], "AMBIGUOUS_CONTACT")
        self.assertEqual(
            self.assess(rows=[card(name="Other Person")])["reason"],
            "NOT_IN_CURRENT_SNAPSHOT"
        )
        self.assertEqual(self.assess(rows=[self.first] * 101)["reason"],
                         "INVALID_SNAPSHOT")

    def test_read_epoch_id_is_never_used_for_matching(self):
        second = card(epoch="fresh-read", provider_id="legacy-row-99")
        a = self.assess()
        b = identity.assess(second, [second], PROFILE_A, SECRET_A)
        self.assertEqual(a["matchProof"], b["matchProof"])
        self.assertNotIn("legacy-row-", json.dumps(a))
        self.assertNotIn("epoch-one", json.dumps(a))

    def test_explicit_link_creates_opaque_id_without_modifying_input(self):
        denied = identity.link(
            self.doc, self.first, self.all_cards, PROFILE_A, SECRET_A,
            user_confirmed=False
        )
        self.assertEqual(denied["reason"], "CONFIRMATION_REQUIRED")
        self.assertEqual(self.doc["entries"], [])
        created = self.make_link()
        self.assertTrue(created["ok"])
        self.assertEqual(created["localId"], "0" * 31 + "1")
        self.assertEqual(created["document"]["revision"], 1)
        self.assertTrue(identity.valid_document(created["document"]))
        self.assertEqual(self.doc["entries"], [])
        saved = created["document"]["entries"][0]
        self.assertEqual(set(saved), {
            "localId", "profileId", "matchProof", "favorite", "note"
        })
        self.assertEqual(saved["favorite"], False)
        self.assertEqual(saved["note"], "")
        self.assertNotIn("Jordan", json.dumps(saved))
        self.assertNotIn("+1555", json.dumps(saved))
        self.assertNotIn("legacy-row", json.dumps(saved))
        self.assertNotIn("epoch-", json.dumps(saved))

    def test_link_resolves_only_unique_same_profile_current_snapshot(self):
        created = self.make_link()
        doc = created["document"]
        other = card(epoch="another-read", provider_id="legacy-row-33")
        resolved = identity.resolve(doc, other, [other], PROFILE_A, SECRET_A)
        self.assertEqual(resolved, {
            "ok": True, "status": "LINKED", "localId": created["localId"]
        })
        self.assertEqual(identity.resolve(doc, card(name="Not Same"), [
            card(name="Not Same")], PROFILE_A, SECRET_A)["status"], "NOT_LINKED")
        self.assertEqual(identity.resolve(doc, self.first,
                                          [self.first, other],
                                          PROFILE_A, SECRET_A)["reason"],
                         "AMBIGUOUS_CONTACT")
        self.assertEqual(identity.link(
            doc, other, [other], PROFILE_A, SECRET_A, user_confirmed=True
        )["reason"], "ALREADY_LINKED")

    def test_favorite_revision_change_is_explicit_and_in_memory_only(self):
        created = self.make_link()
        doc = created["document"]
        denied = identity.edit(doc, created["localId"], doc["revision"],
                               favorite=True, user_confirmed=False)
        self.assertEqual(denied["reason"], "CONFIRMATION_REQUIRED")
        result = identity.edit(doc, created["localId"], doc["revision"],
                               favorite=True, user_confirmed=True)
        self.assertTrue(result["ok"])
        self.assertTrue(result["changed"])
        self.assertEqual(result["document"]["revision"], 2)
        self.assertTrue(result["document"]["entries"][0]["favorite"])
        self.assertFalse(doc["entries"][0]["favorite"])
        self.assertEqual(identity.edit(
            doc, created["localId"], 0, favorite=True,
            user_confirmed=True)["reason"], "STALE_OR_INVALID_DOCUMENT")
        no_op = identity.edit(
            result["document"], created["localId"], 2,
            favorite=True, user_confirmed=True
        )
        self.assertTrue(no_op["ok"])
        self.assertFalse(no_op["changed"])

    def test_note_requires_explicit_intent_and_will_not_leak_on_resolve(self):
        created = self.make_link()
        doc = created["document"]
        updated = identity.edit(doc, created["localId"], 1, note="private note",
                                user_confirmed=True)
        self.assertTrue(updated["ok"])
        self.assertEqual(updated["document"]["entries"][0]["note"], "private note")
        resolved = identity.resolve(
            updated["document"], self.first, self.all_cards, PROFILE_A, SECRET_A
        )
        self.assertNotIn("private note", json.dumps(resolved))
        self.assertEqual(
            identity.edit(doc, created["localId"], 1,
                          note="\x00bad", user_confirmed=True)["reason"],
            "INVALID_EDIT"
        )
        self.assertEqual(
            identity.edit(doc, created["localId"], 1,
                          note="n" * (identity.MAX_NOTE + 1),
                          user_confirmed=True)["reason"], "INVALID_EDIT"
        )

    def test_delete_binding_really_deletes_notes_and_favorite(self):
        created = self.make_link()
        doc = created["document"]
        fav = identity.edit(doc, created["localId"], doc["revision"],
                            favorite=True, note="private note", user_confirmed=True)
        doc2 = fav["document"]
        self.assertEqual(identity.unlink(doc2, created["localId"], 2,
                                         user_confirmed=False)["reason"],
                         "CONFIRMATION_REQUIRED")
        removed = identity.unlink(doc2, created["localId"], 2,
                                  user_confirmed=True)
        self.assertEqual(removed["document"]["entries"], [])
        self.assertEqual(removed["document"]["revision"], 3)
        self.assertTrue(doc2["entries"][0]["favorite"])
        self.assertNotIn("private note", json.dumps(removed["document"]))

    def test_collision_and_invalid_changes_are_rejected(self):
        first = self.make_link()
        doc = first["document"]
        extra = card(name="Other", phones=["+15550001111"], emails=[])
        collision = identity.link(
            doc, extra, [extra], PROFILE_A, SECRET_A,
            user_confirmed=True, create_id=lambda: uuid.UUID(int=1)
        )
        self.assertEqual(collision["reason"], "IDENTITY_COLLISION")
        invalid = deepcopy(doc)
        invalid["entries"].append(deepcopy(invalid["entries"][0]))
        self.assertFalse(identity.valid_document(invalid))
        for kwargs in (
            {"favorite": "true"}, {"note": True},
            {"favorite": None, "note": None},
        ):
            self.assertEqual(identity.edit(
                doc, first["localId"], 1, user_confirmed=True, **kwargs
            )["reason"], "INVALID_EDIT")

    def test_code_has_no_storage_provider_call_or_implicit_release(self):
        source = (ROOT / "services/phone/PhonePersonalContactIdentity.py").read_text()
        for forbidden in (
            "import dbus", "import subprocess", "import socket", "sqlite3",
            "open(", "Path(", "FileView", "Quickshell",
            "sendMessage(", "requestCallAction(", "ListContacts(", "GetModems(",
            "secret-tool", "keyring.get_password", "write_text(", "print(",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("hmac.new(secret, material, hashlib.sha256)", source)
        self.assertIn('"CONFIRMATION_REQUIRED"', source)


if __name__ == "__main__":
    unittest.main()
