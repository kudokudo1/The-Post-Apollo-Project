"""Offline, RS256-only JWT access-token verification adapter (EXPERIMENTAL).

No network, OIDC discovery, IdP hosting, login, credentials, secret management,
or HTTP service. Trusted JWKS and revocation checker must be supplied by a
protected backend. This is NOT production authorization until the issuer's
actual token contract, JWKS lifecycle, revocation, clock, and host trust are
security-reviewed and integrated.

Uses PyJWT + cryptography for signature validation, never custom JWT crypto.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from synthetic_request_boundary_v0 import VerifiedSession


class OfflineJWKSVerifier:
    """A strict, offline token verifier compatible with SessionVerifier.

    JWKS is trusted, out-of-band configuration rather than client or token data.
    The verifier does not fetch URLs from any token header. Only public RSA
    keys with explicit kid, RS256 and use=sig are accepted. Token format is
    a *proposed* short-lived access-token profile, not generic OIDC support.
    """

    def __init__(self, *, trusted_jwks: Mapping[str, object],
                 issuer: str, audience: str,
                 is_revoked: Callable[[str, str, str], bool],
                 max_lifetime_seconds: int = 900) -> None:
        if (type(issuer) is not str or not issuer.startswith("https://")
                or not issuer[8:] or type(audience) is not str or not audience
                or not callable(is_revoked)
                or type(max_lifetime_seconds) is not int
                or max_lifetime_seconds < 1 or max_lifetime_seconds > 3600):
            raise ValueError("Trusted issuer, audience, revocation checker, lifetime required")
        if not isinstance(trusted_jwks, Mapping):
            raise ValueError("Trusted JWKS must be a mapping")
        if set(trusted_jwks) != {"keys"}:
            raise ValueError("Trusted JWKS must contain only keys")
        entries = trusted_jwks.get("keys")
        if type(entries) is not list or not 1 <= len(entries) <= 8:
            raise ValueError("Trusted JWKS must have 1 to 8 active keys")
        keys: dict[str, RSAPublicKey] = {}
        for item in entries:
            if type(item) is not dict:
                raise ValueError("Each key must be a plain object")
            # No private RSA components, x5u/jku URLs, alternate algorithms
            # or silent overrides of the trusted signing-key policy.
            if set(item) != {"kid", "kty", "alg", "use", "n", "e"}:
                raise ValueError("Only a pinned public RSA signing key is allowed")
            kid = item["kid"]
            if (type(kid) is not str or not kid or len(kid) > 128
                    or kid in keys or item["kty"] != "RSA"
                    or item["alg"] != "RS256" or item["use"] != "sig"):
                raise ValueError("Invalid or duplicate RSA signing key")
            try:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(item))
            except Exception as exc:
                raise ValueError("Invalid RSA public signing key") from exc
            if (not isinstance(key, RSAPublicKey) or key.key_size < 2048
                    or key.public_numbers().e != 65537):
                raise ValueError("RSA signing key does not satisfy security profile")
            keys[kid] = key
        self._keys = keys
        self._issuer = issuer
        self._audience = audience
        self._is_revoked = is_revoked
        self._max_lifetime = max_lifetime_seconds

    def verify(self, token: str, *, now: int) -> VerifiedSession | None:
        """Verify signature and strict claims; return no identity on failure.

        'now' must come from the protected host clock, never the incoming
        request. PyJWT also checks system UTC for temporal claims.
        """
        if (type(token) is not str or not token or len(token) > 8192
                or token != token.strip()
                or type(now) is not int or now < 0):
            return None
        try:
            header = jwt.get_unverified_header(token)
            if (type(header) is not dict
                    or set(header) != {"typ", "alg", "kid"}
                    or header["typ"] != "at+jwt"
                    or header["alg"] != "RS256"
                    or type(header["kid"]) is not str):
                return None
            key = self._keys.get(header["kid"])
            if key is None:
                return None
            claims = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],  # NEVER derived from token
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["iss", "aud", "sub", "iat", "nbf",
                                     "exp", "sid", "jti"]},
                leeway=0,
            )
            if type(claims) is not dict:
                return None
            # Strict app profile. A vendor that does not issue these claims
            # needs an explicit reviewed adapter, not disabled verification.
            for name in ("sub", "sid", "jti"):
                if (type(claims.get(name)) is not str
                        or not claims[name] or len(claims[name]) > 128):
                    return None
            for name in ("iat", "nbf", "exp"):
                if type(claims.get(name)) is not int:
                    return None
            issued, not_before, expires = (
                claims["iat"], claims["nbf"], claims["exp"]
            )
            if (issued < 0 or issued > now or not_before > now
                    or expires <= now or expires <= issued
                    or expires - issued > self._max_lifetime):
                return None
            revoked = self._is_revoked(self._issuer, claims["sid"], claims["jti"])
            if type(revoked) is not bool or revoked:
                return None
            return VerifiedSession(
                principal_id=claims["sub"], issuer=self._issuer,
                audience=self._audience, session_id=claims["sid"],
                issued_at=issued, expires_at=expires,
            )
        except Exception:
            # Never leak PyJWT, crypto, lookup, or revocation internals to caller.
            return None
