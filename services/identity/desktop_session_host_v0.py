"""Experimental in-process privileged Identity Center session-host contract v0.

NOT a deployable login manager, browser listener, token vault, network client
or security boundary against code sharing this Python process. A future
isolated desktop host must own these objects, callbacks and secrets. NEVER
expose a host instance, callback, credential or PKCE challenge data to QML.

The code intentionally has no main(), listener, browser-launch implementation,
token exchange, token verifier, network access, credential storage or logging.
It orchestrates *injected trusted host-only operations* in disposable CI.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import hmac
import re
import secrets
from collections.abc import Callable
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from desktop_context_projection_v0 import (
    DesktopContextProjection, HostContextReply,
)

_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)
_AUTH_CODE = re.compile(r"[A-Za-z0-9._~+-]{1,2048}\Z", re.ASCII)
_MAX_LOGIN_SECONDS = 300
_MAX_TOKEN_SECONDS = 900


@dataclass(frozen=True, slots=True)
class TrustedHostConfig:
    """Preconfigured by a PRIVILEGED host, never client/QML input."""
    issuer: str
    authorization_endpoint: str
    client_id: str
    redirect_uri: str
    api_audience: str

    def __post_init__(self) -> None:
        issuer = urlsplit(self.issuer)
        auth = urlsplit(self.authorization_endpoint)
        cb = urlsplit(self.redirect_uri)
        if (issuer.scheme != "https" or not issuer.hostname
                or issuer.username or issuer.password or issuer.query
                or issuer.fragment or issuer.path in ("", "/")
                or issuer.path.endswith("/")
                or auth.scheme != "https"
                or (auth.scheme, auth.hostname, auth.port)
                    != (issuer.scheme, issuer.hostname, issuer.port)
                or auth.username or auth.password or auth.query or auth.fragment
                or not auth.path.startswith(issuer.path + "/")
                or cb.scheme != "http" or cb.hostname != "127.0.0.1"
                or cb.port is None or cb.port < 1024
                or cb.username or cb.password or cb.query or cb.fragment
                or cb.path != "/callback"
                or not _SAFE_ID.fullmatch(self.client_id)
                or not _SAFE_ID.fullmatch(self.api_audience)):
            raise ValueError("Invalid pinned native OIDC host configuration")


@dataclass(frozen=True, slots=True)
class VerifiedCodeExchange:
    """Result of the HOST's cryptographic ID token verification + exchange.

    The injected callback MUST verify signed OIDC ID token, iss, aud, nonce,
    JWT lifetime and actual code+S256 PKCE using trusted IdP endpoints.
    This object is merely an attestation from that callback, NOT verification.
    """
    access_token: str = field(repr=False)
    issuer: str
    client_id: str
    nonce: str = field(repr=False)
    subject: str = field(repr=False)
    expires_at: int
    token_type: str
    signed_id_token_verified: bool


@dataclass(frozen=True, slots=True)
class _Pending:
    verifier: str = field(repr=False)
    nonce: str = field(repr=False)
    state: str = field(repr=False)
    started_at: int


class DesktopSessionHost:
    """Test-only native-host orchestration, never reachable from Social QML.

    browser_open: only receives host-built authorization URL and must launch
      the system browser (NOT embedded webview), in a future secure host.
    exchange_and_verify: host-owned real PKCE token exchange + signed ID token
      verification; code verifier and nonce never leave host trust boundary.
    api_get: host-owned authenticated request to PINNED API, gets bearer as
      Python input; does not send it to a client-chosen URL or UI/IPC.
    """

    def __init__(self, *, config: TrustedHostConfig,
                 browser_open: Callable[[str], None],
                 exchange_and_verify: Callable[[str, str, str, str], VerifiedCodeExchange],
                 api_get: Callable[[str], HostContextReply],
                 clock: Callable[[], int]) -> None:
        if (type(config) is not TrustedHostConfig
                or not all(callable(x) for x in
                           (browser_open, exchange_and_verify, api_get, clock))):
            raise ValueError("Host-owned dependencies required")
        self._config = config
        self._browser_open = browser_open
        self._exchange = exchange_and_verify
        self._api_get = api_get
        self._clock = clock
        self._pending: _Pending | None = None
        self._access_token: str | None = None
        self._expires_at: int | None = None
        self._last_clock: int | None = None
        self._display = DesktopContextProjection(
            host_fetch=self._host_fetch, clock=self._clock,
        )

    def _now(self) -> int:
        now = self._clock()
        if (type(now) is not int or now < 0
                or (self._last_clock is not None and now < self._last_clock)):
            raise ValueError("Trusted clock missing or rolled back")
        self._last_clock = now
        return now

    def _clear(self) -> None:
        self._pending = None
        self._access_token = None
        self._expires_at = None
        self._display.disconnect()

    def logout(self) -> dict[str, object]:
        """Local logout only. Real remote session revocation needs own host."""
        self._clear()
        return self.snapshot()

    def start_login(self) -> dict[str, object]:
        """Create a fresh 256-bit state/nonce and PKCE S256 challenge."""
        self._clear()
        try:
            now = self._now()
            verifier = secrets.token_urlsafe(64)
            state = secrets.token_urlsafe(32)
            nonce = secrets.token_urlsafe(32)
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode("ascii")).digest()
            ).rstrip(b"=").decode("ascii")
            self._pending = _Pending(verifier, nonce, state, now)
            query = urlencode({
                "client_id": self._config.client_id,
                "redirect_uri": self._config.redirect_uri,
                "response_type": "code",
                "scope": "openid",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
                "nonce": nonce,
            })
            url = self._config.authorization_endpoint + "?" + query
            self._browser_open(url)
            return {"status": "LOGIN_PENDING"}
        except Exception:
            self._clear()
            return {"status": "UNAVAILABLE"}

    def complete_callback(self, callback_url: str) -> dict[str, object]:
        """Only an approved future loopback callback receiver may call this.

        The pending challenge is consumed before verification. Even a bad
        callback cancels the attempt so no duplicate/replay can succeed.
        """
        pending = self._pending
        self._clear()
        if pending is None:
            return {"status": "SIGNED_OUT"}
        try:
            now = self._now()
            if now - pending.started_at > _MAX_LOGIN_SECONDS:
                raise ValueError("Expired authorization attempt")
            if type(callback_url) is not str or len(callback_url) > 4096:
                raise ValueError("Malformed callback")
            parsed = urlsplit(callback_url)
            expected = urlsplit(self._config.redirect_uri)
            if (parsed.scheme, parsed.hostname, parsed.port, parsed.path) != (
                    expected.scheme, expected.hostname, expected.port,
                    expected.path) or parsed.username or parsed.password or parsed.fragment:
                raise ValueError("Untrusted callback origin")
            args = parse_qsl(parsed.query, keep_blank_values=True,
                             strict_parsing=True, max_num_fields=4)
            if len(args) != 3 or {k for k, _ in args} != {"code", "state", "iss"}:
                raise ValueError("Unexpected OAuth callback fields")
            values = dict(args)
            if (not hmac.compare_digest(values["state"], pending.state)
                    or values["iss"] != self._config.issuer
                    or _AUTH_CODE.fullmatch(values["code"]) is None):
                raise ValueError("State, issuer or code mismatch")
            verified = self._exchange(
                values["code"], pending.verifier,
                pending.nonce, self._config.redirect_uri,
            )
            if type(verified) is not VerifiedCodeExchange:
                raise ValueError("No trusted verified token result")
            if (verified.signed_id_token_verified is not True
                    or verified.issuer != self._config.issuer
                    or verified.client_id != self._config.client_id
                    or not hmac.compare_digest(verified.nonce, pending.nonce)
                    or type(verified.subject) is not str or not verified.subject
                    or verified.token_type != "Bearer"
                    or type(verified.expires_at) is not int
                    or not now < verified.expires_at <= now + _MAX_TOKEN_SECONDS
                    or type(verified.access_token) is not str
                    or not 0 < len(verified.access_token) <= 8192
                    or any(c.isspace() for c in verified.access_token)):
                raise ValueError("Host token attestation refused")
            self._access_token = verified.access_token
            self._expires_at = verified.expires_at
            return {"status": "SIGNED_IN"}
        except Exception:
            self._clear()
            return {"status": "SIGNED_OUT"}

    def _host_fetch(self) -> HostContextReply:
        now = self._now()
        if (self._access_token is None or self._expires_at is None
                or now >= self._expires_at):
            self._clear()
            return HostContextReply(401, "application/json",
                                    b'{"status":"DENIED"}')
        # The host is responsible for trusted HTTPS, URL allowlist, cert
        # validation and per-request API auth. This callback is not QML.
        return self._api_get(self._access_token)

    def refresh_context(self) -> dict[str, object]:
        """Only sanitized display snapshot escapes; no token/subject/code."""
        return self._display.refresh()

    def snapshot(self) -> dict[str, object]:
        try:
            now = self._now()
            if self._access_token is not None and (
                    self._expires_at is None or now >= self._expires_at):
                self._clear()
        except Exception:
            self._clear()
        return self._display.snapshot()
