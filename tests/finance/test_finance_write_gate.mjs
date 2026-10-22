import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {mkdtempSync,rmSync,mkdirSync,writeFileSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

const cli=fileURLToPath(new URL("../../scripts/finance/write_transaction.mjs",import.meta.url));
const command={
  action:"create",requestId:"c".repeat(32),accountId:"fictional-123",
  month:"2026-10",date:"2026-10-22",description:"Fake Test Shop",
  amountCents:-400
};
function run(home, input=JSON.stringify(command)+"\n") {
  return spawnSync(process.execPath,[cli],{
    env:{...process.env,HOME:home},encoding:"utf8",input,timeout:12000
  });
}
test("write CLI refuses with missing operator-owned activation file",()=>{
  const home=mkdtempSync(join(tmpdir(),"financew-write-fake-"));
  try {
    const result=run(home);
    assert.notEqual(result.status,0);
    assert.match(result.stdout,/FINANCEW_TRANSACTION_RESULT blocked:writes-disabled/);
    assert.ok(!result.stdout.includes(command.description));
    assert.ok(!result.stderr.includes(command.description));
  } finally {rmSync(home,{recursive:true,force:true});}
});
test("unsafe/world-readable activation file remains disabled",()=>{
  const home=mkdtempSync(join(tmpdir(),"financew-write-fake-"));
  try {
    const base=join(home,".config","financew");
    mkdirSync(base,{recursive:true,mode:0o700});
    writeFileSync(join(base,"transaction-writes-enabled"),
      "FINANCEW_TRANSACTION_WRITES_APPROVED\n",{mode:0o644});
    const result=run(home);
    assert.notEqual(result.status,0);
    assert.match(result.stdout,/blocked:writes-disabled/);
  } finally {rmSync(home,{recursive:true,force:true});}
});
test("activating cannot bypass unresolved recovery journal",()=>{
  const home=mkdtempSync(join(tmpdir(),"financew-write-fake-"));
  try {
    const base=join(home,".config","financew");
    mkdirSync(base,{recursive:true,mode:0o700});
    writeFileSync(join(base,"transaction-writes-enabled"),
      "FINANCEW_TRANSACTION_WRITES_APPROVED\n",{mode:0o600});
    const journal=join(home,".local","state","financew","operations");
    mkdirSync(journal,{recursive:true,mode:0o700});
    writeFileSync(join(journal,"z".repeat(32)+".json"),
      JSON.stringify({version:1,status:"attempted"})+"\n",{mode:0o600});
    // The fixture does not create credentials, so it must fail closed even
    // before inspecting the journal. No @actual-app/api or real network call.
    const result=run(home);
    assert.notEqual(result.status,0);
    assert.match(result.stdout,/FINANCEW_TRANSACTION_RESULT blocked:/);
    assert.ok(!result.stdout.includes(command.description));
  } finally {rmSync(home,{recursive:true,force:true});}
});
