"""Disposable end-to-end REAL Keycloak -> verified JWT -> persisted Organizations.

This script is run ONLY by an isolated CI workflow with the test realm in
keycloak_pilot_fixture_v0.py. It never registers real staff or starts public
listeners. The verifier is the already-reviewed *loopback-only pilot* adapter;
not a production credential/session host or a chosen IdP vendor.
"""
from __future__ import annotations

import argparse
import http.client
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
from wsgiref.simple_server import make_server

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
sys.path.insert(0, str(ROOT / "tests" / "identity"))

from durable_context_store_v0 import DurableContextStore, CONTEXT_SCHEMA
from keycloak_loopback_pilot_verifier_v0 import LoopbackKeycloakPilotVerifier
from read_only_context_wsgi_v0 import ReadOnlyContextApp
from keycloak_real_oidc_pilot_v0 import (
    ISSUER, API_AUDIENCE, CLIENT_ID, exchange, open_provider, require,
    verify_id_token, verify_loopback_url,
)

ENDPOINT = "/v0/me/contexts"


def _seed_synthetic_database(path: Path) -> None:
    """Test administrator only; no admin/writer endpoint is exposed to users."""
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(
            (ROOT / "services/identity/durable_context_schema_v0.sql").read_text()
        )
        db.execute("INSERT INTO principals VALUES ('internal-worker')")
        for org, kind in (("llc_a", "llc"), ("llc_b", "llc"),
                          ("nonprofit", "nonprofit"),
                          ("unrelated_customer", "customer")):
            db.execute("INSERT INTO organizations VALUES (?, ?)", (org, kind))
            db.execute("INSERT INTO divisions VALUES (?, 'health')", (org,))
            db.execute("INSERT INTO units VALUES (?, 'maryland')", (org,))
        for org in ("llc_a", "llc_b"):
            db.execute(
                "INSERT INTO memberships VALUES ('internal-worker', ?, 'active')",
                (org,),
            )
        db.execute(
            """INSERT INTO grants
               VALUES ('test-read', 'internal-worker', 'llc_a',
                       'records.read', 'health', 'maryland', NULL)"""
        )
        db.execute("INSERT INTO portfolios VALUES ('family')")
        for org in ("llc_a", "llc_b", "nonprofit"):
            db.execute(
                "INSERT INTO portfolio_organizations VALUES ('family', ?)",
                (org,),
            )
        db.execute(
            "INSERT INTO portfolio_members VALUES ('family', 'internal-worker')"
        )


def _update_fixture(path: Path, query: str, params: tuple = ()) -> None:
    """Synthetic test admin only, independent of the read-only HTTP handler."""
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute(query, params)


def _request(port: int, access_token: str, *,
             url: str = ENDPOINT, method: str = "GET",
             extra_headers: dict[str, str] | None = None) -> tuple[int, dict]:
    require(isinstance(port, int) and 1 <= port <= 65535,
            "CI API port must be loopback ephemeral")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    try:
        conn.request(method, url, headers=headers)
        response = conn.getresponse()
        body = json.loads(response.read())
        require(response.getheader("Cache-Control") == "no-store",
                "Authenticated company summary must not be cached")
        return response.status, body
    finally:
        conn.close()


def _real_keycloak(discovery_url: str) -> dict:
    verify_loopback_url(discovery_url)
    for _ in range(90):
        try:
            response = requests.get(discovery_url, timeout=2)
            if response.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(2)
    else:
        raise AssertionError("Disposable Keycloak failed its readiness check")
    metadata = response.json()
    require(metadata.get("issuer") == ISSUER,
            "Keycloak discovery issuer mismatch")
    for name in ("jwks_uri", "token_endpoint", "authorization_endpoint",
                 "introspection_endpoint", "end_session_endpoint"):
        verify_loopback_url(metadata[name])
    return metadata


