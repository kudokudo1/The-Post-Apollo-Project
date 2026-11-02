"""Keycloak-specific *loopback-only* access token verifier for disposable CI.

This is NOT a supported production IdP, public API, host transport, revocation
service or key refresh manager. A real Keycloak server signs test tokens; a
protected test driver injects public JWKS and an authenticated introspection
callback. Never use token-controlled key URLs or client-requested identity.

Keycloak's access token profile differs from the strict RFC 9068-only synthetic
verifier. This separate adapter accepts its JWT header ONLY with a pinned API
audience and authorized-party client, so OIDC ID tokens are not API credentials.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from urllib.parse import urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from synthetic_request_boundary_v0 import VerifiedSession


class LoopbackKeycloakPilotVerifier:
    """CI-only dependency injected into the existing synthetic request boundary."""

    def __init__(self, *, issuer: str, audience: str, client_id: str,
                 trusted_jwks: Mapping[str, object],
                 token_active: Callable[[str], bool]) -> None:
        parsed = urlsplit(issuer)
        if (type(issuer) is not str or parsed.scheme != "http"
                or parsed.hostname != "127.0.0.1" or parsed.port != 8080
                or parsed.path != "/realms/post-apollo-disposable"
                or parsed.query or parsed.fragment
                or audience != "post-apollo-pilot-api"
                or client_id != "post-apollo-pilot-public"
                or not callable(token_active)):
            raise ValueError("Only fixed disposable loopback Keycloak CI configuration is allowed")
        if not isinstance(trusted_jwks, Mapping):
            raise ValueError("Missing trusted public JWKS")
        entries = trusted_jwks.get("keys")
        if type(entries) is not list or not 1 <= len(entries) <= 16:
            raise ValueError("Invalid JWKS key count")
        keys: dict[str, RSAPublicKey] = {}
        for item in entries:
            if not isinstance(item, Mapping):
                raise ValueError("Invalid JWKS key")
            if (item.get("kty") != "RSA"
                    or item.get("use") != "sig"
                    or item.get("alg") != "RS256"):
                continue  # Keycloak may publish non-RS256/enc keys too.
            kid = item.get("kid")
            if (type(kid) is not str or not kid or kid in keys
                    or len(kid) > 128
                    or not all(type(item.get(field)) is str
                               for field in ("n", "e"))):
                raise ValueError("Malformed public RSA signing key")
            try:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(
                    {name: item[name] for name in ("kty", "n", "e")}
                ))
            except Exception as exc:
                raise ValueError("Invalid trusted RSA public key") from exc
            if (not isinstance(key, RSAPublicKey) or key.key_size < 2048
                    or key.public_numbers().e != 65537):
                raise ValueError("Weak trusted RSA key")
            keys[kid] = key
        if not keys:
            raise ValueError("No acceptable trusted RSA signing keys")
        self._keys = keys
        self._issuer = issuer
        self._audience = audience
        self._client_id = client_id
        self._token_active = token_active

    def verify(self, token: str, *, now: int) -> VerifiedSession | None:
        if (type(token) is not str or not token or len(token) > 8192
                or token != token.strip()
                or type(now) is not int or now < 0):
            return None
        try:
            header = jwt.get_unverified_header(token)
            if (not isinstance(header, dict)
                    or set(header) != {"typ", "alg", "kid"}
                    or header["typ"] != "JWT" or header["alg"] != "RS256"
                    or type(header["kid"]) is not str):
                return None
            key = self._keys.get(header["kid"])
            if key is None:
                return None
            claims = jwt.decode(
                token, key, algorithms=["RS256"],
                issuer=self._issuer, audience=self._audience,
                options={"require": ["iss", "aud", "sub", "iat", "exp", "azp", "jti"]},
                leeway=0,
            )
            if (type(claims) is not dict
                    or claims.get("azp") != self._client_id):
                return None
            session_id = claims.get("sid") or claims.get("session_state")
            if (type(session_id) is not str or not session_id
                    or type(claims.get("sub")) is not str or not claims["sub"]
                    or type(claims.get("jti")) is not str or not claims["jti"]
                    or any(type(claims.get(f)) is not int
                           for f in ("iat", "exp"))):
                return None
            issued, expires = claims["iat"], claims["exp"]
            if (issued < 0 or issued > now or expires <= now
                    or expires <= issued or expires - issued > 900):
                return None
            active = self._token_active(token)
            if type(active) is not bool or not active:
                return None
            return VerifiedSession(
                principal_id=claims["sub"], issuer=self._issuer,
                audience=self._audience, session_id=session_id,
                issued_at=issued, expires_at=expires,
            )
        except Exception:
            # No sensitive claim, token, network, verifier or SQL details leak.
            return None
