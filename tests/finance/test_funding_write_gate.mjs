import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {mkdtempSync,mkdirSync,writeFileSync,rmSync,existsSync} from "node:fs";
import {join} from "node:path";
import {tmpdir} from "node:os";
import {fileURLToPath} from "node:url";
const writer=fileURLToPath(new URL("../../scripts/finance/write_funding.mjs",import.meta.url));
const sample={mode:"income",requestId:"a".repeat(32),sourceKey:"f".repeat(64),
 accountId:"fictional-checking",month:"2026-10",date:"2026-10-22",
 amountCents:200,categoryId:"fictional-income",description:"PRIVATE FICTIONAL"};
function setup(){
 const home=mkdtempSync(join(tmpdir(),"financew-funding-lock-"));
 const config=join(home,".config","financew");
 mkdirSync(config,{recursive:true,mode:0o700});
 return {home,config};
}
function run(home,command=sample){
 return spawnSync(process.execPath,[writer],{
  encoding:"utf8",timeout:10000,input:JSON.stringify(command)+"\n",
  env:{...process.env,HOME:home,ACTUAL_SERVER_URL:"",
    ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:"",
    ACTUAL_PASSWORD_FILE:"",ACTUAL_ENCRYPTION_PASSWORD_FILE:""}
 });
}
function permit(f,mode=0o600,marker="FINANCEW_FUNDING_WRITES_APPROVED"){
 writeFileSync(join(f.config,"funding-writes-enabled"),marker+"\n",{mode});
}
const cleanup=f=>rmSync(f.home,{recursive:true,force:true});
test("absent permit refuses before creating any journal or contacting Actual",()=>{
 const f=setup();try{
  const result=run(f.home);
  assert.equal(result.status,1);
  assert.equal(result.stdout.trim(),"FINANCEW_FUNDING_RESULT blocked:writes-disabled");
  assert.ok(!existsSync(join(f.home,".local")));
  assert.ok(!result.stdout.includes(sample.description));
 }finally{cleanup(f);}
});
test("world-readable or wrong permit never permits a financial write",()=>{
 for(const [mode,marker] of [
  [0o644,"FINANCEW_FUNDING_WRITES_APPROVED"],
  [0o600,"SOME_OTHER_APPROVAL"]
 ]){
  const f=setup();try{
   permit(f,mode,marker);
   const result=run(f.home);
   assert.equal(result.status,1);
   assert.equal(result.stdout.trim(),"FINANCEW_FUNDING_RESULT blocked:writes-disabled");
   assert.ok(!existsSync(join(f.home,".local")));
  }finally{cleanup(f);}
 }
});
test("correct funding permit does not bypass source credentials or journal",()=>{
 const f=setup();try{
  permit(f);
  const result=run(f.home);
  assert.equal(result.status,1);
  assert.match(result.stdout,/FINANCEW_FUNDING_RESULT blocked:/);
  assert.ok(!result.stdout.includes(sample.description));
  assert.ok(!existsSync(join(f.home,".local","state","financew","operations","funding-"+sample.requestId+".json")));
 }finally{cleanup(f);}
});
