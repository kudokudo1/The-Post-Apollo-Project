import {test} from "node:test";
import assert from "node:assert/strict";
import {CategoryRefusal,validateCategoryCommand,preflightCategory,executeCategory}
  from "../../scripts/finance/category_guard.mjs";

const base={mode:"create",requestId:"a".repeat(32),
  sourceKey:"f".repeat(64),month:"2026-10",groupId:"group-needs",
  categoryId:"",expectedName:"",proposedName:"Groceries"};
const groups=[{id:"group-needs",name:"Needs",is_income:false},
  {id:"group-income",name:"Income",is_income:true}];
const categories=[{id:"category-rent",name:"Rent",group_id:"group-needs"},
  {id:"category-income",name:"Income",group_id:"group-income",is_income:true}];
const failure=(code)=>e=>e instanceof CategoryRefusal && e.code===code;

test("strict create/rename validation refuses unknown fields and ambiguous names",()=>{
  assert.deepEqual(validateCategoryCommand(base),base);
  const rename={...base,mode:"rename",categoryId:"category-rent",
    expectedName:"Rent",proposedName:"Housing"};
  assert.deepEqual(validateCategoryCommand(rename),rename);
  for(const cmd of [
    {...base,extra:true},{...base,sourceKey:"bad"},
    {...base,requestId:"bad"},{...base,groupId:""},
    {...base,proposedName:" "},{...base,proposedName:"\u0000bad"},
    {...base,proposedName:" A "},{...base,proposedName:"A".repeat(81)},
    {...base,categoryId:"category-rent"},
    {...rename,expectedName:" "},{...rename,categoryId:""},
    {...rename,proposedName:"rent"},{...base,mode:"delete"}
  ])assert.throws(()=>validateCategoryCommand(cmd),CategoryRefusal);
});

test("fresh category checks reject wrong group, stale or duplicate names",()=>{
  assert.equal(preflightCategory(base,groups,categories).mode,"create");
  assert.throws(()=>preflightCategory({...base,proposedName:"RENT"},
    groups,categories),failure("possible-duplicate-category"));
  assert.throws(()=>preflightCategory({...base,groupId:"group-income"},
    groups,categories),failure("stale-category-group"));
  const rename={...base,mode:"rename",categoryId:"category-rent",
    expectedName:"Rent",proposedName:"Housing"};
  assert.equal(preflightCategory(rename,groups,categories).mode,"rename");
  assert.throws(()=>preflightCategory({...rename,expectedName:"Old name"},
    groups,categories),failure("stale-category"));
  assert.throws(()=>preflightCategory({...rename,categoryId:"other-id"},
    groups,categories),failure("stale-category"));
  assert.throws(()=>preflightCategory(base,groups,[{id:"broken"}]),
    failure("invalid-category-source"));
});

function fake() {
  let rows=structuredClone(categories);
  const events=[];
  let seq=0;
  return {
    events,
    async getCategoryGroups(){events.push("get-groups");return structuredClone(groups);},
    async getCategories(){events.push("get-categories");return structuredClone(rows);},
    async createCategory(fields){
      assert.deepEqual(fields,{name:"Groceries",group_id:"group-needs",is_income:false});
      events.push("create");
      rows.push({id:"created-category",group_id:fields.group_id,name:fields.name,
        is_income:false});
      return "created-category";
    },
    async updateCategory(id,fields){
      events.push("update");
      assert.deepEqual(fields,{name:"Housing"});
      assert.equal(id,"category-rent");
      rows.find(c=>c.id===id).name=fields.name;
      return null;
    },
    async sync(){events.push("sync");++seq;},
    get syncCount(){return seq;}
  };
}
test("create category uses one mutation and readback after journal-before-write",async()=>{
  const api=fake();
  const result=await executeCategory({api,input:base,
    recordAttempt:async()=>{api.events.push("journal");}});
  assert.equal(result.status,"committed");
  assert.equal(api.events.filter(x=>x==="create").length,1);
  assert.equal(api.syncCount,1);
  assert.ok(api.events.indexOf("journal")<api.events.indexOf("create"));
  assert.ok(api.events.indexOf("sync")<api.events.lastIndexOf("get-categories"));
});
test("rename changes only name, same ID and group",async()=>{
  const api=fake();
  const command={...base,mode:"rename",categoryId:"category-rent",
    expectedName:"Rent",proposedName:"Housing"};
  const result=await executeCategory({api,input:command,
    recordAttempt:async()=>{api.events.push("journal");}});
  assert.equal(result.status,"committed");
  assert.ok(api.events.indexOf("journal")<api.events.indexOf("update"));
  assert.equal(api.events.filter(x=>x==="update").length,1);
  assert.equal(api.syncCount,1);
});
test("stale category never records a journal or mutates",async()=>{
  const api=fake();let attempts=0;
  const command={...base,mode:"rename",categoryId:"category-rent",
    expectedName:"Unexpected",proposedName:"Housing"};
  await assert.rejects(()=>executeCategory({api,input:command,
    recordAttempt:async()=>attempts++}),failure("stale-category"));
  assert.equal(attempts,0);
  assert.ok(!api.events.includes("update"));
});
test("sync uncertainty cannot claim a committed category",async()=>{
  const api=fake();
  api.sync=async()=>{api.events.push("sync");throw Error("simulated-drop");};
  let recorded=0;
  await assert.rejects(()=>executeCategory({api,input:base,
    recordAttempt:async()=>recorded++}),/simulated-drop/);
  assert.equal(recorded,1);
  assert.equal(api.events.filter(x=>x==="create").length,1);
});
