#!/usr/bin/env node
// FinanceW local drafts. Never imports Actual, reads credentials, or invokes a budget writer.
// Financial text is stored plaintext in a mode-0600 private file, not logs.
import {readFile,writeFile,lstat,mkdir,open,rename,rm} from "node:fs/promises";
import {homedir} from "node:os";
import {join} from "node:path";
import {randomUUID} from "node:crypto";

const directory=join(homedir(),".local","state","financew","drafts");
const index=join(directory,"index.json");
const maxItems=50;
class Refusal extends Error {constructor(code) {super(code);this.code=code;}}
function refuse(code) {throw new Refusal(code);}
function validSource(value) {return typeof value==="string" && /^[a-f0-9]{64}$/.test(value);}
function validMonth(value) {return typeof value==="string" && /^\d{4}-(0[1-9]|1[0-2])$/.test(value);}
function validId(value) {return typeof value==="string"
  && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);}
function safeText(value,max) {return typeof value==="string" && value.length<=max
  && !/[\u0000-\u001f\u007f]/.test(value);}
function validDraft(value) {
  return value && typeof value==="object" && !Array.isArray(value)
    && validSource(value.sourceKey) && validMonth(value.month)
    && safeText(value.accountId,120) && /^[a-zA-Z0-9_-]{1,120}$/.test(value.accountId)
    && safeText(value.dateText,10) && /^[0-9-]{0,10}$/.test(value.dateText)
    && safeText(value.payeeText,120)
    && safeText(value.amountText,18) && /^[0-9.]{0,18}$/.test(value.amountText)
    && (value.direction==="expense" || value.direction==="income");
}
async function ensurePrivateDirectory() {
  await mkdir(directory,{recursive:true,mode:0o700});
  const meta=await lstat(directory);
  if(!meta.isDirectory() || (meta.mode & 0o077)!==0) refuse("unsafe-directory");
}
async function loadIndex() {
  let info;
  try {info=await lstat(index);}
  catch(error) {
    if(error.code==="ENOENT") return {version:1,revision:0,drafts:[]};
    refuse("read-failed");
  }
  if(!info.isFile() || (info.mode & 0o077)!==0 || info.size>65536)
    refuse("unsafe-index");
  let data;
  try {data=JSON.parse(await readFile(index,"utf8"));}
  catch {refuse("corrupt-index");}
  if(!data || data.version!==1 || !Number.isSafeInteger(data.revision)
      || data.revision<0 || !Array.isArray(data.drafts)
      || data.drafts.length>maxItems || !data.drafts.every(item=>
        validId(item?.id) && validDraft(item)
          && safeText(item.createdAt,40) && safeText(item.updatedAt,40)))
    refuse("corrupt-index");
  if(new Set(data.drafts.map(item=>item.id)).size!==data.drafts.length)
    refuse("corrupt-index");
  return data;
}
async function commitIndex(data) {
  const temporary=join(directory,randomUUID()+".tmp");
  let file;
  try {
    file=await open(temporary,"wx",0o600);
    await file.writeFile(JSON.stringify(data)+"\n");
    await file.sync();
    await file.close();file=null;
    // Never follow an existing symlink or silently overwrite unsafe storage.
    try {
      const old=await lstat(index);
      if(!old.isFile() || (old.mode & 0o077)!==0) refuse("unsafe-index");
    } catch(error) {if(error.code!=="ENOENT") throw error;}
    await rename(temporary,index);
    const parent=await open(directory,"r");
    try {await parent.sync();} finally {await parent.close();}
  } finally {
    if(file) await file.close();
    await rm(temporary,{force:true}).catch(()=>{});
  }
}
async function fromStdin() {
  let input="";
  for await(const chunk of process.stdin) {
    input+=chunk.toString("utf8");
    if(input.length>4096) refuse("input-too-large");
    if(input.includes("\n")) break;
  }
  const parts=input.split("\n");
  if(parts.length!==2 || parts[1]!=="") refuse("invalid-frame");
  try {return JSON.parse(parts[0]);}
  catch {refuse("invalid-json");}
}
function responseFor(data,sourceKey,month) {
  return {revision:data.revision,drafts:data.drafts
    .filter(x=>x.sourceKey===sourceKey && x.month===month)};
}
async function main() {
  const command=await fromStdin();
  if(!command || typeof command!=="object" || Array.isArray(command)
      || !["list","upsert","delete"].includes(command.action)
      || !validSource(command.sourceKey) || !validMonth(command.month))
    refuse("invalid-command");
  await ensurePrivateDirectory();
  const data=await loadIndex();
  if(command.action!=="list") {
    if(!Number.isSafeInteger(command.expectedRevision)
        || command.expectedRevision!==data.revision)
      refuse("stale-index");
    if(command.action==="upsert") {
      const draft=command.draft;
      if(!validDraft(draft) || draft.sourceKey!==command.sourceKey
          || draft.month!==command.month) refuse("invalid-draft");
      const now=new Date().toISOString();
      const requestedId=command.id;
      let prior=null;
      if(requestedId!=null) {
        if(!validId(requestedId)) refuse("invalid-id");
        prior=data.drafts.find(x=>x.id===requestedId);
        if(!prior || prior.sourceKey!==command.sourceKey
            || prior.month!==command.month) refuse("draft-not-found");
      } else if(data.drafts.length>=maxItems) refuse("draft-limit");
      const saved={id:prior?.id || randomUUID(),sourceKey:draft.sourceKey,
        month:draft.month,accountId:draft.accountId,dateText:draft.dateText,
        payeeText:draft.payeeText,amountText:draft.amountText,
        direction:draft.direction,createdAt:prior?.createdAt||now,updatedAt:now};
      if(prior) data.drafts=data.drafts.map(x=>x.id===prior.id?saved:x);
      else data.drafts.push(saved);
    } else {
      if(!validId(command.id)) refuse("invalid-id");
      const entry=data.drafts.find(x=>x.id===command.id);
      if(!entry || entry.sourceKey!==command.sourceKey
          || entry.month!==command.month) refuse("draft-not-found");
      data.drafts=data.drafts.filter(x=>x.id!==command.id);
    }
    data.revision+=1;
    await commitIndex(data);
  }
  process.stdout.write("FINANCEW_DRAFT_RESULT "
    +JSON.stringify(responseFor(data,command.sourceKey,command.month))+"\n");
}
main().catch(error=>{
  const code=error instanceof Refusal?error.code:"operation-failed";
  process.stderr.write("FINANCEW_DRAFT_ERROR "+code+"\n");
  process.exitCode=1;
});
