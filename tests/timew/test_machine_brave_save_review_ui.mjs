import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const handlers=new Map();
function elem(id=""){
  const events=new Map();
  return {
    id,value:"",checked:false,disabled:false,textContent:"",children:[],
    type:"",append(...things){this.children.push(...things)},
    replaceChildren(...things){this.children=things},
    addEventListener(name,cb){events.set(name,cb)},
    click(){return events.get("click")?.()},
    change(){return events.get("change")?.()},
  };
}
const elems=new Map();
for(const id of [
  "load-save-tabs","save-sealed-tabs","close-save-review","save-tab-list",
  "allow-sensitive-save","save-window-label","save-passphrase",
  "save-passphrase-confirm","confirm-sealed-save","save-status","save-result"
])elems.set(id,elem(id));
elems.get("save-window-label").value="WORK";
let isHidden=false,focus=true,allowTabs=true,allowNative=true,tabReads=0,
  sendCalls=0,requestJSON="",deferWindow=false,windowResolve=null;
const allTabs=()=>[
  {id:201,index:0,incognito:false,windowId:101,active:false,pinned:true,
   url:"https://work.test/main"},
  {id:202,index:1,incognito:false,windowId:101,active:false,pinned:false,
   url:"https://accounts.test/auth?reset=TOPSECRET"},
  {id:203,index:2,incognito:false,windowId:101,active:false,pinned:false,
   url:"chrome://settings"},
  {id:999,index:3,incognito:false,windowId:101,active:true,pinned:false,
   url:"chrome-extension://anything/save-review.html"}
];
globalThis.document={
  get hidden(){return isHidden},
  getElementById(id){return elems.get(id)},
  createElement(){return elem()},
  addEventListener(type,fn){handlers.set("doc:"+type,fn)},
};
globalThis.window={
  addEventListener(type,fn){handlers.set("win:"+type,fn)}
};
globalThis.location={hash:"#101:201"};
globalThis.chrome={
  permissions:{
    async contains(arg){
      assert.equal(arg.permissions.length,1);
      if(arg.permissions[0]==="tabs")return allowTabs;
      if(arg.permissions[0]==="nativeMessaging")return allowNative;
      throw new Error("unknown permission");
    }
  },
  tabs:{
    async getCurrent(){return {id:999,windowId:101,active:true,incognito:false}},
    async remove(id){assert.equal(id,999)}
  },
  windows:{
    async get(id,arg){
      assert.equal(id,101);
      if(!arg.populate)return {id:101,type:"normal",incognito:false,focused:focus};
      tabReads++;
      if(deferWindow)return new Promise(resolve=>{windowResolve=resolve});
      return {id:101,type:"normal",incognito:false,focused:focus,tabs:allTabs()};
    }
  },
  runtime:{
    async sendNativeMessage(host,req){
      sendCalls++;
      assert.equal(host,"org.postapollo.machine_brave_save_trial");
      assert.equal(req.kind,"machine-brave-sealed-save-request-v1");
      assert.equal(req.operator_save_requested,true);
      requestJSON=JSON.stringify(req);
      for(const secret of ["TOPSECRET","https://","work.test","accounts.test",
                           "SYNTHETIC PASSPHRASE","WORK", "reset="])
        assert.equal(requestJSON.includes(secret),false,secret);
      return {
        kind:"machine-brave-sealed-save-response-v1",status:"sealed_record_saved",
        challenge:req.challenge,
        record_id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        sha256:"b".repeat(64),ciphertext_authentication_verified:false,
        origin_authenticated:false,
        persistent_browser_window_binding_verified:false,
        restore_allowed:false,safe_actions:[]
      };
    }
  }
};
await import("../../integrations/machine/brave-topology/save-review.mjs");
const click=async id=>elems.get(id).click();
assert.equal(tabReads,0);
assert.equal(sendCalls,0);
assert.equal(elems.get("save-sealed-tabs").disabled,true);
// Without both separately granted permissions, no browser URLs may be read.
allowTabs=false;
await click("load-save-tabs");
assert.equal(tabReads,0);
assert.match(elems.get("save-status").textContent,/WINDOW LOAD REFUSED/);
allowTabs=true;allowNative=false;
await click("load-save-tabs");
assert.equal(tabReads,0);
allowNative=true;
// Load current normal window once. No checkbox is automatically selected.
await click("load-save-tabs");
assert.equal(tabReads,1);
const rows=elems.get("save-tab-list").children;
assert.equal(rows.length,3);
const checkbox=i=>rows[i].children[0].children[0];
const text=i=>rows[i].children[0].children[1].textContent;
assert.match(text(0),/work.test/);
assert.match(text(1),/QUERY\/FRAGMENT REVIEW/);
assert.match(text(2),/EXCLUDED/);
assert.equal(checkbox(0).checked,false);
assert.equal(checkbox(1).disabled,true);
assert.equal(checkbox(2).disabled,true);
assert.equal(elems.get("save-sealed-tabs").disabled,false);
// Save with no selection must refuse even if password provided.
const pass="SYNTHETIC PASSPHRASE 1234567890";
elems.get("save-passphrase").value=pass;
elems.get("save-passphrase-confirm").value=pass;
elems.get("confirm-sealed-save").checked=true;
await click("save-sealed-tabs");
assert.equal(sendCalls,0);
// Explicitly select normal and query tabs; query needs separate opt in.
checkbox(0).checked=true;
checkbox(0).change();
elems.get("allow-sensitive-save").checked=true;
elems.get("allow-sensitive-save").change();
const rows2=elems.get("save-tab-list").children;
const queryBox=rows2[1].children[0].children[0];
assert.equal(queryBox.disabled,false);
queryBox.checked=true;queryBox.change();
elems.get("save-passphrase").value=pass;
elems.get("save-passphrase-confirm").value=pass;
await click("save-sealed-tabs");
assert.equal(sendCalls,1);
assert.equal(tabReads,2);
assert.match(elems.get("save-status").textContent,/ENCRYPTED SNAPSHOT STORED/);
assert.match(elems.get("save-result").textContent,/SEALED RECORD ID/);
assert.equal(elems.get("save-passphrase").value,"");
assert.equal(elems.get("save-passphrase-confirm").value,"");
assert.equal(elems.get("save-tab-list").children.length,0);
await click("save-sealed-tabs");
assert.equal(sendCalls,1,"must never save twice from the same review");

