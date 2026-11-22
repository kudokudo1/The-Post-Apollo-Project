// FinanceW M5 // category-group create/rename write policy.
// Pure validation and one exact mutation. Caller must separately enforce
// operator permit, source identity, shared lock and durable attempt journal.
export class CategoryGroupRefusal extends Error {
  constructor(code){super(code);this.code=code;}
}
const refuse=code=>{throw new CategoryGroupRefusal(code);};
const id=/^[A-Za-z0-9-]{4,80}$/;
const request=/^[0-9a-f]{32}$/;
const source=/^[0-9a-f]{64}$/;
const month=/^20\d{2}-(0[1-9]|1[0-2])$/;
const norm=value=>value.trim().toLowerCase();
function groupName(value){
  if(typeof value!=="string")refuse("invalid-name");
  const trimmed=value.trim().replace(/\s+/g," ");
  if(!trimmed || trimmed.length>80 || /[\u0000-\u001f\u007f]/.test(value))
    refuse("invalid-name");
  if(norm(trimmed)==="income")refuse("reserved-income-group");
  if(trimmed!==value)refuse("noncanonical-name");
  return value;
}
export function validateGroupCommand(input){
  if(!input || typeof input!=="object" || Array.isArray(input))
    refuse("invalid-command");
  const keys=["mode","requestId","sourceKey","month","groupId",
    "expectedName","proposedName"];
  const present=Object.keys(input);
  if(present.length!==keys.length || present.some(k=>!keys.includes(k)))
    refuse("unexpected-fields");
  if(input.mode!=="create" && input.mode!=="rename")refuse("invalid-mode");
  if(typeof input.requestId!=="string" || !request.test(input.requestId))
    refuse("invalid-request-id");
  if(typeof input.sourceKey!=="string" || !source.test(input.sourceKey))
    refuse("invalid-source-key");
  if(typeof input.month!=="string" || !month.test(input.month))
    refuse("invalid-month");
  groupName(input.proposedName);
  if(input.mode==="create"){
    if(input.groupId!=="" || input.expectedName!=="")
      refuse("unexpected-create-target");
  }else{
    if(typeof input.groupId!=="string" || !id.test(input.groupId))
      refuse("invalid-group-id");
    groupName(input.expectedName);
    if(norm(input.expectedName)===norm(input.proposedName))
      refuse("unchanged-name");
  }
  return {...input};
}
export function preflightGroup(input,groups){
  const cmd=validateGroupCommand(input);
  if(!Array.isArray(groups) || groups.some(g=>!g
      || typeof g.id!=="string" || !id.test(g.id)
      || typeof g.name!=="string"
      || typeof g.is_income!=="boolean"))
    refuse("invalid-group-source");
  if(new Set(groups.map(g=>g.id)).size!==groups.length)
    refuse("ambiguous-group-source");
  if(groups.some(g=>g.name.trim()
      && norm(g.name)===norm(cmd.proposedName)
      && (cmd.mode==="create" || g.id!==cmd.groupId)))
    refuse("possible-duplicate-group");
  if(cmd.mode==="rename"){
    const matches=groups.filter(g=>g.id===cmd.groupId);
    if(matches.length!==1 || matches[0].is_income
        || matches[0].name!==cmd.expectedName)
      refuse("stale-group");
  }
  return cmd;
}
export async function executeGroup({api,input,recordAttempt}){
  if(!api || typeof recordAttempt!=="function"
      || typeof api.getCategoryGroups!=="function"
      || typeof api.createCategoryGroup!=="function"
      || typeof api.updateCategoryGroup!=="function"
      || typeof api.sync!=="function")
    refuse("missing-write-guards");
  const cmd=validateGroupCommand(input);
  preflightGroup(cmd,await api.getCategoryGroups());
  await recordAttempt(cmd); // persisted BEFORE first mutation
  let created="";
  if(cmd.mode==="create"){
    created=await api.createCategoryGroup({name:cmd.proposedName,is_income:false});
    if(typeof created!=="string" || !id.test(created))
      refuse("uncertain-write");
  }else{
    await api.updateCategoryGroup(cmd.groupId,{name:cmd.proposedName});
  }
  await api.sync();
  const after=await api.getCategoryGroups(); // independent post-sync readback
  if(!Array.isArray(after))refuse("uncertain-write");
  const target=cmd.mode==="create"?created:cmd.groupId;
  const matching=after.filter(g=>g && g.id===target);
  const duplicates=after.filter(g=>g && typeof g.name==="string"
    && norm(g.name)===norm(cmd.proposedName));
  if(matching.length!==1 || matching[0].name!==cmd.proposedName
      || matching[0].is_income===true || duplicates.length!==1
      || duplicates[0].id!==target)
    refuse("uncertain-write");
  return {status:"committed"};
}
