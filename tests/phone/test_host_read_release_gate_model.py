"""P18d in-process release/cancel model, with fake host and BlueFerry only.

These tests do NOT authenticate a real desktop session or authorize access to
an iPhone. They exercise callback ordering and scope continuity only.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
from threading import Event, Thread
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))

from HostReadReleaseGateModel import (  # noqa: E402
    HostAssertedPhoneScope, HostReadReleaseGateModel, _snapshot_matches,
)
from BlueFerryHostReadPort import read_for_trusted_host  # noqa: E402
from BlueFerrySocialProjection import (  # noqa: E402
    normalize_threads, normalize_contact_page,
)

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
SECOND_PROFILE = "223e4567-e89b-42d3-a456-426614174000"
OWNER = ":1.99"
STAMP = "2026-11-06T14:00:00-05:00"


def scope(**updates):
    fields = {
        "principal_id": "principal_one",
        "session_id": "session_one",
        "device_binding_id": "device_one",
        "line_binding_id": "line_one",
        "profile_id": PROFILE,
        "provider_owner": OWNER,
        "owner_kind": "PERSONAL",
        "organization_id": None,
        "operation": "messages.read",
        "grant_generation": 7,
        "context_generation": 3,
    }
    fields.update(updates)
    return HostAssertedPhoneScope(**fields)


def threads():
    return [{
        "key": "address:phone:15551234567", "name": "Example",
        "is_group": False, "reply_ready": False, "unread": False,
        "messages_truncated": False, "messages": [
            {"handle": "msg:1", "body": "INVENTED PRIVATE BODY",
             "timestamp": STAMP, "outgoing": False,
             "read": True, "sender": ""},
        ],
    }]


def contacts():
    return {
        "contacts": [{"id": "card-one", "name": "Example",
                      "organization": "", "primary": "fake@example.invalid",
                      "phone_count": 0, "email_count": 1,
                      "has_photo": False}],
        "total": 1, "offset": 0, "query": "",
    }


def snapshot(s):
    return (normalize_threads(threads(), profile_id=s.profile_id)
            if s.operation == "messages.read" else
            normalize_contact_page(contacts(), profile_id=s.profile_id,
                                   daemon_epoch=12))


class FakeSource:
    def __init__(self, s, *, on_fetch=None):
        self.s = s
        self.actions = []
        self.on_fetch = on_fetch

    def owner(self):
        self.actions.append("owner")
        return self.s.provider_owner

    def status(self, owner):
        self.actions.append("status")
        return {
            "api_version": 2, "daemon": True,
            "phone_profile_id": self.s.profile_id,
            "map": True, "pbap": True,
            "contact_card_count": 1, "contact_card_epoch": 12,
        }

    def threads(self, owner):
        self.actions.append("threads")
        if self.on_fetch:
            self.on_fetch()
        return threads()

    def contact_cards(self, owner):
        self.actions.append("contacts")
        if self.on_fetch:
            self.on_fetch()
        return contacts()


class GateTests(unittest.TestCase):
    def setUp(self):
        self.deliveries = []
        self.purges = []
        self.allowed = True

        def deliver(asserted, content):
            self.deliveries.append((asserted, content))
            return True

        def purge(asserted):
            self.purges.append(asserted)
            self.deliveries.clear()
            return True

        self.deliver = deliver
        self.purge = purge
        self.gate = HostReadReleaseGateModel(
            evaluator=lambda asserted: self.allowed,
            deliver=deliver, purge=purge,
        )

    def check_reply(self, reply):
        self.assertEqual(reply["execution"], "IN_PROCESS_MODEL_ONLY")
        self.assertFalse(reply["routeEligible"])
        self.assertFalse(reply["contentAccessEnabled"])
        self.assertEqual(reply["authorization"], "NOT_IMPLEMENTED")
        self.assertEqual(set(reply), {
            "schema", "execution", "state", "epoch", "routeEligible",
            "contentAccessEnabled", "authorization",
        })
        self.assertNotIn("principal", str(reply))
        self.assertNotIn(PROFILE, str(reply))
        self.assertNotIn("INVENTED PRIVATE BODY", str(reply))

    def test_end_to_end_synthetic_thread_read_with_gate(self):
        s = scope()
        state, callbacks = self.gate.begin(s)
        self.check_reply(state)
        self.assertEqual(state["state"], "ARMED_MODEL_ONLY")
        result = read_for_trusted_host(
            operation=s.operation, profile_id=s.profile_id,
            source=FakeSource(s),
            host_guard=callbacks.guard, host_release=callbacks.release,
        )
        self.assertEqual(result["state"], "HOST_HANDOFF_REPORTED")
        self.assertEqual(len(self.deliveries), 1)
        actual = self.deliveries[0][1]
        self.assertEqual(actual["conversations"][0]["serviceId"], "blueferry")
        self.assertEqual(actual["messageSets"][0]["messages"][0]["body"],
                         "INVENTED PRIVATE BODY")
        cancelled = self.gate.cancel()
        self.check_reply(cancelled)
        self.assertEqual(cancelled["state"], "CANCELLED_MODEL_ONLY")
        self.assertEqual(self.deliveries, [])
        self.assertEqual(self.purges, [s])
        self.assertFalse(callbacks.guard(s.operation, s.profile_id, OWNER))
        self.assertFalse(callbacks.release(
            s.operation, s.profile_id, OWNER, actual))

    def test_end_to_end_synthetic_contact_read_without_message_capability(self):
        s = scope(operation="contacts.read")
        _, callbacks = self.gate.begin(s)
        source = FakeSource(s)
        answer = read_for_trusted_host(
            operation="contacts.read", profile_id=PROFILE, source=source,
            host_guard=callbacks.guard, host_release=callbacks.release,
        )
        self.assertEqual(answer["state"], "HOST_HANDOFF_REPORTED")
        self.assertEqual(source.actions, [
            "owner", "status", "contacts", "owner", "status",
        ])
        self.assertEqual(self.deliveries[0][1]["contacts"][0]["displayNameInProfile"],
                         "Example")
        self.assertFalse(callbacks.guard("messages.read", PROFILE, OWNER))
        self.assertFalse(callbacks.release(
            "messages.read", PROFILE, OWNER, snapshot(s)))
        self.assertEqual(len(self.deliveries), 1)

    def test_revoke_during_provider_fetch_cancels_before_release(self):
        s = scope()
        _, callbacks = self.gate.begin(s)
        source = FakeSource(s, on_fetch=lambda: self.gate.cancel())
        answer = read_for_trusted_host(
            operation=s.operation, profile_id=PROFILE, source=source,
            host_guard=callbacks.guard, host_release=callbacks.release,
        )
        self.assertEqual(answer["state"], "HOST_DENIED")
        self.assertEqual(self.deliveries, [])
        self.assertEqual(self.purges, [s])

    def test_authentication_revocation_seen_on_final_guard(self):
        s = scope()
        _, callbacks = self.gate.begin(s)
        self.allowed = False
        source = FakeSource(s)
        answer = read_for_trusted_host(
            operation=s.operation, profile_id=PROFILE, source=source,
            host_guard=callbacks.guard, host_release=callbacks.release,
        )
        self.assertEqual(answer["state"], "HOST_DENIED")
        self.assertEqual(source.actions, ["owner"])
        self.assertEqual(self.purges, [s])

    def test_permission_loss_between_last_guard_and_sink(self):
        s = scope()
        calls = []
        def evaluate(_):
            calls.append(True)
            return len(calls) < 4
        gate = HostReadReleaseGateModel(
            evaluator=evaluate, deliver=self.deliver, purge=self.purge,
        )
        _, callbacks = gate.begin(s)
        result = read_for_trusted_host(
            operation=s.operation, profile_id=PROFILE, source=FakeSource(s),
            host_guard=callbacks.guard, host_release=callbacks.release,
        )
        self.assertEqual(result["state"], "HOST_RELEASE_REFUSED")
        self.assertEqual(len(calls), 4)
        self.assertEqual(self.deliveries, [])
        self.assertEqual(self.purges, [s])

    def test_second_scope_requires_explicit_purge_and_stale_callbacks_fail(self):
        personal = scope()
        corporate = scope(
            principal_id="principal_two",
            session_id="session_two",
            device_binding_id="device_two",
            line_binding_id="line_two",
            profile_id=SECOND_PROFILE,
            provider_owner=":1.101",
            owner_kind="ORGANIZATION", organization_id="verified_org",
            grant_generation=9, context_generation=4,
        )
        _, first = self.gate.begin(personal)
        refused, cb = self.gate.begin(corporate)
        self.assertEqual(refused["state"], "EXPLICIT_CANCEL_REQUIRED")
        self.assertIsNone(cb)
        self.assertTrue(first.release(
            personal.operation, personal.profile_id,
            personal.provider_owner, snapshot(personal),
        ))
        self.assertEqual(len(self.deliveries), 1)
        self.assertEqual(self.gate.cancel()["state"], "CANCELLED_MODEL_ONLY")
        second_state, second = self.gate.begin(corporate)
        self.assertEqual(second_state["state"], "ARMED_MODEL_ONLY")
        self.assertFalse(first.guard(
            personal.operation, personal.profile_id, personal.provider_owner))
        self.assertFalse(first.release(
            personal.operation, personal.profile_id, personal.provider_owner,
            snapshot(personal),
        ))
        self.assertEqual(self.deliveries, [])
        self.assertTrue(second.release(
            corporate.operation, corporate.profile_id,
            corporate.provider_owner, snapshot(corporate),
        ))
        self.assertEqual(self.deliveries[0][0], corporate)
        self.assertEqual(self.deliveries[0][1]["deviceProfileId"], SECOND_PROFILE)

    def test_same_scope_rearm_does_not_revive_callbacks_from_old_epoch(self):
        s = scope()
        _, old = self.gate.begin(s)
        self.gate.cancel()
        _, current = self.gate.begin(s)
        self.assertFalse(old.guard(s.operation, PROFILE, OWNER))
        self.assertFalse(old.release(s.operation, PROFILE, OWNER, snapshot(s)))
        self.assertTrue(current.guard(s.operation, PROFILE, OWNER))

    def test_rejected_snapshot_does_not_cross_profile_or_operation(self):
        s = scope()
        _, callbacks = self.gate.begin(s)
        wrong = snapshot(scope(profile_id=SECOND_PROFILE))
        self.assertFalse(callbacks.release(s.operation, PROFILE, OWNER, wrong))
        self.assertEqual(self.deliveries, [])
        self.assertEqual(self.purges, [s])
        _, callbacks = self.gate.begin(s)
        wrong_op = snapshot(scope(operation="contacts.read"))
        self.assertFalse(callbacks.release(s.operation, PROFILE, OWNER, wrong_op))
        self.assertEqual(self.deliveries, [])

    def test_invalid_unhashable_group_metadata_fails_closed(self):
        s = scope()
        bad = snapshot(s)
        bad["messageSets"][0]["conversationId"] = []
        self.assertFalse(_snapshot_matches(bad, s))
        _, callbacks = self.gate.begin(s)
        self.assertFalse(callbacks.release(s.operation, PROFILE, OWNER, bad))
        self.assertFalse(self.deliveries)

    def test_rejected_sink_purges_even_if_sink_may_have_partially_written(self):
        s = scope()
        def partially_writes(_, content):
            self.deliveries.append((s, content))
            return False
        gate = HostReadReleaseGateModel(
            evaluator=lambda _: True, deliver=partially_writes, purge=self.purge
        )
        _, callbacks = gate.begin(s)
        self.assertFalse(callbacks.release(s.operation, PROFILE, OWNER, snapshot(s)))
        self.assertEqual(self.deliveries, [])
        self.assertEqual(self.purges, [s])

    def test_purge_failure_seals_gate_until_external_host_recovery(self):
        s = scope()
        gate = HostReadReleaseGateModel(
            evaluator=lambda _: True,
            deliver=self.deliver,
            purge=lambda _: False,
        )
        _, callbacks = gate.begin(s)
        self.assertTrue(callbacks.release(s.operation, PROFILE, OWNER, snapshot(s)))
        answer = gate.cancel()
        self.assertEqual(answer["state"], "PURGE_UNCONFIRMED")
        state, next_callbacks = gate.begin(s)
        self.assertEqual(state["state"], "PURGE_UNCONFIRMED")
        self.assertIsNone(next_callbacks)
        self.assertFalse(callbacks.release(s.operation, PROFILE, OWNER, snapshot(s)))

    def test_deliver_and_revoke_are_serialized_inside_one_instance(self):
        entered, unblock = Event(), Event()
        history = []
        def blocking_deliver(_, content):
            entered.set()
            if not unblock.wait(3):
                return False
            history.append(content)
            return True
        def purge(_):
            history.clear()
            return True
        gate = HostReadReleaseGateModel(
            evaluator=lambda _: True, deliver=blocking_deliver, purge=purge,
        )
        s = scope()
        _, callbacks = gate.begin(s)
        release_reply, revoke_reply = [], []
        release_thread = Thread(target=lambda: release_reply.append(
            callbacks.release(s.operation, PROFILE, OWNER, snapshot(s))))
        revoke_thread = Thread(target=lambda: revoke_reply.append(gate.cancel()))
        release_thread.start()
        self.assertTrue(entered.wait(2), "sink did not begin")
        revoke_thread.start()
        self.assertFalse(revoke_reply, "revocation bypassed the release lock")
        unblock.set()
        release_thread.join(3)
        revoke_thread.join(3)
        self.assertFalse(release_thread.is_alive())
        self.assertFalse(revoke_thread.is_alive())
        self.assertEqual(release_reply, [True])
        self.assertEqual(revoke_reply[0]["state"], "CANCELLED_MODEL_ONLY")
        self.assertEqual(history, [])
        self.assertFalse(callbacks.guard(s.operation, PROFILE, OWNER))

    def test_fail_closed_scope_validation_and_no_hidden_real_authority(self):
        for updates in (
            {"owner_kind": "PERSONAL", "organization_id": "org_fake"},
            {"owner_kind": "ORGANIZATION", "organization_id": None},
            {"owner_kind": "SYSTEM"},
            {"grant_generation": 0},
            {"context_generation": -1},
            {"profile_id": "AA:BB:CC:DD:EE:FF"},
            {"provider_owner": "io.weirdware.BlueFerry"},
            {"principal_id": "person@example.invalid"},
            {"operation": "messages.send"},
        ):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError):
                    scope(**updates)
        denied, callbacks = self.gate.begin(object())
        self.check_reply(denied)
        self.assertEqual(denied["state"], "HOST_DENIED")
        self.assertIsNone(callbacks)
        self.allowed = False
        denied, callbacks = self.gate.begin(scope())
        self.assertEqual(denied["state"], "HOST_DENIED")
        self.assertIsNone(callbacks)

    def test_no_phone_read_or_qml_activation_on_import(self):
        script = (ROOT / "services/phone/HostReadReleaseGateModel.py").read_text()
        for forbidden in (
            'if __name__ == "__main__"',
            "import dbus", "import socket", "import subprocess",
            "ListThreads(", "ListContactCards(", "SendToThread(",
            "os.environ", "sys.argv", "print(",
        ):
            self.assertNotIn(forbidden, script)
        self.assertIn("RLock()", script)
        self.assertIn('self._epoch += 1', script)


if __name__ == "__main__":
    unittest.main()
