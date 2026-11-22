import {test} from "node:test";
import assert from "node:assert/strict";
import {CategoryGroupRefusal,validateGroupCommand,preflightGroup,executeGroup}
  from "../../scripts/finance/category_group_guard.mjs";

const create={mode:"create",requestId:"a".repeat(32),sourceKey:"f".repeat(64),
  month:"2026-11",groupId:"",expectedName:"",proposedName:"Household"};
const rename={...create,mode:"rename",groupId:"group-needs",
  expectedName:"Needs",proposedName:"Essentials"};
const groups=[{id:"group-needs",name:"Needs",is_income:false},
  {id:"group-income",name:"Income",is_income:true},
  {id:"group-wants",name:"Wants"}];
const fails=code=>e=>e instanceof CategoryGroupRefusal && e.code===code;

test("M5 validate create/rename strictly and reject malformed or extra fields",()=>{
  assert.deepEqual(validateGroupCommand(create),create);
  assert.deepEqual(validateGroupCommand(rename),rename);
  for(const bad of [
    {...create,extra:1},{...create,mode:"delete"},
    {...create,requestId:"x"},{...create,sourceKey:"x"},
    {...create,month:"2026-13"},{...create,proposedName:""},
    {...create,proposedName:"a".repeat(81)},
    {...create,proposedName:" Income"},
    {...create,proposedName:"Income"},
    {...create,proposedName:" A "},
    {...create,proposedName:"A\u0000B"},
    {...create,groupId:"group-needs"},
    {...rename,groupId:"a!"},{...rename,expectedName:""},
    {...rename,proposedName:"needs"}
  ])assert.throws(()=>validateGroupCommand(bad),CategoryGroupRefusal);
});
test("M5 preflight uses fresh IDs and all hidden group names",()=>{
  assert.equal(preflightGroup(create,groups).mode,"create");
  assert.equal(preflightGroup(rename,groups).mode,"rename");
  assert.throws(()=>preflightGroup({...create,proposedName:"WANTS"},groups),
    fails("possible-duplicate-group"));
  assert.throws(()=>preflightGroup({...rename,expectedName:"Earlier"},groups),
    fails("stale-group"));
  assert.throws(()=>preflightGroup({...rename,groupId:"group-income",
    expectedName:"Income"},groups),fails("stale-group"));
  assert.throws(()=>preflightGroup(create,[...groups,groups[0]]),
    fails("ambiguous-group-source"));
  assert.throws(()=>preflightGroup(create,[{id:"no",name:"X"}]),
    fails("invalid-group-source"));
});
function fake() {
  const rows=structuredClone(groups),events=[];
  return {
    events,
    async getCategoryGroups(){events.push("read");return structuredClone(rows);},
    async createCategoryGroup(fields){
      assert.deepEqual(fields,{name:"Household",is_income:false});
      events.push("create");
      rows.push({id:"created-group",...fields});return "created-group";
    },
    async updateCategoryGroup(id,fields){
      assert.equal(id,"group-needs");
      assert.deepEqual(fields,{name:"Essentials"});
      events.push("rename");
      rows.find(g=>g.id===id).name=fields.name;
      return id;
    },
    async sync(){events.push("sync");}
  };
}
test("M5 create journals before mutation and reads back after sync",async()=>{
  const api=fake();
  assert.deepEqual(await executeGroup({api,input:create,
    recordAttempt:async()=>{api.events.push("journal");}}),{status:"committed"});
  assert.deepEqual(api.events,["read","journal","create","sync","read"]);
});
test("M5 rename only changes name of original ID",async()=>{
  const api=fake();
  assert.deepEqual(await executeGroup({api,input:rename,
    recordAttempt:async()=>{api.events.push("journal");}}),{status:"committed"});
  assert.deepEqual(api.events,["read","journal","rename","sync","read"]);
});
test("M5 stale group refuses without recording attempt",async()=>{
  const api=fake(),command={...rename,expectedName:"Different"};
  let recorded=0;
  await assert.rejects(()=>executeGroup({api,input:command,
    recordAttempt:async()=>recorded++}),fails("stale-group"));
  assert.equal(recorded,0);
  assert.deepEqual(api.events,["read"]);
});
test("M5 post-mutation sync failure cannot return committed",async()=>{
  const api=fake();let recorded=0;
  api.sync=async()=>{api.events.push("sync");throw Error("drop");};
  await assert.rejects(()=>executeGroup({api,input:create,
    recordAttempt:async()=>recorded++}),/drop/);
  assert.equal(recorded,1);
  assert.deepEqual(api.events,["read","create","sync"]);
});
test("M5 missing write guards refuses",async()=>{
  await assert.rejects(()=>executeGroup({api:{},input:create,recordAttempt(){}}),
    fails("missing-write-guards"));
});
