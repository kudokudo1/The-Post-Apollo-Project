import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {fileURLToPath} from "node:url";

const source=readFileSync(fileURLToPath(new URL("../../services/finance/FinanceAllocationPreview.js",import.meta.url)),"utf8");
assert.doesNotMatch(source,/\b(fetch|XMLHttpRequest|Process|addTransactions|setBudgetAmount|updateTransaction|writeFile|exec)\b/);
const api=runInNewContext(source+";({parseAllocationCents,previewAllocation});",{});
function snapshot(budgeted=20000,available=8000,toBudget=30000) {
  return {schemaVersion:1,source:"actual-budget",readOnly:true,
    sourceKey:"a".repeat(64),month:"2026-10",toBudgetCents:toBudget,
    categories:[{id:"fictional-food",name:"Food",group:"Living",
      budgetedCents:budgeted,spentCents:-12000,availableCents:available}]};
}
test("non-mutating category allocation preview changes the envelope and To Budget",()=>{
  const input=snapshot();
  const before=JSON.stringify(input);
  const result=api.previewAllocation(input,"fictional-food","250.00");
  assert.equal(result.ok,true);
  assert.equal(result.allocationChangeCents,5000);
  assert.equal(result.originalBudgetedCents,20000);
  assert.equal(result.targetBudgetedCents,25000);
  assert.equal(result.categoryAvailableAfterCents,13000);
  assert.equal(result.toBudgetAfterCents,25000);
  assert.equal(result.exceedsUnallocatedFunds,false);
  assert.equal(JSON.stringify(input),before,"snapshot may not be changed");
});
test("decreasing an allocation returns funds to To Budget",()=>{
  const p=api.previewAllocation(snapshot(),"fictional-food","0.00");
  assert.equal(p.ok,true);
  assert.equal(p.allocationChangeCents,-20000);
  assert.equal(p.categoryAvailableAfterCents,-12000);
  assert.equal(p.toBudgetAfterCents,50000);
  assert.equal(p.categoryRemainsOverspent,true);
});
test("over-allocation is a warning, never mistaken for additional money",()=>{
  const p=api.previewAllocation(snapshot(),"fictional-food","600.00");
  assert.equal(p.ok,true);
  assert.equal(p.toBudgetAfterCents,-10000);
  assert.equal(p.exceedsUnallocatedFunds,true);
});
test("USD entry is exact cents and zero supported",()=>{
  for(const [text,expected] of [["0",0],["1.2",120],["1.02",102],
    ["999999999.99",99999999999]]) assert.equal(api.parseAllocationCents(text),expected);
  for(const invalid of ["-1.00","1.234","1e3","$1.00","Infinity","","1000000000.00"]) {
    assert.equal(api.parseAllocationCents(invalid),null,invalid);
  }
});
test("stale, unauthenticated, duplicate, and unrecognized categories refused",()=>{
  assert.equal(api.previewAllocation(null,"fictional-food","2.00").ok,false);
  const noAuth=snapshot();noAuth.readOnly=false;
  assert.equal(api.previewAllocation(noAuth,"fictional-food","2.00").ok,false);
  const other=snapshot();other.sourceKey="";
  assert.equal(api.previewAllocation(other,"fictional-food","2.00").ok,false);
  assert.equal(api.previewAllocation(snapshot(),"other-category","2.00").ok,false);
  const dup=snapshot();dup.categories.push({...dup.categories[0]});
  assert.equal(api.previewAllocation(dup,"fictional-food","2.00").ok,false);
});
test("integer overflow and bad source amounts fail closed",()=>{
  const notInteger=snapshot();notInteger.toBudgetCents=12.5;
  assert.equal(api.previewAllocation(notInteger,"fictional-food","2.00").ok,false);
  const overflow=snapshot(-9007199254740991,0,9007199254740991);
  assert.equal(api.previewAllocation(overflow,"fictional-food","2.00").ok,false);
});
