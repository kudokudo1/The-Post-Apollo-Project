#!/usr/bin/env python3
"""MACHINE: offline, non-authorizing transfer plan and recovery evidence contract.

Pure metadata arithmetic against the UNMERGED source-preflight (#1898) and
protected-target-readiness (#1906) response schemas. No filesystem I/O,
transfer, key, service, IPC, browser host, migration CLI, or permission grant.
Receipts are UNSIGNED synthetic observations, never durable proof or consent.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveSealedVault as vault

KIND = "machine-offline-transfer-recovery-contract-v1"
SOURCE_KIND = "machine-protected-archive-migration-inventory-v1"
TARGET_KIND = "machine-protected-destination-readiness-observation-v1"
ZERO = "0" * 64
ROW_FIELDS = {"record_id", "created_at_utc", "sealed_bytes", "sha256"}
SOURCE_FALSE = ("source_ciphertext_authentication_verified",
                "distinct_service_uid_installed", "protected_destination_inspected",
                "independent_backup_verified", "client_authenticated",
                "operator_consent_verified", "migration_authorized", "restore_allowed")
TARGET_FALSE = ("path_ancestry_authenticated",
                "kernel_cross_uid_isolation_verified", "selinux_policy_verified",
                "backup_verified", "client_authenticated",
                "operator_consent_verified", "migration_authorized", "restore_allowed")
PLAN_FIELDS = {"kind", "source_sha256", "target_sha256", "records",
               "existing_target_records", "plan_sha256", "read_only",
               "migration_authorized", "restore_allowed", "safe_actions"}
RECEIPT_FIELDS = {"sequence", "record_id", "record_sha256", "phase",
                  "previous_sha256", "plan_sha256", "entry_sha256"}
TRANSITIONS = {
    None: {"staged", "uncertain"},
    "staged": {"published", "rolled_back", "uncertain"},
    "published": {"observed", "rolled_back", "uncertain"},
    "observed": set(),
    "rolled_back": set(),
    "uncertain": set(),
}


class ContractRefusal(ValueError):
    pass


def refuse():
    raise ContractRefusal("MACHINE OFFLINE TRANSFER CONTRACT REFUSED")


def require(condition):
    if not condition:
        refuse()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(value):
    require(type(value) is str and vault.DIGEST_RE.fullmatch(value) is not None)
    return value


def rows(value):
    require(type(value) is list and len(value) <= vault.MAX_RECORDS)
    result = []
    identifiers = set()
    for item in value:
        require(type(item) is dict and set(item) == ROW_FIELDS)
        key = item["record_id"]
        require(type(key) is str and vault.ID_RE.fullmatch(key) is not None
                and key not in identifiers)
        identifiers.add(key)
        size = item["sealed_bytes"]
        require(type(size) is int and 0 < size <= vault.MAX_RECORD)
        stamp = item["created_at_utc"]
        require(type(stamp) is str and len(stamp) <= 64)
        try:
            moment = dt.datetime.fromisoformat(stamp)
            require(moment.utcoffset() == dt.timedelta(0))
        except (TypeError, ValueError, OverflowError):
            refuse()
        result.append({"record_id": key, "created_at_utc": stamp,
                       "sealed_bytes": size, "sha256": sha(item["sha256"])})
    require([r["record_id"] for r in result] ==
            sorted(r["record_id"] for r in result))
    return result


def snapshot(value, kind):
    require(type(value) is dict and kind in ("source", "target"))
    false_fields = SOURCE_FALSE if kind == "source" else TARGET_FALSE
    fields = ({"status", "inventory", "inventory_sha256", "read_only",
               "safe_actions"} if kind == "source" else
              {"status", "observation", "observation_sha256", "read_only",
               "safe_actions"})
    require(set(value) == fields | set(false_fields))
    require(value["read_only"] is True and value["safe_actions"] == [])
    require(all(value[key] is False for key in false_fields))
    name = "inventory" if kind == "source" else "observation"
    hash_name = name + "_sha256"
    expected_status = ("offline_migration_inventory_preflight" if kind == "source"
                       else "ci_only_protected_destination_observed")
    require(value["status"] == expected_status)
    obj = value[name]
    require(type(obj) is dict)
    expected = ({"kind", "source_state", "record_count",
                 "total_sealed_bytes", "records"} if kind == "source" else
                {"kind", "record_count", "total_sealed_bytes", "records"})
    require(set(obj) == expected)
    require(obj["kind"] == (SOURCE_KIND if kind == "source" else TARGET_KIND))
    if kind == "source":
        require(obj["source_state"] in ("present", "absent"))
    records = rows(obj["records"])
    require(type(obj["record_count"]) is int and
            obj["record_count"] == len(records))
    require(type(obj["total_sealed_bytes"]) is int and
            obj["total_sealed_bytes"] == sum(r["sealed_bytes"] for r in records))
    require(sha(value[hash_name]) == digest(obj))
    return records


def plan_payload(plan):
    return {key: plan[key] for key in PLAN_FIELDS - {"plan_sha256"}}


def validate_plan(plan):
    require(type(plan) is dict and set(plan) == PLAN_FIELDS)
    require(plan["kind"] == KIND and plan["read_only"] is True)
    require(plan["migration_authorized"] is False and
            plan["restore_allowed"] is False and plan["safe_actions"] == [])
    sha(plan["source_sha256"])
    sha(plan["target_sha256"])
    proposed = rows(plan["records"])
    existing = rows(plan["existing_target_records"])
    require(proposed and len(proposed) + len(existing) <= vault.MAX_RECORDS)
    require(not ({r["record_id"] for r in proposed} &
                 {r["record_id"] for r in existing}))
    require(sha(plan["plan_sha256"]) == digest(plan_payload(plan)))
    return proposed, existing


def build_plan(source, target):
    """Describe a possible encrypted-only copy. NEVER execute it."""
    proposed, existing = snapshot(source, "source"), snapshot(target, "target")
    require(source["inventory"]["source_state"] == "present" and proposed)
    require(len(proposed) + len(existing) <= vault.MAX_RECORDS)
    require(not ({r["record_id"] for r in proposed} &
                 {r["record_id"] for r in existing}))
    result = {
        "kind": KIND,
        "source_sha256": source["inventory_sha256"],
        "target_sha256": target["observation_sha256"],
        "records": proposed,
        "existing_target_records": existing,
        "read_only": True,
        "migration_authorized": False,
        "restore_allowed": False,
        "safe_actions": [],
    }
    result["plan_sha256"] = digest(result)
    validate_plan(result)
    return result


def check_receipts(plan, receipts):
    """Validate a deterministic, unauthenticated fixture hash chain."""
    proposed, _ = validate_plan(plan)
    permitted = {row["record_id"]: row["sha256"] for row in proposed}
    require(type(receipts) is list and len(receipts) <= 4 * len(proposed))
    prior = ZERO
    phases = {}
    for index, entry in enumerate(receipts, 1):
        require(type(entry) is dict and set(entry) == RECEIPT_FIELDS)
        key = entry["record_id"]
        require(type(key) is str and key in permitted)
        require(type(entry["sequence"]) is int and entry["sequence"] == index)
        require(entry["record_sha256"] == permitted[key])
        require(entry["plan_sha256"] == plan["plan_sha256"])
        require(entry["previous_sha256"] == prior)
        phase = entry["phase"]
        require(type(phase) is str and phase in TRANSITIONS[phases.get(key)])
        require(sha(entry["entry_sha256"]) ==
                digest({k: entry[k] for k in RECEIPT_FIELDS - {"entry_sha256"}}))
        prior = entry["entry_sha256"]
        phases[key] = phase
    return phases


def append_fixture_receipt(plan, history, record_id, phase):
    """In-memory fixture entry, NOT a signed or persisted recovery ledger."""
    phases = check_receipts(plan, history)
    proposed, _ = validate_plan(plan)
    mapping = {row["record_id"]: row["sha256"] for row in proposed}
    require(type(record_id) is str and record_id in mapping)
    require(type(phase) is str and phase in TRANSITIONS[phases.get(record_id)])
    entry = {
        "sequence": len(history) + 1, "record_id": record_id,
        "record_sha256": mapping[record_id], "phase": phase,
        "previous_sha256": history[-1]["entry_sha256"] if history else ZERO,
        "plan_sha256": plan["plan_sha256"],
    }
    entry["entry_sha256"] = digest(entry)
    result = history + [entry]
    check_receipts(plan, result)
    return result


def reconcile(plan, before_source, before_target, after_source, after_target, receipts):
    """Compare sampled metadata. Never authorize move, deletion or restore."""
    require(plan == build_plan(before_source, before_target))
    proposed, existing = validate_plan(plan)
    current_source = snapshot(after_source, "source")
    current_target = snapshot(after_target, "target")
    phases = check_receipts(plan, receipts)
    baseline = {r["record_id"]: r for r in existing}
    planned = {r["record_id"]: r for r in proposed}
    present = {r["record_id"]: r for r in current_target}
    uncertain = (
        after_source["inventory_sha256"] != plan["source_sha256"] or
        current_source != proposed or
        any(present.get(k) != v for k, v in baseline.items()) or
        any(k not in baseline and (k not in planned or planned[k] != value)
            for k, value in present.items()) or
        any((phase in ("published", "observed") and k not in present) or
            (phase == "rolled_back" and k in present) or
            phase == "uncertain"
            for k, phase in phases.items())
    )
    newly_observed = sum(k in present for k in planned)
    state = ("manual_reconciliation_required" if uncertain else
             "no_new_records_observed" if not newly_observed else
             "all_records_observed" if newly_observed == len(planned) else
             "partial_records_observed")
    return {
        "kind": "machine-offline-transfer-recovery-observation-v1",
        "status": state,
        "plan_sha256": plan["plan_sha256"],
        "new_records_observed": newly_observed,
        "planned_records": len(planned),
        "fixture_receipt_count": len(receipts),
        "fixture_receipts_authenticated": False,
        "requires_independent_human_review": True,
        "read_only": True,
        "source_custody_authenticated": False,
        "backup_verified": False,
        "client_authenticated": False,
        "operator_consent_verified": False,
        "migration_authorized": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


if __name__ == "__main__":
    # No executable migration or production operator interface.
    raise SystemExit(1)
