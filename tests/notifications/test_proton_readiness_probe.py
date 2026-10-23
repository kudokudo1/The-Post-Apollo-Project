#!/usr/bin/env python3
"""Read-only Proton UI count diagnostics, including offline browser families."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "integrations/proton/browser"
PROBE = DIRECTORY / "readiness_probe.js"
BACKGROUND = DIRECTORY / "background.js"

probe = PROBE.read_text(encoding="utf8")
background = BACKGROUND.read_text(encoding="utf8")
for forbidden in ("textContent", "innerHTML", "outerHTML", "localStorage",
                  "sessionStorage", "document.cookie", "fetch(", "XMLHttpRequest",
                  "getAttribute('href')", 'getAttribute("href")',
                  ".click(", "mailboxAccess: true", "canMutate: true"):
    assert forbidden not in probe, f"Forbidden in page probe: {forbidden}"
assert "document.querySelectorAll" in probe
assert '"PROTON_READINESS_V4"' in probe
assert "messageIdentityVerified: false" in probe
assert "canMutate: false" in probe
assert "querySelectorAll" not in background

NODE = r"""
"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const probe=fs.readFileSync(process.argv[1],"utf8");
const source=fs.readFileSync(process.argv[2],"utf8");
const button=(aria,title,disabled=false,ariaDisabled=false,testid=null)=>({
  disabled,getAttribute(name){
    if(name==="aria-label")return aria;
    if(name==="title")return title;
    if(name==="aria-disabled")return ariaDisabled?"true":null;
    if(name==="data-testid")return testid;
    return null;
  }
});
function mailRow(checkboxID, rowID) {
  return {
    getAttribute(name){return name==="data-item-id"?checkboxID:null;},
    closest(selector){
      assert.strictEqual(selector,"[data-element-id]");
      return rowID===null?null:{
        getAttribute(name){return name==="data-element-id"?rowID:null;}
      };
    }
  };
}
function runProbe(origin,buttons=[],checked=0,mailRows=[]){
  const scope={location:{origin},document:{querySelectorAll(query){
    if(query==="button, [role='button']")return buttons;
    if(query==="input[type='checkbox'][data-testid='item-checkbox']:checked")
      return mailRows;
    assert.strictEqual(query,
      "input[type='checkbox']:checked, [role='checkbox'][aria-checked='true']");
    return Array.from({length:checked},()=>({}));
  }}};
  return JSON.parse(JSON.stringify(vm.runInNewContext(probe,scope)));
}
const expectedKeys=[
 "kind","originOk","inspectedControls","scanTruncated",
 "exactReadEnabled","exactReadDisabled","otherReadLabels",
 "unlabeledControls","checkedControls","messageIdentityVerified","canMutate",
 "toolbarReadEnabled","toolbarReadDisabled","toolbarUnreadEnabled",
 "toolbarUnreadDisabled","selectedMailRows","selectedRowStructureOk"
].sort();
function checkPrivacy(result){
 assert.deepStrictEqual(Object.keys(result).sort(),expectedKeys);
 assert.strictEqual(result.kind,"PROTON_READINESS_V4");
 assert.strictEqual(result.messageIdentityVerified,false);
 assert.strictEqual(result.canMutate,false);
 assert.strictEqual(typeof result.selectedRowStructureOk,"boolean");
 for(const value of Object.values(result))assert.ok(
  typeof value==="boolean"||typeof value==="number"||value==="PROTON_READINESS_V4");
}
let r=runProbe("https://evil.test",[button("Mark as read","")],3);
checkPrivacy(r);
assert.strictEqual(r.originOk,false);
assert.strictEqual(r.exactReadEnabled,0);
assert.strictEqual(r.toolbarReadEnabled,0);
assert.strictEqual(r.selectedMailRows,0);
r=runProbe("https://mail.proton.me");
checkPrivacy(r);
assert.strictEqual(r.inspectedControls,0);
assert.strictEqual(r.exactReadEnabled,0);
r=runProbe("https://mail.proton.me",[
 button("Mark as read",""),button("Mark as read",""),
 button("Mark as read","",true),button("Mark as read","",false,true),
 button("Mark read",""),button("Mark as unread",""),button(null,null),
 button(null,"Archive"),
 button(null,null,false,false,"toolbar:read"),
 button(null,null,true,false,"toolbar:read"),
 button(null,null,false,false,"toolbar:unread"),
 button(null,null,false,true,"toolbar:unread")
],2);
checkPrivacy(r);
assert.strictEqual(r.inspectedControls,12);
assert.strictEqual(r.toolbarReadEnabled,1);
assert.strictEqual(r.toolbarReadDisabled,1);
assert.strictEqual(r.toolbarUnreadEnabled,1);
assert.strictEqual(r.toolbarUnreadDisabled,1);
assert.strictEqual(r.exactReadEnabled,2);
assert.strictEqual(r.exactReadDisabled,2);
assert.strictEqual(r.otherReadLabels,2);
assert.strictEqual(r.unlabeledControls,5);
assert.strictEqual(r.checkedControls,2);
assert.strictEqual(r.selectedMailRows,0);
assert.strictEqual(r.selectedRowStructureOk,false);
// Page-level checkbox count is NOT the number of mail rows. Only matching
// native checked item-checkboxes under their owning data-element-id qualify.
r=runProbe("https://mail.proton.me",[],3,[mailRow("opaque-row-1","opaque-row-1")]);
checkPrivacy(r);
assert.strictEqual(r.checkedControls,3);
assert.strictEqual(r.selectedMailRows,1);
assert.strictEqual(r.selectedRowStructureOk,true);
r=runProbe("https://mail.proton.me",[],2,[mailRow("row-a","row-b")]);
assert.strictEqual(r.selectedMailRows,1);
assert.strictEqual(r.selectedRowStructureOk,false);
r=runProbe("https://mail.proton.me",[],2,[
  mailRow("row-a","row-a"),mailRow("row-b","row-b")]);
