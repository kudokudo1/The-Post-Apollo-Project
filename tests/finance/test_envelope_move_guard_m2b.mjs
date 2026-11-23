import {test} from "node:test";
import assert from "node:assert/strict";
import {validateEnvelopeMoveCommand,preflightEnvelopeMove,
  executeEnvelopeMove,EnvelopeMoveRefusal}
  from "../../scripts/finance/envelope_move_guard.mjs";

const fromId="fictional-groceries",toId="fictional-fuel";
function command(overrides={}) {
  return {action:"move-envelope",requestId:"a".repeat(32),
    sourceKey:"b".repeat(64),month:"2026-11",
    fromCategoryId:fromId,toCategoryId:toId,moveCents:2550,
    expectedFromBudgetedCents:20000,expectedFromAvailableCents:14000,
    expectedToBudgetedCents:5000,expectedToAvailableCents:2500,
    expectedToBudgetCents:4000,...overrides};
}
function budget() {
  return {toBudget:4000,categoryGroups:[
    {is_income:true,categories:[{id:"income-1",budgeted:0,balance:0}]},
    {name:"Needs",is_income:false,categories:[
      {id:fromId,budgeted:20000,balance:14000},
      {id:toId,budgeted:5000,balance:2500},
      {id:"fictional-utilities",budgeted:3000,balance:-1000}
    ]}
  ]};
}
function mock({failAtSet=0,failSync=false,alterReadback=false}={}) {
  let state=budget(),attempts=0,sets=0,syncs=0,reads=0;
  const api={
    async getBudgetMonth() {
      reads++;
      const result=structuredClone(state);
      if(alterReadback&&reads>1)
        result.categoryGroups[1].categories[1].balance++;
      return result;
    },
    async setBudgetAmount(month,id,target) {
      sets++;
      if(sets===failAtSet)throw Error("injected-second-set-failure");
      assert.equal(month,"2026-11");
      const row=state.categoryGroups[1].categories.find(c=>c.id===id);
      assert.ok(row,id);
      const delta=target-row.budgeted;
      row.budgeted=target;
      row.balance+=delta;
      state.toBudget-=delta;
    },
    async sync() {
      syncs++;
      if(failSync)throw Error("injected-sync-failure");
    }
  };
  return {api,recordAttempt:async()=>{attempts++;},
    counts:()=>({attempts,sets,syncs,reads}),
    state:()=>structuredClone(state),
    change:fn=>fn(state)};
}
async function refusal(code,fn) {
  await assert.rejects(fn,e=>e instanceof EnvelopeMoveRefusal&&e.code===code);
}

test("two-category policy commits only after both changes, one sync and readback",async()=>{
  const m=mock();
  assert.equal(validateEnvelopeMoveCommand(command()).moveCents,2550);
  assert.deepEqual(await executeEnvelopeMove({api:m.api,input:command(),
    recordAttempt:m.recordAttempt}),{status:"committed"});
  assert.deepEqual(m.counts(),{attempts:1,sets:2,syncs:1,reads:2});
  const b=m.state();
  assert.equal(b.toBudget,4000);
  assert.deepEqual(b.categoryGroups[1].categories.slice(0,2),[
    {id:fromId,budgeted:17450,balance:11450},
    {id:toId,budgeted:7550,balance:5050}
  ]);
});

test("pure preflight conserves allocation/available totals without mutation",()=>{
  const b=budget(),original=JSON.stringify(b);
  const c=preflightEnvelopeMove(command(),b);
  assert.equal(c.nextFromBudgeted+c.nextToBudgeted,25000);
  assert.equal(c.nextFromAvailable+c.nextToAvailable,16500);
  assert.equal(c.toBudgetUnchanged,4000);
  assert.equal(JSON.stringify(b),original);
});

test("conservative source limits match M2a preview, destination can stay overspent",()=>{
  const b=budget();
  assert.equal(preflightEnvelopeMove(command({
    toCategoryId:"fictional-utilities",moveCents:200,
    expectedToBudgetedCents:3000,expectedToAvailableCents:-1000
  }),b).nextToAvailable,-800);
  assert.throws(()=>preflightEnvelopeMove(command({moveCents:14001}),b),
    e=>e.code==="insufficient-source-available");
  const rollover=budget();
  rollover.categoryGroups[1].categories[0].budgeted=100;
  assert.throws(()=>preflightEnvelopeMove(command({
    expectedFromBudgetedCents:100,moveCents:200}),rollover),
    e=>e.code==="insufficient-source-assignment");
});

