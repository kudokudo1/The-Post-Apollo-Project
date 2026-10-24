import assert from "node:assert/strict";
import {test} from "node:test";
import {readFile} from "node:fs/promises";
import {validMonth, localServerUrl, normalizeSnapshot,
  takeReadOnlySnapshot} from "../../scripts/finance/actual_readonly.mjs";

const sample = {
  month: "2026-10",
  budget: {
    toBudget: 20000,
    categoryGroups: [
      {id:"group-expenses", name: "Usual Expenses", is_income: false, categories: [
        {id: "spotify", name: "Spotify Subscription",
          budgeted: 5000, spent: 0, balance: 5000}
      ]},
      {id:"group-income", name: "Income", is_income: true, categories: [
        {id:"income", name:"Starting Balances",
          budgeted:0, spent:0, balance:25000}
      ]}
    ]
  },
  accounts: [
    {id:"checking", name:"FinanceW Test Checking", offbudget:false, closed:false},
    {id:"closed", name:"Old account", closed:true},
    {id:"other", name:"Off-budget", offbudget:true}
  ],
  balances: new Map([["checking",25000]]),
  payees: [{id:"shop",name:"Corner Market"}],
  transactionSets: new Map([["checking",[
    {id:"txn-18",date:"2026-10-18", account:"checking", amount:-1200, payee_id:"shop", cleared:true},
    {id:"txn-19",date:"2026-10-19", account:"checking", amount:25000, imported_payee:"Payroll"},
    {id:"txn-17",date:"2026-10-17", account:"checking", amount:-220, payee_id:"missing"}
  ]]])
};

test("snapshot contains the original fictional $250 / $50 / $200 values", () => {
  const result = normalizeSnapshot(sample);
  assert.equal(result.readOnly, true);
  assert.equal(result.toBudgetCents, 20000);
  assert.deepEqual(result.accounts, [
    {id:"checking",name:"FinanceW Test Checking",balanceCents:25000}
  ]);
  assert.deepEqual(result.categories, [{
    id:"spotify",name:"Spotify Subscription",group:"Usual Expenses",
    groupId:"group-expenses",budgetedCents:5000,spentCents:0,availableCents:5000
  }]);
  assert.deepEqual(result.categoryGroups,[{id:"group-expenses",name:"Usual Expenses"}]);
  assert.equal(result.schemaVersion, 1);
  assert.equal(result.transactionsCount, 3);
  assert.deepEqual(result.transactions.map(x=>x.date),
    ["2026-10-19","2026-10-18","2026-10-17"]);
  assert.equal(result.transactions[1].description, "Corner Market");
  assert.equal(result.accounts[0].id, "checking");
  assert.equal(result.transactions[1].id, "txn-18");
  assert.equal(result.transactions[1].accountId, "checking");
  assert.equal(result.transactions[1].editable, true);
  assert.equal(result.transactions[1].amountCents, -1200);
  assert.equal(result.transactions[2].description, "TRANSACTION");
});

test("only read-only Actual getters called, no financial mutations", async () => {
  const methods=[];
  const api = {
    getBudgetMonth: async month => {methods.push(["getBudgetMonth",month]);return sample.budget;},
    getAccounts: async () => {methods.push(["getAccounts"]);return sample.accounts;},
    getAccountBalance: async id => {methods.push(["getAccountBalance",id]);return 25000;},
    getPayees: async () => {methods.push(["getPayees"]);return sample.payees;},
    getTransactions: async (id, start, end) => {
      methods.push(["getTransactions",id,start,end]);
      return sample.transactionSets.get(id);
    }
  };
  const r=await takeReadOnlySnapshot(api, "2026-10");
  assert.equal(r.accounts[0].balanceCents,25000);
  assert.equal(r.transactionsCount, 3);
  assert.deepEqual(methods.find(x=>x[0]==="getTransactions").slice(1),
    ["checking", "2026-10-01", "2026-10-31"]);
  assert.deepEqual(methods.map(x=>x[0]).sort(),
    ["getAccounts","getAccountBalance","getBudgetMonth","getPayees","getTransactions"].sort());
});

