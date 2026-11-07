"""Experimental host-owned OIDC authorization-code exchange and ID-token verification.

NO executable login service, UI endpoint, token file, secret store or production
IdP selection. The trusted host supplies pinned HTTPS endpoints, pre-fetched
issuer JWKS and a trusted clock. A hostile token/header cannot select keys or URLs.
The only callback exposed to DesktopSessionHost is exchange_and_verify(code,
verifier, nonce, redirect_uri). Real JWT RS256 signature verification uses
PyJWT + cryptography, not an invented "verified" flag.

The token endpoint may send a refresh_token but it is never retained, returned,
logged, or used; an access token remains in the protected host memory only.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import hmac
import http.client
import json
from pathlib import Path
import re
import ssl
from collections.abc import Callable, Mapping
from urllib.parse import urlencode, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from desktop_context_projection_v0 import _pairs_unique
from desktop_session_host_v0 import VerifiedCodeExchange
from pinned_https_identity_transport_v0 import _url, HostPinnedHttpsTransport

_CODE = re.compile(r"[A-Za-z0-9._~+-]{1,2048}\Z", re.ASCII)
_PKCE = re.compile(r"[A-Za-z0-9._~-]{43,128}\Z", re.ASCII)
_CLIENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)
_MAX_BYTES = 65536
_MAX_TOKEN_LIFETIME = 900


def _strict_object(raw: bytes) -> dict:
    if type(raw) is not bytes or not 0 < len(raw) <= _MAX_BYTES:
        raise ValueError("Invalid identity response")
    try:
        obj = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if type(obj) is not dict:
            raise ValueError("Invalid identity response")
        return obj
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise ValueError("Invalid identity response") from exc


def _jwt_object(segment: str) -> dict:
    if type(segment) is not str or not 0 < len(segment) <= 8192:
        raise ValueError("Invalid signed identity")
    try:
        raw = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
        return _strict_object(raw)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise ValueError("Invalid signed identity") from exc


@dataclass(frozen=True, slots=True)
class HostOidcExchangeConfig:
    """Host-pinned public native-app token endpoint and client policy."""

    issuer: str
    token_endpoint: str
    authorization_endpoint: str
    client_id: str
    timeout_seconds: float = 3.0
    ca_bundle: Path | None = None

    def __post_init__(self) -> None:
        issuer_origin, _, _, issuer_path = _url(self.issuer)
        token_origin, _, _, token_path = _url(self.token_endpoint)
        auth_origin, _, _, auth_path = _url(self.authorization_endpoint)
        if (self.issuer.endswith("/") or issuer_path == "/"
                or token_origin != issuer_origin
                or auth_origin != issuer_origin
                or not token_path.startswith(issuer_path + "/")
                or not auth_path.startswith(issuer_path + "/")
                or _CLIENT.fullmatch(self.client_id) is None
                or type(self.timeout_seconds) not in (int, float)
                or not 0.5 <= self.timeout_seconds <= 10
                or (self.ca_bundle is not None and
                    (not isinstance(self.ca_bundle, Path)
                     or not self.ca_bundle.is_absolute()
                     or self.ca_bundle.is_symlink()))):
            raise ValueError("Invalid host-pinned OIDC configuration")


class HostOidcCodeExchange:
    """Verify one pinned RS256 ID-token profile after a real HTTPS code POST.

    Configuration and JWKS are supplied only by a trusted host. JWKS should
    be fetched with the existing HostPinnedHttpsTransport.fetch_json() then
    approved by the existing issuer metadata discovery policy; this object
    never downloads keys from a JWT header. It can be supplied directly to
    DesktopHostLifecycle as exchange_and_verify.
    """

    def __init__(self, *, config: HostOidcExchangeConfig,
                 trusted_jwks: Mapping[str, object],
                 clock: Callable[[], int]) -> None:
        if type(config) is not HostOidcExchangeConfig or not callable(clock):
            raise ValueError("Protected host configuration and clock required")
        if not isinstance(trusted_jwks, Mapping) or set(trusted_jwks) != {"keys"}:
            raise ValueError("Host-approved JWKS required")
        entries = trusted_jwks["keys"]
        if type(entries) is not list or not 1 <= len(entries) <= 8:
            raise ValueError("Unapproved signing key set")
        keys: dict[str, RSAPublicKey] = {}
        for entry in entries:
            if type(entry) is not dict or set(entry) != {
                    "kid", "kty", "alg", "use", "n", "e"}:
                raise ValueError("Unsupported signing key")
            kid = entry["kid"]
            if (type(kid) is not str or not 0 < len(kid) <= 128
                    or kid in keys or entry["alg"] != "RS256"
                    or entry["kty"] != "RSA" or entry["use"] != "sig"):
                raise ValueError("Invalid signing key")
            try:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(entry))
            except Exception as exc:
                raise ValueError("Invalid public signing key") from exc
            if (not isinstance(key, RSAPublicKey) or key.key_size < 2048
                    or key.public_numbers().e != 65537):
                raise ValueError("Weak signing key")
            keys[kid] = key
        self._config = config
        self._keys = keys
        self._clock = clock

    @classmethod
    def from_pinned_transport(
        cls, *, config: HostOidcExchangeConfig,
        transport: HostPinnedHttpsTransport,
        clock: Callable[[], int],
    ) -> "HostOidcCodeExchange":
        """Approve pinned issuer metadata/JWKS once inside host custody.

        The discovery document may CONFIRM a host-pinned endpoint, never
        select or redirect one. Rotation needs a fresh approved host session.
        """
        if (type(config) is not HostOidcExchangeConfig
                or type(transport) is not HostPinnedHttpsTransport
                or transport._config.issuer != config.issuer
                or transport._config.ca_bundle != config.ca_bundle):
            raise ValueError("Issuer HTTPS transport does not match host")
        metadata = transport.fetch_json(transport._config.metadata_url)
        if (metadata.get("issuer") != config.issuer
                or metadata.get("jwks_uri") != transport._config.jwks_url
                or metadata.get("token_endpoint") != config.token_endpoint
                or metadata.get("authorization_endpoint") != config.authorization_endpoint
                or type(metadata.get("response_types_supported")) is not list
                or "code" not in metadata["response_types_supported"]
                or type(metadata.get("code_challenge_methods_supported")) is not list
                or "S256" not in metadata["code_challenge_methods_supported"]):
            raise ValueError("Pinned issuer discovery does not match host policy")
        keys = transport.fetch_json(transport._config.jwks_url)
        return cls(config=config, trusted_jwks=keys, clock=clock)

    def _token_response(self, code: str, verifier: str,
                        redirect_uri: str) -> dict:
        """Perform exactly one protected HTTPS POST to the pinned endpoint."""
        _, host, port, path = _url(self._config.token_endpoint)
        payload = urlencode({
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self._config.client_id,
            "code_verifier": verifier,
        }).encode("ascii")
        connection: http.client.HTTPSConnection | None = None
        try:
            tls = ssl.create_default_context(
                cafile=str(self._config.ca_bundle)
                if self._config.ca_bundle is not None else None
            )
            tls.minimum_version = ssl.TLSVersion.TLSv1_2
            if tls.verify_mode != ssl.CERT_REQUIRED or not tls.check_hostname:
                raise ValueError("Unverified HTTPS forbidden")
            connection = http.client.HTTPSConnection(
                host, port, timeout=self._config.timeout_seconds, context=tls,
            )
            connection.request("POST", path, body=payload, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Cache-Control": "no-store",
            })
            response = connection.getresponse()
            if (response.status != 200
                    or response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
                       != "application/json"
                    or response.getheader("Content-Encoding", "identity").lower()
                       != "identity"):
                raise ValueError("Code exchange refused")
            length = response.getheader("Content-Length")
            if length is not None and (
                    not length.isascii() or not length.isdecimal()
                    or not 0 < int(length) <= _MAX_BYTES):
                raise ValueError("Code exchange response size refused")
            return _strict_object(response.read(_MAX_BYTES + 1))
        except Exception as exc:
            # Never surface code, verifier, host URL, CA path, token or response.
            raise ValueError("Code exchange unavailable") from None
        finally:
            if connection is not None:
                connection.close()

    def _verify_id_token(self, token: str, nonce: str, access: str,
                         now: int) -> tuple[str, int]:
        if type(token) is not str or not 0 < len(token) <= 16384:
            raise ValueError("ID-token verification failed")
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("ID-token verification failed")
        header = _jwt_object(parts[0])
        # Decode JSON before PyJWT so duplicate claims and headers cannot
        # change meaning between validators.
        raw_claims = _jwt_object(parts[1])
        if (not {"alg", "kid"} <= set(header)
                or not set(header) <= {"alg", "kid", "typ"}
                or header["alg"] != "RS256"
                or header.get("typ", "JWT") != "JWT"
                or type(header["kid"]) is not str):
            raise ValueError("Unapproved ID-token header")
        key = self._keys.get(header["kid"])
        if key is None:
            raise ValueError("Unknown ID-token signer")
        try:
            claims = jwt.decode(
                token, key=key, algorithms=["RS256"],
                issuer=self._config.issuer, audience=self._config.client_id,
                options={
                    "require": ["iss", "sub", "aud", "exp", "iat", "nonce"],
                    # Manual comparisons against the trusted host clock
                    # below, not the GitHub runner's or desktop's wall clock.
                    "verify_exp": False, "verify_iat": False,
                    "verify_nbf": False,
                },
            )
        except Exception:
            raise ValueError("Signed ID-token rejected") from None
        if claims != raw_claims:
            raise ValueError("Inconsistent signed ID-token claims")
        subject = claims.get("sub")
        issued, expires = claims.get("iat"), claims.get("exp")
        if (type(subject) is not str or not 0 < len(subject) <= 128
                or type(claims.get("aud")) is not str
                or claims["aud"] != self._config.client_id
                or type(claims.get("nonce")) is not str
                or not hmac.compare_digest(claims["nonce"], nonce)
                or type(issued) is not int or type(expires) is not int
                or issued < 0 or issued > now or expires <= now
                or expires <= issued or expires - issued > _MAX_TOKEN_LIFETIME
                or (claims.get("azp", self._config.client_id)
                    != self._config.client_id)
                or ("nbf" in claims and
                    (type(claims["nbf"]) is not int or claims["nbf"] > now))):
            raise ValueError("ID-token claims rejected")
        if "at_hash" in claims:
            expected = base64.urlsafe_b64encode(
                hashlib.sha256(access.encode("ascii")).digest()[:16]
            ).rstrip(b"=").decode("ascii")
            if (type(claims["at_hash"]) is not str
                    or not hmac.compare_digest(claims["at_hash"], expected)):
                raise ValueError("Access token does not match ID token")
        return subject, expires

    def exchange_and_verify(self, code: str, verifier: str, nonce: str,
                            redirect_uri: str) -> VerifiedCodeExchange:
        """Host-only, disposable one-shot callback for DesktopSessionHost."""
        if (type(code) is not str or _CODE.fullmatch(code) is None
                or type(verifier) is not str or _PKCE.fullmatch(verifier) is None
                or type(nonce) is not str or not 16 <= len(nonce) <= 256
                or any(ord(c) < 33 or ord(c) > 126 for c in nonce)
                or type(redirect_uri) is not str
                or len(redirect_uri) > 256):
            raise ValueError("Host code exchange parameters refused")
        try:
            redirect = urlsplit(redirect_uri)
            if (redirect.scheme != "http" or redirect.hostname != "127.0.0.1"
                    or redirect.port is None or redirect.port < 1024
                    or redirect.path != "/callback"
                    or redirect.query or redirect.fragment
                    or redirect.username or redirect.password):
                raise ValueError("Invalid native redirect")
        except ValueError:
            raise ValueError("Invalid native redirect") from None
        now = self._clock()
        if type(now) is not int or now < 0:
            raise ValueError("Trusted host time unavailable")
        data = self._token_response(code, verifier, redirect_uri)
        access, identity = data.get("access_token"), data.get("id_token")
        lifetime = data.get("expires_in")
        if (type(access) is not str or not 0 < len(access) <= 8192
                or not access.isascii() or any(c.isspace() or ord(c) < 33
                                                 for c in access)
                or type(identity) is not str
                or data.get("token_type") != "Bearer"
                or type(lifetime) is not int
                or not 1 <= lifetime <= _MAX_TOKEN_LIFETIME):
            raise ValueError("Invalid host token response")
        # The IdP may include refresh_token, but the host neither retains
        # it nor supports refresh. Only returned VerifiedCodeExchange is used.
        subject, id_exp = self._verify_id_token(identity, nonce, access, now)
        expiry = min(now + lifetime, id_exp)
        if expiry <= now:
            raise ValueError("Expired verified code exchange")
        return VerifiedCodeExchange(
            access_token=access, issuer=self._config.issuer,
            client_id=self._config.client_id, nonce=nonce,
            subject=subject, expires_at=expiry,
            token_type="Bearer", signed_id_token_verified=True,
        )
