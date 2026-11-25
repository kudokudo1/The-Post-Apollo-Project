"""R3d durable local correlation, disposable private DB only."""
import copy
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


if __name__=="__main__":
    unittest.main(verbosity=2)
