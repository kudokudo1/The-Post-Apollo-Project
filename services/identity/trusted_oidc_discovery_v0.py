"""EXPERIMENTAL offline OIDC discovery + JWKS rotation handoff.

The trusted host must inject a fetch_json function that authenticates the
configured HTTPS issuer, disables redirects, limits response sizes and time,
and never uses user/token-controlled URLs. No network code or HTTP server
exists here; test fixtures supply an in-memory metadata/JWKS issuer.

The previously merged OfflineJWKSVerifier owns token crypto and revocation.
Not a deployed IdP integration or production authorization boundary.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from urllib.parse import urlsplit

from oidc_jwks_verifier_v0 import OfflineJWKSVerifier
from synthetic_request_boundary_v0 import VerifiedSession


def _trusted_https_url(url: object, *, origin: str | None = None) -> bool:
    if type(url) is not str or len(url) > 2048:
        return False
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname
                or not parsed.netloc or parsed.username is not None
                or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.port == 0
                or "\\" in url or any(ord(c) < 33 for c in url)):
            return False
        if origin is not None and f"{parsed.scheme}://{parsed.netloc}" != origin:
            return False
        return True
    except (TypeError, ValueError):
        return False


class TrustedDiscoveryVerifier:
    """Read-only token verifier populated by trusted, explicit refresh.

    Only the host may call refresh(). A token, request, or UI callback cannot
    select metadata, a JWKS URI, signing keys, issuer, or verifier policies.
    The strict same-origin restriction is a pilot policy, not a general claim
    that all legitimate OIDC issuers host their endpoints on one domain.
    """

    def __init__(self, *, issuer: str, audience: str,
                 trusted_jwks_uri: str,
                 fetch_json: Callable[[str], object],
                 is_revoked: Callable[[str, str, str], bool],
                 ttl_seconds: int = 300) -> None:
        if (not _trusted_https_url(issuer) or issuer.endswith("/")
                or type(audience) is not str or not audience
                or not callable(fetch_json) or not callable(is_revoked)
                or type(ttl_seconds) is not int
                or not 1 <= ttl_seconds <= 900):
            raise ValueError("Trusted issuer, audience, fetcher, revocation and TTL required")
        issuer_parsed = urlsplit(issuer)
        if issuer_parsed.query or issuer_parsed.fragment:
            raise ValueError("Issuer cannot contain query or fragment")
        origin = f"{issuer_parsed.scheme}://{issuer_parsed.netloc}"
        if (not _trusted_https_url(trusted_jwks_uri, origin=origin)
                or not urlsplit(trusted_jwks_uri).path):
            raise ValueError("Preapproved JWKS endpoint must use issuer origin")
        self._issuer = issuer
        self._audience = audience
        self._origin = origin
        self._jwks_uri = trusted_jwks_uri
        self._metadata_uri = issuer + "/.well-known/openid-configuration"
        self._fetch_json = fetch_json
        self._is_revoked = is_revoked
        self._ttl = ttl_seconds
        self._active: OfflineJWKSVerifier | None = None
        self._expires_at = 0

    @property
    def metadata_uri(self) -> str:
        return self._metadata_uri

    def refresh(self, *, now: int) -> bool:
        """Host-initiated atomic metadata+keys update, fail closed on error.

        Old signer trust is NOT retained after failed refresh. The host must
        use a trusted clock. Fetcher transport security is out of scope here.
        """
        self._active = None
        self._expires_at = 0
        if type(now) is not int or now < 0:
            return False
        try:
            metadata = self._fetch_json(self._metadata_uri)
            if type(metadata) is not dict:
                return False
            if (metadata.get("issuer") != self._issuer
                    or metadata.get("jwks_uri") != self._jwks_uri):
                return False
            for name in ("authorization_endpoint", "token_endpoint"):
                if not _trusted_https_url(metadata.get(name), origin=self._origin):
                    return False
            # This pilot requires code flow + PKCE; do not enable implicit
            # or resource-owner-password flows to work around an issuer.
            responses = metadata.get("response_types_supported")
            challenges = metadata.get("code_challenge_methods_supported")
            if (type(responses) is not list or "code" not in responses
                    or type(challenges) is not list or "S256" not in challenges):
                return False
            # Only the operator-pinned JWKS URI can reach the fetcher;
            # metadata cannot redirect to a key server elsewhere.
            jwks = self._fetch_json(self._jwks_uri)
            if not isinstance(jwks, Mapping):
                return False
            next_verifier = OfflineJWKSVerifier(
                trusted_jwks=jwks,
                issuer=self._issuer,
                audience=self._audience,
                is_revoked=self._is_revoked,
            )
            self._active = next_verifier
            self._expires_at = now + self._ttl
            return True
        except Exception:
            return False

    def verify(self, token: str, *, now: int) -> VerifiedSession | None:
        """Do not accept tokens when keys are missing, expired or failed refresh."""
        if (type(now) is not int or now < 0 or now >= self._expires_at
                or self._active is None):
            return None
        return self._active.verify(token, now=now)
