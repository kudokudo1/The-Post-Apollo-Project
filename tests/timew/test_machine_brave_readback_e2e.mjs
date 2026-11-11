import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {spawnSync} from "node:child_process";
import {readFileSync,readdirSync,rmSync} from "node:fs";
import {endianness} from "node:os";
import {resolve,join,dirname,basename} from "node:path";
import {sealSelectedSession} from "../../integrations/machine/brave-topology/session-seal.mjs";
import {inspectSealedSnapshot} from "../../integrations/machine/brave-topology/session-unseal.mjs";
import {makeSealedSaveRequest,checkSealedSaveResponse} from
  "../../integrations/machine/brave-topology/save-host-protocol.mjs";
import {makeReadRequest,verifyReadReply} from
  "../../integrations/machine/brave-topology/read-host-protocol.mjs";

const repo=resolve(new URL("../../",import.meta.url).pathname);
const ext="a".repeat(32),origin="chrome-extension://"+ext+"/";
const pass="TEST ONLY DIFFERENT FROM ANY REAL USER PASSPHRASE";
const token="PRIVATE-QUERY-SYNTHETIC-EXAMPLE-102";
const le=endianness()==="LE";
let trial=null;
function subprocess(args,opts={}){
  const p=spawnSync("python3",["-B","-I",...args],{
    cwd:repo,encoding:"utf8",timeout:30000,...opts
  });
  assert.equal(p.error,undefined);
  assert.equal(String(p.stderr),"");
  return p;
}
function frame(obj){
  const content=Buffer.from(JSON.stringify(obj));
  const h=Buffer.alloc(4);
  if(le)h.writeUInt32LE(content.length);else h.writeUInt32BE(content.length);
  return Buffer.concat([h,content]);
}
function response(bytes){
  assert.ok(bytes.length>=4);
  const n=le?bytes.readUInt32LE(0):bytes.readUInt32BE(0);
  assert.equal(bytes.length-4,n);
  return JSON.parse(bytes.subarray(4).toString("utf8"));
}
function call(host,request,originArg=origin){
  return subprocess([join(trial,host),originArg],{
    input:frame(request),encoding:null,
    env:{...process.env,XDG_DATA_HOME:"/tmp/NOT-A-VIRGIN-DATA-HOME"}
  });
}
try{
  const setup=[
    "import json,sys",
    "sys.path.insert(0,'services/time')",
    "from MachineBraveDisposableTrial import init_trial,register_trial",
    "from MachineBraveFocusTrial import register_focus",
    "from MachineBraveTitleTrial import register as title",
    "from MachineBraveSaveTrial import register as save",
    "from MachineBraveReadTrial import register as reader,verify",
    "r=init_trial()['trial_root']",
    "e='a'*32",
    "register_trial(r,e)",
    "register_focus(r,e)",
    "title(r,e)",
    "save(r,e)",
    "reader(r,e)",
    "assert verify(r)['status']=='disposable_sealed_read_registration_verified'",
    "print(json.dumps({'root':r}))"
  ].join("\n");
  const prepared=subprocess(["-c",setup]);
  assert.equal(prepared.status,0);
  trial=JSON.parse(prepared.stdout).root;
  assert.equal(dirname(trial),"/tmp");
  assert.match(basename(trial),/^postapollo-machine-brave-trial-[A-Za-z0-9_-]{6,}$/);

  // Missing record read never creates a vault.
  const unknown="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  const challenge="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  const noRecord=call("MachineBraveReadHost.py",makeReadRequest(challenge,unknown));
  assert.notEqual(noRecord.status,0);
  assert.equal(response(noRecord.stdout).status,"request_rejected");
  const data=join(trial,"vault-data/post-apollo");
  const missingDir=await import("node:fs");
  assert.equal(missingDir.existsSync(data),false);

  const selected=[
    {index:3,url:"https://example.test/path?token="+token,
      pinned:false,wasActive:false},
    {index:1,url:"https://radio.test/listen",
      pinned:true,wasActive:true}
  ];
  const envelope=await sealSelectedSession({
    label:"WORK",tabs:selected,passphrase:pass,includeSensitive:true
  },webcrypto);
  const saveRequest=makeSealedSaveRequest(challenge,envelope);
  const saved=call("MachineBraveSaveHost.py",saveRequest);
  assert.equal(saved.status,0);
  const receipt=checkSealedSaveResponse(challenge,response(saved.stdout));
  const dir=join(data,"machine/brave-sealed-vault");
  const files=readdirSync(dir);
  assert.deepEqual(files,[receipt.record_id+".json"]);
  const before=readFileSync(join(dir,files[0]));

  const nonce="cccccccc-cccc-4ccc-8ccc-cccccccccccc";
  const readRequest=makeReadRequest(nonce,receipt.record_id);
  assert.equal(JSON.stringify(readRequest).includes(token),false);
  const observed=call("MachineBraveReadHost.py",readRequest);
  assert.equal(observed.status,0);
  const checked=verifyReadReply(nonce,receipt.record_id,response(observed.stdout));
  assert.equal(checked.sha256,receipt.sha256);
  assert.deepEqual(checked.envelope,envelope);
  for(const secret of [pass,token,"https://","radio.test","example.test"]){
    assert.equal(observed.stdout.includes(Buffer.from(secret)),false,secret);
  }
  const review=await inspectSealedSnapshot(checked.envelope,pass,webcrypto);
  assert.equal(review.status,"authenticated_redacted_review");
  assert.deepEqual(review.tabs.map(x=>x.hostname),["radio.test","example.test"]);
  assert.equal(review.tab_count,2);
  assert.equal(review.restore_allowed,false);
  assert.equal(JSON.stringify(review).includes(token),false);
  assert.deepEqual(readdirSync(dir),files);
  assert.deepEqual(readFileSync(join(dir,files[0])),before);

  // Refuse any alternative origin, unknown ID or added plaintext request.
  const badOrigin=call("MachineBraveReadHost.py",readRequest,
    "chrome-extension://"+"b".repeat(32)+"/");
  assert.notEqual(badOrigin.status,0);
  assert.equal(response(badOrigin.stdout).status,"request_rejected");
  const extra=call("MachineBraveReadHost.py",{
    ...readRequest,plaintext_url:"https://secret.test"
  });
  assert.notEqual(extra.status,0);
  assert.equal(response(extra.stdout).status,"request_rejected");

  // Wrong password fails inside browser crypto, with zero restore action.
  await assert.rejects(()=>inspectSealedSnapshot(
    checked.envelope,"WRONG PASSWORD 0000000000",webcrypto));
  assert.deepEqual(readFileSync(join(dir,files[0])),before);
}finally{
  if(trial!==null){
    assert.equal(dirname(trial),"/tmp");
    assert.match(basename(trial),/^postapollo-machine-brave-trial-[A-Za-z0-9_-]{6,}$/);
    rmSync(trial,{recursive:true,force:true});
  }
}
console.log("MACHINE encrypted save → native read-only record → WebCrypto verified redacted review PASS");
