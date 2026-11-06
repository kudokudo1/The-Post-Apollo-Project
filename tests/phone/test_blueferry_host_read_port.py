"""P18c test-only host callbacks prove a bounded provider read-port contract.

There is no real authenticated host or private message read in this suite.
All records are invented, and the release callback is merely a test probe.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
module = importlib.import_module("BlueFerryHostReadPort")
PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"
OWNER = ":1.99"
TIMESTAMP = "2026-11-06T16:02:00Z"


def status(**changes):
    record = {"api_version": 2, "daemon": True, "phone_profile_id": PROFILE,
              "map": True, "pbap": True, "contact_card_count": 1,
              "contact_card_epoch": 4}
    record.update(changes)
    return record


def threads():
    return [{
        "key": "address:phone:15551234567", "name": "Example",
        "is_group": False, "reply_ready": False, "unread": False,
        "messages_truncated": False, "messages": [
            {"handle": "msg:1", "body": "synthetic private body",
             "timestamp": TIMESTAMP, "outgoing": False,
             "read": True, "sender": ""},
        ],
    }]


def cards():
    return {"contacts": [{
        "id": "contact-1", "name": "Example", "organization": "",
        "primary": "invented@example.invalid", "phone_count": 0,
        "email_count": 1, "has_photo": False,
    }], "total": 1, "offset": 0, "query": ""}


class FakeSource:
    def __init__(self, *, owner=OWNER, statuses=None, threads_data=None,
                 cards_data=None):
        self._owner = owner
        self.statuses = list(statuses if statuses is not None else [status(), status()])
        self.thread_result = threads_data if threads_data is not None else threads()
        self.card_result = cards_data if cards_data is not None else cards()
        self.calls = []
        self.owner_sequence = None

    def owner(self):
        self.calls.append("owner")
        if self.owner_sequence is not None:
            return next(self.owner_sequence)
        return self._owner

    def status(self, owner):
        self.calls.append(("status", owner))
        return self.statuses.pop(0)

    def threads(self, owner):
        self.calls.append(("threads", owner))
        return self.thread_result

    def contact_cards(self, owner):
        self.calls.append(("cards", owner))
        return self.card_result


class HostPortTests(unittest.TestCase):
    def invoke(self, source, *, operation="messages.read", profile=PROFILE,
               guard=None, release=None):
        host_guard = guard if guard is not None else mock.Mock(return_value=True)
        host_release = release if release is not None else mock.Mock(return_value=True)
        reply = module.read_for_trusted_host(
            operation=operation, profile_id=profile, source=source,
            host_guard=host_guard, host_release=host_release,
        )
        self.assertEqual(reply["schema"], module.SCHEMA)
        self.assertFalse(reply["contentInResponse"])
        self.assertEqual(reply["authorization"], "HOST_OWNED_UNVERIFIED")
        self.assertEqual(set(reply), {
            "schema", "execution", "state", "contentInResponse", "authorization",
        })
        self.assertNotIn("synthetic", str(reply))
        self.assertNotIn(PROFILE, str(reply))
        return reply, host_guard, host_release

    def test_messages_read_pins_owner_and_only_releases_via_host_callback(self):
        source = FakeSource()
        result, guard, release = self.invoke(source)
        self.assertEqual(result["state"], "HOST_HANDOFF_REPORTED")
        self.assertEqual(guard.call_count, 2)
        self.assertEqual(release.call_count, 1)
        self.assertEqual(source.calls, [
            "owner", ("status", OWNER), ("threads", OWNER),
            "owner", ("status", OWNER),
        ])
        op, profile, owner, projection = release.call_args.args
        self.assertEqual((op, profile, owner), ("messages.read", PROFILE, OWNER))
        self.assertEqual(projection["authorization"], "NOT_EVALUATED")
        self.assertEqual(projection["messageSets"][0]["messages"][0]["body"],
                         "synthetic private body")

    def test_contacts_read_pins_epoch_and_does_not_read_messages(self):
        source = FakeSource()
        result, guard, release = self.invoke(source, operation="contacts.read")
        self.assertEqual(result["state"], "HOST_HANDOFF_REPORTED")
        self.assertEqual(source.calls, [
            "owner", ("status", OWNER), ("cards", OWNER),
            "owner", ("status", OWNER),
        ])
        snapshot = release.call_args.args[3]
        self.assertEqual(snapshot["daemonEpoch"], "4")
        self.assertEqual(snapshot["contacts"][0]["primary"],
                         "invented@example.invalid")
        self.assertEqual(snapshot["contacts"][0]["id"],
                         f"{PROFILE}:4:contact-1")

    def test_guard_denied_before_read_or_after_read_never_releases(self):
        for flags in ([False], [True, False]):
            source = FakeSource()
            guard = mock.Mock(side_effect=flags)
            result, _, release = self.invoke(source, guard=guard)
            self.assertEqual(result["state"], "HOST_DENIED")
            release.assert_not_called()
            if flags == [False]:
                self.assertEqual(source.calls, ["owner"])

    def test_precondition_failures_never_touch_source(self):
        for op, profile in (
            ("messages.send", PROFILE), ("contacts.write", PROFILE),
            ("messages.read", "fake"), ("messages.read", OTHER.upper()),
        ):
            src = FakeSource()
            result, _, release = self.invoke(src, operation=op, profile=profile)
            self.assertEqual(result["state"], "REFUSED")
            self.assertEqual(src.calls, [])
            release.assert_not_called()

    def test_owner_disappears_or_is_replaced_mid_read(self):
        for prior, later in (("", OWNER), ("io.weirdware.BlueFerry", OWNER),
                             (OWNER, ":1.101"), (OWNER, "")):
            with self.subTest(prior=prior,later=later):
                source = FakeSource(owner=OWNER)
                source.owner_sequence = iter([prior, later])
                result, _, release = self.invoke(source)
                self.assertEqual(result["state"],
                                 "PROVIDER_UNAVAILABLE" if prior != OWNER
                                 else "PROVIDER_CHANGED")
                release.assert_not_called()

    def test_active_profile_change_or_capability_drop_blocks_release(self):
        variants = (
            [status(phone_profile_id=OTHER), status()],
            [status(), status(phone_profile_id=OTHER)],
            [status(map=False), status()],
            [status(), status(map=False)],
            [status(api_version=3), status()],
        )
        for seq in variants:
            with self.subTest(seq=seq):
                source = FakeSource(statuses=seq)
                result, _, release = self.invoke(source)
                self.assertIn(result["state"], {"PROVIDER_UNAVAILABLE", "PROVIDER_CHANGED"})
                release.assert_not_called()

    def test_contact_epoch_change_blocks_releasing_stale_contact_ids(self):
        source = FakeSource(statuses=[status(contact_card_epoch=4),
                                      status(contact_card_epoch=5)])
        result, _, release = self.invoke(source, operation="contacts.read")
        self.assertEqual(result["state"], "PROVIDER_CHANGED")
        release.assert_not_called()

    def test_contact_capability_and_epoch_are_required(self):
        for bad in (
            status(pbap=False), status(contact_card_epoch=None),
            status(contact_card_epoch=True), status(contact_card_count="1"),
        ):
            source = FakeSource(statuses=[bad, status()])
            result, _, release = self.invoke(source, operation="contacts.read")
            self.assertEqual(result["state"], "PROVIDER_UNAVAILABLE")
            release.assert_not_called()

    def test_host_release_failure_never_claims_delivery(self):
        source = FakeSource()
        result, _, release = self.invoke(source, release=mock.Mock(return_value=False))
        self.assertEqual(result["state"], "HOST_RELEASE_REFUSED")
        release.assert_called_once()
        source = FakeSource()
        result, _, release = self.invoke(
            source, release=mock.Mock(side_effect=RuntimeError("synthetic private body"))
        )
        self.assertEqual(result["state"], "PROVIDER_UNAVAILABLE")
        self.assertNotIn("synthetic", str(result))

    def test_malformed_private_payload_never_reaches_release_callback(self):
        bad = threads()
        bad[0]["messages"][0]["timestamp"] = "wrong"
        source = FakeSource(threads_data=bad)
        result, _, release = self.invoke(source)
        self.assertEqual(result["state"], "PROVIDER_UNAVAILABLE")
        release.assert_not_called()

    def test_module_import_has_no_cli_or_automatic_read(self):
        source = (ROOT / "services/phone/BlueFerryHostReadPort.py").read_text()
        self.assertNotIn('if __name__ == "__main__"', source)
        self.assertNotIn("print(", source)
        for forbidden in ("SendToThread(", "MarkThreadRead(", "GetContact(",
                          "GetContactPhoto(", "bluetoothctl", "systemctl start",
                          "subprocess.Popen(", "socket.listen("):
            self.assertNotIn(forbidden, source)
        self.assertIn('get_object(owner, OBJECT, introspect=False)', source)
        self.assertIn("get_name_owner(SERVICE)", source)


class DbusiportTests(unittest.TestCase):
    def test_owner_bound_reads_use_expected_blueferry_dbus_methods(self):
        import json

        class Session:
            def __init__(self):
                self.actions=[]
            def name_has_owner(self, name):
                self.actions.append(("has", name))
                return name == module.SERVICE
            def get_name_owner(self, name):
                self.actions.append(("owner", name))
                return OWNER
            def get_object(self, name, object_path, introspect=False):
                self.actions.append(("get", name, object_path, introspect))
                return "proxy"

        class Interface:
            def GetStatus(self, **kwargs):
                self.calls.append(("status", kwargs))
                return json.dumps(status())
            def ListThreads(self, limit, **kwargs):
                self.calls.append(("threads", limit, kwargs))
                return json.dumps(threads())
            def ListContactCards(self, offset, limit, query, **kwargs):
                self.calls.append(("cards", offset, limit, query, kwargs))
                return json.dumps(cards())

        iface = Interface()
        iface.calls=[]
        class Dbus:
            @staticmethod
            def UInt32(value):
                return value
            @staticmethod
            def Interface(proxy, name):
                self_obj.assertEqual(proxy, "proxy")
                self_obj.assertEqual(name, module.INTERFACE)
                return iface
        self_obj=self
        bus=Session()
        source=module.UniqueOwnerBlueFerrySource(dbus_api=Dbus, session_bus=bus)
        self.assertEqual(source.owner(), OWNER)
        self.assertEqual(source.status(OWNER)["phone_profile_id"], PROFILE)
        self.assertEqual(len(source.threads(OWNER)), 1)
        self.assertEqual(source.contact_cards(OWNER)["total"], 1)
        self.assertEqual([x[0] for x in iface.calls],
                         ["status", "threads", "cards"])
        for action in bus.actions:
            if action[0] == "get":
                self.assertEqual(action[1], OWNER)
                self.assertFalse(action[3])
        self.assertNotIn(("get", module.SERVICE, module.OBJECT, False), bus.actions)

    def test_unexpected_provider_response_is_rejected(self):
        class Session:
            def name_has_owner(self, _):
                return True
            def get_name_owner(self, _):
                return OWNER
            def get_object(self, *_, **__):
                return "proxy"
        class Interface:
            def GetStatus(self, **kwargs):
                return "{invalid"
        class Dbus:
            Interface = staticmethod(lambda *_: Interface())
        source=module.UniqueOwnerBlueFerrySource(
            dbus_api=Dbus, session_bus=Session()
        )
        with self.assertRaises(ValueError):
            source.status(OWNER)


if __name__ == "__main__":
    unittest.main()
