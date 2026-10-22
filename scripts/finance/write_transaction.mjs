#!/usr/bin/env node
// FinanceW D9: explicit, guarded transaction writer. Nothing writes unless a
// mode-0600 operator-owned local authorization file is present. No argv data.
// One JSON command over stdin; no automatic retries or exposed financial logs.
import {readFile, lstat, mkdir, open, mkdtemp, rm, chmod} from "node:fs/promises";
import {tmpdir, homedir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {readActualServerURL} from "./source_config.mjs";
import {validateTransactionCommand,executeTransaction,TransactionRefusal}
  from "./transaction_guard.mjs";

const config = join(homedir(), ".config", "financew");
const ledgerDir = join(homedir(), ".local", "state", "financew", "operations");
function errorCode(e) {
  return e instanceof TransactionRefusal ? e.code : "operation-failed";
}
async function privateFile(path) {
  const st = await lstat(path);
  if (!st.isFile() || (st.mode & 0o077) !== 0)
    throw new TransactionRefusal("unsafe-private-file");
  return (await readFile(path,"utf8")).trim();
}
async function inputFromStdin() {
  let input = "";
  for await (const piece of process.stdin) {
    input += piece.toString("utf8");
    if (input.length > 4096) throw new TransactionRefusal("input-too-large");
    if (input.includes("\n")) break;
  }
  const parts = input.split("\n");
  if (parts.length !== 2 || parts[1] !== "")
    throw new TransactionRefusal("invalid-input-frame");
  let object;
  try { object = JSON.parse(parts[0]); }
  catch { throw new TransactionRefusal("invalid-json"); }
  return validateTransactionCommand(object);
}

async function main() {
  // Authorization is never set by the widget, and must be deliberately
  // provisioned by the operator on the local machine.
  let permit;
  try { permit = await privateFile(join(config,"transaction-writes-enabled")); }
  catch { throw new TransactionRefusal("writes-disabled"); }
  if (permit !== "FINANCEW_TRANSACTION_WRITES_APPROVED")
    throw new TransactionRefusal("writes-disabled");

  const cmd = await inputFromStdin();
  await mkdir(ledgerDir,{recursive:true,mode:0o700});
  const dirInfo = await lstat(ledgerDir);
  if (!dirInfo.isDirectory() || (dirInfo.mode & 0o077) !== 0)
    throw new TransactionRefusal("unsafe-journal-directory");
  // Dead owner / crash leaves the lock behind. Fail closed until manually
  // investigated, never delete a stale-looking lock automatically.
  const lockPath = join(ledgerDir,".write-lock");
  let lock;
  try {lock = await open(lockPath,"wx",0o600);}
  catch {throw new TransactionRefusal("write-in-progress-or-recovery-needed");}
  let api, working;
  let attempted = false;
  try {
    working = await mkdtemp(join(tmpdir(),"financew-write-"));
    await chmod(working,0o700);
    const serverURL = await readActualServerURL();
    const password = await privateFile(join(config,"actual-password"));
    const syncId = await privateFile(join(config,"actual-sync-id"));
    if (!/^[a-zA-Z0-9-]{8,80}$/.test(syncId))
      throw new TransactionRefusal("invalid-sync-id");
    const journalPath = join(ledgerDir,cmd.requestId+".json");
    // A repeated request identity is always blocked, including after crash.
    // The journal carries only a command digest, never transaction details.
    const digest = createHash("sha256")
      .update(JSON.stringify(cmd)).digest("hex");
    const recordAttempt = async () => {
      let file;
      try {file = await open(journalPath,"wx",0o600);}
      catch {throw new TransactionRefusal("operation-already-attempted");}
      try {
        await file.writeFile(JSON.stringify({
          version:1,hash:digest,action:cmd.action,attemptedAt:new Date().toISOString()
        })+"\n");
        await file.sync();
        attempted = true;
      } finally {await file.close();}
    };
    api = await import("@actual-app/api");
    await api.init({dataDir:working,serverURL,password});
    const encryptionPath = process.env.ACTUAL_ENCRYPTION_PASSWORD_FILE;
    const encryptionPassword = encryptionPath
      ? await privateFile(encryptionPath) : null;
    await api.downloadBudget(syncId,encryptionPassword
      ? {password:encryptionPassword} : undefined);
    const result = await executeTransaction({api, input:cmd, recordAttempt});
    return result.status;
  } catch (error) {
    if (attempted) return "uncertain";
    throw error;
  } finally {
    if (api) {
      try { await api.shutdown(); } catch { /* never retry automatically */ }
    }
    if (working) await rm(working,{recursive:true,force:true});
    if (lock) await lock.close();
    await rm(lockPath,{force:true});
  }
}

try {
  const status = await main();
  process.stdout.write("FINANCEW_TRANSACTION_RESULT "+status+"\n");
} catch (error) {
  process.stdout.write("FINANCEW_TRANSACTION_RESULT blocked:"
    + errorCode(error)+"\n");
  process.exitCode = 1;
}
