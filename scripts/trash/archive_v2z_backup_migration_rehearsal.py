#!/usr/bin/env python3
"""Trash++ V2z: disposable ArchiveStore backup/migration/rollback rehearsal.

Only a pre-existing private trashpp-v2z-fixture-* source and separately
pre-existing private trashpp-v2z-backups-* workspace sharing one parent are
accepted. The source requires an explicit private marker. Never writes
production ArchiveStore, never issues source/restore/burn authorization.

SQLite's online backup API captures a consistent DB snapshot. Backup bytes,
legacy payload/receipt chains, schema and accounting are verified before a
test-only V2y schema extension is exercised on a THIRD database. Recovery
copies the sealed backup into a FOURTH directory without touching the source.

The manifest is same-UID test evidence, NOT a cryptographic owner signature,
trusted clock, off-host immutable backup, or production migration approval.
"""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote

from scripts.trash.archive_store_v2 import ArchiveStore, DB_NAME, SCHEMA as ARCHIVE_SCHEMA
from scripts.trash.archive_v2_provenance import ProvenanceError, verify_receipt
from scripts.trash.archive_v2y_archive_schema_rehearsal import (
    MARKER as V2Y_MARKER, MARKER_CONTENT as V2Y_MARKER_CONTENT,
    TestArchiveStoreAdmissionV2y,
)

SOURCE_MARKER = "trashpp-v2z-fixture-only.marker"
SOURCE_MARKER_BYTES = b"post-apollo-trashpp-v2z-source-TEST-ONLY\n"
BACKUP = "sealed-baseline.sqlite3"
MANIFEST = "sealed-baseline.json"
MANIFEST_SCHEMA = "post-apollo.trashpp.v2z.test-backup-manifest"
MAX_JSON = 4096
EXPECTED_TABLES = {"archive_meta", "snapshots", "snapshot_receipts"}
EXPECTED_META = ("id", "schema_id", "revision", "payload_bytes")
EXPECTED_SNAPSHOT = (
    "id", "owner_id", "resource_id", "source_revision", "captured_ms",
    "display_label", "sha256", "payload", "provenance_required",
)
EXPECTED_RECEIPT = (
    "snapshot_id", "owner_id", "resource_id", "source_revision",
    "source_captured_ms", "archived_ms", "display_label", "payload_sha256",
    "previous_receipt_sha256", "receipt_sha256", "receipt_schema",
)
MANIFEST_FIELDS = frozenset((
    "schema", "archiveSchema", "backupSha256", "snapshotDigest",
    "revision", "items", "payloadBytes", "backupBytes",
))


class MigrationSafetyRefused(Exception):
    """Stable refusal codes, no user paths or payloads."""


def _need(ok, code):
    if not ok:
        raise MigrationSafetyRefused(code)


def _private_directory(path, expected_prefix):
    _need(type(path) is Path and path.is_absolute()
          and ".." not in path.parts and len(str(path)) <= 4096
          and path.name.startswith(expected_prefix),
          "V2Z_TEST_ROOT_REQUIRED")
    try:
        st = path.lstat()
    except OSError as exc:
        raise MigrationSafetyRefused("V2Z_TEST_ROOT_MISSING") from exc
    _need(stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid()
          and st.st_mode & 0o077 == 0 and st.st_nlink >= 2,
          "V2Z_TEST_ROOT_UNSAFE")
    return st


def _private_regular(path, *, marker=False):
    try:
        st = path.lstat()
    except OSError as exc:
        raise MigrationSafetyRefused(
            "V2Z_TEST_MARKER_MISSING" if marker else
            "V2Z_BACKUP_MISSING") from exc
    _need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1
          and st.st_uid == os.geteuid() and st.st_mode & 0o077 == 0,
          "V2Z_TEST_FILE_UNSAFE")
    return st