assert.strictEqual(r.selectedMailRows,2);
assert.strictEqual(r.selectedRowStructureOk,false);
r=runProbe("https://mail.proton.me",[],2,[mailRow("","")]);
assert.strictEqual(r.selectedRowStructureOk,false);
r=runProbe("https://mail.proton.me",[],2,[mailRow("row-a",null)]);
assert.strictEqual(r.selectedRowStructureOk,false);

r=runProbe("https://mail.proton.me",[
 button("  MARK  AS  READ ",""),button("","Mark as read"),
 button("Mark as read on Message 123","")
],40);
assert.strictEqual(r.exactReadEnabled,2);
assert.strictEqual(r.otherReadLabels,1);
assert.strictEqual(r.checkedControls,20);
r=runProbe("https://mail.proton.me",Array.from({length:600},()=>button(null,null)));
assert.strictEqual(r.inspectedControls,500);
assert.strictEqual(r.unlabeledControls,500);
assert.strictEqual(r.scanTruncated,true);

async function runBackground(family,validTab=true,nativeError=false,counts){
 const calls={native:0,probe:0,event:0},log=[];
 const result=counts||runProbe("https://mail.proton.me",[
   button(null,null,false,false,"toolbar:read"),
   button(null,null,false,false,"toolbar:unread")],1);
 const safe={protocol:1,kind:"PONG",origin:"https://mail.proton.me",
   mailboxAccess:false,messageIdentityVerified:false,capabilities:[]};
 const api={
  action:{onClicked:{addListener(f){api.click=f}}},
  runtime:{lastError:null,sendNativeMessage(name,request,callback){
   calls.native++;
   assert.strictEqual(name,"org.postapollo.proton_mail");
   assert.deepStrictEqual(JSON.parse(JSON.stringify(request)),
       {protocol:1,kind:"PING"});
   if(family==="chromium"){
     if(nativeError)api.runtime.lastError={message:"offline PRIVATE"};
     callback(nativeError?undefined:safe);
     api.runtime.lastError=null;
   }else return nativeError?Promise.reject(new Error("offline PRIVATE")):
                              Promise.resolve(safe);
  }},
  scripting:{executeScript(options,callback){
   const details=JSON.parse(JSON.stringify(options));
   if(details.world==="MAIN") {
     calls.event++;
     assert.deepStrictEqual(details,
       {target:{tabId:27},files:["notification_event_pilot.js"],world:"MAIN"});
     const event={kind:"PROTON_EVENT_PILOT_V1",stage:"started",
       originOk:true,attempts:0,capped:false,windowMs:90000,
       messageIdentityVerified:false,canMutate:false};
     if(family==="chromium")callback([{result:event}]);
     else return Promise.resolve([{result:event}]);
   } else {
     calls.probe++;
     assert.deepStrictEqual(details,
       {target:{tabId:27},files:["readiness_probe.js"]});
     if(family==="chromium")callback([{result}]);
     else return Promise.resolve([{result}]);
   }
  }}
 };
 const scope={URL,console:{info:(s)=>log.push(s),warn:(s)=>log.push(s)}};
 scope[family==="chromium"?"chrome":"browser"]=api;
 vm.runInNewContext(source,scope,{filename:"background.js"});
 api.click({id:27,url:validTab?"https://mail.proton.me/u/0/inbox":"https://evil.test"});
 await Promise.resolve();await Promise.resolve();await Promise.resolve();
 assert.strictEqual(calls.probe,validTab?1:0);
 assert.strictEqual(calls.event,validTab?1:0);
 assert.strictEqual(calls.native,validTab?1:0);
 assert.ok(!log.some(s=>s.includes("PRIVATE")||s.includes("Message 123")
   ||s.includes("secret-private-id")));
 if(validTab){
   assert.ok(log.some(s=>s.includes("exactEnabled="+result.exactReadEnabled)));
   assert.ok(log.some(s=>s.includes("checkedControls="+result.checkedControls)));
   assert.ok(log.some(s=>s.includes("selectedMailRows="+result.selectedMailRows)));
   assert.ok(log.some(s=>s.includes("selectedRowStructureOk="+result.selectedRowStructureOk)));
   assert.ok(log.some(s=>s.includes("toolbarReadEnabled="+result.toolbarReadEnabled)));
   assert.ok(log.some(s=>s.includes("toolbarUnreadEnabled="+result.toolbarUnreadEnabled)));
   assert.ok(log.some(s=>s.includes("identity NOT verified")));
 }
}
(async()=>{
 for(const browser of ["chromium","firefox"]){
   await runBackground(browser);
   await runBackground(browser,true,true);
   await runBackground(browser,false);
   await runBackground(browser,true,false,runProbe("https://mail.proton.me"));
   await runBackground(browser,true,false,runProbe(
     "https://mail.proton.me",[],3,[mailRow("secret-private-id","secret-private-id")]));
 }
 console.log("Proton private UI counts and shared browser mocks: PASS");
})().catch(e=>{console.error(e);process.exit(1)});
"""
subprocess.run(["node", "-e", NODE, str(PROBE), str(BACKGROUND)], check=True)
print("Proton read-only readiness diagnostics: PASS")
