"""Experimental read-only WSGI /v0/me/contexts transport contract.

This MODULE DOES NOT START A SERVER. Only CI may bind a disposable loopback
listener. Authentication is an injected trusted verifier and clock; callers
of Python can replace these dependencies, so this is NOT a protected host.
No login flow, durable audit, TLS, rate limits, public API or real user data.

A real service must own its verifier, key rotation/revocation and DB connection,
extract a bearer token from an authenticated transport, and apply separate
current authorization to every privileged operation.
"""
from __future__ import annotations

from collections.abc import Callable
import json

from durable_context_store_v0 import DurableContextStore
from synthetic_request_boundary_v0 import SessionVerifier, VerifiedSession


class ReadOnlyContextApp:
    """Only GET /v0/me/contexts, with no caller-selected principal or tenant."""

    def __init__(self, *, store: DurableContextStore, verifier: SessionVerifier,
                 clock: Callable[[], int], issuer: str, audience: str) -> None:
        if (not isinstance(store, DurableContextStore)
                or not callable(getattr(verifier, "verify", None))
                or not callable(clock)
                or type(issuer) is not str or not issuer
                or type(audience) is not str or not audience):
            raise ValueError("Trusted host dependencies are required")
        self._store = store
        self._verifier = verifier
        self._clock = clock
        self._issuer = issuer
        self._audience = audience

    def _response(self, environ: dict) -> tuple[str, dict[str, object]]:
        if (environ.get("PATH_INFO") != "/v0/me/contexts"
                or environ.get("SCRIPT_NAME") not in ("", None)):
            return "404 Not Found", {"status": "DENIED"}
        if environ.get("REQUEST_METHOD") != "GET":
            return "405 Method Not Allowed", {"status": "DENIED"}
        # No query-string person, org, role, portfolio, time or API-key input.
        if environ.get("QUERY_STRING") or environ.get("CONTENT_LENGTH") not in ("", None, "0"):
            return "400 Bad Request", {"status": "DENIED"}
        header = environ.get("HTTP_AUTHORIZATION")
        if (type(header) is not str or not header.startswith("Bearer ")
                or len(header) > 8200 or "\n" in header or "\r" in header):
            return "401 Unauthorized", {"status": "DENIED"}
        token = header[7:]
        if (not token or token != token.strip()
                or len(token) > 8192 or any(c.isspace() for c in token)):
            return "401 Unauthorized", {"status": "DENIED"}
        try:
            now = self._clock()
            if type(now) is not int or now < 0:
                return "401 Unauthorized", {"status": "DENIED"}
            session = self._verifier.verify(token, now=now)
            if (type(session) is not VerifiedSession
                    or type(session.principal_id) is not str
                    or not session.principal_id
                    or type(session.session_id) is not str
                    or not session.session_id
                    or session.issuer != self._issuer
                    or session.audience != self._audience
                    or type(session.issued_at) is not int
                    or type(session.expires_at) is not int
                    or session.issued_at < 0 or session.issued_at > now
                    or session.expires_at <= now
                    or session.expires_at <= session.issued_at):
                return "401 Unauthorized", {"status": "DENIED"}
            # session.principal_id is the IdP provider subject; the internal
            # principal is resolved only through issuer+subject DB mapping.
            context = self._store.summary(
                self._issuer, session.principal_id, now=now,
            )
            if context is None:
                return "401 Unauthorized", {"status": "DENIED"}
            return "200 OK", context
        except Exception:
            # No verification/SQLite exception, provider subject or token
            # ever reaches the HTTP client as a diagnostic.
            return "503 Service Unavailable", {"status": "DENIED"}

    def __call__(self, environ: dict, start_response: Callable):
        status, payload = self._response(environ)
        body = json.dumps(payload, separators=(",", ":"),
                          ensure_ascii=True).encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("Pragma", "no-cache"),
            ("Vary", "Authorization"),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
        ]
        if status.startswith("405"):
            headers.append(("Allow", "GET"))
        start_response(status, headers)
        return [body]
