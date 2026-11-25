"""R3i local recovery review evidence, not abandonment or permission.

A review binds an exact old action row and current pending request to a
new live owner. Acknowledgment appends evidence without altering the
journal, request, startup gate or protected operation state.
"""
import hashlib
import json
import uuid

from memory_adjustment_queue import QueueError, _int, _uuid
from memory_queue_local_actions import LocalActions, MAX_SAFE

TABLE = "memory_queue_recovery_reviews_v1"
DDL = """CREATE TABLE memory_queue_recovery_reviews_v1 (
    review_id TEXT PRIMARY KEY NOT NULL,
    action_id TEXT NOT NULL,
    reviewer_owner_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    acknowledged_at INTEGER NOT NULL
)"""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode("ascii")).hexdigest()


def _snapshot(db, journal, action_id, owner_id):
    journal._schema(db)
    raw = journal._row(db, action_id)
    if raw is None:
        raise QueueError("ACTION_RECORD_UNAVAILABLE")
    row = journal._decode(db, raw)
    if journal._is_dismissed(db, action_id):
        raise QueueError("ACTION_ALREADY_DISMISSED")
    if row["message"]["owner_id"] == owner_id:
        raise QueueError("RECOVERY_REQUIRES_NEW_OWNER")
    pending = journal.queue._pending(db)
    return {"version":1,"record":row,
            "pending_request_id":pending["id"] if pending else None,
            "pending_digest":_digest(pending),
            "adjustment_outcome":"UNVERIFIED","can_execute":False,
            "startup_unlock":False}


def _schema(db, *, create=False):
    row = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                     (TABLE,)).fetchone()
    if row is None:
        if not create:
            return False
        db.execute(DDL)
        row = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                         (TABLE,)).fetchone()
    if not row or "".join(row[0].split()).lower() != "".join(DDL.split()).lower():
        raise QueueError("UNSUPPORTED_RECOVERY_REVIEW_SCHEMA")
    return True


class RecoveryReview:
    def __init__(self, journal, owner_id):
        self.journal = journal
        self.owner_id = _uuid(owner_id)
        self._live = None

    def begin(self, action_id, *, wall_ms, mono_ms, max_age_ms):
        _uuid(action_id)
        _int(wall_ms,0,MAX_SAFE)
        _int(mono_ms,0,MAX_SAFE)
        _int(max_age_ms,1,60000)
        # Replace prior selection; old review ticket is no longer usable.
        self._live = None
        with self.journal.queue._transaction() as db:
            _schema(db)
            snapshot = _snapshot(db,self.journal,action_id,self.owner_id)
        review = {"version":1,"review_id":str(uuid.uuid4()),"owner_id":self.owner_id,
                  "action_id":action_id,"snapshot":snapshot,
                  "review_digest":_digest(snapshot),"reviewed_at_ms":wall_ms,
                  "can_execute":False,"startup_unlock":False}
        self._live = (_json(review),wall_ms,mono_ms,max_age_ms)
        return review

    def invalidate(self):
        self._live = None

    def acknowledge(self, *, review_id, review_digest, clock):
        return self._finish(review_id=review_id,review_digest=review_digest,clock=clock,dismiss=False)

    def dismiss(self, *, review_id, review_digest, clock):
        """Explicit separate local disposition; never imply protected consent."""
        return self._finish(review_id=review_id,review_digest=review_digest,clock=clock,dismiss=True)

    def _finish(self, *, review_id, review_digest, clock, dismiss):
        live,self._live=self._live,None
        if live is None:
            raise QueueError("RECOVERY_REVIEW_NOT_LIVE")
        serialized,start_wall,start_mono,max_age=live
        review=json.loads(serialized)
        _uuid(review_id)
        if review_id!=review["review_id"] or review_digest!=review["review_digest"]:
            raise QueueError("RECOVERY_REVIEW_MISMATCH")

        def admit():
            wall_ms,mono_ms=clock()
            _int(wall_ms,0,MAX_SAFE)
            _int(mono_ms,0,MAX_SAFE)
            if not (0<=wall_ms-start_wall<max_age and 0<=mono_ms-start_mono<max_age):
                raise QueueError("RECOVERY_REVIEW_EXPIRED")
            return wall_ms

        admit()
        with self.journal.queue._transaction(write=True) as db:
            current=_snapshot(db,self.journal,review["action_id"],self.owner_id)
            if _digest(current)!=review_digest or current!=review["snapshot"]:
                raise QueueError("RECOVERY_EVIDENCE_CHANGED")
            # Check after lock acquisition and evidence validation. If
            # schema creation takes time, recheck before inserting as well;
            # expiration rolls back the entire transaction (including DDL).
            admit()
            if dismiss:
                if not hasattr(self.journal,"dismiss_in_transaction"):
                    raise QueueError("LOCAL_DISPOSITION_MODE_REQUIRED")
                return self.journal.dismiss_in_transaction(db,review,admit)
            _schema(db,create=True)
            wall_ms=admit()
            receipt={"version":1,"review":review,"acknowledged_at_ms":wall_ms,
                     "disposition":"REVIEW_ACKNOWLEDGED_ONLY",
                     "adjustment_outcome":"UNVERIFIED","can_execute":False,
                     "startup_unlock":False}
            db.execute("INSERT INTO "+TABLE+
                       "(review_id,action_id,reviewer_owner_id,payload,acknowledged_at) VALUES(?,?,?,?,?)",
                       (review_id,review["action_id"],self.owner_id,_json(receipt),wall_ms))
            return receipt

    def lookup(self, review_id):
        _uuid(review_id)
        with self.journal.queue._transaction() as db:
            if not _schema(db):
                return None
            row=db.execute("SELECT action_id,reviewer_owner_id,payload,acknowledged_at FROM "+TABLE+
                           " WHERE review_id=?",(review_id,)).fetchone()
            if row is None:
                return None
            try:
                receipt=json.loads(row[2])
                review=receipt["review"]
                if (set(receipt)!={"version","review","acknowledged_at_ms","disposition",
                                  "adjustment_outcome","can_execute","startup_unlock"}
                        or set(review)!={"version","review_id","owner_id","action_id","snapshot",
                                       "review_digest","reviewed_at_ms","can_execute","startup_unlock"}
                        or type(receipt["version"]) is not int or receipt["version"]!=1
                        or type(review["version"]) is not int or review["version"]!=1
                        or review["review_id"]!=review_id or review["action_id"]!=_uuid(row[0])
                        or review["owner_id"]!=_uuid(row[1])
                        or receipt["acknowledged_at_ms"]!=_int(row[3],0,MAX_SAFE)
                        or not 0<=receipt["acknowledged_at_ms"]-_int(review["reviewed_at_ms"],0,MAX_SAFE)<60000
                        or receipt["disposition"]!="REVIEW_ACKNOWLEDGED_ONLY"
                        or receipt["adjustment_outcome"]!="UNVERIFIED"
                        or receipt["can_execute"] is not False or receipt["startup_unlock"] is not False
                        or review["can_execute"] is not False or review["startup_unlock"] is not False
                        or _digest(review["snapshot"])!=review["review_digest"]
                        or _json(receipt)!=row[2]):
                    raise QueueError("INVALID_RECOVERY_REVIEW")
                # Historical record, not proof the current queue is unchanged.
                # Never treat stored acknowledgment as authority.
                return receipt
            except (ValueError,TypeError,KeyError,AttributeError,RecursionError) as exc:
                raise QueueError("INVALID_RECOVERY_REVIEW") from exc
