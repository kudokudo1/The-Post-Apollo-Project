"""Offline RSA/JWKS signature and request-boundary tests. No real IdP/secrets."""
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
import oidc_jwks_verifier_v0 as adapter
import synthetic_policy_v0 as policy
import synthetic_request_boundary_v0 as boundary


def b64int(value: int) -> str:
    data = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def jwk_for(key, kid: str) -> dict:
    pub = key.public_key().public_numbers()
    return {"kid": kid, "kty": "RSA", "alg": "RS256", "use": "sig",
            "n": b64int(pub.n), "e": b64int(pub.e)}


class OfflineJWKSVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signing = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public = jwk_for(cls.signing, "active")
        cls.other_public = jwk_for(cls.other, "next")

    def setUp(self):
        self.now = int(time.time())
        self.revoked = set()
        self.revocation_error = False

        def checker(issuer, sid, jti):
            if self.revocation_error:
                raise RuntimeError("private revocation backend error")
            return (issuer, sid, jti) in self.revoked

        self.checker = checker
        self.verifier = self.make_verifier()
        self.store = policy.SyntheticPolicyStore()
        self.addCleanup(self.store.close)
        for person in ("worker", "other_customer"):
            self.store.seed_principal(person)
        for org, kind in (("llc", "llc"), ("nonprofit", "nonprofit"),
                          ("external", "customer")):
            self.store.seed_organization(org, kind)
            self.store.seed_division(org, "health")
            self.store.seed_unit(org, "md")
            self.store.seed_record(org, "r1", "health", "md")
        self.store.seed_membership("worker", "llc")
        self.store.seed_membership("other_customer", "external")
        self.store.seed_grant("worker_grant", "worker", "llc", "records.read")
        self.store.seed_grant("customer_grant", "other_customer",
                              "external", "records.read")
        self.api = boundary.SyntheticRequestBoundary(
            self.store, verifier=self.verifier, clock=lambda: self.now,
            expected_issuer="https://idp.invalid/issuer",
            expected_audience="post-apollo-test-api",
        )

    def make_verifier(self, keys=None):
        return adapter.OfflineJWKSVerifier(
            trusted_jwks={"keys": [self.public] if keys is None else keys},
            issuer="https://idp.invalid/issuer",
            audience="post-apollo-test-api",
            is_revoked=self.checker,
        )

    def claims(self, **overrides):
        values = {
            "iss": "https://idp.invalid/issuer",
            "aud": "post-apollo-test-api",
            "sub": "worker",
            "sid": "session-worker",
            "jti": "token-1",
            "iat": self.now - 5,
            "nbf": self.now - 5,
            "exp": self.now + 240,
        }
        values.update(overrides)
        return values

    def signed(self, claims=None, *, key=None, kid="active", alg="RS256",
               headers=None):
        header = {"kid": kid, "typ": "at+jwt"}
        if headers:
            header.update(headers)
        return jwt.encode(
            self.claims() if claims is None else claims,
            self.signing if key is None else key,
            algorithm=alg,
            headers=header,
        )

    def access(self, token, org="llc"):
        return dict(schema=boundary.SCHEMA, operation="authorizeRecord",
                    accessToken=token, organizationId=org,
                    recordId="r1", action="records.read")

    def test_rs256_signature_yields_verified_session(self):
        item = self.verifier.verify(self.signed(), now=self.now)
        self.assertIsInstance(item, boundary.VerifiedSession)
        self.assertEqual(item.principal_id, "worker")
        self.assertEqual(item.session_id, "session-worker")

    def test_signed_token_checks_tenant_grant_not_token_org_claim(self):
        token = self.signed(self.claims(orgId="external", role="superadmin"))
        self.assertEqual(self.api.handle(self.access(token)), {"status": "ALLOWED"})
        self.assertEqual(self.api.handle(self.access(token, org="external")),
                         {"status": "DENIED"})
        # A separately signed external customer can access only their tenant.
        customer = self.signed(self.claims(sub="other_customer", sid="s-c", jti="j-c"))
        self.assertEqual(self.api.handle(self.access(customer, "external")),
                         {"status": "ALLOWED"})
        self.assertEqual(self.api.handle(self.access(customer, "llc")),
                         {"status": "DENIED"})

    def test_token_reissued_by_other_key_is_rejected(self):
        token = self.signed(key=self.other)
        self.assertIsNone(self.verifier.verify(token, now=self.now))

    def test_unknown_kid_and_key_rotation(self):
        rotated = self.signed(key=self.other, kid="next")
        self.assertIsNone(self.verifier.verify(rotated, now=self.now))
        two_keys = self.make_verifier([self.public, self.other_public])
        self.assertEqual(two_keys.verify(rotated, now=self.now).principal_id, "worker")
        only_new = self.make_verifier([self.other_public])
        self.assertIsNone(only_new.verify(self.signed(), now=self.now))

    def test_header_with_key_url_or_embedded_jwk_is_refused(self):
        for extra in ({"jku": "https://evil.invalid/jwks"},
                      {"x5u": "https://evil.invalid/cert"},
                      {"crit": ["x"]}, {"jwk": self.public}):
            with self.subTest(extra=next(iter(extra))):
                token = self.signed(headers=extra)
                self.assertIsNone(self.verifier.verify(token, now=self.now))

    def test_wrong_token_type_is_refused(self):
        token = self.signed(headers={"typ": "JWT"})
        self.assertIsNone(self.verifier.verify(token, now=self.now))

    def test_none_and_hs_algorithm_are_refused(self):
        token = jwt.encode(self.claims(), key="symmetric-test-secret",
                           algorithm="HS256",
                           headers={"kid": "active", "typ": "at+jwt"})
        self.assertIsNone(self.verifier.verify(token, now=self.now))
        unsigned = jwt.encode(self.claims(), key=None, algorithm="none",
                              headers={"kid": "active", "typ": "at+jwt"})
        self.assertIsNone(self.verifier.verify(unsigned, now=self.now))

    def test_expired_future_issued_future_nbf_fail_closed(self):
        for override in ({"exp": self.now - 1},
                         {"iat": self.now + 50},
                         {"nbf": self.now + 50},
                         {"exp": self.now + 901},
                         {"exp": self.now - 5}):
            with self.subTest(override=override):
                self.assertIsNone(self.verifier.verify(
                    self.signed(self.claims(**override)), now=self.now))

    def test_missing_or_wrong_claim_types_fail_closed(self):
        for name in ("iss", "aud", "sub", "sid", "jti", "iat", "nbf", "exp"):
            claims = self.claims()
            del claims[name]
            with self.subTest(missing=name):
                self.assertIsNone(self.verifier.verify(
                    self.signed(claims), now=self.now))
        for override in ({"iat": True}, {"exp": "9999999999"},
                         {"sid": ""}, {"jti": []}, {"sub": 5},
                         {"nbf": 2.5}):
            with self.subTest(override=override):
                self.assertIsNone(self.verifier.verify(
                    self.signed(self.claims(**override)), now=self.now))

    def test_wrong_issuer_or_audience(self):
        for changed in ({"iss": "https://other.invalid/issuer"},
                        {"aud": "another-api"}):
            self.assertIsNone(self.verifier.verify(
                self.signed(self.claims(**changed)), now=self.now))

    def test_revoked_token_and_revocation_service_outage(self):
        token = self.signed()
        self.revoked.add(("https://idp.invalid/issuer", "session-worker", "token-1"))
        self.assertIsNone(self.verifier.verify(token, now=self.now))
        self.assertEqual(self.api.handle(self.access(token)), {"status": "DENIED"})
        self.revoked.clear()
        self.revocation_error = True
        self.assertIsNone(self.verifier.verify(token, now=self.now))

    def test_malformed_or_oversize_token_denied(self):
        for value in (None, "", {}, "garbage", " " + self.signed(),
                      "x" * 8193):
            with self.subTest(kind=type(value).__name__):
                self.assertIsNone(self.verifier.verify(value, now=self.now))

    def test_config_refuses_private_keys_and_untrusted_key_specs(self):
        examples = (
            {**self.public, "d": "untrusted"},
            {**self.public, "jku": "https://evil.invalid"},
            {**self.public, "alg": "HS256"},
            {**self.public, "use": "enc"},
            {**self.public, "kty": "oct"},
        )
        for key in examples:
            with self.subTest(key=key.get("alg")):
                with self.assertRaises(ValueError):
                    self.make_verifier([key])

    def test_bad_config_duplicate_kid_empty_keyset(self):
        for keys in ([], [self.public, self.public], [self.public] * 9):
            with self.assertRaises(ValueError):
                self.make_verifier(keys)

    def test_malformed_trust_clock_denies(self):
        token = self.signed()
        for now in (None, True, -1, "100"):
            self.assertIsNone(self.verifier.verify(token, now=now))

    def test_policy_revocation_after_successful_signature(self):
        token = self.signed()
        self.assertEqual(self.api.handle(self.access(token)), {"status": "ALLOWED"})
        self.store.revoke_membership("worker", "llc")
        self.assertEqual(self.api.handle(self.access(token)), {"status": "DENIED"})

    def test_no_real_network_or_signing_key_store(self):
        source = (SRC / "oidc_jwks_verifier_v0.py").read_text()
        for banned in ("requests.get", "urllib.request", "http.server",
                       "socket.socket", "private_key", "create_user"):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
