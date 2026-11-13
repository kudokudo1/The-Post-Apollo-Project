#!/usr/bin/env python3
"""SocialW Publisher P1.4: owner-local, DENY-ONLY scheduling ledger.

No network libraries, social tokens, publisher adapters, or executor are used.
A due job becomes NEEDS_REVIEW. It does NOT send or mark a post published.
A separate optional watch process can perform that transition without SocialW.

All mutations are SQLite transactions; the idempotency key suppresses retries.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = 2
MAX_EVENTS = 4000
MAX_JOBS = 500
MAX_ACTIVE = 150
STATES = {"scheduled", "paused", "needs_review", "reviewed", "blocked", "cancelled"}
RECURRENCES = {"once", "daily", "weekly"}
DRAFT_ID = re.compile(r"^d[1-9][0-9]*$")
LOCAL_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
MAX_DRAFT_BYTES = 1500000
UTC = dt.timezone.utc


class Refused(Exception):
    """Safe, structured command refusal, not a partial mutation."""


def require(condition: bool, reason: str):
    if not condition:
        raise Refused(reason)


def strict_json(raw: str) -> dict:
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise Refused("DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj
    try:
        obj = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, TypeError):
        raise Refused("MALFORMED_DRAFT_JSON") from None
    require(isinstance(obj, dict), "INVALID_DRAFT_DOCUMENT")
    return obj


def draft_snapshot(path: Path, draft_id: str) -> dict:
    require(bool(DRAFT_ID.fullmatch(draft_id)), "INVALID_DRAFT_ID")
    try:
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_nlink == 1 and not (info.st_mode & 0o022),
                "UNTRUSTED_DRAFT_FILE")
        require(0 < info.st_size <= MAX_DRAFT_BYTES, "INVALID_DRAFT_FILE_SIZE")
        # Resolve/check the exact user-controlled file, not a remote URL.
        with path.open("rb") as file:
            data = file.read(MAX_DRAFT_BYTES + 1)
        require(len(data) <= MAX_DRAFT_BYTES, "INVALID_DRAFT_FILE_SIZE")
    except OSError:
        raise Refused("DRAFT_FILE_UNAVAILABLE") from None
    doc = strict_json(data.decode("utf-8"))
    require(doc.get("version") == 1 and isinstance(doc.get("drafts"), list),
            "UNSUPPORTED_DRAFT_VERSION")
    matches = [v for v in doc["drafts"]
               if isinstance(v, dict) and v.get("id") == draft_id]
    require(len(matches) == 1, "DRAFT_NOT_FOUND")
    draft = matches[0]
    title, body, revision = (
        draft.get("title"), draft.get("body"), draft.get("updatedAtMs"))
    require(isinstance(title, str) and 0 < len(title) <= 120
            and isinstance(body, str) and len(body) <= 10000
            and type(revision) is int and revision > 0,
            "INVALID_DRAFT_SOURCE")
    # Hash of exact revision and content; no content copied into queue DB.
    payload = json.dumps([draft_id, title, body, revision],
                         separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {"id": draft_id, "title": title, "revision": revision,
            "digest": hashlib.sha256(payload).hexdigest()}


def local_to_ms(local: str, timezone: str) -> int:
    require(isinstance(local, str) and LOCAL_TIME.fullmatch(local) is not None,
            "INVALID_LOCAL_TIME")
    require(isinstance(timezone, str) and 1 <= len(timezone) <= 64
            and re.fullmatch(r"[A-Za-z0-9_+\-/]+", timezone) is not None,
            "INVALID_TIMEZONE")
    try:
        naive = dt.datetime.strptime(local, "%Y-%m-%dT%H:%M")
        require(2020 <= naive.year <= 2100, "UNSUPPORTED_DATE")
        tz = ZoneInfo(timezone)
    except (ValueError, ZoneInfoNotFoundError):
        raise Refused("INVALID_TIMEZONE_OR_DATE") from None

    valid = []
    for fold in (0, 1):
        aware = naive.replace(tzinfo=tz, fold=fold)
        utc = aware.astimezone(UTC)
        if utc.astimezone(tz).replace(tzinfo=None) == naive:
            valid.append(int(utc.timestamp() * 1000))
    valid = sorted(set(valid))
    require(bool(valid), "NONEXISTENT_LOCAL_TIME")
    require(len(valid) == 1, "AMBIGUOUS_LOCAL_TIME")
    return valid[0]


def next_recurrence(local: str, tz: str, recurrence: str,
                    after_ms: int) -> tuple[str, int]:
    require(recurrence in ("daily", "weekly"), "NOT_RECURRING")
    original = dt.datetime.strptime(local, "%Y-%m-%dT%H:%M")
    step = dt.timedelta(days=1 if recurrence == "daily" else 7)
    candidate = original
    for _ in range(4000):
        candidate += step
        text = candidate.strftime("%Y-%m-%dT%H:%M")
        try:
            due = local_to_ms(text, tz)
        except Refused as exc:
            if str(exc) == "NONEXISTENT_LOCAL_TIME":
                continue  # Skip invalid spring-forward occurrence.
            raise  # Ambiguous DST hour needs explicit operator decision.
        if due > after_ms:
            return text, due
    raise Refused("NO_VALID_NEXT_OCCURRENCE")


def safe_file(path: Path):
    if not path.exists() and not path.is_symlink():
        return
    try:
        info = path.lstat()
    except OSError:
        raise Refused("FILE_CHECK_FAILED") from None
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and info.st_nlink == 1 and not (info.st_mode & 0o077),
            "UNTRUSTED_QUEUE_FILE")


def connect(db_path: Path) -> sqlite3.Connection:
    require(db_path.is_absolute() and db_path.suffix == ".sqlite3",
            "INVALID_QUEUE_PATH")
    require(not db_path.parent.is_symlink() and db_path.parent.is_dir(),
            "INVALID_QUEUE_PARENT")
    require(db_path.parent.stat().st_uid == os.getuid(), "UNOWNED_QUEUE_PARENT")
    for suffix in ("", "-wal", "-shm", "-journal"):
        safe_file(Path(str(db_path) + suffix))
    os.umask(0o077)
    try:
        conn = sqlite3.connect(str(db_path), timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        # Every process must recheck schema under ONE database-wide write
        # transaction. A pre-lock version read races other initializers.
        conn.execute("BEGIN IMMEDIATE")
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            require(version in (0, 1, VERSION), "UNSUPPORTED_QUEUE_VERSION")
            if version == 0:
                conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    draft_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    digest TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    local_time TEXT NOT NULL,
                    recurrence TEXT NOT NULL
                      CHECK(recurrence IN ('once','daily','weekly')),
                    due_ms INTEGER NOT NULL,
                    status TEXT NOT NULL
                      CHECK(status IN ('scheduled','paused','needs_review',
                                       'reviewed','blocked','cancelled')),
                    occurrence INTEGER NOT NULL DEFAULT 1,
                    created_ms INTEGER NOT NULL,
                    updated_ms INTEGER NOT NULL,
                    note TEXT NOT NULL DEFAULT ''
                )""")
                conn.execute("CREATE INDEX IF NOT EXISTS due_jobs "
                             "ON jobs(status,due_ms)")
            if version in (0, 1):
                # Existing v1 jobs get a single explicitly UNVERIFIED snapshot,
                # not fabricated prior events. The entire upgrade is atomic.
                conn.execute("""CREATE TABLE IF NOT EXISTS queue_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE RESTRICT,
                    action TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    occurred_ms INTEGER NOT NULL,
                    occurrence INTEGER NOT NULL,
                    detail TEXT NOT NULL
                )""")
                conn.execute("""CREATE INDEX IF NOT EXISTS events_by_job
                    ON queue_events(job_id,id)""")
                for row in conn.execute(
                        "SELECT id,status,updated_ms,occurrence FROM jobs"):
                    conn.execute("""INSERT INTO queue_events
                        (job_id,action,from_state,to_state,occurred_ms,occurrence,detail)
                        VALUES (?,'legacy_snapshot','unknown',?,?,?,
                                'LEGACY_BASELINE_UNVERIFIED')""",
                        (row["id"],row["status"],row["updated_ms"],row["occurrence"]))
                conn.execute("PRAGMA user_version=2")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        safe_file(db_path)
        return conn
    except (sqlite3.Error, OSError):
        raise Refused("QUEUE_STORAGE_UNAVAILABLE") from None


