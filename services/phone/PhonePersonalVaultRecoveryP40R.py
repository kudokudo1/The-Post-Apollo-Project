"""P40R // Read-only observation after an uncertain Personal contact vault write.

An atomic file rename can succeed even when the following directory fsync
fails. The resulting error is not evidence that a write did not happen.

This tool reports only *currently observed* authenticated encrypted state.
It does not establish an installed host, verify C5 consent, grant a retry,
produce durable anti-rollback evidence, provision keys or activate PHONE.
A trusted future host must independently authorize every inspection.
No CLI, QML, D-Bus, keyring or provider entry point is implemented.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import PhonePersonalContactIdentity as Identity
import PhonePersonalContactVault as Vault

SCHEMA = "post-apollo.phone.personal-vault-post-write-observation.p40r"
BASE = {
    "schema": SCHEMA,
    "productionEnabled": False,
    "writeAuthorized": False,
    "retryAuthorized": False,
    "durableCommitProven": False,
}
REFUSED = {**BASE, "status": "OBSERVATION_UNAVAILABLE"}
MATCH = {**BASE, "status": "CURRENT_CIPHERTEXT_MATCHES_PENDING"}
PRIOR = {**BASE, "status": "CURRENT_CIPHERTEXT_HAS_PRIOR_REVISION"}
OTHER = {**BASE, "status": "CURRENT_CIPHERTEXT_UNRESOLVED"}


def _fingerprint(document: dict[str, object]) -> bytes:
    # Fixed-size local comparison; plaintext or contact identifiers never
    # leave this function or appear in status messages.
    canonical = json.dumps(
        document, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(b"postapollo.phone.p40r.pending\x00" + canonical).digest()


def inspect_after_uncertain_save(
    *, master_key: object, profile: object, root: object,
    pending_document: object, expected_revision: object,
) -> dict[str, object]:
    """Observe the current sealed revision; NEVER authorize resubmission.

    MATCH means the encrypted file *currently* matches the expected P34
    document, not that a prior fsync succeeded or rollback is impossible.
    PRIOR might mean no write, or a restored old ciphertext. Neither state
    is sufficient to retry automatically. On malformed/tampered data, deny.
    """
    try:
        if (type(master_key) is not bytes or len(master_key) != 32
                or type(profile) is not str
                or Identity.PROFILE.fullmatch(profile) is None
                or not isinstance(root, Path) or not root.is_absolute()
                or root.name != Vault.ROOT_NAME
                or type(expected_revision) is not int
                or not 0 <= expected_revision < 2**53 - 2
                or not Identity.valid_document(pending_document)
                or pending_document["revision"] != expected_revision + 1
                or any(row["profileId"] != profile
                       for row in pending_document["entries"])):
            return dict(REFUSED)
        current = Vault.read(master_key, profile, root)
        if (not Identity.valid_document(current)
                or any(row["profileId"] != profile
                       for row in current["entries"])):
            return dict(REFUSED)
        if current["revision"] == pending_document["revision"]:
            if hmac.compare_digest(
                _fingerprint(current), _fingerprint(pending_document)
            ):
                return dict(MATCH)
            return dict(OTHER)
        if current["revision"] == expected_revision:
            return dict(PRIOR)
        return dict(OTHER)
    except Exception:
        # No note, key, profile, file path or upstream exception can escape.
        return dict(REFUSED)


# Deliberately no save, erase, retry, unlock, auto-recovery, or host IPC.
