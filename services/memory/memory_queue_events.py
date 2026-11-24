"""M1c.3d.1: durable notification candidates, not delivery or authority.

The same unprivileged SQLite transaction checks the request and deduplicates
each event kind. Nothing calls Notification Hub, starts a timer or executes.
"""
from memory_adjustment_queue import QueueError, _int, _uuid
from memory_queue_advisory import BLOCKERS, READY_CODE

DEFERRED = BLOCKERS - {"OBSERVATION_UNAVAILABLE"} | {"OPERATION_BUSY", "STABILITY_INTERVAL"}
ATTENTION = {"OBSERVATION_UNAVAILABLE", "BOOT_CHANGED", "SOURCE_CHANGED",
             "OPERATION_AMBIGUOUS", "STALE_OBSERVATION", "INVALID_OBSERVATION",
             "OBSERVATION_ORDER_INVALID"}
KINDS = {"DEFERRED": DEFERRED, "ATTENTION": ATTENTION,
         "READY_ADVISORY": {READY_CODE},
         "EXPIRED": {"EXPIRED"}, "CANCELLED": {"CANCELLED"}}
TERMINAL = {"EXPIRED", "CANCELLED"}


def _event_id(request_id, kind):
    return "apollo-cpu-memory-" + request_id + "-" + kind.lower().replace("_", "-")


