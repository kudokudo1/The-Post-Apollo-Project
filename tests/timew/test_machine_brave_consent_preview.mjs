import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const handlers = new Map();
function element(id="") {
  const listeners = new Map();
  return {
    id,disabled:false,textContent:"",children:[],
    addEventListener(name,fn){listeners.set(name,fn)},
    click(){return listeners.get("click")()},
    replaceChildren(...values){this.children=values},
  };
}
const ids=new Map();
for(const id of [
  "grant-tabs","preview-tabs","revoke-tabs","tab-preview-status",
  "tab-preview-summary","tab-preview-list"
])ids.set(id,element(id));
const previewList=ids.get("tab-preview-list");
globalThis.document={
  getElementById(id){return ids.get(id)},
  createElement(tag){assert.equal(tag,"li");return element("list-item")},
};
globalThis.window={
  addEventListener(event,callback){handlers.set(event,callback)}
};
let granted=false,willGrant=true,lookups=0,requestCalls=0,revokeCalls=0,
    currentCalls=0,permissionQueries=0,normal=true,incognito=false,
    deferWindow=false,windowResolve=null;
const snapshot=()=>({
  id:109,type:"normal",incognito:false,
  tabs:[
    {index:0,active:true,pinned:true,incognito:false,
      url:"https://private.test/normal"},
    {index:1,active:false,pinned:false,incognito:false,
      url:"https://accounts.test/reset?TOKEN=TOPSECRET"},
    {index:2,active:false,pinned:false,incognito:false,
      url:"chrome://extensions"}
  ]
});
globalThis.chrome={
  permissions:{
    async contains(o){
      assert.deepEqual(o,{permissions:["tabs"]});
      permissionQueries++;
      return granted;
    },
    async request(o){
      assert.deepEqual(o,{permissions:["tabs"]});
      requestCalls++;
      if(willGrant)granted=true;
      return willGrant;
    },
    async remove(o){
      assert.deepEqual(o,{permissions:["tabs"]});
      revokeCalls++;
      const before=granted;granted=false;
      return before;
    }
  },
  windows:{
    async getCurrent(arg){
      assert.deepEqual(arg,{populate:false});
      currentCalls++;
      return {id:109,type:normal?"normal":"popup",incognito};
    },
    async get(id,arg){
      assert.equal(id,109);assert.deepEqual(arg,{populate:true});
      lookups++;
      if(deferWindow) return new Promise(resolve=>{windowResolve=resolve});
      return snapshot();
    }
  }
};
await import("../../integrations/machine/brave-topology/session-preview-ui.mjs");
const click=async id=>ids.get(id).click();
for(let k=0;k<8;k++)await Promise.resolve();
assert.equal(lookups,0,"import must not read tabs");
assert.equal(requestCalls,0,"import must not prompt permission");
assert.equal(granted,false);
assert.match(ids.get("tab-preview-status").textContent,/NOT GRANTED/);

// Preview cannot acquire tabs permission and cannot read without permission.
await click("preview-tabs");
assert.match(ids.get("tab-preview-status").textContent,/TAB ACCESS REQUIRED/);
assert.equal(lookups,0);
assert.equal(requestCalls,0);

// Explicit permission prompt alone never reads browser addresses.
willGrant=false;
await click("grant-tabs");
assert.equal(requestCalls,1);
assert.equal(granted,false);
assert.equal(lookups,0);
assert.match(ids.get("tab-preview-status").textContent,/DECLINED/);
willGrant=true;
await click("grant-tabs");
assert.equal(requestCalls,2);
assert.equal(granted,true);
assert.equal(lookups,0);
assert.match(ids.get("tab-preview-status").textContent,/CLICK PREVIEW SEPARATELY/);

// Only the current normal non-private window gets read once.
await click("preview-tabs");
assert.equal(lookups,1);
assert.ok(currentCalls>=2);
assert.equal(ids.get("tab-preview-summary").textContent,
  "3 TABS // 1 CANDIDATE // 1 REVIEW // 1 EXCLUDED");