def history_problems(conn: sqlite3.Connection) -> list[dict]:
    """Verify every job's current state/occurrence matches its last event.

    This detects accidental divergence, not malicious same-user SQLite edits.
    """
    try:
        rows = conn.execute("""SELECT j.id,j.status,j.occurrence,
            (SELECT e.to_state FROM queue_events e
             WHERE e.job_id=j.id ORDER BY e.id DESC LIMIT 1) AS event_status,
            (SELECT e.occurrence FROM queue_events e
             WHERE e.job_id=j.id ORDER BY e.id DESC LIMIT 1) AS event_occurrence
            FROM jobs j ORDER BY j.id LIMIT 501""").fetchall()
        problems = [
            {"jobId":r["id"],"reason":"EVENT_STATE_MISMATCH"}
            for r in rows if r["status"] != r["event_status"]
            or r["occurrence"] != r["event_occurrence"]
        ]
        # An existing last-event state is not enough to prove the earlier
        # local transition trail is internally continuous.
        previous = {}
        for event in conn.execute("""SELECT id,job_id,action,from_state,
            to_state,occurrence FROM queue_events ORDER BY id LIMIT 4001"""):
            ident = event["job_id"]
            old = previous.get(ident)
            if old is None:
                valid_first = (event["action"] == "schedule"
                    and event["from_state"] == "none"
                    and event["to_state"] == "scheduled"
                    and event["occurrence"] == 1) or (
                    event["action"] == "legacy_snapshot"
                    and event["from_state"] == "unknown"
                    and event["to_state"] in STATES
                    and event["occurrence"] >= 1)
                if not valid_first:
                    problems.append({"jobId":ident,"reason":"EVENT_ORIGIN_INVALID"})
            else:
                status, occurrence = old
                ok = event["from_state"] == status and event["to_state"] in STATES
                ok = ok and (
                    (event["action"] == "rearm" and event["occurrence"] == occurrence + 1)
                    or (event["action"] != "rearm" and event["occurrence"] == occurrence))
                if not ok:
                    problems.append({"jobId":ident,"reason":"EVENT_CHAIN_DIVERGENCE"})
            previous[ident] = (event["to_state"], event["occurrence"])
        orphans = conn.execute("""SELECT COUNT(*) FROM queue_events e
            LEFT JOIN jobs j ON j.id=e.job_id WHERE j.id IS NULL""").fetchone()[0]
        if orphans:
            problems.append({"jobId":0,"reason":"ORPHAN_EVENTS"})
        return problems
    except sqlite3.Error:
        return [{"jobId":0,"reason":"EVENT_LEDGER_UNAVAILABLE"}]


