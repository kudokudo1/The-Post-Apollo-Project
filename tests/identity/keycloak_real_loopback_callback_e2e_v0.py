"""Genuine disposable Keycloak redirect -> CI loopback receiver -> Organizations.

The browser is simulated by the existing cookie-preserving login-form test.
The REAL Keycloak-issued redirect is delivered to the REAL 127.0.0.1:8765
callback listener, not constructed from a fake code or state.

IMPORTANT: Keycloak in disposable CI runs over HTTP at 127.0.0.1:8080.
This test uses a TEST-OWNED host callback and never weakens the HTTPS-only
TrustedHostConfig, deploys a service, registers real users, or touches QML.
Native desktop process isolation, token exchange implementation and secure
system-browser hosting remain separate, unapproved production work.
"""
from __future__ import annotations

import argparse
import hmac
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit
from wsgiref.simple_server import make_server

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
sys.path.insert(0, str(ROOT / "tests" / "identity"))

from desktop_context_projection_v0 import DesktopContextProjection, HostContextReply
from durable_context_store_v0 import DurableContextStore
from keycloak_loopback_pilot_verifier_v0 import LoopbackKeycloakPilotVerifier
from native_loopback_callback_v0 import LoopbackCallbackReceiver
from read_only_context_wsgi_v0 import ReadOnlyContextApp
from keycloak_durable_context_e2e_v0 import (
    _real_keycloak, _seed_synthetic_database, _update_fixture, _request,
)
from keycloak_real_oidc_pilot_v0 import (
    API_AUDIENCE, CALLBACK, CLIENT_ID, ISSUER, exchange, open_provider,
    require, verify_id_token, verify_loopback_url,
)


