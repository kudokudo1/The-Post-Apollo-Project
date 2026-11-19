#!/usr/bin/env python3
"""BG2 native fixture scheduler + crash-recoverable occurrence outbox.

The owning process may tick a DISPOSABLE V2 file after the B2B20 old
writer exits and its SQLite launch gate is held. Uses the same V2 tick
semantics as mounted QML. Real sound/notification is deliberately absent.

The outbox commits PREPARED before an atomic file replace, SAVED after
file+directory fsync, and DELIVERING before an isolated fixture callback.
An uncertain delivery is NEVER silently retried: real providers require
idempotent delivery acknowledgements before this is production-ready.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

# Modules are loaded only from this checked-in Clock component directory.
import importlib.util
import sys


def _load(filename, module):
    spec = importlib.util.spec_from_file_location(
        module, Path(__file__).resolve().with_name(filename))
    if spec is None or spec.loader is None:
        raise RuntimeError("Clock BG2 component unavailable")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


Policy = _load("AlarmNativeTickPolicy.py", "clock_bg2_v2_policy")
Final = _load("AlarmFinalV2SourceWitness.py", "clock_bg2_v2_final")

MAX_SOURCE = 2 * 1024 * 1024


class Refused(ValueError):
    """Fixed refusal codes; no alarm names, paths or private content."""


class ClockFixtureNativeEngine:
    """A native V2 fixture writer, never an installed ring permission."""

    def __init__(self, *, controller, synthetic_only=False):
        if synthetic_only is not True:
            raise Refused("PRODUCTION_BG2_NOT_INSTALLED")
        self.controller = controller
        self.uid = os.getuid()
        self._gate()
        self.source = controller.final.source
        self.digest = controller.final.pinned_sha256
        self.db = controller.ledger.conn
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS native_tick_outbox("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "phase TEXT NOT NULL,"
            "before_digest TEXT NOT NULL,"
            "after_digest TEXT NOT NULL,"
            "now_ms INTEGER NOT NULL,"
            "events TEXT NOT NULL)")
        # No external process can insert actuation into this fixture DB.
        self._check_last()

    def _gate(self):
        try:
            c = self.controller
            report = c.inspect()
            if (report["phase"] != "FIXTURE_NATIVE_SELECTED"
                    or report["fixtureOnly"] is not True
                    or report["nativeOwnsAlarmFile"] is not False
                    or report["installedRestartFence"] is not False
                    or c.ledger.root.name != "clock-native-cutover-fixture"
                    or c.peer is None
                    or not c.final.synthetic
                    or not c.final.source.is_absolute()
                    or not c.final.source.parent.is_absolute()
                    or not c.ledger.conn):
                raise Refused("SYNTHETIC_NATIVE_HANDOFF_REQUIRED")
            if not c.peer.get("pidfd") or not c.peer.get("pid"):
                raise Refused("OLD_WRITER_KERNEL_EXIT_REQUIRED")
            os.fstat(c.peer["pidfd"])
            if not c.__class__.__module__:
                raise Refused("SYNTHETIC_NATIVE_HANDOFF_REQUIRED")
            # We do not use PID-only /proc lookups to claim the writer exited.
            poller = __import__("select").poll()
            poller.register(c.peer["pidfd"], __import__("select").POLLIN |
                            __import__("select").POLLERR |
                            __import__("select").POLLHUP)
            if not poller.poll(0):
                raise Refused("OLD_WRITER_KERNEL_EXIT_REQUIRED")
        except (AttributeError, KeyError, TypeError, OSError) as exc:
            raise Refused("SYNTHETIC_NATIVE_HANDOFF_REQUIRED") from exc
        return True

    def _source_bytes(self):
        self._gate()
        parent_fd = Final._open_parent(
            self.source.parent, uid=self.uid, synthetic=True)
        file_fd = None
        try:
            file_fd = os.open(
                Final.SOURCE_NAME, os.O_RDONLY | os.O_NOFOLLOW |
                os.O_CLOEXEC | getattr(os,"O_NONBLOCK",0),
                dir_fd=parent_fd)
            st = os.fstat(file_fd)
            Final._stat_guard(st, uid=self.uid, directory=False)
            if not 1 <= st.st_size <= MAX_SOURCE:
                raise Refused("BG2_SOURCE_SIZE_REFUSED")
            chunks, count = [], 0
            while True:
                buf = os.read(file_fd, min(65536, MAX_SOURCE+1-count))
                if not buf:
                    break
                chunks.append(buf)
                count += len(buf)
                if count > MAX_SOURCE:
                    raise Refused("BG2_SOURCE_SIZE_REFUSED")
            raw = b"".join(chunks)
            if len(raw) != st.st_size or Final._snapshot(os.fstat(file_fd)) != Final._snapshot(st):
                raise Refused("BG2_SOURCE_CHANGED")
            current = os.stat(Final.SOURCE_NAME,dir_fd=parent_fd,
                              follow_symlinks=False)
            if Final._snapshot(st) != Final._snapshot(current):
                raise Refused("BG2_SOURCE_CHANGED")
            recheck_fd = Final._open_parent(
                self.source.parent, uid=self.uid, synthetic=True)
            try:
                old,new = os.fstat(parent_fd),os.fstat(recheck_fd)
                if (old.st_dev,old.st_ino) != (new.st_dev,new.st_ino):
                    raise Refused("BG2_SOURCE_PARENT_CHANGED")
            finally:
                os.close(recheck_fd)
            try:
                data = json.loads(raw.decode("utf8"),
                                  object_pairs_hook=Final._unique_pairs)
            except (UnicodeError,ValueError,TypeError,RecursionError) as exc:
                raise Refused("BG2_SOURCE_NOT_VALID_V2") from exc
            if not Policy.valid_document(data):
                raise Refused("BG2_SOURCE_NOT_VALID_V2")
            return raw,data
        except OSError as exc:
            raise Refused("BG2_SOURCE_READ_REFUSED") from exc
        finally:
            if file_fd is not None:
                os.close(file_fd)
            os.close(parent_fd)

    def _check_last(self):
        try:
            rows=self.db.execute(
                "SELECT id,phase,before_digest,after_digest,now_ms,events "
                "FROM native_tick_outbox ORDER BY id DESC LIMIT 1").fetchall()
        except sqlite3.Error as exc:
            raise Refused("BG2_OUTBOX_UNAVAILABLE") from exc
        if not rows:
            return None
        seq,phase,before,after,when,events=rows[0]
        if (phase not in ("PREPARED","SAVED","DELIVERING","DELIVERED")
                or type(seq) is not int or seq < 1
                or type(when) is not int or when < 1
                or type(before) is not str or type(after) is not str
                or len(before)!=64 or len(after)!=64
                or any(c not in "0123456789abcdef" for c in before+after)
                or type(events) is not str or len(events)>4096):
            raise Refused("BG2_OUTBOX_CORRUPT")
        try:
            event=json.loads(events)
        except (ValueError,TypeError) as exc:
            raise Refused("BG2_OUTBOX_CORRUPT") from exc
        if (type(event) is not dict or
                set(event)!={"started","missed","expired"} or
                any(type(event[x]) is not list or
                    any(type(y) is not int or y < 1 for y in event[x])
                    for x in event)):
            raise Refused("BG2_OUTBOX_CORRUPT")
        return seq,phase,before,after,when,event

    def _mark(self, seq, expected, state):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            result=self.db.execute(
                "UPDATE native_tick_outbox SET phase=? "
                "WHERE id=? AND phase=?", (state,seq,expected))
            if result.rowcount != 1:
                raise Refused("BG2_OUTBOX_PHASE_CHANGED")
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def _write_atomic(self, before, result):
        dirfd = Final._open_parent(
            self.source.parent, uid=self.uid, synthetic=True)
        tmp = ".bg2-fixture-" + secrets.token_hex(16)
        fd = None
        exists = False
        try:
            # Revalidate before replace, including the approved path.
            raw,_ = self._source_bytes()
            if hashlib.sha256(raw).hexdigest() != before:
                raise Refused("BG2_SOURCE_CHANGED_BEFORE_REPLACE")
            fd = os.open(
                tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|
                os.O_NOFOLLOW,0o600,dir_fd=dirfd)
            exists = True
            view = memoryview(result)
            while view:
                wrote=os.write(fd,view)
                if wrote <= 0:
                    raise Refused("BG2_WRITE_INCOMPLETE")
                view=view[wrote:]
            os.fsync(fd)
            os.close(fd)
            fd=None
            # Fully synced replacement before an event can be dispatched.
            os.rename(tmp,Final.SOURCE_NAME,src_dir_fd=dirfd,
                      dst_dir_fd=dirfd)
            exists=False
            os.fsync(dirfd)
        except OSError as exc:
            raise Refused("BG2_ATOMIC_SOURCE_WRITE_REFUSED") from exc
        finally:
            if fd is not None:
                os.close(fd)
            if exists:
                try:
                    os.unlink(tmp,dir_fd=dirfd)
                except OSError:
                    pass
            os.close(dirfd)

    def step(self, now_ms):
        """Single durable native V2 scheduling transition in a fixture."""
        self._gate()
        last=self._check_last()
        if last is not None and last[1] != "DELIVERED":
            raise Refused("BG2_PENDING_OR_UNCERTAIN_DELIVERY")
        raw,old=self._source_bytes()
        before=hashlib.sha256(raw).hexdigest()
        if before != self.digest:
            raise Refused("BG2_SOURCE_CHANGED_OUTSIDE_OWNER")
        result=Policy.tick(old,now_ms)
        if not result["changed"]:
            return {"phase":"UNCHANGED","started":[],"missed":[],
                    "expired":[],"fixtureOnly":True,"canRing":False,
                    "canNotify":False}
        updated=json.dumps(result["document"],indent=2,
                           ensure_ascii=False).encode("utf8") + b"\n"
        if len(updated)>MAX_SOURCE or not Policy.valid_document(result["document"]):
            raise Refused("BG2_REPLACEMENT_INVALID")
        after=hashlib.sha256(updated).hexdigest()
        events={k:result[k] for k in ("started","missed","expired")}
        serialized=json.dumps(events,sort_keys=True,separators=(",",":"))
        try:
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute(
                "INSERT INTO native_tick_outbox"
                "(phase,before_digest,after_digest,now_ms,events) "
                "VALUES('PREPARED',?,?,?,?)",
                (before,after,now_ms,serialized))
            seq=self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
            self.db.execute("COMMIT")
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise
        self._write_atomic(before,updated)
        replaced,_=self._source_bytes()
        if hashlib.sha256(replaced).hexdigest()!=after:
            raise Refused("BG2_SOURCE_CHANGED_AFTER_REPLACE")
        self._mark(seq,"PREPARED","SAVED")
        self.digest=after
        return {"phase":"SAVED","started":events["started"],
                "missed":events["missed"],"expired":events["expired"],
                "fixtureOnly":True,"canRing":False,"canNotify":False}

    def reconcile(self):
        """Crash recovery refuses ambiguous external writes or delivery."""
        self._gate()
        last=self._check_last()
        if last is None:
            return "EMPTY"
        seq,phase,before,after,_,_=last
        raw,_=self._source_bytes()
        observed=hashlib.sha256(raw).hexdigest()
        if phase=="PREPARED":
            if observed!=after:
                raise Refused("BG2_PREPARED_WRITE_UNCERTAIN")
            self._mark(seq,"PREPARED","SAVED")
            self.digest=after
            return "SAVED"
        if observed!=after:
            raise Refused("BG2_SOURCE_CHANGED_OUTSIDE_OWNER")
        self.digest=after
        if phase=="DELIVERING":
            raise Refused("BG2_DELIVERY_OUTCOME_UNCERTAIN")
        return phase

    def deliver(self, fixture_callback):
        """Fixture event emission after fsync; never real sound/notifications.

        An interrupted callback becomes DELIVERING: no automatic replay.
        """
        self._gate()
        last=self._check_last()
        if last is None or last[1]!="SAVED":
            raise Refused("BG2_NO_SAVED_OCCURRENCE_TO_EMIT")
        if not callable(fixture_callback):
            raise Refused("BG2_FIXTURE_CALLBACK_REQUIRED")
        seq,_,_,after,when,events=last
        raw,_=self._source_bytes()
        if hashlib.sha256(raw).hexdigest()!=after:
            raise Refused("BG2_SOURCE_CHANGED_OUTSIDE_OWNER")
        self._mark(seq,"SAVED","DELIVERING")
        # The callback is only a test sink; the real delivery path must
        # independently provide idempotent provider acknowledgement.
        fixture_callback({"sequence":seq,"atMs":when,
                          "started":events["started"],
                          "missed":events["missed"],
                          "expired":events["expired"]})
        self._mark(seq,"DELIVERING","DELIVERED")
        return {"phase":"DELIVERED","fixtureOnly":True,
                "canRing":False,"canNotify":False}

    def run_fixture_loop(self, *, get_now_ms, should_stop, deliver,
                         interval_seconds=0.01, limit=100):
        """A real background loop only inside the disposable controller."""
        if (not callable(get_now_ms) or not callable(should_stop)
                or not callable(deliver) or type(limit) is not int
                or limit<1 or limit>10000
                or type(interval_seconds) not in (int,float)
                or not 0.001<=interval_seconds<=60):
            raise Refused("BG2_FIXTURE_LOOP_ARGUMENTS_REQUIRED")
        completed=0
        while not should_stop() and completed<limit:
            result=self.step(get_now_ms())
            if result["phase"]=="SAVED":
                self.deliver(deliver)
            completed+=1
            time.sleep(interval_seconds)
        return completed
