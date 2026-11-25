"""R3d durable local correlation, disposable private DB only."""
import copy
import contextlib
import sqlite3
import threading
import time
from unittest import mock
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_local_actions import LocalActions
from memory_queue_runtime import Runtime
from memory_queue_owner import Owner

SOURCE={"boot_id":"c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
        "base":{"device":42,"inode":9007199254740993,"size_kib":16777212},
        "extension":{"device":42,"inode":9007199254740995,"size_kib":8388604}}


class Tests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"queue.db"
        self.q=Queue(self.path)
        self.wall,self.mono=100000,10000
        self.owner=str(uuid.uuid4())
        self.seq=0
        self.captures=0
        self.runtime=self.make_runtime()

    def capture(self):
        self.captures+=1
        return {"version":1,"source":copy.deepcopy(SOURCE),
                "wall_ms":self.wall,"monotonic_ms":self.mono}

    def make_runtime(self):
        return Runtime(self.q,self.capture,lambda *_:None,interval_ms=1000,
                       max_age_ms=3000,max_gap_ms=2000,stable_ms=3000,
                       clock=lambda:(self.wall,self.mono))

    def message(self,kind="QUEUE",expected=None):
        self.seq+=1
        return {"version":1,"owner_id":self.owner,"action_id":str(uuid.uuid4()),
                "action_sequence":self.seq,"kind":kind,"expected_request_id":expected,
                "target_gib":16 if kind in {"QUEUE","REPLACE"} else None,
                "expires_at":200 if kind in {"QUEUE","REPLACE"} else None}

    def reopen(self):
        self.q=Queue(self.path)
        return LocalActions(self.q)

    def test_lost_queue_reply_exact_result_after_restart(self):
        m=self.message()
        result=self.runtime.local_action(m)["request"]
        j=self.reopen()
        saved=j.lookup(m["action_id"])
        self.assertEqual(saved["state"],"COMMITTED")
        self.assertEqual(saved["result_request_id"],result["id"])
        self.assertEqual(j.inventory(limit=16)["pending_request_id"],result["id"])
        self.assertFalse(saved["can_execute"])
        self.assertNotIn("inode",str(saved))
        self.runtime=self.make_runtime()
        with self.assertRaisesRegex(QueueError,"ACTION_ALREADY_RECORDED"):
            self.runtime.local_action(m)
        self.assertEqual(self.captures,1)

    def test_prepared_restart_cannot_commit_or_resubmit(self):
        m=self.message()
        LocalActions(self.q).prepare(m,now=100)
        j=self.reopen()
        self.assertEqual(j.inventory(limit=1)["prepared"]["message"],m)
        self.assertIsNone(self.q.pending())
        with self.assertRaisesRegex(QueueError,"ACTION_RECONCILIATION_REQUIRED"):
            j.commit(m,now=100,source=SOURCE)
        self.runtime=self.make_runtime()
        with self.assertRaisesRegex(QueueError,"ACTION_ALREADY_RECORDED"):
            self.runtime.local_action(m)
        with self.assertRaisesRegex(QueueError,"ACTION_RECONCILIATION_REQUIRED"):
            self.runtime.local_action(self.message())
        self.assertEqual(self.captures,0)

    def test_capture_failure_retains_prepared(self):
        m=self.message()
        self.runtime.capture_source=lambda:None
        with self.assertRaises(QueueError):
            self.runtime.local_action(m)
        self.assertEqual(self.reopen().lookup(m["action_id"])["state"],"PREPARED")
        self.assertIsNone(self.q.pending())

    def test_atomic_rollback_if_correlation_update_fails(self):
        m=self.message()
        j=LocalActions(self.q)
        j.prepare(m,now=100)
        with self.q._transaction(write=True) as db:
            db.execute("""CREATE TRIGGER fixture_fail BEFORE UPDATE ON
                memory_queue_local_actions_v1 BEGIN SELECT RAISE(ABORT,'fixture'); END""")
        with self.assertRaises(QueueError):
            j.commit(m,now=100,source=SOURCE)
        self.assertIsNone(self.q.pending())
        self.assertEqual(j.lookup(m["action_id"])["state"],"PREPARED")
        with self.assertRaisesRegex(QueueError,"ACTION_RECONCILIATION_REQUIRED"):
            j.commit(m,now=100,source=SOURCE)

    def test_replace_and_cancel_preserve_links(self):
        a=self.message()
        old=self.runtime.local_action(a)["request"]
        b=self.message("REPLACE",old["id"])
        new=self.runtime.local_action(b)["request"]
        c=self.message("CANCEL",new["id"])
        self.runtime.local_action(c)
        j=self.reopen()
        self.assertIsNone(self.q.pending())
        self.assertEqual(j.lookup(a["action_id"])["result_request_id"],old["id"])
        self.assertEqual(j.lookup(b["action_id"])["result_request_id"],new["id"])
        self.assertEqual(j.lookup(c["action_id"])["result_request_id"],new["id"])
        page=j.inventory(limit=2)
        self.assertTrue(page["truncated"])
        self.assertEqual(len(page["recent"]),2)
        self.assertFalse(page["startup_unlock"])

    def test_expire_exact_request(self):
        old=self.runtime.local_action(self.message())["request"]
        self.wall,self.mono=200000,110000
        m=self.message("EXPIRE",old["id"])
        result=self.runtime.local_action(m)["request"]
        self.assertEqual(result["state"],"EXPIRED")
        self.assertEqual(self.reopen().lookup(m["action_id"])["result_request_id"],old["id"])

    def test_changed_message_refuses(self):
        m=self.message()
        j=LocalActions(self.q)
        j.prepare(m,now=100)
        with self.assertRaises(QueueError):
            j.commit(dict(m,expires_at=201),now=100,source=SOURCE)
        self.assertIsNone(self.q.pending())

    def test_corrupt_result_refuses_inventory(self):
        m=self.message()
        self.runtime.local_action(m)
        j=LocalActions(self.q)
        with self.q._transaction(write=True) as db:
            db.execute("UPDATE memory_queue_local_actions_v1 SET result_id=?",(str(uuid.uuid4()),))
        with self.assertRaisesRegex(QueueError,"ACTION_RESULT_MISSING"):
            j.inventory(limit=16)

    def test_explicit_inventory_no_observer_or_capture(self):
        j=LocalActions(self.q)
        for _ in range(50):
            self.assertFalse(j.inventory(limit=16)["startup_unlock"])
        self.assertEqual(self.captures,0)
        with self.assertRaises(QueueError):
            j.inventory(limit=17)

    def make_owner(self, *, durable=True):
        owner=Owner(self.q,lambda q:self.make_runtime(),durable_actions=durable)
        self.addCleanup(owner.close)
        self.owner=owner.owner_id
        self.seq=0
        return owner

    def test_owner_dispatch_correlated_no_legacy_fallback(self):
        owner=self.make_owner()
        def fail(**_):
            self.fail("legacy enqueue invoked in durable mode")
        owner.runtime.enqueue=fail
        m=self.message()
        reply=owner.action(m)
        self.assertEqual(reply["disposition"],"REPORTED")
        rid=reply["result"]["request"]["id"]
        packet=owner.inventory(limit=16)
        self.assertEqual(packet["kind"],"INVENTORY")
        self.assertEqual(packet["owner_id"],owner.owner_id)
        self.assertGreater(packet["sequence"],reply["sequence"])
        self.assertEqual(packet["inventory"]["pending_request_id"],rid)
        self.assertFalse(packet["inventory"]["startup_unlock"])
        self.assertNotIn("inode",str(packet))
        saved=owner.lookup_action(m["action_id"])
        self.assertEqual(saved["record"]["result_request_id"],rid)
        self.assertEqual(saved["record"]["message"],m)
        self.assertEqual(self.captures,1)
        with self.assertRaisesRegex(QueueError,"STALE_ACTION_SEQUENCE"):
            owner.action(m)
        self.assertIsNone(owner.lookup_action(str(uuid.uuid4()))["record"])

    def test_owner_restart_recovery_no_legacy_downgrade(self):
        owner=self.make_owner()
        m=self.message()
        reply=owner.action(m)
        rid=reply["result"]["request"]["id"]
        owner.close()
        self.q=Queue(self.path)
        with self.assertRaisesRegex(QueueError,"DURABLE_ACTION_MODE_REQUIRED"):
            Owner(self.q,lambda q:self.make_runtime())
        next_owner=self.make_owner()
        self.assertNotEqual(next_owner.owner_id,m["owner_id"])
        self.assertEqual(next_owner.lookup_action(m["action_id"])["record"]["result_request_id"],rid)
        with self.assertRaisesRegex(QueueError,"STALE_OR_INVALID_OWNER"):
            next_owner.action(m)
        self.assertEqual(self.captures,1)
        self.assertEqual(next_owner.action(self.message("CANCEL",rid))["result"]["request"]["state"],"CANCELLED")
        self.assertIsNone(self.q.pending())

    def test_owner_capture_failure_blocks_mutation_after_restart(self):
        owner=self.make_owner()
        owner.runtime.capture_source=lambda:None
        m=self.message()
        self.assertEqual(owner.action(m)["disposition"],"UNKNOWN")
        owner.close()
        self.q=Queue(self.path)
        next_owner=self.make_owner()
        packet=next_owner.inventory(limit=1)
        self.assertEqual(packet["inventory"]["prepared"]["message"],m)
        self.assertEqual(next_owner.action(self.message())["disposition"],"UNKNOWN")
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.captures,0)

    def test_legacy_owner_detects_journal_created_after_open(self):
        owner=self.make_owner(durable=False)
        LocalActions(self.q)
        with self.assertRaisesRegex(QueueError,"DURABLE_ACTION_MODE_REQUIRED"):
            owner.action(self.message())
        self.assertEqual(self.captures,0)
        self.assertIsNone(self.q.pending())

    def test_owner_legacy_inventory_refused(self):
        owner=self.make_owner(durable=False)
        with self.assertRaisesRegex(QueueError,"DURABLE_ACTION_MODE_REQUIRED"):
            owner.inventory(limit=1)
        with self.assertRaisesRegex(QueueError,"DURABLE_ACTION_MODE_REQUIRED"):
            owner.lookup_action(str(uuid.uuid4()))

    def staged_owner(self, *, max_age=1000):
        owner=Owner(self.q,lambda q:self.make_runtime(),durable_actions=True,
                    staged_max_age_ms=max_age)
        self.addCleanup(owner.close)
        self.owner=owner.owner_id
        self.seq=0
        return owner

    def test_staged_prepare_durable_before_any_mutation(self):
        owner=self.staged_owner()
        m=self.message()
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_REQUIRED"):
            owner.action(m)
        self.assertEqual(self.captures,0)
        receipt=owner.prepare_action(m)
        self.assertEqual(receipt["kind"],"PREPARED_ACTION")
        self.assertEqual(receipt["record"]["message"],m)
        self.assertEqual(receipt["record"]["state"],"PREPARED")
        self.assertEqual(receipt["next_action_sequence"],2)
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.captures,0)
        self.assertFalse(receipt["can_execute"])
        self.assertEqual(owner.lookup_action(m["action_id"])["record"],receipt["record"])
        reply=owner.commit_action(m)
        self.assertEqual(reply["disposition"],"REPORTED")
        self.assertEqual(reply["next_action_sequence"],2)
        self.assertEqual(self.captures,1)
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"COMMITTED")
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_NOT_LIVE"):
            owner.commit_action(m)
        self.assertEqual(self.captures,1)

    def test_staged_lost_prepare_reply_restart_no_continuation(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        owner.close()
        self.q=Queue(self.path)
        next_owner=self.staged_owner()
        self.assertEqual(next_owner.inventory(limit=16)["inventory"]["prepared"]["message"],m)
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_NOT_LIVE"):
            next_owner.commit_action(m)
        with self.assertRaisesRegex(QueueError,"ACTION_RECONCILIATION_REQUIRED"):
            next_owner.prepare_action(self.message())
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.captures,0)

    def test_staged_mismatch_consumes_live_continuation(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_MISMATCH"):
            owner.commit_action(dict(m,expires_at=201))
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_NOT_LIVE"):
            owner.commit_action(m)
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.captures,0)

    def test_staged_expiry_before_capture(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        self.wall+=1000
        self.mono+=1000
        self.assertEqual(owner.commit_action(m)["disposition"],"UNKNOWN")
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.captures,0)

    def test_staged_expiry_during_capture(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        def slow():
            self.wall+=1000
            self.mono+=1000
            return self.capture()
        owner.runtime.capture_source=slow
        self.assertEqual(owner.commit_action(m)["disposition"],"UNKNOWN")
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.captures,1)

    def test_staged_replace_cancel_and_expire(self):
        owner=self.staged_owner()
        def act(kind,expected=None):
            m=self.message(kind,expected)
            self.assertEqual(owner.prepare_action(m)["record"]["state"],"PREPARED")
            r=owner.commit_action(m)
            self.assertEqual(r["disposition"],"REPORTED")
            return r["result"]["request"]
        old=act("QUEUE")
        new=act("REPLACE",old["id"])
        self.assertEqual(act("CANCEL",new["id"])["state"],"CANCELLED")
        third=act("QUEUE")
        self.wall,self.mono=200000,110000
        self.assertEqual(act("EXPIRE",third["id"])["state"],"EXPIRED")
        self.assertIsNone(self.q.pending())

    def test_staged_requires_explicit_durable_mode(self):
        with self.assertRaisesRegex(QueueError,"DURABLE_ACTION_MODE_REQUIRED"):
            Owner(self.q,lambda q:self.make_runtime(),staged_max_age_ms=1000)
        owner=self.make_owner()
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_MODE_REQUIRED"):
            owner.prepare_action(self.message())


    def interrupted_prepared(self):
        old=self.staged_owner()
        m=self.message()
        old.prepare_action(m)
        old.close()
        self.q=Queue(self.path)
        return self.staged_owner(),m

    def test_recovery_ack_preserves_prepared_and_lock(self):
        owner,m=self.interrupted_prepared()
        review=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        self.assertEqual(review["snapshot"]["record"]["state"],"PREPARED")
        self.assertFalse(review["startup_unlock"])
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.captures,0)
        r=owner.acknowledge_recovery_review(review_id=review["review_id"],
                    review_digest=review["review_digest"])["receipt"]
        self.assertEqual(r["disposition"],"REVIEW_ACKNOWLEDGED_ONLY")
        self.assertFalse(r["startup_unlock"])
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_NOT_LIVE"):
            owner.acknowledge_recovery_review(review_id=review["review_id"],
                    review_digest=review["review_digest"])
        owner.close()
        self.q=Queue(self.path)
        reopened=self.staged_owner()
        self.assertEqual(reopened.recovery_review_history(review["review_id"])["receipt"],r)
        with self.assertRaisesRegex(QueueError,"ACTION_RECONCILIATION_REQUIRED"):
            reopened.prepare_action(self.message())
        self.assertEqual(self.captures,0)

    def test_recovery_review_missing_and_same_owner_refuse(self):
        owner=self.staged_owner()
        with self.assertRaisesRegex(QueueError,"ACTION_RECORD_UNAVAILABLE"):
            owner.begin_recovery_review(str(uuid.uuid4()),max_age_ms=1000)
        m=self.message()
        owner.prepare_action(m)
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_PENDING"):
            owner.begin_recovery_review(m["action_id"],max_age_ms=1000)
        owner.commit_action(m)
        with self.assertRaisesRegex(QueueError,"RECOVERY_REQUIRES_NEW_OWNER"):
            owner.begin_recovery_review(m["action_id"],max_age_ms=1000)

    def test_recovery_ack_expired_and_replaced_ticket(self):
        owner,m=self.interrupted_prepared()
        first=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        second=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_MISMATCH"):
            owner.acknowledge_recovery_review(review_id=first["review_id"],
                    review_digest=first["review_digest"])
        self.assertIsNone(owner.recovery_review_history(first["review_id"])["receipt"])
        third=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        self.wall+=1000
        self.mono+=1000
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_EXPIRED"):
            owner.acknowledge_recovery_review(review_id=third["review_id"],
                    review_digest=third["review_digest"])
        self.assertIsNone(owner.recovery_review_history(second["review_id"])["receipt"])

    def test_recovery_ack_new_owner_cannot_use_old_ticket(self):
        owner,m=self.interrupted_prepared()
        review=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        owner.close()
        self.q=Queue(self.path)
        new=self.staged_owner()
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_NOT_LIVE"):
            new.acknowledge_recovery_review(review_id=review["review_id"],
                    review_digest=review["review_digest"])
        self.assertIsNone(new.recovery_review_history(review["review_id"])["receipt"])

    def test_recovery_ack_detects_changed_pending_record(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        owner.commit_action(m)
        owner.close()
        self.q=Queue(self.path)
        new=self.staged_owner()
        review=new.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        # Simulate a competing direct writer, not an approved path.
        self.q.cancel(self.q.pending()["id"],now=101)
        with self.assertRaisesRegex(QueueError,"RECOVERY_EVIDENCE_CHANGED"):
            new.acknowledge_recovery_review(review_id=review["review_id"],
                    review_digest=review["review_digest"])
        self.assertIsNone(new.recovery_review_history(review["review_id"])["receipt"])

    def test_recovery_review_committed_local_only(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        result=owner.commit_action(m)["result"]["request"]
        owner.close()
        self.q=Queue(self.path)
        new=self.staged_owner()
        review=new.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        self.assertEqual(review["snapshot"]["record"]["result_request_id"],result["id"])
        receipt=new.acknowledge_recovery_review(review_id=review["review_id"],
                    review_digest=review["review_digest"])["receipt"]
        self.assertEqual(receipt["adjustment_outcome"],"UNVERIFIED")
        self.assertFalse(receipt["can_execute"])
        self.assertNotIn("inode",str(receipt))
        self.assertEqual(self.q.pending()["id"],result["id"])

    @contextlib.contextmanager
    def contended_write(self, *, wall_delta, mono_delta):
        """A real separate SQLite writer holds BEGIN IMMEDIATE until the
        tested connection attempts its own BEGIN IMMEDIATE. Advance only
        the injected clocks during that wait, not via a pre-lock fixture.
        The original code would wrongly accept the old timestamp.
        """
        real_connect=sqlite3.connect
        held,attempted,released,abort=(threading.Event() for _ in range(4))
        errors=[]

        def hold():
            try:
                with contextlib.closing(real_connect(self.path,timeout=1,
                                                     isolation_level=None)) as db:
                    db.execute("BEGIN IMMEDIATE")
                    held.set()
                    if not attempted.wait(3) or abort.is_set():
                        return
                    # The tested connection is entering SQLite while our
                    # writer lock is held. Keep it briefly to exercise wait.
                    time.sleep(0.05)
                    self.wall+=wall_delta
                    self.mono+=mono_delta
                    db.rollback()
                    released.set()
            except BaseException as exc:
                errors.append(exc)
                held.set()

        class Contended(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                if sql=="BEGIN IMMEDIATE" and not attempted.is_set():
                    attempted.set()
                    cursor=super().execute(sql,*args,**kwargs)
                    if not released.wait(1):
                        raise AssertionError("contention fixture did not release")
                    return cursor
                return super().execute(sql,*args,**kwargs)

        def connect(*args,**kwargs):
            return real_connect(*args,factory=Contended,**kwargs)

        worker=threading.Thread(target=hold,daemon=True)
        worker.start()
        try:
            self.assertTrue(held.wait(3))
            self.assertFalse(errors)
            with mock.patch("memory_adjustment_queue.sqlite3.connect",side_effect=connect):
                yield
            self.assertTrue(attempted.is_set())
            self.assertTrue(released.is_set())
        finally:
            abort.set()
            attempted.set()
            worker.join(4)
            self.assertFalse(worker.is_alive())
            self.assertFalse(errors)

    def test_staged_write_lock_wait_expires_wall(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        with self.contended_write(wall_delta=1000,mono_delta=0):
            reply=owner.commit_action(m)
        self.assertEqual(reply["disposition"],"UNKNOWN")
        self.assertIsNone(self.q.pending())
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")
        with self.assertRaisesRegex(QueueError,"STAGED_ACTION_NOT_LIVE"):
            owner.commit_action(m)
        self.assertEqual(self.captures,1)

    def test_staged_write_lock_wait_expires_monotonic(self):
        owner=self.staged_owner()
        m=self.message()
        owner.prepare_action(m)
        with self.contended_write(wall_delta=0,mono_delta=1000):
            reply=owner.commit_action(m)
        self.assertEqual(reply["disposition"],"UNKNOWN")
        self.assertIsNone(self.q.pending())
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")

    def test_staged_write_lock_wait_stales_source(self):
        owner=self.staged_owner(max_age=10000)
        m=self.message()
        owner.prepare_action(m)
        with self.contended_write(wall_delta=3001,mono_delta=3001):
            reply=owner.commit_action(m)
        self.assertEqual(reply["disposition"],"UNKNOWN")
        self.assertIsNone(self.q.pending())
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")
        self.assertEqual(self.captures,1)

    def test_staged_write_lock_wait_expires_request(self):
        self.wall=199999
        owner=self.staged_owner(max_age=10000)
        m=self.message()
        owner.prepare_action(m)
        with self.contended_write(wall_delta=1,mono_delta=1):
            reply=owner.commit_action(m)
        self.assertEqual(reply["disposition"],"UNKNOWN")
        self.assertIsNone(self.q.pending())
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")

    def test_staged_write_lock_admission_timestamp(self):
        owner=self.staged_owner(max_age=3000)
        m=self.message()
        owner.prepare_action(m)
        with self.contended_write(wall_delta=1000,mono_delta=1000):
            reply=owner.commit_action(m)
        self.assertEqual(reply["disposition"],"REPORTED")
        self.assertEqual(self.q.pending()["requested_at"],101)
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["committed_at"],101)

    def test_recovery_ack_write_lock_wait_expires_wall(self):
        owner,m=self.interrupted_prepared()
        review=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        with self.contended_write(wall_delta=1000,mono_delta=0):
            with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_EXPIRED"):
                owner.acknowledge_recovery_review(review_id=review["review_id"],
                            review_digest=review["review_digest"])
        self.assertIsNone(owner.recovery_review_history(review["review_id"])["receipt"])
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")
        self.assertIsNone(self.q.pending())
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_NOT_LIVE"):
            owner.acknowledge_recovery_review(review_id=review["review_id"],
                        review_digest=review["review_digest"])

    def test_recovery_ack_write_lock_wait_expires_monotonic(self):
        owner,m=self.interrupted_prepared()
        review=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        with self.contended_write(wall_delta=0,mono_delta=1000):
            with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_EXPIRED"):
                owner.acknowledge_recovery_review(review_id=review["review_id"],
                            review_digest=review["review_digest"])
        self.assertIsNone(owner.recovery_review_history(review["review_id"])["receipt"])
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")

    def test_recovery_ack_write_lock_admission_timestamp(self):
        owner,m=self.interrupted_prepared()
        review=owner.begin_recovery_review(m["action_id"],max_age_ms=1000)["review"]
        with self.contended_write(wall_delta=200,mono_delta=200):
            receipt=owner.acknowledge_recovery_review(review_id=review["review_id"],
                            review_digest=review["review_digest"])["receipt"]
        self.assertEqual(receipt["acknowledged_at_ms"],100200)
        self.assertEqual(owner.recovery_review_history(review["review_id"])["receipt"],receipt)
        self.assertEqual(owner.lookup_action(m["action_id"])["record"]["state"],"PREPARED")

if __name__=="__main__":
    unittest.main(verbosity=2)
