"""R6b actual isolated child and independent disposable SQLite evidence."""
import json
import os
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts/forest"
sys.path.insert(0, str(SCRIPTS))
from runtime_public_child_r6b import canonical, decode, WireError, CONTROL, RESPONSE, Child, Wire, TOTAL

TRIAL = "a"*32


class ProcessTrial:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="r6b-ci-")
        self.path = Path(self.tmp.name)
        self.p = subprocess.Popen([sys.executable,"-I","-B","-u",
            str(SCRIPTS/"runtime_public_child_r6b.py")], cwd=self.path,
            env=dict(HOME=str(self.path),TMPDIR=str(self.path),
                     LANG="C.UTF-8",FOREST_R6_CI_ONLY="1"),
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            bufsize=0,close_fds=True)
        self.action = 0
        self.bytes = self.frames = 0

    def __enter__(self):
        return self

    def __exit__(self,*exc):
        if self.p.poll() is None:
            self.p.kill()
        self.p.wait(timeout=5)
        for f in (self.p.stdin,self.p.stdout,self.p.stderr):
            f.close()
        self.tmp.cleanup()

    def send(self,kind,data,ack=False):
        if not ack:
            self.action += 1
        raw=canonical(dict(v=1,trial=TRIAL,action=self.action,kind=kind,data=data))
        assert len(raw)<=CONTROL
        self.p.stdin.write(raw)
        self.bytes+=len(raw)
        self.frames+=1

    def read(self):
        deadline=time.monotonic()+8
        raw=bytearray()
        while len(raw)<RESPONSE:
            remain=deadline-time.monotonic()
            if remain<=0 or not select.select([self.p.stdout],[],[],remain)[0]:
                raise AssertionError("response timeout")
            b=os.read(self.p.stdout.fileno(),1)
            if not b:
                raise AssertionError("unexpected EOF")
            raw.extend(b)
            if b==b"\n":
                obj=decode(bytes(raw),RESPONSE)
                assert obj["action"]==self.action and obj["trial"]==TRIAL
                self.bytes+=len(raw)
                self.frames+=1
                return obj
        raise AssertionError("response limit")

    def result(self,kind,data,code):
        self.send(kind,data)
        x=self.read()
        assert x["kind"]=="RESULT" and x["data"]["code"]==code,x
        return x["data"]["units"]

    def offer(self,kind,key,offer,ack,code):
        self.send(kind,{})
        x=self.read()
        assert x["kind"]==offer
        scope=x["data"][key]
        self.send(ack,{key:scope,"accepted":True},ack=True)
        y=self.read()
        assert y["kind"]=="RESULT" and y["data"]==dict(code=code,units=[]),y
        return scope

    def db(self):
        paths=list(self.path.glob("forest-r5-public-*/conversation.sqlite"))
        assert len(paths)==1,paths
        return sqlite3.connect(str(paths[0]))

    def next(self):
        return self.offer("NEXT","ref","OPEN_OFFER","OPEN_ACK","TURN_STARTED")

    def finish(self,ref):
        units=[]
        for i in range(5):
            units.extend(self.result("STEP",{"ref":ref},
                        "COMMITTED_LOCAL" if i==4 else "ACTIVE"))
        assert [u["sequence"] for u in units]==list(range(1,len(units)+1))
        assert all(u["kind"]=="STATUS" and u["requestId"]==ref["requestId"] for u in units)
        assert len(units)==4,units  # REQUESTED, RESERVED, STARTED, commit; DELTA suppressed.
        return units

    def page(self,scope,after):
        req={k:scope[k] for k in ("treeKey","generation","sessionId","revision")}
        req.update(requestId=f"{self.action+1000:032x}",after=after,limit=2)
        self.send("HISTORY_PAGE",dict(scope=scope,request=req))
        x=self.read()
        assert x["kind"]=="PAGE" and x["data"]["scope"]==scope
        p=x["data"]["page"]
        assert p["requestId"]==req["requestId"] and p["sessionId"]==scope["sessionId"]
        return p

    def history(self):
        return self.offer("HISTORY_ATTACH","scope","HISTORY_OFFER",
                          "HISTORY_ACK","HISTORY_ATTACHED")

    def closed(self,code):
        assert self.p.wait(timeout=8)==code
        assert self.p.stdout.read()==b""
        assert self.p.stderr.read()==b""


