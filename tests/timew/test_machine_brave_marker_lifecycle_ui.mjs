import assert from "node:assert/strict";

const uuid="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const byId=new Map();
const events=new Map();
const button=id=>{
  const listeners=new Map();
  const item={
    id,textContent:"",disabled:false,
    addEventListener(type,callback){listeners.set(type,callback)},
    click(){return listeners.get("click")()},
  };
  byId.set(id,item);
  return item;
};
const status=button("status");
status.textContent="READY // NO OBSERVATION YET"; // Initial HTML text, before module load
const verify=button("verify-marker");
const close=button("close-marker");

let hidden=false,focused=true,active=true,conId=81;
let nativeCall=null,removed=[];
globalThis.document={
  title:"",getElementById(id){return byId.get(id)},
  get hidden(){return hidden},
  addEventListener(type,callback){events.set("document:"+type,callback)}
};
globalThis.window={
  addEventListener(type,callback){events.set("window:"+type,callback)}
};
globalThis.location={hash:"#"+uuid};
const reply=()=>({
  kind:"machine-brave-marker-observe-response-v1",
  status:"transient_title_marker_observed",
  challenge:uuid,read_only_host:true,
  marker_unique_and_stable:true,sway_container_id:conId,
  output:"DP-3",workspace:"1",browser_window_id:null,
  extension_origin_authenticated:false,
  host_private_window_exclusion_verified:false,
  persistent_window_identity_verified:false,
  session_capture_allowed:false,restore_allowed:false,safe_actions:[],
});
globalThis.chrome={
  tabs:{
    async getCurrent(){return {id:17,windowId:201,active,incognito:false}},
    async remove(id){removed.push(id)}
  },
  windows:{
    async get(id){
      assert.equal(id,201);
      return {type:"normal",incognito:false,focused};
    }
  },
  permissions:{
    async contains({permissions}){
      assert.deepEqual(permissions,["nativeMessaging"]);
      return true;
    }
  },
  runtime:{
    async sendNativeMessage(name,request){
      assert.equal(name,"org.postapollo.machine_brave_title_marker");
      assert.equal(request.challenge,uuid);
      return nativeCall ? nativeCall() : reply();
    }
  }
};

await import("../../integrations/machine/brave-topology/marker.mjs");
assert.equal(document.title,"MACHINE WINDOW CHECK "+uuid);
assert.equal(verify.disabled,false);
assert.equal(status.textContent,"READY // NO OBSERVATION YET");

// First and same-context explicit recheck.
await verify.click();
assert.match(status.textContent,/TITLE MARKER MATCHED \/\/ TEMPORARY \/\/ NO RESTORE/);
assert.match(status.textContent,/IN MEMORY ONLY/);
await verify.click();
assert.match(status.textContent,/TITLE MARKER MATCHED/);

// A changed Sway container cannot silently replace an existing candidate.
conId=82;
await verify.click();
assert.match(status.textContent,/WINDOW ASSOCIATION CHANGED \/\/ REVOKED/);
await verify.click();
assert.match(status.textContent,/SWAY CON 82/);

// Leaving the browser focus immediately invalidates the displayed candidate.
focused=false;
events.get("window:blur")();
assert.match(status.textContent,/WINDOW FOCUS LOST \/\/ CANDIDATE EXPIRED/);
focused=true;
await verify.click();
assert.match(status.textContent,/TITLE MARKER MATCHED/);

// Browser tab hiding discards a match and requires another user click.
hidden=true;active=false;
events.get("document:visibilitychange")();
assert.match(status.textContent,/TEST TAB HIDDEN \/\/ CANDIDATE EXPIRED/);
hidden=false;active=true;
await verify.click();
assert.match(status.textContent,/TITLE MARKER MATCHED/);

// A stale native reply after focus loss MUST NOT resurrect the match.
let deliver;
nativeCall=()=>new Promise(resolve=>{deliver=resolve});
const checking=verify.click();
for(let i=0;i<20 && !deliver;i++) await Promise.resolve();
assert.equal(typeof deliver,"function");
events.get("window:blur")();
deliver(reply());
await checking;
assert.match(status.textContent,/CANDIDATE EXPIRED/);
assert.doesNotMatch(status.textContent,/TITLE MARKER MATCHED/);
nativeCall=null;

// Reopening after the focus loss requires a new explicit check.
await verify.click();
assert.match(status.textContent,/TITLE MARKER MATCHED/);

// The close control only closes its own temporary tab, revoking first.
await close.click();
assert.deepEqual(removed,[17]);
events.get("window:pagehide")();
assert.equal(verify.disabled,false);

console.log("MACHINE marker UI: success/recheck/change/blur/hide/stale/close PASS");
