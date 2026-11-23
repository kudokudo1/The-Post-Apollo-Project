"""DOC 6 Identity V5 diagnostic-only native admission preflight.

This module is deliberately non-authorizing. A dictionary of evidence claims
can report which external owner contracts are outstanding, but *even all True*
claims cannot prove their provenance or mint a protected command capability.

No gateway, socket, QML, OAuth, signer, storage, or C5 issuer is imported here.
The eventual native bridge must use separately reviewed, authenticated provider
interfaces; it must NEVER promote the diagnostic output to an allow decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

SCHEMA = "post-apollo.identity.native-admission-diagnostic.v0"
REQUIRED = (
    "c3e_external_custodian",
    "c3e_history_antirollback",
    "c4b_identity_signed_install",
    "c4b_live_process_and_seat",
    "receipt_key_custody",
    "c5_human_one_use_intent",
    "c5_outcome_reconciliation",
)
_ACTIONS = frozenset(("BEGIN", "STATUS", "CANCEL", "RECOVER"))
_STATES = frozenset(("NOT_READY", "UNKNOWN_HOLD"))


@dataclass(frozen=True, slots=True)
class NativeAdmissionDiagnostic:
    schema: str
    action: str
    state: str
    missing: tuple[str, ...]
    can_begin_sign_in: bool = False
    can_cancel: bool = False
    can_recover: bool = False
    can_connect_provider: bool = False
    production_authority: bool = False


def inspect_evidence_claims(
    *, action: str, claims: Mapping[str, object] | None,
    command_outcome_unknown: bool = False,
) -> NativeAdmissionDiagnostic:
    """Non-executable negative projection; claims are never attestations.

    An ambiguous dispatched command is UNKNOWN_HOLD, even if *all* claims
    say true. Unknown keys, unknown actions, non-bool claims and missing
    evidence are strictly diagnosed as NOT_READY, never silently accepted.
    This function cannot contact a provider or consume an operator grant.
    """
    if type(action) is not str or action not in _ACTIONS:
        raise ValueError("Unknown Identity command action")
    if type(command_outcome_unknown) is not bool:
        raise ValueError("Outcome uncertainty must be an exact boolean")
    if claims is None:
        claims = {}
    if not isinstance(claims, Mapping):
        raise ValueError("Diagnostic claims must be a mapping")

    # Freeze a bounded, exact field set; caller objects are not retained.
    try:
        keys = tuple(claims.keys())
        if (len(keys) > len(REQUIRED)
                or any(type(key) is not str or key not in REQUIRED for key in keys)):
            raise ValueError("Unexpected native admission evidence field")
        values = {field: claims[field] for field in keys}
    except (KeyError, TypeError, RuntimeError) as exc:
        raise ValueError("Unstable native admission evidence") from exc
    if any(type(value) is not bool for value in values.values()):
        raise ValueError("Native admission evidence claims must be booleans")
    missing = tuple(field for field in REQUIRED if values.get(field) is not True)
    state = "UNKNOWN_HOLD" if command_outcome_unknown else "NOT_READY"
    assert state in _STATES
    return NativeAdmissionDiagnostic(
        schema=SCHEMA, action=action, state=state, missing=missing,
    )
