const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const policy = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, "widgets/forest/ui2/PublicSessionDisplay.js"), "utf8"), policy);
const raw = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, "widgets/ForestChatSessionPolicy.js"), "utf8"), raw);
const upstream = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, "services/forest/ForestSessionListConsumerPolicy.js"), "utf8"), upstream);
const view = {requestId:"ui21_fixture_0001",treeKey:"CHERRY",generation:1};
const row = {session_id:"demo-a",title:"Public sample",revision:0,updated_at_ms:1};
const frame = rows => ({schema:"postapollo.forest.public-session-display.v1",...view,sessions:rows});
let count = 0;
function check(name, fn) { fn(); count++; console.log("PASS",name); }
function denied(f, requested=view,current=view) {
    const out = policy.project(f,requested,current);
    assert.equal(out.state,"UNAVAILABLE"); assert.equal(out.sessions.length,0);
    assert.equal(out.sourceAuthenticated,false); assert.equal(out.permissionGranted,false);
    assert.equal(out.safeActions.length,0);
}
check("projection copy and stable sorting",()=>{
    const f=frame([row,{...row,session_id:"demo-b",updated_at_ms:2}]);
    const o=policy.project(f,view,view);
    assert.equal(o.state,"STRUCTURALLY_VALID_PUBLIC_FIXTURE");
    assert.equal(o.sessions[0].session_id,"demo-b");
    assert.equal(o.sessions[1].session_id,"demo-a");
    assert.equal(o.sourceAuthenticated,false); assert.equal(o.permissionGranted,false);
    assert.equal(o.safeActions.length,0); o.sessions[1].title="changed";
    assert.equal(row.title,"Public sample");
});
check("empty display",()=>assert.equal(policy.project(frame([]),view,view).state,"STRUCTURALLY_VALID_PUBLIC_FIXTURE"));
check("actual existing upstream projection compatible, raw validator intact",()=>{
    const original={...row,tree_key:"CHERRY",state:"OPEN",created_at_ms:1};
    const p=upstream.beginList(view.treeKey,view.requestId,view.generation);
    const u=upstream.consumeList(p,{schema:"postapollo.forest.list-sessions-ui.v1",action:"LIST_SESSIONS",...view,status:"READ_ONLY",complete:true,sessions:[original]},view.treeKey,view.generation);
    assert.equal(u.sessions.length,1);
    assert.equal(raw.openSessions(u.sessions,view.treeKey).length,0);
    assert.equal(raw.openSessions([original],view.treeKey).length,1);
    assert.equal(policy.project(frame(u.sessions),view,view).sessions.length,1);
    denied(frame([original]));
});
check("stale generation",()=>denied(frame([row]),view,{...view,generation:2}));
check("cross Tree",()=>denied(frame([row]),view,{...view,treeKey:"MAPLE"}));
check("wrong request",()=>denied(frame([row]),view,{...view,requestId:"ui21_fixture_0002"}));
check("wrong schema",()=>denied({...frame([row]),schema:"other"}));
check("unknown authority field",()=>denied({...frame([row]),permissionGranted:true}));
check("duplicate ID",()=>denied(frame([row,row])));
check("unknown fields",()=>denied(frame([{...row,owner_key:"not-real"}])));
check("invalid revision",()=>denied(frame([{...row,revision:-1}])));
check("invalid timestamp",()=>denied(frame([{...row,updated_at_ms:Infinity}])));
check("UTF8 byte bound",()=>denied(frame([{...row,title:"🌲".repeat(41)}])));
check("malformed surrogate",()=>denied(frame([{...row,title:String.fromCharCode(0xd800)}])));
check("control/bidi refusal",()=>denied(frame([{...row,title:"x"+String.fromCharCode(0x202e)}])));
check("oversized array",()=>denied(frame(Array.from({length:101},(_,i)=>({...row,session_id:"demo-"+i})))));
check("whole snapshot refused",()=>denied(frame([row,{...row,session_id:"demo-b",title:""}])));
check("invalid view",()=>denied(frame([row]),{...view,generation:0},view));
check("fixture uses existing feed and fails closed",()=>{
    const q=fs.readFileSync(path.join(root,"widgets/forest/ui2/PublicConversationFixture.qml"),"utf8");
    assert.match(q,/ConversationFeed\s*\{/);
    assert.match(q,/sendEnabled:\s*false/);
    assert.match(q,/messageTextFormat:\s*Text.PlainText/);
    assert.doesNotMatch(q,/onSendRequested\s*:|\b(?:Window|Process|XMLHttpRequest)\s*\{/);
});
console.log(count+" checks passed (JS and QML source only; no native rendering)");
