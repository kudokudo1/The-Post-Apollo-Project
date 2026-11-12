#!/usr/bin/env python3
"""Trash++ V3a // READ-ONLY, DENY-ONLY production cutover gap assessment.

Consumes V2w and V2z *result-shaped, untrusted metadata*. It neither verifies
those source signatures nor performs any filesystem/SQLite operation. A caller
may not self-declare protected signing, independent monotonic authority,
trusted time, a writer freeze, owner consent or production readiness.

Do not wire this to the live Archive broker, migration, Restore or Burn.
"""
from __future__ import annotations

from scripts.trash.archive_v2_signed_capture import ALLOWED_OWNERS, SHA

KIND = "post-apollo.trashpp.v3a.cutover-readiness-review"
OBS_KIND = "post-apollo.trashpp.v3a.untrusted-cutover-observation"

FLOOR_FIELDS = frozenset((
    "state", "ownerId", "epoch", "sequence", "externalFloorSha256",
    "releaseSha256", "signatureVerified", "offUidFileObserved",
    "externallyProtectedMonotonicAuthorityVerified", "trustedClockVerified",
    "sourceAuthorityVerified", "captureAllowed", "productionAllowed",
    "restoreAllowed", "burnAllowed",
))
BACKUP_FIELDS = frozenset((
    "state", "snapshotDigest", "backupSha256", "items", "revision",
    "payloadBytes", "backupBytes", "productionAllowed", "captureAllowed",
    "restoreAllowed", "burnAllowed",
))
STAGE_FIELDS = frozenset((
    "state", "stageSchemaVerified", "legacyRecordsPreserved",
    "backupSha256", "sourceAuthorityVerified", "productionAllowed",
    "captureAllowed", "restoreAllowed", "burnAllowed",
))
RECOVERY_FIELDS = frozenset((
    "state", "restoredItems", "backupSha256", "originalArchiveModified",
    "productionAllowed", "captureAllowed", "restoreAllowed", "burnAllowed",
))
OBS_FIELDS = frozenset((
    "kind", "ownerId", "sourceRevisionObserved", "sourceSnapshotDigestObserved",
    "sourceItemCountObserved", "activeWritersObserved", "postBackupWritesObserved",
    "floorEpochObserved", "floorSequenceObserved", "floorReleaseSha256Observed",
    "writerFreezeState", "signerCustodyState", "backupCustodyState",
    "trustedTimeState", "monotonicWitnessState", "sourceOwnerApprovalState",
    "rollbackState", "c3eState", "c5State", "productionAllowed",
))
FALSE_TRUST = (
    "externallyProtectedMonotonicAuthorityVerified", "trustedClockVerified",
    "sourceAuthorityVerified", "captureAllowed", "productionAllowed",
    "restoreAllowed", "burnAllowed",
)
FALSE_ACTIONS = ("captureAllowed", "productionAllowed", "restoreAllowed",
                 "burnAllowed")


class ReadinessRefused(ValueError):
    """No paths, keys, SQL payloads or caller input in the exception."""


def _need(ok, code):
    if not ok:
        raise ReadinessRefused(code)


def _fields(value, expected, code):
    _need(type(value) is dict and set(value) == expected, code)


