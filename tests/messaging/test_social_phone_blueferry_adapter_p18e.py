"""Synthetic BlueFerry adapter display-parsing tests. No phone/device contact.

The JS module is shared by dormant QML adapter. A Node VM executes the exact
pure functions against actual P18a-converted *invented* records.
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
import BlueFerrySocialProjection as projection  # noqa: E402

JS = ROOT / "services" / "messaging" / "adapters" / "BlueFerryProjectionView.js"
QML = ROOT / "services" / "messaging" / "adapters" / "BlueFerryAdapter.qml"
PANE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
ROUTER = ROOT / "services" / "messaging" / "SocialMessageRouter.qml"
PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"
NODE_RUN = r"""
const fs = require("fs");
const vm = require("vm");
const code = fs.readFileSync(process.argv[1], "utf8");
const args = JSON.parse(fs.readFileSync(0, "utf8"));
const context = vm.createContext({});
vm.runInContext(code, context, {timeout: 1000});
const fn = context[args.method];
if (typeof fn !== "function") throw Error("Missing pure adapter parser");
const output = fn(args.payload, args.profile);
process.stdout.write(JSON.stringify(output) + "\n");
"""


def native_thread():
    return {
        "key": "address:phone:15550001111",
        "name": "Test Contact",
        "is_group": False,
        "reply_ready": False,
        "unread": False,
        "messages_truncated": False,
        "messages": [
            {"handle": "msg2", "body": "Later", "timestamp": "2026-11-06T18:45:01Z",
             "outgoing": True, "read": True, "sender": ""},
            {"handle": "msg1", "body": "Earlier", "timestamp": "2026-11-06T18:45:00Z",
             "outgoing": False, "read": True, "sender": ""},
        ],
    }


def threads():
    return projection.normalize_threads([native_thread()], profile_id=PROFILE)


def cards():
    return projection.normalize_contact_page({
        "total": 1, "offset": 0, "query": "",
        "contacts": [{
            "id": "card-1", "name": "Test Contact", "organization": "Test Org",
            "primary": "contact@example.invalid", "phone_count": 1,
            "email_count": 1, "has_photo": False,
        }],
    }, profile_id=PROFILE, daemon_epoch=13)


class BlueFerryAdapterJavaScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if cls.node is None:
            raise AssertionError("Node JS required to exercise pure QML adapter validator")

    def parse(self, method, payload, profile=PROFILE):
        run = subprocess.run(
            [self.node, "-e", NODE_RUN, str(JS)],
            input=json.dumps({
                "method": method, "payload": payload, "profile": profile,
            }),
            text=True, capture_output=True, timeout=8, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr[:1500])
        return json.loads(run.stdout)

    def test_p18a_threads_match_existing_social_contract(self):
        value = self.parse("messagesView", threads())
        self.assertIsNotNone(value)
        convo, = value["conversations"]
        self.assertEqual(convo["serviceId"], "blueferry")
        self.assertEqual(convo["displayNameInProfile"], "Test Contact")
        self.assertEqual(convo["lastMessage"], "Later")
        self.assertEqual(convo["unreadCount"], 0)
        self.assertEqual(convo["type"], "direct")
        messages = value["messagesById"][convo["id"]]
        self.assertEqual([row["body"] for row in messages], ["Earlier", "Later"])
        self.assertEqual([row["direction"] for row in messages],
                         ["incoming", "outgoing"])
        self.assertTrue(all(row["conversationId"] == convo["id"] for row in messages))
        self.assertTrue(all(row["timestampUnit"] == "iso8601-offset"
                            for row in messages))
        self.assertNotIn("nativeKey", convo)
        self.assertNotIn("read", messages[0])

    def test_p18a_contact_cards_remain_separate_from_message_threads(self):
        result = self.parse("contactsView", cards())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["displayNameInProfile"], "Test Contact")
        self.assertEqual(result[0]["organization"], "Test Org")
        self.assertEqual(result[0]["primary"], "contact@example.invalid")
        self.assertEqual(result[0]["id"], f"{PROFILE}:13:card-1")
        self.assertNotIn("nativeCardId", result[0])
        self.assertNotIn("messages", result[0])

    def test_different_profile_and_unsupported_or_missing_header_rejected(self):
        value = threads()
        wrong = self.parse("messagesView", value, OTHER)
        self.assertIsNone(wrong)
        for key, item in (
            ("schema", "wrong"), ("execution", "UNSAFE"),
            ("serviceId", "telegram"), ("routeEligible", True),
            ("authorization", "GRANTED"), ("deviceProfileId", OTHER),
        ):
            malformed = dict(value)
            malformed[key] = item
            with self.subTest(key=key):
                self.assertIsNone(self.parse("messagesView", malformed))
        self.assertIsNone(self.parse("messagesView", None))
        self.assertIsNone(self.parse("messagesView", cards()))
        self.assertIsNone(self.parse("contactsView", threads()))

    def test_duplicate_messages_malformed_fields_and_order_are_rejected(self):
        value = threads()
        for change in ("duplicate", "wrong-profile", "reverse", "invalid-body",
                       "bad-timestamp", "wrong-direction", "wrong-unit"):
            altered = json.loads(json.dumps(value))
            group = altered["messageSets"][0]
            row = group["messages"][0]
            if change == "duplicate":
                group["messages"].append(dict(row))
            elif change == "wrong-profile":
                row["conversationId"] = OTHER + ":bad"
            elif change == "reverse":
                group["messages"].reverse()
            elif change == "invalid-body":
                row["body"] = "private\u0000body"
            elif change == "bad-timestamp":
                row["sent_at"] = "2026-11-06T18:45:00"
            elif change == "wrong-direction":
                row["direction"] = "maybe"
            else:
                row["timestampUnit"] = "milliseconds"
            with self.subTest(change=change):
                self.assertIsNone(self.parse("messagesView", altered))

    def test_contacts_wrong_epoch_duplicate_or_poisoned_rows_rejected(self):
        value = cards()
        for change in ("bad-epoch", "duplicate", "wrong-profile",
                       "bad-count", "bad-name", "fake-authority"):
            altered = json.loads(json.dumps(value))
            card = altered["contacts"][0]
            if change == "bad-epoch":
                altered["daemonEpoch"] = "14"
            elif change == "duplicate":
                altered["contacts"].append(dict(card))
                altered["total"] = 2
            elif change == "wrong-profile":
                card["deviceProfileId"] = OTHER
            elif change == "bad-count":
                card["phoneCount"] = -1
            elif change == "bad-name":
                card["displayNameInProfile"] = "x" * 257
            else:
                altered["authorization"] = "AUTHENTICATED"
            with self.subTest(change=change):
                self.assertIsNone(self.parse("contactsView", altered))

    def test_bounds_and_no_arbitrary_user_content_on_invalid_type(self):
        value = threads()
        value["conversations"] = value["conversations"] * 65
        self.assertIsNone(self.parse("messagesView", value))
        value = threads()
        value["messageSets"][0]["messages"][0]["body"] = "x" * 16385
        self.assertIsNone(self.parse("messagesView", value))
        value = cards()
        value["contacts"][0]["hasPhoto"] = "true"
        self.assertIsNone(self.parse("contactsView", value))

    def test_scope_helpers_validate_tokens_and_epochs(self):
        for method, valid, invalid in (
            ("validProfile", PROFILE, OTHER.upper()),
            ("validOpaqueContext", "context_1234567890abcdef", "short"),
            ("validDeliveryEpoch", 9, 0),
        ):
            # Inspect pure helper with Node in the exact same VM as validation.
            node = r"""
