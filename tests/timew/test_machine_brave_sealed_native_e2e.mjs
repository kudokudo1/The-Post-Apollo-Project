import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {readFileSync,readdirSync,rmSync} from "node:fs";
import {spawnSync} from "node:child_process";
import {endianness} from "node:os";
import {resolve,join,dirname,basename} from "node:path";
import {sealSelectedSession} from "../../integrations/machine/brave-topology/session-seal.mjs";
import {makeSealedSaveRequest,checkSealedSaveResponse} from "../../integrations/machine/brave-topology/save-host-protocol.mjs";

const repo=resolve(new URL("../../",import.meta.url).pathname);
const EXT="a".repeat(32), origin="chrome-extension://"+EXT+"/";
const password="SYNTHETIC NATIVE ROUNDTRIP PASSPHRASE";
const token="SYNTHETIC-TOKEN-DO-NOT-PRINT";
let root=null;
function run(args,options={}){
  const p=spawnSync("python3",["-B","-I",...args],{
    cwd:repo,timeout:30000,encoding:"utf8",...options
  });
  assert.equal(p.error,undefined);
  assert.equal(String(p.stderr),"");
  return p;
}
const le=endianness()==="LE";
function frame(value){
  const raw=Buffer.from(JSON.stringify(value));
  const head=Buffer.alloc(4);
  if(le)head.writeUInt32LE(raw.length);
  else head.writeUInt32BE(raw.length);
  return Buffer.concat([head,raw]);
}
function reply(raw){
  const size=le?raw.readUInt32LE(0):raw.readUInt32BE(0);
  assert.equal(raw.length-4,size);
  return JSON.parse(raw.subarray(4).toString("utf8"));
}
const fromB64=s=>Uint8Array.from(Buffer.from(s,"base64url"));
try{
  const setup=[
    "import json,sys",
    "sys.path.insert(0,'services/time')",
    "from MachineBraveDisposableTrial import init_trial,register_trial",
    "from MachineBraveFocusTrial import register_focus",
    "from MachineBraveTitleTrial import register as title",
    "from MachineBraveSaveTrial import register as save",
    "r=init_trial()['trial_root']",
    "e='a'*32",
    "register_trial(r,e)",
    "register_focus(r,e)",
    "title(r,e)",
    "save(r,e)",
    "print(json.dumps({'root':r}))"
  ].join("\n");
  const initialized=run(["-c",setup]);
  assert.equal(initialized.status,0);
  root=JSON.parse(initialized.stdout).root;
  assert.equal(dirname(root),"/tmp");
  assert.match(basename(root),/^postapollo-machine-brave-trial-[A-Za-z0-9_-]{6,}$/);

  const selected=[
    {index:1,url:"https://example.test/first",pinned:true,wasActive:true},
    {index:2,url:"https://example.test/auth?token="+token,pinned:false,wasActive:false}
  ];
  const envelope=await sealSelectedSession({
    label:"WORK",tabs:selected,passphrase:password,includeSensitive:true
  },webcrypto);
  const nonce="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  const request=frame(makeSealedSaveRequest(nonce,envelope));
  for(const secret of [token,password,"https://","example.test"])
    assert.equal(request.includes(Buffer.from(secret)),false,secret);
  const receiver=run([join(root,"MachineBraveSaveHost.py"),origin],{
    input:request,encoding:null,
    env:{...process.env,XDG_DATA_HOME:"/tmp/NOT-APPROVED-FOR-SAVE"}
  });
  assert.equal(receiver.status,0);
  assert.equal(receiver.stderr.length,0);
  const received=checkSealedSaveResponse(nonce,reply(receiver.stdout));
  assert.equal(received.status,"sealed_record_saved");
  const directory=join(root,"vault-data/post-apollo/machine/brave-sealed-vault");
  const files=readdirSync(directory);
  assert.deepEqual(files,[received.record_id+".json"]);
  const raw=readFileSync(join(directory,files[0]));
  for(const secret of [token,password,"https://","example.test"])
    assert.equal(raw.includes(Buffer.from(secret)),false,secret);
  const stored=JSON.parse(raw.toString("utf8"));
  assert.deepEqual(stored.envelope,envelope);
  const bytes=new TextEncoder().encode(password);
  const keySource=await webcrypto.subtle.importKey(
    "raw",bytes,"PBKDF2",false,["deriveKey"]);
  bytes.fill(0);
  const key=await webcrypto.subtle.deriveKey({
    name:"PBKDF2",hash:"SHA-256",salt:fromB64(envelope.salt),
    iterations:600000
  },keySource,{name:"AES-GCM",length:256},false,["decrypt"]);
  const plaintext=await webcrypto.subtle.decrypt({
    name:"AES-GCM",iv:fromB64(envelope.nonce),
    additionalData:new TextEncoder().encode(envelope.aad),tagLength:128
  },key,fromB64(envelope.ciphertext));
  const decoded=JSON.parse(new TextDecoder().decode(plaintext));
  assert.equal(decoded.window_label,"WORK");
  assert.deepEqual(decoded.tabs.map(x=>x.url),selected.map(x=>x.url));
  assert.equal(decoded.restore_allowed,false);
  assert.equal(decoded.browser_sway_identity_verified,false);
}finally{
  if(root!==null){
    assert.equal(dirname(root),"/tmp");
    assert.match(basename(root),/^postapollo-machine-brave-trial-[A-Za-z0-9_-]{6,}$/);
    rmSync(root,{recursive:true,force:true});
  }
}
console.log("MACHINE real WebCrypto to native ciphertext vault and authenticated decrypt // PASS");
