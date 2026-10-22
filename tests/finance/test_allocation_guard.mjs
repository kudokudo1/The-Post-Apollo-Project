import {test} from "node:test";
import assert from "node:assert/strict";
import {validateAllocationCommand,preflightAllocation,executeAllocation,
  AllocationRefusal} from "../../scripts/finance/allocation_guard.mjs";

const id="fictional-cat-1",month="2026-10";
function cmd(overrides={}) {
  return {action:"set-amount",requestId:"a".repeat(32),
    sourceKey:"b".repeat(64),month,categoryId:id,
    expectedBudgetedCents:20000,expectedAvailableCents:8000,
    expectedToBudgetCents:30000,targetBudgetedCents:25000,...overrides};
}
function budget() {return {
  toBudget:30000,categoryGroups:[
    {is_income:true,categories:[{id:"income-cat",budgeted:0,balance:0}]},
    {name:"Living",categories:[{id,budgeted:20000,balance:8000}]}
  ]
};}
function mocked() {
  let state=budget(),attempts=0,calls=0,syncs=0;
  return {
    api:{
      async getBudgetMonth(){return structuredClone(state);},
      async setBudgetAmount(_,cat,value) {
        calls++;
        const row=state.categoryGroups[1].categories.find(c=>c.id===cat);
        if (!row) throw Error("unexpected-test-category");
        const delta=value-row.budgeted;
        row.budgeted=value;row.balance+=delta;state.toBudget-=delta;
        return "ok";
      },
      async sync(){syncs++;return "ok";}
    },
    recordAttempt:async()=>{attempts++;},
    counts:()=>({attempts,calls,syncs}),
    change(fn){fn(state);}
  };
}
async function refusal(code,fn) {
  await assert.rejects(fn,error=>error instanceof AllocationRefusal
    && error.code===code);
}
test("valid absolute allocation is adjusted in cents, synced once, reread",async()=>{
  const m=mocked();
  assert.equal(validateAllocationCommand(cmd()).targetBudgetedCents,25000);
  const result=await executeAllocation({api:m.api,input:cmd(),
    recordAttempt:m.recordAttempt});
  assert.deepEqual(result,{status:"committed"});
  assert.deepEqual(m.counts(),{attempts:1,calls:1,syncs:1});
});
test("stale category or To Budget refuses before recording an attempt",async()=>{
  const m=mocked();
  m.change(x=>{x.toBudget=29999;});
  await refusal("stale-budget",()=>executeAllocation({api:m.api,input:cmd(),
    recordAttempt:m.recordAttempt}));
  assert.deepEqual(m.counts(),{attempts:0,calls:0,syncs:0});
});
test("over-allocation and overspending are hard refusals for first stage",async()=>{
  const m=mocked();
  for(const [value,code] of [[60000,"insufficient-unallocated-funds"],
                              [0,"category-would-be-overspent"]]){
    await refusal(code,()=>executeAllocation({
      api:m.api,input:cmd({targetBudgetedCents:value}),
      recordAttempt:m.recordAttempt
    }));
  }
  assert.deepEqual(m.counts(),{attempts:0,calls:0,syncs:0});
});
test("unexpected fields and malformed values never reach Actual",async()=>{
  const values=[
    {...cmd(),unexpected:true},
    cmd({sourceKey:"wrong"}),cmd({month:"2026-13"}),
    cmd({requestId:"too-short"}),cmd({targetBudgetedCents:-100}),
    cmd({targetBudgetedCents:4.5}),cmd({categoryId:"bad"}),
    cmd({expectedAvailableCents:Infinity})
  ];
  const m=mocked();
  for(const value of values)await assert.rejects(
    ()=>executeAllocation({api:m.api,input:value,recordAttempt:m.recordAttempt}),
    AllocationRefusal);
  assert.deepEqual(m.counts(),{attempts:0,calls:0,syncs:0});
});
test("duplicate category identity cannot be resolved by guesswork",async()=>{
  const b=budget();b.categoryGroups[1].categories.push({...b.categoryGroups[1].categories[0]});
  assert.throws(()=>preflightAllocation(cmd(),b),error=>error instanceof AllocationRefusal
    && error.code==="category-unavailable");
});
test("a successful set without matching readback is UNCERTAIN, not success",async()=>{
  const m=mocked(),original=m.api.setBudgetAmount;
  m.api.setBudgetAmount=async()=>{return "ok";};
  await refusal("uncertain-write",()=>executeAllocation({api:m.api,
    input:cmd(),recordAttempt:m.recordAttempt}));
  assert.deepEqual(m.counts(),{attempts:1,calls:0,syncs:1});
  m.api.setBudgetAmount=original;
});
test("attempt journaling failure prevents the API mutation",async()=>{
  const m=mocked();
  await assert.rejects(()=>executeAllocation({api:m.api,input:cmd(),
    recordAttempt:async()=>{throw Error("durability-failure");}}),/durability-failure/);
  assert.deepEqual(m.counts(),{attempts:0,calls:0,syncs:0});
});
test("pure preflight does not alter the authoritative budget object",()=>{
  const b=budget(),before=JSON.stringify(b);
  const preview=preflightAllocation(cmd(),b);
  assert.deepEqual({delta:preview.delta,remaining:preview.nextUnallocated,
      available:preview.nextAvailable},
    {delta:5000,remaining:25000,available:13000});
  assert.equal(JSON.stringify(b),before);
});
