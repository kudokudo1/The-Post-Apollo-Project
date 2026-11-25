"""R5: operator-approved local-only recovery disposition, opt-in v2 journal.

The original seven columns and all prior records are retained. One extra
column contains immutable dismissal evidence. V1 readers reject the schema
rather than silently ignoring the new disposition; no v1 wire mode.
"""
import json
from memory_adjustment_queue import QueueError, _int, _uuid
from memory_queue_local_actions import LocalActions, MAX_SAFE

INDEX = ("CREATE UNIQUE INDEX memory_queue_one_prepared_v2 "
         "ON memory_queue_local_actions_v1(state) WHERE state='PREPARED' AND dismissal IS NULL")
EXPECTED = [("ordinal","INTEGER",0,1),("action_id","TEXT",1,0),
            ("payload","TEXT",1,0),("state","TEXT",1,0),
            ("prepared_at","INTEGER",1,0),("result_id","TEXT",0,0),
            ("committed_at","INTEGER",0,0),("dismissal","TEXT",0,0)]


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)


class LocalActionsV2(LocalActions):
    def __init__(self,queue,*,migrate=False):
        self.queue=queue
        self._fresh=None
        if type(migrate) is not bool:
            raise QueueError("INVALID_LOCAL_DISPOSITION_MODE")
        if migrate:
            # Explicit caller holds the existing exclusive Owner flock.
            with queue._transaction() as db:
                columns=db.execute("PRAGMA table_info(memory_queue_local_actions_v1)").fetchall()
            if not columns:
                LocalActions(queue)
            with queue._transaction(write=True) as db:
                names=[row[1] for row in db.execute("PRAGMA table_info(memory_queue_local_actions_v1)")]
                if names==[item[0] for item in EXPECTED[:-1]]:
                    LocalActions._schema(db)
                    # Validate original rows before schema promotion.
                    for raw in db.execute("SELECT "+self.COLUMNS+" FROM "+self.TABLE):
                        self._decode(db,raw)
                    db.execute("ALTER TABLE memory_queue_local_actions_v1 ADD COLUMN dismissal TEXT")
                    db.execute("DROP INDEX memory_queue_one_prepared_v1")
                    db.execute(INDEX)
                self._schema(db)
        else:
            with queue._transaction() as db:
                self._schema(db)

    def _schema(self,db):
        columns=db.execute("PRAGMA table_info(memory_queue_local_actions_v1)").fetchall()
        if [(r[1],r[2],r[3],r[5]) for r in columns]!=EXPECTED:
            raise QueueError("UNSUPPORTED_ACTION_DISPOSITION_SCHEMA")
        indices=db.execute("PRAGMA index_list(memory_queue_local_actions_v1)").fetchall()
        unique_id=False
        for row in indices:
            if row[2]==1 and row[4]==0:
                name=row[1].replace('"','""')
                unique_id |= [r[2] for r in db.execute('PRAGMA index_info("'+name+'")')]==["action_id"]
        idx=db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='memory_queue_one_prepared_v2'").fetchone()
        if (not unique_id or not idx or "".join(idx[0].split()).lower()!="".join(INDEX.split()).lower()
                or any(row[1]=="memory_queue_one_prepared_v1" for row in indices)):
            raise QueueError("UNSUPPORTED_ACTION_DISPOSITION_SCHEMA")
        # Retained dismissals are part of admission evidence. Corruption
        # cannot silently turn a PREPARED row into a released fence.
        for raw in db.execute("SELECT "+self.COLUMNS+",dismissal FROM "+self.TABLE+" WHERE dismissal IS NOT NULL"):
            self._decode_disposition(db,raw)

    def _blocking_clause(self):
        return "state='PREPARED' AND dismissal IS NULL"

    def _is_dismissed(self,db,action_id):
        row=db.execute("SELECT dismissal FROM "+self.TABLE+" WHERE action_id=?",(_uuid(action_id),)).fetchone()
        return row is not None and row[0] is not None

    def _decode_disposition(self,db,raw):
        from memory_queue_pipe import _review_wire
        from memory_queue_recovery_review import _digest
        record=self._decode(db,raw[:-1])
        payload=raw[-1]
        try:
            if type(payload) is not str or len(payload)>8192:
                raise QueueError("INVALID_LOCAL_DISPOSITION")
            value=json.loads(payload)
            if (type(value) is not dict or set(value)!={"version","review","dismissed_at_ms","disposition",
                    "adjustment_outcome","can_execute","startup_unlock"}
                    or type(value["version"]) is not int or value["version"]!=2
                    or value["disposition"]!="LOCAL_PREPARATION_DISMISSED"
                    or value["adjustment_outcome"]!="UNVERIFIED"
                    or value["can_execute"] is not False or value["startup_unlock"] is not False
                    or record["state"]!="PREPARED" or canonical(value)!=payload):
                raise QueueError("INVALID_LOCAL_DISPOSITION")
            review=_review_wire(value["review"])
            if (review["snapshot"]["record"]!=record
                    or _digest(review["snapshot"])!=review["review_digest"]
                    or not 0<=_int(value["dismissed_at_ms"],0,MAX_SAFE)-review["reviewed_at_ms"]<60000):
                raise QueueError("INVALID_LOCAL_DISPOSITION")
            return value
        except (TypeError,ValueError,KeyError,AttributeError,RecursionError) as exc:
            raise QueueError("INVALID_LOCAL_DISPOSITION") from exc

    def dismiss_in_transaction(self,db,review,wall_ms):
        """Only RecoveryReview's explicit live dismissal path may call this.

        Caller already holds the owner and SQLite writer lock, revalidated
        exact current snapshot and checked both admission clocks.
        """
        self._schema(db)
        action_id=review["action_id"]
        row=self._row(db,action_id)
        if row is None or self._is_dismissed(db,action_id):
            raise QueueError("ACTION_RECORD_UNAVAILABLE")
        record=self._decode(db,row)
        if record["state"]!="PREPARED" or record!=review["snapshot"]["record"]:
            raise QueueError("LOCAL_DISPOSITION_REQUIRES_PREPARED")
        receipt={"version":2,"review":review,"dismissed_at_ms":wall_ms,
                 "disposition":"LOCAL_PREPARATION_DISMISSED","adjustment_outcome":"UNVERIFIED",
                 "can_execute":False,"startup_unlock":False}
        payload=canonical(receipt)
        # Validate the complete retained evidence before updating. No
        # original row fields or request rows are modified.
        self._decode_disposition(db,tuple(row)+(payload,))
        count=db.execute("UPDATE "+self.TABLE+" SET dismissal=? WHERE action_id=? AND state='PREPARED' AND dismissal IS NULL",
                         (payload,action_id)).rowcount
        if count!=1:
            raise QueueError("LOCAL_DISPOSITION_CONFLICT")
        return receipt

    def disposition(self,action_id):
        with self.queue._transaction() as db:
            self._schema(db)
            row=db.execute("SELECT "+self.COLUMNS+",dismissal FROM "+self.TABLE+" WHERE action_id=?",(_uuid(action_id),)).fetchone()
            return self._decode_disposition(db,row) if row and row[-1] is not None else None

    def inventory(self,*,limit):
        _int(limit,1,16)
        with self.queue._transaction() as db:
            self._schema(db)
            rows=db.execute("SELECT "+self.COLUMNS+",dismissal FROM "+self.TABLE+
                            " ORDER BY ordinal DESC LIMIT ?",(limit+1,)).fetchall()
            prepared=db.execute("SELECT "+self.COLUMNS+" FROM "+self.TABLE+" WHERE "+self._blocking_clause()+" LIMIT 2").fetchall()
            if len(prepared)>1:
                raise QueueError("MULTIPLE_PREPARED_ACTIONS")
            pending=self.queue._pending(db)
            return {"version":2,"recent":[{"record":self._decode(db,row[:-1]),
                        "disposition":self._decode_disposition(db,row) if row[-1] is not None else None}
                        for row in rows[:limit]],"truncated":len(rows)>limit,
                    "prepared":self._decode(db,prepared[0]) if prepared else None,
                    "pending_request_id":pending["id"] if pending else None,
                    "startup_unlock":False,"adjustment_outcome":"UNVERIFIED","can_execute":False}
