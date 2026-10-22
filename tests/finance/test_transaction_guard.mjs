import {test} from "node:test";
import assert from "node:assert/strict";
import {validateTransactionCommand,validTransactionDate,executeTransaction}
  from "../../scripts/finance/transaction_guard.mjs";

const base = {
  action:"create",requestId:"a".repeat(32),sourceKey:"b".repeat(64),
  accountId:"checking-123",
  month:"2026-10",date:"2026-10-22",description:"Fictional cafe",
  amountCents:-1250
};
function fake(rows=[]) {
  const calls=[];
  const api={
    getAccounts:async()=>[{id:base.accountId,offbudget:false,closed:false}],
    getTransactions:async()=>rows,
    addTransactions:async(id,transactions,options)=>{
      calls.push(["add",id,transactions,options]);
      const row={account:id,...transactions[0]};
      rows.push(row);
      // Actual API 26.10.0 returns "ok" for a successful add.
      return "ok";
    },
    updateTransaction:async(id,fields)=>{
      calls.push(["update",id,fields]);
      const row=rows.find(t=>t.id===id);
      Object.assign(row,fields);
    },
    sync:async()=>{calls.push(["sync"]);},
  };
  return {api,calls,rows};
}
test("strict date and command validation",()=>{
  assert.equal(validTransactionDate("2026-02-29","2026-02"),false);
  assert.equal(validTransactionDate("2028-02-29","2028-02"),true);
  assert.equal(validTransactionDate("2026-10-01","2026-11"),false);
  assert.deepEqual(validateTransactionCommand(base),base);
  for(const broken of [
    {date:"2026-11-03"},{date:"2026-10-32"},{amountCents:1.5},
    {amountCents:0},{amountCents:100000000000},{description:" "},
    {description:"x".repeat(121)},{requestId:"short"},
    {accountId:""},{action:"delete"},{extra:"oops"},{transactionId:"not-allowed"}
  ]) assert.throws(()=>validateTransactionCommand({...base,...broken}));
});
test("verified fake creation syncs one operation, no transfers or learning",async()=>{
  const f=fake(); let attempts=0;
  const r=await executeTransaction({api:f.api,input:base,
    recordAttempt:async()=>{attempts++;}});
  assert.equal(r.status,"committed");
  assert.equal(attempts,1);
  assert.equal(f.calls[0][0],"add");
  assert.equal(f.calls[0][1],base.accountId);
  assert.deepEqual(f.calls[0][3],
    {runTransfers:false,learnCategories:false});
  assert.equal(f.calls[0][2][0].account,undefined);
  assert.equal(f.calls[0][2][0].imported_id,"financew-"+base.requestId);
  assert.equal(f.calls[0][2][0].payee_name,base.description);
  assert.equal(f.calls[1][0],"sync");
});
test("identical date+amount requires manual reconciliation, no write",async()=>{
  const f=fake([{id:"old",date:base.date,amount:base.amountCents}]);
  let n=0;
  await assert.rejects(()=>executeTransaction({api:f.api,input:base,
    recordAttempt:async()=>{n++;}}), /possible-duplicate/);
  assert.equal(n,0);
  assert.equal(f.calls.length,0);
});
test("stale, offbudget, and closed account block",async()=>{
  for(const acct of [
    [{id:"other"}],[{id:base.accountId,offbudget:true}],
    [{id:base.accountId,closed:true}]
  ]) {
    const f=fake();f.api.getAccounts=async()=>acct;
    await assert.rejects(()=>executeTransaction({api:f.api,input:base,
      recordAttempt:async()=>{throw Error("must not attempt");}}),/stale-account/);
    assert.equal(f.calls.length,0);
  }
});
test("journal boundary blocks actual mutation if recording fails",async()=>{
  const f=fake();
  await assert.rejects(()=>executeTransaction({api:f.api,input:base,
    recordAttempt:async()=>{throw Error("journal-error");}}),/journal-error/);
  assert.equal(f.calls.length,0);
});
test("update needs stable matching old record and changes only date/amount",async()=>{
  const id="transaction-123";
  const before={id,account:base.accountId,date:base.date,amount:-1250,
    payee:"payee-123"};
  const cmd={...base,action:"update",transactionId:id,
    original:{date:base.date,amountCents:-1250},date:"2026-10-23",
    amountCents:-1500};
  const f=fake([before]);let attempts=0;
  const r=await executeTransaction({api:f.api,input:cmd,
    recordAttempt:async()=>{attempts++;}});
  assert.equal(r.status,"committed");
  assert.equal(attempts,1);
  assert.deepEqual(f.calls,[
    ["update",id,{date:"2026-10-23",amount:-1500}],["sync"]
  ]);
  assert.equal(f.rows[0].payee,"payee-123");
});
test("changed amount and split/transfer transactions refuse edits",async()=>{
  const cmd={...base,action:"update",transactionId:"transaction-123",
    original:{date:base.date,amountCents:-1250}};
  for(const wrong of [
    {amount:-1400},{is_parent:true},{is_child:true},
    {transfer_id:"other"},{imported_id:"bank-100"},
    {subtransactions:[{amount:-1250}]}
  ]) {
    const f=fake([{id:cmd.transactionId,account:base.accountId,
      date:base.date,amount:-1250,...wrong}]);
    await assert.rejects(()=>executeTransaction({api:f.api,input:cmd,
      recordAttempt:async()=>{throw Error("must not attempt");}}));
    assert.equal(f.calls.length,0);
  }
});
