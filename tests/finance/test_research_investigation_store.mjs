import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {run,Refusal} from "../../scripts/finance/research_investigation_store.mjs";
const base=fs.mkdtempSync(path.join(os.tmpdir(),"finance-research-m2-"));
const dir=path.join(base,"research");
const timestamp="2026-11-22T20:00:00Z";
const isRefusal = code => e => e instanceof Refusal && e.message === code;
try {
  let doc=run({action:"list"},dir);
  assert.equal(doc.revision,0);
  assert.equal(fs.existsSync(dir),false,"list must not create storage");
  doc=run({action:"create",expectedRevision:0,id:"case-1",title:"Research",
    question:"What happened?",timestamp},dir);
  assert.equal(doc.revision,1);
  assert.equal(doc.investigations.length,1);
  const file=path.join(dir,"investigations.json");
  assert.equal(fs.statSync(dir).mode & 0o077,0);
  assert.equal(fs.statSync(file).mode & 0o077,0);
  assert.equal(run({action:"list"},dir).investigations[0].id,"case-1");
  assert.throws(()=>run({action:"create",expectedRevision:0,id:"case-2",title:"Old",
    question:"Why?",timestamp},dir),isRefusal("STALE_REVISION"));
  const evidence={id:"source-1",source:"sec-edgar-submissions",
    title:"Official filing",summary:"Recorded fact",observedAt:timestamp,
    url:"https://www.sec.gov/Archives/edgar/data/320193/file.htm"};
  doc=run({action:"attach",expectedRevision:1,investigationId:"case-1",evidence,timestamp},dir);
  assert.equal(doc.revision,2);
  assert.equal(doc.investigations[0].evidence.length,1);
  assert.throws(()=>run({action:"attach",expectedRevision:2,investigationId:"case-1",
    evidence:{...evidence,id:"source-2",url:"https://evil.example/file.htm"},timestamp},dir),
    isRefusal("INVALID_RESEARCH_CHANGE"));
  assert.equal(run({action:"list"},dir).revision,2);
  doc=run({action:"remove",expectedRevision:2,investigationId:"case-1",
    evidenceId:"source-1",timestamp},dir);
  assert.equal(doc.revision,3);
  assert.equal(doc.investigations[0].evidence.length,0);
  // Refuse concurrent writer, and preserve original unchanged.
  const lock=path.join(dir,"investigations.lock");
  fs.writeFileSync(lock,"", {mode:0o600});
  assert.throws(()=>run({action:"create",expectedRevision:3,id:"case-2",title:"Blocked",
    question:"Why?",timestamp},dir),isRefusal("WRITE_BUSY"));
  assert.equal(run({action:"list"},dir).revision,3);
  fs.unlinkSync(lock);
  // Corruption is never converted into an empty store or overwritten.
  const saved=fs.readFileSync(file);
  fs.writeFileSync(file,"{bad json",{mode:0o600});
  assert.throws(()=>run({action:"list"},dir),isRefusal("CORRUPT_STORE"));
  assert.throws(()=>run({action:"create",expectedRevision:3,id:"case-2",title:"Blocked",
    question:"Why?",timestamp},dir),isRefusal("CORRUPT_STORE"));
  assert.equal(fs.readFileSync(file,"utf8"),"{bad json");
  fs.writeFileSync(file,saved);
  // Refuse symlink records, including links pointing outside the private folder.
  const other=path.join(base,"outside.json");fs.writeFileSync(other,"{}",{mode:0o600});
  fs.unlinkSync(file);
  fs.symlinkSync(other,file);
  assert.throws(()=>run({action:"list"},dir),isRefusal("UNSAFE_FILE"));
  fs.unlinkSync(file);
  fs.writeFileSync(file,saved);
  fs.chmodSync(file,0o644);
  assert.throws(()=>run({action:"list"},dir),isRefusal("UNSAFE_FILE"));
  fs.chmodSync(file,0o600);
  assert.equal(run({action:"list"},dir).revision,3);
  // Exact command shape: no shadow fields.
  assert.throws(()=>run({action:"list",extra:true},dir),isRefusal("INVALID_COMMAND"));
  console.log("Finance Research M2 local store: PASS");
} finally {
  fs.rmSync(base,{recursive:true,force:true});
}
