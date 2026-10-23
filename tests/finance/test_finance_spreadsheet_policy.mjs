import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {fileURLToPath} from "node:url";
const source=readFileSync(fileURLToPath(new URL(
  "../../services/finance/FinanceSpreadsheetPolicy.js",import.meta.url)),"utf8");
const rules=runInNewContext(source+";({normalizeStepperAmount,stepAmount});");
test("whole dollars and decimal shorthand normalize to integer cents",()=>{
 for(const [input,result] of [["1",100],["1.5",150],["0",0],["0.01",1],
    ["999999999.99",99999999999]])assert.equal(rules.normalizeStepperAmount(input),result,input);
});
test("grid steps may reach zero without going negative",()=>{
 assert.equal(rules.stepAmount("5",100,true),"6.00");
 assert.equal(rules.stepAmount("1",-100,true),"0.00");
 assert.equal(rules.stepAmount("0",-100,true),null);
 assert.equal(rules.stepAmount("12.50",-100,true),"11.50");
});
test("income steps never create zero or negative funds",()=>{
 assert.equal(rules.stepAmount("2.00",-100,false),"1.00");
 assert.equal(rules.stepAmount("1.00",-100,false),null);
 assert.equal(rules.stepAmount("0.01",-100,false),null);
 assert.equal(rules.stepAmount("0.01",100,false),"1.01");
});
test("invalid or excessive money stays invalid, never silently saved",()=>{
 for(const value of ["-1","4e3","1.234","$","9999999999","1,000",""])
   assert.equal(rules.stepAmount(value,100,true),null,value);
 assert.equal(rules.stepAmount("999999999.99",100,true),null);
 assert.equal(rules.stepAmount("1",1.5,true),null);
});
test("spreadsheet stepping has no Actual or write interfaces",()=>{
 for(const word of ["@actual-app/api","writeFile(","Process {","LocalStorage",
   "setBudgetAmount(","addTransactions(","updateTransaction(","fetch(",
   "funding-writes-enabled","allocation-writes-enabled"])
   assert.equal(source.includes(word),false,word);
});
