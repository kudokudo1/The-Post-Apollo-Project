import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {webcrypto} from "node:crypto";
import {sealSelectedSession} from "../../integrations/machine/brave-topology/session-seal.mjs";

function element(id=""){
  const handlers=new Map();
  return {
    id,value:"",disabled:false,textContent:"",children:[],
    addEventListener(type,fn){handlers.set(type,fn)},
    click(){return handlers.get("click")?.()},
    replaceChildren(...nodes){this.children=nodes}
  };
}
const byId=new Map();
for(const id of ["decrypt-read-once","forget-read","close-read-review",
  "read-record-id","read-passphrase","read-status","read-summary","read-tab-list"])
  byId.set(id,element(id));
const events=new Map();
let hidden=false,readCalls=0,tabReads=0;
const record="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const pass="SYNTHETIC PHRASING FOR ENCRYPTED SNAPSHOT REVIEW";
const token="TOPSECRETTESTVALUE";
const envelope=await sealSelectedSession({
  label:"MEDIA",passphrase:pass,includeSensitive:true,tabs:[
    {index:0,url:"https://radio.test/listen",pinned:true,wasActive:true},
    {index:3,url:"https://example.test/private?token="+token,
      pinned:false,wasActive:false}
  ]
},webcrypto);
globalThis.document={
  get hidden(){return hidden},
  getElementById(id){return byId.get(id)},
  createElement(tag){assert.equal(tag,"li");return element()},
  addEventListener(type,fn){events.set("document:"+type,fn)}
};
globalThis.window={
  addEventListener(type,fn){events.set("window:"+type,fn)}
};
globalThis.chrome={
  permissions:{
    async contains(arg){assert.deepEqual(arg,{permissions:["nativeMessaging"]});return true}
  },
  tabs:{
    async getCurrent(){tabReads++;return {id:200,windowId:30,incognito:false,active:true}},
    async remove(id){assert.equal(id,200)}
  },
  windows:{
    async get(id,opts){
      assert.equal(id,30);assert.deepEqual(opts,{populate:false});
      return {type:"normal",incognito:false,focused:true};
    }
  },
  runtime:{
    async sendNativeMessage(name,request){
      assert.equal(name,"org.postapollo.machine_brave_read_trial");
      assert.equal(request.record_id,record);
      assert.equal(request.operator_read_requested,true);
      assert.equal(JSON.stringify(request).includes(token),false);
      readCalls++;
      return {
        kind:"machine-brave-sealed-read-response-v1",
        status:"sealed_record_read",challenge:request.challenge,
        record_id:record,sha256:"a".repeat(64),envelope,
        ciphertext_authentication_verified:false,
        origin_authenticated:false,
        persistent_browser_window_binding_verified:false,
        restore_allowed:false,safe_actions:[]
      };
    }
  }
};
await import("../../integrations/machine/brave-topology/read-review.mjs");
const click=async id=>byId.get(id).click();
assert.equal(readCalls,0);
assert.equal(tabReads,0);
// Missing id and password do not reach native host.
await click("decrypt-read-once");
assert.equal(readCalls,0);
assert.match(byId.get("read-status").textContent,/REQUIRED/);
byId.get("read-record-id").value=record;
byId.get("read-passphrase").value="wrong but adequately long password";
await click("decrypt-read-once");
assert.equal(readCalls,1);
assert.match(byId.get("read-status").textContent,/REFUSED/);
assert.equal(byId.get("read-passphrase").value,"");
assert.equal(byId.get("read-tab-list").children.length,0);

// Correct password verifies locally and shows only hostname/position.
byId.get("read-passphrase").value=pass;
await click("decrypt-read-once");
assert.equal(readCalls,2);
assert.match(byId.get("read-status").textContent,/AES-GCM AUTHENTICATED/);
assert.match(byId.get("read-summary").textContent,/MEDIA \/\/ 2 TABS/);
assert.equal(byId.get("read-tab-list").children.length,2);
const visible=JSON.stringify({
  summary:byId.get("read-summary").textContent,
  nodes:byId.get("read-tab-list").children.map(x=>x.textContent)
});
for(const secret of [token,pass,"https://","/listen","/private","?token"]){
  assert.equal(visible.includes(secret),false,secret);
}
// No spontaneous second read after successful review.
await click("decrypt-read-once");
assert.equal(readCalls,2);
await click("forget-read");
assert.equal(byId.get("read-summary").textContent,"");
assert.equal(byId.get("read-tab-list").children.length,0);
assert.equal(byId.get("read-record-id").value,"");

// Focus loss invalidates visible results and old in-flight native replies.
byId.get("read-record-id").value=record;
byId.get("read-passphrase").value=pass;
await click("decrypt-read-once");
assert.equal(readCalls,3);
events.get("window:blur")();
assert.equal(byId.get("read-tab-list").children.length,0);
assert.match(byId.get("read-status").textContent,/FOCUS LOST/);

// Page teardown cannot preserve a decrypted preview.
hidden=true;events.get("document:visibilitychange")();
assert.equal(byId.get("read-tab-list").children.length,0);
events.get("window:pagehide")();
assert.equal(byId.get("read-tab-list").children.length,0);

const root="../../integrations/machine/brave-topology/";
const source=name=>readFileSync(new URL(root+name,import.meta.url),"utf8");
const page=source("read-review.mjs"),open=source("open-read-review.mjs");
const markup=source("read-review.html"),manifest=JSON.parse(source("manifest.json"));
assert.ok(open.includes('button.addEventListener("click",openReview)'));
assert.ok(open.includes('chrome.tabs.create({'));
assert.ok(page.includes("inspectSealedSnapshot(checked.envelope,passphrase)"));
assert.ok(page.includes('window.addEventListener("blur"'));
assert.ok(page.includes('list.replaceChildren(...nodes)'));
assert.ok(markup.includes("DECRYPT AND REVIEW ONCE"));
assert.deepEqual(manifest.permissions,[]);
assert.deepEqual(manifest.optional_permissions,["nativeMessaging","tabs"]);
assert.equal(manifest.incognito,"not_allowed");
assert.equal(Object.hasOwn(manifest,"background"),false);
for(const file of [page,open]){
  for(const forbidden of [
    "chrome.storage.","chrome.sessions.","chrome.windows.update(",
    "chrome.tabs.update(","chrome.tabs.query(","chrome.tabs.executeScript",
    "fetch(","XMLHttpRequest","localStorage","sessionStorage",
    "indexedDB","console.log(","console.error(","setTimeout(","setInterval("
  ]) assert.equal(file.includes(forbidden),false,forbidden);
}
console.log("MACHINE encrypted review UI: no auto-read, authenticated redaction and focus expiry PASS");