def append_event(conn: sqlite3.Connection, job_id: int,
                 action: str, before: str, after: str,
                 occurred_ms: int, occurrence: int, detail: str):
    n=conn.execute("SELECT count(*) FROM queue_events").fetchone()[0]
    require(n < MAX_EVENTS,"HISTORY_CAPACITY_REACHED")
    conn.execute("""INSERT INTO queue_events
        (job_id,action,from_state,to_state,occurred_ms,occurrence,detail)
        VALUES (?,?,?,?,?,?,?)""",
        (job_id,action,before,after,occurred_ms,occurrence,detail))


def history(conn: sqlite3.Connection, job_id: int = 0) -> dict:
    require(job_id >= 0, "INVALID_JOB_ID")
    rows=conn.execute("""SELECT id,job_id,action,from_state,to_state,
        occurred_ms,occurrence,detail FROM queue_events
        WHERE (?=0 OR job_id=?) ORDER BY id DESC LIMIT 200""",
        (job_id,job_id)).fetchall()
    return {"ok":True,"events":[{**dict(r),"providerReceipt":None}
                                for r in rows],
            "source":"LOCAL_QUEUE_ONLY","posted":0,"canPublish":False}


def audit(conn: sqlite3.Connection, drafts: Path) -> dict:
    check=conn.execute("PRAGMA integrity_check").fetchone()[0]
    require(check == "ok", "QUEUE_INTEGRITY_FAILED")
    problems=history_problems(conn)
    source_problems=[]
    for row in conn.execute("""SELECT id,draft_id,revision,digest FROM jobs
        WHERE status IN ('scheduled','paused','needs_review')
        ORDER BY id LIMIT 500"""):
        try:
            snap=draft_snapshot(drafts,row["draft_id"])
            matches=snap["digest"]==row["digest"] and snap["revision"]==row["revision"]
        except (Refused, UnicodeError):
            matches=False
        if not matches:
            source_problems.append({"jobId":row["id"],"reason":"SOURCE_CHANGED_OR_MISSING"})
    return {"ok":True,"ledgerConsistent":not problems,
            "ledgerProblems":problems,"sourceProblems":source_problems,
            "repairPerformed":False,"posted":0,"canPublish":False}