@unittest.skipIf(os.getuid()==0,"requires unprivileged child")
class ChildTests(unittest.TestCase):
    def test_two_turns_reopen_read_only_history_stop(self):
        with ProcessTrial() as t:
            self.assertEqual(t.result("HELLO",{},"READY"),[])
            t.send("NEXT",{})
            offer=t.read()["data"]["ref"]
            with t.db() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM forest_turns").fetchone(),(0,))
            t.send("OPEN_ACK",dict(ref=offer,accepted=True),ack=True)
            self.assertEqual(t.read()["data"],dict(code="TURN_STARTED",units=[]))
            t.finish(offer)
            h1=t.history()
            p1=t.page(h1,0)
            self.assertTrue(p1["complete"])
            ref=t.next()
            self.assertNotEqual(ref,offer)
            t.finish(ref)
            h2=t.history()
            p2=t.page(h2,0)
            p3=t.page(h2,2)
            self.assertEqual(p1["messages"],p2["messages"])
            self.assertEqual(h1["sessionId"],h2["sessionId"])
            self.assertEqual(t.result("REOPEN",{},"JOURNAL_REOPENED"),[])
            h3=t.history()
            self.assertNotEqual(h2["viewKey"],h3["viewKey"])
            self.assertEqual(h2["sessionId"],h3["sessionId"])
            self.assertEqual(t.page(h3,0)["messages"],p2["messages"])
            self.assertEqual(t.page(h3,2)["messages"],p3["messages"])
            ref=t.next()
            for _ in range(4):
                t.result("STEP",dict(ref=ref),"ACTIVE")
            t.result("STOP",dict(ref=ref),"STOP_OBSERVED")
            t.result("STEP",dict(ref=ref),"ABORTED_LOCAL")
            with t.db() as db:
                self.assertEqual(db.execute("SELECT revision FROM forest_sessions").fetchone(),(5,))
                self.assertEqual(db.execute("SELECT status FROM forest_attempts_b3 "
                    "ORDER BY expected_revision").fetchall(),
                    [("COMMITTED",),("COMMITTED",),("ABORTED",)])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM forest_turns WHERE role='assistant'").fetchone(),(2,))
                self.assertEqual(db.execute("SELECT reply_turn_id FROM forest_attempts_b3 "
                    "WHERE status='ABORTED'").fetchone(),(None,))
                ids={x[0] for x in db.execute("SELECT turn_id FROM forest_turns")}
                self.assertTrue(ids.isdisjoint({x["turn_id"] for x in p2["messages"]+p3["messages"]}))
            self.assertLessEqual(t.bytes,131072)
            self.assertLessEqual(t.frames,160)
            self.assertEqual(t.result("CLOSE",{},"CLOSED"),[])
            t.closed(0)

    def test_reopen_rejects_missing_replaced_or_symlink_path(self):
        for mode in ("missing", "replacement", "symlink"):
            with self.subTest(mode=mode), ProcessTrial() as t:
                t.result("HELLO", {}, "READY")
                t.finish(t.next())
                path, = t.path.glob("forest-r5-public-*/conversation.sqlite")
                saved = path.with_name("original.sqlite")
                path.rename(saved)
                if mode == "replacement":
                    path.write_bytes(b"not the original journal")
                elif mode == "symlink":
                    path.symlink_to(saved)
                self.assertEqual(t.result("REOPEN", {}, "REFUSED"), [])
                t.closed(2)

    def test_cumulative_frame_reserve_before_next_offer(self):
        # HELLO consumes two frames, every history attachment four.
        # At 158 frames, CLOSE can fit but NEXT's full exchange cannot.
        for close in (True, False):
            with self.subTest(close=close), ProcessTrial() as t:
                t.result("HELLO", {}, "READY")
                for _ in range(39):
                    t.history()
                self.assertEqual(t.frames, 158)
                with t.db() as db:
                    self.assertEqual(db.execute(
                        "SELECT revision FROM forest_sessions").fetchone(), (0,))
                    self.assertEqual(db.execute(
                        "SELECT COUNT(*) FROM forest_turns").fetchone(), (0,))
                if close:
                    self.assertEqual(t.result("CLOSE", {}, "CLOSED"), [])
                    self.assertEqual(t.frames, 160)
                    t.closed(0)
                else:
                    t.send("NEXT", {})
                    # No OPEN_OFFER or RESULT may consume the reserved
                    # capacity or start an operation. Child closes silently.
                    t.closed(2)

    def test_wrong_or_false_ack_closes(self):
        for false in (True,False):
            with self.subTest(false=false),ProcessTrial() as t:
                t.result("HELLO",{},"READY")
                t.send("NEXT",{})
                ref=t.read()["data"]["ref"]
                with t.db() as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM forest_turns").fetchone(),(0,))
                if false:
                    t.send("OPEN_ACK",dict(ref=ref,accepted=False),ack=True)
                    self.assertEqual(t.read()["data"],dict(code="REFUSED",units=[]))
                else:
                    ref["viewKey"]="f"*32
                    t.send("OPEN_ACK",dict(ref=ref,accepted=True),ack=True)
                t.closed(2)

    def test_ack_lost_result_does_not_replay(self):
        with ProcessTrial() as t:
            t.result("HELLO",{},"READY")
            t.send("NEXT",{})
            ref=t.read()["data"]["ref"]
            t.send("OPEN_ACK",dict(ref=ref,accepted=True),ack=True)
            # Do not consume the result; independently witness possible durable append.
            deadline=time.monotonic()+3
            count=0
            while time.monotonic()<deadline:
                with t.db() as db:
                    count=db.execute("SELECT COUNT(*) FROM forest_turns").fetchone()[0]
                if count:
                    break
                time.sleep(.01)
            self.assertEqual(count,1)
            t.p.stdin.close()
            self.assertEqual(t.p.wait(timeout=8),2)
            self.assertEqual(t.p.stderr.read(),b"")

    def test_stale_history_request_and_duplicate_action(self):
        with ProcessTrial() as t:
            t.result("HELLO",{},"READY")
            scope=t.history()
            req={k:scope[k] for k in ("treeKey","generation","sessionId","revision")}
            req.update(requestId="b"*32,after=0,limit=2,revision=1)
            self.assertEqual(t.result("HISTORY_PAGE",dict(scope=scope,request=req),"REFUSED"),[])
            t.closed(2)
        with ProcessTrial() as t:
            t.result("HELLO",{},"READY")
            t.send("NEXT",{},ack=True)
            t.closed(2)

    def test_invalid_raw_and_timeout(self):
        for raw in (b"x\n", b" "*512, b'{"x":1,"x":2}\n', b"\xff\n", b'{"v":1'):
            with self.subTest(raw=raw[:10]),ProcessTrial() as t:
                t.p.stdin.write(raw)
                t.p.stdin.close()
                t.closed(2)
        with ProcessTrial() as t:
            t.result("HELLO",{},"READY")
            t.send("NEXT",{})
            t.read()
            t.closed(2)


