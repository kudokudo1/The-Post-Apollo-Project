#!/usr/bin/env python3
"""MACHINE // pure, fail-closed classification of synthetic cross-resource states.

This is a READ-ONLY contract for separately sampled source/target metadata,
fixture-only SQLite journal observations, and synthetic staging/link counts.
It never opens an archive, consults the filesystem, persists a receipt,
executes a transfer, deletes anything, or authorizes a retry or restore.

A fixture HMAC-valid journal is NOT a trusted writer, an externally anchored
release floor, C3e process/seat identity, C5 human consent or actual custody.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveOfflineTransferRecoveryContract as offline
import MachineBraveFixtureRecoveryJournal as journal
import MachineBraveSealedVault as vault

KIND = "machine-cross-resource-recovery-classification-v1"
OBSERVATION_FIELDS = {"stage_file_count", "published_links"}
LINK_FIELDS = {"record_id", "nlink"}
JOURNAL_FIELDS = {
    "kind", "status", "head", "phase_observations", "plan_sha256",
    "fixture_hmac_valid", "independent_floor_authenticated",
    "trusted_service_authenticated", "backup_verified",
    "operator_consent_verified", "migration_authorized", "restore_allowed",
    "requires_independent_human_review", "safe_actions",
}
FALSE_JOURNAL_FIELDS = (
    "independent_floor_authenticated", "trusted_service_authenticated",
    "backup_verified", "operator_consent_verified",
    "migration_authorized", "restore_allowed",
)
ALLOWED_JOURNAL_STATUSES = {
    "fixture_unanchored_observation",
    "fixture_pinned_head_observed",
    "manual_reconciliation_required",
}
PHASES = {"staged", "published", "observed", "rolled_back", "uncertain"}
MINIMUM_TRANSITIONS = {
    "staged": 1, "published": 2, "observed": 3,
    "rolled_back": 2, "uncertain": 1,
}


class RecoveryRefusal(ValueError):
    pass


def refuse():
    raise RecoveryRefusal("MACHINE CROSS-RESOURCE RECOVERY CONTRACT REFUSED")


def require(condition):
    if not condition:
        refuse()


def _journal_view(plan, observation):
    """Check the *reported* fixture journal format, not signer authority."""
    require(type(observation) is dict and set(observation) == JOURNAL_FIELDS)
    require(observation["kind"] == journal.KIND)
    require(observation["status"] in ALLOWED_JOURNAL_STATUSES)
    require(observation["plan_sha256"] == plan["plan_sha256"])
    require(observation["fixture_hmac_valid"] is True)
    require(all(observation[key] is False for key in FALSE_JOURNAL_FIELDS))
    require(observation["requires_independent_human_review"] is True)
    require(observation["safe_actions"] == [])

    head = observation["head"]
    require(type(head) is dict and set(head) == {"sequence", "mac"})
    require(type(head["sequence"]) is int and
            0 <= head["sequence"] <= 4 * len(plan["records"]))
    offline.sha(head["mac"])
    if head["sequence"] == 0:
        require(head["mac"] == journal.EMPTY_MAC)

    phases = observation["phase_observations"]
    require(type(phases) is dict and len(phases) <= len(plan["records"]))
    allowed = {r["record_id"] for r in plan["records"]}
    require(all(type(key) is str and key in allowed and
                type(value) is str and value in PHASES
                for key, value in phases.items()))
    require(head["sequence"] >=
            sum(MINIMUM_TRANSITIONS[phase] for phase in phases.values()))
    return phases


def _artifact_view(value):
    """Untrusted, already-measured counts. Never inspect paths or inodes."""
    require(type(value) is dict and set(value) == OBSERVATION_FIELDS)
    stage_count = value["stage_file_count"]
    require(type(stage_count) is int and
            0 <= stage_count <= vault.MAX_RECORDS)
    links = value["published_links"]
    require(type(links) is list and len(links) <= vault.MAX_RECORDS)
    result = {}
    for entry in links:
        require(type(entry) is dict and set(entry) == LINK_FIELDS)
        key = entry["record_id"]
        count = entry["nlink"]
        require(type(key) is str and
                vault.ID_RE.fullmatch(key) is not None and key not in result)
        require(type(count) is int and 0 <= count <= 1024)
        result[key] = count
    return stage_count, result


def classify(plan, before_source, before_target, after_source, after_target,
             journal_observation, artifact_observation):
    """One bounded, deterministic classification. Never propose an action.

    Reject malformed, foreign or positively authorizing schemas. Classify
    individually valid but mutually inconsistent observations as a manual
    HOLD, including a published record that the journal never committed.
    """
    require(type(plan) is dict)
    require(plan == offline.build_plan(before_source, before_target))
    proposed, existing = offline.validate_plan(plan)
    current_source = offline.snapshot(after_source, "source")
    current_target = offline.snapshot(after_target, "target")
    phases = _journal_view(plan, journal_observation)
    stage_count, link_counts = _artifact_view(artifact_observation)

    prior = {r["record_id"]: r for r in existing}
    planned = {r["record_id"]: r for r in proposed}
    current = {r["record_id"]: r for r in current_target}
    new_records = {key: current[key] for key in planned if key in current}
    reasons = set()

    if (after_source["inventory_sha256"] != plan["source_sha256"] or
            current_source != proposed):
        reasons.add("source_inventory_changed")
    if any(current.get(key) != value for key, value in prior.items()):
        reasons.add("preexisting_destination_changed")
    if any(key not in prior and key not in planned for key in current):
        reasons.add("unexpected_destination_record")
    if stage_count:
        reasons.add("staging_leftover")
    if journal_observation["status"] == "manual_reconciliation_required":
        reasons.add("journal_head_mismatch")
    if any(key not in new_records for key in link_counts):
        reasons.add("orphan_link_observation")

    for key, expected in planned.items():
        observed = current.get(key)
        phase = phases.get(key)
        if observed is None:
            reasons.add("planned_publication_missing")
            if phase in {"published", "observed"}:
                reasons.add("receipt_without_published_record")
        else:
            if observed != expected:
                reasons.add("published_metadata_mismatch")
            if phase is None:
                reasons.add("publication_without_journal_receipt")
            elif phase == "rolled_back":
                reasons.add("rolled_back_record_still_present")
            elif phase != "observed":
                reasons.add("journal_phase_incomplete")
            if key not in link_counts:
                reasons.add("published_link_observation_missing")
            elif link_counts[key] != 1:
                reasons.add("published_link_not_single")
        if phase == "uncertain":
            reasons.add("journal_phase_uncertain")

    consistent_fixture_only = (not reasons and
                               len(new_records) == len(planned) and
                               all(phases.get(k) == "observed" for k in planned))
    return {
        "kind": KIND,
        "status": ("synthetic_consistent_but_untrusted"
                   if consistent_fixture_only
                   else "manual_reconciliation_required"),
        "hold_reasons": sorted(reasons),
        "plan_sha256": plan["plan_sha256"],
        "planned_records": len(planned),
        "published_records_observed": len(new_records),
        "journal_observation_untrusted": True,
        "snapshot_metadata_not_custody_proof": True,
        "independent_floor_authenticated": False,
        "client_authenticated": False,
        "operator_consent_verified": False,
        "backup_verified": False,
        "production_transfer_verified": False,
        "requires_independent_human_review": True,
        "read_only": True,
        "automatic_retry_allowed": False,
        "automatic_cleanup_allowed": False,
        "delete_original_allowed": False,
        "migration_authorized": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


if __name__ == "__main__":
    # No operator or production execution entrypoint.
    raise SystemExit(1)
