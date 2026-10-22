#!/usr/bin/env node
"use strict";
// Exercise the actual Hub B8 Notes policy; no real user data or file writes.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const script=fs.readFileSync(path.join(__dirname,
    "../../services/hub/ApolloHubNotesPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const policy=vm.createContext({});
vm.runInContext(script,policy,{filename:"ApolloHubNotesPolicy.js"});

const time=1000000;
let base=policy.emptyDocument();
assert.equal(policy.validate(base).ok,true);
assert.equal(policy.displayList("empty",base).writable,true);
assert.equal(policy.displayList("loading",base).writable,false);
assert.equal(policy.displayList("unsupported",base,"UNSUPPORTED_VERSION").error,
             "UNSUPPORTED_VERSION");
assert.equal(policy.detail("error",base,"n1"),null);

let first=policy.create(base,"  Reading list  ","Line 1\r\nLine 2",time);
assert.equal(first.ok,true);
assert.equal(first.document.notes.length,1);
assert.equal(first.document.notes[0].id,"n1");
assert.equal(first.document.notes[0].title,"Reading list");
assert.equal(first.document.notes[0].body,"Line 1\nLine 2");
assert.equal(first.document.notes[0].revision,1);
assert.equal(first.document.nextId,2);
assert.equal(base.notes.length,0); // immutable
base=first.document;
assert.equal(policy.create(base,"", "body",time+10).reason,"INVALID_TITLE");
assert.equal(policy.create(base,"a\nb","body",time+10).reason,"INVALID_TITLE");
assert.equal(policy.create(base,"x".repeat(121),"body",time+10).reason,"INVALID_TITLE");
assert.equal(policy.create(base,"ok",null,time+10).reason,"INVALID_BODY");
assert.equal(policy.create(base,"ok","x".repeat(8193),time+10).reason,"INVALID_BODY");
assert.equal(policy.create(base,"ok","nul\u0000bad",time+10).reason,"INVALID_BODY");
assert.equal(policy.create(base,"ok","",0).reason,"INVALID_TIME");

let second=policy.create(base,"Quick note","",time+10);
assert.equal(second.ok,true);
base=second.document;
assert.equal(policy.displayList("ready",base).total,2);
assert.equal(policy.displayList("ready",base).items[0].id,"n2");
assert.equal(policy.displayList("ready",base).items[1].id,"n1");
let details=policy.detail("ready",base,"n1");
assert.equal(details.title,"Reading list");
assert.equal(details.body,"Line 1\nLine 2");
assert.equal(details.revision,1);
details.body="local edit is not stored";
assert.equal(base.notes[0].body,"Line 1\nLine 2");
assert.equal(policy.detail("saving",base,"n1"),null);
assert.equal(policy.detail("ready",base,"nope"),null);

assert.equal(policy.update(base,"n1",0,"Title","Body",time+20).reason,
             "STALE_REVISION");
assert.equal(policy.update(base,"n1",2,"Title","Body",time+20).reason,
             "STALE_REVISION");
assert.equal(policy.update(base,"n1",1,"Reading list","Line 1\nLine 2",
                           time+20).reason,"NO_CHANGE");
assert.equal(policy.update(base,"n1",1,"Title","Body",time-1).reason,
             "INVALID_TIME");
assert.equal(policy.update(base,"n1",1,"Title",123,time+20).reason,
             "INVALID_BODY");
assert.equal(policy.update(base,"missing",1,"Title","Body",time+20).reason,
             "UNKNOWN_ID");

const updated=policy.update(base,"n1",1,"Revised","Saved explicitly",time+30);
assert.equal(updated.ok,true);
assert.equal(updated.document.notes[0].id,"n1");
assert.equal(updated.document.notes[0].revision,2);
assert.equal(updated.document.notes[0].body,"Saved explicitly");
assert.equal(base.notes[0].revision,1);
assert.equal(policy.update(updated.document,"n1",1,"Old","Stale",time+40).reason,
             "STALE_REVISION");
assert.equal(policy.remove(updated.document,"n1",1,true).reason,
             "STALE_REVISION");
