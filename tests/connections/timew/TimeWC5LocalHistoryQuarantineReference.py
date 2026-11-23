"""DOC 5 / TimeW C5 local-history quarantine at future hardware cutover.

SOURCE/CI FIXTURE ONLY. Both input collections are caller-controlled. This
module has no filesystem, network, signing, copying, activation or native
command API. It cannot verify custodian enrollment or operator consent.
Even a completely disjoint proposed new root is never trusted.
"""
from __future__ import annotations

import re

from TimeWC5SpendFenceReference import (
    MAX_MS, ReferenceRefused, _claim, _uuid4,
)

SCHEMA = "postapollo.connections.c5.timew.local-history-quarantine-fixture.v1"
FUTURE_DOMAIN = "post-apollo.connections.c5.timew.protected-candidate.v1"
LOCAL_ORIGIN = "LOCAL_DEVELOPMENT_ONLY"
CANDIDATE_ORIGIN = "SEPARATE_HARDWARE_CANDIDATE"
MODES = frozenset((
    "FRESH_EMPTY_GENESIS", "ARCHIVE_ONLY",
    "PROMOTE_LOCAL_GRANTS", "RESTORE_LOCAL_BACKUP",
))
STATES = frozenset(("ACTIVE", "SPENT", "REVOKED", "UNKNOWN"))
LOCAL_FIELDS = frozenset((
    "claim", "local_state", "source_mode", "local_head_sha256",
    "local_key_id",
))
PROPOSAL_FIELDS = frozenset((
    "schema", "candidate_origin", "candidate_domain",
    "mode", "new_genesis_id", "new_issuer_epoch", "new_key_id",
    "candidate_head_sha256", "imported_grant_ids",
    "imported_operation_ids", "imported_issuer_epochs",
    "imported_key_ids", "native_authority_requested",
    "local_fallback_requested", "claimed_admin_enrolled",
    "claimed_operator_approval",
))
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_RECORDS = 128
MAX_IMPORTED = 128


def hold(reason, *, count=0):
    """No returned bit or list can authorize grant transfer or an effect."""
    return {
        "diagnostic": reason,
        "untrusted_local_record_count": count,
        "archive_copy_performed": False,
        "archive_verified": False,
        "candidate_enrollment_verified": False,
        "operator_approval_verified": False,
        "independent_current_head_verified": False,
        "fresh_genesis_activated": False,
        "legacy_grants_imported": False,
        "historical_spent_trusted": False,
        "protected_spent_verified": False,
        "native_action_allowed": False,
        "production_authorized": False,
        "safe_retry_allowed": False,
        "undo_allowed": False,
        "safe_actions": [],
    }


def _hash(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def _strict_uuid(value):
    try:
        _uuid4(value)
        return True
    except ReferenceRefused:
        return False


def _uuid_tuple(value):
    return (type(value) is tuple and len(value) <= MAX_IMPORTED
            and all(_strict_uuid(item) for item in value)
            and len(value) == len(set(value)))


def _local_row(value):
    if type(value) is not dict or set(value) != LOCAL_FIELDS:
        return None
    if (value["source_mode"] != LOCAL_ORIGIN
            or type(value["local_state"]) is not str
            or value["local_state"] not in STATES
            or not _hash(value["local_head_sha256"])
            or not _strict_uuid(value["local_key_id"])):
        return None
    try:
        return _claim(value["claim"])
    except (ReferenceRefused, TypeError, KeyError, ValueError):
        return None


def _proposal(value):
    if type(value) is not dict or set(value) != PROPOSAL_FIELDS:
        return False
    if (value["schema"] != SCHEMA
            or value["candidate_origin"] != CANDIDATE_ORIGIN
            or value["candidate_domain"] != FUTURE_DOMAIN
            or type(value["mode"]) is not str or value["mode"] not in MODES
            or not _strict_uuid(value["new_genesis_id"])
            or not _strict_uuid(value["new_issuer_epoch"])
            or not _strict_uuid(value["new_key_id"])
            or not _hash(value["candidate_head_sha256"])
            or not all(_uuid_tuple(value[k]) for k in (
                "imported_grant_ids", "imported_operation_ids",
                "imported_issuer_epochs", "imported_key_ids"))
            or any(type(value[k]) is not bool for k in (
                "native_authority_requested", "local_fallback_requested",
                "claimed_admin_enrolled", "claimed_operator_approval"))):
        return False
    return True


def assess_local_history_cutover_fixture(*, local_records, proposal):
    """Never promote locally minted grant/history state to trusted authority.

    The "candidate" attributes and claimed operator/admin booleans are
    untrusted assertions, NOT independent proof. No external I/O or root/key
    enrollment. This test does not even create a real archive.
    """
    if type(local_records) is not tuple or len(local_records) > MAX_RECORDS:
        return hold("INVALID_LOCAL_RECORD_CONTAINER_HOLD")
    if not _proposal(proposal):
        return hold("INVALID_CUTOVER_PROPOSAL_HOLD")

    parsed = []
    grants, operations, epochs, keys, heads = set(), set(), set(), set(), set()
    for row in local_records:
        c = _local_row(row)
        if c is None:
            return hold("MALFORMED_OR_MISLABELED_LOCAL_RECORD_HOLD")
        if c["grant_id"] in grants or c["operation_id"] in operations:
            return hold("DUPLICATE_LOCAL_IDENTITY_HOLD")
        parsed.append(c)
        grants.add(c["grant_id"])
        operations.add(c["operation_id"])
        epochs.add(c["issuer_epoch"])
        keys.add(row["local_key_id"])
        heads.add(row["local_head_sha256"])

    count = len(parsed)
    if proposal["native_authority_requested"]:
        return hold("LOCAL_HISTORY_NATIVE_AUTHORITY_REQUEST_REFUSED_HOLD",
                    count=count)
    if proposal["local_fallback_requested"]:
        return hold("LOCAL_AUTHORITY_FALLBACK_REFUSED_HOLD", count=count)
    if proposal["mode"] == "PROMOTE_LOCAL_GRANTS":
        return hold("LEGACY_GRANT_PROMOTION_REFUSED_HOLD", count=count)
    if proposal["mode"] == "RESTORE_LOCAL_BACKUP":
        return hold("LOCAL_BACKUP_REPLAY_REFUSED_HOLD", count=count)
    if any(proposal[field] for field in (
        "imported_grant_ids", "imported_operation_ids",
        "imported_issuer_epochs", "imported_key_ids",
    )):
        return hold("HISTORICAL_CREDENTIAL_IMPORT_REFUSED_HOLD", count=count)
    if (proposal["new_genesis_id"] in grants | operations | epochs
            or proposal["new_issuer_epoch"] in epochs | grants | operations
            or proposal["new_key_id"] in keys
            or proposal["candidate_head_sha256"] in heads):
        return hold("LOCAL_IDENTITY_OR_HEAD_REUSE_REFUSED_HOLD", count=count)
    if proposal["mode"] == "ARCHIVE_ONLY":
        return hold("LOCAL_ARCHIVE_CANDIDATE_UNVERIFIED_HOLD", count=count)
    # Distinct syntactic identifiers do not prove separate hardware, root,
    # actual fresh genesis or independently current antirollback authority.
    return hold("FRESH_GENESIS_CANDIDATE_UNENROLLED_HOLD", count=count)
