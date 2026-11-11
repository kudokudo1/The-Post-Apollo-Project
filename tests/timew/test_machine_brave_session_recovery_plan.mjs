import assert from "node:assert/strict";
import {
  SESSION_PLAN_KIND, MAX_SESSION_WINDOWS,
  MAX_SESSION_TABS_PER_WINDOW, MAX_SESSION_TOTAL_TABS,
  planSyntheticBraveSession, assessRestartPairing,
} from "../../integrations/machine/brave-topology/session-recovery-plan.mjs";

const tab=(index,url="https://example.test/path",extras={})=>({
  index, active:index===0, pinned:index===0, url, ...extras
});
const win=(operator_label,n,extra={})=>({
  operator_label, incognito:false, type:"normal",
  tabs:Array.from({length:n},(_,i)=>tab(i)),
  ...extra
});
const fixture=[
  win("WORK",2,{tabs:[
    tab(0,"https://example.test/dashboard?reset_token=SECRET123"),
    tab(1,"https://example.test/no-query"),
  ]}),
  win("MEDIA",5,{tabs:[
    tab(0,"https://music.test/"),
    tab(1,"chrome://extensions"),
    tab(2,"https://example.test/board#SECRET_FRAGMENT"),
    tab(3,"https://person:password@safe.test/"),
    tab(4,"file:///home/user/PRIVATE"),
  ]}),
  win("PERSONAL",6),
];
// Ignore private browsers *before* accessing any protected nested data.
const incognito={
  incognito:true, type:"normal",
  get tabs(){throw Error("PRIVATE TAB URL: NEVER READ")},
  get operator_label(){throw Error("PRIVATE LABEL: NEVER READ")},
};
const popup={
  incognito:false,type:"popup",
  get tabs(){throw Error("POPUP TAB URL: NEVER READ")},
  get operator_label(){throw Error("POPUP LABEL: NEVER READ")},
};
const before=structuredClone(fixture);
const result=planSyntheticBraveSession([...fixture,incognito,popup]);
assert.deepEqual(fixture,before);
assert.equal(result.kind,SESSION_PLAN_KIND);
assert.equal(result.status,"synthetic_preview_only");
assert.equal(result.browser_permission_requested,false);
assert.equal(result.private_windows_excluded,true);
assert.equal(result.user_tab_urls_exported,false);
assert.equal(result.titles_exported,false);
assert.equal(result.persistent_session_identity_verified,false);
assert.equal(result.browser_sway_binding_verified,false);
assert.equal(result.persisted,false);
assert.equal(result.restore_allowed,false);
assert.deepEqual(result.safe_actions,[]);
assert.deepEqual(result.counts,{
  normal_windows:3,tabs:13,candidate_only:8,
  requires_sensitive_review:2,not_eligible:3,
  private_windows_skipped:1
});
assert.deepEqual(result.windows.map(w=>[
  w.operator_label,w.tab_count,w.pinned_tab_count,w.active_tab_position
]),[["WORK",2,1,0],["MEDIA",5,1,0],["PERSONAL",6,1,0]]);
assert.deepEqual(result.windows[0].tab_eligibility,[
  {position:0,eligibility:"requires_sensitive_review"},
  {position:1,eligibility:"candidate_only"},
]);
assert.equal(result.windows[1].tab_eligibility[1].eligibility,"not_eligible");
assert.equal(result.windows[1].tab_eligibility[2].eligibility,"requires_sensitive_review");
assert.equal(result.windows[1].tab_eligibility[3].eligibility,"not_eligible");
assert.equal(Object.isFrozen(result),true);
assert.equal(Object.isFrozen(result.windows[0].tab_eligibility[0]),true);

