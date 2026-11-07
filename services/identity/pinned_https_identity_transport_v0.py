"""Host-owned, pinned HTTPS read transport for Identity Center v0.

This is an experimental, NON-ACTIVATED transport adapter for an independently
secured privileged host. It has NO CLI, daemon, autostart, token exchange,
credential persistence, identity-provider selection, or QML entrypoint.

Only two exact preapproved issuer URLs may supply discovery/JWKS metadata.
Only one exact preapproved API endpoint may receive a host-owned bearer.
Never accept a tenant, subject, endpoint, redirect, CA, token or permission
from the display widget. HTTPS certificate/hostname validation stays ON.
"""
from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
from pathlib import Path
import ssl
from urllib.parse import urlsplit

from desktop_context_projection_v0 import HostContextReply, _pairs_unique

_MAX_RESPONSE = 65536
_DENIED = b'{"status":"DENIED"}'
_RESPONSE_TYPE = "application/json"


def _url(value: object) -> tuple[str, str, int, str]:
    """Return a trusted HTTPS origin, hostname, port and exact encoded path."""
    if (type(value) is not str or not 0 < len(value) <= 2048
            or "\\" in value or any(ord(c) <= 32 or ord(c) > 126 for c in value)):
        raise ValueError("Invalid pinned HTTPS endpoint")
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
        if (parsed.scheme != "https" or not parsed.netloc or not host
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or not parsed.path
                or parsed.path.startswith("//") or "/./" in parsed.path
                or "/../" in parsed.path or "%" in parsed.path
                or port == 0):
            raise ValueError("Invalid pinned HTTPS endpoint")
        # The URL, not any server response, selects the exact network peer.
        return f"https://{parsed.netloc}", host, port or 443, parsed.path
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid pinned HTTPS endpoint") from exc


@dataclass(frozen=True, slots=True)
class PinnedIdentityHttpsConfig:
    """Approved solely by the protected host, never parsed from UI input."""

    issuer: str
    jwks_url: str
    context_url: str
    timeout_seconds: float = 3.0
    ca_bundle: Path | None = None

    def __post_init__(self) -> None:
        issuer_origin, _, _, issuer_path = _url(self.issuer)
        jwks_origin, _, _, jwks_path = _url(self.jwks_url)
        context_origin, _, _, context_path = _url(self.context_url)
        issuer_parts = urlsplit(self.issuer)
        if (self.issuer.endswith("/")
                or issuer_path in ("", "/")
                or jwks_origin != issuer_origin
                or not jwks_path.startswith(issuer_path + "/")
                or context_path != "/v0/me/contexts"
                or context_origin == ""  # Explicit, never inferred.
                or type(self.timeout_seconds) not in (float, int)
                or not 0.5 <= self.timeout_seconds <= 10
                or (self.ca_bundle is not None
                    and (not isinstance(self.ca_bundle, Path)
                         or not self.ca_bundle.is_absolute()))):
            raise ValueError("Invalid host-pinned Identity Center configuration")
        if self.ca_bundle is not None and self.ca_bundle.is_symlink():
            raise ValueError("Host CA bundle must not be a symlink")
        # No DNS resolution or transport is performed by construction.
        object.__setattr__(self, "_unused", None) if False else None

    @property
    def metadata_url(self) -> str:
        return self.issuer + "/.well-known/openid-configuration"


class HostPinnedHttpsTransport:
    """Only host-controlled exact HTTPS GETs; never a general URL fetcher.

    The API callback can be injected into DesktopHostLifecycle.api_get;
    the discovery callback into TrustedDiscoveryVerifier.fetch_json.
    Neither callback is callable via the read-only Unix socket or QML.
    """

    def __init__(self, config: PinnedIdentityHttpsConfig) -> None:
        if type(config) is not PinnedIdentityHttpsConfig:
            raise ValueError("Host-pinned configuration required")
        self._config = config

    def _get(self, pinned_url: str, bearer: str | None) -> HostContextReply:
        _, hostname, port, path = _url(pinned_url)
        # Never permit the network request to select the URL from response
        # metadata, token fields, a redirect or a local Social label.
        authorized = {
            self._config.metadata_url, self._config.jwks_url,
        } if bearer is None else {self._config.context_url}
        if pinned_url not in authorized:
            return HostContextReply(503, _RESPONSE_TYPE, _DENIED)

        connection: http.client.HTTPSConnection | None = None
        try:
            context = ssl.create_default_context(
                cafile=str(self._config.ca_bundle)
                if self._config.ca_bundle is not None else None
            )
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
                raise ValueError("Unverified HTTPS context forbidden")
            headers = {
                "Accept": "application/json",
                "Cache-Control": "no-store",
                "Accept-Encoding": "identity",
            }
            if bearer is not None:
                headers["Authorization"] = "Bearer " + bearer
            # HTTPSConnection does not use environment proxies and doesn't
            # follow Location headers. TLS cert must match pinned hostname.
            connection = http.client.HTTPSConnection(
                hostname, port, timeout=self._config.timeout_seconds,
                context=context,
            )
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            status = response.status
            if status in (401, 403) and bearer is not None:
                # Pass only a status, never an untrusted authentication body.
                return HostContextReply(status, _RESPONSE_TYPE, _DENIED)
            if (status != 200
                    or response.getheader("Content-Type", "").split(";", 1)[0].lower().strip()
                       != _RESPONSE_TYPE
                    or response.getheader("Content-Encoding", "identity").lower()
                       != "identity"):
                return HostContextReply(503, _RESPONSE_TYPE, _DENIED)
            length = response.getheader("Content-Length")
            if length is not None and (
                not length.isascii() or not length.isdecimal()
                or not 0 < int(length) <= _MAX_RESPONSE
            ):
                return HostContextReply(503, _RESPONSE_TYPE, _DENIED)
            payload = response.read(_MAX_RESPONSE + 1)
            if not 0 < len(payload) <= _MAX_RESPONSE:
                return HostContextReply(503, _RESPONSE_TYPE, _DENIED)
            return HostContextReply(200, _RESPONSE_TYPE, payload)
        except Exception:
            # Do not return the URL, TLS error, CA file, JWT, or server body.
            return HostContextReply(503, _RESPONSE_TYPE, _DENIED)
        finally:
            if connection is not None:
                connection.close()

    def fetch_json(self, pinned_url: str) -> dict[str, object]:
        """Host-only OIDC discovery/JWKS supplier with exact URL allowlist.

        Caller must still apply TrustedDiscoveryVerifier's issuer, endpoints,
        S256 and signing-key checks. A syntactically valid document is NOT an
        authentication grant, and never authorizes a role or login itself.
        """
        if type(pinned_url) is not str or pinned_url not in (
            self._config.metadata_url, self._config.jwks_url
        ):
            raise ValueError("Unapproved discovery/JWKS URL")
        reply = self._get(pinned_url, None)
        if reply.status_code != 200:
            raise ValueError("Pinned HTTPS identity data unavailable")
        try:
            data = json.loads(
                reply.body.decode("utf-8", errors="strict"),
                object_pairs_hook=_pairs_unique,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            )
            if type(data) is not dict:
                raise ValueError("Invalid issuer document")
            return data
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise ValueError("Invalid issuer document") from exc

    def get_contexts(self, bearer: str) -> HostContextReply:
        """Host-only current-user API query; the UI never supplies the token."""
        if (type(bearer) is not str or not 0 < len(bearer) <= 8192
                or any(c.isspace() or ord(c) < 33 or ord(c) > 126
                       for c in bearer)):
            return HostContextReply(401, _RESPONSE_TYPE, _DENIED)
        return self._get(self._config.context_url, bearer)
