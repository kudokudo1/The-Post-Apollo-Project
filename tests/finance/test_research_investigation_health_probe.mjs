import assert from "node:assert/strict";
import { spawn,spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { Readable } from "node:stream";
import { fileURLToPath } from "node:url";
import {
  performHealthProbe,consumeHealthFrame,HealthProbeRefusal,
  RESULT_PREFIX,ERROR_PREFIX
} from "../../scripts/finance/research_investigation_health_probe.mjs";

const asOf="2026-11-23T12:00:00Z";
const request=JSON.stringify({action:"audit",asOf,staleDays:180})+"\n";
const empty={schemaVersion:1,revision:0,investigations:[]};
let readCalls=0;
const out=performHealthProbe(request,command=>{
  readCalls++;
  assert.deepEqual(command,{action:"list"});
  return empty;
});
assert.equal(readCalls,1);
assert.ok(out.startsWith(RESULT_PREFIX));
assert.equal(JSON.parse(out.slice(RESULT_PREFIX.length)).metrics.evidenceCount,0);
for(const invalid of [
  '{"action":"create","asOf":"2026-11-23T12:00:00Z","staleDays":180}\n',
  '{"action":"audit","asOf":"2026-11-23T12:00:00Z","staleDays":180,"extra":true}\n',
  '{"action":"audit","asOf":"2026-11-23T12:00:00Z","staleDays":0}\n',
  '{"action":"audit","asOf":"invalid","staleDays":180}\n',
  '{"action":"audit"}\n',
  "not JSON\n",request+request,request.trimEnd(),
  "x".repeat(257)+"\n"
]) {
  const prior=readCalls;
  assert.throws(()=>performHealthProbe(invalid,()=>{readCalls++;return empty;}),
    e=>e instanceof HealthProbeRefusal);
  assert.equal(readCalls,prior,"Invalid input must not touch M2");
}
assert.equal(await consumeHealthFrame(Readable.from([
  Buffer.from('{"action":"audit","asOf":"'),
  Buffer.from(asOf+'","staleDays":180}\n')
])),request);
for(const input of ["request without LF",request+request]) {
  await assert.rejects(consumeHealthFrame(Readable.from([Buffer.from(input)])),
    e=>e instanceof HealthProbeRefusal);
}
const script=fileURLToPath(new URL(
  "../../scripts/finance/research_investigation_health_probe.mjs",import.meta.url));
const sandbox=fs.mkdtempSync(path.join(os.tmpdir(),"finance-research-health-"));
const dataHome=path.join(sandbox,"private-xdg");
const env={...process.env,XDG_DATA_HOME:dataHome};
function cli(input,args=[]) {
  return spawnSync(process.execPath,[script,...args],{
    input,encoding:"utf8",env,timeout:3000,maxBuffer:1024*1024
  });
}
try{
  let result=cli(request);
  assert.equal(result.status,0,result.stderr);
  assert.equal(fs.existsSync(dataHome),false,
    "Read-only probe must not create data directories");
  for(const input of [
    '{"action":"remove"}\n',request+request,"garbage\n"
  ]){
    result=cli(input);
    assert.equal(result.status,1);
    assert.equal(result.stdout,"");
    assert.ok(result.stderr.startsWith(ERROR_PREFIX));
  }
  result=cli(request,["--write"]);
  assert.equal(result.status,1);
  assert.match(result.stderr,/INVALID_ARGUMENTS/);
  const dir=path.join(dataHome,"post-apollo","finance","research-investigations");
  fs.mkdirSync(dir,{recursive:true,mode:0o700});
  const file=path.join(dir,"investigations.json");
  const secret="PRIVATE-TITLE-AND-LINK-DO-NOT-PRINT";
  const doc={
    schemaVersion:1,revision:4,
    investigations:[{
      schemaVersion:1,id:"case-1",title:secret,
      question:"What changed? "+secret,
      createdAt:"2026-01-01T00:00:00Z",
      updatedAt:"2026-11-21T00:00:00Z",
      evidence:[{
        id:"source-1",source:"manual",title:secret,
        summary:secret,url:"https://example.com/"+secret,
        observedAt:"2026-01-01T00:00:00Z",reviewed:false
      }]
    }]
  };
  fs.writeFileSync(file,JSON.stringify(doc)+"\n",{mode:0o600});
  const before=fs.readFileSync(file,"utf8");
  result=cli(request);
  assert.equal(result.status,0,result.stderr);
  assert.equal(result.stderr,"");
  assert.ok(result.stdout.startsWith(RESULT_PREFIX));
  assert.ok(!result.stdout.includes(secret),
    "Probe must not emit original question, URL, title or summary");
  const health=JSON.parse(result.stdout.slice(RESULT_PREFIX.length));
  assert.equal(health.sourceRevision,4);
  assert.equal(health.metrics.manualReviewPending,1);
  assert.equal(health.metrics.oldObservations,1);
  assert.equal(health.metrics.provenanceVerifiedByAudit,0);
  assert.equal(fs.readFileSync(file,"utf8"),before,
    "Health probe must not mutate existing data");

  // This process must answer once newline arrives, even if Qt keeps stdin open.
  const child=spawn(process.execPath,[script],{
    env,stdio:["pipe","pipe","pipe"]
  });
  let stdout="",stderr="",timer;
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data",chunk=>{stdout+=chunk;});
  child.stderr.on("data",chunk=>{stderr+=chunk;});
  const closed=new Promise((resolve,reject)=>{
    child.on("close",resolve);
    child.on("error",reject);
  });
  child.stdin.write(request);
  const code=await Promise.race([
    closed,
    new Promise((_,reject)=>{
      timer=setTimeout(()=>{
        child.kill("SIGKILL");
        reject(new Error("Health probe waited for EOF"));
      },2500);
    })
  ]);
  clearTimeout(timer);
  child.stdin.destroy();
  assert.equal(code,0,stderr);
  assert.equal(stdout,result.stdout);

  fs.writeFileSync(file,"{broken JSON",{mode:0o600});
  result=cli(request);
  assert.equal(result.status,1);
  assert.equal(result.stdout,"");
  assert.match(result.stderr,/READ_UNAVAILABLE/);
  assert.equal(fs.readFileSync(file,"utf8"),"{broken JSON",
    "Corrupt research files must remain untouched");
  console.log("Finance Research M5 local read-only health probe: PASS");
}finally{
  fs.rmSync(sandbox,{recursive:true,force:true});
}
