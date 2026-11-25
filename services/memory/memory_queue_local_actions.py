"""R3d durable local action correlation, not protected operation evidence.

Opt-in journal in the existing private queue DB. PREPARED is committed before
capture; intent mutation and COMMITTED correlation share one transaction.
No replay, deletion, acknowledgment, startup unlock or protected authority.
"""
import json

from memory_adjustment_queue import QueueError, _int, _uuid, _new

MAX_SAFE = 2**53 - 1
FIELDS = {"version", "owner_id", "action_id", "action_sequence", "kind",
          "expected_request_id", "target_gib", "expires_at"}
KINDS = {"QUEUE", "REPLACE", "CANCEL", "EXPIRE"}


def validate(message):
    if (type(message) is not dict or set(message) != FIELDS
            or type(message["version"]) is not int or message["version"] != 1):
        raise QueueError("INVALID_LOCAL_ACTION")
    _uuid(message["owner_id"])
    _uuid(message["action_id"])
    _int(message["action_sequence"], 1, MAX_SAFE - 1)
    kind = message["kind"]
    if type(kind) is not str or kind not in KINDS:
        raise QueueError("INVALID_LOCAL_ACTION")
    if kind == "QUEUE":
        if message["expected_request_id"] is not None:
            raise QueueError("INVALID_EXPECTED_REQUEST")
    else:
        _uuid(message["expected_request_id"])
    if kind in {"QUEUE", "REPLACE"}:
        if _int(message["target_gib"], 4, 64) % 4:
            raise QueueError("INVALID_TARGET")
        _int(message["expires_at"], 1, MAX_SAFE)
    elif message["target_gib"] is not None or message["expires_at"] is not None:
        raise QueueError("INVALID_ACTION_FIELDS")
    return dict(message)


def canonical(message):
    return json.dumps(validate(message), sort_keys=True, separators=(",", ":"))


