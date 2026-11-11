#!/usr/bin/env python3
"""MACHINE // CI-only cross-resource crash windows with synthetic ciphertext.

Reuse the EXISTING disposable-root migration simulation (#1900), in-memory
recovery contract (#1911) and disposable SQLite fixture journal (#1915).
This deliberately shows that two individually consistent resources may
disagree after a process crash. It provides NO production migrator or grant.

This test REQUIRES a disposable GitHub Actions Ubuntu root runner. Do not run
on any user's workstation or use real Brave archives or service credentials.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
sys.path.insert(0, str(ROOT / "tests/timew"))

import MachineBraveOfflineTransferRecoveryContract as contract
import MachineBraveFixtureRecoveryJournal as journal
import MachineBraveCrossResourceRecoveryContract as recovery
import test_machine_protected_destination_rollback as destination
import MachineBraveSealedVault as vault

KEY = b"MACHINE-CROSS-BOUNDARY-SYNTHETIC-TEST-KEY-20261111"
SRC = destination.SOURCE_ID
EXISTING = destination.SENTINEL_ID
EXIT = {
    "before_copy": 70,
    "after_stage": 71,
    "at_link": 72,
    "after_copy": 73,
    "rollback_after_publish": 74,
    "before_journal_commit": 91,
    "after_journal_commit": 92,
    "complete": 0,
}


def require(ok):
    assert ok, "MACHINE SYNTHETIC CROSS-RESOURCE OBSERVATION FAILED"


def row(identifier, raw):
    record = vault._record(raw, identifier)
    return {
        "record_id": identifier,
        "created_at_utc": record["created_at_utc"],
        "sealed_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def source_snapshot(items):
    obj = {
        "kind": contract.SOURCE_KIND, "source_state": "present",
        "record_count": len(items),
        "total_sealed_bytes": sum(x["sealed_bytes"] for x in items),
        "records": sorted(items, key=lambda x: x["record_id"]),
    }
    response = {
        "status": "offline_migration_inventory_preflight",
        "inventory": obj, "inventory_sha256": contract.digest(obj),
        "read_only": True, "safe_actions": [],
    }
    response.update({name: False for name in contract.SOURCE_FALSE})
    return response


def target_snapshot(items):
    obj = {
        "kind": contract.TARGET_KIND, "record_count": len(items),
        "total_sealed_bytes": sum(x["sealed_bytes"] for x in items),
        "records": sorted(items, key=lambda x: x["record_id"]),
    }
    response = {
        "status": "ci_only_protected_destination_observed",
        "observation": obj, "observation_sha256": contract.digest(obj),
        "read_only": True, "safe_actions": [],
    }
    response.update({name: False for name in contract.TARGET_FALSE})
    return response


def expected():
    source_raw = destination.record(SRC, b"fixture-source")
    existing_raw = destination.record(EXISTING, b"existing-destination-sentinel")
    before_source = source_snapshot([row(SRC, source_raw)])
    before_target = target_snapshot([row(EXISTING, existing_raw)])
    plan = contract.build_plan(before_source, before_target)
    return source_raw, existing_raw, before_source, before_target, plan


def make_fixture():
    """Only disposable, named /tmp fixtures. No user paths accepted."""
    base = Path(tempfile.mkdtemp(prefix="machine-destination-ci-", dir="/tmp"))
    ledger_base = Path(tempfile.mkdtemp(prefix=journal.ROOT_PREFIX, dir="/tmp"))
    require(base.parent == ledger_base.parent == Path("/tmp"))
    require(base.name.startswith("machine-destination-ci-"))
    require(ledger_base.name.startswith(journal.ROOT_PREFIX))
    base.chmod(0o711)
    ledger_base.chmod(0o700)
    source, protected = base / "source", base / "protected"
    source.mkdir(mode=0o700)
    protected.mkdir(mode=0o700)
    os.chown(source, destination.BROWSER_UID, destination.BROWSER_UID)
    os.chown(protected, destination.SERVICE_UID, destination.SERVICE_UID)
    source.chmod(0o700)
    protected.chmod(0o700)
    raw, sentinel, before_source, before_target, plan = expected()
    srcfile = destination.make_owned_file(
        source, SRC, raw, destination.BROWSER_UID)
    sentinel_file = destination.make_owned_file(
        protected, EXISTING, sentinel, destination.SERVICE_UID)
    head = journal.initialize(ledger_base / journal.FILENAME, plan, KEY)
    return {
        "base": base, "ledger_base": ledger_base, "source": source,
        "protected": protected, "srcfile": srcfile,
        "sentinel_file": sentinel_file, "raw": raw,
        "sentinel": sentinel, "before_source": before_source,
        "before_target": before_target, "plan": plan, "head": head,
        "journal": ledger_base / journal.FILENAME,
        "original_source_inode": srcfile.stat().st_ino,
        "original_sentinel_inode": sentinel_file.stat().st_ino,
    }


def destroy(fixture):
    base, ledger_base = fixture["base"], fixture["ledger_base"]
    require(base.parent == Path("/tmp") and
            base.name.startswith("machine-destination-ci-"))
    require(ledger_base.parent == Path("/tmp") and
            ledger_base.name.startswith(journal.ROOT_PREFIX))
    shutil.rmtree(base)
    shutil.rmtree(ledger_base)


def child(mode, base, journal_path):
    source, protected = base / "source", base / "protected"
    raw, _, _, _, plan = expected()
    expected_sha = hashlib.sha256(raw).hexdigest()
    require(mode in EXIT and mode != "complete" or mode == "complete")
    if mode == "before_copy":
        os._exit(70)
    if mode == "after_stage":
        destination.fixture_transfer(
            source, protected, SRC, expected_sha,
            after_stage=lambda: os._exit(71))
        raise AssertionError("stage exit did not fire")
    if mode == "at_link":
        original_link = os.link

        def exit_after_link(*args, **kwargs):
            original_link(*args, **kwargs)
            os._exit(72)

        # Child-only monkeypatch; tests the instant after target publication
        # but before staging-link cleanup and directory fsync.
        os.link = exit_after_link
        destination.fixture_transfer(source, protected, SRC, expected_sha)
        raise AssertionError("link exit did not fire")
    if mode == "rollback_after_publish":
        try:
            destination.fixture_transfer(
                source, protected, SRC, expected_sha, inject="after_publish")
        except destination.InjectedFailure:
            os._exit(74)
        raise AssertionError("injected post-publication failure not raised")

    require(destination.fixture_transfer(
        source, protected, SRC, expected_sha) == expected_sha)
    if mode == "after_copy":
        os._exit(73)
    empty = {"sequence": 0, "mac": journal.EMPTY_MAC}
    if mode == "before_journal_commit":
        journal.append_fixture(
            journal_path, plan, KEY, empty, SRC, "staged",
            crash_point="before_commit")
        raise AssertionError("pre-commit crash did not fire")
    if mode == "after_journal_commit":
        journal.append_fixture(
            journal_path, plan, KEY, empty, SRC, "staged",
            crash_point="after_commit")
        raise AssertionError("post-commit crash did not fire")

    require(mode == "complete")
    head = journal.append_fixture(
        journal_path, plan, KEY, empty, SRC, "staged")
    head = journal.append_fixture(
        journal_path, plan, KEY, head, SRC, "published")
    head = journal.append_fixture(
        journal_path, plan, KEY, head, SRC, "observed")
    require(head["sequence"] == 3)


def run_child(mode, fixture):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(__file__).resolve()),
         "child", mode, str(fixture["base"]), str(fixture["journal"])],
        capture_output=True, text=True, timeout=18)
    require(result.returncode == EXIT[mode])
    require(result.stdout == "" and result.stderr == "")


def observe(fixture):
    """Compare two stores without pretending they share an atomic commit."""
    source, protected = fixture["source"], fixture["protected"]
    dest = protected / (SRC + ".json")
    temp = list(protected.glob(".tmp-ci-*"))
    require(all(name.name.startswith(".tmp-ci-") for name in temp))
    require(len(temp) <= 1)
    if dest.exists():
        info = dest.lstat()
        require(stat.S_ISREG(info.st_mode) and
                info.st_uid == destination.SERVICE_UID and
                stat.S_IMODE(info.st_mode) == 0o600)
        require(dest.read_bytes() == fixture["raw"])
        target_after = target_snapshot([
            row(SRC, dest.read_bytes()),
            row(EXISTING, fixture["sentinel"]),
        ])
    else:
        target_after = fixture["before_target"]

    ledger_observation = journal.inspect(
        fixture["journal"], fixture["plan"], KEY)
    phases = ledger_observation["phase_observations"]
    require(ledger_observation["migration_authorized"] is False)
    require(ledger_observation["restore_allowed"] is False)
    require(ledger_observation["independent_floor_authenticated"] is False)
    require(ledger_observation["trusted_service_authenticated"] is False)
    require(ledger_observation["operator_consent_verified"] is False)

    # The merged in-memory contract only models inventories + fixture
    # receipts. A valid target can look "all_records_observed" with an EMPTY
    # journal after a process crash. THIS IS NOT TRANSFER COMPLETION.
    old_contract = contract.reconcile(
        fixture["plan"], fixture["before_source"],
        fixture["before_target"], fixture["before_source"],
        target_after, [])
    require(old_contract["migration_authorized"] is False)
    require(old_contract["restore_allowed"] is False)
    require(old_contract["requires_independent_human_review"] is True)
    require(old_contract["safe_actions"] == [])

    complete_fixture = (
        dest.exists() and not temp and dest.stat().st_nlink == 1
        and phases.get(SRC) == "observed"
        and ledger_observation["head"]["sequence"] == 3)
    # In ANY incomplete case, do not advance or automatically clean up.
    status = ("synthetic_consistent_but_untrusted"
              if complete_fixture else "manual_reconciliation_required")
    # Independent pure contract consumes actual parent-process observations
    # from this disposable root-only fixture. Both a perfect synthetic end
    # state and an incomplete one must keep all permissions DENIED.
    artifact = {
        "stage_file_count": len(temp),
        "published_links": (
            [{"record_id": SRC, "nlink": dest.lstat().st_nlink}]
            if dest.exists() else []),
    }
    classification = recovery.classify(
        fixture["plan"], fixture["before_source"],
        fixture["before_target"], fixture["before_source"],
        target_after, ledger_observation, artifact)
    require(classification["status"] == status)
    require(classification["automatic_retry_allowed"] is False)
    require(classification["automatic_cleanup_allowed"] is False)
    require(classification["delete_original_allowed"] is False)
    require(classification["migration_authorized"] is False)
    require(classification["restore_allowed"] is False)
    require(classification["safe_actions"] == [])
    require(classification["requires_independent_human_review"] is True)
    return status, ledger_observation, old_contract, dest, temp


def verify_invariants(fixture):
    src = fixture["srcfile"]
    sentinel = fixture["sentinel_file"]
    require(src.read_bytes() == fixture["raw"])
    require(sentinel.read_bytes() == fixture["sentinel"])
    require(src.stat().st_uid == destination.BROWSER_UID)
    require(sentinel.stat().st_uid == destination.SERVICE_UID)
    require(src.stat().st_ino == fixture["original_source_inode"])
    require(sentinel.stat().st_ino == fixture["original_sentinel_inode"])
    require(stat.S_IMODE(src.stat().st_mode) == 0o600)
    require(stat.S_IMODE(sentinel.stat().st_mode) == 0o600)


def test_scenarios():
    expected_status = {
        "before_copy": (False, 0, 0),
        "after_stage": (False, 1, 0),
        "at_link": (True, 1, 0),
        "after_copy": (True, 0, 0),
        "rollback_after_publish": (False, 0, 0),
        "before_journal_commit": (True, 0, 0),
        "after_journal_commit": (True, 0, 1),
        "complete": (True, 0, 3),
    }
    for mode, (expected_target, orphan_count, expected_sequence) in (
            expected_status.items()):
        fixture = make_fixture()
        try:
            verify_invariants(fixture)
            if mode == "before_copy":
                # Actual Linux kernel permission test once per matrix.
                destination.verify_isolation(
                    fixture["source"], fixture["protected"])
            run_child(mode, fixture)
            verify_invariants(fixture)
            status, ledger, old_contract, dest, temp = observe(fixture)
            require(dest.exists() == expected_target)
            require(len(temp) == orphan_count)
            require(ledger["head"]["sequence"] == expected_sequence)
            require(status == (
                "synthetic_consistent_but_untrusted" if mode == "complete"
                else "manual_reconciliation_required"))
            if mode == "at_link":
                require(dest.stat().st_nlink == 2)
            if mode == "after_copy":
                # An identical sampled destination, with NO journal, can
                # still be reported by #1911 as all records observed.
                require(old_contract["status"] == "all_records_observed")
                require(ledger["phase_observations"] == {})
            if mode == "after_journal_commit":
                require(ledger["phase_observations"] == {SRC: "staged"})
                # Loss of the commit reply cannot replay the old head.
                try:
                    journal.append_fixture(
                        fixture["journal"], fixture["plan"], KEY,
                        fixture["head"], SRC, "staged")
                except journal.JournalRefusal:
                    pass
                else:
                    raise AssertionError("stale lost-reply retry accepted")
            if mode == "complete":
                require(ledger["phase_observations"] == {SRC: "observed"})
                # Even synthetic consistency is NOT proof of protected
                # identity, custody, backup, user consent or restoration.
                require(ledger["trusted_service_authenticated"] is False)
                require(ledger["requires_independent_human_review"] is True)
                # Post-observation tamper/missing published object demands hold.
                dest.unlink()
                require(observe(fixture)[0] == "manual_reconciliation_required")
        finally:
            destroy(fixture)


def main():
    require(sys.platform.startswith("linux") and os.geteuid() == 0)
    for uid in (destination.BROWSER_UID, destination.SERVICE_UID,
                destination.FOREIGN_UID):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            continue
        raise RuntimeError("CI synthetic UID belongs to a real user; stop")
    test_scenarios()
    print(
        "MACHINE cross-resource: 8 genuine process exit/failure windows, "
        "source/sentinel preserved, orphan and stale-ledger hold, "
        "no positive archive authority PASS")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "child":
        child(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]))
    elif len(sys.argv) == 1:
        main()
    else:
        raise SystemExit("CI fixture only; invalid arguments")