assert.deepEqual(previewList.children.map(n=>n.textContent),[
  "TAB 1 // CANDIDATE ONLY",
  "TAB 2 // REQUIRES SENSITIVE REVIEW",
  "TAB 3 // NOT ELIGIBLE"
]);
assert.match(ids.get("tab-preview-status").textContent,/MEMORY ONLY/);
const display=JSON.stringify([
  ids.get("tab-preview-summary").textContent,
  previewList.children.map(n=>n.textContent),
  ids.get("tab-preview-status").textContent
]);
for(const secret of ["TOPSECRET","https://","private.test","accounts.test",
                     "chrome://","reset?TOKEN","title","favicon"]){
  assert.equal(display.includes(secret),false,secret);
}

// Private/popup failure before populate:true, with no sensitive payload
incognito=true;
await click("preview-tabs");
assert.equal(lookups,1);
assert.equal(previewList.children.length,0);
assert.match(ids.get("tab-preview-status").textContent,/PREVIEW REFUSED/);
incognito=false;normal=false;
await click("preview-tabs");
assert.equal(lookups,1);
assert.equal(previewList.children.length,0);
normal=true;

// Switching windows while the asynchronous snapshot is pending aborts render.
deferWindow=true;windowResolve=null;
const pending=click("preview-tabs");
for(let k=0;k<20&&!windowResolve;k++)await Promise.resolve();
assert.equal(typeof windowResolve,"function");
handlers.get("blur")();
assert.equal(previewList.children.length,0);
assert.match(ids.get("tab-preview-status").textContent,/FOCUS LOSS/);
windowResolve(snapshot());
await pending;
assert.equal(previewList.children.length,0);
deferWindow=false;windowResolve=null;

// Revoke only active permission; clear both summary and list immediately.
await click("preview-tabs");
assert.equal(previewList.children.length,3);
await click("revoke-tabs");
assert.equal(granted,false);
assert.equal(revokeCalls,1);
assert.equal(previewList.children.length,0);
assert.equal(ids.get("tab-preview-summary").textContent,"");
assert.match(ids.get("tab-preview-status").textContent,/ACTIVE TAB ACCESS REVOKED/);
const lookedUp=lookups;
await click("preview-tabs");
assert.equal(lookups,lookedUp);

// Page teardown drops any on-screen preview and does not store data.
handlers.get("pagehide")();
assert.equal(previewList.children.length,0);
assert.equal(ids.get("tab-preview-summary").textContent,"");

// Source contracts: no background observers, storage or native export.
const root="../../integrations/machine/brave-topology/";
const src=readFileSync(new URL(root+"session-preview-ui.mjs",import.meta.url),"utf8");
const html=readFileSync(new URL(root+"popup.html",import.meta.url),"utf8");
const manifest=JSON.parse(readFileSync(new URL(root+"manifest.json",import.meta.url)));
assert.ok(src.includes("chrome.permissions.request(ACCESS)"));
assert.ok(src.includes('chrome.permissions.remove(ACCESS)'));
assert.ok(src.includes('chrome.windows.get(selected.id, {populate:true})'));
assert.ok(src.includes('planSyntheticBraveSession(['));
assert.ok(src.includes('rowText("TAB "'));
assert.ok(src.includes('window.addEventListener("pagehide"'));
assert.ok(src.includes('window.addEventListener("blur"'));
assert.deepEqual(manifest.permissions,[]);
assert.deepEqual(manifest.host_permissions,[]);
assert.deepEqual(manifest.optional_permissions,["nativeMessaging","tabs"]);
assert.equal(manifest.incognito,"not_allowed");
assert.equal(Object.hasOwn(manifest,"background"),false);
for(const k of ["grant-tabs","preview-tabs","revoke-tabs","tab-preview-status",
                "tab-preview-summary","tab-preview-list"]) {
  assert.ok(html.includes('id="'+k+'"'));
}
assert.ok(html.includes('src="session-preview-ui.mjs"'));
for(const dangerous of [
  "chrome.storage.", "chrome.sessions.", "chrome.tabs.query(",
  "chrome.tabs.create(", "chrome.windows.update(", "chrome.windows.create(",
  "chrome.runtime.sendNativeMessage(", "fetch(", "XMLHttpRequest", "WebSocket",
  "localStorage","sessionStorage","indexedDB","console.log(", "console.error(",
  "navigator.clipboard", "innerHTML", "JSON.stringify(","setInterval(",
  "setTimeout(", "restore("
])assert.equal(src.includes(dangerous),false,dangerous);
console.log("MACHINE opt-in current-window tab preview // denied, grant, redacted, revoke, stale PASS");
