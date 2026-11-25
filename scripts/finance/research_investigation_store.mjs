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
  if (typeof dir !== "string" || !path.isAbsolute(dir)
      || path.normalize(dir) !== dir || dir.length > 4096)
    refuse("UNSAFE_DIRECTORY");
  // Never use recursive mkdir: it follows unchecked parent symlinks
  // and may create Research paths outside the intended data root.
  let current=path.parse(dir).root;
  const parts=dir.slice(current.length).split(path.sep).filter(Boolean);
  for (const part of parts) {
    current=path.join(current,part);
    let info;
    try { info=fs.lstatSync(current); }
    catch (e) {
      if (e.code !== "ENOENT") refuse("STORE_UNAVAILABLE");
      if (!create) return false;
      try {fs.mkdirSync(current,{mode:0o700});}
      catch (error) {
        if (error.code !== "EEXIST") refuse("STORE_UNAVAILABLE");
      }
      try {info=fs.lstatSync(current);}
      catch {refuse("STORE_UNAVAILABLE");}
    }
    if (!info.isDirectory() || info.isSymbolicLink())
      refuse("UNSAFE_DIRECTORY");
    if (current === dir && (info.uid !== process.getuid()
        || (info.mode & 0o077))) refuse("UNSAFE_DIRECTORY");
  }
  return true;
}
function unsafeRegular(st) {
  return !st.isFile() || st.isSymbolicLink() || st.nlink !== 1
    || st.uid !== process.getuid() || (st.mode & 0o077)
    || st.size > MAX_BYTES;
}
function secureRegular(file) {
  let st;
  try { st = fs.lstatSync(file); }
  catch(e) { if (e.code === "ENOENT") return false; refuse("UNSAFE_FILE"); }
  if (unsafeRegular(st)) refuse("UNSAFE_FILE");
  return st;
}
// The writer's lock must be on stable storage before the first mutation.
function syncPrivateDirectory(dir) {
  const fd=fs.openSync(dir,fs.constants.O_RDONLY|fs.constants.O_DIRECTORY|fs.constants.O_NOFOLLOW);
  try {
    const st=fs.fstatSync(fd);
    if (!st.isDirectory() || st.uid !== process.getuid() || (st.mode & 0o077))
      refuse("UNSAFE_DIRECTORY");
    fs.fsyncSync(fd);
  } finally {fs.closeSync(fd);}
}
function releaseWriterLock(dir, lock, lockfd) {
  // Only release the exact inode created by this writer. A replaced lock
  // is NOT this process's lock and must never be removed by cleanup.
  try {
    const held=fs.fstatSync(lockfd);
    let named;
    try {named=fs.lstatSync(lock);} catch {refuse("UNSAFE_LOCK");}
    if (!named.isFile() || named.isSymbolicLink()
        || named.uid !== process.getuid() || (named.mode & 0o077)
        || named.nlink !== 1 || named.dev !== held.dev || named.ino !== held.ino)
      refuse("UNSAFE_LOCK");
    fs.unlinkSync(lock);
  } finally {fs.closeSync(lockfd);}
  syncPrivateDirectory(dir);
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
  const expected=secureRegular(file);
  if (!expected) return empty();
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    const st = fs.fstatSync(fd);
    if (unsafeRegular(st) || st.dev !== expected.dev || st.ino !== expected.ino)
      refuse("UNSAFE_FILE");
    const raw = fs.readFileSync(fd,{encoding:"utf8"});
    if (Buffer.byteLength(raw,"utf8") > MAX_BYTES) refuse("STORE_LIMIT");
    let doc;
    try { doc = JSON.parse(raw); } catch { refuse("CORRUPT_STORE"); }
    if (!validDocument(doc)) refuse("CORRUPT_STORE");
    return doc;
  } finally { fs.closeSync(fd); }
}
function save(dir,doc,markCommitUncertain) {
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
    // Once rename is attempted, its outcome may be unknown after I/O or
    // process failure. Mark BEFORE the syscall and retain the lock until
    // a confirmed directory fsync establishes durable commit.
    markCommitUncertain();
    fs.renameSync(temp,file);
    syncPrivateDirectory(dir);
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
  let uncertainCommit=false;
  let durableCommit=false;
  try {
    fs.fsyncSync(lockfd);
    syncPrivateDirectory(dir);
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
    save(dir,next,()=>{ uncertainCommit=true; });
    durableCommit=true;
    return next;
  } catch(error) {
    if (uncertainCommit && !durableCommit)
      refuse("COMMIT_OUTCOME_UNKNOWN");
    throw error;
  } finally {
    if (uncertainCommit && !durableCommit) {
      // Deliberately strand the durable lock; an operator must inspect
      // the last revision before any manual recovery. No auto-retry.
      fs.closeSync(lockfd);
    } else {
      releaseWriterLock(dir,lock,lockfd);
    }
  }
}
// One line is sufficient: the writer must finish even if a Quickshell
// caller leaves stdin open. Do not allocate an unbounded stdin buffer.
function readBoundedCommand(fd) {
  const parts=[];
  let total=0;
  while (total <= MAX_COMMAND_BYTES) {
    const part=Buffer.allocUnsafe(Math.min(1024,MAX_COMMAND_BYTES+1-total));
    const n=fs.readSync(fd,part,0,part.length,null);
    if (n===0) refuse("INVALID_INPUT_FRAME");
    const chunk=part.subarray(0,n);
    total+=n;
    if (total>MAX_COMMAND_BYTES) refuse("INVALID_INPUT_FRAME");
    const newline=chunk.indexOf(10);
    if (newline!==-1) {
      if (newline!==chunk.length-1) refuse("INVALID_INPUT_FRAME");
      parts.push(chunk);
      return Buffer.concat(parts).toString("utf8");
    }
    parts.push(chunk);
  }
  refuse("INVALID_INPUT_FRAME");
}
export {run,rootDirectory,Refusal};
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  try {
    const raw=readBoundedCommand(0);
    let command;
    try {command=JSON.parse(raw);} catch {refuse("INVALID_JSON");}
    const doc=run(command);
    process.stdout.write(PREFIX+"RESULT "+JSON.stringify(doc)+"\n");
  } catch(error) {
    process.stderr.write(PREFIX+"ERROR "+(error instanceof Refusal ? error.message : "OPERATION_FAILED")+"\n");
    process.exitCode=1;
  }
}