def main(fixture_dir: Path) -> None:
    fixture = json.loads((fixture_dir / "runtime.json").read_text())
    metadata = _real_keycloak(ISSUER + "/.well-known/openid-configuration")
    jwks = requests.get(metadata["jwks_uri"], timeout=15).json()
    private: dict[str, object] = {}
    shown_http: list[bytes] = []

    def active(value: str) -> bool:
        reply = requests.post(
            metadata["introspection_endpoint"],
            data={"token": value},
            auth=(API_AUDIENCE, fixture["introspection_secret"]),
            allow_redirects=False,
            timeout=15,
        )
        require(reply.status_code == 200, "Real confidential introspection failed")
        status = reply.json().get("active")
        require(type(status) is bool, "Keycloak did not decide active status")
        return status

    verifier = LoopbackKeycloakPilotVerifier(
        issuer=ISSUER, audience=API_AUDIENCE, client_id=CLIENT_ID,
        trusted_jwks=jwks, token_active=active,
    )

    def host_owned_callback(uri: str) -> dict[str, object]:
        """Test host validates actual browser callback and signed tokens."""
        parts = urlsplit(uri)
        require(uri.startswith(CALLBACK + "?")
                and parts.fragment == "",
                "OAuth browser callback URI escaped loopback")
        values = parse_qs(parts.query, keep_blank_values=True)
        require("error" not in values, "Keycloak returned an OAuth error")
        require(values.get("state") and len(values["state"]) == 1
                and hmac.compare_digest(
                    values["state"][0], str(private["state"])
                ), "OAuth state or CSRF mismatch")
        require(values.get("iss") == [ISSUER],
                "Keycloak issuer mix-up check failed")
        require(values.get("code") and len(values["code"]) == 1,
                "Real Keycloak authorization code missing")
        require(set(values) <= {"code", "state", "iss", "session_state"},
                "Unexpected callback authority fields")

        answer = exchange(
            metadata, values["code"][0], str(private["verifier"])
        )
        require(answer.status_code == 200,
                "Actual browser callback code+PKCE exchange failed")
        tokens = answer.json()
        for field in ("access_token", "id_token", "refresh_token"):
            require(type(tokens.get(field)) is str and tokens[field],
                    "Keycloak did not supply required signed token")
        verified_id = verify_id_token(
            tokens["id_token"], jwks, str(private["nonce"])
        )
        access = tokens["access_token"]
        signed = verifier.verify(access, now=int(time.time()))
        require(signed is not None
                and signed.principal_id == verified_id["sub"]
                and active(access),
                "Real signed Keycloak access token/ID subject rejected")
        private["access"] = access
        private["refresh"] = tokens["refresh_token"]
        private["subject"] = signed.principal_id
        return {"status": "SIGNED_IN"}

    def deliver_real_redirect(target: str, verifier_string: str,
                              nonce: str, state: str) -> None:
        """Browser simulation follows the exact Keycloak Location header."""
        require(target.startswith(CALLBACK + "?"),
                "IdP attempted redirect to an unregistered receiver")
        verify_loopback_url(target)
        private.update({
            "verifier": verifier_string,
            "nonce": nonce,
            "state": state,
        })
        # No cookie, Authorization header or IdP credentials are sent to
        # callback. Only the one-time code and state from Keycloak.
        response = requests.get(
            target, allow_redirects=False, timeout=15,
            headers={"Accept": "text/plain"},
        )
        shown_http.append(response.content)
        require(response.status_code == 200,
                "Genuine IdP browser redirect rejected by CI callback")
        require(response.headers.get("Cache-Control") == "no-store",
                "Callback confirmation may not be cached")
        require("Location" not in response.headers,
                "Callback cannot redirect to credential-leaking target")

    # This port is fixed ONLY to match the existing disposable Keycloak realm
    # registration. Normal receiver startup still uses ephemeral port 0.
    with LoopbackCallbackReceiver(
        callback=host_owned_callback, port=8765,
    ) as receiver:
        require(receiver.redirect_uri == CALLBACK,
                "Receiver port mismatched disposable Keycloak registration")

        # This helper automates the disposable Keycloak browser login form,
        # retains the exact real redirect and actually GETs the receiver.
        returned_code, expected_verifier, expected_nonce = open_provider(
            metadata, fixture["username"], fixture["password"],
            on_redirect=deliver_real_redirect,
        )
        require(returned_code and private.get("access")
                and private.get("verifier") == expected_verifier
                and private.get("nonce") == expected_nonce,
                "Callback did not complete actual signed exchange")
        access = str(private["access"])
        require(access not in repr(shown_http)
                and access not in repr(receiver.redirect_uri),
                "Callback HTTP response leaked a bearer token")

        # Receiver consumes the genuine Keycloak redirect exactly once.
        require(requests.get(
            receiver.redirect_uri + "?code=replay&state=bad&iss=" + ISSUER,
            timeout=10, allow_redirects=False,
        ).status_code == 410,
                "Callback was replayable after genuine provider login")

        with tempfile.TemporaryDirectory(prefix="post-apollo-receiver-e2e-") as tmp:
            path = Path(tmp) / "tenant-fixture.sqlite"
            _seed_synthetic_database(path)
            api = ReadOnlyContextApp(
                store=DurableContextStore(path), verifier=verifier,
                clock=lambda: int(time.time()), issuer=ISSUER,
                audience=API_AUDIENCE,
            )
            server = make_server("127.0.0.1", 0, api)
            worker = threading.Thread(
                target=server.serve_forever, daemon=True,
            )
            worker.start()
            try:
                port = server.server_port

                # Auth success does not create a Post-Apollo person. Only
                # explicit trusted issuer+subject mapping does.
                status, body = _request(port, access)
                require(status == 401 and body == {"status": "DENIED"},
                        "Unmapped genuine IdP account gained company access")
                _update_fixture(
                    path,
                    "INSERT INTO provider_subjects VALUES (?, ?, ?)",
                    (ISSUER, private["subject"], "internal-worker"),
                )

                def host_fetch() -> HostContextReply:
                    status, body = _request(port, access)
                    return HostContextReply(
                        status, "application/json",
                        json.dumps(body, separators=(",", ":")).encode("utf-8"),
                    )

                display = DesktopContextProjection(
                    host_fetch=host_fetch, clock=lambda: int(time.time()),
                )
                view = display.refresh()
                require(view["status"] == "READY"
                        and [x["organizationId"] for x in view["organizations"]]
                        == ["llc_a", "llc_b"]
                        and view["portfolios"] == [{
                            "portfolioId": "family",
                            "organizationIds": ["llc_a", "llc_b"],
                        }]
                        and view["canSwitchOrganization"] is False,
                        "Real callback cannot reach authorized tokenless display")
                require("nonprofit" not in repr(view)
                        and "unrelated_customer" not in repr(view)
                        and access not in repr(view)
                        and str(private["subject"]) not in repr(view),
                        "Tokenless display revealed another tenant or credential")

                _update_fixture(
                    path,
                    "UPDATE memberships SET state='revoked' "
                    "WHERE principal_id='internal-worker' AND org_id='llc_a'",
                )
                current = display.refresh()
                require(current["status"] == "READY"
                        and [x["organizationId"] for x in current["organizations"]]
                        == ["llc_b"],
                        "Revoked LLC survived read-only display refresh")

                # Keycloak real logout makes previously valid bearer inactive;
                # no cached organization data may survive another refresh.
                logout = requests.post(
                    ISSUER + "/protocol/openid-connect/logout",
                    data={
                        "client_id": CLIENT_ID,
                        "refresh_token": private["refresh"],
                    },
                    timeout=15, allow_redirects=False,
                )
                require(logout.status_code in (200, 204)
                        and not active(access),
                        "Real Keycloak logout did not revoke session")
                closed = display.refresh()
                require(closed["status"] == "SIGNED_OUT"
                        and closed["organizations"] == []
                        and closed["portfolios"] == []
                        and closed["canSwitchOrganization"] is False,
                        "Organizations remained visible after IdP logout")
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)

    print("PASS: real disposable Keycloak redirect delivered to 127.0.0.1 callback")
    print("PASS: genuine authorization code + S256 PKCE + signed ID/access verification")
    print("PASS: tokenless authorized Organizations, membership revocation and IdP logout")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, required=True)
    args = parser.parse_args()
    main(args.fixture_dir)
