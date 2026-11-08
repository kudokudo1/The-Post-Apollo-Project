"""Telegram revocation M1: synthetic provider-side boundary and fail-closed proof.

No Telegram network, credentials, real session files, QML integration, or
production permission activation. All sign-out behavior is a fake callback.
"""
import asyncio
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/messaging/fixtures/telegram_session_revocation_m1.py"
spec = importlib.util.spec_from_file_location("telegram_m1_test_only", SOURCE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeTelegramProvider:
    def __init__(self):
        self.accounts = {
            ("shared", ""): self._make("shared", "", "fake-session-shared-A"),
            ("private", "identity-1"): self._make(
                "private", "identity-1", "fake-session-private-one"),
            ("private", "identity-2"): self._make(
                "private", "identity-2", "fake-session-private-two"),
        }
        self.calls = []
        self.ack = True
        self.raise_on_logout = False
        self.after_mode = "normal"

    @staticmethod
    def _make(target, identity, nonce):
        return dict(target=target, identity=identity, epoch=7, nonce=nonce,
                    authorized=True, operationBusy=False)

    def inspect(self, target, identity):
        record = self.accounts.get((target, identity))
        if record is None:
            return None
        if self.after_mode == "missing" and self.calls:
            return None
        if self.after_mode == "reauth" and self.calls:
            out = dict(record)
            out["authorized"] = True
            return out
        return dict(record)

    async def log_out(self, target, identity):
        self.calls.append((target, identity))
        if self.raise_on_logout:
            raise RuntimeError("FAKE_NETWORK_UNKNOWN")
        if self.ack is True:
            item = self.accounts[(target, identity)]
            item["authorized"] = False
            item["epoch"] += 1
        return self.ack


class TelegramRevocationContracts(unittest.TestCase):
    def setUp(self):
        self.time = 101.5
        self.provider = FakeTelegramProvider()
        self.host = m.DisposableTelegramRevocation(
            marker=m.TEST_MARKER, provider=self.provider, clock=lambda: self.time)

    @staticmethod
    def request(target="shared", identity=""):
        return dict(scope=m.OPERATION, operation="log_out",
                    target=target, identity=identity)

    def review(self, request_id, target="shared", identity="", **changes):
        data = dict(requestId=request_id, scope=m.OPERATION, operation="log_out",
                    target=target, identity=identity,
                    confirmRemoteRevocation=True, confirmLocalSessionLoss=True)
        data.update(changes)
        return data

    def execute(self, request_id, target="shared", identity="", **changes):
        data = dict(requestId=request_id, scope=m.OPERATION, operation="log_out",
                    target=target, identity=identity)
        data.update(changes)
        return asyncio.run(self.host.client_execute(data))

    def deny_real_authority(self, result):
        for flag in m.DENY:
            self.assertIs(result[flag], False, flag)
        self.assertNotIn("fake-session-", repr(result))
        self.assertNotIn("identity-1", repr(result))
        self.assertNotIn("identity-2", repr(result))
        self.assertNotIn("personal.session", repr(result))

    def test_no_operation_before_separate_two_part_test_review(self):
        prepare = self.host.client_prepare(self.request())
        self.assertEqual(prepare["status"], "SYNTHETIC_REVIEW_REQUIRED_NO_GRANT")
        self.deny_real_authority(prepare)
        self.assertFalse(prepare["syntheticStepAccepted"])
        self.assertEqual(self.execute(prepare["requestId"])["status"],
                         "NOT_APPROVED_OR_REPLAYED")
        self.assertEqual(self.provider.calls, [])
        for wrong in (
            self.review(prepare["requestId"], confirmRemoteRevocation=False),
            self.review(prepare["requestId"], confirmLocalSessionLoss=False),
            self.review(prepare["requestId"], operation="disconnect"),
            self.review(prepare["requestId"], target="private", identity="identity-1"),
        ):
            outcome = self.host.synthetic_reviewer_approve(wrong)
            self.assertEqual(outcome["status"], "SYNTHETIC_REVIEW_REFUSED")
            self.deny_real_authority(outcome)
        self.assertEqual(self.provider.calls, [])

    def test_shared_revoke_is_one_time_and_never_mutates_private_scopes(self):
        rid = self.host.client_prepare(self.request())["requestId"]
        self.host.synthetic_reviewer_approve(self.review(rid))
        result = self.execute(rid)
        self.assertEqual(result["status"], "SYNTHETIC_TELETHON_ACK_AND_LOCAL_STATUS_ONLY")
        self.assertTrue(result["syntheticStepAccepted"])
        self.deny_real_authority(result)
        self.assertEqual(self.provider.calls, [("shared", "")])
        self.assertFalse(self.provider.accounts[("shared", "")]["authorized"])
        self.assertTrue(self.provider.accounts[("private", "identity-1")]["authorized"])
        self.assertTrue(self.provider.accounts[("private", "identity-2")]["authorized"])
        self.assertEqual(self.execute(rid)["status"], "NOT_APPROVED_OR_REPLAYED")
        self.assertEqual(len(self.provider.calls), 1)

    def test_private_revoke_is_exact_scoped_and_never_touches_shared(self):
        rid = self.host.client_prepare(self.request("private", "identity-1"))["requestId"]
        self.assertEqual(self.host.synthetic_reviewer_approve(
            self.review(rid, "private", "identity-1"))["status"],
            "SYNTHETIC_REVIEW_ACCEPTED_NO_REAL_GRANT")
        wrong = self.execute(rid, "private", "identity-2")
        self.assertEqual(wrong["status"], "REQUEST_BINDING_CHANGED")
        self.assertEqual(self.provider.calls, [])
        success = self.execute(rid, "private", "identity-1")
        self.assertTrue(success["syntheticStepAccepted"])
        self.assertEqual(self.provider.calls, [("private", "identity-1")])
        self.assertTrue(self.provider.accounts[("shared", "")]["authorized"])
        self.assertTrue(self.provider.accounts[("private", "identity-2")]["authorized"])

    def test_request_scope_identity_extra_field_and_forgeries_refuse(self):
        invalid = [
            self.request("shared", "identity-1"), self.request("private", ""),
            self.request("private", "identity-0"),
            self.request("private", "../identity-1"),
            self.request("private", "identity-01"),
            self.request("private", "identity-9999999999"),
            self.request("private", "identity-1/"),
            {**self.request(), "scope": "telegram.session.disconnect"},
            {**self.request(), "operation": "disconnect"},
            {**self.request(), "sessionPath": "/home/person/.session"},
            {**self.request(), "approved": True},
            None, [], {},
        ]
        for item in invalid:
            with self.subTest(item=item):
                result = self.host.client_prepare(item)
                self.assertEqual(result["status"], "INVALID_OPERATION_OR_SCOPE")
                self.deny_real_authority(result)
        self.assertEqual(self.provider.calls, [])

    def test_stale_scope_busy_and_changed_source_refuse_before_mutation(self):
        for action in (
            lambda: self.provider.accounts[("shared", "")].__setitem__("epoch", 8),
            lambda: self.provider.accounts[("shared", "")].__setitem__("nonce", "fake-session-other"),
            lambda: self.provider.accounts[("shared", "")].__setitem__("operationBusy", True),
            lambda: self.provider.accounts[("shared", "")].__setitem__("authorized", False),
        ):
            self.setUp()
            rid = self.host.client_prepare(self.request())["requestId"]
            self.host.synthetic_reviewer_approve(self.review(rid))
            action()
            result = self.execute(rid)
            self.assertEqual(result["status"], "SESSION_CHANGED_BEFORE_REVOCATION")
            self.deny_real_authority(result)
            self.assertEqual(self.provider.calls, [])

    def test_changed_during_review_and_busy_preflight_refuse(self):
        self.provider.accounts[("shared", "")]["operationBusy"] = True
        self.assertEqual(self.host.client_prepare(self.request())["status"],
                         "SESSION_NOT_INDEPENDENTLY_VERIFIED")
        self.provider.accounts[("shared", "")]["operationBusy"] = False
        rid = self.host.client_prepare(self.request())["requestId"]
        self.provider.accounts[("shared", "")]["epoch"] += 1
        self.assertEqual(self.host.synthetic_reviewer_approve(self.review(rid))["status"],
                         "SESSION_CHANGED_BEFORE_REVIEW")
        self.assertEqual(self.provider.calls, [])

    def test_expiry_revocation_and_missing_host_deny(self):
        rid = self.host.client_prepare(self.request())["requestId"]
        self.host.synthetic_reviewer_approve(self.review(rid))
        self.time += 30.01
        self.assertEqual(self.execute(rid)["status"], "REVOKED_OR_EXPIRED")
        self.assertEqual(self.provider.calls, [])
        self.setUp()
        rid = self.host.client_prepare(self.request())["requestId"]
        self.host.synthetic_reviewer_approve(self.review(rid))
        self.host.synthetic_revoke()
        self.assertEqual(self.execute(rid)["status"], "NOT_APPROVED_OR_REPLAYED")
        self.assertEqual(self.provider.calls, [])
        with self.assertRaisesRegex(RuntimeError, "NON_DISPOSABLE_HOST"):
            m.DisposableTelegramRevocation(
                marker="production", provider=self.provider, clock=lambda: self.time)

    def test_provider_ack_unknown_failure_and_post_status_uncertainty(self):
        for variant in ("ack_false", "exception", "post_missing", "post_reauth"):
            with self.subTest(variant=variant):
                self.setUp()
                if variant == "ack_false":
                    self.provider.ack = False
                if variant == "exception":
                    self.provider.raise_on_logout = True
                if variant == "post_missing":
                    self.provider.after_mode = "missing"
                if variant == "post_reauth":
                    self.provider.after_mode = "reauth"
                rid = self.host.client_prepare(self.request())["requestId"]
                self.host.synthetic_reviewer_approve(self.review(rid))
                result = self.execute(rid)
                self.assertFalse(result["syntheticStepAccepted"])
                self.deny_real_authority(result)
                self.assertEqual(len(self.provider.calls), 1)
                self.assertEqual(self.execute(rid)["status"], "NOT_APPROVED_OR_REPLAYED")

    def test_no_production_entrypoint_or_untrusted_destructive_button(self):
        base = ROOT / "services"
        for item in (
            ROOT / "shell.qml",
            ROOT / "widgets/CpuPlusW.qml",
            ROOT / "widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml",
            ROOT / "widgets/messanger/MessagingW.qml",
            base / "messaging/adapters/TelegramAdapter.qml",
            base / "messaging/bridges/telegram/bridge.py",
        ):
            source = item.read_text()
            self.assertNotIn("telegram_session_revocation_m1", source)
        adapter = (base / "messaging/adapters/TelegramAdapter.qml").read_text()
        bridge = (base / "messaging/bridges/telegram/bridge.py").read_text()
        broker = (base / "connections/ConnectionsBroker.qml").read_text()
        self.assertNotIn('sub.add_parser("logout")', bridge)
        self.assertNotIn('sub.add_parser("revoke")', bridge)
        self.assertNotIn("log_out()", adapter)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        details = (ROOT / "widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml").read_text()
        self.assertNotIn('label: "DISCONNECT"', details)
        self.assertNotIn('label: "REVOKE TELEGRAM"', details)
        self.assertIn('label: "RECHECK SESSION"', details)
        self.assertIn('label: "OPEN TELEGRAM"', details)


if __name__ == "__main__":
    unittest.main()
