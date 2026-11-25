"""R5 local disposition; only disposable DB and synthetic observation."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services/memory"))
from memory_adjustment_queue import Queue,QueueError
from memory_queue_local_actions import LocalActions
from memory_queue_local_disposition import LocalActionsV2
from memory_queue_runtime import Runtime
from memory_queue_owner import Owner
from memory_queue_pipe import Session, encode

SOURCE={"boot_id":"c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
        "base":{"device":42,"inode":100,"size_kib":16777212},
        "extension":{"device":42,"inode":101,"size_kib":8388604}}


class Tests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"queue.db"
        self.q=Queue(self.path)
        self.wall,self.mono=100000,10000
        self.captures=0
        self.owner=self.open(False)
        self.old=self.message()
        self.original=self.owner.prepare_action(self.old)["record"]
        self.owner.close()
        self.owner=self.open(True)

    def open(self,v2):
        def capture():
            self.captures+=1
            return {"version":1,"source":copy.deepcopy(SOURCE),"wall_ms":self.wall,"monotonic_ms":self.mono}
        owner=Owner(self.q,lambda q:Runtime(q,capture,lambda *_:None,
            interval_ms=1000,max_age_ms=3000,max_gap_ms=2000,stable_ms=3000,
            clock=lambda:(self.wall,self.mono),local_disposition_enabled=v2),
            durable_actions=True,staged_max_age_ms=10000,local_disposition_enabled=v2)
        self.addCleanup(owner.close)
        return owner

    def message(self,action_id=None):
        return {"version":1,"owner_id":self.owner.owner_id,"action_id":action_id or str(uuid.uuid4()),
                "action_sequence":1,"kind":"QUEUE","expected_request_id":None,"target_gib":16,"expires_at":200}

    def review(self):
        return self.owner.begin_recovery_review(self.old["action_id"],max_age_ms=1000)["review"]

    def dismiss(self,review):
        return self.owner.dismiss_recovery_preparation(review_id=review["review_id"],
                review_digest=review["review_digest"])["receipt"]

    def test_ack_is_not_dismissal_and_explicit_release_retains_original(self):
        review=self.review()
        ack=self.owner.acknowledge_recovery_review(review_id=review["review_id"],review_digest=review["review_digest"])
        self.assertEqual(ack["receipt"]["disposition"],"REVIEW_ACKNOWLEDGED_ONLY")
        self.assertIsNotNone(self.owner.inventory(limit=16)["inventory"]["prepared"])
        receipt=self.dismiss(self.review())
        self.assertEqual(receipt["disposition"],"LOCAL_PREPARATION_DISMISSED")
        self.assertFalse(receipt["startup_unlock"])
        self.assertFalse(receipt["can_execute"])
        self.assertEqual(self.captures,0)
        self.assertIsNone(self.q.pending())
        self.assertEqual(self.owner.lookup_action(self.old["action_id"])["record"],self.original)
        self.owner.close()
        self.owner=self.open(True)
        self.assertEqual(self.owner.disposition_history(self.old["action_id"])["receipt"],receipt)
        inventory=self.owner.inventory(limit=16)["inventory"]
        self.assertEqual(inventory["version"],2)
        self.assertIsNone(inventory["prepared"])
        self.assertEqual(inventory["recent"][0],{"record":self.original,"disposition":receipt})
        with self.assertRaisesRegex(QueueError,"ACTION_ALREADY_DISMISSED"):
            self.review()
        # Old UUID remains forbidden even with a fresh owner/sequence.
        with self.assertRaisesRegex(QueueError,"ACTION_ALREADY_RECORDED"):
            self.owner.prepare_action(self.message(self.old["action_id"]))
        fresh=self.message()
        fresh["action_sequence"]=2
        self.owner.prepare_action(fresh)
        result=self.owner.commit_action(fresh)
        self.assertEqual(result["disposition"],"REPORTED")
        self.assertEqual(self.captures,1)
        self.assertEqual(self.owner.disposition_history(self.old["action_id"])["receipt"],receipt)
        self.assertEqual(self.owner.lookup_action(self.old["action_id"])["record"],self.original)

    def test_wrong_digest_consumes_live_ticket(self):
        review=self.review()
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_MISMATCH"):
            self.dismiss(dict(review,review_digest="0"*64))
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_NOT_LIVE"):
            self.dismiss(review)
        self.assertIsNotNone(self.owner.inventory(limit=1)["inventory"]["prepared"])

    def test_expired_review_preserves_preparation(self):
        review=self.review()
        self.wall+=1000
        self.mono+=1000
        with self.assertRaisesRegex(QueueError,"RECOVERY_REVIEW_EXPIRED"):
            self.dismiss(review)
        self.assertIsNone(self.owner.disposition_history(self.old["action_id"])["receipt"])
        self.assertEqual(self.owner.lookup_action(self.old["action_id"])["record"],self.original)

    def test_old_reader_and_v1_wire_fail_closed(self):
        with self.assertRaises(QueueError):
            LocalActions(self.q)
        with self.assertRaisesRegex(QueueError,"LOCAL_DISPOSITION_WIRE_V2_REQUIRED"):
            Session(self.owner,lambda *_:None)
        self.assertIsNotNone(self.owner.inventory(limit=1)["inventory"]["prepared"])

    def test_corrupt_disposition_refuses_admission(self):
        self.dismiss(self.review())
        with self.q._transaction(write=True) as db:
            db.execute("UPDATE memory_queue_local_actions_v1 SET dismissal='{}'")
        with self.assertRaisesRegex(QueueError,"INVALID_LOCAL_DISPOSITION"):
            self.owner.inventory(limit=16)
        with self.assertRaisesRegex(QueueError,"INVALID_LOCAL_DISPOSITION"):
            self.owner.prepare_action(self.message())
        self.assertEqual(self.captures,0)

    def test_missing_action_is_not_dismissible(self):
        with self.assertRaisesRegex(QueueError,"ACTION_RECORD_UNAVAILABLE"):
            self.owner.begin_recovery_review(str(uuid.uuid4()),max_age_ms=1000)
        self.assertIsNone(self.q.pending())


    def wire(self,*,connect=True):
        sent=[]
        session=Session(self.owner,sent.append,review_max_age_ms=1000,disposition_wire=True)
        session.start()
        self.assertEqual([p["kind"] for p in sent],["HELLO_DISPOSITION"])
        def send(kind,**fields):
            session.receive(encode({"version":1,"kind":kind,"owner_id":self.owner.owner_id,**fields})[:-1])
            return sent[-1]
        if connect:
            send("CONNECT_DISPOSITION")
            self.assertEqual([p["kind"] for p in sent],["HELLO_DISPOSITION","INVALIDATE","STATUS"])
        return session,sent,send

    def test_wire_disposition_exact_review_then_history(self):
        session,sent,send=self.wire()
        review=send("RECOVERY_REVIEW",action_id=self.old["action_id"])
        selection={"review_id":review["review"]["review_id"],"review_digest":review["review"]["review_digest"],
                   "review_sequence":review["sequence"]}
        send("RECOVERY_DISMISS",**selection)
        self.assertEqual([p["kind"] for p in sent[-3:]],["LOCAL_DISPOSITION","INVALIDATE","STATUS"])
        receipt=sent[-3]["receipt"]
        self.assertFalse(receipt["startup_unlock"])
        self.assertFalse(receipt["can_execute"])
        inventory=send("INVENTORY",limit=4)["inventory"]
        self.assertEqual(inventory["version"],2)
        self.assertIsNone(inventory["prepared"])
        self.assertEqual(inventory["recent"][0]["record"],self.original)
        self.assertEqual(inventory["recent"][0]["disposition"],receipt)
        self.assertEqual(send("DISPOSITION_HISTORY",action_id=self.old["action_id"])["receipt"],receipt)
        with self.assertRaisesRegex(QueueError,"RECOVERY_PIPE_NOT_LIVE"):
            send("RECOVERY_DISMISS",**selection)
        self.assertTrue(session.closed)
        self.assertEqual(self.captures,0)

    def test_wire_lost_disposition_receipt_is_read_only_after_restart(self):
        session,sent,send=self.wire()
        review=send("RECOVERY_REVIEW",action_id=self.old["action_id"])
        def fail(packet):
            if packet["kind"]=="LOCAL_DISPOSITION":
                raise OSError("fixture lost dismissal reply")
            sent.append(packet)
        session.emit=fail
        with self.assertRaises(OSError):
            send("RECOVERY_DISMISS",review_id=review["review"]["review_id"],
                 review_digest=review["review"]["review_digest"],review_sequence=review["sequence"])
        self.assertTrue(session.closed)
        self.owner=self.open(True)
        _,_,read=self.wire()
        receipt=read("DISPOSITION_HISTORY",action_id=self.old["action_id"])["receipt"]
        self.assertEqual(receipt["review"],review["review"])
        self.assertIsNone(read("INVENTORY",limit=4)["inventory"]["prepared"])
        self.assertIsNone(self.q.pending())

    def test_wire_refuses_old_client_before_any_action(self):
        session,_,send=self.wire(connect=False)
        with self.assertRaisesRegex(QueueError,"LOCAL_DISPOSITION_HANDSHAKE_REQUIRED"):
            send("INVENTORY",limit=1)
        self.assertTrue(session.closed)
        self.assertEqual(self.captures,0)

    def test_wire_wrong_review_sequence_terminal(self):
        session,_,send=self.wire()
        review=send("RECOVERY_REVIEW",action_id=self.old["action_id"])
        with self.assertRaisesRegex(QueueError,"RECOVERY_PIPE_MISMATCH"):
            send("RECOVERY_DISMISS",review_id=review["review"]["review_id"],
                 review_digest=review["review"]["review_digest"],review_sequence=review["sequence"]+1)
        self.assertTrue(session.closed)
        self.owner=self.open(True)
        self.assertIsNone(self.owner.disposition_history(self.old["action_id"])["receipt"])

if __name__=="__main__":
    unittest.main(verbosity=2)
