"""Identity Center: read-only desktop Organizations display projection v0.

THIS IS AN INTEGRATION SEAM, NOT A TOKEN MANAGER OR CONNECTED UI.

A future privileged host owns OAuth browser/PKCE, token storage, TLS, API
credentials, audience/issuer validation and revocation. This projection gets
only the final untrusted HTTP response from a host-owned callback. It has no
network/file/process APIs and never accepts a bearer token, password, or
client-selected principal/tenant. QML must never obtain the host callback.

Strictly validate/whitelist display data; fail closed and clear on errors,
expiry and staleness. A display snapshot NEVER grants resource permissions.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from collections.abc import Callable
from typing import Any


SCHEMA = "post-apollo.identity.context-summary.v0"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)
_MAX_BYTES = 65536
_MAX_ORGANIZATIONS = 100
_MAX_PORTFOLIOS = 100
_MAX_GRANTS = 64
_MAX_AGE = 30


@dataclass(frozen=True, slots=True)
class HostContextReply:
    """Response supplied by the trusted host; carries NO credential to UI."""
    status_code: int
    content_type: str
    body: bytes


class _InvalidSnapshot(ValueError):
    pass


def _identifier(value: object) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise _InvalidSnapshot("Invalid display identifier")
    return value


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise _InvalidSnapshot("Duplicate JSON object field")
        obj[key] = value
    return obj


def _strict_json(data: bytes) -> object:
    if type(data) is not bytes or not 0 < len(data) <= _MAX_BYTES:
        raise _InvalidSnapshot("Missing or oversized response")
    try:
        return json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                _InvalidSnapshot("Nonfinite JSON number")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise _InvalidSnapshot("Invalid JSON response") from exc


def _context(body: bytes, *, now: int) -> dict[str, object]:
    payload = _strict_json(body)
    if (type(payload) is not dict
            or set(payload) != {"status", "schema", "organizations", "portfolios"}
            or payload["status"] != "OK" or payload["schema"] != SCHEMA):
        raise _InvalidSnapshot("Unexpected context envelope")
    organizations = payload["organizations"]
    portfolios = payload["portfolios"]
    if (type(organizations) is not list
            or len(organizations) > _MAX_ORGANIZATIONS
            or type(portfolios) is not list
            or len(portfolios) > _MAX_PORTFOLIOS):
        raise _InvalidSnapshot("Invalid context collections")

    sanitized_orgs: list[dict[str, object]] = []
    seen_orgs: set[str] = set()
    for item in organizations:
        if type(item) is not dict or set(item) != {
            "organizationId", "kind", "scopeGrants"
        }:
            raise _InvalidSnapshot("Unexpected organization fields")
        org_id = _identifier(item["organizationId"])
        kind = item["kind"]
        grants = item["scopeGrants"]
        if (org_id in seen_orgs or kind not in ("llc", "nonprofit", "customer")
                or type(kind) is not str or type(grants) is not list
                or len(grants) > _MAX_GRANTS):
            raise _InvalidSnapshot("Invalid organization or grants")
        seen_orgs.add(org_id)
        clean_grants: list[dict[str, object]] = []
        seen_grants: set[tuple] = set()
        for grant in grants:
            if type(grant) is not dict or set(grant) != {
                "action", "divisionId", "unitId", "expiresAt"
            }:
                raise _InvalidSnapshot("Unexpected grant fields")
            action = grant["action"]
            if type(action) is not str or action not in ("records.read", "records.write"):
                raise _InvalidSnapshot("Unsupported grant action")
            division = grant["divisionId"]
            unit = grant["unitId"]
            expiry = grant["expiresAt"]
            if division is not None:
                division = _identifier(division)
            if unit is not None:
                unit = _identifier(unit)
            if expiry is not None and (type(expiry) is not int or expiry <= now):
                raise _InvalidSnapshot("Expired or invalid grant")
            identity = (action, division, unit, expiry)
            if identity in seen_grants:
                raise _InvalidSnapshot("Duplicate scope grant")
            seen_grants.add(identity)
            clean_grants.append({
                "action": action, "divisionId": division,
                "unitId": unit, "expiresAt": expiry,
            })
        sanitized_orgs.append({
            "organizationId": org_id, "kind": kind,
            "scopeGrants": clean_grants,
        })

    sanitized_ports: list[dict[str, object]] = []
    seen_ports: set[str] = set()
    for port in portfolios:
        if type(port) is not dict or set(port) != {"portfolioId", "organizationIds"}:
            raise _InvalidSnapshot("Unexpected portfolio fields")
        port_id = _identifier(port["portfolioId"])
        members = port["organizationIds"]
        if (port_id in seen_ports or type(members) is not list
                or not members or len(members) > _MAX_ORGANIZATIONS):
            raise _InvalidSnapshot("Invalid portfolio association")
        seen_ports.add(port_id)
        org_ids = [_identifier(v) for v in members]
        if len(set(org_ids)) != len(org_ids) or not set(org_ids) <= seen_orgs:
            # A portfolio MUST NOT introduce a company absent from active
            # memberships; even an API bug cannot leak it to the UI.
            raise _InvalidSnapshot("Portfolio membership mismatch")
        sanitized_ports.append({
            "portfolioId": port_id,
            "organizationIds": org_ids,
        })
    return {"organizations": sanitized_orgs, "portfolios": sanitized_ports}


class DesktopContextProjection:
    """No tokens, networking, filesystem, or UI/permission side effects.

    Host callback must be separately reviewed, authenticated and trust-owned.
    The UI receives copies via snapshot(), never the callback or credentials.
    """

    def __init__(self, *, host_fetch: Callable[[], HostContextReply],
                 clock: Callable[[], int]) -> None:
        if not callable(host_fetch) or not callable(clock):
            raise ValueError("Trusted host callback and clock required")
        self._fetch = host_fetch
        self._clock = clock
        self._status = "NOT_CONNECTED"
        self._updated_at: int | None = None
        self._data: dict[str, object] | None = None

    def disconnect(self) -> None:
        """Forget all enterprise display data, including after explicit logout."""
        self._data = None
        self._updated_at = None
        self._status = "NOT_CONNECTED"

    def refresh(self) -> dict[str, object]:
        """Fetch afresh; never keep an older success after any new failure."""
        self.disconnect()
        try:
            now = self._clock()
            if type(now) is not int or now < 0:
                raise _InvalidSnapshot("No trusted time")
            response = self._fetch()
            if type(response) is not HostContextReply:
                raise _InvalidSnapshot("Invalid host response")
            if response.status_code in (401, 403):
                self._status = "SIGNED_OUT"
            elif response.status_code == 200:
                if (type(response.content_type) is not str or
                        response.content_type.lower().split(";", 1)[0].strip()
                        != "application/json"):
                    raise _InvalidSnapshot("Unexpected response type")
                self._data = _context(response.body, now=now)
                self._status = ("READY" if self._data["organizations"]
                                else "NO_MEMBERSHIPS")
                self._updated_at = now
            else:
                self._status = "UNAVAILABLE"
        except Exception:
            # This is a read-only display fallback, not an error reporting
            # channel. Do not surface HTTP errors, token, SQL or server details.
            self.disconnect()
            self._status = "UNAVAILABLE"
        return self.snapshot()

    def snapshot(self) -> dict[str, object]:
        """Always return a detached, copy-only display view.

        If host time or freshness is unavailable, existing private tenant
        metadata is destroyed. Never leave a stale list visible indefinitely.
        """
        if self._data is not None:
            try:
                now = self._clock()
                if (type(now) is not int or self._updated_at is None
                        or now < self._updated_at
                        or now - self._updated_at >= _MAX_AGE):
                    raise _InvalidSnapshot("Stale display data")
                for org in self._data["organizations"]:
                    for grant in org["scopeGrants"]:
                        exp = grant["expiresAt"]
                        if exp is not None and exp <= now:
                            raise _InvalidSnapshot("Display grant expired")
            except Exception:
                self.disconnect()
                self._status = "UNAVAILABLE"
        # Defensive deep copy: callers cannot mutate internal cached state.
        payload = json.loads(json.dumps(self._data)) if self._data is not None else None
        return {
            "schema": "post-apollo.identity.desktop-context-display.v0",
            "status": self._status,
            "organizations": payload["organizations"] if payload else [],
            "portfolios": payload["portfolios"] if payload else [],
            "canSwitchOrganization": False,
        }
