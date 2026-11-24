"""M1c.3d.2: durable one-attempt fence, not a Hub delivery receipt.

Only a serialized live owner may call attempt with a fresh status reader and
a synchronous offer callback. Never persist, enqueue or replay the packet.
No commands, automatic execution, retries, timers or Hub history writes here.
"""
from memory_adjustment_queue import QueueError, _int
from memory_queue_events import Events, TERMINAL


class Delivery:
    def __init__(self, events):
        self.events = events
        self.queue = events.queue
        with self.queue._transaction(write=True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memory_queue_attempts_v1 (
                event_id TEXT PRIMARY KEY NOT NULL,
                reserved_at INTEGER NOT NULL
            )""")
            self._schema(db)

    @staticmethod
    def _schema(db):
        rows = db.execute("PRAGMA table_info(memory_queue_attempts_v1)").fetchall()
        if [(r[1], r[2], r[3], r[5]) for r in rows] != [
                ("event_id", "TEXT", 1, 1), ("reserved_at", "INTEGER", 1, 0)]:
            raise QueueError("UNSUPPORTED_ATTEMPT_SCHEMA")

    def _event(self, db, event_id):
        self.events._validate_schema(db)
        row = db.execute("""SELECT event_id,request_id,kind,code,observed_at
                            FROM memory_queue_events_v1 WHERE event_id=?""",
                         (event_id,)).fetchone()
        if row is None:
            raise QueueError("EVENT_MISSING")
        event = self.events._decode(db, row)
        return event, self.events._get_request(db, event["request_id"])

    @staticmethod
    def _current(event, request, status, wall_ms, mono_ms, age_ms):
        """Revalidate a historical candidate against current intent and status."""
        _int(wall_ms)
        _int(mono_ms)
        _int(age_ms, 1)
        now = wall_ms // 1000
        if now < event["observed_at"]:
            raise QueueError("CLOCK_ROLLBACK")
        if event["kind"] in TERMINAL:
            if request["state"] != event["kind"]:
                raise QueueError("STALE_EVENT")
            checked = event["observed_at"]
            expiry_ms = checked * 1000 + age_ms
        else:
            if request["state"] != "QUEUED" or now >= request["expires_at"]:
                raise QueueError("STALE_EVENT")
            if (type(status) is not dict or type(status.get("version")) is not int
                    or status["version"] != 1 or status.get("can_execute") is not False
                    or status.get("request_id") != request["id"]
                    or status.get("code") != event["code"]
                    or type(status.get("target_gib")) is not int
                    or status["target_gib"] != request["target_gib"]
                    or type(status.get("actual_kib")) is not int
                    or status["actual_kib"] != request["actual_kib"]
                    or type(status.get("expires_at")) is not int
                    or status["expires_at"] != request["expires_at"]):
                raise QueueError("STALE_EVENT")
            state = status.get("state")
            allowed = {"DEFERRED": ("WAITING",), "ATTENTION": ("WAITING", "UNKNOWN"),
                       "READY_ADVISORY": ("READY_ADVISORY",)}
            if state not in allowed[event["kind"]]:
                raise QueueError("STALE_EVENT")
            checked = _int(status.get("last_checked_at"))
            if checked < event["observed_at"]:
                raise QueueError("STALE_EVENT")
            expiry_ms = min(checked * 1000 + age_ms, request["expires_at"] * 1000)
            if event["kind"] == "READY_ADVISORY":
                remaining = _int(status.get("ready_valid_before_monotonic_ms")) - mono_ms
                if remaining <= 0:
                    raise QueueError("STALE_EVENT")
                expiry_ms = min(expiry_ms, wall_ms + remaining)
        if wall_ms < checked * 1000 or wall_ms >= expiry_ms:
            raise QueueError("STALE_EVENT")
        return expiry_ms

    def attempt(self, event_id, *, read_status, clock, max_age_ms, offer):
        """Reserve durably before making at most one synchronous Hub call.

        clock() -> (Unix milliseconds, monotonic milliseconds), same monotonic
        domain as Monitor. read_status() must read the live serialized owner,
        not a disk cache. A crash after reservation may lose the notification;
        never retry it automatically, even if the Hub history lacks the ID.
        """
        if type(event_id) is not str or len(event_id) > 100:
            raise QueueError("INVALID_EVENT_ID")
        status = read_status()
        wall, mono = clock()
        with self.queue._transaction(write=True) as db:
            self._schema(db)
            event, request = self._event(db, event_id)
            old = db.execute("SELECT reserved_at FROM memory_queue_attempts_v1 WHERE event_id=?",
                             (event_id,)).fetchone()
            if old is not None:
                _int(old[0])
                if old[0] < event["observed_at"] * 1000:
                    raise QueueError("INVALID_ATTEMPT")
                return "ALREADY_RESERVED"
            self._current(event, request, status, wall, mono, max_age_ms)
            db.execute("INSERT INTO memory_queue_attempts_v1 VALUES(?,?)", (event_id, wall))

        # Do not hold SQLite locks across the UI call. Recheck after commit;
        # if conditions changed, keep the reservation consumed. There is still
        # no atomic transaction spanning the queue, monitor and Hub.
        try:
            status = read_status()
            wall2, mono2 = clock()
            if wall2 < wall or mono2 < mono:
                raise QueueError("CLOCK_ROLLBACK")
            with self.queue._transaction() as db:
                event2, request = self._event(db, event_id)
                if event2 != event:
                    raise QueueError("EVENT_CHANGED")
                expires = self._current(event2, request, status, wall2, mono2, max_age_ms)
        except (QueueError, OSError, ValueError, TypeError):
            return "RESERVED_NOT_OFFERED"

        packet = dict(event, delivery_state="ATTEMPT_RESERVED",
                      checked_at_ms=wall2, valid_before_wall_ms=expires)
        try:
            result = offer(packet)
        except Exception:
            return "OFFER_OUTCOME_UNKNOWN"
        # Only an advisory result of the synchronous call, never durable ack.
        return result if type(result) is str and result in {
            "HUB_NOT_READY", "HISTORY_PRESENT", "BLOCKED", "STALE_PACKET",
            "INVALID_PACKET", "HISTORY_OBSERVED", "OFFER_OUTCOME_UNKNOWN"
        } else "OFFER_OUTCOME_UNKNOWN"