class Events:
    """Opt-in additive table; v1 intent records remain unchanged.

    One candidate per request and kind for this slice. No re-alert after
    readiness regression, no delivery marker, no acknowledgement or pruning.
    """
    def __init__(self, queue):
        self.queue = queue
        with queue._transaction(write=True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memory_queue_events_v1 (
                event_id TEXT PRIMARY KEY NOT NULL,
                request_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                code TEXT NOT NULL,
                observed_at INTEGER NOT NULL,
                UNIQUE(request_id, kind)
            )""")
            self._validate_schema(db)

    @staticmethod
    def _validate_schema(db):
        columns = db.execute("PRAGMA table_info(memory_queue_events_v1)").fetchall()
        expected = [("event_id", "TEXT", 1, 1), ("request_id", "TEXT", 1, 0),
                    ("kind", "TEXT", 1, 0), ("code", "TEXT", 1, 0),
                    ("observed_at", "INTEGER", 1, 0)]
        if [(r[1], r[2], r[3], r[5]) for r in columns] != expected:
            raise QueueError("UNSUPPORTED_EVENT_SCHEMA")
        # Refuse a missing unique index, including after accidental schema drift.
        indices = db.execute("PRAGMA index_list(memory_queue_events_v1)").fetchall()
        unique = [r for r in indices if r[2] == 1 and r[4] == 0]
        has_pair = False
        for row in unique:
            index = row[1].replace('"', '""')
            cols = db.execute('PRAGMA index_info("' + index + '")').fetchall()
            if [c[2] for c in cols] == ["request_id", "kind"]:
                has_pair = True
        if not has_pair:
            raise QueueError("UNSUPPORTED_EVENT_SCHEMA")

    def _get_request(self, db, request_id):
        row = db.execute("SELECT id,state,payload FROM requests WHERE id=?", (request_id,)).fetchone()
        if row is None:
            raise QueueError("EVENT_REQUEST_MISSING")
        return self.queue._decode(row)

    def _decode(self, db, row):
        event_id, request_id, kind, code, observed = row
        _uuid(request_id)
        _int(observed)
        if (type(kind) is not str or kind not in KINDS
                or type(code) is not str or code not in KINDS[kind]
                or event_id != _event_id(request_id, kind)):
            raise QueueError("INVALID_EVENT")
        request = self._get_request(db, request_id)
        if observed < request["requested_at"]:
            raise QueueError("INVALID_EVENT_TIME")
        if kind in TERMINAL:
            if request["state"] != kind or observed != request["changed_at"]:
                raise QueueError("INVALID_TERMINAL_EVENT")
        elif observed >= request["expires_at"] or (
                request["state"] != "QUEUED" and observed > request["changed_at"]):
            raise QueueError("INVALID_EVENT_TIME")
        return {"version": 1, "event_id": event_id, "request_id": request_id,
                "kind": kind, "code": code, "observed_at": observed,
                "target_gib": request["target_gib"],
                "original_actual_kib": request["actual_kib"],
                "delivery_state": "CANDIDATE_ONLY", "can_execute": False}

    def _insert(self, db, request, kind, code, observed_at):
        event_id = _event_id(request["id"], kind)
        row = (event_id, request["id"], kind, code, observed_at)
        self._decode(db, row)
        result = db.execute("""INSERT INTO memory_queue_events_v1 VALUES(?,?,?,?,?)
                            ON CONFLICT(request_id,kind) DO NOTHING""", row)
        saved = db.execute("""SELECT event_id,request_id,kind,code,observed_at
                              FROM memory_queue_events_v1 WHERE request_id=? AND kind=?""",
                           (request["id"], kind)).fetchone()
        return {"created": result.rowcount == 1, "event": self._decode(db, saved)}

    def stage(self, status, *, now, monotonic_ms, max_age_seconds):
        """Persist a monitor candidate only while the exact intent is pending.

        Status is an untrusted advisory projection, not proof of readiness.
        An eventual delivery adapter must revalidate current status, expiry
        and monotonic deadline; a persisted READY is only historical evidence.
        """
        _int(now)
        _int(monotonic_ms)
        _int(max_age_seconds, 1)
        if (type(status) is not dict or type(status.get("version")) is not int
                or status["version"] != 1 or status.get("can_execute") is not False):
            raise QueueError("INVALID_STATUS")
        request_id = _uuid(status.get("request_id"))
        state, code = status.get("state"), status.get("code")
        if type(state) is not str or type(code) is not str:
            raise QueueError("INVALID_STATUS")
        if state == "WAITING" and code in DEFERRED:
            kind = "DEFERRED"
        elif state in ("UNKNOWN", "WAITING") and code in ATTENTION:
            kind = "ATTENTION"
        elif state == "READY_ADVISORY" and code == READY_CODE:
            kind = "READY_ADVISORY"
            deadline = _int(status.get("ready_valid_before_monotonic_ms"))
            if deadline <= monotonic_ms:
                raise QueueError("STALE_STATUS")
        else:
            return None
        checked = _int(status.get("last_checked_at"))
        if not 0 <= now - checked <= max_age_seconds:
            raise QueueError("STALE_STATUS")
        with self.queue._transaction(write=True) as db:
            self._validate_schema(db)
            request = self.queue._expected(db, request_id)
            if now >= request["expires_at"]:
                raise QueueError("EXPIRED_REQUEST")
            if (type(status.get("target_gib")) is not int
                    or status["target_gib"] != request["target_gib"]
                    or type(status.get("actual_kib")) is not int
                    or status["actual_kib"] != request["actual_kib"]
                    or type(status.get("expires_at")) is not int
                    or status["expires_at"] != request["expires_at"]):
                raise QueueError("STATUS_REQUEST_MISMATCH")
            return self._insert(db, request, kind, code, checked)

    def stage_terminal(self, request_id):
        """Only an actually persisted cancellation or expiry qualifies."""
        _uuid(request_id)
        with self.queue._transaction(write=True) as db:
            self._validate_schema(db)
            request = self._get_request(db, request_id)
            kind = request["state"]
            if kind not in TERMINAL:
                return None
            return self._insert(db, request, kind, kind, request["changed_at"])

    def for_request(self, request_id):
        _uuid(request_id)
        with self.queue._transaction() as db:
            self._validate_schema(db)
            self._get_request(db, request_id)
            rows = db.execute("""SELECT event_id,request_id,kind,code,observed_at
                                 FROM memory_queue_events_v1 WHERE request_id=?
                                 ORDER BY observed_at,event_id LIMIT 6""", (request_id,)).fetchall()
            if len(rows) > len(KINDS):
                raise QueueError("DUPLICATE_EVENTS")
            return [self._decode(db, row) for row in rows]
