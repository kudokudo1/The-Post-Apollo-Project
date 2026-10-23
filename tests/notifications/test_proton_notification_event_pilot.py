#!/usr/bin/env python3
"""Click-only page Notification constructor pilot, simulated browser tests."""
from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/"integrations/proton/browser"
PROBE=DIRECTORY/"notification_event_pilot.js"
BACKGROUND=DIRECTORY/"background.js"
CHROMIUM=json.loads((DIRECTORY/"manifest.json").read_text())
FIREFOX=json.loads((DIRECTORY/"manifest.firefox.json").read_text())
probe=PROBE.read_text()
background=BACKGROUND.read_text()

for manifest in (CHROMIUM,FIREFOX):
    assert sorted(manifest["permissions"]) == ["activeTab","nativeMessaging","scripting"]
    assert "host_permissions" not in manifest
    assert "content_scripts" not in manifest
assert 'world: "MAIN"' in background
assert 'files: ["notification_event_pilot.js"]' in background
assert 'inspectNotificationEventPilot(tab);' in background
assert "messageIdentityVerified: false" in probe
assert "canMutate: false" in probe
assert 'location.origin !== "https://mail.proton.me"' in probe
assert "Reflect.construct(target, args, newTarget)" in probe
assert "setTimeout(() => state.finish" in probe
for forbidden in ("document.cookie", "localStorage", "sessionStorage",
                  "fetch(", "XMLHttpRequest", "sendNativeMessage",
                  "Notification.requestPermission(", "Notification.close(",
                  "navigator.serviceWorker", "JSON.stringify", "postMessage("):
    assert forbidden not in probe, forbidden
assert 'console.info("Post-Apollo Proton: event pilot stage="' in background

