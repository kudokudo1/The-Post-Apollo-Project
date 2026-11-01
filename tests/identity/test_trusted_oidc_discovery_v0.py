"""Disposable OIDC metadata/JWKS issuer fixture; no HTTP or real accounts."""
from __future__ import annotations

import base64
from copy import deepcopy
from pathlib import Path
import sys
import time
import unittest

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

SRC = Path(__file__).resolve().parents[2] / "services" / "identity"
sys.path.insert(0, str(SRC))
import synthetic_policy_v0 as policy
import synthetic_request_boundary_v0 as boundary
import trusted_oidc_discovery_v0 as discovery


ISSUER = "https://synthetic-idp.invalid/realm/demo"
DISCOVERY_URL = ISSUER + "/.well-known/openid-configuration"
JWKS_URL = ISSUER + "/protocol/openid-connect/certs"


def _b64(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _jwk(key, kid: str) -> dict:
    numbers = key.public_key().public_numbers()
    return {"kid": kid, "kty": "RSA", "alg": "RS256", "use": "sig",
            "n": _b64(numbers.n), "e": _b64(numbers.e)}


class DisposableIssuer:
    """In-process fake metadata and public key publication, NOT an IdP."""

    def __init__(self, jwks: dict) -> None:
        self.calls: list[str] = []
        self.fail: str | None = None
        self.metadata = {
            "issuer": ISSUER,
            "authorization_endpoint": ISSUER + "/protocol/openid-connect/auth",
            "token_endpoint": ISSUER + "/protocol/openid-connect/token",
            "jwks_uri": JWKS_URL,
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
        }
        self.jwks = jwks

    def fetch(self, url: str) -> object:
        self.calls.append(url)
        if url == self.fail:
            raise OSError("disposable transport failure")
        if url == DISCOVERY_URL:
            return deepcopy(self.metadata)
        if url == JWKS_URL:
            return deepcopy(self.jwks)
        raise AssertionError("Unapproved URL entered fetcher: " + url)


class TrustedDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.key2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.attacker_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)

    def setUp(self):
        self.now = int(time.time())
        self.issuer = DisposableIssuer({"keys": [_jwk(self.key1, "key-1")]})
        self.revoked = set()
        self.fail_revocation = False

        def revocation(issuer, sid, jti):
            if self.fail_revocation:
                raise RuntimeError("fake revocation service unavailable")
            return (issuer, sid, jti) in self.revoked

        self.revocation = revocation
        self.verifier = self.make_verifier()
        self.store = policy.SyntheticPolicyStore()
        self.addCleanup(self.store.close)
        for person in ("worker", "customer"):
            self.store.seed_principal(person)
        for org, kind in (("llc_a", "llc"), ("nonprofit", "nonprofit"),
                          ("unrelated", "customer")):
            self.store.seed_organization(org, kind)
            self.store.seed_division(org, "health")
            self.store.seed_unit(org, "maryland")
            self.store.seed_record(org, "example", "health", "maryland")
        self.store.seed_membership("worker", "llc_a")
        self.store.seed_membership("customer", "unrelated")
        self.store.seed_grant("worker-r", "worker", "llc_a", "records.read")
        self.store.seed_grant("customer-r", "customer", "unrelated", "records.read")
        self.api = boundary.SyntheticRequestBoundary(
            self.store, verifier=self.verifier, clock=lambda: self.now,
            expected_issuer=ISSUER, expected_audience="post-apollo-pilot",
        )

    def make_verifier(self, **overrides):
        args = {
            "issuer": ISSUER, "audience": "post-apollo-pilot",
            "trusted_jwks_uri": JWKS_URL,
            "fetch_json": self.issuer.fetch,
            "is_revoked": self.revocation,
            "ttl_seconds": 60,
        }
        args.update(overrides)
        return discovery.TrustedDiscoveryVerifier(**args)

    def token(self, *, key=None, kid="key-1", sub="worker", **overrides):
        claims = {
            "iss": ISSUER, "aud": "post-apollo-pilot", "sub": sub,
            "sid": "fake-session", "jti": "fake-token",
            "iat": self.now - 10, "nbf": self.now - 10,
            "exp": self.now + 180,
        }
        claims.update(overrides)
        return jwt.encode(
            claims, key or self.key1, algorithm="RS256",
            headers={"kid": kid, "typ": "at+jwt"},
        )

    def request(self, token, org="llc_a"):
        return {
            "schema": boundary.SCHEMA, "operation": "authorizeRecord",
            "accessToken": token, "organizationId": org,
            "recordId": "example", "action": "records.read",
        }

    def test_trusted_issuer_metadata_and_real_signature_meet_permission_gate(self):
        jwt_text = self.token()
        self.assertEqual(self.api.handle(self.request(jwt_text)), {"status": "DENIED"})
        self.assertTrue(self.verifier.refresh(now=self.now))
        self.assertEqual(self.issuer.calls, [DISCOVERY_URL, JWKS_URL])
        self.assertEqual(self.api.handle(self.request(jwt_text)), {"status": "ALLOWED"})
        self.assertEqual(self.api.handle(self.request(jwt_text, "nonprofit")),
                         {"status": "DENIED"})
        self.assertEqual(self.api.handle(self.request(jwt_text, "unrelated")),
                         {"status": "DENIED"})

    def test_discovery_metadata_cannot_redirect_to_attacker_keys(self):
        self.issuer.metadata["jwks_uri"] = "https://attacker.invalid/keys"
        self.assertFalse(self.verifier.refresh(now=self.now))
        self.assertEqual(self.issuer.calls, [DISCOVERY_URL])
        self.assertIsNone(self.verifier.verify(self.token(), now=self.now))

    def test_wrong_issuer_metadata_fails_closed(self):
        self.issuer.metadata["issuer"] = "https://attacker.invalid/realm/demo"
        self.assertFalse(self.verifier.refresh(now=self.now))
        self.assertEqual(self.issuer.calls, [DISCOVERY_URL])

    def test_wrong_auth_or_token_endpoint_fails_closed(self):
        for name in ("authorization_endpoint", "token_endpoint"):
            for value in ("http://synthetic-idp.invalid/endpoint",
                          "https://attacker.invalid/endpoint",
                          "https://user@synthetic-idp.invalid/endpoint",
                          "https://synthetic-idp.invalid:0/bad",
                          "https://synthetic-idp.invalid/#fragment"):
                self.issuer.calls.clear()
                old = self.issuer.metadata[name]
                self.issuer.metadata[name] = value
                with self.subTest(name=name, value=value):
                    self.assertFalse(self.verifier.refresh(now=self.now))
                    self.assertEqual(self.issuer.calls, [DISCOVERY_URL])
                self.issuer.metadata[name] = old

    def test_code_flow_and_pkce_are_required_in_pilot(self):
        for name, value in (
            ("response_types_supported", ["id_token"]),
            ("code_challenge_methods_supported", ["plain"]),
            ("response_types_supported", "code"),
            ("code_challenge_methods_supported", None),
        ):
            old = self.issuer.metadata[name]
            self.issuer.metadata[name] = value
            with self.subTest(name=name, value=value):
                self.assertFalse(self.verifier.refresh(now=self.now))
            self.issuer.metadata[name] = old

    def test_missing_metadata_or_invalid_json_fails_closed(self):
        self.issuer.metadata = {"issuer": ISSUER}
        self.assertFalse(self.verifier.refresh(now=self.now))
        self.issuer.metadata = []  # invalid decoded document type
        self.assertFalse(self.verifier.refresh(now=self.now))

    def test_key_rotation_requires_explicit_refresh(self):
        first = self.token()
        self.assertTrue(self.verifier.refresh(now=self.now))
        rotated = self.token(key=self.key2, kid="key-2")
        self.assertIsNone(self.verifier.verify(rotated, now=self.now))
        self.issuer.jwks = {"keys": [_jwk(self.key1, "key-1"),
                                     _jwk(self.key2, "key-2")]}
        self.assertTrue(self.verifier.refresh(now=self.now))
        self.assertIsNotNone(self.verifier.verify(first, now=self.now))
        self.assertIsNotNone(self.verifier.verify(rotated, now=self.now))
        self.issuer.jwks = {"keys": [_jwk(self.key2, "key-2")]}
        self.assertTrue(self.verifier.refresh(now=self.now))
        self.assertIsNone(self.verifier.verify(first, now=self.now))
        self.assertIsNotNone(self.verifier.verify(rotated, now=self.now))

    def test_failed_refresh_revokes_old_key_snapshot(self):
        self.assertTrue(self.verifier.refresh(now=self.now))
        self.issuer.fail = JWKS_URL
        self.assertFalse(self.verifier.refresh(now=self.now))
        self.assertEqual(self.api.handle(self.request(self.token())),
                         {"status": "DENIED"})

    def test_expired_snapshot_denies_even_valid_unexpired_jwt(self):
        self.assertTrue(self.verifier.refresh(now=self.now))
        self.now += 60
        self.assertEqual(self.api.handle(self.request(self.token())),
                         {"status": "DENIED"})

    def test_revocation_checker_outage_and_revoked_session_fail_closed(self):
        self.assertTrue(self.verifier.refresh(now=self.now))
        token = self.token()
        self.revoked.add((ISSUER, "fake-session", "fake-token"))
        self.assertIsNone(self.verifier.verify(token, now=self.now))
        self.revoked.clear()
        self.fail_revocation = True
        self.assertIsNone(self.verifier.verify(token, now=self.now))

    def test_unknown_or_attacker_signed_token_remains_denied(self):
        self.assertTrue(self.verifier.refresh(now=self.now))
        attacker = self.token(key=self.attacker_key)
        self.assertEqual(self.api.handle(self.request(attacker)),
                         {"status": "DENIED"})

    def test_trusted_config_rejects_unapproved_uri_or_clock(self):
        for uri in ("http://synthetic-idp.invalid/keys",
                    "https://attacker.invalid/keys",
                    "https://user@synthetic-idp.invalid/keys",
                    "https://synthetic-idp.invalid/keys?x=1"):
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError):
                    self.make_verifier(trusted_jwks_uri=uri)
        for clock in (None, True, -1, "10"):
            self.assertFalse(self.verifier.refresh(now=clock))

    def test_invalid_keyset_and_malformed_revocation_will_deny(self):
        self.issuer.jwks = {"keys": [{"bad": "key"}]}
        self.assertFalse(self.verifier.refresh(now=self.now))
        self.assertIsNone(self.verifier.verify(self.token(), now=self.now))

    def test_portfolio_does_not_become_company_authorization(self):
        self.store.seed_portfolio("family")
        self.store.seed_portfolio_member("family", "worker")
        self.store.seed_portfolio_organization("family", "llc_a")
        self.store.seed_portfolio_organization("family", "nonprofit")
        self.assertTrue(self.verifier.refresh(now=self.now))
        token = self.token()
        req = {
            "schema": boundary.SCHEMA,
            "operation": "listPortfolioOrganizations",
            "accessToken": token,
            "portfolioId": "family",
        }
        self.assertEqual(self.api.handle(req),
                         {"status": "OK", "organizationIds": ["llc_a"]})
        self.assertEqual(self.api.handle(self.request(token, "nonprofit")),
                         {"status": "DENIED"})

    def test_source_never_performs_network_requests(self):
        source = (SRC / "trusted_oidc_discovery_v0.py").read_text()
        for forbidden in ("urlopen(", "requests.get(", "http.server",
                          "socket.socket(", "fetch_json(token", "get_unverified_header"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