test("malformed and unexpected inputs refuse without any attempt",async()=>{
  const bad=[
    null,[],{...command(),extra:true},
    command({action:"transfer-bank"}),command({requestId:"bad"}),
    command({sourceKey:"bad"}),command({month:"2026-13"}),
    command({fromCategoryId:"?"}),command({fromCategoryId:toId}),
    command({moveCents:0}),command({moveCents:-100}),
    command({moveCents:1.5}),command({moveCents:Infinity}),
    command({expectedToAvailableCents:"2500"}),
    command({expectedFromBudgetedCents:-1}),
    command({expectedToBudgetCents:Number.MAX_SAFE_INTEGER})
  ];
  const m=mock();
  for(const cmd of bad)await assert.rejects(()=>executeEnvelopeMove({
    api:m.api,input:cmd,recordAttempt:m.recordAttempt}),EnvelopeMoveRefusal);
  assert.deepEqual(m.counts(),{attempts:0,sets:0,syncs:0,reads:0});
});

test("stale source month money or ambiguous categories refuse before attempt",async()=>{
  const m=mock();
  m.change(x=>{x.toBudget=3999;});
  await refusal("stale-budget",()=>executeEnvelopeMove({
    api:m.api,input:command(),recordAttempt:m.recordAttempt}));
  assert.deepEqual(m.counts(),{attempts:0,sets:0,syncs:0,reads:1});
  const duplicate=budget();
  duplicate.categoryGroups[1].categories.push({...duplicate.categoryGroups[1].categories[0]});
  assert.throws(()=>preflightEnvelopeMove(command(),duplicate),
    e=>e.code==="category-unavailable");
  const invalidGroup=budget(); invalidGroup.categoryGroups[1].is_income="false";
  assert.throws(()=>preflightEnvelopeMove(command(),invalidGroup),
    e=>e.code==="invalid-budget");
  const missingIncome=command({toCategoryId:"income-1",expectedToBudgetedCents:0,
    expectedToAvailableCents:0});
  assert.throws(()=>preflightEnvelopeMove(missingIncome,budget()),
    e=>e.code==="category-unavailable");
});

test("write journal callback failure occurs before BOTH API mutations",async()=>{
  const m=mock();
  await assert.rejects(()=>executeEnvelopeMove({api:m.api,input:command(),
    recordAttempt:async()=>{throw Error("durability-failed");}}),
  /durability-failed/);
  assert.deepEqual(m.counts(),{attempts:0,sets:0,syncs:0,reads:1});
});

test("second mutation fails after source changed: never sync or rollback",async()=>{
  const m=mock({failAtSet:2});
  await assert.rejects(()=>executeEnvelopeMove({api:m.api,input:command(),
    recordAttempt:m.recordAttempt}),/injected-second-set-failure/);
  assert.deepEqual(m.counts(),{attempts:1,sets:2,syncs:0,reads:1});
  const b=m.state();
  assert.equal(b.toBudget,6550);
  assert.equal(b.categoryGroups[1].categories[0].budgeted,17450);
  assert.equal(b.categoryGroups[1].categories[1].budgeted,5000);
  // The outer writer MUST leave ATTEMPTED and fail CLOSED; no rollback.
});

test("sync failure and mismatched readback are never reported committed",async()=>{
  const failed=mock({failSync:true});
  await assert.rejects(()=>executeEnvelopeMove({api:failed.api,
    input:command(),recordAttempt:failed.recordAttempt}),/injected-sync-failure/);
  assert.deepEqual(failed.counts(),{attempts:1,sets:2,syncs:1,reads:1});
  const mismatched=mock({alterReadback:true});
  await refusal("uncertain-write",()=>executeEnvelopeMove({api:mismatched.api,
    input:command(),recordAttempt:mismatched.recordAttempt}));
  assert.deepEqual(mismatched.counts(),{attempts:1,sets:2,syncs:1,reads:2});
});

test("missing hooks and unsafe numeric overflow are refused",async()=>{
  await refusal("missing-write-guards",()=>executeEnvelopeMove({
    api:null,input:command(),recordAttempt:async()=>{}}));
  const b=budget();
  b.categoryGroups[1].categories[1].budgeted=99999999999;
  assert.throws(()=>preflightEnvelopeMove(command({
    expectedToBudgetedCents:99999999999,moveCents:1}),b),
    e=>e.code==="overflow");
});
