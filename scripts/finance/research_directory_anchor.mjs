// FinanceW Research M10d: Linux-only read-only directory descriptor prototype.
// This module cannot create folders, rename files, write, unlock or retry.
// It is NOT wired to the existing M2 writer or FinanceW UI.
import fs from "node:fs";
import path from "node:path";

const DIRECTORY_FLAGS = fs.constants.O_RDONLY | fs.constants.O_DIRECTORY
  | fs.constants.O_NOFOLLOW | (fs.constants.O_CLOEXEC || 0);
const FILE_FLAGS = fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW
  | fs.constants.O_NONBLOCK | (fs.constants.O_CLOEXEC || 0);
const MAX_READ_BYTES = 500000;
const PROCFD = "/proc/self/fd";
const ALLOWED_FILES = new Set(["investigations.json", "investigations.lock"]);

export class ResearchAnchorRefusal extends Error {}
function refuse(code) { throw new ResearchAnchorRefusal(code); }
function validateTarget(target) {
  if (typeof target !== "string" || !path.isAbsolute(target)
      || target.length > 4096 || path.normalize(target) !== target
      || target === path.parse(target).root)
    refuse("INVALID_STORAGE_PATH");
  const parts=target.slice(path.parse(target).root.length).split(path.sep);
  if (parts.length===0 || parts.some(p=>!p || p==="." || p===".."))
    refuse("INVALID_STORAGE_PATH");
  return parts;
}
function procChild(fd,name) { return `${PROCFD}/${fd}/${name}`; }
function privateDir(fd) {
  const st=fs.fstatSync(fd);
  if (!st.isDirectory() || st.uid!==process.getuid() || (st.mode&0o077))
    refuse("UNSAFE_STORAGE_DIRECTORY");
  return st;
}
function secureFile(fd) {
  const st=fs.fstatSync(fd);
  if (!st.isFile() || st.uid!==process.getuid() || (st.mode&0o077)
      || st.nlink!==1)
    refuse("UNSAFE_STORAGE_FILE");
  return st;
}
/**
 * Linux native read-only proof: enter every ancestor using the *previous*
 * pinned directory descriptor rather than resolving the mutable full path.
 * The /proc/self/fd spelling serves as a Linux descriptor-relative handle.
 * This is a prototype requiring independent review, not a writer grant.
 */
export function openResearchDirectoryAnchor(target) {
  const parts=validateTarget(target);
  if (process.platform!=="linux") refuse("LINUX_ONLY");
  // Require Linux procfs instead of silently falling back to unsafe paths.
  if (!fs.existsSync(PROCFD)) refuse("PROCFS_UNAVAILABLE");
  let fd;
  try {
    fd=fs.openSync(path.parse(target).root,DIRECTORY_FLAGS);
    for (const component of parts) {
      let next;
      try {next=fs.openSync(procChild(fd,component),DIRECTORY_FLAGS);}
      catch {refuse("STORAGE_PATH_UNAVAILABLE");}
      fs.closeSync(fd);
      fd=next;
    }
    const identity=privateDir(fd);
    const pinned=fd;
    fd=undefined;
    let closed=false;
    return Object.freeze({
      get readOnly() {return true;},
      get canWrite() {return false;},
      get canUnlock() {return false;},
      get canRetry() {return false;},
      get directoryIdentity() {
        if (closed) refuse("ANCHOR_CLOSED");
        const current=privateDir(pinned);
        if (current.dev!==identity.dev || current.ino!==identity.ino)
          refuse("DIRECTORY_IDENTITY_CHANGED");
        return Object.freeze({device:current.dev,inode:current.ino});
      },
      readFile(name,limit=MAX_READ_BYTES) {
        if (closed) refuse("ANCHOR_CLOSED");
        if (!ALLOWED_FILES.has(name) || !Number.isSafeInteger(limit)
            || limit<1 || limit>MAX_READ_BYTES)
          refuse("INVALID_READ_REQUEST");
        privateDir(pinned);
        let fileFd;
        try {
          try {fileFd=fs.openSync(procChild(pinned,name),FILE_FLAGS);}
          catch(e) {
            if (e.code==="ENOENT") return null;
            refuse("UNSAFE_STORAGE_FILE");
          }
          const st=secureFile(fileFd);
          if (st.size>limit) refuse("STORAGE_FILE_LIMIT");
          // Never allocate an unbounded buffer, even if the inode grows
          // between fstat and the following read calls.
          const buffer=Buffer.alloc(limit+1);
          let total=0;
          while (total<buffer.length) {
            const n=fs.readSync(fileFd,buffer,total,buffer.length-total,null);
            if(n===0) break;
            total+=n;
          }
          if(total>limit) refuse("STORAGE_FILE_LIMIT");
          return buffer.subarray(0,total).toString("utf8");
        } finally {
          if(fileFd!==undefined) fs.closeSync(fileFd);
        }
      },
      close() {
        if (!closed) {closed=true;fs.closeSync(pinned);}
      }
    });
  } catch(e) {
    if (e instanceof ResearchAnchorRefusal) throw e;
    refuse("STORAGE_PATH_UNAVAILABLE");
  } finally {
    if(fd!==undefined) fs.closeSync(fd);
  }
}
