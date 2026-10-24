// FinanceW Categories M2 // category create/rename policy.
// No filesystem, credentials, local permissions, or Actual imports.
// The caller must supply independently authorized, source-bound durable
// journaling and recordAttempt() before any mutating API call.
export class CategoryRefusal extends Error {
  constructor(code){super(code);this.code=code;}
}
const refuse=code=>{throw new CategoryRefusal(code);};
const idPattern=/^[A-Za-z0-9-]{4,80}$/;
const requestPattern=/^[0-9a-f]{32}$/;
const sourcePattern=/^[0-9a-f]{64}$/;
const monthPattern=/^20\d{2}-(0[1-9]|1[0-2])$/;

function name(value) {
  if(typeof value!=="string")refuse("invalid-name");
  const trimmed=value.trim().replace(/\s+/g," ");
  if(!trimmed || trimmed.length>80 || /[\u0000-\u001f\u007f]/.test(value))
    refuse("invalid-name");
  return trimmed;
}
const norm=value=>value.trim().toLowerCase();
export function validateCategoryCommand(input) {
  if(!input || typeof input!=="object" || Array.isArray(input))
    refuse("invalid-command");
  const expected=["mode","requestId","sourceKey","month","groupId",
    "categoryId","expectedName","proposedName"];
  const fields=Object.keys(input);
  if(fields.length!==expected.length || fields.some(k=>!expected.includes(k)))
    refuse("unexpected-fields");
  if(!["create","rename"].includes(input.mode))refuse("invalid-mode");
  if(typeof input.requestId!=="string" || !requestPattern.test(input.requestId))
    refuse("invalid-request-id");
  if(typeof input.sourceKey!=="string" || !sourcePattern.test(input.sourceKey))
    refuse("invalid-source-key");
  if(typeof input.month!=="string" || !monthPattern.test(input.month))
    refuse("invalid-month");
  if(typeof input.groupId!=="string" || !idPattern.test(input.groupId))
    refuse("invalid-group-id");
  const proposedName=name(input.proposedName);
  if(proposedName!==input.proposedName)refuse("noncanonical-name");
  if(input.mode==="create") {
    if(input.categoryId!=="" || input.expectedName!=="")
      refuse("unexpected-create-target");
  } else {
    if(typeof input.categoryId!=="string" || !idPattern.test(input.categoryId))
      refuse("invalid-category-id");
    const expectedName=name(input.expectedName);
    if(expectedName!==input.expectedName)refuse("noncanonical-expected-name");
    if(norm(expectedName)===norm(proposedName))refuse("unchanged-name");
  }
  return {...input};
}
export function preflightCategory(input,groups,categories) {
  const cmd=validateCategoryCommand(input);
  if(!Array.isArray(groups) || !Array.isArray(categories))
    refuse("invalid-category-source");
  const parents=groups.filter(g=>g && g.id===cmd.groupId
    && g.is_income!==true && typeof g.name==="string");
  if(parents.length!==1)refuse("stale-category-group");
  // Compare all categories, including hidden ones. Names alone are not IDs.
  if(categories.some(c=>!c || typeof c.id!=="string"
      || typeof c.group_id!=="string" || typeof c.name!=="string"))
    refuse("invalid-category-source");
  const matches=categories.filter(c=>c.group_id===cmd.groupId
    && norm(c.name)===norm(cmd.proposedName));
  if(matches.length && (cmd.mode==="create"
      || matches.some(c=>c.id!==cmd.categoryId)))
    refuse("possible-duplicate-category");
  if(cmd.mode==="rename") {
    const current=categories.filter(c=>c.id===cmd.categoryId);
    if(current.length!==1 || current[0].group_id!==cmd.groupId
        || current[0].name!==cmd.expectedName
        || current[0].is_income===true)
      refuse("stale-category");
  }
  return cmd;
}
export async function executeCategory({api,input,recordAttempt}) {
  if(!api || typeof recordAttempt!=="function"
      || typeof api.getCategoryGroups!=="function"
      || typeof api.getCategories!=="function"
      || typeof api.createCategory!=="function"
      || typeof api.updateCategory!=="function"
      || typeof api.sync!=="function")
    refuse("missing-write-guards");
  const cmd=validateCategoryCommand(input);
  const groups=await api.getCategoryGroups();
  const categories=await api.getCategories();
  preflightCategory(cmd,groups,categories);
  // Every result after this point must be treated as UNCERTAIN unless
  // it has been synced and independently read back.
  await recordAttempt(cmd);
  let createdId="";
  if(cmd.mode==="create") {
    createdId=await api.createCategory({
      name:cmd.proposedName,group_id:cmd.groupId,is_income:false
    });
    if(typeof createdId!=="string" || !idPattern.test(createdId))
      refuse("uncertain-write");
  } else {
    await api.updateCategory(cmd.categoryId,{name:cmd.proposedName});
  }
  await api.sync();
  const after=await api.getCategories();
  const finalGroups=await api.getCategoryGroups();
  if(!Array.isArray(after) || !Array.isArray(finalGroups)
      || finalGroups.filter(g=>g && g.id===cmd.groupId
        && g.is_income!==true).length!==1)
    refuse("uncertain-write");
  const targetId=cmd.mode==="create"?createdId:cmd.categoryId;
  const saved=after.filter(c=>c && c.id===targetId);
  const duplicates=after.filter(c=>c && c.group_id===cmd.groupId
    && typeof c.name==="string"
    && norm(c.name)===norm(cmd.proposedName));
  if(saved.length!==1 || saved[0].name!==cmd.proposedName
      || saved[0].group_id!==cmd.groupId || saved[0].is_income===true
      || duplicates.length!==1 || duplicates[0].id!==targetId)
    refuse("uncertain-write");
  return {status:"committed"};
}