def _read_limited(path, limit):
    _private_regular(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC
                     | getattr(os, "O_NOFOLLOW", 0))
        try:
            _private_regular(path)
            before = os.fstat(fd)
            _need(stat.S_ISREG(before.st_mode) and
                  before.st_nlink == 1 and before.st_uid == os.geteuid()
                  and before.st_mode & 0o077 == 0 and
                  before.st_size <= limit,
                  "V2Z_TEST_FILE_UNSAFE")
            buf = os.read(fd, limit + 1)
            after = os.fstat(fd)
            _need(len(buf) <= limit
                  and (before.st_dev,before.st_ino,before.st_size,
                       before.st_mtime_ns,before.st_ctime_ns)
                    == (after.st_dev,after.st_ino,after.st_size,
                        after.st_mtime_ns,after.st_ctime_ns),
                  "V2Z_TEST_FILE_CHANGED")
            return buf
        finally:
            os.close(fd)
    except MigrationSafetyRefused:
        raise
    except OSError as exc:
        raise MigrationSafetyRefused("V2Z_TEST_FILE_UNAVAILABLE") from exc


def _create_private(path, contents):
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                     | os.O_CLOEXEC | getattr(os,"O_NOFOLLOW",0), 0o600)
        try:
            with os.fdopen(fd,"wb",closefd=False) as stream:
                stream.write(contents)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
    except FileExistsError as exc:
        raise MigrationSafetyRefused("V2Z_ARTIFACT_EXISTS") from exc
    except OSError as exc:
        raise MigrationSafetyRefused("V2Z_ARTIFACT_CREATE_FAILED") from exc


def _sync_dir(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
                     | getattr(os,"O_NOFOLLOW",0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise MigrationSafetyRefused("V2Z_DIRECTORY_SYNC_FAILED") from exc


def _hash_file(path):
    _private_regular(path)
    digest = hashlib.sha256()
    try:
        with open(path,"rb",buffering=0) as stream:
            before = os.fstat(stream.fileno())
            for chunk in iter(lambda:stream.read(256 * 1024),b""):
                digest.update(chunk)
            after = os.fstat(stream.fileno())
        _need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,
               before.st_ctime_ns) ==
              (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,
               after.st_ctime_ns),
              "V2Z_BACKUP_CHANGED")
        return digest.hexdigest(),after.st_size
    except OSError as exc:
        raise MigrationSafetyRefused("V2Z_BACKUP_UNAVAILABLE") from exc


def _has_unique_index(db, table, fields):
    for index in db.execute('PRAGMA index_list("' + table + '")'):
        if index[2] != 1:
            continue
        safe = index[1].replace('"','""')
        found = tuple(entry[2] for entry in
                      db.execute('PRAGMA index_info("' + safe + '")'))
        if found == fields:
            return True
    return False


