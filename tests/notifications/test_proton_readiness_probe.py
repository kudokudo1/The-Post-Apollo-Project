#!/usr/bin/env python3
"""Proton opt-in read-only page readiness probe: no identity, no mailbox writes."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ROOT_JS = ROOT / "integrations/proton/browser"
PROBE = ROOT_JS / "readiness_probe.js"
BACKGROUND = ROOT_JS / "background.js"

probe = PROBE.read_text(encoding="utf8")
for forbidden in ("textContent", "innerHTML", "outerHTML", "localStorage",
                  "sessionStorage", "document.cookie", "fetch(", "XMLHttpRequest",
                  "getAttribute('href')", 'getAttribute("href")',
                  ".click(", "mailboxAccess: true", "canMutate: true"):
    assert forbidden not in probe, f"privacy/control forbidden in probe: {forbidden}"
assert "document.querySelectorAll" in probe
assert '"PROTON_READINESS_V1"' in probe
assert "messageIdentityVerified: false" in probe
assert "canMutate: false" in probe
assert "querySelectorAll" not in BACKGROUND.read_text(encoding="utf8")

NODE = r"""
"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const probe=fs.readFileSync(process.argv[1],"utf8");
const source=fs.readFileSync(process.argv[2],"utf8");
const readButton=(aria,title,disabled=false,ariaDisabled=false)=>({
  disabled,
  getAttribute(n){
    return n==="aria-label"?aria:n==="title"?title:
       n==="aria-disabled"?(ariaDisabled?"true":null):null;
  }
});
function inspect(origin,buttons){
  const scope={location:{origin},document:{querySelectorAll(q){
    assert.strictEqual(q,"button, [role='button']");
    return buttons;
  }}};
  return JSON.parse(JSON.stringify(vm.runInNewContext(probe,scope)));
}
const noMessage=(r)=>{
 assert.strictEqual(r.kind,"PROTON_READINESS_V1");
 assert.strictEqual(r.messageIdentityVerified,false);
 assert.strictEqual(r.canMutate,false);
 assert.deepStrictEqual(Object.keys(r).sort(),[
   "canMutate","kind","markReadCandidates","messageIdentityVerified","originOk"
 ].sort());
};
let r=inspect("https://evil.test",[readButton("Mark as read","")]);
assert.strictEqual(r.originOk,false);
assert.strictEqual(r.markReadCandidates,0);
noMessage(r);
r=inspect("https://mail.proton.me",[readButton("Mark as read","")]);
assert.strictEqual(r.originOk,true);
assert.strictEqual(r.markReadCandidates,1);
noMessage(r);
r=inspect("https://mail.proton.me",[readButton("","Mark as read")]);
assert.strictEqual(r.markReadCandidates,1);
r=inspect("https://mail.proton.me",[readButton("Mark as read","",true)]);
assert.strictEqual(r.markReadCandidates,0);
r=inspect("https://mail.proton.me",[readButton("Mark as read","",false,true)]);
assert.strictEqual(r.markReadCandidates,0);
r=inspect("https://mail.proton.me",[readButton("Move to trash",""),readButton("Mark as unread","")]);
assert.strictEqual(r.markReadCandidates,0);
r=inspect("https://mail.proton.me",[readButton("Mark as read",""),readButton("Mark as read","")]);
assert.strictEqual(r.markReadCandidates,2);
r=inspect("https://mail.proton.me",Array.from({length:600},()=>readButton("Archive","")));
assert.strictEqual(r.markReadCandidates,0);
async function background(family,goodTab=true) {
 const calls={native:0,scripting:0}, logs=[];
 const response={protocol:1,kind:"PONG",origin:"https://mail.proton.me",
   mailboxAccess:false,messageIdentityVerified:false,capabilities:[]};
 const api={
  action:{onClicked:{addListener(fn){api.click=fn}}},
  runtime:{lastError:null,sendNativeMessage(name,request,callback){
    calls.native++;
    assert.strictEqual(name,"org.postapollo.proton_mail");
    assert.deepStrictEqual(JSON.parse(JSON.stringify(request)),{protocol:1,kind:"PING"});
    if(family==="chromium")callback(response);else return Promise.resolve(response);
  }},
  scripting:{executeScript(options,callback){
    calls.scripting++;
    assert.deepStrictEqual(JSON.parse(JSON.stringify(options)),{
      target:{tabId:27},files:["readiness_probe.js"]
    });
    const results=[{result:inspect("https://mail.proton.me",[readButton("Mark as read","")])}];
    if(family==="chromium")callback(results);else return Promise.resolve(results);
  }}
 };
 const scope={URL,console:{info(s){logs.push(s)},warn(s){logs.push(s)}}};
 scope[family==="chromium"?"chrome":"browser"]=api;
 vm.runInNewContext(source,scope,{filename:"background.js"});
 api.click({id:27,url:goodTab?"https://mail.proton.me/u/0/inbox":"https://evil.test"});
 await Promise.resolve();await Promise.resolve();await Promise.resolve();
 assert.strictEqual(calls.native,goodTab?1:0);
 assert.strictEqual(calls.scripting,goodTab?1:0);
 assert.ok(!logs.some(m=>m.includes("Mark as read")||m.includes("https://evil.test")));
 if(goodTab)assert.ok(logs.some(m=>m.includes("identity NOT verified")));
}
(async()=>{
 for(const family of ["chromium","firefox"]){
   await background(family,true);
   await background(family,false);
 }
 console.log("Proton page readiness simulated browser checks: PASS");
})().catch(e=>{console.error(e);process.exit(1)});
"""
subprocess.run(["node", "-e", NODE, str(PROBE), str(BACKGROUND)], check=True)
print("Proton read-only Mark Read readiness: PASS")
