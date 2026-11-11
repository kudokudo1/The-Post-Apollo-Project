import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {sealSelectedSession} from "../../integrations/machine/brave-topology/session-seal.mjs";
import {inspectSealedSnapshot,validateSealedEnvelope} from
  "../../integrations/machine/brave-topology/session-unseal.mjs";
import {makeReadRequest,verifyReadReply,READ_HOST} from
  "../../integrations/machine/brave-topology/read-host-protocol.mjs";

const password="SYNTHETIC LONG PASSPHRASE ONLY FOR TEST";
const token="CONFIDENTIAL-TEST-TOKEN-099";
const tabs=[
  {index:1,url:"https://example.test/dashboard?token="+token,
    pinned:false,wasActive:false},
  {index:0,url:"https://radio.test/station",pinned:true,wasActive:true},
];
const sealed=await sealSelectedSession({
  label:"WORK",tabs,passphrase:password,includeSensitive:true
},webcrypto);
validateSealedEnvelope(sealed);
const reviewed=await inspectSealedSnapshot(sealed,password,webcrypto);
assert.equal(reviewed.status,"authenticated_redacted_review");
assert.equal(reviewed.window_label,"WORK");
assert.equal(reviewed.tab_count,2);
assert.equal(reviewed.pinned_count,1);
assert.equal(reviewed.sensitive_count,1);
assert.equal(reviewed.restore_allowed,false);
assert.equal(reviewed.browser_sway_identity_verified,false);
assert.deepEqual(reviewed.safe_actions,[]);
assert.deepEqual(reviewed.tabs.map(x=>[
  x.position,x.hostname,x.risk,x.pinned,x.was_active
]),[
  [0,"radio.test","candidate",true,true],
  [1,"example.test","sensitive",false,false]
]);
assert.equal(Object.isFrozen(reviewed.tabs),true);
assert.equal(Object.isFrozen(reviewed.tabs[0]),true);
const visible=JSON.stringify(reviewed);
for(const secret of [token,"https://","/station","dashboard","?token","ciphertext","passphrase"]){
  assert.equal(visible.includes(secret),false,secret);
}
const refuse=async (envelope,pass=password)=>assert.rejects(
  ()=>inspectSealedSnapshot(envelope,pass,webcrypto),
  {message:"SEALED SNAPSHOT REVIEW REFUSED"}
);
await refuse(sealed,"INCORRECT PASSPHRASE VALUE 0000");
await refuse({...sealed,nonce:"not-base64"});
await refuse({...sealed,version:2});
await refuse({...sealed,restore_allowed:true});
await refuse({...sealed,kdf:"UNKNOWN"});
await refuse({...sealed,iterations:0});
await refuse({...sealed,iterations:600000.5});
await refuse({...sealed,aad:"wrong"});
await refuse({...sealed,salt:"x"});
await refuse({...sealed,ciphertext:sealed.ciphertext.slice(1)});
const data=Buffer.from(sealed.ciphertext,"base64url");
data[0]^=1;
await refuse({...sealed,ciphertext:data.toString("base64url")});
const id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const challenge="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
assert.equal(READ_HOST,"org.postapollo.machine_brave_read_trial");
assert.deepEqual(makeReadRequest(challenge,id),{
  kind:"machine-brave-sealed-read-request-v1",challenge,
  record_id:id,operator_read_requested:true
});
assert.throws(()=>makeReadRequest(challenge,"../../session"),/REFUSED/);
const reply={
  kind:"machine-brave-sealed-read-response-v1",
  status:"sealed_record_read",challenge,record_id:id,
  sha256:"a".repeat(64),envelope:sealed,
  ciphertext_authentication_verified:false,
  origin_authenticated:false,
  persistent_browser_window_binding_verified:false,
  restore_allowed:false,safe_actions:[]
};
const verified=verifyReadReply(challenge,id,reply);
assert.deepEqual(verified,{envelope:sealed,sha256:"a".repeat(64),
                           restore_allowed:false,safe_actions:[]});
for(const wrong of [
  {...reply,challenge:id},{...reply,record_id:challenge},
  {...reply,restore_allowed:true},{...reply,origin_authenticated:true},
  {...reply,sha256:"bad"},{...reply,safe_actions:["open"]},
  {...reply,plaintext_urls:["https://bad.test"]},
  {...reply,envelope:{...sealed,url:"https://bad.test"}},
  {...reply,envelope:{...sealed,algorithm:"AES-CBC"}}
]){
  assert.throws(()=>verifyReadReply(challenge,id,wrong));
}
console.log("MACHINE sealed readback WebCrypto authentication, redacted-only review PASS");
