"""P33 full address rows from an already approved, bounded legacy contact snapshot.

Synthetic data and a local Node VM only. No real BlueFerry, iPhone, D-Bus,
contact store, host access, message send, phone call or clipboard operations.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import BlueFerrySocialProjection as converter

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
JS = ROOT / "services/messaging/adapters/BlueFerryProjectionView.js"
PANE = ROOT / "widgets/messanger/PhonePane.qml"
DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"


def legacy_payload():
    return [
        {"name": "Test Person", "phones": ["+15550001001", "+15550001002"],
         "emails": ["test@example.invalid", "work@example.invalid"]},
        {"name": "Email Only", "phones": [], "emails": ["email@example.invalid"]},
        {"name": "No Addresses", "phones": [], "emails": []},
    ]


def snapshot():
    return converter.normalize_legacy_contact_page(
        legacy_payload(), profile_id=PROFILE, read_epoch="synthetic-read-epoch"
    )


class LegacyAddressRowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if cls.node is None:
            raise AssertionError("Node is required for the actual QML JS parser")

    def parse(self, payload):
        script = r"""
const fs = require("fs"), vm = require("vm");
const scope = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), scope);
const payload = JSON.parse(fs.readFileSync(0,"utf8"));
process.stdout.write(JSON.stringify(scope.contactsView(payload, payload.deviceProfileId)));
"""
        run = subprocess.run(
            [self.node, "-e", script, str(JS)], input=json.dumps(payload),
            capture_output=True, text=True, check=False, timeout=8
        )
        self.assertEqual(run.returncode, 0, run.stderr[:1500])
        return json.loads(run.stdout)

    def test_all_legacy_numbers_emails_survive_two_validated_projections(self):
        data = snapshot()
        self.assertTrue(data["legacyReadOnly"])
        self.assertFalse(data["routeEligible"])
        card, email_only, empty = data["contacts"]
        self.assertEqual(card["phoneCount"], 2)
        self.assertEqual(card["emailCount"], 2)
        self.assertEqual(card["phoneNumbers"], ["+15550001001", "+15550001002"])
        self.assertEqual(card["emailAddresses"],
                         ["test@example.invalid", "work@example.invalid"])
        self.assertEqual(card["primary"], card["phoneNumbers"][0])
        self.assertTrue(card["hasAddressDetails"])
        self.assertNotIn("phoneLabels", card)
        self.assertEqual(email_only["primary"], "email@example.invalid")
        self.assertEqual(email_only["phoneNumbers"], [])
        self.assertEqual(empty["phoneNumbers"], [])
        rows = self.parse(data)
        self.assertEqual(rows[0]["phoneNumbers"], card["phoneNumbers"])
        self.assertEqual(rows[0]["emailAddresses"], card["emailAddresses"])
        self.assertTrue(rows[0]["hasAddressDetails"])
        self.assertNotIn("nativeCardId", rows[0])
        self.assertNotIn("sendEnabled", rows[0])
        self.assertNotIn("phoneLabels", rows[0])
        self.assertEqual(rows[2]["emailAddresses"], [])

    def test_modern_count_only_cards_do_not_invent_addresses(self):
        old = converter.normalize_contact_page(
            {"total": 1, "offset": 0, "query": "", "contacts": [{
                "id": "example", "name": "Example", "organization": "Team",
                "primary": "+15550001003", "phone_count": 2, "email_count": 1,
                "has_photo": False
            }]}, profile_id=PROFILE, daemon_epoch=9
        )
        card = old["contacts"][0]
        self.assertFalse(card["hasAddressDetails"])
        self.assertEqual(card["phoneNumbers"], [])
        self.assertEqual(card["emailAddresses"], [])
        self.assertEqual(card["phoneCount"], 2)
        view = self.parse(old)
        self.assertFalse(view[0]["hasAddressDetails"])
        self.assertEqual(view[0]["phoneNumbers"], [])
        self.assertEqual(view[0]["emailAddresses"], [])

    def test_malformed_legacy_address_data_fails_closed_with_no_private_leak(self):
        for bad in (
            [{"name": "Private", "phones": ["\x00"], "emails": []}],
            [{"name": "Private", "phones": ["+15550001111"] * 65, "emails": []}],
            [{"name": "Private", "phones": ["+15550001111"], "emails": [False]}],
            [{"name": "Private", "phones": [33], "emails": []}],
            [{"name": "Private", "phones": ["+15550001111"], "emails": ["bad\nmail"]}],
        ):
            with self.subTest(error_type=type(bad[0]["phones"]).__name__):
                with self.assertRaises(ValueError) as ctx:
                    converter.normalize_legacy_contact_page(
                        bad, profile_id=PROFILE, read_epoch="fresh")
                self.assertNotIn("Private", str(ctx.exception))

    def test_inconsistent_or_forged_paired_address_fields_are_rejected(self):
        good = snapshot()
        for edit in (
            lambda c: c.update(phoneNumbers=["+15550001001"]),
            lambda c: c.update(emailAddresses=["x@example.invalid"]),
            lambda c: c.update(hasAddressDetails="yes"),
            lambda c: c.update(phoneNumbers=[42, "+15550001002"]),
            lambda c: c.update(phoneNumbers=["\u0000", "+15550001002"]),
            lambda c: c.update(primary="not the first number"),
            lambda c: c.update(hasAddressDetails=False),
        ):
            clone = json.loads(json.dumps(good))
            edit(clone["contacts"][0])
            self.assertIsNone(self.parse(clone))
        old = json.loads(json.dumps(good))
        old["contacts"][0].pop("hasAddressDetails")
        self.assertIsNone(self.parse(old))

    def test_python_normalizer_rejects_bad_arrays_and_incorrect_primary(self):
        base = {
            "total": 1, "offset": 0, "query": "", "contacts": [{
                "id": "c", "name": "Test", "organization": "", "primary": "+15550000001",
                "phone_count": 1, "email_count": 0, "has_photo": False,
                "phone_numbers": ["+15550000001"], "email_addresses": []
            }]
        }
        edits = (
            lambda r: r.pop("email_addresses"),
            lambda r: r.update(phone_numbers=["+15550000001", "+15550000002"]),
            lambda r: r.update(email_addresses=["a@example.invalid"]),
            lambda r: r.update(phone_numbers="not a list"),
            lambda r: r.update(primary="+15559990000"),
            lambda r: r.update(phone_numbers=["bad\tvalue"]),
        )
        for change in edits:
            value = json.loads(json.dumps(base))
            change(value["contacts"][0])
            with self.assertRaises(ValueError):
                converter.normalize_contact_page(
                    value, profile_id=PROFILE, daemon_epoch="fresh")
        self.assertTrue(
            converter.normalize_contact_page(base, profile_id=PROFILE,
                                              daemon_epoch="fresh")["contacts"][0]
            ["hasAddressDetails"]
        )

    def test_contact_screen_rows_are_locked_and_use_existing_call_review_only(self):
        pane = PANE.read_text(encoding="utf-8")
        detail = DETAIL.read_text(encoding="utf-8")
        for required in (
            "signal callNumberRequested(string number)",
            "SAVED PHONE NUMBERS", "SAVED EMAIL ADDRESSES",
            "PHONE // UNLABELED", "EMAIL // UNLABELED",
            "readOnly: true", "selectByMouse: true",
            'label: "MAKE CALL"', "detail.contact.phoneNumbers",
            "detail.contact.emailAddresses",
            "onTriggered: detail.callNumberRequested(",
            "interactive: detail.contact !== null",
        ):
            self.assertIn(required, detail)
        action = pane.split("function openSelectedContactForNumber(raw)", 1)[1].split(
            "function openSelectedContactMessages()", 1)[0]
        for required in (
            'selectedSection !== "CONTACTS"', "selectedPhoneContactCard",
            "card.hasAddressDetails !== true", "Array.isArray(card.phoneNumbers)",
            "card.phoneNumbers.indexOf(raw) < 0",
            'selectedSection = "CALLS";', "phoneDialInput.text = number;",
            "callsConfirmDial = false;", 'callsPendingDial = "";',
        ):
            self.assertIn(required, action)
        self.assertNotIn("requestCallAction(", action)
        self.assertNotIn("phoneCallsActionProcess.command", action)
        self.assertNotIn("savePersonalApproval(", action)
        self.assertIn("onCallNumberRequested: function(number)", pane)
        self.assertIn('label: "REVIEW OUTGOING CALL"', pane)
        self.assertIn('label: "CONFIRM CALL"', pane)
        self.assertIn("sendEnabled: false", pane)
        self.assertNotIn("Process {", detail)


if __name__ == "__main__":
    unittest.main()
