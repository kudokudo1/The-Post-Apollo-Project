#!/usr/bin/env python3
"""Trash++ V3c // CI-ONLY separate-UID SQLite high-water fixture.

This is NOT a protected production authority. The test UID is hardcoded and
may not be provisioned or used on a workstation. A real root/authority-owner
can restore an old database and evade this self-contained ledger. Its purpose
is to exercise a distinct Linux UID, atomic witness advance, crash windows,
fork/rollback refusal and that remaining independent-anchor limitation.

Do not import from a live ArchiveStore or expose as a service/CLI.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sqlite3
import stat

from scripts.trash import archive_v3b_signed_rollback_witness as witness

TEST_OWNER_UID = 65031
TEST_BROKER_UID = 65032
PARENT_PREFIX = "trashpp-v3c-ci-"
DB_NAME = "fixture-highwater.sqlite3"
SCHEMA = "trashpp-v3c-ci-only-highwater-v1"


class FixtureRefusal(ValueError):
    """Fixed code, never reveal supplied path, signature or owner data."""


def _need(ok, code):
    if not ok:
        raise FixtureRefusal(code)


def _root(root):
    _need(type(root) is type(Path("/")) and root.is_absolute()
          and root.name == "authority" and
          root.parent.parent == Path("/tmp") and
          root.parent.name.startswith(PARENT_PREFIX) and
          os.geteuid() == TEST_OWNER_UID,
          "V3C_TEST_UID_OR_PATH_REFUSED")
    try:
        base = root.parent.lstat()
        owner = root.lstat()
        _need(stat.S_ISDIR(base.st_mode) and base.st_uid == 0
              and stat.S_IMODE(base.st_mode) == 0o711
              and stat.S_ISDIR(owner.st_mode)
              and owner.st_uid == TEST_OWNER_UID
              and stat.S_IMODE(owner.st_mode) == 0o700
              and not root.is_symlink(), "V3C_TEST_ROOT_UNSAFE")
    except OSError as exc:
        raise FixtureRefusal("V3C_TEST_ROOT_UNAVAILABLE") from exc
    return root / DB_NAME


def _check_file(path, *, exists):
    try:
        st = path.lstat()
    except FileNotFoundError:
        st = None
    except OSError as exc:
        raise FixtureRefusal("V3C_DB_PATH_UNAVAILABLE") from exc
    _need((st is not None) == exists, "V3C_DB_EXISTS_MISMATCH")
    if st is not None:
        _need(stat.S_ISREG(st.st_mode) and st.st_uid == TEST_OWNER_UID
              and st.st_nlink == 1 and
              stat.S_IMODE(st.st_mode) == 0o600,
              "V3C_DB_UNSAFE")


def _connect(root):
    path = _root(root)
    _check_file(path, exists=True)
    try:
        db = sqlite3.connect(str(path), isolation_level=None, timeout=2)
        db.execute("PRAGMA busy_timeout=2000")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA trusted_schema=OFF")
        _check_file(path, exists=True)
        return db
    except sqlite3.Error as exc:
        raise FixtureRefusal("V3C_DB_UNAVAILABLE") from exc


def _audit(db):
    try:
        _need(db.execute("PRAGMA integrity_check").fetchone() == ("ok",),
              "V3C_DB_INTEGRITY_INVALID")
        meta = db.execute("SELECT schema FROM fixture_meta").fetchall()
        _need(meta == [(SCHEMA,)], "V3C_DB_SCHEMA_INVALID")
        events = db.execute(
            "SELECT sequence,digest,predecessor,owner_id,grant_sha256,"
            "epoch,floor_sequence,release_sha256,revoked "
            "FROM witness_events ORDER BY sequence").fetchall()
        head = db.execute(
            "SELECT sequence,digest,owner_id,grant_sha256,"
            "epoch,floor_sequence,release_sha256,revoked "
            "FROM witness_head").fetchall()
        _need(len(head) <= 1 and len(events) <= 1024,
              "V3C_DB_HISTORY_INVALID")
        previous = ""
        for count, row in enumerate(events, 1):
            seq, digest, predecessor, owner, grant, epoch, floor_seq, release, revoked = row
            _need(type(seq) is int and seq == count
                  and type(digest) is str and witness._sha(digest)
                  and predecessor == previous
                  and owner in witness.ALLOWED_OWNERS
                  and witness._sha(grant) and witness._positive(epoch)
                  and witness._positive(floor_seq) and witness._sha(release)
                  and revoked in (0, 1),
                  "V3C_DB_CHAIN_INVALID")
            if count > 1:
                prior_row = events[count-2]
                _need(owner == prior_row[3] and grant == prior_row[4]
                      and revoked >= prior_row[8]
                      and epoch >= prior_row[5]
                      and (epoch > prior_row[5]
                           or floor_seq >= prior_row[6]),
                      "V3C_DB_HISTORY_INVALID")
            previous = digest
        if events:
            last = events[-1]
            _need(head == [(
                last[0], last[1], last[3], last[4],
                last[5], last[6], last[7], last[8],
            )], "V3C_DB_HEAD_MISMATCH")
        else:
            _need(head == [], "V3C_DB_HEAD_MISMATCH")
        return head[0] if head else None
    except sqlite3.Error as exc:
        raise FixtureRefusal("V3C_DB_SCHEMA_INVALID") from exc


def initialize(root):
    """Creates only an EMPTY 0600 CI database under the fixed test UID."""
    path = _root(root)
    _check_file(path, exists=False)
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
        os.fchmod(descriptor, 0o600)
        os.close(descriptor)
    except OSError as exc:
        raise FixtureRefusal("V3C_DB_CREATE_REFUSED") from exc
    db = _connect(root)
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE fixture_meta (schema TEXT PRIMARY KEY)")
        db.execute("INSERT INTO fixture_meta VALUES(?)", (SCHEMA,))
        db.execute(
            "CREATE TABLE witness_events ("
            "sequence INTEGER PRIMARY KEY, digest TEXT NOT NULL UNIQUE,"
            "predecessor TEXT NOT NULL, owner_id TEXT NOT NULL,"
            "grant_sha256 TEXT NOT NULL, epoch INTEGER NOT NULL,"
            "floor_sequence INTEGER NOT NULL, release_sha256 TEXT NOT NULL,"
            "revoked INTEGER NOT NULL CHECK(revoked IN (0,1)))")
        db.execute(
            "CREATE TABLE witness_head ("
            "sequence INTEGER PRIMARY KEY, digest TEXT NOT NULL,"
            "owner_id TEXT NOT NULL, grant_sha256 TEXT NOT NULL,"
            "epoch INTEGER NOT NULL, floor_sequence INTEGER NOT NULL,"
            "release_sha256 TEXT NOT NULL,"
            "revoked INTEGER NOT NULL CHECK(revoked IN (0,1)))")
        db.execute("COMMIT")
        _audit(db)
    except (sqlite3.Error, FixtureRefusal) as exc:
        try:
            db.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise FixtureRefusal("V3C_INIT_REFUSED") from exc
    finally:
        db.close()
    return _response(None, "TEST_EMPTY_HEAD_DENY_ONLY")


def _response(head, state):
    return {
        "state": state,
        "sequence": head[0] if head else 0,
        "witnessSha256": head[1] if head else "",
        "fixtureHistoryInternallyConsistent": True,
        "independentAnchorAuthenticated": False,
        "externallyProtectedMonotonicAuthorityVerified": False,
        "authorityOwnerRollbackDetectable": False,
        "trustedClockVerified": False,
        "sourceOwnerApprovalVerified": False,
        "captureAllowed": False, "productionAllowed": False,
        "restoreAllowed": False, "burnAllowed": False,
        "automaticRetryAllowed": False, "deleteOriginalAllowed": False,
        "safeActions": [],
    }


def inspect(root):
    db = _connect(root)
    try:
        return _response(_audit(db), "TEST_HEAD_OBSERVED_DENY_ONLY")
    finally:
        db.close()


def record(root, *, old_envelope, new_envelope, pin, floor,
           floor_signer_public_key, expected_owner_id,
           expected_grant_sha256, crash_point=None):
    """BEGIN IMMEDIATE serialized synthetic monotonic update; deny-only."""
    _need(crash_point in (None, "before_commit", "after_commit"),
          "V3C_CRASH_HOOK_REFUSED")
    witness._pin(pin, floor_signer_public_key)
    _need(type(expected_owner_id) is str
          and expected_owner_id in witness.ALLOWED_OWNERS
          and witness._sha(expected_grant_sha256),
          "V3C_POLICY_INVALID")
    try:
        witness._floor(floor)
        proposed, digest = witness._verify(new_envelope, pin)
    except (witness.WitnessRefused, ValueError) as exc:
        raise FixtureRefusal("V3C_SIGNED_EVIDENCE_REFUSED") from exc
    _need(proposed["ownerId"] == expected_owner_id == floor["ownerId"]
          and proposed["grantSha256"] == expected_grant_sha256
          and proposed["epoch"] == floor["epoch"]
          and proposed["floorSequence"] == floor["sequence"]
          and proposed["floorSha256"] == floor["externalFloorSha256"]
          and proposed["releaseSha256"] == floor["releaseSha256"],
          "V3C_FLOOR_BINDING_REFUSED")
    db = _connect(root)
    try:
        db.execute("BEGIN IMMEDIATE")
        head = _audit(db)
        if head is not None and digest == head[1]:
            db.execute("ROLLBACK")
            return _response(head, "TEST_IDENTICAL_COMMIT_OBSERVED_DENY_ONLY")
        if head is None:
            _need(old_envelope is None
                  and proposed["witnessSequence"] == 1
                  and proposed["previousWitnessSha256"] == "",
                  "V3C_FIRST_ENROLLMENT_REFUSED")
        else:
            _need(type(old_envelope) is dict, "V3C_PINNED_PREDECESSOR_REQUIRED")
            try:
                predecessor, old_digest = witness._verify(old_envelope, pin)
                result = witness.compare(
                    old_envelope, new_envelope, pin, floor,
                    expected_owner_id=expected_owner_id,
                    expected_grant_sha256=expected_grant_sha256,
                    floor_signer_public_key=floor_signer_public_key)
            except (witness.WitnessRefused, ValueError) as exc:
                raise FixtureRefusal("V3C_PREDECESSOR_REFUSED") from exc
            _need(old_digest == head[1]
                  and predecessor["witnessSequence"] == head[0]
                  and proposed["witnessSequence"] == head[0] + 1
                  and proposed["previousWitnessSha256"] == head[1]
                  and head[2] == proposed["ownerId"]
                  and head[3] == proposed["grantSha256"]
                  and (not bool(head[7]) or proposed["revoked"])
                  and set(result["holdReasons"]) <= ({
                      "same_uid_floor_fixture",
                      "off_uid_file_not_monotonic_authority",
                  } | ({"revocation_witness_observed"}
                       if proposed["revoked"] else set())),
                  "V3C_SIGNED_HISTORY_REFUSED")
        db.execute(
            "INSERT INTO witness_events VALUES(?,?,?,?,?,?,?,?,?)",
            (proposed["witnessSequence"], digest,
             proposed["previousWitnessSha256"], proposed["ownerId"],
             proposed["grantSha256"], proposed["epoch"],
             proposed["floorSequence"], proposed["releaseSha256"],
             int(proposed["revoked"])))
        db.execute("DELETE FROM witness_head")
        db.execute(
            "INSERT INTO witness_head VALUES(?,?,?,?,?,?,?,?)",
            (proposed["witnessSequence"], digest, proposed["ownerId"],
             proposed["grantSha256"], proposed["epoch"],
             proposed["floorSequence"], proposed["releaseSha256"],
             int(proposed["revoked"])))
        new_head = _audit(db)
        if crash_point == "before_commit":
            os._exit(93)
        db.execute("COMMIT")
        if crash_point == "after_commit":
            os._exit(94)
        return _response(new_head, "TEST_HEAD_COMMITTED_DENY_ONLY")
    except (sqlite3.Error, FixtureRefusal, ValueError, TypeError) as exc:
        try:
            db.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        if isinstance(exc, FixtureRefusal):
            raise
        raise FixtureRefusal("V3C_COMMIT_REFUSED") from exc
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(1)  # No CLI and no real authority enrollment.