test("fail closed rather than inventing a missing balance", () => {
  assert.throws(()=>normalizeSnapshot({...sample,
    budget: {...sample.budget,toBudget: undefined}}), /invalid-financial-field/);
  assert.throws(()=>normalizeSnapshot({...sample,
    balances: new Map()}), /unexpected-account/);
  assert.throws(()=>normalizeSnapshot({...sample,
    budget:{...sample.budget,categoryGroups:[{...sample.budget.categoryGroups[0],id:undefined}]} }),
    /unexpected-category-group-identity/);
  assert.throws(()=>normalizeSnapshot({...sample,
    budget: {...sample.budget,categoryGroups: [{}]}}), /unexpected-category-group/);
  assert.throws(()=>normalizeSnapshot({...sample,
    budget: {...sample.budget,categoryGroups: [{
      id:"group-expenses",name:"Usual Expenses",categories:[{id:"x",name:"Test",budgeted:500,
        spent:0,balance:5.3}]
    }]}}), /invalid-financial-field/);
});

test("transaction input validation refuses bad dates, amounts, and accounts", () => {
  const bad = badRow => ({...sample, transactionSets: new Map([
    ["checking", [badRow]]
  ])});
  const row = sample.transactionSets.get("checking")[0];
  assert.throws(()=>normalizeSnapshot(bad({...row,amount:1.5})),
    /invalid-financial-field/);
  assert.throws(()=>normalizeSnapshot(bad({...row,date:"2026-09-30"})),
    /unexpected-transaction/);
  assert.throws(()=>normalizeSnapshot(bad({...row,account:"other"})),
    /unexpected-transaction/);
  assert.throws(()=>normalizeSnapshot(bad({...row,id:undefined})),
    /unexpected-transaction/);
  assert.throws(()=>normalizeSnapshot({...sample,
    transactionSets:new Map([["checking", "nope"]])}), /unexpected-transactions/);
});

test("latest transaction preview is bounded to 24 items, never totals splits", () => {
  const entries = Array.from({length: 40}, (_, index) => ({
    id: "bulk-"+index, date: "2026-10-18", account: "checking", amount: -100 - index
  }));
  const snapshot = normalizeSnapshot({...sample,
    transactionSets: new Map([["checking",entries]])});
  assert.equal(snapshot.transactionsCount, 40);
  assert.equal(snapshot.transactions.length, 24);
  assert.ok(snapshot.transactions.every(x => !("subtransactions" in x)));
});

test("local URLs and months only", () => {
  assert.equal(localServerUrl(), "http://127.0.0.1:5007");
  assert.equal(localServerUrl("http://localhost:5007"),"http://localhost:5007");
  for(const url of ["https://example.com", "http://192.168.1.7:5007",
      "file:///tmp/budget", "http://user:pass@localhost:5007",
      "http://localhost:5007/?password=abc"]) {
    assert.throws(()=>localServerUrl(url));
  }
  assert.equal(validMonth("2026-10"),true);
  assert.equal(validMonth("2026-13"),false);
});

test("CLI has no budget mutator or auto-start feature", async () => {
  const cli = await readFile(new URL("../../scripts/finance/read_budget.mjs",
    import.meta.url),"utf8");
  assert.ok(cli.includes('ACTUAL_PASSWORD_FILE'));
  assert.ok(cli.includes('await readActualServerURL()'));
  assert.ok(cli.includes('ACTUAL_SYNC_ID_FILE'));
  assert.ok(cli.includes('".config", "financew", "actual-sync-id"'));
  assert.ok(cli.includes('".config", "financew", "actual-password"'));
  assert.ok(cli.includes('await rm(directory, {recursive: true, force: true})'));
  for(const forbidden of ["setBudgetAmount(","createAccount(","runBankSync(",
    "updateTransaction(","execSync(","setInterval("]) {
    assert.ok(!cli.includes(forbidden), forbidden);
  }
});
