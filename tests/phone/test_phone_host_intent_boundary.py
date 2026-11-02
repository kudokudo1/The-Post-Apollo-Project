"""Pure negative tests for proposed Social Phone -> host intent boundary.

No user accounts, device access, messages, network or live identity services.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "phone"))
import PhoneHostIntentBoundary as boundary  # noqa: E402


def intent(**changes):
    result = {
        "contract": boundary.INTENT_SCHEMA,
        "operation": "requestReceiveAccess",
        "deviceSelector": "fixtureDeviceA",
        "lineSelector": "fixtureLineA",
        "ownerKind": "PERSONAL",
        "organizationSelector": None,
        "requestedCapability": "messages.receive",
    }
    result.update(changes)
    return result


class HostIntentBoundaryTests(unittest.TestCase):
    def assertRejected(self, request):
        self.assertIsNone(boundary.parse_untrusted_receive_selection(request))
        status = boundary.sanitized_intent_status(request)
        self.assertEqual(status["status"], "INVALID_REQUEST")
        self.assertFalse(status["routeEligible"])
        self.assertFalse(status["contentAccessEnabled"])

    def test_exact_personal_receive_intent_has_untrusted_selectors(self):
        parsed = boundary.parse_untrusted_receive_selection(intent())
        self.assertIsInstance(parsed, boundary.UntrustedReceiveSelection)
        self.assertEqual(parsed.device_selector, "fixtureDeviceA")
        self.assertEqual(parsed.line_selector, "fixtureLineA")
        self.assertEqual(parsed.owner_kind, "PERSONAL")
        self.assertIsNone(parsed.organization_selector)
        self.assertFalse(hasattr(parsed, "authorized"))
        self.assertFalse(hasattr(parsed, "principal_id"))

    def test_exact_org_intent_is_only_a_selector(self):
        parsed = boundary.parse_untrusted_receive_selection(
            intent(ownerKind="ORGANIZATION", organizationSelector="fixtureOrgA")
        )
        self.assertEqual(parsed.organization_selector, "fixtureOrgA")
        self.assertFalse(hasattr(parsed, "membership"))
        self.assertFalse(hasattr(parsed, "grant_id"))

    def test_valid_intent_is_always_authorization_required(self):
        for request in (
            intent(),
            intent(ownerKind="ORGANIZATION", organizationSelector="fixtureOrgA"),
        ):
            with self.subTest(request=request):
                status = boundary.sanitized_intent_status(request)
                self.assertEqual(status["status"], "AUTHORIZATION_REQUIRED")
                self.assertEqual(status["execution"], "INTENT_VALIDATION_ONLY")
                self.assertFalse(status["routeEligible"])
                self.assertFalse(status["contentAccessEnabled"])

    def test_personal_cannot_claim_organization_scope(self):
        self.assertRejected(intent(organizationSelector="fixtureOrgA"))

    def test_organization_requires_explicit_organization_selector(self):
        self.assertRejected(intent(ownerKind="ORGANIZATION"))
        self.assertRejected(intent(ownerKind="ORGANIZATION", organizationSelector=""))

    def test_reject_portfolio_as_ownership_kind(self):
        self.assertRejected(intent(ownerKind="PORTFOLIO", organizationSelector="portfolioA"))

    def test_reject_division_as_ownership_kind(self):
        self.assertRejected(intent(ownerKind="BRANCH", organizationSelector="fixtureOrgA"))

    def test_no_identity_claims_can_be_supplied(self):
        for field in ("principalId", "identityId", "sessionId", "sessionRef",
                      "userId", "userEmail", "actor"):
            with self.subTest(field=field):
                self.assertRejected(intent(**{field: "someone"}))

    def test_no_grant_or_permission_claims_can_be_supplied(self):
        for field in ("grantId", "accessGrant", "canRead", "authorized",
                      "permission", "scopes", "roles", "isAdmin"):
            with self.subTest(field=field):
                self.assertRejected(intent(**{field: True}))

    def test_no_token_or_secret_can_be_supplied(self):
        for field in ("accessToken", "refreshToken", "password", "cookie",
                      "bearer", "apiKey", "jwt"):
            with self.subTest(field=field):
                self.assertRejected(intent(**{field: "synthetic-secret"}))

    def test_no_phone_message_content_can_be_supplied(self):
        for field in ("body", "message", "phoneNumber", "recipient",
                      "addresses", "attachment", "conversationId"):
            with self.subTest(field=field):
                self.assertRejected(intent(**{field: "synthetic-message"}))

    def test_only_receive_operation_is_a_valid_intent(self):
        for op in ("requestSendAccess", "receive", "connectAll", "pairDevice",
                   "getConversations", "readHistory", "requestCallAudio", ""):
            with self.subTest(op=op):
                self.assertRejected(intent(operation=op))

    def test_send_history_contacts_and_calls_not_inherited(self):
        for cap in ("messages.send", "messages.read", "contacts.read",
                    "notifications.receive", "calls.answer", "calls.audio", ""):
            with self.subTest(cap=cap):
                self.assertRejected(intent(requestedCapability=cap))

    def test_no_transport_override_or_bluetooth_optin_from_intent(self):
        for key in ("transport", "networkOnly", "bluetoothEnabled", "routeEligible",
                    "platform", "kdeProvider"):
            with self.subTest(key=key):
                self.assertRejected(intent(**{key: "LAN"}))

    def test_explicit_schema_required(self):
        self.assertRejected(intent(contract="post-apollo.phone.synthetic-access-grant.v0"))
        self.assertRejected(intent(contract="post-apollo.phone.host-intent.v0"))
        self.assertRejected(intent(contract=None))

    def test_exact_fields_required_even_when_removed(self):
        for key in boundary.EXPECTED_FIELDS:
            with self.subTest(key=key):
                request = intent()
                del request[key]
                self.assertRejected(request)

    def test_malformed_request_types_never_raise(self):
        for value in (None, [], "fake", 42, True, (), object()):
            with self.subTest(value=type(value).__name__):
                self.assertRejected(value)

    def test_reject_nonstring_selectors(self):
        for val in (None, True, 0, 123, [], {}, b"device"):
            with self.subTest(value=type(val).__name__):
                self.assertRejected(intent(deviceSelector=val))
                self.assertRejected(intent(lineSelector=val))

    def test_reject_phone_numbers_emails_and_paths_as_opaque_selectors(self):
        for val in ("+12025550199", "2025550199", "test@example.com",
                    "/modules/kdeconnect/devices/abc", "x/../y", "x:y",
                    "x.test", "a b", "a\nb"):
            with self.subTest(value=val):
                self.assertRejected(intent(deviceSelector=val))
                self.assertRejected(intent(lineSelector=val))

    def test_reject_unicode_control_spaces_and_whitespace(self):
        for val in ("手机", "mañana", "α", "x\x00x", " a", "a ", "\tx"):
            with self.subTest(value=val):
                self.assertRejected(intent(deviceSelector=val))

    def test_reject_oversized_or_empty_selector(self):
        for val in ("", "a" * 65, "a" * 50000):
            with self.subTest(length=len(val)):
                self.assertRejected(intent(deviceSelector=val))
                self.assertRejected(intent(lineSelector=val))

    def test_reject_malformed_organization_selector_even_on_valid_device(self):
        for val in (123, True, "5551234567", "org/a", "o" * 70):
            with self.subTest(val=str(val)[:12]):
                self.assertRejected(intent(ownerKind="ORGANIZATION", organizationSelector=val))

    def test_input_is_not_mutated(self):
        request = intent()
        before = dict(request)
        boundary.parse_untrusted_receive_selection(request)
        boundary.sanitized_intent_status(request)
        self.assertEqual(request, before)

    def test_output_never_echoes_untrusted_identifiers_or_content(self):
        for request in (
            intent(),
            intent(ownerKind="ORGANIZATION", organizationSelector="fixtureOrgA"),
            intent(accessToken="supersecret"),
        ):
            result = boundary.sanitized_intent_status(request)
            self.assertEqual(set(result), {
                "contract", "execution", "status", "requestedCapability",
                "platform", "transport", "routeEligible", "contentAccessEnabled",
            })
            for secret in ("fixtureDeviceA", "fixtureLineA",
                           "fixtureOrgA", "supersecret"):
                self.assertNotIn(secret, str(result))
            self.assertEqual(result["platform"], "UNVERIFIED")
            self.assertEqual(result["transport"], "UNVERIFIED")

    def test_repr_does_not_disclose_client_selectors(self):
        parsed = boundary.parse_untrusted_receive_selection(
            intent(deviceSelector="syntheticSensitiveDevice")
        )
        self.assertNotIn("syntheticSensitiveDevice", repr(parsed))

    def test_no_active_host_or_provider_functions(self):
        for prohibited in ("authorize", "connect", "sendSms", "subscribe",
                           "createGrant", "revokeGrant"):
            self.assertFalse(hasattr(boundary, prohibited))
        self.assertFalse(hasattr(boundary.UntrustedReceiveSelection, "allow"))

    def test_type_strictness_for_proposed_fields(self):
        for field, value in (
            ("ownerKind", True),
            ("contract", 2),
            ("operation", ["requestReceiveAccess"]),
            ("requestedCapability", b"messages.receive"),
        ):
            with self.subTest(field=field):
                self.assertRejected(intent(**{field: value}))


if __name__ == "__main__":
    unittest.main()
