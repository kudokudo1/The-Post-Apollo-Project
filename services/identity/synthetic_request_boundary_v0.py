"""Identity Center v0 // OFFLINE authenticated-request *contract* fixture.

NO network listener, real identity provider, real credentials, session issuance,
user database, or production authorization. The trusted verifier is an injected
DEPENDENCY; until it is replaced by a security-reviewed IdP verifier the class
must not be exposed to untrusted clients or production data.

The purpose of this seam is to test that a request's claimed principal is NEVER
used for authorization: the caller identity comes only from verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from synthetic_policy_v0 import SyntheticPolicyStore


SCHEMA = "post-apollo.identity.synthetic-request.v0"


@dataclass(frozen=True, slots=True)
class VerifiedSession:
    """Only an injected *trusted* verifier may return this result.

    This Python dataclass is not an unforgeable certificate. The real system
    MUST validate IdP signature/introspection, issuer, audience, expiry and
    revocation before returning any authenticated session.
    """
    principal_id: str
    issuer: str
    audience: str
    session_id: str
    issued_at: int
    expires_at: int


class SessionVerifier(Protocol):
    def verify(self, token: str, *, now: int) -> VerifiedSession | None:
        """Fail closed on unknown/revoked/invalid token; never trust request claims."""
        ...


class SyntheticRequestBoundary:
    """Versioned, read-only request boundary; no HTTP binding or data mutation.

    verifier and clock MUST belong to the trusted host. Caller-controlled
    verifier/clock would trivially defeat this simulation and are not secure.
    """

    def __init__(self, policy: SyntheticPolicyStore, *,
                 verifier: SessionVerifier, clock: Callable[[], int],
                 expected_issuer: str, expected_audience: str) -> None:
        if (not callable(getattr(verifier, "verify", None))
                or not callable(clock)
                or any(type(x) is not str or not x
                       for x in (expected_issuer, expected_audience))):
            raise ValueError("A trusted verifier, clock, issuer and audience are required")
        self._policy = policy
        self._verifier = verifier
        self._clock = clock
        self._issuer = expected_issuer
        self._audience = expected_audience

    def _principal(self, token: object, now: int) -> str | None:
        if (type(token) is not str or not token or len(token) > 8192
                or token != token.strip()):
            return None
        try:
            verified = self._verifier.verify(token, now=now)
        except Exception:
            # No verifier exceptions or token details reach the caller.
            return None
        if type(verified) is not VerifiedSession:
            return None
        if (type(verified.principal_id) is not str
                or not verified.principal_id
                or type(verified.session_id) is not str
                or not verified.session_id
                or verified.issuer != self._issuer
                or verified.audience != self._audience
                or type(verified.issued_at) is not int
                or type(verified.expires_at) is not int
                or verified.issued_at < 0
                or verified.issued_at > now
                or verified.expires_at <= now
                or verified.expires_at <= verified.issued_at):
            return None
        return verified.principal_id

    def handle(self, request: object) -> dict[str, object]:
        """Return generic denial for all failures, never echo secrets.

        Two supported synthetic operations:
          authorizeRecord: schema, operation, accessToken, organizationId,
                           recordId, action
          listPortfolioOrganizations: schema, operation, accessToken,
                                      portfolioId
        Claims like principalId, role or org membership are NOT accepted.
        """
        denied = {"status": "DENIED"}
        if not isinstance(request, dict):
            return denied
        operation = request.get("operation")
        expected = (
            {"schema", "operation", "accessToken", "organizationId", "recordId", "action"}
            if operation == "authorizeRecord" else
            {"schema", "operation", "accessToken", "portfolioId"}
            if operation == "listPortfolioOrganizations" else None
        )
        if (expected is None or set(request) != expected
                or request.get("schema") != SCHEMA):
            return denied
        # Server time is not supplied by the request. Invalid clock => DENIED.
        try:
            now = self._clock()
        except Exception:
            return denied
        if type(now) is not int or now < 0:
            return denied
        principal = self._principal(request.get("accessToken"), now)
        if principal is None:
            return denied
        try:
            if operation == "authorizeRecord":
                ok = self._policy.allowed(
                    principal, request["organizationId"], request["recordId"],
                    request["action"], now=now,
                )
                return {"status": "ALLOWED"} if ok else denied
            orgs = self._policy.visible_portfolio_orgs(
                principal, request["portfolioId"]
            )
            return {"status": "OK", "organizationIds": list(orgs)}
        except Exception:
            # No SQL, policy error or user attribute is reflected to a client.
            return denied