assert.equal(policy.remove(updated.document,"n1",2,false).reason,
             "CONFIRM_REQUIRED");
assert.equal(updated.document.notes.length,2);
const deleted=policy.remove(updated.document,"n1",2,true);
assert.equal(deleted.ok,true);
assert.equal(deleted.document.notes.length,1);
assert.equal(deleted.document.nextId,3);
assert.equal(policy.create(deleted.document,"Next","",time+70)
             .document.notes[1].id,"n3");

const raw=JSON.stringify(updated.document);
assert.equal(policy.parse(raw).ok,true);
assert.equal(policy.parse(raw).document.notes[0].revision,2);
assert.equal(policy.parse("{garbage").reason,"INVALID_JSON");
assert.equal(policy.parse("").reason,"INVALID_FILE");
assert.equal(policy.parse("x".repeat(1048577)).reason,"INVALID_FILE");
assert.equal(policy.parse(JSON.stringify({version:2,nextId:1,notes:[]})).reason,
             "UNSUPPORTED_VERSION");
assert.equal(policy.parse(JSON.stringify({version:1,nextId:1,notes:[{
    id:"n1",title:"A",body:"",revision:1,createdAtMs:1,updatedAtMs:1
}]})).reason,"SEQUENCE_REWIND");
assert.equal(policy.parse(JSON.stringify({version:1,nextId:3,notes:[
    {id:"n1",title:"A",body:"",revision:1,createdAtMs:1,updatedAtMs:1},
    {id:"n1",title:"B",body:"",revision:1,createdAtMs:1,updatedAtMs:1}
]})).reason,"DUPLICATE_ID");
for(const n of [
    {id:"n0",title:"T",body:"",revision:1,createdAtMs:1,updatedAtMs:1},
    {id:"n1",title:"",body:"",revision:1,createdAtMs:1,updatedAtMs:1},
    {id:"n1",title:"T ",body:"",revision:1,createdAtMs:1,updatedAtMs:1},
    {id:"n1",title:"T",body:"",revision:0,createdAtMs:1,updatedAtMs:1},
    {id:"n1",title:"T",body:"",revision:1,createdAtMs:10,updatedAtMs:5},
    {id:"n1",title:"T",body:"\u0000",revision:1,createdAtMs:1,updatedAtMs:1}
]){
    assert.equal(policy.parse(JSON.stringify({version:1,nextId:3,
                                             notes:[n]})).ok,false);
}
const extra={...updated.document,accessToken:"PRIVATE",notes:[
    {...updated.document.notes[0],exec:"DANGEROUS"},
    updated.document.notes[1]
]};
const parsedExtra=policy.parse(JSON.stringify(extra));
assert.equal(parsedExtra.ok,true);
assert.equal(JSON.stringify(parsedExtra.document).includes("PRIVATE"),false);
const listing=policy.displayList("ready",parsedExtra.document);
assert.equal(listing.items[0].title,"Revised");
assert.equal(listing.items[0].preview,"Saved explicitly");
assert.equal(JSON.stringify(listing).includes("DANGEROUS"),false);
assert.equal(JSON.stringify(listing).includes("createdAtMs"),false);
assert.equal(JSON.stringify(listing).includes("body"),false);
assert.equal(policy.displayList("saving",updated.document).writable,false);
assert.equal(policy.displayList("error",updated.document).total,0);
assert.equal(policy.displayList("unsupported",updated.document).total,0);

const full=policy.emptyDocument();
full.nextId=102;
full.notes=Array.from({length:100},(_,i)=>({
    id:"n"+(i+1),title:"Note "+i,body:"",revision:1,
    createdAtMs:1,updatedAtMs:1
}));
assert.equal(policy.validate(full).ok,true);
assert.equal(policy.create(full,"Extra","",time).reason,"CAPACITY");
const large=policy.create(policy.emptyDocument(),"Big","a".repeat(8192),time);
assert.equal(large.ok,true);
assert.equal(large.document.notes[0].body.length,8192);
assert.equal(policy.inputBody("with\r\nnewlines"),"with\nnewlines");

console.log("ApolloHub B8 Notes revision, persistence schema and safety policy tests passed");
