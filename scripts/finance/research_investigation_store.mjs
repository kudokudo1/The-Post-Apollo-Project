#!/usr/bin/env node
// FinanceW Research M2: local-only versioned investigation store.
// Explicit CLI actions. No network, model calls, banking, or automatic retries.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { createInvestigation, attachEvidence, removeEvidence, validateCollection } from "./research_investigations.mjs";

const PREFIX = "FINANCE_RESEARCH_STORE_";
const MAX_BYTES = 500000;
const MAX_COMMAND_BYTES = 8192;
const KEYS = Object.freeze({
  list: ["action"],
  create: ["action","expectedRevision","id","title","question","timestamp"],
  attach: ["action","expectedRevision","investigationId","evidence","timestamp"],
  remove: ["action","expectedRevision","investigationId","evidenceId","timestamp"]
});
class Refusal extends Error {}
const refuse = code => { throw new Refusal(code); };
function exactFields(value, keys) {
  return value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === keys.length
    && keys.every(key => Object.prototype.hasOwnProperty.call(value, key));
}
function rootDirectory() {
  const base = process.env.XDG_DATA_HOME;
  const parent = typeof base === "string" && path.isAbsolute(base)
    ? base : path.join(os.homedir(), ".local", "share");
  return path.join(parent, "post-apollo", "finance", "research-investigations");
}
function privateDirectory(dir, create) {
  if (create) fs.mkdirSync(dir, {recursive:true,mode:0o700});
  let info;
  try { info = fs.lstatSync(dir); }
  catch (e) { if (!create && e.code === "ENOENT") return false; refuse("STORE_UNAVAILABLE"); }
  if (!info.isDirectory() || info.isSymbolicLink() || info.uid !== process.getuid() || (info.mode & 0o077))
    refuse("UNSAFE_DIRECTORY");
  return true;
}
function secureRegular(file) {
  let st;
  try { st = fs.lstatSync(file); }
  catch(e) { if (e.code === "ENOENT") return false; refuse("UNSAFE_FILE"); }
  if (!st.isFile() || st.isSymbolicLink() || st.uid !== process.getuid() || (st.mode & 0o077) || st.size > MAX_BYTES)
    refuse("UNSAFE_FILE");
  return true;
}
function empty() { return {schemaVersion:1,revision:0,investigations:[]}; }
function validDocument(doc) {
  return exactFields(doc,["schemaVersion","revision","investigations"])
    && doc.schemaVersion === 1 && Number.isSafeInteger(doc.revision)
    && doc.revision >= 0 && doc.revision < Number.MAX_SAFE_INTEGER
    && validateCollection(doc.investigations);
}
function load(dir) {
  if (!privateDirectory(dir,false)) return empty();
  const file = path.join(dir,"investigations.json");
  if (!secureRegular(file)) return empty();
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const st = fs.fstatSync(fd);
    if (!st.isFile() || st.uid !== process.getuid() || (st.mode & 0o077) || st.size > MAX_BYTES)
      refuse("UNSAFE_FILE");
    const raw = fs.readFileSync(fd,{encoding:"utf8"});
    if (Buffer.byteLength(raw,"utf8") > MAX_BYTES) refuse("STORE_LIMIT");
    let doc;
    try { doc = JSON.parse(raw); } catch { refuse("CORRUPT_STORE"); }
    if (!validDocument(doc)) refuse("CORRUPT_STORE");
    return doc;
  } finally { fs.closeSync(fd); }
}
function save(dir,doc) {
  if (!validDocument(doc)) refuse("INVALID_DOCUMENT");
  const payload = JSON.stringify(doc) + "\n";
  if (Buffer.byteLength(payload,"utf8") > MAX_BYTES) refuse("STORE_LIMIT");
  const file = path.join(dir,"investigations.json");
  const temp = path.join(dir,"."+randomUUID()+".tmp");
  let fd;
  try {
    fd = fs.openSync(temp,fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_WRONLY|fs.constants.O_NOFOLLOW,0o600);
    fs.writeFileSync(fd,payload,"utf8");
    fs.fsyncSync(fd);
    fs.closeSync(fd);
    fd=undefined;
    secureRegular(file);
    fs.renameSync(temp,file);
    const dfd=fs.openSync(dir,fs.constants.O_RDONLY|fs.constants.O_DIRECTORY|fs.constants.O_NOFOLLOW);
    try {fs.fsyncSync(dfd);} finally {fs.closeSync(dfd);}
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    try {fs.unlinkSync(temp);}catch(e){if(e.code !== "ENOENT") throw e;}
  }
}
function run(command,dir=rootDirectory()) {
  if (!command || !Object.prototype.hasOwnProperty.call(KEYS,command.action)
      || !exactFields(command,KEYS[command.action])) refuse("INVALID_COMMAND");
  if (command.action === "list") return load(dir);
  if (!Number.isSafeInteger(command.expectedRevision) || command.expectedRevision < 0)
    refuse("INVALID_REVISION");
  privateDirectory(dir,true);
  // LOCK_EX behavior: fail fast while another writer is active; never auto-retry.
  const lock=path.join(dir,"investigations.lock");
  let lockfd;
  try {
    lockfd=fs.openSync(lock,fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_WRONLY|fs.constants.O_NOFOLLOW,0o600);
  } catch(e) { if(e.code === "EEXIST") refuse("WRITE_BUSY"); refuse("UNSAFE_LOCK"); }
  try {
    const current=load(dir);
    if (current.revision !== command.expectedRevision) refuse("STALE_REVISION");
    let investigations;
    try {
      if (command.action === "create")
        investigations=createInvestigation(current.investigations,command);
      else if (command.action === "attach")
        investigations=attachEvidence(current.investigations,command.investigationId,command.evidence,command.timestamp);
      else investigations=removeEvidence(current.investigations,command.investigationId,command.evidenceId,command.timestamp);
    } catch { refuse("INVALID_RESEARCH_CHANGE"); }
    const next={schemaVersion:1,revision:current.revision+1,investigations};
    save(dir,next);
    return next;
  } finally {
    fs.closeSync(lockfd);
    fs.unlinkSync(lock);
  }
}
export {run,rootDirectory,Refusal};
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  try {
    const raw=fs.readFileSync(0,{encoding:"utf8"});
    if (Buffer.byteLength(raw,"utf8") > MAX_COMMAND_BYTES || !raw.endsWith("\n"))
      refuse("INVALID_INPUT_FRAME");
    let command;
    try {command=JSON.parse(raw);} catch {refuse("INVALID_JSON");}
    const doc=run(command);
    process.stdout.write(PREFIX+"RESULT "+JSON.stringify(doc)+"\n");
  } catch(error) {
    process.stderr.write(PREFIX+"ERROR "+(error instanceof Refusal ? error.message : "OPERATION_FAILED")+"\n");
    process.exitCode=1;
  }
}