def reconcile(conn: sqlite3.Connection, drafts: Path, now_ms: int) -> dict:
    """Explicit fail-closed repair: block stale local jobs; never dispatch."""
    def operation():
        problems=history_problems(conn)
        require(not problems,"HISTORY_DIVERGENCE")
        blocked=0
        for row in conn.execute("""SELECT id,status,draft_id,revision,digest,
            occurrence FROM jobs WHERE status IN ('scheduled','paused')
            ORDER BY id LIMIT 500""").fetchall():
            try:
                snap=draft_snapshot(drafts,row["draft_id"])
                matches=snap["digest"]==row["digest"] and snap["revision"]==row["revision"]
            except (Refused,UnicodeError):
                matches=False
            if not matches:
                conn.execute("""UPDATE jobs SET status='blocked',updated_ms=?,
                    note='SOURCE_CHANGED_OR_UNAVAILABLE' WHERE id=?""",
                    (now_ms,row["id"]))
                append_event(conn,row["id"],"reconcile",row["status"],"blocked",
                             now_ms,row["occurrence"],"SOURCE_CHANGED_OR_UNAVAILABLE")
                blocked+=1
        return {"ok":True,"blocked":blocked,"posted":0,"canPublish":False}
    return transaction(conn,operation)


def transaction(conn: sqlite3.Connection, change):
    conn.execute("BEGIN IMMEDIATE")
    try:
        require(not history_problems(conn), "HISTORY_DIVERGENCE")
        result = change()
        conn.execute("COMMIT")
        return result
    except Exception:
        conn.execute("ROLLBACK")
        raise