class OwnerBoundaryTests(unittest.TestCase):
    def test_failed_open_ack_never_appends_before_cleanup(self):
        class FakeWire:
            def __init__(self, mode):
                self.mode = mode
                self.offer = None

            def send(self, obj):
                self.offer = obj

            def read(self):
                if self.mode == "missing":
                    raise WireError()
                ref = dict(self.offer["data"]["ref"])
                if self.mode == "wrong":
                    ref["viewKey"] = "f"*32
                return dict(v=1, trial=TRIAL, action=2, kind="OPEN_ACK",
                            data=dict(ref=ref, accepted=self.mode != "false"))

            def check(self):
                return 1

            def room(self, *args):
                pass

        for mode in ("missing", "wrong", "false"):
            with self.subTest(mode=mode):
                child = Child(FakeWire(mode))
                child.trial, child.action = TRIAL, 1
                child.dispatch("HELLO", {})
                try:
                    child.action = 2
                    with self.assertRaises(Exception) as e:
                        child.dispatch("NEXT", {})
                    if mode != "false":
                        self.assertIsInstance(e.exception, WireError)
                    self.assertFalse(child.effect_possible)
                    self.assertEqual(child.host._db.execute(
                        "SELECT COUNT(*) FROM forest_turns").fetchone(), (0,))
                    self.assertEqual(child.host._db.execute(
                        "SELECT COUNT(*) FROM forest_attempts_b3").fetchone(), (0,))
                finally:
                    child.current = None
                    child.host.close()

    def _committed_child(self):
        class AcceptWire:
            def send(self, obj):
                self.last = obj

            def read(self):
                offer = self.last
                return dict(v=1, trial=TRIAL, action=offer["action"],
                            kind="OPEN_ACK",
                            data=dict(ref=offer["data"]["ref"], accepted=True))

            def check(self):
                return 1

            def room(self, *args):
                pass

        child = Child(AcceptWire())
        child.trial, child.action = TRIAL, 1
        child.dispatch("HELLO", {})
        try:
            child.action += 1
            child.dispatch("NEXT", {})
            c = child.current
            ref = dict(requestId=c.request_id, viewKey=c.view_key,
                       generation=c.generation)
            for _ in range(5):
                child.action += 1
                child.dispatch("STEP", {"ref": ref})
            self.assertEqual(child.wire.last["data"]["code"], "COMMITTED_LOCAL")
            self.assertTrue(child.reopen_ready)
            return child
        except BaseException:
            child.current = None
            child.host.close()
            raise

    def test_reopen_precheck_refuses_before_retirement_or_sqlite_open(self):
        for mode in ("missing", "replacement", "symlink", "directory_mode"):
            with self.subTest(mode=mode):
                child = self._committed_child()
                host = child.host
                path = host._path
                saved = path.with_name("original.sqlite")
                original = host._db
                try:
                    if mode == "directory_mode":
                        path.parent.chmod(0o755)
                    else:
                        path.rename(saved)
                        if mode == "replacement":
                            # Even valid SQLite must never reach the opener.
                            with sqlite3.connect(path) as alternate:
                                alternate.execute("CREATE TABLE unrelated(x)")
                        elif mode == "symlink":
                            path.symlink_to(saved)
                    with patch.object(child, "_retire", wraps=child._retire) as retire, \
                         patch.object(sqlite3, "connect", wraps=sqlite3.connect) as connect:
                        child.action += 1
                        with self.assertRaises(Exception):
                            child.dispatch("REOPEN", {})
                        retire.assert_not_called()
                        connect.assert_not_called()
                    self.assertIs(host._db, original)
                    self.assertFalse(original.in_transaction)
                    self.assertFalse(child.effect_possible)
                    self.assertNotEqual(child.wire.last["data"]["code"], "JOURNAL_REOPENED")
                finally:
                    path.parent.chmod(0o700)
                    if saved.exists():
                        path.unlink(missing_ok=True)
                        saved.rename(path)
                    child.current = None
                    host.close()

    def test_reopen_rechecks_identity_after_retirement_before_opener(self):
        child = self._committed_child()
        host = child.host
        path = host._path
        saved = path.with_name("original.sqlite")
        original = host._db
        retire = child._retire

        def substitute_after_retire():
            retire()
            path.rename(saved)
            path.write_bytes(b"substituted before reopen")

        try:
            with patch.object(child, "_retire", side_effect=substitute_after_retire) as retired, \
                 patch.object(sqlite3, "connect", wraps=sqlite3.connect) as connect:
                child.action += 1
                with self.assertRaises(Exception):
                    child.dispatch("REOPEN", {})
                retired.assert_called_once_with()
                connect.assert_not_called()
            self.assertIs(host._db, original)
            self.assertFalse(original.in_transaction)
            self.assertFalse(child.effect_possible)
            self.assertIsNone(child.current)
            self.assertNotEqual(child.wire.last["data"]["code"], "JOURNAL_REOPENED")
        finally:
            if saved.exists():
                path.unlink(missing_ok=True)
                saved.rename(path)
            child.current = None
            host.close()

    def test_reopen_retains_post_open_identity_check(self):
        child = self._committed_child()
        host = child.host
        path = host._path
        saved = path.with_name("original.sqlite")
        reopen = host.reopen_journal

        def changed_after_reopen():
            result = reopen()
            path.rename(saved)
            path.write_bytes(b"substituted after original reopen")
            return result

        try:
            with patch.object(host, "reopen_journal", side_effect=changed_after_reopen) as call:
                child.action += 1
                with self.assertRaises(Exception):
                    child.dispatch("REOPEN", {})
                call.assert_called_once_with()
            self.assertTrue(child.effect_possible)
            self.assertFalse(host._db.in_transaction)
            self.assertNotEqual(child.wire.last["data"]["code"], "JOURNAL_REOPENED")
        finally:
            if saved.exists():
                path.unlink(missing_ok=True)
                saved.rename(path)
            child.current = None
            host.close()

    def test_blocked_output_and_capacity_reserve(self):
        ir, iw = os.pipe()
        rr, rw = os.pipe()
        try:
            wire = Wire(ir, rw)
            wire.phase()
            wire.bytes = TOTAL - 100
            wire.last_read = 0
            with self.assertRaises(WireError):
                wire.reserve(False)
            wire.bytes = 0
            wire.frames = 0
            # Fill a nonblocking pipe without retaining its contents.
            while True:
                try:
                    os.write(rw, b"x"*4096)
                except BlockingIOError:
                    break
            wire.deadline = time.monotonic()+.05
            with self.assertRaises(WireError):
                wire.send(dict(v=1,trial=TRIAL,action=1,kind="RESULT",
                    data=dict(code="READY",units=[])))
            self.assertGreater(wire.bytes, 0)
        finally:
            for fd in (ir, iw, rr, rw):
                os.close(fd)


class CodecTests(unittest.TestCase):
    def test_canonical_caps_and_lexical_limits(self):
        good=dict(v=1,trial=TRIAL,action=1,kind="HELLO",data={})
        raw=canonical(good)
        self.assertEqual(decode(raw,CONTROL),good)
        for bad in (raw.replace(b'"v":1',b'"v":true'),
                    raw.replace(b'"v":1',b'"v":1.0'),
                    raw.replace(b'"v":1',b'"v":1,"v":1'),
                    raw.replace(b'"data":{}',b'"data":{"__proto__":{}}'),
                    raw.replace(b'"data":{}',b'"data":{"x":"\\u0041"}'),
                    raw.replace(b'"data":{}',b'"data":{"x":'+b'['*9+b'0'+b']'*9+b'}'),
                    raw.replace(b'"data":{}',b'"data":{"x":9007199254740992}'),
                    raw[:-1], b" "*512+b"\n"):
            with self.subTest(bad=bad[:60]),self.assertRaises(WireError):
                decode(bad,CONTROL)
        with self.assertRaises(WireError):
            decode(canonical(dict(good,data={"x":[0]*257})),RESPONSE)


if __name__=="__main__":
    unittest.main(verbosity=2)
