#!/usr/bin/env python3
"""Pure synthetic, in-memory tests for MACHINE offline plan/recovery metadata.

No files, real vaults, browser processes, service accounts, root, key material
or transfer actors are used. This MUST NOT become an archive migration test.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
import MachineBraveOfflineTransferRecoveryContract as contract
import MachineBraveSealedVault as vault

A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
D = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def row(key, marker):
    return {"record_id": key, "created_at_utc": "2026-11-11T19:00:00+00:00",
            "sealed_bytes": len(marker),
            "sha256": hashlib.sha256(marker).hexdigest()}


def source(records, state="present"):
    obj = {"kind": contract.SOURCE_KIND, "source_state": state,
           "record_count": len(records),
           "total_sealed_bytes": sum(r["sealed_bytes"] for r in records),
           "records": records}
    result = {
        "status": "offline_migration_inventory_preflight",
        "inventory": obj, "inventory_sha256": contract.digest(obj),
        "read_only": True, "safe_actions": [],
    }
    result.update({key: False for key in contract.SOURCE_FALSE})
    return result


def target(records):
    obj = {"kind": contract.TARGET_KIND, "record_count": len(records),
           "total_sealed_bytes": sum(r["sealed_bytes"] for r in records),
           "records": records}
    result = {
        "status": "ci_only_protected_destination_observed",
        "observation": obj, "observation_sha256": contract.digest(obj),
        "read_only": True, "safe_actions": [],
    }
    result.update({key: False for key in contract.TARGET_FALSE})
    return result


def refused(func, *args):
    try:
        func(*args)
    except (contract.ContractRefusal, vault.VaultError):
        return
    raise AssertionError("MACHINE accepted unsafe or unbound metadata")


def replace_row(snapshot, field, records):
    updated = copy.deepcopy(snapshot)
    name = "inventory" if field == "source" else "observation"
    updated[name]["records"] = records
    updated[name]["record_count"] = len(records)
    updated[name]["total_sealed_bytes"] = sum(r["sealed_bytes"] for r in records)
    updated[name + "_sha256"] = contract.digest(updated[name])
    return updated


def guard(output):
    assert output["read_only"] is True
    assert output["migration_authorized"] is False
    assert output["restore_allowed"] is False
    assert output["safe_actions"] == []
    serial = str(output)
    for secret in ("ciphertext", "passphrase", "https://example", "/home/", "/tmp/"):
        assert secret not in serial


def main():
    a, b, c, d = row(A, b"A-secret-synthetic"), row(B, b"B-secret-synthetic"), (
        row(C, b"existing-target-synthetic")), row(D, b"unexpected")
    sb = source([a, b])
    tb = target([c])
    plan = contract.build_plan(sb, tb)
    assert contract.build_plan(sb, tb) == plan
    contract.validate_plan(plan)
    guard(plan)
    assert plan["source_sha256"] == sb["inventory_sha256"]
    assert plan["target_sha256"] == tb["observation_sha256"]
    assert plan["records"] == [a, b]
    assert plan["existing_target_records"] == [c]
    assert len(plan["plan_sha256"]) == 64

    # Explicitly no already-existing UUID replacement or empty source transfer.
    refused(contract.build_plan, source([]), tb)
    refused(contract.build_plan, source([], "absent"), tb)
    refused(contract.build_plan, sb, target([a, c]))

    # No field may smuggle authorization or synthetic evidence into positive trust.
    for key in contract.SOURCE_FALSE:
        forged = copy.deepcopy(sb)
        forged[key] = True
        refused(contract.build_plan, forged, tb)
    for key in contract.TARGET_FALSE:
        forged = copy.deepcopy(tb)
        forged[key] = True
        refused(contract.build_plan, sb, forged)
    for fixture, which in ((sb, "source"), (tb, "target")):
        modified = copy.deepcopy(fixture)
        modified["safe_actions"] = ["copy"]
        if which == "source":
            refused(contract.build_plan, modified, tb)
        else:
            refused(contract.build_plan, sb, modified)
        modified = copy.deepcopy(fixture)
        modified["extra_authenticated_claim"] = True
        if which == "source":
            refused(contract.build_plan, modified, tb)
        else:
            refused(contract.build_plan, sb, modified)

    # A modified/reordered inventory cannot be accepted with an old fingerprint.
    altered = copy.deepcopy(sb)
    altered["inventory"]["records"][0]["sha256"] = "0" * 64
    refused(contract.build_plan, altered, tb)
    altered = copy.deepcopy(sb)
    altered["inventory"]["records"].reverse()
    altered["inventory_sha256"] = contract.digest(altered["inventory"])
    refused(contract.build_plan, altered, tb)
    for malformed in (
        [{**a, "sealed_bytes": True}, b],
        [{**a, "record_id": "bad"}, b],
        [{**a, "created_at_utc": "2026-11-11"}, b],
        [{**a, "sha256": "not-sha256"}, b],
        [a, a],
        [{**a, "unrequested": "plaintext"}, b],
    ):
        refused(contract.build_plan, replace_row(sb, "source", malformed), tb)

    too_many = [row(f"{i:08x}-aaaa-4aaa-8aaa-{i:012x}", bytes([i]))
                for i in range(33)]
    refused(contract.build_plan, source(too_many), tb)
    refused(contract.build_plan, sb, target([c] * 31))
    altered_plan = copy.deepcopy(plan)
    altered_plan["migration_authorized"] = True
    refused(contract.validate_plan, altered_plan)
    altered_plan = copy.deepcopy(plan)
    altered_plan["records"][0]["sha256"] = "0" * 64
    refused(contract.validate_plan, altered_plan)
    altered_plan = copy.deepcopy(plan)
    altered_plan["restore_allowed"] = True
    refused(contract.validate_plan, altered_plan)

    # Baseline, partial and complete snapshots are observations, NOT approval.
    untouched = contract.reconcile(plan, sb, tb, sb, tb, [])
    assert untouched["status"] == "no_new_records_observed"
    guard(untouched)
    partial = target([a, c])
    observed_partial = contract.reconcile(plan, sb, tb, sb, partial, [])
    assert observed_partial["status"] == "partial_records_observed"
    assert observed_partial["new_records_observed"] == 1
    guard(observed_partial)
    complete = target([a, b, c])
    observed_complete = contract.reconcile(plan, sb, tb, sb, complete, [])
    assert observed_complete["status"] == "all_records_observed"
    assert observed_complete["requires_independent_human_review"] is True
    assert observed_complete["fixture_receipts_authenticated"] is False
    guard(observed_complete)

    # Hash-chained fixture entries are sequential, plan-bound, and untrusted.
    history = []
    history = contract.append_fixture_receipt(plan, history, A, "staged")
    history = contract.append_fixture_receipt(plan, history, A, "published")
    history = contract.append_fixture_receipt(plan, history, A, "observed")
    history = contract.append_fixture_receipt(plan, history, B, "staged")
    history = contract.append_fixture_receipt(plan, history, B, "rolled_back")
    assert contract.check_receipts(plan, history) == {
        A: "observed", B: "rolled_back"}
    observed = contract.reconcile(plan, sb, tb, sb, partial, history)
    assert observed["status"] == "partial_records_observed"
    guard(observed)
    refused(contract.append_fixture_receipt, plan, history, A, "published")
    refused(contract.append_fixture_receipt, plan, history, D, "staged")
    refused(contract.append_fixture_receipt, plan, history, B, "observed")

    replay = history + history[-1:]
    refused(contract.check_receipts, plan, replay)
    swapped = [history[1], history[0]] + history[2:]
    refused(contract.check_receipts, plan, swapped)
    tampered = copy.deepcopy(history)
    tampered[-1]["phase"] = "published"
    refused(contract.check_receipts, plan, tampered)
    tampered = copy.deepcopy(history)
    tampered[0]["previous_sha256"] = "1" * 64
    refused(contract.check_receipts, plan, tampered)
    tampered = copy.deepcopy(history)
    tampered[-1]["plan_sha256"] = "1" * 64
    refused(contract.check_receipts, plan, tampered)

    # Contradictory evidence, stale sources, changed sentinels or rogue target
    # records require manual review even when a checksum chain is syntactically valid.
    assert contract.reconcile(plan, sb, tb, sb, complete, history)[
        "status"] == "manual_reconciliation_required"
    changed_source = source([row(A, b"source mutated"), b])
    assert contract.reconcile(plan, sb, tb, changed_source, tb, [])[
        "status"] == "manual_reconciliation_required"
    changed_target = target([row(C, b"old sentinel altered")])
    assert contract.reconcile(plan, sb, tb, sb, changed_target, [])[
        "status"] == "manual_reconciliation_required"
    assert contract.reconcile(plan, sb, tb, sb, target([c, d]), [])[
        "status"] == "manual_reconciliation_required"
    assert contract.reconcile(plan, sb, tb, sb, target([row(A, b"bad"), c]), [])[
        "status"] == "manual_reconciliation_required"
    published_only = contract.append_fixture_receipt(plan, [], B, "staged")
    published_only = contract.append_fixture_receipt(
        plan, published_only, B, "published")
    assert contract.reconcile(plan, sb, tb, sb, partial, published_only)[
        "status"] == "manual_reconciliation_required"
    uncertain = contract.append_fixture_receipt(plan, [], B, "uncertain")
    assert contract.reconcile(plan, sb, tb, sb, tb, uncertain)[
        "status"] == "manual_reconciliation_required"
    refused(contract.reconcile, plan, changed_source, tb, sb, tb, [])
    refused(contract.reconcile, plan, sb, changed_target, sb, tb, [])

    # Neither synthetic chain nor metadata digest is cryptographic identity
    # or user consent, and the module has no operation that moves user data.
    source_text = (
        ROOT / "services/time/MachineBraveOfflineTransferRecoveryContract.py"
    ).read_text()
    for forbidden in ("os.chown(", "os.chmod(", "os.unlink(", "os.rename(",
                      "os.replace(", "open(", "shutil.", "subprocess.",
                      "socket.", "sqlite3.", "vault.put(", "vault.delete("):
        assert forbidden not in source_text, forbidden

    print("MACHINE offline transfer plan and unsigned recovery chain: "
          "strict snapshots, stale/forged evidence refusal, no authority PASS")


if __name__ == "__main__":
    main()
