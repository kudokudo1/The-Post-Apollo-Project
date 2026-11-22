import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const source=readFileSync(new URL("../../widgets/FinanceBankingImportPolicy.js",import.meta.url),"utf8");
const context=vm.createContext({Date,Set});
vm.runInContext(source,context);

const choices=context.accounts();
assert.equal(JSON.stringify(choices.map(a=>a.id)),
    JSON.stringify(["cashapp","chime","paypal","bank"]));
assert.equal(context.money(-120050),"-$1200.50");
assert.equal(context.canonicalDate("11/22/2026"),"2026-11-22");
assert.equal(context.canonicalDate("2026-11-22"),"2026-11-22");
for(const bad of ["2026-02-29","02/30/2026","2026-13-01","2026-01-00","01/02/22","tomorrow",""]) {
    assert.equal(context.canonicalDate(bad),null,bad);
}
for(const [text,expected] of [["12.34",1234],["-12.34",-1234],["(42.01)",-4201],["$1,234.50",123450],["-$10.00",-1000],["+0.01",1]]) {
    assert.equal(context.signedCents(text),expected,text);
}
for(const bad of ["", "0", "1.234", "NaN", "1e3", "99999999.00", "12,34.00", "(-20.00)"]) {
    assert.equal(context.signedCents(bad),null,bad);
}

const chimeCsv="Date,Description,Amount\r\n"
    +"11/21/2026,\"Transfer to Cash App\",-75.00\r\n"
    +"11/20/2026,Rent,-1200.00\r\n"
    +"11/21/2026,Payroll,1800.00\r\n";
const cashCsv="\ufeffDate,Description,Amount\n"
    +"2026-11-22,\"From Chime transfer\",75\n"
    +"2026-11-22,\"Coffee, Store\",-12.50\n";
const paypalCsv="Transaction Date,Name,Net\n2026-11-21,Marketplace,-23.00\n";
const chime=context.parseCsv(chimeCsv,"chime");
const cash=context.parseCsv(cashCsv,"cashapp");
const paypal=context.parseCsv(paypalCsv,"paypal");
assert.equal(chime.ok,true,JSON.stringify(chime));
assert.equal(cash.ok,true,JSON.stringify(cash));
assert.equal(paypal.ok,true,JSON.stringify(paypal));
assert.equal(cash.rows[1].description,"Coffee, Store");
assert.equal(chime.rowsCount,3);
assert.equal(chime.connected,false);
assert.equal(chime.persisted,false);
assert.equal(context.parseCsv(chimeCsv,"unknown").ok,false);
const rows=[...chime.rows,...cash.rows,...paypal.rows].map((r,i)=>({...r,id:"row-"+(i+1)}));
const review=context.review(rows,[]);
assert.equal(review.ok,true);
assert.equal(review.debitsCents,131050);
assert.equal(review.creditsCents,187500);
assert.equal(review.spendingLikeDebitsCents,131050,"Unconfirmed transfers count as debits");
assert.equal(review.confirmedPairs,0);
assert.equal(review.candidates.length,1);
const candidate=review.candidates[0];
assert.equal(candidate.fromSource,"Chime");
assert.equal(candidate.toSource,"Cash App");
assert.equal(candidate.amountCents,7500);
const confirmed=context.review(rows,[[candidate.fromId,candidate.toId]]);
assert.equal(confirmed.ok,true);
assert.equal(confirmed.confirmedPairs,1);
assert.equal(confirmed.confirmedTransferOutCents,7500);
assert.equal(confirmed.spendingLikeDebitsCents,123550);
assert.equal(confirmed.candidates.length,0);
assert.equal(confirmed.connected,false);
assert.equal(confirmed.persisted,false);
assert.equal(context.review(rows,[[candidate.fromId,candidate.toId],[candidate.fromId,candidate.toId]]).ok,false);
assert.equal(context.review(rows,[[candidate.toId,candidate.fromId]]).ok,false);
assert.equal(context.review(rows,[["forged",candidate.toId]]).ok,false);

const duplicateSameAccount=context.parseCsv(
    "Date,Description,Amount\n2026-11-22,Store,-12.00\n2026-11-22,Store,-12.00","bank");
assert.equal(duplicateSameAccount.ok,false);
assert.match(duplicateSameAccount.error,/IDENTICAL ROWS/);
const repeatImport=context.review(rows.concat({...rows[0],id:"extra"}),[]);
assert.equal(repeatImport.ok,false);
assert.match(repeatImport.error,/DUPLICATE/);
const tooMany="Date,Description,Amount\n"+Array.from({length:201},
    (_,i)=>"2026-11-22,Example "+i+",-1.00").join("\n");
assert.equal(context.parseCsv(tooMany,"bank").ok,false);
assert.equal(context.parseCsv("a".repeat(65537),"bank").ok,false);

const debitCredit=context.parseCsv(
    "Date,Description,Debit,Credit\n11/22/2026,Food,$5.20,\n11/22/2026,Refund,,5.20","bank");
assert.equal(debitCredit.ok,true,JSON.stringify(debitCredit));
assert.equal(debitCredit.rows[0].amountCents,-520);
assert.equal(debitCredit.rows[1].amountCents,520);
for(const malformed of [
    "Date,Description,Amount\n2026-11-22,\"unclosed,-1",
    "Date,Description,Amount\n2026-11-22,\"bad\"junk,-1",
    "Date,Description,Amount\n2026-11-22,a\"b,-1",
    "Date,Description,Amount\n2026-11-22,Bad,-1,EXTRA",
    "Date,Description,Amount\n2026-11-22,Bad,not money",
    "Date,Description,Amount\n2026-11-22,Bad,0.00",
    "Date,Description,Amount\n2026-11-22,Bad,1.00\n2026-11-22,Another,1.00\u0000",
    "Date,Description,Amount,Amount\n2026-11-22,Item,1,1"
]) assert.equal(context.parseCsv(malformed,"bank").ok,false,malformed);

const noHint=[{id:"a",sourceId:"chime",sourceName:"Chime",date:"2026-11-21",
    description:"Coffee",amountCents:-7500},{id:"b",sourceId:"cashapp",sourceName:"Cash App",
    date:"2026-11-22",description:"Sales",amountCents:7500}];
assert.equal(context.review(noHint,[]).candidates.length,0,"No unhinted auto-match");
const ambiguous=[...noHint.map(r=>({...r,description:"transfer"})),
    {id:"c",sourceId:"paypal",sourceName:"PayPal",date:"2026-11-22",
        description:"transfer",amountCents:7500}];
assert.equal(context.review(ambiguous,[]).candidates.length,0,"Ambiguous candidates remain unpaired");
const sameAccount=[...noHint.map(r=>({...r,sourceId:"chime"}))];
assert.equal(context.review(sameAccount,[]).candidates.length,0);
const late=[...noHint.map(r=>({...r,description:"transfer"}))];
late[1].date="2026-11-28";
assert.equal(context.review(late,[]).candidates.length,0);
assert.equal(context.review(Array(501).fill({id:"same"}),[]).ok,false);

console.log("Banking M1: CSV parsing, signs, caps, multi-source review, conservative transfer candidates PASS");
