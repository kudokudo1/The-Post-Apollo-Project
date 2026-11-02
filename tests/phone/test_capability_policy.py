"""Synthetic Phone Bridge P0 tests. No device, network, BlueZ, or UI access."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import CapabilityPolicy as phone  # noqa: E402


def candidate(backend="wifi-a", transport="NETWORK", **changes):
    item = {
        "backendId": backend, "principalId": "person-a",
        "deviceId": "phone-a", "lineId": "personal-line",
        "transport": transport, "operations": ["messages.send", "contacts.read"],
        "authorization": "VERIFIED", "permission": "GRANTED",
        "health": "READY", "probe": "VERIFIED",
    }
    item.update(changes)
    return item


def request(candidates=None, mode="AUTO", bluetooth=False,
            bt_operations=None, manual=None, **changes):
    obj = {
        "schema": phone.SCHEMA, "requestId": "req-1",
        "principalId": "person-a", "deviceId": "phone-a",
        "lineId": "personal-line", "operation": "messages.send",
        "inFlight": "NONE",
        "policy": {
            "mode": mode, "bluetoothFallback": bluetooth,
            "bluetoothOperations": bt_operations or [],
            "manualBackendId": manual,
        },
        "candidates": [] if candidates is None else candidates,
    }
    obj.update(changes)
    return obj


class CapabilityPolicyTests(unittest.TestCase):
    def test_network_wins_even_when_bluetooth_listed_first(self):
        result = phone.plan(request([
            candidate("bt-a", "BLUETOOTH"), candidate("wifi-a", "NETWORK")
        ], bluetooth=True, bt_operations=["messages.send"]))
        self.assertEqual(
            (result["state"], result["backendId"], result["transport"], result["reason"]),
            ("ROUTE_CANDIDATE", "wifi-a", "NETWORK", "NETWORK_PREFERRED")
        )
        self.assertEqual(result["execution"], "PLAN_ONLY")

    def test_bluetooth_fallback_is_explicit_per_capability(self):
        result = phone.plan(request(
            [candidate("bt-a", "BLUETOOTH")], bluetooth=True,
            bt_operations=["messages.send"]))
        self.assertEqual(result["backendId"], "bt-a")
        self.assertEqual(result["reason"], "BLUETOOTH_FALLBACK")

    def test_bluetooth_fallback_disabled_by_default(self):
        result = phone.plan(request([candidate("bt-a", "BLUETOOTH")]))
        self.assertEqual(result["state"], "UNAVAILABLE")
        self.assertIsNone(result["backendId"])

    def test_bluetooth_is_not_implicitly_allowed_for_other_operations(self):
        result = phone.plan(request(
            [candidate("bt-a", "BLUETOOTH")], bluetooth=True,
            bt_operations=["contacts.read"]))
        self.assertEqual(result["state"], "UNAVAILABLE")

    def test_network_only_never_uses_bluetooth_even_with_opt_in(self):
        result = phone.plan(request(
            [candidate("bt-a", "BLUETOOTH")], mode="NETWORK_ONLY",
            bluetooth=True, bt_operations=["messages.send"]))
        self.assertEqual(result["reason"], "NO_VERIFIED_NETWORK_ROUTE")

    def test_manual_network_can_select_specific_backend(self):
        result = phone.plan(request(
            [candidate("wifi-a"), candidate("wifi-b")], mode="MANUAL",
            manual="wifi-b"))
        self.assertEqual(result["backendId"], "wifi-b")
        self.assertEqual(result["reason"], "MANUAL_CHOICE")

    def test_manual_bluetooth_still_requires_device_capability_opt_in(self):
        items = [candidate("bt-a", "BLUETOOTH")]
        disallowed = phone.plan(request(items, mode="MANUAL", manual="bt-a"))
        self.assertIsNone(disallowed["backendId"])
        allowed = phone.plan(request(items, mode="MANUAL", manual="bt-a",
                                     bluetooth=True, bt_operations=["messages.send"]))
        self.assertEqual(allowed["backendId"], "bt-a")

    def test_two_network_routes_demand_selection_not_unrelated_bluetooth(self):
        result = phone.plan(request([
            candidate("wifi-a"), candidate("wifi-b"),
            candidate("bt-a", "BLUETOOTH")
        ], bluetooth=True, bt_operations=["messages.send"]))
        self.assertEqual(result["state"], "SELECTION_REQUIRED")
        self.assertIsNone(result["backendId"])

    def test_two_bluetooth_routes_are_ambiguous(self):
        result = phone.plan(request(
            [candidate("bt-a", "BLUETOOTH"), candidate("bt-b", "BLUETOOTH")],
            bluetooth=True, bt_operations=["messages.send"]))
        self.assertEqual(result["state"], "SELECTION_REQUIRED")

    def test_reject_duplicate_backend_identifiers(self):
        with self.assertRaises(ValueError):
            phone.plan(request([candidate("wifi-a"), candidate("wifi-a")]))

    def test_principal_device_and_line_bound_to_request(self):
        for change in (
            {"principalId": "person-b"},
            {"deviceId": "phone-b"},
            {"lineId": "company-line"},
        ):
            with self.subTest(change=change):
                result = phone.plan(request([candidate(**change)]))
                self.assertIsNone(result["backendId"])
                self.assertEqual(result["state"], "UNAVAILABLE")

    def test_no_cross_tenant_context_promotion(self):
        # Matching label, but a different verified principal and line.
        result = phone.plan(request([
            candidate("work", principalId="person-b", lineId="company-line"),
            candidate("personal", authorization="UNKNOWN"),
        ]))
        self.assertEqual(result["state"], "UNAVAILABLE")
        self.assertIsNone(result["backendId"])

    def test_fail_closed_without_exact_capability(self):
        result = phone.plan(request([
            candidate(operations=["messages.read"])
        ]))
        self.assertEqual(result["state"], "UNAVAILABLE")

    def test_fail_closed_when_authorization_permission_health_or_probe_missing(self):
        deviations = [
            {"authorization": "UNKNOWN"}, {"authorization": "DENIED"},
            {"permission": "UNKNOWN"}, {"permission": "DENIED"},
            {"health": "DEGRADED"}, {"health": "OFFLINE"},
            {"probe": "UNVERIFIED"},
        ]
        for change in deviations:
            with self.subTest(change=change):
                result = phone.plan(request([candidate(**change)]))
                self.assertEqual(result["state"], "UNAVAILABLE")
                self.assertIsNone(result["backendId"])

    def test_unknown_send_outcome_blocks_all_new_routes(self):
        result = phone.plan(request(
            [candidate("wifi-a"), candidate("bt-a", "BLUETOOTH")],
            inFlight="SEND_OUTCOME_UNKNOWN", bluetooth=True,
            bt_operations=["messages.send"]))
        self.assertEqual(result["reason"], "SEND_OUTCOME_UNKNOWN")
        self.assertEqual(result["state"], "BLOCKED")
        self.assertIsNone(result["backendId"])

    def test_active_call_blocks_unverified_midcall_switch(self):
        result = phone.plan(request(
            [candidate("wifi-a", operations=["calls.audio"])],
            operation="calls.audio", inFlight="CALL_ACTIVE"))
        self.assertEqual(result["reason"], "ACTIVE_CALL_NOT_REROUTABLE")
        self.assertIsNone(result["backendId"])

    def test_no_backend_does_not_claim_provider_connection(self):
        result = phone.plan(request())
        self.assertEqual(result["execution"], "PLAN_ONLY")
        self.assertEqual(result["state"], "UNAVAILABLE")
        self.assertIsNone(result["backendId"])

    def test_unverified_iphone_message_route_not_magically_available(self):
        result = phone.plan(request([
            candidate("iphone-lan", authorization="UNKNOWN"),
            candidate("iphone-map", "BLUETOOTH", probe="UNVERIFIED"),
        ], bluetooth=True, bt_operations=["messages.send"]))
        self.assertEqual(result["state"], "UNAVAILABLE")

    def test_unknown_operations_and_fields_are_rejected(self):
        invalid = [
            request(operation="facetime.answer"),
            request(secret="not-accepted"),
            request(candidates=[candidate(cookie="forbidden")]),
            request(candidates=[candidate(operations=["messages.send", "messages.send"])]),
            request(policy={"mode": "AUTO"}),
            request(principalId="../other"),
            request(candidates=[candidate(deviceId="../other")]),
            request(inFlight="RETRY_ANYWAY"),
        ]
        for payload in invalid:
            with self.subTest(keys=list(payload)):
                with self.assertRaises(ValueError):
                    phone.plan(payload)

    def test_bounds_and_manual_mode_reject_invalid_inputs(self):
        invalid = [
            request(candidates=[candidate(f"wifi-{i}") for i in range(17)]),
            request(mode="MANUAL", manual=None),
            request(mode="AUTO", manual="wifi-a"),
            request(bluetooth="true"),
            request(bt_operations=["unknown.operation"], bluetooth=True),
            request(candidates={"wifi": candidate()}),
        ]
        for payload in invalid:
            with self.subTest(payload=str(payload)[:90]):
                with self.assertRaises(ValueError):
                    phone.plan(payload)

    def test_output_has_no_private_account_device_or_contact_data(self):
        result = phone.plan(request([candidate("wifi-a")]))
        self.assertEqual(set(result), {
            "schema", "execution", "requestId", "operation", "state",
            "reason", "backendId", "transport",
        })
        self.assertNotIn("phone-a", str(result))
        self.assertNotIn("personal-line", str(result))
        self.assertNotIn("person-a", str(result))


if __name__ == "__main__":
    unittest.main()