def schedule(conn: sqlite3.Connection, drafts: Path, draft_id: str,
             local: str, tz: str, recurrence: str, now_ms: int) -> dict:
    require(recurrence in RECURRENCES, "INVALID_RECURRENCE")
    due = local_to_ms(local, tz)
    snapshot = draft_snapshot(drafts, draft_id)
    key_content = json.dumps([draft_id, snapshot["digest"], local, tz,
                              recurrence], separators=(",", ":"))
    key = hashlib.sha256(key_content.encode()).hexdigest()

    def operation():
        prior = conn.execute("SELECT id,status FROM jobs WHERE key=?", (key,)).fetchone()
        if prior:
            return {"ok": True, "id": prior["id"], "status": prior["status"],
                    "idempotent": True}
        require(due > now_ms, "SCHEDULE_MUST_BE_FUTURE")
        n = conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"]
        a = conn.execute("""SELECT count(*) AS n FROM jobs WHERE
                status IN ('scheduled','paused','needs_review','blocked')""").fetchone()["n"]
        require(n < MAX_JOBS and a < MAX_ACTIVE, "QUEUE_CAPACITY_REACHED")
        cur = conn.execute("""INSERT INTO jobs
            (key,draft_id,title,revision,digest,timezone,local_time,
             recurrence,due_ms,status,created_ms,updated_ms)
            VALUES (?,?,?,?,?,?,?,?,?,'scheduled',?,?)""",
            (key,draft_id,snapshot["title"],snapshot["revision"],
             snapshot["digest"],tz,local,recurrence,due,now_ms,now_ms))
        append_event(conn,cur.lastrowid,"schedule","none","scheduled",
                     now_ms,1,"LOCAL_SCHEDULE_ONLY")
        return {"ok":True,"id":cur.lastrowid,"status":"scheduled",
                "idempotent":False}
    return transaction(conn, operation)


def job_list(conn: sqlite3.Connection, drafts: Path, now_ms: int) -> dict:
    rows = conn.execute("""SELECT id,draft_id,title,revision,timezone,local_time,
        recurrence,due_ms,status,occurrence,note FROM jobs
        ORDER BY CASE WHEN status='scheduled' THEN 0 ELSE 1 END, due_ms,id
        LIMIT 500""").fetchall()
    return {"ok": True, "jobs": [
        {**dict(row), "due": row["status"] == "scheduled"
         and row["due_ms"] <= now_ms} for row in rows
    ],"executor":"DISABLED","canPublish":False}


def tick(conn: sqlite3.Connection, drafts: Path, now_ms: int) -> dict:
    def operation():
        rows = conn.execute("""SELECT id,draft_id,revision,digest,occurrence FROM jobs
            WHERE status='scheduled' AND due_ms<=? ORDER BY due_ms,id
            LIMIT 150""", (now_ms,)).fetchall()
        needs_review = blocked = 0
        for row in rows:
            try:
                snap = draft_snapshot(drafts, row["draft_id"])
                valid = snap["revision"] == row["revision"] and snap["digest"] == row["digest"]
            except Refused:
                valid = False
            if valid:
                conn.execute("""UPDATE jobs SET status='needs_review',
                    updated_ms=?,note='DUE_NO_DISPATCH' WHERE id=?""",
                    (now_ms,row["id"]))
                append_event(conn,row["id"],"due","scheduled","needs_review",
                             now_ms,row["occurrence"],"DUE_NO_DISPATCH")
                needs_review += 1
            else:
                conn.execute("""UPDATE jobs SET status='blocked',
                    updated_ms=?,note='SOURCE_CHANGED_OR_UNAVAILABLE' WHERE id=?""",
                    (now_ms,row["id"]))
                append_event(conn,row["id"],"source_block","scheduled","blocked",
                             now_ms,row["occurrence"],"SOURCE_CHANGED_OR_UNAVAILABLE")
                blocked += 1
        return {"ok":True,"reviewRequired":needs_review,"blocked":blocked,
                "posted":0,"executor":"DISABLED"}
    return transaction(conn, operation)


