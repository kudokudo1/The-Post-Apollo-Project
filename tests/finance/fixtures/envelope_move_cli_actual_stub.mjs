// FICTIONAL Actual API: isolated process-local ledger and deterministic failures.
// Deliberately no network, credentials, user files or actual-app dependency.
import {readFile,writeFile} from "node:fs/promises";
const file=process.env.FINANCEW_FAKE_LEDGER_PATH;
if(!file)throw Error("missing-fictional-ledger");
let initialized=false;
async function read(){return JSON.parse(await readFile(file,"utf8"));}
async function write(data){await writeFile(file,JSON.stringify(data));}
export async function init(opts){
  if(opts.serverURL!=="http://127.0.0.1:5006"
      ||opts.password!=="fictional-password")
    throw Error("unexpected-test-source");
  initialized=true;
}
export async function downloadBudget(id){
  if(!initialized||id!=="fictional-sync-123")
    throw Error("unexpected-test-budget");
}
export async function getBudgetMonth(month){
  if(!/^20\d{2}-(0[1-9]|1[0-2])$/.test(month))
    throw Error("bad-test-month");
  const data=await read();
  if(!data.budget)throw Error("missing-fictional-budget");
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="readback-mismatch"
      && data.events.includes("sync")){
    data.budget.categoryGroups[0].categories[1].balance++;
  }
  return data.budget;
}
export async function setBudgetAmount(month,categoryId,target){
  const data=await read();
  const attempts=data.events.filter(x=>x==="set-allocation").length;
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="before-second-set"
      && attempts===1)
    throw Error("fictional-second-step-refused");
  const matches=(data.budget.categoryGroups||[])
    .flatMap(group=>group.categories||[])
    .filter(cat=>cat.id===categoryId);
  if(matches.length!==1||!Number.isSafeInteger(target))
    throw Error("invalid-test-category");
  const delta=target-matches[0].budgeted;
  matches[0].budgeted=target;
  matches[0].balance+=delta;
  data.budget.toBudget-=delta;
  data.events.push("set-allocation");
  await write(data);
}
export async function sync(){
  const data=await read();
  data.events.push("sync");
  await write(data);
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="sync")
    throw Error("fictional-sync-interruption");
}
export async function shutdown(){}
