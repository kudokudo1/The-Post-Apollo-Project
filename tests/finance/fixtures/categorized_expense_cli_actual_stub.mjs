// Fake local ledger for protected CLI tests: zero networking, real data or
// Actual credentials. All bytes are in the test runner's disposable HOME.
import {readFile,writeFile} from "node:fs/promises";

const file=process.env.FINANCEW_FAKE_LEDGER_PATH;
if(!file)throw Error("missing-fictional-ledger");
let initialized=false;
async function read(){return JSON.parse(await readFile(file,"utf8"));}
async function write(data){await writeFile(file,JSON.stringify(data));}
export async function init(opts) {
  if(opts.serverURL!=="http://127.0.0.1:5006"
      ||opts.password!=="fictional-password")
    throw Error("unexpected-test-source");
  initialized=true;
}
export async function downloadBudget(id){
  if(!initialized || id!=="fictional-sync-123")
    throw Error("unexpected-test-budget");
}
export async function getAccounts(){
  const d=await read();d.events.push("accounts");await write(d);
  return d.accounts;
}
export async function getBudgetMonth(month){
  if(month!=="2026-11")throw Error("wrong-test-month");
  const d=await read();d.events.push("budget");await write(d);
  return d.budget;
}
export async function getTransactions(accountId,from,to){
  if(accountId!=="fictional-checking" || from!=="2026-11-01"
      || to!=="2026-11-31")throw Error("unexpected-read-range");
  const d=await read();d.events.push("transactions");await write(d);
  const rows=d.transactions.filter(t=>t.account===accountId
    && t.date>=from && t.date<=to);
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="wrong-readback-category"
      &&d.events.includes("sync"))
    return rows.map(x=>({...x,category:"fictional-other"}));
  return rows;
}
export async function addTransactions(accountId,entries,options){
  if(accountId!=="fictional-checking" || entries.length!==1
      ||options?.runTransfers!==false ||options?.learnCategories!==false)
    throw Error("unexpected-test-create");
  if(Object.keys(entries[0]).sort().join(",")
      !=="amount,category,cleared,date,id,imported_id,payee_name")
    throw Error("unexpected-test-transaction-fields");
  if(entries[0].category!=="fictional-groceries")
    throw Error("category-field-not-supplied");
  const data=await read();
  data.events.push("add");
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="before-add"){
    await write(data);
    throw Error("injected-add-failure");
  }
  const row={...entries[0],account:accountId};
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="wrong-category")
    row.category="fictional-wrong";
  data.transactions.push(row);
  await write(data);
  return process.env.FINANCEW_FAKE_FAIL_STAGE==="bad-ack"?"bad":"ok";
}
export async function sync(){
  const d=await read();d.events.push("sync");await write(d);
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="sync")
    throw Error("injected-sync-failure");
}
export async function shutdown(){}