def _inspect(path, *, with_v2y=False):
    """Full read-only integrity, relational constraints and chain audit."""
    _private_regular(path)
    uri = "file:" + quote(str(path),safe="/") + "?mode=ro&cache=private"
    try:
        with closing(sqlite3.connect(uri,uri=True,timeout=5)) as db:
            db.execute("PRAGMA query_only=ON")
            _need(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                  "V2Z_SQLITE_INTEGRITY_FAILED")
            _need(db.execute("PRAGMA foreign_key_check").fetchone() is None,
                  "V2Z_FOREIGN_KEY_FAILED")
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            expected = EXPECTED_TABLES | ({
                "fixture_signed_admissions","fixture_admission_meta"
            } if with_v2y else set())
            _need(tables == expected,"V2Z_SCHEMA_UNKNOWN")
            for name,columns in (
                ("archive_meta",EXPECTED_META),
                ("snapshots",EXPECTED_SNAPSHOT),
                ("snapshot_receipts",EXPECTED_RECEIPT)):
                got = tuple(row[1] for row in db.execute(
                    'PRAGMA table_info("' + name + '")'))
                _need(got == columns,"V2Z_SCHEMA_CHANGED")
            _need(_has_unique_index(db,"snapshots",
                                    ("owner_id","resource_id","source_revision"))
                  and _has_unique_index(db,"snapshot_receipts",
                                        ("receipt_sha256",)),
                  "V2Z_SCHEMA_CONSTRAINTS_MISSING")
            fks = db.execute("PRAGMA foreign_key_list(snapshot_receipts)").fetchall()
            _need(any(f[2]=="snapshots" and f[3]=="snapshot_id" and f[4]=="id"
                      for f in fks),"V2Z_SCHEMA_CONSTRAINTS_MISSING")
            meta = db.execute("""SELECT schema_id,revision,payload_bytes
                FROM archive_meta WHERE id=1""").fetchone()
            _need(meta is not None and meta[0] == ARCHIVE_SCHEMA
                  and type(meta[1]) is int and meta[1]>=0
                  and type(meta[2]) is int and meta[2]>=0
                  and db.execute("SELECT count(*) FROM archive_meta").fetchone()[0] == 1,
                  "V2Z_ARCHIVE_META_INVALID")
            digest = hashlib.sha256()
            total = count = 0
            parents = {}
            for record in db.execute("""SELECT s.id,s.owner_id,s.resource_id,
                s.source_revision,s.captured_ms,s.display_label,s.sha256,
                s.provenance_required,s.payload,
                r.snapshot_id,r.owner_id,r.resource_id,r.source_revision,
                r.source_captured_ms,r.archived_ms,r.display_label,
                r.payload_sha256,r.previous_receipt_sha256,
                r.receipt_sha256,r.receipt_schema
                FROM snapshots s LEFT JOIN snapshot_receipts r
                    ON r.snapshot_id=s.id
                ORDER BY s.rowid ASC"""):
                payload = record[8]
                _need(type(payload) is bytes
                      and hashlib.sha256(payload).hexdigest() == record[6],
                      "V2Z_PAYLOAD_CORRUPT")
                try:
                    receipt = verify_receipt(record[:8],record[9:])
                except ProvenanceError as exc:
                    raise MigrationSafetyRefused("V2Z_RECEIPT_CORRUPT") from exc
                key = (record[1],record[2])
                if receipt["state"] == "RECEIPT_MATCHED":
                    _need(receipt["previousReceiptHash"] ==
                          parents.get(key,""),
                          "V2Z_RECEIPT_CHAIN_BROKEN")
                    parents[key] = receipt["receiptSha256"]
                # Never serialize user payload into the backup manifest.
                row = list(record[:8]) + list(record[9:])
                digest.update(json.dumps(row,ensure_ascii=True,
                    separators=(",",":"),allow_nan=False).encode("ascii"))
                digest.update(b"\n")
                total += len(payload)
                count += 1
            _need(total == meta[2] and meta[1] >= count,
                  "V2Z_ARCHIVE_ACCOUNTING_INVALID")
            if with_v2y:
                from scripts.trash.archive_v2y_archive_schema_rehearsal import (
                    MIGRATION_SCHEMA,_valid_admission_schema,
                )
                _need(_valid_admission_schema(db)
                      and db.execute("""SELECT schema_id
                          FROM fixture_admission_meta WHERE id=1""").fetchone()
                          == (MIGRATION_SCHEMA,),
                      "V2Z_STAGE_SCHEMA_INVALID")
            return {
                "revision":meta[1],
                "items":count,
                "payloadBytes":total,
                "snapshotDigest":digest.hexdigest(),
            }
    except MigrationSafetyRefused:
        raise
    except (sqlite3.DatabaseError,TypeError,ValueError) as exc:
        raise MigrationSafetyRefused("V2Z_SQLITE_UNAVAILABLE") from exc


