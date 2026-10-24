import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {test} from "node:test";

const source=readFileSync(new URL("../../services/finance/FinanceCategoryPlan.js",
  import.meta.url),"utf8").replace(/^\.pragma library\s*/,"");
const context={};
runInNewContext(source,context);
const preview=context.previewCategoryPlan;
const snapshot={
  readOnly:true,source:"actual-budget",sourceKey:"a".repeat(64),month:"2026-10",
  categoryGroups:[{id:"needs",name:"Needs"},{id:"wants",name:"Wants"}],
  categories:[
    {id:"groceries",name:"Groceries",groupId:"needs"},
    {id:"coffee",name:"Coffee",groupId:"wants"}
  ]
};

test("create preview binds immutable source, month and actual group ID",()=>{
  const p=preview(snapshot,"create","","needs","  Car repairs  ");
  assert.equal(p.ok,true);
  assert.equal(p.groupId,"needs");
  assert.equal(p.groupName,"Needs");
  assert.equal(p.proposedName,"Car repairs");
  assert.equal(p.month,"2026-10");
  assert.equal(p.sourceKey,snapshot.sourceKey);
  assert.equal(p.savesToActual,false);
  assert.equal(p.categoryId,"");
});

test("rename targets exactly one stable category in the original group",()=>{
  const p=preview(snapshot,"rename","groceries","needs"," Food ");
  assert.equal(p.ok,true);
  assert.equal(p.categoryId,"groceries");
  assert.equal(p.originalName,"Groceries");
  assert.equal(p.proposedName,"Food");
  assert.equal(preview(snapshot,"rename","groceries","wants","Food").ok,false);
  assert.equal(preview(snapshot,"rename","unknown","needs","Food").ok,false);
  assert.equal(preview(snapshot,"rename","groceries","needs","Groceries").ok,false);
});

test("duplicate category names fail only within their group",()=>{
  assert.equal(preview(snapshot,"create","","needs","gRoCeRiEs").ok,false);
  assert.equal(preview(snapshot,"create","","wants","Groceries").ok,true);
  assert.equal(preview(snapshot,"rename","groceries","needs"," groceries ").ok,false);
  const duplicate={...snapshot,categories:[
    ...snapshot.categories,{id:"other",name:"GROCERIES",groupId:"needs"}
  ]};
  assert.equal(preview(duplicate,"rename","groceries","needs","Groceries").ok,false);
});

test("invalid source, ambiguous group, unsafe or empty names refuse",()=>{
  assert.equal(preview(null,"create","","needs","Food").ok,false);
  assert.equal(preview({...snapshot,readOnly:false},"create","","needs","Food").ok,false);
  assert.equal(preview({...snapshot,sourceKey:"bad"},"create","","needs","Food").ok,false);
  assert.equal(preview({...snapshot,month:"2026-99"},"create","","needs","Food").ok,false);
  assert.equal(preview(snapshot,"create","","unknown","Food").ok,false);
  assert.equal(preview({...snapshot,categoryGroups:[
    ...snapshot.categoryGroups,snapshot.categoryGroups[0]
  ]},"create","","needs","Food").ok,false);
  for(const name of [""," ","N".repeat(81),"\u0001Fake"]) {
    assert.equal(preview(snapshot,"create","","needs",name).ok,false);
  }
  assert.equal(preview(snapshot,"delete","groceries","needs","Food").ok,false);
});

test("no mutators, files, network or authorization in preview policy",()=>{
  for(const bad of ["createCategory(","updateCategory(","deleteCategory(",
    "writeFile(","Process {","fetch(","api.","FINANCEW_",
    "approvalArmed","setBudgetAmount(","fs."]) {
    assert.equal(source.includes(bad),false,bad);
  }
});
