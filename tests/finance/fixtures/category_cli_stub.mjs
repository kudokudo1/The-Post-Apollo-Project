// Disposable fictional data only, never opens network sockets.
import {readFile,writeFile} from "node:fs/promises";
const path=process.env.FINANCEW_FAKE_LEDGER_PATH;
if(!path)throw Error("no-fictional-category-ledger");
let initialized=false;
const read=async()=>JSON.parse(await readFile(path,"utf8"));
const save=async value=>writeFile(path,JSON.stringify(value));
export async function init(opts) {
  if(opts.serverURL!=="http://127.0.0.1:5006"
      || opts.password!=="fictional-password")throw Error("invalid-fictional-source");
  initialized=true;
}
export async function downloadBudget(syncId) {
  if(!initialized || syncId!=="fictional-sync-123")throw Error("invalid-fictional-budget");
}
export async function getCategoryGroups() {
  const data=await read();
  return data.groups;
}
export async function getCategories() {
  const data=await read();
  return data.categories;
}
export async function createCategory(category) {
  if(Object.keys(category).sort().join(",")!=="group_id,is_income,name"
      || category.is_income!==false)throw Error("unexpected-create-fields");
  const data=await read();
  data.events.push("create");
  const id="fictional-category-new";
  data.categories.push({...category,id});
  await save(data);
  return id;
}
export async function updateCategory(id,fields) {
  if(Object.keys(fields).join(",")!=="name")throw Error("unexpected-update-fields");
  const data=await read();
  const item=data.categories.find(c=>c.id===id);
  if(!item)throw Error("missing-fictional-category");
  item.name=fields.name;
  data.events.push("update");
  await save(data);
  return null;
}
export async function sync() {
  const data=await read();
  data.events.push("sync");
  await save(data);
  if(process.env.FINANCEW_FAKE_FAIL_STAGE==="sync")
    throw Error("fictional-sync-dropped");
}
export async function shutdown() {}
