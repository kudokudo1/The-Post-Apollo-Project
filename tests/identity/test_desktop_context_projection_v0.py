"""Tokenless desktop read-only Organizations projection contract (CI only).

The ONLY token exists in the fake privileged test-host closure and never in
DesktopContextProjection, its snapshot, Social QML or any stored file. The
actual bearer is validated by the preexisting WSGI request boundary.
"""
from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from wsgiref.util import setup_testing_defaults

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from desktop_context_projection_v0 import (
    DesktopContextProjection, HostContextReply, SCHEMA,
)
from durable_context_store_v0 import DurableContextStore
from read_only_context_wsgi_v0 import ReadOnlyContextApp
from synthetic_request_boundary_v0 import VerifiedSession

ISSUER = "https://disposable-idp.invalid/realm"
AUDIENCE = "post-apollo-display-test"


class FakeVerifier:
    def __init__(self):
        self.revoke = False
        self.offline = False

    def verify(self, token, *, now):
        if self.offline:
            raise OSError("simulated provider unavailable")
        if self.revoke or token != "private-host-test-token":
            return None
        return VerifiedSession("subject-only", ISSUER, AUDIENCE,
                               "session-synthetic", 50, 400)


def fixture_body():
    return {
        "status": "OK", "schema": SCHEMA,
        "organizations": [
            {"organizationId": "llc_a", "kind": "llc",
             "scopeGrants": [{"action": "records.read", "divisionId": "health",
                              "unitId": "maryland", "expiresAt": 210}]},
            {"organizationId": "llc_b", "kind": "llc", "scopeGrants": []},
        ],
        "portfolios": [{"portfolioId": "family",
                        "organizationIds": ["llc_a", "llc_b"]}],
    }


def reply(payload, status_code=200, content_type="application/json"):
    return HostContextReply(status_code, content_type,
                            json.dumps(payload).encode("utf-8"))