class TestMigrationSafetyV2z:
    """No write to input; backup, stage and recovery are separate fixtures."""

    def __init__(self, source, workspace):
        _need(type(source) is ArchiveStore and
              isinstance(workspace,(str,Path)),
              "V2Z_TEST_SOURCE_REQUIRED")
        self.source = source
        self.root = source.root
        self.workspace = Path(workspace)
        _private_directory(self.root,"trashpp-v2z-fixture-")
        _private_directory(self.workspace,"trashpp-v2z-backups-")
        _need(self.workspace.parent == self.root.parent
              and self.workspace != self.root,
              "V2Z_WORKSPACE_NOT_SEPARATE")
        _need(source.path == self.root / DB_NAME,
              "V2Z_SOURCE_DB_MISMATCH")
        _private_regular(self.root / SOURCE_MARKER,marker=True)
        _need(_read_limited(self.root / SOURCE_MARKER,256) ==
              SOURCE_MARKER_BYTES,
              "V2Z_SOURCE_MARKER_INVALID")
        self.backup_file = self.workspace / BACKUP
        self.manifest_file = self.workspace / MANIFEST

    def _guard(self):
        _private_directory(self.root,"trashpp-v2z-fixture-")
        _private_directory(self.workspace,"trashpp-v2z-backups-")
        _need(_read_limited(self.root / SOURCE_MARKER,256) ==
              SOURCE_MARKER_BYTES,
              "V2Z_SOURCE_MARKER_CHANGED")
        _private_regular(self.source.path)

    def _backup_database(self, source, target):
        _private_regular(source)
        _need(not target.exists(),"V2Z_ARTIFACT_EXISTS")
        _create_private(target,b"")
        uri = "file:" + quote(str(source),safe="/") + "?mode=ro&cache=private"
        try:
            with closing(sqlite3.connect(uri,uri=True,timeout=5)) as source_db:
                source_db.execute("PRAGMA query_only=ON")
                with closing(sqlite3.connect(str(target),timeout=5)) as backup_db:
                    source_db.backup(backup_db,pages=64,sleep=0.01)
                    backup_db.execute("PRAGMA wal_checkpoint") if False else None
                    backup_db.commit()
            with open(target,"rb") as stream:
                os.fsync(stream.fileno())
            _sync_dir(target.parent)
        except (sqlite3.DatabaseError,OSError) as exc:
            raise MigrationSafetyRefused("V2Z_BACKUP_FAILED") from exc

    def seal_backup(self, *, on_stage=None):
        _need(on_stage is None or callable(on_stage),
              "V2Z_TEST_HOOK_INVALID")
        self._guard()
        _need(not self.backup_file.exists()
              and not self.manifest_file.exists(),
              "V2Z_ARTIFACT_EXISTS")
        before = _inspect(self.source.path)
        self._backup_database(self.source.path,self.backup_file)
        if on_stage: on_stage("after_backup_copy")
        copied = _inspect(self.backup_file)
        after = _inspect(self.source.path)
        _need(copied == before == after,
              "V2Z_SOURCE_CHANGED_DURING_BACKUP")
        digest, bytes_used = _hash_file(self.backup_file)
        manifest = {
            "schema":MANIFEST_SCHEMA,
            "archiveSchema":ARCHIVE_SCHEMA,
            "backupSha256":digest,
            "snapshotDigest":copied["snapshotDigest"],
            "revision":copied["revision"],
            "items":copied["items"],
            "payloadBytes":copied["payloadBytes"],
            "backupBytes":bytes_used,
        }
        if on_stage: on_stage("before_seal")
        raw = json.dumps(manifest,sort_keys=True,
                         separators=(",",":"),ensure_ascii=True).encode("ascii")
        _need(len(raw) < MAX_JSON,"V2Z_MANIFEST_LIMIT")
        _create_private(self.manifest_file,raw)
        _sync_dir(self.workspace)
        return self.verify_backup()

    def verify_backup(self):
        self._guard()
        data = _read_limited(self.manifest_file,MAX_JSON)
        try:
            manifest = json.loads(data.decode("ascii"))
        except (UnicodeError,ValueError,TypeError) as exc:
            raise MigrationSafetyRefused("V2Z_MANIFEST_INVALID") from exc
        _need(type(manifest) is dict
              and set(manifest) == MANIFEST_FIELDS
              and manifest["schema"] == MANIFEST_SCHEMA
              and manifest["archiveSchema"] == ARCHIVE_SCHEMA
              and json.dumps(manifest,sort_keys=True,separators=(",",":"),
                             ensure_ascii=True).encode("ascii") == data,
              "V2Z_MANIFEST_INVALID")
        digest,size = _hash_file(self.backup_file)
        _need(digest == manifest["backupSha256"]
              and size == manifest["backupBytes"],
              "V2Z_BACKUP_HASH_MISMATCH")
        measured = _inspect(self.backup_file)
        _need(all(measured[name] == manifest[name] for name in
                  ("snapshotDigest","revision","items","payloadBytes")),
              "V2Z_BACKUP_CONTENT_MISMATCH")
        return {
            "state":"TEST_SEALED_BACKUP_VERIFIED_DENY_ONLY",
            "snapshotDigest":measured["snapshotDigest"],
            "backupSha256":digest,"items":measured["items"],
            "revision":measured["revision"],
            "payloadBytes":measured["payloadBytes"],
            "backupBytes":size,
            "productionAllowed":False,
            "captureAllowed":False,
            "restoreAllowed":False,
            "burnAllowed":False,
        }

    def _new_stage(self, name, *, on_stage=None):
        sealed = self.verify_backup()
        target_dir = self.workspace / name
        try:
            target_dir.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise MigrationSafetyRefused("V2Z_STAGE_EXISTS") from exc
        except OSError as exc:
            raise MigrationSafetyRefused("V2Z_STAGE_CREATE_FAILED") from exc
        _private_directory(target_dir,"trashpp-v2y-fixture-")
        _create_private(target_dir / V2Y_MARKER,V2Y_MARKER_CONTENT)
        target = target_dir / DB_NAME
        self._backup_database(self.backup_file,target)
        if on_stage: on_stage("after_stage_copy")
        _need(_inspect(target)["snapshotDigest"] ==
              sealed["snapshotDigest"],
              "V2Z_STAGE_BASELINE_MISMATCH")
        return target_dir, sealed

    def rehearse_schema(self, *, on_stage=None):
        _need(on_stage is None or callable(on_stage),
              "V2Z_TEST_HOOK_INVALID")
        staged, sealed = self._new_stage(
            "trashpp-v2y-fixture-stage",on_stage=on_stage)
        archive = ArchiveStore(staged)
        bridge = TestArchiveStoreAdmissionV2y(archive)
        if on_stage: on_stage("after_stage_migration")
        verified = _inspect(staged / DB_NAME,with_v2y=True)
        _need(verified["snapshotDigest"] == sealed["snapshotDigest"]
              and verified["items"] == sealed["items"]
              and verified["payloadBytes"] == sealed["payloadBytes"]
              and verified["revision"] == sealed["revision"],
              "V2Z_LEGACY_RECORDS_CHANGED")
        self.verify_backup()
        # Reassess source; staged migration must never change original bytes.
        original = _inspect(self.source.path)
        _need(original["snapshotDigest"] == sealed["snapshotDigest"]
              and original["revision"] == sealed["revision"],
              "V2Z_SOURCE_CHANGED_DURING_REHEARSAL")
        return {
            "state":"TEST_STAGE_SCHEMA_MIGRATED_DENY_ONLY",
            "stageSchemaVerified":True,
            "legacyRecordsPreserved":True,
            "backupSha256":sealed["backupSha256"],
            "sourceAuthorityVerified":False,
            "productionAllowed":False,"captureAllowed":False,
            "restoreAllowed":False,"burnAllowed":False,
        }

    def rehearse_recovery(self, *, on_stage=None):
        """Never overwrites stage or source; creates a fourth isolated DB."""
        _need(on_stage is None or callable(on_stage),
              "V2Z_TEST_HOOK_INVALID")
        restored,sealed = self._new_stage(
            "trashpp-v2y-fixture-recovery",on_stage=on_stage)
        state = _inspect(restored / DB_NAME)
        _need(state["snapshotDigest"] == sealed["snapshotDigest"]
              and state["revision"] == sealed["revision"]
              and state["payloadBytes"] == sealed["payloadBytes"]
              and state["items"] == sealed["items"],
              "V2Z_RECOVERY_FAILED")
        self.verify_backup()
        return {
            "state":"TEST_ISOLATED_RECOVERY_VERIFIED_DENY_ONLY",
            "restoredItems":state["items"],
            "backupSha256":sealed["backupSha256"],
            "originalArchiveModified":False,
            "productionAllowed":False,"captureAllowed":False,
            "restoreAllowed":False,"burnAllowed":False,
        }
