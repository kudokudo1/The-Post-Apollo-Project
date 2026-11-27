const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const p=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,"../../widgets/forest/ui2/LocalConversationPresentation.js"),"utf8"),p);
const make=()=>{
    const feed={visible:true,conversation:{id:"original"},effectiveScope:"local-view-1",
        streamingTailEnabled:true,showComposer:false,sendEnabled:false,richMessageActions:false,
        loading:false,error:"",messages:[],tail:"",
        clearStreamingTail(){this.tail="";},
        updateStreamingTail(scope,body){
            if(scope!==this.effectiveScope || this.messages.length!==2)return false;
            this.tail=body;return true;
        }};
    return {feed,c:p.createPresentation(feed)};
};
const snap=(sequence,status,text="",local_outcome="UNKNOWN_HOLD",provisional=false,native_admitted=false)=>
    ({sequence,status,text,local_outcome,provisional,native_admitted});
const start=()=>{const {c,feed}=make();c.observe(1);assert.equal(c.attach(1,"Exact public input"),true);return {c,feed};};
let n=0;
function check(name,fn){fn();n++;console.log("PASS",name);}
check("nothing opens or renders from unsolicited packets",()=>{
    const {c,feed}=make();assert.equal(c.receive(1,snap(1,"GENERATING","text","UNKNOWN_HOLD",true,true)),false);
    assert.equal(c.attach(1,"input"),false);assert.equal(feed.messages.length,0);
});
check("attach exact accepted input and one operation",()=>{
    const {c,feed}=start();assert.equal(feed.messages[0].body,"Exact public input");
    assert.equal(c.attach(1,"replacement"),false);
    assert.equal(c.receive(1,snap(1,"PREPARED")),true);assert.equal(feed.messages.length,1);
});
check("actual admission marker required for output; no fixture promotion",()=>{
    const {c,feed}=start();
    assert.equal(c.receive(1,snap(1,"GENERATING","RE","UNKNOWN_HOLD",true,false)),false);
    assert.equal(c.state().status,"UNKNOWN_HOLD");assert.equal(feed.messages.length,1);
});
check("coalesced snapshots grow same incoming row and original committed body",()=>{
    const {c,feed}=start();assert.equal(c.receive(1,snap(4,"GENERATING","RE","UNKNOWN_HOLD",true,true)),true);
    const rows=feed.messages;
    assert.equal(c.receive(1,snap(7,"GENERATING","READY","UNKNOWN_HOLD",true,true)),true);
    assert.equal(feed.messages,rows);assert.equal(feed.tail,"READY");
    assert.equal(c.receive(1,snap(9,"LOCAL_COMMITTED","READY","COMMITTED_LOCAL",false,true)),true);
    assert.equal(feed.messages,rows);assert.equal(c.state().terminal,true);
    assert.equal(c.receive(1,snap(10,"UNKNOWN_HOLD")),false);assert.equal(feed.tail,"READY");
});
check("STOP observation is not terminal; abort discards provisional answer",()=>{
    const {c,feed}=start();c.receive(1,snap(1,"GENERATING","RE","UNKNOWN_HOLD",true,true));
    assert.equal(c.receive(1,snap(2,"STOP_REQUESTED","RE","UNKNOWN_HOLD",true,true)),true);
    assert.equal(c.state().terminal,false);assert.equal(feed.tail,"RE");
    assert.equal(c.receive(1,snap(4,"UNKNOWN_HOLD","","ABORTED_LOCAL",false,true)),true);
    assert.equal(feed.messages.length,1);assert.equal(feed.tail,"");assert.equal(c.state().terminal,true);
});
check("duplicate and stale scope cannot advance original",()=>{
    const {c,feed}=start();c.receive(1,snap(3,"GENERATING","RE","UNKNOWN_HOLD",true,true));
    assert.equal(c.receive(2,snap(4,"LOCAL_COMMITTED","READY","COMMITTED_LOCAL",false,true)),false);
    assert.equal(c.receive(1,snap(3,"GENERATING","RE","UNKNOWN_HOLD",true,true)),false);
    assert.equal(c.state().sequence,3);assert.equal(feed.tail,"RE");
});
check("ABA withdrawal clears original and cannot reopen it",()=>{
    const {c,feed}=start();c.receive(1,snap(1,"GENERATING","RE","UNKNOWN_HOLD",true,true));
    c.observe(2);c.observe(1);
    assert.equal(c.attach(1,"other"),false);assert.equal(c.receive(1,snap(2,"LOCAL_COMMITTED","READY","COMMITTED_LOCAL",false,true)),false);
    assert.equal(feed.messages.length,0);assert.equal(c.state().status,"WITHDRAWN");
});
check("retirement never clears replacement display scope",()=>{
    const {c,feed}=start();feed.effectiveScope="replacement";const rows=[{body:"replacement"}];feed.messages=rows;
    c.observe(2);assert.equal(feed.messages,rows);
    assert.equal(c.receive(1,snap(2,"UNKNOWN_HOLD")),false);assert.equal(feed.messages,rows);
});
check("bad typed snapshot clears partial and is terminal",()=>{
    for(const bad of [
        snap(2,"GENERATING","other","UNKNOWN_HOLD",true,true),
        snap(2,"LOCAL_COMMITTED","READY","UNKNOWN_HOLD",false,true),
        snap(2,"GENERATING","RE"+"é".repeat(8000),"UNKNOWN_HOLD",true,true),
        {...snap(2,"GENERATING","READY","UNKNOWN_HOLD",true,true),extra:true},
        snap(2,"GENERATING","RE\x00","UNKNOWN_HOLD",true,true),
        snap(2,"PREPARED")
    ]){
        const {c,feed}=start();c.receive(1,snap(1,"GENERATING","RE","UNKNOWN_HOLD",true,true));
        assert.equal(c.receive(1,bad),false);assert.equal(c.state().status,"UNKNOWN_HOLD");
        assert.equal(feed.messages.length,1);assert.equal(feed.tail,"");
    }
});
check("renderer refusal cannot promote a response",()=>{
    const {c,feed}=start();feed.updateStreamingTail=()=>false;
    assert.equal(c.receive(1,snap(1,"LOCAL_COMMITTED","READY","COMMITTED_LOCAL",false,true)),false);
    assert.equal(feed.messages.length,1);assert.equal(c.state().status,"UNKNOWN_HOLD");
});
check("invalid input and hidden view cannot attach",()=>{
    const {c,feed}=make();c.observe(1);
    for(const bad of ["","é".repeat(2049),"a\x00b","\ud800"])assert.equal(c.attach(1,bad),false);
    feed.visible=false;assert.equal(c.attach(1,"prompt"),false);
});
console.log("UI2_REAL_PRESENTATION_PASS",n);
