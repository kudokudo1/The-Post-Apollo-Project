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
      {name: "Usual Expenses", is_income: false, categories: [
        {id: "spotify", name: "Spotify Subscription",
          budgeted: 5000, spent: 0, balance: 5000}
      ]},
      {name: "Income", is_income: true, categories: [
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
  balances: new Map([["checking",25000]])
};

test("snapshot contains the original fictional $250 / $50 / $200 values", () => {
  const result = normalizeSnapshot(sample);
  assert.equal(result.readOnly, true);
  assert.equal(result.toBudgetCents, 20000);
  assert.deepEqual(result.accounts, [
    {name:"FinanceW Test Checking",balanceCents:25000}
  ]);
  assert.deepEqual(result.categories, [{
    id:"spotify",name:"Spotify Subscription",group:"Usual Expenses",
    budgetedCents:5000,spentCents:0,availableCents:5000
  }]);
  assert.equal(result.schemaVersion, 1);
});

test("only three Actual getters called, no financial mutations", async () => {
  const methods=[];
  const api = {
    getBudgetMonth: async month => {methods.push(["getBudgetMonth",month]);return sample.budget;},
    getAccounts: async () => {methods.push(["getAccounts"]);return sample.accounts;},
    getAccountBalance: async id => {methods.push(["getAccountBalance",id]);return 25000;}
  };
  const r=await takeReadOnlySnapshot(api, "2026-10");
  assert.equal(r.accounts[0].balanceCents,25000);
  assert.deepEqual(methods.map(x=>x[0]).sort(),
    ["getAccounts","getAccountBalance","getBudgetMonth"].sort());
});

test("fail closed rather than inventing a missing balance", () => {
  assert.throws(()=>normalizeSnapshot({...sample,
    budget: {...sample.budget,toBudget: undefined}}), /invalid-financial-field/);
  assert.throws(()=>normalizeSnapshot({...sample,
    balances: new Map()}), /unexpected-account/);
  assert.throws(()=>normalizeSnapshot({...sample,
    budget: {...sample.budget,categoryGroups: [{}]}}), /unexpected-category-group/);
  assert.throws(()=>normalizeSnapshot({...sample,
    budget: {...sample.budget,categoryGroups: [{
      name:"Usual Expenses",categories:[{id:"x",name:"Test",budgeted:500,
        spent:0,balance:5.3}]
    }]}}), /invalid-financial-field/);
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
  assert.ok(cli.includes('await rm(directory, {recursive: true, force: true})'));
  for(const forbidden of ["setBudgetAmount(","createAccount(","runBankSync(",
    "updateTransaction(","execSync(","setInterval("]) {
    assert.ok(!cli.includes(forbidden), forbidden);
  }
});
