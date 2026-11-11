import assert from "node:assert/strict";
import {webcrypto,pbkdf2Sync,createDecipheriv} from "node:crypto";
import {
  sealSelectedSession,classifySelectableUrl,SEALED_KIND,
  PBKDF2_ITERATIONS,MAX_SELECTED_TABS
} from "../../integrations/machine/brave-topology/session-seal.mjs";
import {makeSealedSaveRequest,checkSealedSaveResponse,SAVE_HOST} from
  "../../integrations/machine/brave-topology/save-host-protocol.mjs";

const password="SYNTHETIC PASSPHRASE NOT A USER SECRET";
const TOKEN="TEST-QUERY-SECRET-12345";
const selected=[
  {index:5,url:"https://example.test/board?auth="+TOKEN,
   pinned:false,wasActive:false},
  {index:2,url:"https://radio.test/listen",pinned:true,wasActive:true},
];
assert.equal(classifySelectableUrl(selected[0].url),"sensitive");
assert.equal(classifySelectableUrl(selected[1].url),"candidate");
assert.equal(classifySelectableUrl("chrome://extensions"),"excluded");
assert.equal(classifySelectableUrl("file:///home/user/private"),"excluded");
assert.equal(classifySelectableUrl("https://user:password@example.test/"),"excluded");
const bad=(opts)=>assert.rejects(
  ()=>sealSelectedSession({label:"WORK",tabs:selected,passphrase:password,...opts},webcrypto),
  {message:"SEALED SESSION REFUSED"}
);
await bad({includeSensitive:false});
await bad({label:"../../TRAVERSAL",includeSensitive:true});
await bad({passphrase:"short",includeSensitive:true});
await bad({tabs:[],includeSensitive:true});
await bad({tabs:[selected[0],selected[0]],includeSensitive:true});
await bad({tabs:[selected[0],{...selected[1],wasActive:true},
                 {...selected[0],index:8,wasActive:true}],includeSensitive:true});
await bad({tabs:[{...selected[1],url:"chrome://settings"}],includeSensitive:true});
await bad({tabs:[{...selected[1],extra:"secret"}],includeSensitive:true});
await bad({tabs:Array.from({length:MAX_SELECTED_TABS+1},(_,i)=>({
  index:i,url:"https://example.test/"+i,pinned:false,wasActive:false
}))});
const props={label:"WORK",tabs:selected,passphrase:password,includeSensitive:true};
const a=await sealSelectedSession(props,webcrypto);
const b=await sealSelectedSession(props,webcrypto);
assert.equal(a.kind,SEALED_KIND);
assert.equal(a.version,1);
assert.equal(a.algorithm,"AES-256-GCM");
assert.equal(a.kdf,"PBKDF2-HMAC-SHA256");
assert.equal(a.iterations,PBKDF2_ITERATIONS);
assert.equal(a.aad,SEALED_KIND);
assert.notEqual(a.nonce,b.nonce);
assert.notEqual(a.salt,b.salt);
assert.notEqual(a.ciphertext,b.ciphertext);
const serialized=JSON.stringify(a);
for(const secret of [password,TOKEN,"https://","example.test","radio.test",
                     "source_position","WORK","tabs"]){
  assert.equal(serialized.includes(secret),false,secret);
}
const dec=x=>Buffer.from(x,"base64url");
const key=pbkdf2Sync(password,dec(a.salt),PBKDF2_ITERATIONS,32,"sha256");
const raw=dec(a.ciphertext);
const decipher=createDecipheriv("aes-256-gcm",key,dec(a.nonce));
decipher.setAAD(Buffer.from(SEALED_KIND));
decipher.setAuthTag(raw.subarray(-16));
const plaintext=Buffer.concat([
  decipher.update(raw.subarray(0,-16)),decipher.final()
]);
const restored=JSON.parse(plaintext.toString("utf8"));
assert.equal(restored.kind,"machine-brave-selected-session-v1");
assert.equal(restored.window_label,"WORK");
assert.equal(restored.restore_allowed,false);
assert.equal(restored.browser_sway_identity_verified,false);
assert.deepEqual(restored.tabs.map(t=>[t.source_position,t.url,t.was_active,t.pinned]),[
  [2,"https://radio.test/listen",true,true],
  [5,"https://example.test/board?auth="+TOKEN,false,false]
]);
const tampered=Buffer.from(raw);
tampered[0]^=1;
const badDec=createDecipheriv("aes-256-gcm",key,dec(a.nonce));
badDec.setAAD(Buffer.from(SEALED_KIND));
badDec.setAuthTag(tampered.subarray(-16));
assert.throws(()=>Buffer.concat([
  badDec.update(tampered.subarray(0,-16)),badDec.final()
]));
assert.equal(SAVE_HOST,"org.postapollo.machine_brave_save_trial");
const nonce="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const request=makeSealedSaveRequest(nonce,a);
assert.deepEqual(Object.keys(request).sort(),[
  "challenge","envelope","kind","operator_save_requested"
]);
assert.equal(request.operator_save_requested,true);
assert.equal(JSON.stringify(request).includes(TOKEN),false);
const response={
  kind:"machine-brave-sealed-save-response-v1",status:"sealed_record_saved",
  challenge:nonce,record_id:"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  sha256:"a".repeat(64),ciphertext_authentication_verified:false,
  origin_authenticated:false,
  persistent_browser_window_binding_verified:false,
  restore_allowed:false,safe_actions:[]
};
assert.deepEqual(checkSealedSaveResponse(nonce,response),{
  status:"sealed_record_saved",record_id:response.record_id,
  sha256:response.sha256,restore_allowed:false,safe_actions:[]
});
for(const malicious of [
  {...response,url:"https://secret"},
  {...response,restore_allowed:true},
  {...response,origin_authenticated:true},
  {...response,ciphertext_authentication_verified:true},
  {...response,safe_actions:["restore"]},
  {...response,challenge:"cccccccc-cccc-4ccc-8ccc-cccccccccccc"},
  {...response,sha256:"BAD"},
  {...response,status:"request_rejected"}
]){
  assert.throws(()=>checkSealedSaveResponse(nonce,malicious));
}
console.log("MACHINE WebCrypto selected tabs sealed, zero-URL envelope, strict native response PASS");