def _nonnegative(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def _positive(value):
    return type(value) is int and 1 <= value <= 1000000000


def _sha(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _negative(value, keys):
    return all(value[key] is False for key in keys)


def _floor(value):
    _fields(value, FLOOR_FIELDS, "V3A_FLOOR_SCHEMA_REFUSED")
    _need(value["state"] in (
        "TEST_EXTERNAL_FLOOR_MATCHED_DENY_ONLY",
        "OFF_UID_FLOOR_OBSERVED_DENY_ONLY"),
        "V3A_FLOOR_STATE_REFUSED")
    _need(type(value["ownerId"]) is str and
          value["ownerId"] in ALLOWED_OWNERS and
          _positive(value["epoch"]) and _positive(value["sequence"]) and
          _sha(value["externalFloorSha256"]) and
          _sha(value["releaseSha256"]) and
          value["signatureVerified"] is True and
          type(value["offUidFileObserved"]) is bool and
          value["offUidFileObserved"] is (
              value["state"] == "OFF_UID_FLOOR_OBSERVED_DENY_ONLY") and
          _negative(value, FALSE_TRUST),
          "V3A_FLOOR_AUTHORITY_REFUSED")


def _backup(value):
    _fields(value, BACKUP_FIELDS, "V3A_BACKUP_SCHEMA_REFUSED")
    _need(value["state"] == "TEST_SEALED_BACKUP_VERIFIED_DENY_ONLY" and
          _sha(value["backupSha256"]) and
          _sha(value["snapshotDigest"]) and
          _nonnegative(value["items"]) and
          _nonnegative(value["revision"]) and
          _nonnegative(value["payloadBytes"]) and
          type(value["backupBytes"]) is int and
          1 <= value["backupBytes"] <= 2**63 - 1 and
          _negative(value, FALSE_ACTIONS),
          "V3A_BACKUP_STATE_REFUSED")


def _stage(value, backup):
    _fields(value, STAGE_FIELDS, "V3A_STAGE_SCHEMA_REFUSED")
    _need(value["state"] == "TEST_STAGE_SCHEMA_MIGRATED_DENY_ONLY" and
          value["stageSchemaVerified"] is True and
          value["legacyRecordsPreserved"] is True and
          value["backupSha256"] == backup["backupSha256"] and
          value["sourceAuthorityVerified"] is False and
          _negative(value, FALSE_ACTIONS),
          "V3A_STAGE_EVIDENCE_REFUSED")


def _recovery(value, backup):
    _fields(value, RECOVERY_FIELDS, "V3A_RECOVERY_SCHEMA_REFUSED")
    _need(value["state"] == "TEST_ISOLATED_RECOVERY_VERIFIED_DENY_ONLY" and
          value["backupSha256"] == backup["backupSha256"] and
          type(value["restoredItems"]) is int and
          value["restoredItems"] == backup["items"] and
          value["originalArchiveModified"] is False and
          _negative(value, FALSE_ACTIONS),
          "V3A_RECOVERY_EVIDENCE_REFUSED")


def _observation(value, floor):
    _fields(value, OBS_FIELDS, "V3A_OBSERVATION_SCHEMA_REFUSED")
    _need(value["kind"] == OBS_KIND and
          value["ownerId"] == floor["ownerId"] and
          _nonnegative(value["sourceRevisionObserved"]) and
          _sha(value["sourceSnapshotDigestObserved"]) and
          _nonnegative(value["sourceItemCountObserved"]) and
          _nonnegative(value["activeWritersObserved"]) and
          _nonnegative(value["postBackupWritesObserved"]) and
          _positive(value["floorEpochObserved"]) and
          _positive(value["floorSequenceObserved"]) and
          _sha(value["floorReleaseSha256Observed"]) and
          value["writerFreezeState"] in (
              "not_requested", "unknown", "expired", "contested") and
          value["signerCustodyState"] in ("unverified", "unprovisioned") and
          value["backupCustodyState"] in ("same_uid_fixture", "unverified") and
          value["trustedTimeState"] == "unverified" and
          value["monotonicWitnessState"] == "unverified" and
          value["sourceOwnerApprovalState"] == "not_obtained" and
          value["rollbackState"] in ("unverified", "isolated_copy_only") and
          value["c3eState"] == "unverified" and
          value["c5State"] == "unverified" and
          value["productionAllowed"] is False,
          "V3A_UNTRUSTED_APPROVAL_CLAIM_REFUSED")


def review(floor, backup, stage, recovery, cutover):
    """Assess *gaps*, never produce a deploy/migrate/restore decision.

    All input objects are caller-provided observations. Even mutually
    consistent fixture inputs cannot satisfy independent authority gates.
    """
    _floor(floor)
    _backup(backup)
    _stage(stage, backup)
    _recovery(recovery, backup)
    _observation(cutover, floor)
    reasons = {
        "production_source_signer_unverified",
        "source_owner_authorization_missing",
        "independent_monotonic_release_history_unverified",
        "trusted_time_unverified",
        "off_host_backup_custody_unverified",
        "production_writer_freeze_unverified",
        "safe_live_cutover_unverified",
        "lossless_rollback_unverified",
        "c3e_authenticated_source_unverified",
        "c5_one_use_human_consent_unverified",
        "production_snapshot_admission_unverified",
    }
    if not floor["offUidFileObserved"]:
        reasons.add("floor_is_same_uid_test_fixture")
    else:
        reasons.add("off_uid_floor_not_monotonic_proof")
    if cutover["activeWritersObserved"] != 0:
        reasons.add("active_archive_writers_observed")
    if cutover["postBackupWritesObserved"] != 0:
        reasons.add("post_backup_writes_observed")
    if cutover["sourceRevisionObserved"] != backup["revision"]:
        reasons.add("backup_source_revision_disagreement")
    if cutover["sourceSnapshotDigestObserved"] != backup["snapshotDigest"]:
        reasons.add("backup_source_digest_disagreement")
    if cutover["sourceItemCountObserved"] != backup["items"]:
        reasons.add("backup_source_item_count_disagreement")
    if cutover["floorEpochObserved"] != floor["epoch"]:
        reasons.add("release_epoch_disagreement")
    if cutover["floorSequenceObserved"] != floor["sequence"]:
        reasons.add("release_sequence_disagreement")
    if cutover["floorReleaseSha256Observed"] != floor["releaseSha256"]:
        reasons.add("release_digest_disagreement")
    if cutover["writerFreezeState"] in ("expired", "contested"):
        reasons.add("writer_lease_expired_or_contested")

    return {
        "schema": KIND,
        "state": "PRODUCTION_CUTOVER_HOLD",
        "holdReasons": sorted(reasons),
        "observedOwnerId": floor["ownerId"],
        "sourceRevisionObserved": cutover["sourceRevisionObserved"],
        "sealedBackupRevision": backup["revision"],
        "syntheticV2wShapeAccepted": True,
        "syntheticV2zShapeAccepted": True,
        "snapshotDataInspectedByV3a": False,
        "sourceAuthorityVerified": False,
        "trustedClockVerified": False,
        "independentReleaseFloorVerified": False,
        "offHostBackupCustodyVerified": False,
        "writerFreezeVerified": False,
        "productionAllowed": False,
        "captureAllowed": False,
        "restoreAllowed": False,
        "burnAllowed": False,
        "automaticCutoverAllowed": False,
        "automaticRollbackAllowed": False,
        "deleteOriginalAllowed": False,
        "safeActions": [],
        "requiresIndependentReview": True,
        "readOnly": True,
    }


if __name__ == "__main__":
    raise SystemExit(1)  # No production CLI or migration operation.
