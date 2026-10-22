#!/usr/bin/env node
// Read-only FinanceW allocation authorization status. Never creates a
// permit, reads Actual credentials, imports Actual, or writes any file.
import {lstat,readFile} from "node:fs/promises";
import {homedir} from "node:os";
import {join} from "node:path";

const path=join(homedir(),".config","financew","allocation-writes-enabled");
async function status() {
  let info;
  try {info=await lstat(path);}
  catch (error) {
    if(error.code==="ENOENT")return "locked";
    return "error";
  }
  if (!info.isFile() || (info.mode & 0o077)!==0 || info.size>128)
    return "unsafe";
  try {
    const marker=(await readFile(path,"utf8")).trim();
    return marker==="FINANCEW_ALLOCATION_WRITES_APPROVED"
      ? "permit-present" : "unsafe";
  } catch {return "error";}
}
try {
  process.stdout.write("FINANCEW_ALLOCATION_GATE "+await status()+"\n");
} catch {
  process.stdout.write("FINANCEW_ALLOCATION_GATE error\n");
  process.exitCode=1;
}
