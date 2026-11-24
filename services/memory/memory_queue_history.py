"""M1c.3f.1: local history and unbound withdrawal evidence.

No operation invocation, authority, receipt authentication, or completion
transition. The existing root helper's v1 receipt lacks a queue request ID.
A structurally matching receipt remains UNBOUND_EVIDENCE, even after reopening.
"""
import hashlib
import json

from memory_adjustment_queue import QueueError, _int, _uuid
from memory_queue_events import Events

RECEIPT_FIELDS = {"version", "state", "targetGiB", "sizeKiB", "basePriority",
                  "extensionActive", "fileRetained", "timeNs"}


def candidate(request, receipt, observed_at):
    _int(observed_at)
    if type(receipt) is not dict or set(receipt) != RECEIPT_FIELDS:
        raise QueueError("INVALID_RECEIPT")
    if (type(receipt["version"]) is not int or receipt["version"] != 1
            or receipt["state"] != "VERIFIED"
            or type(receipt["basePriority"]) is not int or receipt["basePriority"] != 10
            or receipt["extensionActive"] is not False
            or receipt["fileRetained"] is not True):
        raise QueueError("INVALID_RECEIPT")
    target = _int(receipt["targetGiB"], 4, 64)
    size = _int(receipt["sizeKiB"], 1)
    when = _int(receipt["timeNs"], 1)
    base, extra = request["source"]["base"], request["source"]["extension"]
    if (target % 4 or target != request["target_gib"] or not base or not extra
            or size != base["size_kib"] or not 0 <= target * 1048576 - size <= 1024
            or when // 1000000000 < request["requested_at"]
            or when // 1000000000 > observed_at
            or when // 1000000000 >= request["expires_at"]):
        raise QueueError("RECEIPT_REQUEST_MISMATCH")
    raw = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return raw, hashlib.sha256(raw.encode("ascii")).hexdigest()


class History:
    """Explicit evidence capture and bounded per-request history projection.

    Does not mutate queue intent. Does not initialize event/attempt tables.
    One candidate per request; exact duplicate is idempotent, conflicting
    evidence is refused. Same-UID database is not a trusted receipt issuer.
    """
    def __init__(self, queue):
        self.queue = queue
        with queue._transaction(write=True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memory_queue_receipt_candidates_v1 (
                request_id TEXT PRIMARY KEY NOT NULL,
                digest TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL,
                observed_at INTEGER NOT NULL
            )""")
            self._schema(db)

    @staticmethod
    def _schema(db):
        rows = db.execute("PRAGMA table_info(memory_queue_receipt_candidates_v1)").fetchall()
        if [(r[1], r[2], r[3], r[5]) for r in rows] != [
                ("request_id", "TEXT", 1, 1), ("digest", "TEXT", 1, 0),
                ("payload", "TEXT", 1, 0), ("observed_at", "INTEGER", 1, 0)]:
            raise QueueError("UNSUPPORTED_RECEIPT_SCHEMA")

    def _request(self, db, request_id):
        row = db.execute("SELECT id,state,payload FROM requests WHERE id=?",
                         (request_id,)).fetchone()
        if row is None:
            raise QueueError("REQUEST_MISSING")
        return self.queue._decode(row)

    @staticmethod
    def _decode(request, row):
        digest, raw, observed = row
        try:
            if type(raw) is not str or len(raw) > 4096:
                raise QueueError("INVALID_RECEIPT")
            receipt = json.loads(raw)
            canonical, expected = candidate(request, receipt, observed)
            if raw != canonical or digest != expected:
                raise QueueError("RECEIPT_DIGEST_MISMATCH")
        except (ValueError, TypeError, RecursionError) as exc:
            raise QueueError("INVALID_RECEIPT") from exc
        return {"state": "UNBOUND_EVIDENCE", "digest": digest,
                "observed_at": observed, "receipt": receipt,
                "kernel_verified_for_request": False, "can_execute": False}

    def record_candidate(self, request_id, receipt, *, observed_at):
        _uuid(request_id)
        with self.queue._transaction(write=True) as db:
            self._schema(db)
            request = self._request(db, request_id)
            raw, digest = candidate(request, receipt, observed_at)
            old = db.execute("""SELECT digest,payload,observed_at
                              FROM memory_queue_receipt_candidates_v1 WHERE request_id=?""",
                             (request_id,)).fetchone()
            if old:
                saved = self._decode(request, old)
                if saved["digest"] != digest:
                    raise QueueError("CONFLICTING_RECEIPT")
                return saved
            if db.execute("SELECT 1 FROM memory_queue_receipt_candidates_v1 WHERE digest=?",
                          (digest,)).fetchone():
                raise QueueError("RECEIPT_ALREADY_ASSOCIATED")
            db.execute("INSERT INTO memory_queue_receipt_candidates_v1 VALUES(?,?,?,?)",
                       (request_id, digest, raw, observed_at))
            return self._decode(request, (digest, raw, observed_at))

    @staticmethod
    def _exists(db, table):
        return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                          (table,)).fetchone() is not None

    def detail(self, request_id):
        _uuid(request_id)
        with self.queue._transaction() as db:
            self._schema(db)
            request = self._request(db, request_id)
            row = db.execute("""SELECT digest,payload,observed_at
                              FROM memory_queue_receipt_candidates_v1 WHERE request_id=?""",
                             (request_id,)).fetchone()
            receipt = self._decode(request, row) if row else None
            events = []
            if self._exists(db, "memory_queue_events_v1"):
                Events._validate_schema(db)
                # Decode existing event rows without constructing/writing Events.
                decoder = Events.__new__(Events)
                decoder.queue = self.queue
                rows = db.execute("""SELECT event_id,request_id,kind,code,observed_at
                                  FROM memory_queue_events_v1 WHERE request_id=?
                                  ORDER BY observed_at,event_id LIMIT 6""", (request_id,)).fetchall()
                if len(rows) > 5:
                    raise QueueError("DUPLICATE_EVENTS")
                attempts_exist = self._exists(db, "memory_queue_attempts_v1")
                if attempts_exist:
                    from memory_queue_delivery import Delivery
                    Delivery._schema(db)
                for row in rows:
                    event = decoder._decode(db, row)
                    attempt = db.execute("""SELECT reserved_at FROM memory_queue_attempts_v1
                                           WHERE event_id=?""", (event["event_id"],)).fetchone() if attempts_exist else None
                    if attempt:
                        if _int(attempt[0]) < event["observed_at"] * 1000:
                            raise QueueError("INVALID_ATTEMPT")
                    events.append(dict(event, attempt_reserved_at_ms=attempt[0] if attempt else None,
                                       delivery_outcome="UNKNOWN" if attempt else "NOT_RECORDED"))
            return {"version": 1, "request": request, "notification_events": events,
                    "withdrawal_evidence": receipt, "adjustment_outcome": "UNVERIFIED",
                    "can_execute": False}
