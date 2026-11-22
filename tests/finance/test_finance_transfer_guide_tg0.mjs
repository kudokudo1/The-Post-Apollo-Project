import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../widgets/FinanceTransferGuidePolicy.js', import.meta.url), 'utf8');
const context = vm.createContext({});
vm.runInContext(source, context);
const demo = context.accounts();

assert.equal(demo.length, 4);
assert.ok(demo.every(a => a.fictional === true && a.connectionState === 'NOT CONNECTED'));
assert.equal(context.amountCents('0.01'), 1);
assert.equal(context.amountCents('75'), 7500);
for (const value of ['', '0', '-1', '1.234', '01.00', 'abc', '100000', '1e3']) {
    assert.equal(context.amountCents(value), null, value + ' should be refused');
}
for (const source of demo) {
    for (const target of demo) {
        const plan = context.transferPlan(source.id, target.id, '12.34');
        if (source.id === target.id) {
            assert.equal(plan.ok, false);
        } else {
            assert.equal(plan.ok, true);
            assert.equal(plan.mode, 'GUIDANCE ONLY');
            assert.equal(plan.connected, false);
            assert.equal(plan.moneyMoved, false);
            assert.equal(plan.providerConfirmed, false);
            assert.equal(plan.amountCents, 1234);
            assert.equal(plan.steps.length, 5);
            assert.ok(plan.steps.some(s => s.includes('official provider app')));
        }
    }
}
assert.equal(context.transferPlan('forged', 'chime-demo', '1').ok, false);
assert.equal(context.transferPlan('cashapp-demo', 'chime-demo', '0').ok, false);
assert.equal(context.transferPlan('cashapp-demo', 'paypal-demo', '5').intermediated, true);
assert.equal(context.transferPlan('paypal-demo', 'cashapp-demo', '5').intermediated, true);

const rows = context.demoActivity();
const summary = context.spendingSummary(rows);
assert.equal(summary.ok, true);
assert.equal(summary.expensesCents, 79499);
assert.equal(summary.matchedInternalTransferPairs, 1);
assert.equal(summary.unmatchedTransferGroups, 0);
assert.equal(summary.connected, false);
assert.equal(summary.moneyMoved, false);
assert.equal(context.spendingSummary(rows.filter(r => r.id !== 'demo-2')).unmatchedTransferGroups, 1);
assert.equal(context.spendingSummary([...rows, rows[0]]).ok, false);
const tampered = rows.map(r => ({ ...r }));
tampered[1].amountCents = 7400;
assert.equal(context.spendingSummary(tampered).unmatchedTransferGroups, 1);
console.log('FinanceW TG0 fictional guidance, routes, amount validation and reconciliation PASS');
