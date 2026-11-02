"""Disposable file-backed SQLite + authenticated WSGI current-user contract.

This is a test harness, NOT production auth/hosting/storage. A fake verifier
is injected by the test suite only. Real production users are never involved.
"""
from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path
import http.client
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from durable_context_store_v0 import DurableContextStore, CONTEXT_SCHEMA
from read_only_context_wsgi_v0 import ReadOnlyContextApp
from synthetic_request_boundary_v0 import VerifiedSession

ISSUER = "https://idp.test.invalid/realm"
AUDIENCE = "post-apollo-context-test"


class FakeSessionVerifier:
    """Fixture-only; a real protected host must validate cryptographic tokens."""
    def __init__(self):
        self.sessions = {}
        self.revoked = set()
        self.fail = False

    def verify(self, token, *, now):
        if self.fail:
            raise RuntimeError("simulated IdP failure")
        return None if token in self.revoked else self.sessions.get(token)


class DurableContextEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "tenant-test.sqlite"
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(
            (ROOT / "services/identity/durable_context_schema_v0.sql").read_text()
        )
        for who in ("internal-operator", "internal-charity",
                    "internal-customer", "internal-no-org"):
            conn.execute("INSERT INTO principals VALUES (?)", (who,))
        for issuer, sub, who in (
            (ISSUER, "subject-operator", "internal-operator"),
            (ISSUER, "subject-charity", "internal-charity"),
            (ISSUER, "subject-customer", "internal-customer"),
            (ISSUER, "subject-empty", "internal-no-org"),
            ("https://second-idp.invalid", "subject-operator", "internal-customer"),
        ):
            conn.execute("INSERT INTO provider_subjects VALUES (?, ?, ?)",
                         (issuer, sub, who))
        for org, kind in (("llc_a", "llc"), ("llc_b", "llc"),
                          ("nonprofit", "nonprofit"),
                          ("external", "customer")):
            conn.execute("INSERT INTO organizations VALUES (?, ?)", (org, kind))
            for division in ("health", "sales"):
                conn.execute("INSERT INTO divisions VALUES (?, ?)",
                             (org, division))
            for unit in ("md", "va"):
                conn.execute("INSERT INTO units VALUES (?, ?)", (org, unit))
        for principal, org in (
            ("internal-operator", "llc_a"), ("internal-operator", "llc_b"),
            ("internal-charity", "nonprofit"),
            ("internal-customer", "external"),
        ):
            conn.execute("INSERT INTO memberships VALUES (?, ?, 'active')",
                         (principal, org))
        for values in (
            ("g-a", "internal-operator", "llc_a", "records.read", "health", None, None),
            ("g-b", "internal-operator", "llc_b", "records.read", None, "md", None),
            ("g-charity", "internal-charity", "nonprofit", "records.read",
             "health", None, None),
            ("g-customer", "internal-customer", "external", "records.write",
             None, None, None),
        ):
            conn.execute("INSERT INTO grants VALUES (?, ?, ?, ?, ?, ?, ?)", values)
        for portfolio in ("family", "independent"):
            conn.execute("INSERT INTO portfolios VALUES (?)", (portfolio,))
        for org in ("llc_a", "llc_b", "nonprofit"):
            conn.execute("INSERT INTO portfolio_organizations VALUES (?, ?)",
                         ("family", org))
        conn.execute("INSERT INTO portfolio_organizations VALUES (?, ?)",
                     ("independent", "external"))
        for principal in ("internal-operator", "internal-charity", "internal-no-org"):
            conn.execute("INSERT INTO portfolio_members VALUES (?, ?)",
                         ("family", principal))
        conn.execute("INSERT INTO portfolio_members VALUES (?, ?)",
                     ("independent", "internal-operator"))
        conn.commit()
        conn.close()

        self.now = 100
        self.verifier = FakeSessionVerifier()
        for name, sub in (
            ("operator", "subject-operator"), ("charity", "subject-charity"),
            ("customer", "subject-customer"), ("empty", "subject-empty"),
            ("unmapped", "never-provisioned"),
        ):
            self.verifier.sessions["token-" + name] = VerifiedSession(
                principal_id=sub, issuer=ISSUER, audience=AUDIENCE,
                session_id="session-" + name, issued_at=10, expires_at=200,
            )
        self.store = DurableContextStore(self.path)
        self.app = ReadOnlyContextApp(
            store=self.store, verifier=self.verifier, clock=lambda: self.now,
            issuer=ISSUER, audience=AUDIENCE,
        )

    def write(self, sql, *params):
        # This is a TRUSTED TEST ADMIN connection, not exposed to WSGI.
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(sql, params)

    def invoke(self, token="token-operator", method="GET",
               path="/v0/me/contexts", query="", extra=None,
               authorization=None, length=None):
        environ = {}
        setup_testing_defaults(environ)
        environ.update({
            "REQUEST_METHOD": method, "PATH_INFO": path,
            "QUERY_STRING": query, "SCRIPT_NAME": "",
            "wsgi.input": BytesIO(b""),
            "CONTENT_LENGTH": "" if length is None else length,
        })
        if token is not None:
            environ["HTTP_AUTHORIZATION"] = (
                "Bearer " + token if authorization is None else authorization
            )
        elif authorization is not None:
            environ["HTTP_AUTHORIZATION"] = authorization
        if extra:
            environ.update(extra)
        output = {}
        def start_response(status, headers):
            output["status"] = status
            output["headers"] = dict(headers)
        body = b"".join(self.app(environ, start_response))
        output["body"] = json.loads(body)
        return output

    def test_file_persists_across_new_store_instances(self):
        old = self.store.summary(ISSUER, "subject-operator", now=100)
        newer = DurableContextStore(self.path).summary(
            ISSUER, "subject-operator", now=100,
        )
        self.assertEqual(old, newer)
        self.assertEqual([x["organizationId"] for x in old["organizations"]],
                         ["llc_a", "llc_b"])

    def test_signed_in_issuer_subject_resolves_internal_principal(self):
        response = self.invoke()
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(response["body"]["schema"], CONTEXT_SCHEMA)
        self.assertEqual(len(response["body"]["organizations"]), 2)
        self.assertNotIn("subject-operator", repr(response["body"]))
        self.assertNotIn("internal-operator", repr(response["body"]))

    def test_grant_summaries_preserve_function_vs_geography(self):
        orgs = self.invoke()["body"]["organizations"]
        self.assertEqual(orgs[0]["scopeGrants"], [{
            "action": "records.read", "divisionId": "health",
            "unitId": None, "expiresAt": None,
        }])
        self.assertEqual(orgs[1]["scopeGrants"], [{
            "action": "records.read", "divisionId": None,
            "unitId": "md", "expiresAt": None,
        }])

    def test_portfolio_does_not_expose_nonmember_org(self):
        response = self.invoke()["body"]
        self.assertEqual(response["portfolios"], [{
            "portfolioId": "family", "organizationIds": ["llc_a", "llc_b"],
        }])
        self.assertNotIn("nonprofit", repr(response))
        self.assertNotIn("external", repr(response))

    def test_customer_and_nonprofit_isolation(self):
        charity = self.invoke("token-charity")["body"]
        self.assertEqual([x["organizationId"] for x in charity["organizations"]],
                         ["nonprofit"])
        self.assertEqual(charity["portfolios"][0]["organizationIds"], ["nonprofit"])
        customer = self.invoke("token-customer")["body"]
        self.assertEqual([x["organizationId"] for x in customer["organizations"]],
                         ["external"])
        self.assertEqual(customer["portfolios"], [])
        self.assertNotIn("family", repr(customer))

    def test_provisioned_identity_with_no_membership_gets_empty_success(self):
        result = self.invoke("token-empty")
        self.assertEqual(result["status"], "200 OK")
        self.assertEqual(result["body"]["organizations"], [])
        self.assertEqual(result["body"]["portfolios"], [])

    def test_unprovisioned_external_subject_gets_denied(self):
        self.assertEqual(self.invoke("token-unmapped")["status"],
                         "401 Unauthorized")
        self.assertEqual(self.invoke("token-unmapped")["body"],
                         {"status": "DENIED"})

    def test_issuer_subject_key_prevents_cross_provider_collision(self):
        self.assertEqual(len(self.invoke()["body"]["organizations"]), 2)
        second = DurableContextStore(self.path).summary(
            "https://second-idp.invalid", "subject-operator", now=100,
        )
        self.assertEqual([x["organizationId"] for x in second["organizations"]],
                         ["external"])

    def test_revocation_stored_on_disk_takes_effect_next_request(self):
        self.assertEqual(self.invoke()["status"], "200 OK")
        self.write("UPDATE memberships SET state='revoked' "
                   "WHERE principal_id=? AND org_id=?",
                   "internal-operator", "llc_a")
        body = self.invoke()["body"]
        self.assertEqual([x["organizationId"] for x in body["organizations"]],
                         ["llc_b"])
        self.assertEqual(body["portfolios"][0]["organizationIds"], ["llc_b"])
        # Revoked membership does not remove the independently active B.
        self.assertEqual(self.invoke()["status"], "200 OK")

    def test_expired_scope_is_no_longer_disclosed_after_clock_advance(self):
        self.write("INSERT INTO grants VALUES (?, ?, ?, ?, ?, ?, ?)",
                   "expiry", "internal-operator", "llc_a",
                   "records.write", "sales", "va", 105)
        self.assertEqual(len(self.invoke()["body"]["organizations"][0]["scopeGrants"]), 2)
        self.now = 105
        self.assertEqual(len(self.invoke()["body"]["organizations"][0]["scopeGrants"]), 1)

    def test_active_membership_without_grant_is_visible_but_not_authorization(self):
        self.write("INSERT INTO memberships VALUES (?, ?, 'active')",
                   "internal-operator", "external")
        org = self.invoke()["body"]["organizations"][-1]
        self.assertEqual(org["organizationId"], "external")
        self.assertEqual(org["scopeGrants"], [])

    def test_revoked_session_fails_closed(self):
        self.verifier.revoked.add("token-operator")
        self.assertEqual(self.invoke()["status"], "401 Unauthorized")
        self.assertEqual(self.invoke()["body"], {"status": "DENIED"})

    def test_issuer_audience_expiry_and_bad_clock_fail(self):
        original = self.verifier.sessions["token-operator"]
        for changed in (
            {"issuer": "https://evil.invalid"},
            {"audience": "another-api"},
            {"issued_at": 101},
            {"session_id": ""},
            {"expires_at": 100},
            {"issued_at": True},
        ):
            self.verifier.sessions["token-operator"] = replace(original, **changed)
            with self.subTest(changed=changed):
                self.assertEqual(self.invoke()["status"], "401 Unauthorized")
        self.verifier.sessions["token-operator"] = original
        self.now = 200
        self.assertEqual(self.invoke()["status"], "401 Unauthorized")

    def test_anonymous_unknown_and_invalid_bearer_headers_denied(self):
        self.assertEqual(self.invoke(None)["status"], "401 Unauthorized")
        for value in ("Bearer", "Basic x", "bearer token-operator",
                      "Bearer  token-operator", "Bearer token-operator extra",
                      "Bearer token-operator\nX-Injected:yes",
                      "Bearer " + "x"*8193):
            with self.subTest(value=value[:16]):
                self.assertEqual(self.invoke(authorization=value)["status"],
                                 "401 Unauthorized")
        self.assertEqual(self.invoke("random")["status"], "401 Unauthorized")

    def test_query_string_cannot_override_user_company_or_role(self):
        for q in ("principalId=internal-charity", "organizationId=nonprofit",
                  "portfolioId=family", "now=10", "role=owner"):
            with self.subTest(q=q):
                self.assertEqual(self.invoke(query=q)["status"], "400 Bad Request")
        forged = self.invoke(extra={
            "HTTP_X_PRINCIPAL_ID": "internal-charity",
            "HTTP_X_ORGANIZATION_ID": "nonprofit",
            "HTTP_X_ROLE": "admin",
        })
        self.assertEqual(forged["status"], "200 OK")
        self.assertEqual([o["organizationId"] for o in forged["body"]["organizations"]],
                         ["llc_a", "llc_b"])

    def test_post_put_delete_and_unknown_paths_are_refused(self):
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            self.assertEqual(self.invoke(method=method)["status"],
                             "405 Method Not Allowed")
        self.assertEqual(self.invoke(path="/admin")["status"], "404 Not Found")
        self.assertEqual(self.invoke(length="22")["status"], "400 Bad Request")

    def test_response_headers_never_allow_client_caching_or_cors(self):
        result = self.invoke()
        h = result["headers"]
        self.assertEqual(h["Cache-Control"], "no-store")
        self.assertEqual(h["Vary"], "Authorization")
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Access-Control-Allow-Origin", h)
        self.assertNotIn("Set-Cookie", h)

    def test_reader_refuses_to_create_or_migrate_unknown_database(self):
        with self.assertRaises(ValueError):
            DurableContextStore(Path("relative.db"))
        with self.assertRaises(ValueError):
            DurableContextStore(Path(self.temp.name) / "missing.sqlite")
        self.write("PRAGMA user_version=9")
        with self.assertRaises(ValueError):
            DurableContextStore(self.path)

    def test_db_failure_fails_closed_without_error_or_private_paths(self):
        self.path.unlink()
        result = self.invoke()
        self.assertEqual(result["status"], "503 Service Unavailable")
        self.assertEqual(result["body"], {"status": "DENIED"})
        self.assertNotIn(str(self.path), repr(result))

    def test_verified_session_is_not_the_same_as_grant(self):
        self.write("UPDATE memberships SET state='revoked' "
                   "WHERE principal_id=?", "internal-operator")
        body = self.invoke()["body"]
        self.assertEqual(body["organizations"], [])
        self.assertEqual(body["portfolios"], [])
        self.assertEqual(self.invoke()["status"], "200 OK")

    def test_wsgiref_loopback_http_request_reaches_real_endpoint(self):
        # Actual HTTP transport only inside temporary CI loopback. WSGI app
        # does not start a listener and never binds to 0.0.0.0.
        server = make_server("127.0.0.1", 0, self.app)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port,
                                              timeout=5)
            try:
                conn.request("GET", "/v0/me/contexts",
                             headers={"Authorization": "Bearer token-operator"})
                resp = conn.getresponse()
                body = json.loads(resp.read())
                self.assertEqual(resp.status, 200)
                self.assertEqual([o["organizationId"] for o in body["organizations"]],
                                 ["llc_a", "llc_b"])
            finally:
                conn.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    def test_invalid_schema_and_duplicate_identity_binding_are_rejected(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO provider_subjects VALUES (?, ?, ?)",
                             (ISSUER, "subject-operator", "internal-customer"))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO memberships VALUES (?, ?, 'active')",
                             ("missing-principal", "llc_a"))


if __name__ == "__main__":
    unittest.main()