def modify(conn: sqlite3.Connection, drafts: Path,
           op: str, job_id: int, now_ms: int) -> dict:
    require(job_id > 0 and job_id <= 1000000000, "INVALID_JOB_ID")
    def operation():
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        require(row is not None, "UNKNOWN_JOB")
        before = row["status"]
        target = None
        changes = {}
        if op == "cancel":
            require(before not in ("cancelled", "reviewed"), "CANNOT_CANCEL")
            target = "cancelled"
        elif op == "pause":
            require(before == "scheduled", "CANNOT_PAUSE")
            target = "paused"
        elif op == "resume":
            require(before == "paused", "CANNOT_RESUME")
            target = "scheduled"
        elif op == "acknowledge":
            require(before == "needs_review", "NOT_READY_FOR_REVIEW")
            target = "reviewed"  # Explicitly NOT published or delivered.
        elif op == "rearm":
            require(before == "reviewed" and row["recurrence"] != "once",
                    "CANNOT_REARM")
            snap = draft_snapshot(drafts, row["draft_id"])
            require(snap["digest"] == row["digest"] and snap["revision"] == row["revision"],
                    "SOURCE_CHANGED_REQUIRES_NEW_JOB")
            next_local, due_ms = next_recurrence(row["local_time"], row["timezone"],
                                                 row["recurrence"], now_ms)
            target = "scheduled"
            changes = {"local_time":next_local,"due_ms":due_ms,
                       "occurrence":row["occurrence"] + 1}
        else:
            raise Refused("INVALID_ACTION")
        conn.execute("""UPDATE jobs SET status=?,updated_ms=?,note=?,
            local_time=?,due_ms=?,occurrence=? WHERE id=?""",
            (target,now_ms, "REARMED_AFTER_REVIEW" if op=="rearm" else op.upper(),
             changes.get("local_time",row["local_time"]),
             changes.get("due_ms",row["due_ms"]),
             changes.get("occurrence",row["occurrence"]),job_id))
        append_event(conn,job_id,op,before,target,now_ms,
                     changes.get("occurrence",row["occurrence"]),
                     "REARMED_AFTER_REVIEW" if op=="rearm" else op.upper())
        return {"ok":True,"id":job_id,"status":target,"previous":before,
                "posted":0}
    return transaction(conn, operation)


def now_ms() -> int:
    return int(time.time() * 1000)


def execute(args, current_ms: int | None = None) -> dict:
    if current_ms is None:
        current_ms = now_ms()
    with closing(connect(Path(args.db))) as conn:
        if args.action == "status":
            return job_list(conn, Path(args.drafts), current_ms)
        if args.action == "history":
            return history(conn,args.id)
        if args.action == "audit":
            return audit(conn,Path(args.drafts))
        if args.action == "reconcile":
            return reconcile(conn,Path(args.drafts),current_ms)
        if args.action == "tick":
            return tick(conn, Path(args.drafts), current_ms)
        if args.action == "schedule":
            return schedule(conn, Path(args.drafts), args.draft, args.local_time,
                            args.timezone, args.recurrence, current_ms)
        if args.action in ("cancel","pause","resume","acknowledge","rearm"):
            return modify(conn, Path(args.drafts), args.action, args.id, current_ms)
        raise Refused("INVALID_ACTION")


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="P1.4 deny-only publisher queue")
    parser.add_argument("action", choices=[
        "schedule","status","tick","cancel","pause","resume",
        "acknowledge","rearm","watch","history","audit","reconcile"])
    parser.add_argument("--db", required=True)
    parser.add_argument("--drafts", required=True)
    parser.add_argument("--draft", default="")
    parser.add_argument("--local-time", default="")
    parser.add_argument("--timezone", default="")
    parser.add_argument("--recurrence", default="once")
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--interval-seconds", type=int, default=30)
    try:
        args = parser.parse_args(argv)
        if args.action == "watch":
            require(5 <= args.interval_seconds <= 3600, "INVALID_INTERVAL")
            # Explicitly launched standalone. Never touches any social provider.
            while True:
                execute(argparse.Namespace(**{**vars(args),"action":"tick"}))
                time.sleep(args.interval_seconds)
        result = execute(args)
    except Refused as exc:
        result = {"ok":False,"reason":str(exc)}
    except (sqlite3.Error, OSError, OverflowError):
        result = {"ok":False,"reason":"QUEUE_UNAVAILABLE"}
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
