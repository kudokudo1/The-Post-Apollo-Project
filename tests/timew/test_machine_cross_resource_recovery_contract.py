#!/usr/bin/env python3
"""MACHINE // metadata-only cross-resource recovery classifier adversarial tests.

No SQLite/real archive writes, root, live clients or native-host access.
Uses synthetic records already defined by merged eight-window crash fixture.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
sys.path.insert(0, str(ROOT / "tests/timew"))

import MachineBraveCrossResourceRecoveryContract as classifier
import MachineBraveOfflineTransferRecoveryContract as contract
import MachineBraveFixtureRecoveryJournal as journal
import test_machine_cross_resource_crash_matrix as cross


def fixture():
    source_raw, existing_raw, before_source, before_target, plan = cross.expected()
    after = cross.target_snapshot([
        cross.row(cross.SRC, source_raw),
        cross.row(cross.EXISTING, existing_raw),
    ])
    return before_source, before_target, after, plan


def journal_view(plan, phase=None, *, status="fixture_unanchored_observation"):
    phases = {cross.SRC: phase} if phase else {}
    seq = {
        None: 0, "staged": 1, "published": 2,
        "observed": 3, "rolled_back": 2, "uncertain": 1,
    }[phase]
    observation = {
        "kind": journal.KIND, "status": status,
        "head": {"sequence": seq,
                 "mac": ("0" * 64 if seq == 0 else "a" * 64)},
        "phase_observations": phases,
        "plan_sha256": plan["plan_sha256"],
        "fixture_hmac_valid": True,
        "independent_floor_authenticated": False,
        "trusted_service_authenticated": False,
        "backup_verified": False,
        "operator_consent_verified": False,
        "migration_authorized": False,
        "restore_allowed": False,
        "requires_independent_human_review": True,
        "safe_actions": [],
    }
    return observation


def artifact(*, staged=0, published=None, nlink=1):
    return {
        "stage_file_count": staged,
        "published_links": ([] if published is None else
                            [{"record_id": published, "nlink": nlink}]),
    }


def inspect(s, t, after, plan, *, phase=None, staged=0, published=False,
            nlink=1, target=None, source=None, ledger=None, physical=None):
    return classifier.classify(
        plan, s, t, source or s,
        after if target is None else target,
        journal_view(plan, phase) if ledger is None else ledger,
        artifact(staged=staged,
                 published=cross.SRC if published else None,
                 nlink=nlink) if physical is None else physical)


def denied(output):
    assert output["read_only"] is True
    assert output["requires_independent_human_review"] is True
    for name in ("independent_floor_authenticated", "client_authenticated",
                 "operator_consent_verified", "backup_verified",
                 "production_transfer_verified", "automatic_retry_allowed",
                 "automatic_cleanup_allowed", "delete_original_allowed",
                 "migration_authorized", "restore_allowed"):
        assert output[name] is False, name
    assert output["safe_actions"] == []
    assert output["journal_observation_untrusted"] is True
    assert output["snapshot_metadata_not_custody_proof"] is True
    assert "tmp/" not in str(output)


def refused(s, t, after, plan, *, altered_plan=None, altered_ledger=None,
            altered_physical=None, altered_source=None, altered_target=None):
    try:
        classifier.classify(
            altered_plan if altered_plan is not None else plan,
            s, t, altered_source if altered_source is not None else s,
            altered_target if altered_target is not None else after,
            altered_ledger if altered_ledger is not None else journal_view(plan),
            altered_physical if altered_physical is not None else artifact(),
        )
    except (classifier.RecoveryRefusal, contract.ContractRefusal,
            TypeError, ValueError, KeyError):
        return
    raise AssertionError("unsafe cross-resource input incorrectly accepted")


def main():
    s, t, after, plan = fixture()

    # The eight real crash boundaries from #1919, supplied as read-only
    # metadata rather than executing a privileged transfer here.
    scenarios = [
        ("before_copy", None, 0, False, 1,
         {"planned_publication_missing"}, False),
        ("after_stage", None, 1, False, 1,
         {"staging_leftover"}, False),
        ("at_link", None, 1, True, 2,
         {"staging_leftover", "published_link_not_single",
          "publication_without_journal_receipt"}, True),
        ("after_copy", None, 0, True, 1,
         {"publication_without_journal_receipt"}, True),
        ("rollback_after_publish", None, 0, False, 1,
         {"planned_publication_missing"}, False),
        ("before_journal_commit", None, 0, True, 1,
         {"publication_without_journal_receipt"}, True),
        ("after_journal_commit", "staged", 0, True, 1,
         {"journal_phase_incomplete"}, True),
        ("complete", "observed", 0, True, 1, set(), True),
    ]
    for name, phase, staged, published, link, want, use_after in scenarios:
        destination = after if use_after else t
        out = inspect(
            s, t, after, plan, target=destination,
            phase=phase, staged=staged, published=published, nlink=link)
        denied(out)
        assert want.issubset(set(out["hold_reasons"])), (name, out)
        assert out["status"] == (
            "synthetic_consistent_but_untrusted" if name == "complete"
            else "manual_reconciliation_required"), (name, out)
        if name == "complete":
            assert out["hold_reasons"] == []
        else:
            assert out["hold_reasons"]

    # The ledger and filesystem can contradict each other independently.
    assert "receipt_without_published_record" in inspect(
        s, t, after, plan, target=t, phase="observed")["hold_reasons"]
    assert "rolled_back_record_still_present" in inspect(
        s, t, after, plan, target=after, phase="rolled_back",
        published=True)["hold_reasons"]
    assert "journal_phase_uncertain" in inspect(
        s, t, after, plan, target=t, phase="uncertain")["hold_reasons"]
    assert "published_link_observation_missing" in inspect(
        s, t, after, plan, target=after,
        phase="observed")["hold_reasons"]
    assert "orphan_link_observation" in inspect(
        s, t, after, plan, target=t,
        physical=artifact(published=cross.SRC))["hold_reasons"]

    mismatched_head = journal_view(
        plan, "observed", status="manual_reconciliation_required")
    assert "journal_head_mismatch" in inspect(
        s, t, after, plan, ledger=mismatched_head,
        target=after, published=True)["hold_reasons"]
    # Even if the caller simply *claims* a pinned head, it is not C3e/C5
    # proof, and the classifier never emits executable permissions.
    claimed_pinned = journal_view(
        plan, "observed", status="fixture_pinned_head_observed")
    denied(inspect(s, t, after, plan, ledger=claimed_pinned,
                   published=True, target=after))

    # Unexpected destination records and modifications to an existing
    # sentinel are distinct, still read-only manual-recovery reasons.
    raw, original, *_ = cross.expected()
    extra = cross.row("cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                      cross.destination.record(
                          "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                          b"foreign synthetic"))
    unexpected = cross.target_snapshot([
        cross.row(cross.SRC, raw), cross.row(cross.EXISTING, original),
        extra])
    assert "unexpected_destination_record" in inspect(
        s, t, after, plan, target=unexpected,
        phase="observed", published=True)["hold_reasons"]
    changed_sentinel = cross.target_snapshot([
        cross.row(cross.SRC, raw),
        cross.row(cross.EXISTING,
                  cross.destination.record(cross.EXISTING,
                                            b"changed sentinel")),
    ])
    assert "preexisting_destination_changed" in inspect(
        s, t, after, plan, target=changed_sentinel,
        phase="observed", published=True)["hold_reasons"]
    changed_source = cross.source_snapshot([
        cross.row(cross.SRC, cross.destination.record(cross.SRC,
                                                      b"changed source"))])
    assert "source_inventory_changed" in inspect(
        s, t, after, plan, source=changed_source,
        phase="observed", published=True)["hold_reasons"]
    different_published = cross.target_snapshot([
        cross.row(cross.SRC, cross.destination.record(cross.SRC,
                                                      b"changed destination")),
        cross.row(cross.EXISTING, original),
    ])
    assert "published_metadata_mismatch" in inspect(
        s, t, after, plan, target=different_published,
        phase="observed", published=True)["hold_reasons"]

    # Plan/digest, journal trust flags, malformed metadata and forged
    # physical measurements cannot turn a hold into authorization.
    invalid_plan = copy.deepcopy(plan)
    invalid_plan["restore_allowed"] = True
    refused(s, t, after, plan, altered_plan=invalid_plan)
    invalid_plan = copy.deepcopy(plan)
    invalid_plan["plan_sha256"] = "0" * 64
    refused(s, t, after, plan, altered_plan=invalid_plan)
    for key in ("migration_authorized", "restore_allowed",
                "trusted_service_authenticated", "operator_consent_verified",
                "independent_floor_authenticated"):
        altered = journal_view(plan)
        altered[key] = True
        refused(s, t, after, plan, altered_ledger=altered)
    for mutated in (
        {"kind": journal.KIND},  # incomplete foreign observation
        {**journal_view(plan), "plan_sha256": "1" * 64},
        {**journal_view(plan), "safe_actions": ["retry"]},
        {**journal_view(plan), "status": "signed_trust_granted"},
        {**journal_view(plan), "phase_observations": {cross.SRC: "granted"}},
        {**journal_view(plan), "head": {"sequence": 0, "mac": "a" * 64}},
        {**journal_view(plan), "head": {"sequence": True, "mac": "0" * 64}},
        {**journal_view(plan, "observed"),
         "head": {"sequence": 1, "mac": "a" * 64}},
    ):
        refused(s, t, after, plan, altered_ledger=mutated)
    for bad in (
        {"stage_file_count": True, "published_links": []},
        {"stage_file_count": -1, "published_links": []},
        {"stage_file_count": 0, "published_links": [
            {"record_id": cross.SRC, "nlink": False}]},
        {"stage_file_count": 0, "published_links": [
            {"record_id": cross.SRC, "nlink": 1},
            {"record_id": cross.SRC, "nlink": 1}]},
        {"stage_file_count": 0, "published_links": [
            {"record_id": "../escape", "nlink": 1}]},
        {"stage_file_count": 0, "published_links": [], "grant": True},
    ):
        refused(s, t, after, plan, altered_physical=bad)

    module = (ROOT / "services/time/MachineBraveCrossResourceRecoveryContract.py"
              ).read_text()
    for forbidden in (
        "os.open(", "os.unlink(", "shutil.", "sqlite3.connect(",
        "subprocess.", "vault.put(", "vault.delete(", "os.replace(",
        "migration_authorized\": True", "restore_allowed\": True",
    ):
        assert forbidden not in module, forbidden

    print("MACHINE cross-resource recovery classification: 8 synthetic "
          "crash cases, stale/replayed or unjournaled publication, metadata "
          "drift, foreign records, no automatic action or restore PASS")


if __name__ == "__main__":
    main()
