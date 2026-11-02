"""LIVE Keycloak disposable CI integration: authorization code + PKCE only.

A genuine Keycloak container issues tokens. This test uses a cookie-preserving
HTTP form client to simulate the browser's login interaction with a synthetic
user. It never uses resource-owner password grant or talks to a real service.
Not discovered by normal unittest; requires approved isolated CI Keycloak.
"""
from __future__ import annotations

import argparse
import base64
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import secrets
import sys
import time
from urllib.parse import parse_qs, urljoin, urlparse

import jwt
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from synthetic_policy_v0 import SyntheticPolicyStore
from synthetic_request_boundary_v0 import SyntheticRequestBoundary, SCHEMA
from keycloak_loopback_pilot_verifier_v0 import LoopbackKeycloakPilotVerifier


BASE = "http://127.0.0.1:8080"
ISSUER = BASE + "/realms/post-apollo-disposable"
CLIENT_ID = "post-apollo-pilot-public"
API_AUDIENCE = "post-apollo-pilot-api"
CALLBACK = "http://127.0.0.1:8765/callback"


def require(test: bool, description: str) -> None:
    if not test:
        raise AssertionError(description)


class LoginForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.form_action = None
        self.hidden: dict[str, str] = {}
        self.in_login = False

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag == "form" and (fields.get("id") == "kc-form-login"
                              or "login-actions/authenticate" in fields.get("action", "")):
            self.form_action = fields.get("action")
            self.in_login = True
        elif tag == "input" and self.in_login and fields.get("type") == "hidden":
            name = fields.get("name")
            if name:
                self.hidden[name] = fields.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.in_login = False


def verify_loopback_url(url: str) -> None:
    parts = urlparse(url)
    require(parts.scheme == "http" and parts.hostname == "127.0.0.1"
            and parts.port in (8080, 8765)
            and not parts.username and not parts.password,
            "Unexpected non-loopback URL; refusing request or redirect")


def open_provider(discovery: dict, username: str, password: str):
    """Perform real interactive auth-code flow with a new cookie jar."""
    session = requests.Session()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    state = secrets.token_urlsafe(20)
    nonce = secrets.token_urlsafe(20)
    url = discovery["authorization_endpoint"]
    verify_loopback_url(url)
    login_page = session.get(url, params={
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK,
        "response_type": "code",
        "scope": "openid",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "nonce": nonce,
    }, timeout=15)
    require(login_page.status_code == 200, "Keycloak did not serve login page")
    form = LoginForm()
    form.feed(login_page.text)
    require(form.form_action is not None,
            "Expected actual Keycloak authorization-code login form")
    login_url = urljoin(login_page.url, form.form_action)
    verify_loopback_url(login_url)
    response = session.post(login_url, data={
        **form.hidden, "username": username, "password": password,
        "credentialId": "",
    }, timeout=15, allow_redirects=False)
    require(response.status_code in (302, 303),
            "Keycloak did not issue an authorization-code redirect")
    target = urljoin(response.url, response.headers.get("Location", ""))
    require(target.startswith(CALLBACK + "?"), "Redirect is not the registered callback")
    returned = parse_qs(urlparse(target).query)
    require(returned.get("state") == [state], "OAuth state did not match request")
    require("error" not in returned, "Keycloak returned an OAuth error")
    code = returned.get("code", [None])[0]
    require(type(code) is str and code, "Authorization code missing")
    return code, verifier, nonce


def exchange(discovery: dict, code: str, verifier: str) -> requests.Response:
    endpoint = discovery["token_endpoint"]
    verify_loopback_url(endpoint)
    return requests.post(endpoint, data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK,
        "code": code,
        "code_verifier": verifier,
    }, timeout=15)


def verify_id_token(token: str, jwks: dict, nonce: str) -> dict:
    header = jwt.get_unverified_header(token)
    require(header.get("alg") == "RS256" and type(header.get("kid")) is str,
            "Unexpected OIDC ID token header")
    matched = [key for key in jwks["keys"] if key.get("kid") == header["kid"]
               and key.get("kty") == "RSA"]
    require(len(matched) == 1, "ID signing key unavailable or ambiguous")
    public = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(matched[0]))
    claims = jwt.decode(token, public, algorithms=["RS256"],
                        issuer=ISSUER, audience=CLIENT_ID,
                        options={"require": ["iss", "aud", "sub", "exp", "iat", "nonce"]})
    require(claims["nonce"] == nonce, "OIDC nonce mismatch")
    return claims


