"""P41b exact-change privacy binding tests, synthetic-only."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))

import PhonePersonalActionCommitmentP41b as C
import PhonePersonalSignedTrustP37 as P37

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
PROFILE2 = "223e4567-e89b-42d3-a456-426614174000"
LOCAL = "ab" * 16
KEY = b"c" * 32

def draft(action="NOTE"):
    return {
        "schema": P37.SCHEMA,
        "action": action,
        "profileId": PROFILE,
        "providerOwner": ":1.123",
        "sessionRef": "session_test_123",
        "snapshotEpoch": 9,
        "selectedCardHmac": "a" * 64,
        "expectedRevision": 2,
        "challengeSha256": "b" * 64,
        "minimumReleaseEpoch": 3,
        "minimumReleaseSequence": 5,
        "requestNonce": "c" * 32,
    }


class ExactEditCommitmentTests(unittest.TestCase):
    def commit(self, action="NOTE", **kw):
        return C.bind_exact_edit(
            master_key=KEY, request_draft=draft(action),
            local_id=None if action == "LINK" else LOCAL,
            **kw,
        )

    def test_note_exact_binding_is_deterministic_and_p37_compatible(self):
        one = self.commit(note="PRIVATE FICTIONAL NOTE 🤖")
        two = self.commit(note="PRIVATE FICTIONAL NOTE 🤖")
        self.assertEqual(one, two)
        self.assertTrue(P37._valid_request(one))
        self.assertEqual(len(one["editHmac"]), 64)
        for secret in ("PRIVATE FICTIONAL NOTE", PROFILE, LOCAL, "example@"):
            self.assertNotIn(secret, one["editHmac"])
        self.assertEqual(set(one), P37.REQ_FIELDS)

    def test_every_signed_request_field_mutation_changes_commitment(self):
        base = draft()
        original = C.bind_exact_edit(
            master_key=KEY, request_draft=base, local_id=LOCAL, note="secret"
        )
        mutations = {
            "profileId": PROFILE2,
            "providerOwner": ":1.456",
            "sessionRef": "session_test_456",
            "snapshotEpoch": 10,
            "selectedCardHmac": "d" * 64,
            "expectedRevision": 3,
            "challengeSha256": "e" * 64,
            "minimumReleaseEpoch": 4,
            "minimumReleaseSequence": 6,
            "requestNonce": "f" * 32,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                changed = {**base, field: value}
                digest = C.bind_exact_edit(
                    master_key=KEY, request_draft=changed,
                    local_id=LOCAL, note="secret"
                )
                self.assertNotEqual(original["editHmac"], digest["editHmac"])
                self.assertTrue(P37._valid_request(digest))

    def test_value_action_local_id_and_key_change_commitment(self):
        first = self.commit(note="first")
        self.assertNotEqual(first["editHmac"], self.commit(note="second")["editHmac"])
        self.assertNotEqual(first["editHmac"], self.commit(note="")["editHmac"])
        self.assertNotEqual(first["editHmac"], C.bind_exact_edit(
            master_key=KEY, request_draft=draft(),
            local_id="cd" * 16, note="first"
        )["editHmac"])
        self.assertNotEqual(first["editHmac"], C.bind_exact_edit(
            master_key=b"d" * 32, request_draft=draft(),
            local_id=LOCAL, note="first"
        )["editHmac"])
        self.assertNotEqual(
            self.commit("FAVORITE", favorite=True)["editHmac"],
            self.commit("FAVORITE", favorite=False)["editHmac"]
        )
        for action, values in (
            ("LINK", {}),
            ("UNLINK", {}),
            ("FAVORITE", {"favorite": True}),
        ):
            with self.subTest(action=action):
                self.assertTrue(P37._valid_request(self.commit(action, **values)))

    def test_action_crossovers_and_missing_edit_values_refuse(self):
        invalid = [
            ("NOTE", {"note": None}),
            ("NOTE", {"note": 42}),
            ("NOTE", {"note": "x" * 4097}),
            ("NOTE", {"note": "nul\x00contact"}),
            ("NOTE", {"favorite": True, "note": "private"}),
            ("FAVORITE", {}),
            ("FAVORITE", {"favorite": 1}),
            ("FAVORITE", {"favorite": False, "note": ""}),
            ("LINK", {"favorite": True}),
            ("LINK", {"note": "private"}),
            ("UNLINK", {"note": ""}),
        ]
        for action, values in invalid:
            with self.subTest(action=action, values=list(values)):
                with self.assertRaisesRegex(
                    C.CommitmentRefused, "^PHONE_EDIT_COMMITMENT_REFUSED$"
                ):
                    self.commit(action, **values)

    def test_invalid_request_private_key_or_local_id_refuse(self):
        base = draft()
        bad = [
            {"master_key": "c" * 32},
            {"master_key": b"x" * 31},
            {"master_key": bytearray(KEY)},
            {"request_draft": {**base, "bogus": True}},
            {"request_draft": {k:v for k,v in base.items() if k != "profileId"}},
            {"request_draft": {**base, "expectedRevision": True}},
            {"request_draft": {**base, "selectedCardHmac": "@" * 64}},
            {"request_draft": {**base, "requestNonce": "g" * 32}},
            {"local_id": "transient-legacy-row-0"},
            {"local_id": PROFILE},
            {"note": "\ud800"},
        ]
        for change in bad:
            with self.subTest(change=list(change)):
                kwargs = dict(master_key=KEY, request_draft=base,
                              local_id=LOCAL, note="private")
                kwargs.update(change)
                with self.assertRaisesRegex(
                    C.CommitmentRefused, "^PHONE_EDIT_COMMITMENT_REFUSED$"
                ):
                    C.bind_exact_edit(**kwargs)

    def test_return_is_copy_without_secret_note_or_local_identifier(self):
        base = draft()
        result = C.bind_exact_edit(
            master_key=KEY, request_draft=base,
            local_id=LOCAL, note="PRIVATE FICTIONAL NOTE"
        )
        base["requestNonce"] = "f" * 32
        self.assertEqual(result["requestNonce"], "c" * 32)
        self.assertNotIn("note", result)
        self.assertNotIn("localId", result)
        self.assertNotIn("masterKey", result)
        self.assertEqual(len(result), len(P37.REQ_FIELDS))

    def test_no_disk_io_keyring_qml_or_production_hook(self):
        source = (ROOT / "services/phone/PhonePersonalActionCommitmentP41b.py").read_text()
        for forbidden in (
            "def main(", "if __name__ ==", "import dbus",
            "import os", "open(", "Path(", "subprocess",
            "secret-tool", "Vault.commit(", "QtQuick", "print(",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("P37._valid_request", source)
        self.assertIn("hmac.new", source)


if __name__ == "__main__":
    unittest.main()