NODE=r"""
"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("assert");
const script=fs.readFileSync(process.argv[1],"utf8");
const background=fs.readFileSync(process.argv[2],"utf8");
const copy=value=>JSON.parse(JSON.stringify(value));
function makePage(origin="https://mail.proton.me", withConstructor=true) {
  const delivered=[], timers=[];
  class Original {
    constructor(title, options) {
      delivered.push({title,options});
      this.title=title;
    }
    static get permission() {return "granted";}
    static requestPermission() { return Promise.resolve("granted");}
  }
  const page={};
  if(withConstructor)page.Notification=Original;
  const scope={window:page,location:{origin},
    setTimeout(fn,delay){const id={fn,delay,cancelled:false};timers.push(id);return id;},
    clearTimeout(id){if(id) id.cancelled=true;},
    Object,Reflect,Number,Proxy};
  function click(){return copy(vm.runInNewContext(script,scope,{filename:"event-pilot.js"}));}
  return {page,Original,click,delivered,timers};
}
const keys=["kind","stage","originOk","attempts","capped","windowMs",
  "messageIdentityVerified","canMutate"].sort();
const verify=(result,stage)=>{
  assert.deepStrictEqual(Object.keys(result).sort(),keys);
  assert.strictEqual(result.kind,"PROTON_EVENT_PILOT_V1");
  assert.strictEqual(result.stage,stage);
  assert.strictEqual(result.messageIdentityVerified,false);
  assert.strictEqual(result.canMutate,false);
  assert.strictEqual(result.windowMs,90000);
  assert.ok(Number.isInteger(result.attempts) && result.attempts>=0 && result.attempts<=20);
  assert.strictEqual(typeof result.capped,"boolean");
};
let p=makePage();
verify(p.click(),"started");
assert.notStrictEqual(p.page.Notification,p.Original);
assert.strictEqual(p.page.Notification.permission,"granted");
assert.strictEqual(p.page.Notification.requestPermission instanceof Function,true);
const item=new p.page.Notification("SECRET_MESSAGE_SUBJECT",{tag:"PRIVATE-MAIL-ID"});
assert.strictEqual(item instanceof p.Original,true);
assert.strictEqual(p.delivered.length,1);
assert.strictEqual(p.delivered[0].title,"SECRET_MESSAGE_SUBJECT");
let result=p.click();
verify(result,"stopped");
assert.strictEqual(result.attempts,1);
assert.strictEqual(p.page.Notification,p.Original);
assert.strictEqual(p.timers[0].cancelled,true);
assert.ok(!JSON.stringify(result).includes("SECRET"));
assert.ok(!JSON.stringify(result).includes("PRIVATE"));
verify(p.click(),"started"); // new short-lived window after explicit click
p.timers[1].fn(); // deadline, auto stop and restore
assert.strictEqual(p.page.Notification,p.Original);
result=p.click();
verify(result,"expired");
assert.strictEqual(result.attempts,0);
assert.strictEqual(p.page.Notification,p.Original);
p=makePage();
verify(p.click(),"started");
for(let i=0;i<25;i++)new p.page.Notification("PRIVATE "+i);
result=p.click();
verify(result,"stopped");
assert.strictEqual(result.attempts,20);
assert.strictEqual(result.capped,true);
assert.strictEqual(p.delivered.length,25);
p=makePage("https://mail.proton.me.evil.test");
result=p.click();
verify(result,"wrong-origin");
assert.strictEqual(result.originOk,false);
assert.strictEqual(p.page.Notification,p.Original);
p=makePage("https://mail.proton.me",false);
verify(p.click(),"unavailable");
p=makePage();
Object.defineProperty(p.page,"Notification",{value:p.Original,
  writable:false,configurable:false});
verify(p.click(),"unavailable");
assert.strictEqual(p.page.Notification,p.Original);
p=makePage();
verify(p.click(),"started");
const Other=function LaterNotification(){};
p.page.Notification=Other;
p.timers[0].fn();
assert.strictEqual(p.page.Notification,Other,"must not clobber page's replacement");
result=p.click();
verify(result,"expired");
p=makePage();
p.page.__postApolloProtonNotificationCountV1__={owner:"imposter",attempts:0};
verify(p.click(),"unavailable");
assert.strictEqual(p.page.Notification,p.Original);

async function runFamily(family) {
  const infos=[],warnings=[],calls=[],listeners=[],page=makePage();
  const api={
    action:{onClicked:{addListener:fn=>listeners.push(fn)}},
    runtime:{lastError:null,sendNativeMessage(name,msg,cb) {
      calls.push({name,msg});
      const response={protocol:1,kind:"PONG",origin:"https://mail.proton.me",
        mailboxAccess:false,messageIdentityVerified:false,capabilities:[]};
      if(family==="chromium") cb(response);
      else return Promise.resolve(response);
    }},
    scripting:{executeScript(details,cb){
      calls.push({details});
      assert.strictEqual(details.target.tabId,11);
      let result;
      if(details.world==="MAIN") {
        assert.deepStrictEqual(copy(details.files),["notification_event_pilot.js"]);
        result=page.click();
      } else {
        assert.deepStrictEqual(copy(details.files),["readiness_probe.js"]);
        result={kind:"PROTON_READINESS_V4",originOk:true,
          inspectedControls:0,scanTruncated:false,exactReadEnabled:0,
          exactReadDisabled:0,otherReadLabels:0,toolbarReadEnabled:0,
          toolbarReadDisabled:0,toolbarUnreadEnabled:0,toolbarUnreadDisabled:0,
          unlabeledControls:0,checkedControls:0,selectedMailRows:0,
          selectedRowStructureOk:false,messageIdentityVerified:false,canMutate:false};
      }
      const response=[{frameId:0,result}];
      if(family==="chromium")cb(response);
      else return Promise.resolve(response);
    }}
  };
  const scope={URL,console:{info:x=>infos.push(x),warn:x=>warnings.push(x)}};
  scope[family==="firefox"?"browser":"chrome"]=api;
  vm.runInNewContext(background,scope,{filename:"background.js"});
  assert.strictEqual(listeners.length,1);
  listeners[0]({id:11,url:"https://evil.test/"});
  assert.strictEqual(calls.length,0);
  listeners[0]({id:11,url:"https://mail.proton.me/u/0/inbox"});
  await Promise.resolve();await Promise.resolve();
  assert.strictEqual(calls.length,3);
  assert.ok(infos.some(x=>x.includes("event pilot stage=started")));
  assert.ok(infos.some(x=>x.includes("identity NOT verified")));
  new page.page.Notification("VERY_PRIVATE_SUBJECT",{tag:"VERY_PRIVATE_ID"});
  listeners[0]({id:11,url:"https://mail.proton.me/u/0/inbox"});
  await Promise.resolve();await Promise.resolve();
  assert.strictEqual(calls.length,6);
  assert.ok(infos.some(x=>x.includes("event pilot stage=stopped attempts=1")));
  assert.strictEqual(page.page.Notification,page.Original);
  assert.ok(!infos.concat(warnings).some(x=>x.includes("VERY_PRIVATE")));
  assert.strictEqual(warnings.length,0);
}
(async()=>{
  await runFamily("chromium");
  await runFamily("firefox");
  console.log("Proton click-only web Notification event pilot: PASS");
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
subprocess.run(["node","-e",NODE,str(PROBE),str(BACKGROUND)],check=True)
print("Proton event-only companion pilot contracts: PASS")
