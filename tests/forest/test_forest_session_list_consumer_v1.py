"""ForestW session LIST consumer tests. All responses are synthetic objects.

This is structural validation ONLY; no protected host, B1 database or C5
authorization is used or simulated as production-ready by these tests.
"""
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ForestSessionListConsumerV1Tests(unittest.TestCase):
    def test_only_pure_presenter_no_host_or_protected_db_access(self):
        policy = (ROOT / "services/forest/ForestSessionListConsumerPolicy.js").read_text()
        self.assertIn('postapollo.forest.list-sessions-ui.v1', policy)
        self.assertIn('action !== "LIST_SESSIONS"', policy)
        self.assertIn('state: "STRUCTURALLY_VALID_NOT_AUTHENTICATED"', policy)
        for required in (
            "sourceAuthenticated: false", "permissionGranted: false",
            "canReadSession: false", "safeActions: []",
            "frame.complete !== true", "row.tree_key !== pending.treeKey",
            "pending.generation !== currentGeneration",
            "row.updated_at_ms < row.created_at_ms",
        ):
            self.assertIn(required, policy)
        for prohibited in (
            "XMLHttpRequest", "Qt.openUrlExternally", "Quickshell.exec",
            "Process {", "sqlite3", "connect(", "fetch(", "localhost",
            "generation_enabled: true", "chatHostTrusted: true",
        ):
            self.assertNotIn(prohibited, policy)
        # This PR must not silently turn the UI's hard locked send/voice
        # gate or empty, untrusted B1 session list into an active connection.
        window = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn("readonly property bool chatHostTrusted: false", window)
        self.assertIn("readonly property bool voiceHostTrusted: false", window)
        self.assertIn("readonly property var activeChatSessions: []", window)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_forged_read_list_frame_never_grants_authority(self):
        js = textwrap.dedent(r"""
            const fs = require("fs");
            const vm = require("vm");
            const assert = require("assert");
            const ctx = vm.createContext({});
            vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), ctx);
            const begin = ctx.beginList;
            const consume = ctx.consumeList;
            const clear = ctx.clearList;
            const req = begin("CHERRY", "req_1234567890abcdef", 5);
            assert.strictEqual(req.state, "PENDING");
            const row = (id, tree="CHERRY", state="OPEN", ms=200) => ({
                session_id:id, tree_key:tree, title:"Project " + id,
                state:state, revision:1, created_at_ms:100, updated_at_ms:ms
            });
            const frame = (rows) => ({
                schema:"postapollo.forest.list-sessions-ui.v1",
                action:"LIST_SESSIONS", requestId:req.requestId,
                treeKey:"CHERRY", generation:5, status:"READ_ONLY",
                complete:true, sessions:rows
            });
            const f = frame([row("s_1"), row("s_2","CHERRY","PAUSED"),
                             row("s_3","CHERRY","OPEN",350)]);
            const good = consume(req, f, "CHERRY", 5);
            assert.strictEqual(good.state, "STRUCTURALLY_VALID_NOT_AUTHENTICATED");
            assert.strictEqual(good.sessions.length, 2);
            assert.strictEqual(good.sessions[0].session_id, "s_3");
            assert.strictEqual(good.sessions[1].title, "Project s_1");
            assert.strictEqual(Object.keys(good.sessions[0]).includes("tree_key"), false);
            assert.strictEqual(Object.keys(good.sessions[0]).includes("body"), false);
            const noAuthority = obj => {
                assert.strictEqual(obj.sourceAuthenticated, false);
                assert.strictEqual(obj.permissionGranted, false);
                assert.strictEqual(obj.canReadSession, false);
                assert.strictEqual(obj.safeActions.length, 0);
            };
            noAuthority(good);
            assert.strictEqual(consume(req, frame([]), "CHERRY", 5).sessions.length, 0);
            const failures = [
                ["wrong tree",req,frame([row("s_1")]),"MAPLE",5],
                ["stale generation",req,frame([row("s_1")]),"CHERRY",6],
                ["reset",clear(),frame([row("s_1")]),"CHERRY",5],
                ["wrong request",req,{...f,requestId:"req_badbadbadbadbad"},"CHERRY",5],
                ["wrong frame tree",req,{...f,treeKey:"MAPLE"},"CHERRY",5],
                ["wrong action",req,{...f,action:"READ_SESSION"},"CHERRY",5],
                ["wrong schema",req,{...f,schema:"postapollo.forest.host-intent.experimental-b4a"},"CHERRY",5],
                ["not complete",req,{...f,complete:false},"CHERRY",5],
                ["coerced complete",req,{...f,complete:1},"CHERRY",5],
                ["extra approval",req,{...f,authorized:true},"CHERRY",5],
                ["private body",req,frame([{...row("s_1"),body:"PRIVATE"}]),"CHERRY",5],
                ["owner field",req,frame([{...row("s_1"),owner_key:"secret"}]),"CHERRY",5],
                ["cross tree",req,frame([row("s_1"),row("s_4","CEDAR")]),"CHERRY",5],
                ["duplicate",req,frame([row("s_1"),row("s_1")]),"CHERRY",5],
                ["infinite revision",req,frame([{...row("s_1"),revision:Infinity}]),"CHERRY",5],
                ["bool revision",req,frame([{...row("s_1"),revision:true}]),"CHERRY",5],
                ["unsafe int",req,frame([{...row("s_1"),revision:Number.MAX_SAFE_INTEGER+1}]),"CHERRY",5],
                ["time reversal",req,frame([{...row("s_1"),updated_at_ms:99}]),"CHERRY",5],
                ["control title",req,frame([{...row("s_1"),title:"a\nb"}]),"CHERRY",5],
                ["bidi title",req,frame([{...row("s_1"),title:"x\u202ey"}]),"CHERRY",5],
                ["UTF8 >160 bytes",req,frame([{...row("s_1"),title:"é".repeat(81)}]),"CHERRY",5],
                ["bad surrogate",req,frame([{...row("s_1"),title:"\ud800"}]),"CHERRY",5],
                ["over page",req,frame(Array.from({length:101},(_,i)=>row("s_"+i))),"CHERRY",5],
                ["bad page structure",req,{...f,sessions:"x"},"CHERRY",5],
                ["malformed status",req,{...f,status:"GRANTED"},"CHERRY",5],
            ];
            for(const [name,pending,reply,tree,gen] of failures) {
                const result=consume(pending,reply,tree,gen);
                assert.strictEqual(result.state, "UNAVAILABLE", name);
                assert.strictEqual(result.sessions.length, 0, name);
                noAuthority(result);
            }
            const invalidRequests=[
                begin("OTHER","req_1234567890abcdef",5),
                begin("CHERRY","short",5),
                begin("CHERRY","req_1234567890abcdef",0),
                begin("CHERRY","req_1234567890abcdef",NaN),
            ];
            invalidRequests.forEach(x=>{
                assert.strictEqual(x.state,"UNAVAILABLE");
                noAuthority(x);
            });
        """)
        path = ROOT / "services/forest/ForestSessionListConsumerPolicy.js"
        p = subprocess.run(["node", "-e", js, str(path)],
                           capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