def main(fixture_dir: Path) -> None:
    fixture = json.loads((fixture_dir / "runtime.json").read_text())
    metadata = _real_keycloak(
        ISSUER + "/.well-known/openid-configuration"
    )
    jwks = requests.get(metadata["jwks_uri"], timeout=15).json()

    # Actual Keycloak code grant: browser-form + state/nonce + S256 challenge,
    # real token endpoint. No password grant or admin-created user session.
    code, code_verifier, nonce = open_provider(
        metadata, fixture["username"], fixture["password"]
    )
    token_response = exchange(metadata, code, code_verifier)
    require(token_response.status_code == 200,
            "Real Keycloak PKCE token exchange was rejected")
    result = token_response.json()
    access = result["access_token"]
    id_token = result["id_token"]
    refresh_token = result["refresh_token"]
    id_claims = verify_id_token(id_token, jwks, nonce)

    # Authenticated confidential introspection, never via a client-supplied URL.
    def active(value: str) -> bool:
        answer = requests.post(
            metadata["introspection_endpoint"],
            data={"token": value},
            auth=(API_AUDIENCE, fixture["introspection_secret"]),
            timeout=15,
            allow_redirects=False,
        )
        require(answer.status_code == 200,
                "Disposable Keycloak confidential introspection failed")
        value = answer.json().get("active")
        require(type(value) is bool, "No Keycloak introspection decision")
        return value

    verifier = LoopbackKeycloakPilotVerifier(
        issuer=ISSUER, audience=API_AUDIENCE, client_id=CLIENT_ID,
        trusted_jwks=jwks, token_active=active,
    )
    require(active(access), "New Keycloak session unexpectedly inactive")
    signed_session = verifier.verify(access, now=int(time.time()))
    require(signed_session is not None, "Signed access token failed verification")
    require(signed_session.principal_id == id_claims["sub"],
            "Keycloak access and ID subjects do not match")

    with tempfile.TemporaryDirectory(prefix="post-apollo-idp-api-v0-") as root:
        path = Path(root) / "tenant-test.sqlite"
        _seed_synthetic_database(path)
        store = DurableContextStore(path)
        app = ReadOnlyContextApp(
            store=store, verifier=verifier, clock=lambda: int(time.time()),
            issuer=ISSUER, audience=API_AUDIENCE,
        )
        # This is the only network listener, bound to localhost and a random
        # temporary port for the lifetime of this CI process.
        server = make_server("127.0.0.1", 0, app)
        task = threading.Thread(target=server.serve_forever, daemon=True)
        task.start()
        try:
            port = server.server_port
            # Valid signed token is NOT enough without a trusted explicit
            # issuer+subject -> internal principal enrollment.
            code, body = _request(port, access)
            require(code == 401 and body == {"status": "DENIED"},
                    "Unmapped real Keycloak subject was accepted")

            _update_fixture(
                path,
                "INSERT INTO provider_subjects VALUES (?, ?, ?)",
                (ISSUER, signed_session.principal_id, "internal-worker"),
            )
            code, body = _request(port, access)
            require(code == 200 and body.get("schema") == CONTEXT_SCHEMA,
                    "Mapped signed Keycloak token did not reach durable API")
            require([org["organizationId"] for org in body["organizations"]]
                    == ["llc_a", "llc_b"],
                    "Verified user has incorrect company membership summary")
            require([org["kind"] for org in body["organizations"]]
                    == ["llc", "llc"],
                    "Wrong tenant kind returned")
            require(body["organizations"][0]["scopeGrants"] == [{
                "action": "records.read", "divisionId": "health",
                "unitId": "maryland", "expiresAt": None,
            }], "Expected intersecting division/geography grant was lost")
            require(body["organizations"][1]["scopeGrants"] == [],
                    "Membership without a grant must stay grantless")
            require(body["portfolios"] == [{
                "portfolioId": "family", "organizationIds": ["llc_a", "llc_b"],
            }], "Portfolio leaked the unrelated nonprofit")
            require("unrelated_customer" not in repr(body)
                    and "nonprofit" not in repr(body)
                    and signed_session.principal_id not in repr(body)
                    and "internal-worker" not in repr(body),
                    "Private identity or unrelated organizations leaked")

            # No caller-controlled "admin", organization or identity selection.
            for value in (
                ENDPOINT + "?organizationId=nonprofit",
                ENDPOINT + "?principalId=another-person",
                ENDPOINT + "?role=admin",
            ):
                status, output = _request(port, access, url=value)
                require(status == 400 and output == {"status": "DENIED"},
                        "Client query managed to override provider identity")
            status, output = _request(port, access, method="POST")
            require(status == 405 and output == {"status": "DENIED"},
                    "Read-only endpoint accepted a write method")

            # Persisted independently-authorized offboarding becomes visible
            # at the next request with NO token change or frontend assistance.
            _update_fixture(
                path,
                """UPDATE memberships SET state='revoked'
                   WHERE principal_id='internal-worker' AND org_id='llc_a'"""
            )
            status, body = _request(port, access)
            require(status == 200 and
                    [x["organizationId"] for x in body["organizations"]]
                    == ["llc_b"],
                    "File-backed membership revocation was not re-read")
            require(body["portfolios"] == [{
                "portfolioId": "family", "organizationIds": ["llc_b"],
            }], "Revoked organization remains visible through portfolio")

            # Keycloak logout must invalidate the ORIGINAL still-signed access
            # token at the HTTP layer via live server introspection.
            logout = ISSUER + "/protocol/openid-connect/logout"
            answer = requests.post(logout, data={
                "client_id": CLIENT_ID, "refresh_token": refresh_token,
            }, timeout=15, allow_redirects=False)
            require(answer.status_code in (200, 204),
                    "Disposable Keycloak logout failed")
            require(not active(access),
                    "Keycloak still reports access token active after logout")
            status, output = _request(port, access)
            require(status == 401 and output == {"status": "DENIED"},
                    "Revoked IdP session accessed the persisted organizations")
        finally:
            server.shutdown()
            server.server_close()
            task.join(timeout=10)

    # Never print the bearer token, IDs, passwords or authorization code.
    print("PASS: genuine Keycloak S256 PKCE -> signed JWT -> issuer+subject mapping")
    print("PASS: real authenticated GET /v0/me/contexts and per-tenant grant isolation")
    print("PASS: durable membership revocation and post-logout token denial")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, required=True)
    args = parser.parse_args()
    main(args.fixture_dir)