class LocalActions:
    TABLE = "memory_queue_local_actions_v1"
    COLUMNS = "ordinal,action_id,payload,state,prepared_at,result_id,committed_at"

    def __init__(self, queue):
        self.queue = queue
        self._fresh = None
        with queue._transaction(write=True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memory_queue_local_actions_v1 (
                ordinal INTEGER PRIMARY KEY,
                action_id TEXT NOT NULL UNIQUE,
                payload TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PREPARED','COMMITTED')),
                prepared_at INTEGER NOT NULL,
                result_id TEXT,
                committed_at INTEGER
            )""")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS memory_queue_one_prepared_v1
                          ON memory_queue_local_actions_v1(state) WHERE state='PREPARED'""")
            self._schema(db)

    @classmethod
    def _schema(cls, db):
        columns = db.execute("PRAGMA table_info(memory_queue_local_actions_v1)").fetchall()
        expected = [("ordinal","INTEGER",0,1),("action_id","TEXT",1,0),
                    ("payload","TEXT",1,0),("state","TEXT",1,0),
                    ("prepared_at","INTEGER",1,0),("result_id","TEXT",0,0),
                    ("committed_at","INTEGER",0,0)]
        if [(r[1],r[2],r[3],r[5]) for r in columns] != expected:
            raise QueueError("UNSUPPORTED_ACTION_SCHEMA")
        indices = db.execute("PRAGMA index_list(memory_queue_local_actions_v1)").fetchall()
        unique_id = False
        for row in indices:
            if row[2] == 1 and row[4] == 0:
                name = row[1].replace('"','""')
                unique_id |= [r[2] for r in db.execute(
                    'PRAGMA index_info("' + name + '")')] == ["action_id"]
        idx = db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                         ("memory_queue_one_prepared_v1",)).fetchone()
        if (not unique_id or not idx
                or "".join(idx[0].split()).lower() !=
                "createuniqueindexmemory_queue_one_prepared_v1onmemory_queue_local_actions_v1(state)wherestate='prepared'"):
            raise QueueError("UNSUPPORTED_ACTION_SCHEMA")

    def _request(self, db, request_id):
        row = db.execute("SELECT id,state,payload FROM requests WHERE id=?",
                         (_uuid(request_id),)).fetchone()
        if row is None:
            raise QueueError("ACTION_RESULT_MISSING")
        return self.queue._decode(row)

    def _decode(self, db, row):
        ordinal, action_id, payload, state, prepared, result_id, committed = row
        _int(ordinal, 1, MAX_SAFE)
        _uuid(action_id)
        _int(prepared, 0, MAX_SAFE)
        try:
            if type(payload) is not str or len(payload) > 2048:
                raise QueueError("INVALID_ACTION_ROW")
            message = validate(json.loads(payload))
            if canonical(message) != payload or message["action_id"] != action_id:
                raise QueueError("INVALID_ACTION_ROW")
        except (ValueError, TypeError, RecursionError) as exc:
            raise QueueError("INVALID_ACTION_ROW") from exc
        if state == "PREPARED":
            if result_id is not None or committed is not None:
                raise QueueError("INVALID_ACTION_ROW")
        elif state == "COMMITTED":
            _int(committed, prepared, MAX_SAFE)
            r = self._request(db, result_id)
            kind = message["kind"]
            if kind in {"QUEUE", "REPLACE"}:
                if (r["requested_at"] != committed or r["target_gib"] != message["target_gib"]
                        or r["expires_at"] != message["expires_at"]):
                    raise QueueError("ACTION_RESULT_MISMATCH")
                if kind == "REPLACE":
                    old = self._request(db, message["expected_request_id"])
                    if (old["state"] != "REPLACED" or old["replaced_by"] != result_id
                            or old["changed_at"] != committed):
                        raise QueueError("ACTION_RESULT_MISMATCH")
            elif (result_id != message["expected_request_id"] or r["changed_at"] != committed
                    or r["state"] != ("CANCELLED" if kind == "CANCEL" else "EXPIRED")):
                raise QueueError("ACTION_RESULT_MISMATCH")
        else:
            raise QueueError("INVALID_ACTION_ROW")
        return {"version":1, "ordinal":ordinal, "message":message,
                "state":state, "prepared_at":prepared, "result_request_id":result_id,
                "committed_at":committed, "adjustment_outcome":"UNVERIFIED",
                "can_execute":False}

    def _row(self, db, action_id):
        return db.execute("SELECT " + self.COLUMNS + " FROM " + self.TABLE +
                          " WHERE action_id=?", (_uuid(action_id),)).fetchone()

    def prepare(self, message, *, now):
        m = validate(message)
        _int(now, 0, MAX_SAFE)
        if m["expires_at"] is not None and m["expires_at"] <= now:
            raise QueueError("INVALID_EXPIRY")
        with self.queue._transaction(write=True) as db:
            self._schema(db)
            if self._row(db,m["action_id"]) is not None:
                raise QueueError("ACTION_ALREADY_RECORDED")
            if db.execute("SELECT 1 FROM " + self.TABLE +
                          " WHERE state='PREPARED' LIMIT 1").fetchone():
                raise QueueError("ACTION_RECONCILIATION_REQUIRED")
            if m["kind"] == "QUEUE":
                if self.queue._pending(db) is not None:
                    raise QueueError("PENDING_EXISTS")
            else:
                self.queue._expected(db,m["expected_request_id"])
            db.execute("INSERT INTO " + self.TABLE +
                       "(action_id,payload,state,prepared_at) VALUES(?,?,'PREPARED',?)",
                       (m["action_id"],canonical(m),now))
            result = self._decode(db,self._row(db,m["action_id"]))
        self._fresh = canonical(m)
        return result

    def discard_continuation(self):
        """Forget only process-local continuation; leave durable PREPARED."""
        self._fresh = None

    def commit(self, message, *, now, source=None, admission_clock=None):
        """Explicit continuation, never recovery.

        Staged Runtime supplies a synchronous admission clock: evaluate
        after BEGIN IMMEDIATE and validation, not before SQLite lock wait.
        Legacy direct callers retain their explicit timestamp contract.
        """
        m = validate(message)
        _int(now,0,MAX_SAFE)
        if self._fresh != canonical(m):
            raise QueueError("ACTION_RECONCILIATION_REQUIRED")
        self._fresh = None
        with self.queue._transaction(write=True) as db:
            self._schema(db)
            row = self._row(db,m["action_id"])
            if row is None:
                raise QueueError("ACTION_NOT_PREPARED")
            saved = self._decode(db,row)
            if saved["state"] != "PREPARED" or saved["message"] != m:
                raise QueueError("ACTION_NOT_PREPARED")
            kind = m["kind"]
            old = None
            if kind == "QUEUE":
                if self.queue._pending(db) is not None:
                    raise QueueError("PENDING_EXISTS")
            else:
                old = self.queue._expected(db,m["expected_request_id"])
            if kind not in {"QUEUE","REPLACE"} and source is not None:
                raise QueueError("INVALID_ACTION_FIELDS")
            # Mutation admission is here, with the SQLite writer lock held.
            # A later fsync/commit completion time is not a deadline promise.
            if admission_clock is not None:
                now = _int(admission_clock(), now, MAX_SAFE)
            if now < saved["prepared_at"]:
                raise QueueError("CLOCK_ROLLBACK")
            if kind in {"QUEUE","REPLACE"}:
                record = _new(m["target_gib"],source,now,m["expires_at"])
                if old is not None:
                    self.queue._finish(db,old,"REPLACED",now,record["id"])
                self.queue._insert(db,record)
            else:
                if kind == "EXPIRE" and now < old["expires_at"]:
                    raise QueueError("NOT_EXPIRED")
                record = self.queue._finish(db,old,"CANCELLED" if kind=="CANCEL" else "EXPIRED",now)
            # Same commit as the request row(s). No local evidence gap between
            # durable mutation and result correlation. A crash before commit
            # retains only PREPARED, which must never be replayed on restart.
            count = db.execute("UPDATE " + self.TABLE +
                               " SET state='COMMITTED',result_id=?,committed_at=? "
                               "WHERE action_id=? AND state='PREPARED'",
                               (record["id"],now,m["action_id"])).rowcount
            if count != 1:
                raise QueueError("ACTION_CORRELATION_LOST")
            self._decode(db,self._row(db,m["action_id"]))
            return record

    def lookup(self, action_id):
        with self.queue._transaction() as db:
            self._schema(db)
            row = self._row(db,action_id)
            return self._decode(db,row) if row else None

    def inventory(self, *, limit):
        """Bounded read, not completeness proof or startup authorization."""
        _int(limit,1,16)
        with self.queue._transaction() as db:
            self._schema(db)
            rows = db.execute("SELECT " + self.COLUMNS + " FROM " + self.TABLE +
                              " ORDER BY ordinal DESC LIMIT ?", (limit+1,)).fetchall()
            pending = self.queue._pending(db)
            unresolved = db.execute("SELECT " + self.COLUMNS + " FROM " + self.TABLE +
                                    " WHERE state='PREPARED' LIMIT 2").fetchall()
            if len(unresolved)>1:
                raise QueueError("MULTIPLE_PREPARED_ACTIONS")
            return {"version":1,"recent":[self._decode(db,r) for r in rows[:limit]],
                    "truncated":len(rows)>limit,
                    "prepared":self._decode(db,unresolved[0]) if unresolved else None,
                    "pending_request_id":pending["id"] if pending else None,
                    "startup_unlock":False,"adjustment_outcome":"UNVERIFIED","can_execute":False}
