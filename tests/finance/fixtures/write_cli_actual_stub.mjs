// Isolated fictional ledger for the writer CLI contract tests.
// This is not Actual and never opens a socket or a personal budget.
import {readFile,writeFile} from "node:fs/promises";

const file=process.env.FINANCEW_FAKE_LEDGER_PATH;
if (!file) throw new Error("missing-fictional-ledger");
let initialized=false;
async function read() {return JSON.parse(await readFile(file,"utf8"));}
async function write(data) {await writeFile(file,JSON.stringify(data));}

export async function init(options) {
  if (options.serverURL !== "http://127.0.0.1:5006"
      || options.password !== "fictional-password")
    throw new Error("unexpected-test-source");
  initialized=true;
}
export async function downloadBudget(syncId) {
  if (!initialized || syncId !== "fictional-sync-123")
    throw new Error("unexpected-test-budget");
}
export async function getAccounts() {return (await read()).accounts;}
export async function getTransactions(accountId,from,to) {
  return (await read()).transactions.filter(t => t.account === accountId
    && t.date >= from && t.date <= to);
}
export async function addTransactions(accountId,entries,options) {
  if (options?.runTransfers !== false
      || options?.learnCategories !== false || entries.length !== 1)
    throw new Error("unexpected-test-mutation");
  const data=await read();
  const entry={account:accountId,...entries[0]};
  data.transactions.push(entry);
  data.events.push("add");
  await write(data);
  return "ok";
}
export async function updateTransaction(id,fields) {
  if (Object.keys(fields).sort().join(",") !== "amount,date")
    throw new Error("unexpected-test-edit");
  const data=await read();
  const entry=data.transactions.find(t=>t.id===id);
  if (!entry) throw new Error("unknown-test-transaction");
  Object.assign(entry,fields);
  data.events.push("update");
  await write(data);
}
export async function sync() {
  const data=await read();
  data.events.push("sync");
  await write(data);
  if (process.env.FINANCEW_FAKE_FAIL_STAGE === "sync")
    throw new Error("fictional-sync-interruption");
}
export async function shutdown() {}
