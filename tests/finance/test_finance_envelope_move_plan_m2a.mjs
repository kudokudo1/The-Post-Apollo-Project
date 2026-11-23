import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {test} from "node:test";

const source=readFileSync(new URL("../../services/finance/FinanceEnvelopeMovePlan.js",
    import.meta.url),"utf8").replace(/^\.pragma library\s*/,"");
const ctx={};
runInNewContext(source,ctx);
const preview=ctx.previewEnvelopeMove;
const parse=ctx.parseMoveCents;
const original=()=>({
    schemaVersion:1,source:"actual-budget",readOnly:true,
    sourceKey:"a".repeat(64),month:"2026-11",toBudgetCents:4000,
    categories:[
        {id:"groceries",groupId:"needs",name:"Groceries",
         budgetedCents:20000,availableCents:14000},
        {id:"fuel",groupId:"needs",name:"Fuel",
         budgetedCents:5000,availableCents:2500},
        {id:"utilities",groupId:"needs",name:"Utilities",
         budgetedCents:3000,availableCents:-1000}
    ]
});

test("M2a balanced movement changes two envelopes but not unassigned funds",()=>{
    const snapshot=original();
    const untouched=JSON.stringify(snapshot);
    const p=preview(snapshot,"groceries","fuel"," 25.50 ");
    assert.equal(p.ok,true);
    assert.equal(p.savesToActual,false);
    assert.equal(p.requiresAtomicWriter,true);
    assert.equal(p.moveCents,2550);
    assert.equal(p.sourceKey,snapshot.sourceKey);
    assert.equal(p.month,snapshot.month);
    assert.equal(p.fromCategoryId,"groceries");
    assert.equal(p.toCategoryId,"fuel");
    assert.equal(p.fromBudgetedBeforeCents,20000);
    assert.equal(p.fromBudgetedAfterCents,17450);
    assert.equal(p.toBudgetedBeforeCents,5000);
    assert.equal(p.toBudgetedAfterCents,7550);
    assert.equal(p.fromAvailableBeforeCents,14000);
    assert.equal(p.fromAvailableAfterCents,11450);
    assert.equal(p.toAvailableBeforeCents,2500);
    assert.equal(p.toAvailableAfterCents,5050);
    assert.equal(p.toBudgetBeforeCents,4000);
    assert.equal(p.toBudgetAfterCents,4000);
    assert.equal(JSON.stringify(snapshot),untouched);
});

test("M2a can partially cover destination overspending; never allows negative source",()=>{
    const p=preview(original(),"groceries","utilities","4.00");
    assert.equal(p.ok,true);
    assert.equal(p.destinationRemainsOverspent,true);
    assert.equal(p.toAvailableAfterCents,-600);
    const enough=preview(original(),"groceries","utilities","10.00");
    assert.equal(enough.ok,true);
    assert.equal(enough.destinationRemainsOverspent,false);
    assert.equal(enough.toAvailableAfterCents,0);
});

test("M2a refuses unavailable source funds and negative monthly source allocation",()=>{
    assert.equal(preview(original(),"fuel","groceries","25.01").reason,
                 "NOT ENOUGH AVAILABLE IN SOURCE ENVELOPE");
    const rollover=original();
    rollover.categories[0].budgetedCents=100;
    assert.equal(preview(rollover,"groceries","fuel","2.00").reason,
                 "MOVE EXCEEDS THIS MONTH'S SOURCE ASSIGNMENT");
});

test("M2a rejects self-moves, missing envelopes, and duplicates",()=>{
    assert.equal(preview(original(),"groceries","groceries","1").reason,
                 "CHOOSE DIFFERENT ENVELOPES");
    assert.equal(preview(original(),"","fuel","1").reason,
                 "SELECT TWO ENVELOPES");
    assert.equal(preview(original(),"groceries","missing","1").reason,
                 "ENVELOPE NOT UNIQUE OR UNAVAILABLE");
    const duplicated=original();
    duplicated.categories.push({...duplicated.categories[1]});
    assert.equal(preview(duplicated,"groceries","fuel","1").ok,false);
});

test("M2a rejects untrusted, stale-shaped, and unauthenticated data",()=>{
    for(const next of [
        null,{...original(),readOnly:false},
        {...original(),source:"demo"},
        {...original(),sourceKey:"bad"},
        {...original(),month:"2026-13"},
        {...original(),schemaVersion:2},
        {...original(),categories:"invalid"},
        {...original(),toBudgetCents:Infinity}
    ])assert.equal(preview(next,"groceries","fuel","1").ok,false);
    const malformed=original();
    malformed.categories[1].availableCents="2500";
    assert.equal(preview(malformed,"groceries","fuel","1").reason,
                 "INVALID ENVELOPE BALANCES");
});

test("M2a rejects invalid amounts, unsafe integers and overflow",()=>{
    for(const raw of ["","0","0.00","-1","1.001","1e3","Infinity",
                      "1,000","1000000000","a","1.2.3"])
        assert.equal(parse(raw),null,raw);
    assert.equal(parse("0.01"),1);
    assert.equal(parse("1.2"),120);
    assert.equal(parse("999999999.99"),99999999999);
    const snapshot=original();
    snapshot.categories[1].budgetedCents=99999999999;
    assert.equal(preview(snapshot,"groceries","fuel","0.01").reason,
                 "AMOUNT EXCEEDS SAFE FINANCIAL RANGE");
    assert.equal(preview(original(),"groceries","fuel","0.00").ok,false);
});

test("M2a conserves both allocation and available totals for integer-cent moves",()=>{
    for(const cents of [1,10,123,1000,2500,13999,14000]){
        const p=preview(original(),"groceries","fuel",(cents/100).toFixed(2));
        assert.equal(p.ok,true);
        assert.equal(p.fromBudgetedAfterCents+p.toBudgetedAfterCents,
                     p.fromBudgetedBeforeCents+p.toBudgetedBeforeCents);
        assert.equal(p.fromAvailableAfterCents+p.toAvailableAfterCents,
                     p.fromAvailableBeforeCents+p.toAvailableBeforeCents);
        assert.equal(p.toBudgetBeforeCents,p.toBudgetAfterCents);
    }
});

test("M2a policy has no Actual writer, filesystem, network, permit, or money execution",()=>{
    for(const forbidden of [
        "Process {","LocalStorage","fetch(","setBudgetAmount(","api.",
        "downloadBudget(","writeFile(","FINANCEW_","payment", "allowWrite",
        "sync()", "createTransaction("
    ])assert.equal(source.includes(forbidden),false,forbidden);
});