def main(directory: Path) -> None:
    config = json.loads((directory / "runtime.json").read_text())
    discovery_endpoint = ISSUER + "/.well-known/openid-configuration"
    verify_loopback_url(discovery_endpoint)

    # Readiness is bounded. The Keycloak process is a real disposable server.
    for _ in range(90):
        try:
            response = requests.get(discovery_endpoint, timeout=2)
            if response.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(2)
    else:
        raise AssertionError("Disposable Keycloak did not become ready")

    metadata = response.json()
    require(metadata.get("issuer") == ISSUER, "Real issuer mismatch")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri",
                "introspection_endpoint", "end_session_endpoint"):
        verify_loopback_url(metadata[key])
    require("code" in metadata.get("response_types_supported", []),
            "Keycloak lacks authorization code support")
    require("S256" in metadata.get("code_challenge_methods_supported", []),
            "Keycloak has no advertised S256 PKCE support")

    # Public JWKS is fetched only at the vetted issuer metadata endpoint.
    jwks = requests.get(metadata["jwks_uri"], timeout=10).json()
    code, verifier, nonce = open_provider(
        metadata, config["username"], config["password"])
    tokens_response = exchange(metadata, code, verifier)
    require(tokens_response.status_code == 200,
            "Keycloak authorization code exchange failed")
    issued = tokens_response.json()
    for name in ("access_token", "id_token", "refresh_token"):
        require(type(issued.get(name)) is str and issued[name],
                "Keycloak did not issue all expected tokens")
    id_claims = verify_id_token(issued["id_token"], jwks, nonce)

    # PKCE negative case uses a SECOND, separately issued code. No password grant.
    code2, verifier2, _nonce2 = open_provider(
        metadata, config["username"], config["password"])
    wrong = exchange(metadata, code2, secrets.token_urlsafe(64))
    require(wrong.status_code in (400, 401),
            "Keycloak accepted an incorrect PKCE verifier")

    def introspection_active(access_token: str) -> bool:
        answer = requests.post(
            metadata["introspection_endpoint"], data={"token": access_token},
            auth=(API_AUDIENCE, config["introspection_secret"]), timeout=15,
        )
        require(answer.status_code == 200,
                "Confidential Keycloak introspection failed")
        result = answer.json()
        require(type(result.get("active")) is bool,
                "Introspection missing active decision")
        return result["active"]

    access_token = issued["access_token"]
    require(introspection_active(access_token),
            "Keycloak does not consider freshly issued access token active")
    keycloak = LoopbackKeycloakPilotVerifier(
        issuer=ISSUER, audience=API_AUDIENCE,
        client_id=CLIENT_ID, trusted_jwks=jwks,
        token_active=introspection_active,
    )
    verified = keycloak.verify(access_token, now=int(time.time()))
    require(verified is not None, "Real Keycloak token rejected by pilot adapter")
    require(verified.principal_id == id_claims["sub"],
            "ID token and access token identify different people")

    # Bridge the real authenticated person to synthetic separated org records.
    store = SyntheticPolicyStore()
    try:
        subject = verified.principal_id
        store.seed_principal(subject)
        for org, kind in (("llc_a", "llc"),
                          ("nonprofit", "nonprofit"),
                          ("unrelated_customer", "customer")):
            store.seed_organization(org, kind)
            store.seed_division(org, "health")
            store.seed_unit(org, "maryland")
            store.seed_record(org, "demo", "health", "maryland")
        store.seed_membership(subject, "llc_a")
        store.seed_grant("demo_read", subject, "llc_a", "records.read",
                         division_id="health", unit_id="maryland")
        api = SyntheticRequestBoundary(
            store, verifier=keycloak, clock=lambda: int(time.time()),
            expected_issuer=ISSUER, expected_audience=API_AUDIENCE,
        )

        def access(org):
            return {
                "schema": SCHEMA, "operation": "authorizeRecord",
                "accessToken": access_token, "organizationId": org,
                "recordId": "demo", "action": "records.read",
            }

        require(api.handle(access("llc_a")) == {"status": "ALLOWED"},
                "Verified Keycloak principal was denied its synthetic grant")
        for org in ("nonprofit", "unrelated_customer"):
            require(api.handle(access(org)) == {"status": "DENIED"},
                    "Real Keycloak principal escaped its tenant boundary")

        # Legacy direct refresh-token logout is used ONLY to test Keycloak in
        # disposable CI. Production must use reviewed RP-initiated logout.
        logout_url = ISSUER + "/protocol/openid-connect/logout"
        result = requests.post(logout_url, data={
            "client_id": CLIENT_ID,
            "refresh_token": issued["refresh_token"],
        }, timeout=15)
        require(result.status_code in (200, 204),
                "Disposable Keycloak user session logout failed")
        require(not introspection_active(access_token),
                "Keycloak token remains active after session logout")
        require(api.handle(access("llc_a")) == {"status": "DENIED"},
                "Previously accepted session passed after Keycloak logout")
    finally:
        store.close()

    # Never log access/refresh tokens, secrets, subject, or real user data.
    print("PASS: real Keycloak authorization code + S256 PKCE")
    print("PASS: real JWKS signature, ID nonce and separate API audience")
    print("PASS: live introspection, tenant denial and post-logout rejection")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, required=True)
    args = parser.parse_args()
    main(args.fixture_dir)
