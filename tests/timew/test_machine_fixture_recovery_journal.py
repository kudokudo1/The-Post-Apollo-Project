#!/usr/bin/env python3
"""MACHINE // disposable CI only: crash-safe synthetic receipt journal tests.

No archives, browser sessions, user accounts or live host. The HMAC key is a
publicly visible TEST KEY; it confers no actual client/service authorization.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
import MachineBraveOfflineTransferRecoveryContract as contract
import MachineBraveFixtureRecoveryJournal as journal

KEY = b"MACHINE-FIXTURE-NOT-A-LIVE-KEY-1234567890"
A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def row(key, marker):
    return {"record_id": key, "created_at_utc": "2026-11-11T20:00:00+00:00",
            "sealed_bytes": len(marker),
            "sha256": hashlib.sha256(marker).hexdigest()}


def source(records):
    inventory = {
        "kind": contract.SOURCE_KIND, "source_state": "present",
        "record_count": len(records),
        "total_sealed_bytes": sum(x["sealed_bytes"] for x in records),
        "records": records,
    }
    result = {"status": "offline_migration_inventory_preflight",
              "inventory": inventory, "inventory_sha256": contract.digest(inventory),
              "read_only": True, "safe_actions": []}
    result.update({key: False for key in contract.SOURCE_FALSE})
    return result


def target(records):
    observation = {
        "kind": contract.TARGET_KIND, "record_count": len(records),
        "total_sealed_bytes": sum(x["sealed_bytes"] for x in records),
        "records": records,
    }
    result = {"status": "ci_only_protected_destination_observed",
              "observation": observation,
              "observation_sha256": contract.digest(observation),
              "read_only": True, "safe_actions": []}
    result.update({key: False for key in contract.TARGET_FALSE})
    return result


def sample():
    return contract.build_plan(
        source([row(A, b"fixture-a"), row(B, b"fixture-b")]),
        target([row(C, b"existing-sentinel")]))


def refused(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except (journal.JournalRefusal, contract.ContractRefusal):
        return
    raise AssertionError("unsafe fixture ledger operation unexpectedly accepted")


def hold(output):
    assert output["trusted_service_authenticated"] is False
    assert output["independent_floor_authenticated"] is False
    assert output["operator_consent_verified"] is False
    assert output["backup_verified"] is False
    assert output["migration_authorized"] is False
    assert output["restore_allowed"] is False
    assert output["safe_actions"] == []
    assert output["requires_independent_human_review"] is True
    assert "fixture-a" not in repr(output)


def fixture():
    root = Path(tempfile.mkdtemp(prefix=journal.ROOT_PREFIX, dir="/tmp"))
    root.chmod(0o700)
    return root, root / journal.FILENAME


def crash_child(mode, path, expected):
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(Path(__file__).resolve()),
         "crash", mode, str(path), str(expected["sequence"]), expected["mac"]],
        capture_output=True, text=True, timeout=10)
    assert not result.stderr, result.stderr
    assert result.returncode == (91 if mode == "before_commit" else 92), (
        result.returncode, result.stdout)
    assert not result.stdout


def child_main():
    mode, path, number, mac = sys.argv[2:]
    journal.append_fixture(
        Path(path), sample(), KEY, {"sequence": int(number), "mac": mac},
        A, "staged", crash_point=mode)
    raise AssertionError("crash injection returned")


def test_normal():
    root, path = fixture()
    try:
        plan = sample()
        empty = journal.initialize(path, plan, KEY)
        assert empty == {"sequence": 0, "mac": journal.EMPTY_MAC}
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.stat().st_nlink == 1
        refused(journal.initialize, path, plan, KEY)
        refused(journal.append_fixture, path, plan, KEY,
                {"sequence": 1, "mac": "0" * 64}, A, "staged")
        refused(journal.append_fixture, path, plan, KEY, empty, A, "observed")
        refused(journal.append_fixture, path, plan, KEY, empty, C, "staged")
        refused(journal.append_fixture, path, plan, KEY, empty, A, "unknown")

        head = journal.append_fixture(path, plan, KEY, empty, A, "staged")
        assert head["sequence"] == 1
        refused(journal.append_fixture, path, plan, KEY, empty, B, "staged")
        sight = journal.inspect(path, plan, KEY, head)
        assert sight["status"] == "fixture_pinned_head_observed"
        assert sight["fixture_hmac_valid"] is True
        assert sight["phase_observations"] == {A: "staged"}
        hold(sight)

        head = journal.append_fixture(path, plan, KEY, head, A, "published")
        head = journal.append_fixture(path, plan, KEY, head, A, "observed")
        head = journal.append_fixture(path, plan, KEY, head, B, "staged")
        head = journal.append_fixture(path, plan, KEY, head, B, "rolled_back")
        assert head["sequence"] == 5
        refused(journal.append_fixture, path, plan, KEY, head, B, "published")
        refused(journal.append_fixture, path, plan, KEY, head, A, "staged")
        observed = journal.inspect(path, plan, KEY, head)
        assert observed["phase_observations"] == {A: "observed", B: "rolled_back"}
        hold(observed)
        unanchored = journal.inspect(path, plan, KEY)
        assert unanchored["status"] == "fixture_unanchored_observation"
        assert unanchored["head"] == head
        assert journal.inspect(path, plan, KEY, empty)[
            "status"] == "manual_reconciliation_required"
        refused(journal.inspect, path, plan, b"wrong-test-key-" * 3, head)
        forged = dict(plan)
        forged["migration_authorized"] = True
        refused(journal.inspect, path, forged, KEY, head)
        refused(journal.append_fixture, path, forged, KEY, head, A, "uncertain")
        refused(journal.inspect, path, plan, b"tiny", head)
        refused(journal.inspect, root / "other.sqlite3", plan, KEY)
    finally:
        shutil.rmtree(root)


def test_crashes():
    plan = sample()
    for crash in ("before_commit", "after_commit"):
        root, path = fixture()
        try:
            empty = journal.initialize(path, plan, KEY)
            crash_child(crash, path, empty)
            sight = journal.inspect(path, plan, KEY)
            hold(sight)
            if crash == "before_commit":
                assert sight["head"] == empty
                assert sight["phase_observations"] == {}
                assert journal.inspect(path, plan, KEY, empty)[
                    "status"] == "fixture_pinned_head_observed"
            else:
                assert sight["head"]["sequence"] == 1
                assert sight["phase_observations"] == {A: "staged"}
                assert journal.inspect(path, plan, KEY, empty)[
                    "status"] == "manual_reconciliation_required"
                # Reply loss must not silently cause a second stage event.
                refused(journal.append_fixture, path, plan, KEY, empty, A, "staged")
            assert not list(root.glob("*-journal"))
        finally:
            shutil.rmtree(root)


def test_tamper_and_floor():
    plan = sample()
    for scenario in ("mac", "sequence", "rollback"):
        root, path = fixture()
        try:
            empty = journal.initialize(path, plan, KEY)
            h1 = journal.append_fixture(path, plan, KEY, empty, A, "staged")
            h2 = journal.append_fixture(path, plan, KEY, h1, A, "published")
            with sqlite3.connect(path) as sql:
                if scenario == "mac":
                    sql.execute("UPDATE events SET mac=? WHERE sequence=2",
                                ("f" * 64,))
                elif scenario == "sequence":
                    sql.execute("UPDATE events SET sequence=9 WHERE sequence=2")
                else:
                    # A valid authenticated prefix is not proof against a
                    # valid-prefix rollback. Only an EXTERNAL pinned head sees it.
                    sql.execute("DELETE FROM events WHERE sequence=2")
            if scenario == "rollback":
                assert journal.inspect(path, plan, KEY)["head"] == h1
                assert journal.inspect(path, plan, KEY, h2)[
                    "status"] == "manual_reconciliation_required"
            else:
                refused(journal.inspect, path, plan, KEY, h2)
        finally:
            shutil.rmtree(root)


def test_invalid_paths():
    plan = sample()
    root, path = fixture()
    try:
        root.chmod(0o755)
        refused(journal.initialize, path, plan, KEY)
        root.chmod(0o700)
        empty = journal.initialize(path, plan, KEY)
        alias = root / "alias"
        alias.symlink_to(path)
        refused(journal.inspect, alias, plan, KEY, empty)
        path.chmod(0o644)
        refused(journal.inspect, path, plan, KEY, empty)
        path.chmod(0o600)
        bad = Path("/tmp") / journal.FILENAME
        refused(journal.initialize, bad, plan, KEY)
    finally:
        shutil.rmtree(root)


def test_static_no_archives():
    module = (ROOT / "services/time/MachineBraveFixtureRecoveryJournal.py").read_text()
    for forbidden in ("vault.put(", "vault.delete(", "MachineBraveSaveHost",
                      "shutil.copy", "subprocess.run(", "socket.bind(",
                      "migration_authorized\": True", "restore_allowed\": True"):
        assert forbidden not in module, forbidden


def main():
    assert sys.platform.startswith("linux")
    test_normal()
    test_crashes()
    test_tamper_and_floor()
    test_invalid_paths()
    test_static_no_archives()
    print("MACHINE fixture recovery ledger: MAC tamper, real SQLite pre/post-commit "
          "crash recovery, stale anchored floor and deny-only flags PASS")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "crash":
        child_main()
    else:
        main()
