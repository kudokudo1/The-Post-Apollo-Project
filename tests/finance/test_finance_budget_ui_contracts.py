#!/usr/bin/env python3
"""Read-only FinanceW on-demand Budget UI contracts, no personal data."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
ui = (root / "widgets/FinanceW.qml").read_text()
bridge = (root / "services/finance/FinanceBudgetReadService.qml").read_text()
cli = (root / "scripts/finance/read_budget.mjs").read_text()
assert 'FinanceServices.FinanceBudgetReadService {' in ui
assert 'onLeftClicked: financeBudget.refresh()' in ui
assert 'available: !financeBudget.loading' in ui
assert 'visible: !actualBudgetPage.visible' in ui
assert 'root.moneyText(modelData.balanceCents)' in ui
assert 'root.moneyText(modelData.availableCents)' in ui
assert 'root.moneyText(modelData.budgetedCents)' in ui
assert 'textFormat: Text.PlainText' in ui
assert 'property string state: "idle"' in bridge
assert 'if (loading || probe.running)' in bridge
assert 'Quickshell.shellPath("scripts/finance/read_budget.mjs")' in bridge
assert 'ACTUAL_SYNC_ID: null' in bridge
assert 'ACTUAL_SYNC_ID_FILE: null' in bridge
assert 'ACTUAL_PASSWORD_FILE: null' in bridge
assert 'ACTUAL_SERVER_URL: "http://127.0.0.1:5007"' in bridge
assert 'Number.isSafeInteger(payload.toBudgetCents)' in bridge
assert 'onStreamFinished: budgetBridge.acceptOutput(text)' in bridge
assert 'onStreamFinished: budgetBridge.acceptError(text)' in bridge
assert 'snapshot = null;' in bridge
assert 'Timer {' not in bridge
assert 'running: true' not in bridge
# QML's JS parser requires a catch binding; JS optional catch syntax
# would otherwise prevent the entire Post-Apollo shell from starting.
assert 'catch (error) {' in bridge
assert 'catch {' not in bridge
assert 'console.log' not in bridge
for forbidden in ('runBankSync(', 'setBudgetAmount(', 'updateTransaction('):
    assert forbidden not in bridge
for forbidden in ('password:', 'syncId:', 'ACTUAL_SYNC_ID='):
    assert forbidden not in ui
assert 'ACTUAL_SYNC_ID_FILE' in cli
print("FinanceW D3 manual read-only Budget UI contracts: PASS")