const serialized=JSON.stringify(result);
for(const secret of [
  "https://", "http://", "chrome://", "file://",
  "SECRET", "password", "example.test", "music.test",
  "PRIVATE", '"url"', '"title"', '"sway_container_id"',
  '"temporary_browser_window_id"', '"cookie"', '"profile"',
]){
  assert.equal(serialized.includes(secret),false,secret);
}
const comparison=assessRestartPairing(result,[2,5,6]);
assert.equal(comparison.status,"manual_pairing_required");
assert.equal(comparison.saved_window_slots,3);
assert.equal(comparison.observed_window_slots,3);
assert.equal(comparison.count_signature_may_repeat,true);
assert.equal(comparison.persistent_session_identity_verified,false);
assert.equal(comparison.browser_sway_binding_verified,false);
assert.equal(comparison.session_restorable,false);
assert.equal(comparison.restore_allowed,false);
assert.deepEqual(comparison.safe_actions,[]);
assert.equal(JSON.stringify(comparison).includes("SECRET"),false);
assert.equal(Object.isFrozen(comparison),true);
// Even identical count signatures do not authorize matching across restarts.
assert.deepEqual(assessRestartPairing(result,[2,5,6]).safe_actions,[]);
assert.deepEqual(assessRestartPairing(result,[6,2,5]).safe_actions,[]);
assert.deepEqual(assessRestartPairing(result,[]).safe_actions,[]);

// Refuse malformed fixture structures, ambiguous identity hints, tab overflows.
const refuse=value=>assert.throws(
  ()=>planSyntheticBraveSession(value),
  error=>error?.message==="SESSION RECOVERY PREVIEW REFUSED");
refuse(null);
refuse({});
refuse([null]);
refuse([win("WORK",1),win("work",1)]);
refuse([win("BAD://LABEL",1)]);
refuse([win("A",1,{incognito:null})]);
refuse([win("A",2,{tabs:[tab(0),tab(0)]})]);
refuse([win("A",2,{tabs:[
  tab(0,"https://a.test/"),tab(1,"https://b.test/",{active:true})
]})]);
refuse([win("A",1,{tabs:[tab(-1)]})]);
refuse([win("A",1,{tabs:[tab(0,"https://a.test/",{active:"yes"})]})]);
refuse([win("A",1,{tabs:[tab(0,"https://a.test/",{pinned:"yes"})]})]);
refuse([win("A",1,{tabs:[tab(0,"https://a.test/",{incognito:true})]})]);
refuse([win("A",MAX_SESSION_TABS_PER_WINDOW+1)]);
refuse(Array.from({length:MAX_SESSION_WINDOWS+1},(_,i)=>win("G"+i,0)));
refuse(Array.from({length:5},(_,i)=>win("G"+i,MAX_SESSION_TABS_PER_WINDOW)));
// An adversarial URL property must not be echoed in error messages.
refuse([win("A",1,{tabs:[{
  index:0,active:true,pinned:false,
  get url(){throw Error("MY PRIVATE TAB STRING")}
}]})]);
// Unsupported/invalid tab addresses become redacted position statuses,
// not a leak or implicit permission to save URLs.
for(const addr of [
  null,123,"", "javascript:alert(1)", "data:text/html,SECRET",
  "https://a.test/"+"x".repeat(4097),
  "https://user:pw@secret.test/",
  "https://test.test/#TOKEN",
]) {
  const x=planSyntheticBraveSession([win("A",1,{tabs:[tab(0,addr)]})]);
  assert.equal(x.windows[0].tab_eligibility[0].eligibility,
    typeof addr==="string" && addr.includes("#TOKEN")
      ? "requires_sensitive_review" : "not_eligible");
  assert.deepEqual(x.safe_actions,[]);
}
assert.throws(()=>assessRestartPairing(result,[-1]),/SESSION RECOVERY PREVIEW REFUSED/);
assert.throws(()=>assessRestartPairing({...result,restore_allowed:true},[2]),/SESSION RECOVERY PREVIEW REFUSED/);
assert.throws(()=>assessRestartPairing(result,Array(MAX_SESSION_WINDOWS+1).fill(1)),/SESSION RECOVERY PREVIEW REFUSED/);
console.log("MACHINE synthetic Brave 2 // 5 // 6 restart plan, redaction, no pairing // PASS");