// Structural checks: no background, no browser storage, no URL IPC.
const base="../../integrations/machine/brave-topology/";
const src=name=>readFileSync(new URL(base+name,import.meta.url),"utf8");
const ui=src("save-review.mjs"),opener=src("open-save-review.mjs");
const html=src("save-review.html");
const manifest=JSON.parse(src("manifest.json"));
assert.ok(ui.includes('chrome.runtime.sendNativeMessage(SAVE_HOST,request)'));
assert.ok(ui.includes("const selected=[]"));
assert.ok(ui.includes("currentTab.url!==row.url"));
assert.ok(ui.includes("password.value=\"\""));
assert.ok(ui.includes('window.addEventListener("blur",invalidate)'));
assert.ok(ui.includes('window.addEventListener("pagehide"'));
assert.ok(ui.includes('document.addEventListener("visibilitychange"'));
assert.ok(opener.includes('button.addEventListener("click",openReview)'));
assert.ok(opener.includes('chrome.tabs.create({'));
assert.ok(opener.includes('chrome.permissions.contains({permissions:["tabs"]})'));
assert.ok(opener.includes('chrome.permissions.contains({permissions:["nativeMessaging"]})'));
assert.equal(html.includes("ENCRYPT AND SAVE CHECKED TABS ONCE"),true);
assert.deepEqual(manifest.permissions,[]);
assert.deepEqual(manifest.optional_permissions,["nativeMessaging","tabs"]);
assert.equal(manifest.incognito,"not_allowed");
assert.equal(Object.hasOwn(manifest,"background"),false);
for(const input of ["save-window-label","save-passphrase",
                    "save-passphrase-confirm","confirm-sealed-save"]){
  assert.ok(html.includes('id="'+input+'"'));
}
for(const source of [ui,opener]){
  for(const forbidden of [
    "chrome.storage.","localStorage","sessionStorage","indexedDB",
    "XMLHttpRequest","fetch(","console.log(","console.error(",
    "chrome.windows.update","chrome.windows.create",
    "setInterval(","setTimeout(","chrome.tabs.executeScript","eval("
  ])assert.equal(source.includes(forbidden),false,forbidden);
}
console.log("MACHINE browser selected-tab save: no-read-before-consent, explicit checks, sealed-only PASS");