const fs=require('fs'),vm=require('vm');
const c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),c);
const method=process.argv[2],valid=JSON.parse(process.argv[3]),invalid=JSON.parse(process.argv[4]);
process.stdout.write(JSON.stringify([c[method](valid),c[method](invalid)]));
"""
            run = subprocess.run([self.node,"-e",node,str(JS),method,
                                  json.dumps(valid),json.dumps(invalid)],
                                 capture_output=True,text=True,timeout=8)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout), [True, False])


class BlueFerryAdapterQmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qml = QML.read_text()
        cls.js = JS.read_text()

    def test_stays_independent_of_shared_router_and_phone_pane(self):
        self.assertIn("BlueFerryAdapter", PANE.read_text())
        self.assertNotIn("BlueFerryAdapter", ROUTER.read_text())
        for snippet in (
            'property bool active: false',
            'readonly property string serviceId: "blueferry"',
            'readonly property string backendMode:',
            'readonly property string backendDetail:',
            'readonly property var capabilities:',
            'property var conversations: []',
            'property bool loading: false',
            'property string error: ""',
            'property string selectedConversationId: ""',
            'property var messages: []',
            'property bool messagesLoading: false',
            'property string messagesError: ""',
            'property bool sending: false',
            'property string sendError: ""',
            'property int sendSuccessSerial: 0',
            'function refresh()',
            'function loadMessages(conversationId)',
            'function refreshMessages()',
            'function sendMessage(conversationId, text)',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, self.qml)

    def test_no_private_source_io_or_polling_and_send_remains_disabled(self):
        for forbidden in (
            "Process {", "Timer {", "QtHttp", "XMLHttpRequest", "Quickshell",
            "ListThreads(", "ListContactCards(", "dbus", "systemctl",
            "fetch(", "subprocess", "requestAccessToken", "sendSuccessSerial +=",
            "sendSuccessSerial++", "sendText: true", "liveUpdates: true",
        ):
            self.assertNotIn(forbidden, self.qml)
        self.assertIn("sendText: false", self.qml)
        self.assertIn("return false;", self.qml)
        self.assertIn("sendError = ", self.qml)
        self.assertIn("refresh() {", self.qml)

    def test_context_epoch_stale_reply_and_local_purge_guards(self):
        for phrase in (
            "onActiveChanged:",
            "if (!active)",
            "forgetHostView();",
            "function beginHostView(contextKey, profileId, epoch)",
            "epoch <= _lastEpoch",
            'function dropHostView(contextKey, epoch)',
            "function applyHostProjection(contextKey, epoch, sequence, operation, payload)",
            "contextKey !== _contextKey || epoch !== _contextEpoch",
            "sequence <= _messagesSerial",
            "sequence <= _contactsSerial",
            "Projection.messagesView(payload, _profileId)",
            "Projection.contactsView(payload, _profileId)",
            "messages = [];",
            "contactCards = [];",
            "selectedConversationId = \"\";",
            "messages = _messagesById[conversationId].slice(0);",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.qml)
        self.assertNotIn("grantVerified: true", self.qml)
        self.assertNotIn('backendMode: "READY"', self.qml)

    def test_display_schema_never_calls_it_authorization(self):
        self.assertIn('authorization === "NOT_EVALUATED"', self.js)
        self.assertIn('routeEligible === false', self.js)
        self.assertIn('execution === "OFFLINE_PROJECTION_ONLY"', self.js)
        self.assertIn("not an authentication mechanism or a trusted content endpoint", self.qml.lower())
        self.assertIn("not a durable host purge ack", self.qml.lower())


if __name__ == "__main__":
    unittest.main()