class DesktopProjectionTests(unittest.TestCase):
    def setUp(self):
        self.now = 100
        self.fake = FakeVerifier()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / "test-context.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(
                (ROOT / "services/identity/durable_context_schema_v0.sql").read_text()
            )
            db.execute("INSERT INTO principals VALUES ('internal-a')")
            db.execute("INSERT INTO provider_subjects VALUES (?, ?, 'internal-a')",
                       (ISSUER, "subject-only"))
            for org, kind in (("llc_a", "llc"), ("llc_b", "llc"),
                              ("nonprofit", "nonprofit")):
                db.execute("INSERT INTO organizations VALUES (?, ?)", (org, kind))
                db.execute("INSERT INTO divisions VALUES (?, 'health')", (org,))
                db.execute("INSERT INTO units VALUES (?, 'maryland')", (org,))
            db.execute("INSERT INTO memberships VALUES ('internal-a', 'llc_a', 'active')")
            db.execute("INSERT INTO memberships VALUES ('internal-a', 'llc_b', 'active')")
            db.execute("INSERT INTO grants VALUES ('g1', 'internal-a', 'llc_a', "
                       "'records.read', 'health', 'maryland', 210)")
            db.execute("INSERT INTO portfolios VALUES ('family')")
            for org in ("llc_a", "llc_b", "nonprofit"):
                db.execute("INSERT INTO portfolio_organizations VALUES ('family', ?)",
                           (org,))
            db.execute("INSERT INTO portfolio_members VALUES ('family', 'internal-a')")
        self.path = path
        self.host = ReadOnlyContextApp(
            store=DurableContextStore(path), verifier=self.fake,
            clock=lambda: self.now, issuer=ISSUER, audience=AUDIENCE,
        )
        self.host_calls = 0
        self.custom_reply = None
        # This closure is the fake privileged host. Its bearer string is
        # never passed into the desktop projection or UI snapshot.
        def host_owned_fetch():
            self.host_calls += 1
            if self.custom_reply is not None:
                return self.custom_reply
            env = {}
            setup_testing_defaults(env)
            env.update({
                "PATH_INFO": "/v0/me/contexts", "QUERY_STRING": "",
                "SCRIPT_NAME": "", "REQUEST_METHOD": "GET",
                "CONTENT_LENGTH": "", "wsgi.input": BytesIO(b""),
                "HTTP_AUTHORIZATION": "Bearer private-host-test-token",
            })
            received = {}
            def start_response(status, headers):
                received["code"] = int(status.split(" ", 1)[0])
                received["type"] = dict(headers)["Content-Type"]
            raw = b"".join(self.host(env, start_response))
            return HostContextReply(received["code"], received["type"], raw)

        self.projection = DesktopContextProjection(
            host_fetch=host_owned_fetch, clock=lambda: self.now,
        )

    def test_starts_disconnected_no_fake_orgs(self):
        self.assertEqual(self.projection.snapshot(), {
            "schema": "post-apollo.identity.desktop-context-display.v0",
            "status": "NOT_CONNECTED", "organizations": [],
            "portfolios": [], "canSwitchOrganization": False,
        })
        self.assertEqual(self.host_calls, 0)

    def test_host_authenticated_api_fills_only_its_own_context(self):
        view = self.projection.refresh()
        self.assertEqual(view["status"], "READY")
        self.assertEqual([o["organizationId"] for o in view["organizations"]],
                         ["llc_a", "llc_b"])
        self.assertEqual(view["portfolios"][0]["organizationIds"],
                         ["llc_a", "llc_b"])
        self.assertNotIn("nonprofit", repr(view))
        self.assertFalse(view["canSwitchOrganization"])

    def test_projections_cannot_disclose_test_bearer_subject_or_internal_id(self):
        view = self.projection.refresh()
        for forbidden in ("private-host-test-token", "subject-only",
                          "session-synthetic", "internal-a", "accessToken",
                          "refreshToken", "jti", "sessionId", "grantId"):
            self.assertNotIn(forbidden, repr(view))
        self.assertNotIn("token", repr(vars(self.projection)).lower())

    def test_scope_previews_do_not_grant_an_operation(self):
        view = self.projection.refresh()
        self.assertEqual(view["organizations"][0]["scopeGrants"], [{
            "action": "records.read", "divisionId": "health",
            "unitId": "maryland", "expiresAt": 210,
        }])
        self.assertEqual(view["organizations"][1]["scopeGrants"], [])
        self.assertFalse(view["canSwitchOrganization"])

    def test_revoking_independent_membership_follows_next_refresh(self):
        self.assertEqual(len(self.projection.refresh()["organizations"]), 2)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE memberships SET state='revoked' "
                       "WHERE principal_id='internal-a' AND org_id='llc_a'")
        view = self.projection.refresh()
        self.assertEqual([o["organizationId"] for o in view["organizations"]],
                         ["llc_b"])
        self.assertEqual(view["portfolios"][0]["organizationIds"], ["llc_b"])

    def test_expired_rejected_session_erases_previous_success(self):
        self.assertEqual(self.projection.refresh()["status"], "READY")
        self.fake.revoke = True
        view = self.projection.refresh()
        self.assertEqual(view["status"], "SIGNED_OUT")
        self.assertEqual(view["organizations"], [])
        self.assertEqual(view["portfolios"], [])

    def test_unavailable_backend_erases_previous_success(self):
        self.assertEqual(self.projection.refresh()["status"], "READY")
        self.fake.offline = True
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")
        self.assertEqual(self.projection.snapshot()["organizations"], [])

    def test_clock_failure_erases_snapshot_and_never_fetches(self):
        self.assertEqual(self.projection.refresh()["status"], "READY")
        self.now = -1
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")
        self.assertEqual(self.projection.snapshot()["organizations"], [])

    def test_staleness_expires_before_bearer_or_permission_claim(self):
        self.assertEqual(self.projection.refresh()["status"], "READY")
        self.now = 129
        self.assertEqual(self.projection.snapshot()["status"], "READY")
        self.now = 130
        view = self.projection.snapshot()
        self.assertEqual(view["status"], "UNAVAILABLE")
        self.assertEqual(view["organizations"], [])

    def test_clock_rollback_erases_context(self):
        self.assertEqual(self.projection.refresh()["status"], "READY")
        self.now = 99
        self.assertEqual(self.projection.snapshot()["status"], "UNAVAILABLE")

    def test_expiring_display_grant_clears_entire_preview(self):
        self.now = 200
        self.assertEqual(self.projection.refresh()["status"], "READY")
        self.now = 210
        self.assertEqual(self.projection.snapshot()["status"], "UNAVAILABLE")
        self.assertEqual(self.projection.snapshot()["organizations"], [])

    def test_expired_grant_from_untrusted_server_is_rejected(self):
        self.custom_reply = reply(fixture_body())
        self.now = 210
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")

    def test_ui_cannot_modify_private_projection_with_snapshot_copy(self):
        first = self.projection.refresh()
        first["organizations"][0]["organizationId"] = "nonprofit"
        first["portfolios"][0]["organizationIds"].append("nonprofit")
        current = self.projection.snapshot()
        self.assertEqual(current["organizations"][0]["organizationId"], "llc_a")
        self.assertEqual(current["portfolios"][0]["organizationIds"],
                         ["llc_a", "llc_b"])

    def test_explicit_logout_disconnect_erases_company_information(self):
        self.projection.refresh()
        self.projection.disconnect()
        self.assertEqual(self.projection.snapshot()["status"], "NOT_CONNECTED")
        self.assertEqual(self.projection.snapshot()["organizations"], [])

    def test_empty_membership_is_not_authentication_denial(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE memberships SET state='revoked' "
                       "WHERE principal_id='internal-a'")
        view = self.projection.refresh()
        self.assertEqual(view["status"], "NO_MEMBERSHIPS")
        self.assertEqual(view["organizations"], [])
        self.assertFalse(view["canSwitchOrganization"])

    def test_non_json_or_oversized_or_invalid_status_never_exposed(self):
        self.projection.refresh()
        for bad in (
            HostContextReply(200, "text/html", b"<html>fake</html>"),
            HostContextReply(200, "application/json", b"x" * 65537),
            HostContextReply(500, "application/json", b'{"secret":"sql"}'),
            HostContextReply(200, "application/json", b'{"missing":"schema"}'),
            HostContextReply(True, "application/json", b"{}"),
            HostContextReply(200, "application/json",
                             b'{"status":"OK","status":"OK"}'),
        ):
            with self.subTest(status=bad.status_code, size=len(bad.body)):
                self.custom_reply = bad
                result = self.projection.refresh()
                self.assertEqual(result["status"], "UNAVAILABLE")
                self.assertEqual(result["organizations"], [])

    def test_injected_extra_user_fields_fail_closed_not_sanitized_into_view(self):
        for extra in (
            {"subject": "private"},
            {"accessToken": "private"},
            {"sessionId": "private"},
            {"role": "admin"},
        ):
            with self.subTest(extra=extra):
                self.custom_reply = reply({**fixture_body(), **extra})
                self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")

    def test_portfolio_cannot_add_unjoined_tenant(self):
        payload = fixture_body()
        payload["portfolios"][0]["organizationIds"].append("nonprofit")
        self.custom_reply = reply(payload)
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")

    def test_duplicate_ids_and_invalid_kinds_are_denied(self):
        payload = fixture_body()
        payload["organizations"].append(payload["organizations"][0])
        self.custom_reply = reply(payload)
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")
        payload = fixture_body()
        payload["organizations"][0]["kind"] = "admin"
        self.custom_reply = reply(payload)
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")

    def test_invalid_scopes_and_duplicate_grants_are_denied(self):
        payload = fixture_body()
        payload["organizations"][0]["scopeGrants"][0]["action"] = "records.delete"
        self.custom_reply = reply(payload)
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")
        payload = fixture_body()
        grant = payload["organizations"][0]["scopeGrants"][0]
        payload["organizations"][0]["scopeGrants"].append(dict(grant))
        self.custom_reply = reply(payload)
        self.assertEqual(self.projection.refresh()["status"], "UNAVAILABLE")

    def test_401_and_403_never_retain_prior_org(self):
        self.projection.refresh()
        for code in (401, 403):
            with self.subTest(code=code):
                self.custom_reply = HostContextReply(code, "application/json",
                                                     b'{"status":"DENIED"}')
                result = self.projection.refresh()
                self.assertEqual(result["status"], "SIGNED_OUT")
                self.assertEqual(result["organizations"], [])

    def test_unsolicited_transport_body_never_logged_or_echoed(self):
        self.custom_reply = HostContextReply(
            503, "application/json",
            b'{"details":"Bearer TOKEN_PRIVATE test DB error"}',
        )
        view = self.projection.refresh()
        self.assertEqual(view["status"], "UNAVAILABLE")
        self.assertNotIn("TOKEN_PRIVATE", repr(view))

    def test_constructor_rejects_missing_trusted_host(self):
        for fetch, clock in ((None, lambda: 100), (lambda: None, None)):
            with self.assertRaises(ValueError):
                DesktopContextProjection(host_fetch=fetch, clock=clock)


if __name__ == "__main__":
    unittest.main()
