#!/usr/bin/env node
// FinanceW Research M10b: READ-ONLY recovery inventory for the M2 JSON store.
// A lock is not evidence that a writer finished. This tool cannot unlock,
// retry, write a file, or approve a new write. No notebook content in output.
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { run, rootDirectory, Refusal } from "./research_investigation_store.mjs";

export const RESULT_PREFIX = "FINANCE_RESEARCH_RECOVERY_RESULT ";
export const ERROR_PREFIX = "FINANCE_RESEARCH_RECOVERY_ERROR ";
const MAX_ENTRIES = 128;
const MAX_RESULT_BYTES = 4096;
const TEMPNAME = /^\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.tmp$/i;
const READ_CODES = new Set([
  "STORE_UNAVAILABLE", "UNSAFE_DIRECTORY", "UNSAFE_FILE",
  "CORRUPT_STORE", "STORE_LIMIT"
]);
const digest = x => createHash("sha256").update(x).digest("hex");

function baseResult() {
  return {
    schemaVersion: 1, readOnly: true, canUnlock: false,
    canRetry: false, changesMade: false,
    status: "UNAVAILABLE", reason: "NOT_INSPECTED",
    store: {state: "UNKNOWN",revision:null,fingerprint:null,
      caseCount:null,evidenceCount:null},
    lock: {state:"UNKNOWN",fingerprint:null},
    tempCount:null, unexpectedCount:null
  };
}
function readCode(e) {
  return e instanceof Refusal && READ_CODES.has(e.message)
    ? e.message : "READ_UNAVAILABLE";
}
function statLock(dir) {
  const file=path.join(dir,"investigations.lock");
  let s;
  try {s=fs.lstatSync(file);}
  catch(e) {
    if(e.code==="ENOENT") return {state:"ABSENT",fingerprint:null};
    return {state:"UNKNOWN",fingerprint:null};
  }
  if(!s.isFile() || s.isSymbolicLink()
      || s.uid!==process.getuid() || (s.mode&0o077)!==0
      || s.nlink!==1 || s.size!==0)
    return {state:"UNSAFE",fingerprint:null};
  const fingerprint=digest(JSON.stringify([
    s.dev,s.ino,s.uid,s.mode&0o777,s.nlink,s.ctimeMs
  ]));
  return {state:"PRESENT",fingerprint};
}
function inventory(dir) {
  let entries,seen=0,tempCount=0,unexpectedCount=0;
  try {
    entries=fs.opendirSync(dir);
    while(true) {
      const item=entries.readSync();
      if(!item) break;
      if(++seen>MAX_ENTRIES)
        return {tempCount:null,unexpectedCount:null,tooMany:true};
      const name=item.name;
      if(TEMPNAME.test(name)) tempCount++;
      else if(name!=="investigations.json"
          && name!=="investigations.lock") unexpectedCount++;
    }
    return {tempCount,unexpectedCount,tooMany:false};
  } catch {
    return {tempCount:null,unexpectedCount:null,unavailable:true};
  } finally {
    if(entries) entries.closeSync();
  }
}

/** Reproducible, read-only recovery evidence. NEVER a permission to unlock. */
export function inspectResearchRecovery(dir=rootDirectory()) {
  const result=baseResult();
  let document;
  let readProblem=null;
  try {
    // Reuse the hardened M2 reader, including its ancestor checks.
    document=run({action:"list"},dir);
    result.store={
      state:"READABLE",revision:document.revision,
      fingerprint:digest(JSON.stringify(document)),
      caseCount:document.investigations.length,
      evidenceCount:document.investigations.reduce(
        (count,item)=>count+item.evidence.length,0)
    };
  } catch(e) {
    readProblem=readCode(e);
    result.store.state="REFUSED";
  }

  // Once an ancestor path is rejected, do not traverse it again merely
  // to inspect a lock. Untrusted path diagnostics reveal no file contents.
  if(readProblem==="UNSAFE_DIRECTORY"
      || readProblem==="STORE_UNAVAILABLE"
      || (readProblem==="READ_UNAVAILABLE")) {
    result.reason=readProblem;
    return result;
  }

  let info;
  try {info=fs.lstatSync(dir);}
  catch(e) {
    if(e.code==="ENOENT" && !readProblem) {
      result.status="NO_STORE";
      result.reason="DIRECTORY_ABSENT";
      result.lock={state:"ABSENT",fingerprint:null};
      result.tempCount=0;
      result.unexpectedCount=0;
      return result;
    }
    result.reason="DIRECTORY_UNAVAILABLE";
    return result;
  }
  if(!info.isDirectory() || info.isSymbolicLink()
      || info.uid!==process.getuid() || (info.mode&0o077)) {
    result.reason="UNSAFE_DIRECTORY";
    return result;
  }

  result.lock=statLock(dir);
  const files=inventory(dir);
  result.tempCount=files.tempCount;
  result.unexpectedCount=files.unexpectedCount;

  if(files.unavailable) {
    result.reason="DIRECTORY_UNAVAILABLE";
    return result;
  }
  if(files.tooMany) {
    result.reason="ENTRY_LIMIT";
    return result;
  }
  if(readProblem) {
    result.reason=readProblem;
    return result;
  }
  if(result.lock.state==="UNKNOWN" || result.lock.state==="UNSAFE") {
    result.reason="LOCK_UNSAFE_OR_UNAVAILABLE";
    return result;
  }
  if(result.lock.state==="PRESENT"
      || result.tempCount>0 || result.unexpectedCount>0) {
    result.status="REVIEW_REQUIRED";
    result.reason=result.lock.state==="PRESENT"
      ? "LOCK_PRESENT_OUTCOME_UNKNOWN" : "UNEXPECTED_RESEARCH_FILES";
    return result;
  }
  result.status="NO_RECOVERY_LOCK";
  result.reason="NO_LOCK_OBSERVED";
  return result;
}

const isMain=process.argv[1] &&
  path.resolve(process.argv[1])===fileURLToPath(import.meta.url);
if(isMain) {
  try {
    if(process.argv.length!==2) throw new Error("ARGUMENTS");
    const report=inspectResearchRecovery();
    const payload=JSON.stringify(report);
    if(Buffer.byteLength(payload,"utf8")>MAX_RESULT_BYTES)
      throw new Error("OUTPUT_TOO_LARGE");
    process.stdout.write(RESULT_PREFIX+payload+"\n");
  } catch {
    process.stderr.write(ERROR_PREFIX+"INSPECTION_UNAVAILABLE\n");
    process.exitCode=1;
  }
}
