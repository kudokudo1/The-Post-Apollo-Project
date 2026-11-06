"""P18a BlueFerry phone records fit existing Social field names, without a live route."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
converter = importlib.import_module("BlueFerrySocialProjection")


class SocialPhoneProjectionContractTests(unittest.TestCase):
    def test_conversation_and_message_contract_fields(self):
        profile = "123e4567-e89b-42d3-a456-426614174000"
        native = [{
            "key": "address:phone:15550001111",
            "name": "Person",
            "is_group": False,
            "reply_ready": False,
            "unread": True,
            "messages_truncated": False,
            "messages": [{
                "handle": "stable-message-handle",
                "body": "example body",
                "timestamp": "2026-11-06T12:00:00+00:00",
                "outgoing": False,
                "read": False,
                "sender": "",
            }],
        }]
        out = converter.normalize_threads(native, profile_id=profile)
        convo, = out["conversations"]
        msg, = out["messageSets"][0]["messages"]
        for field in ("id", "serviceId", "type", "displayNameInProfile",
                      "lastMessage", "unreadCount"):
            self.assertIn(field, convo)
        for field in ("id", "conversationId", "body", "direction", "sent_at"):
            self.assertIn(field, msg)
        self.assertEqual(out["serviceId"], "blueferry")
        self.assertEqual(convo["serviceId"], "blueferry")
        self.assertEqual(msg["conversationId"], convo["id"])
        self.assertEqual(msg["direction"], "incoming")
        self.assertIs(convo["providerReplyReady"], False)
        self.assertFalse(out["routeEligible"])
        self.assertEqual(out["authorization"], "NOT_EVALUATED")

    def test_existing_social_pane_remains_closed_until_a_real_host_is_reviewed(self):
        pane = (ROOT / "widgets/messanger/PhonePane.qml").read_text()
        self.assertIn("    ContactList {", pane)
        self.assertIn("    ChatFeed {", pane)
        self.assertIn("phoneReadAdapter.conversations : []", pane)
        self.assertIn("phoneReadAdapter.messages : []", pane)
        self.assertIn("sendEnabled: false", pane)
        self.assertNotIn("BlueFerrySocialProjection.py", pane)
        self.assertIn("Social phone link: NOT VERIFIED", pane)

    def test_cross_service_id_and_native_timestamp_are_not_redefined(self):
        spec = (ROOT / "services/messaging/ADAPTER-CONTRACT.md").read_text()
        self.assertIn("(serviceId, native conversation id)", spec)
        self.assertIn("Timestamp unit is not", spec)
        self.assertIn('SERVICE_ID = "blueferry"', (ROOT / "services/phone/BlueFerrySocialProjection.py").read_text())
        self.assertIn("iso8601-offset", (ROOT / "services/phone/BlueFerrySocialProjection.py").read_text())


if __name__ == "__main__":
    unittest.main()
