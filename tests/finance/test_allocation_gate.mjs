import {test} from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,chmodSync,symlinkSync,
  rmSync,existsSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {fileURLToPath} from "node:url";

const cli=fileURLToPath(new URL("../../scripts/finance/check_allocation_gate.mjs",import.meta.url));
const marker="FINANCEW_ALLOCATION_WRITES_APPROVED";
function fixture() {
  const home=mkdtempSync(join(tmpdir(),"financew-readonly-gate-"));
  const parent=join(home,".config","financew");
  mkdirSync(parent,{recursive:true,mode:0o700});
  return {home,parent,permit:join(parent,"allocation-writes-enabled")};
}
function run(f) {
  return spawnSync(process.execPath,[cli],{
    encoding:"utf8",timeout:10000,env:{...process.env,HOME:f.home,
      ACTUAL_SERVER_URL:"",ACTUAL_PASSWORD_FILE:"",
      ACTUAL_SYNC_ID:"",ACTUAL_SYNC_ID_FILE:""}
  });
}
function expectStatus(f,expected){
  const r=run(f);
  assert.equal(r.status,0,r.stderr);
  assert.equal(r.stderr,"");
  assert.equal(r.stdout,"FINANCEW_ALLOCATION_GATE "+expected+"\n");
}
const cleanup=f=>rmSync(f.home,{recursive:true,force:true});

test("missing permit reports locked and does not create a file",()=>{
  const f=fixture();
  try {
    expectStatus(f,"locked");
    assert.equal(existsSync(f.permit),false);
    assert.equal(existsSync(join(f.home,".local")),false);
  } finally {cleanup(f);}
});
test("private exact marker reports permit-present without modifying it",()=>{
  const f=fixture();
  try {
    writeFileSync(f.permit,marker+"\n",{mode:0o600});
    const before=readFileSync(f.permit,"utf8");
    expectStatus(f,"permit-present");
    assert.equal(readFileSync(f.permit,"utf8"),before);
  } finally {cleanup(f);}
});
test("incorrect marker and world-readable file report unsafe",()=>{
  const f=fixture();
  try {
    writeFileSync(f.permit,"INCORRECT\n",{mode:0o600});
    expectStatus(f,"unsafe");
    writeFileSync(f.permit,marker+"\n",{mode:0o600});
    chmodSync(f.permit,0o644);
    expectStatus(f,"unsafe");
  } finally {cleanup(f);}
});
test("symlink is never followed and external bytes are preserved",()=>{
  const f=fixture();
  try {
    const target=join(f.home,"other-file");
    writeFileSync(target,marker+"\n",{mode:0o600});
    symlinkSync(target,f.permit);
    expectStatus(f,"unsafe");
    assert.equal(readFileSync(target,"utf8"),marker+"\n");
  } finally {cleanup(f);}
});
test("probe contains no filesystem or Actual mutation imports",()=>{
  const source=readFileSync(cli,"utf8");
  for(const forbidden of ["@actual-app/api","mkdir(","writeFile(",
    "createWriteStream","unlink(","rm(","setBudgetAmount(","addTransactions(",
    "FINANCEW_ALLOCATION_RESULT"]) assert.equal(source.includes(forbidden),false,forbidden);
});
