import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {fileURLToPath} from "node:url";
const src=readFileSync(fileURLToPath(new URL("../../services/finance/FinanceInputPolicy.js",import.meta.url)),"utf8");
const p=runInNewContext(src+";({parseDate,editDatePart,stepDatePart,normalizeAmount,isoDate});",{Date});

test("date fields always return ISO and reject impossible dates",()=>{
 assert.equal(p.isoDate(2026,10,23),"2026-10-23");
 assert.equal(p.isoDate(2026,2,30),"");
 assert.equal(p.editDatePart("2026-10-23","","month","13"),"");
 assert.equal(p.editDatePart("2026-10-23","","day","31"),"2026-10-31");
 assert.equal(p.editDatePart("2026-10-23","","day","32"),"");
 assert.equal(p.editDatePart("","","day","15"),"");
 assert.equal(p.editDatePart("","2026-10-01","day","15"),"2026-10-15");
 assert.equal(p.editDatePart("2026-10-23","","year","2027"),"2027-10-23");
});
test("month/year edits clamp day for shorter months and leap years",()=>{
 assert.equal(p.editDatePart("2024-01-31","","month","2"),"2024-02-29");
 assert.equal(p.editDatePart("2024-02-29","","year","2025"),"2025-02-28");
 assert.equal(p.editDatePart("2026-01-31","","month","2"),"2026-02-28");
});
test("keyboard and pointer stepping roll calendar edges consistently",()=>{
 assert.equal(p.stepDatePart("2026-12-31","","day",1),"2027-01-01");
 assert.equal(p.stepDatePart("2026-01-01","","day",-1),"2025-12-31");
 assert.equal(p.stepDatePart("2026-12-31","","month",1),"2027-01-31");
 assert.equal(p.stepDatePart("2026-03-31","","month",-1),"2026-02-28");
 assert.equal(p.stepDatePart("2024-02-29","","year",1),"2025-02-28");
 assert.equal(p.stepDatePart("2099-12-31","","year",1),"2099-12-31");
});
test("money without decimal means zero cents; decimal shorthand padded",()=>{
 for(const [input,result] of [
   ["25","25.00"],["25.5","25.50"],["25.05","25.05"],
   ["0","0.00"],["0.01","0.01"],["999999999","999999999.00"],
   ["$25","25.00"]
 ])assert.equal(p.normalizeAmount(input),result,input);
 for(const input of ["","-2","2.345","1e2","1000000000","1,234","$"])assert.equal(p.normalizeAmount(input),null,input);
});
test("input policy contains no money writer, journal, or persistence",()=>{
 for(const bad of ["@actual-app/api","setBudgetAmount(","updateTransaction(",
 "addTransactions(","writeFile(","Process {","fetch(","LocalStorage",
 "allocation-writes-enabled","transaction-writes-enabled"]){
    assert.equal(src.includes(bad),false,bad);
 }
});
