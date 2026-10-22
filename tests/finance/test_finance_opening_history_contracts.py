#!/usr/bin/env python3
"""D15 bounded, manual historical read-only inspection contracts."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
menu=(root/"widgets/FinanceW.qml").read_text()
service=(root/"services/finance/FinanceOpeningHistoryService.qml").read_text()
cli=(root/"scripts/finance/read_opening_history.mjs").read_text()
module=(root/"scripts/finance/opening_history.mjs").read_text()
assert 'FinanceServices.FinanceOpeningHistoryService {' in menu
assert 'id: openingHistory' in menu
assert 'month: financeBudget.selectedMonth' in menu
assert 'sourceKey: financeBudget.snapshot ? financeBudget.snapshot.sourceKey : ""' in menu
assert 'id: inspectOpeningBalances' in menu
assert 'label: "INSPECT OPENING BALANCES"' in menu
assert 'onLeftClicked: openingHistory.scan()' in menu
assert 'text: openingHistory.message' in menu
assert 'openingHistory.accounts' in menu
assert 'FIRST RECORDED // ' in menu
assert 'STARTING BALANCE CANDIDATES // ' in menu
assert 'NOT VERIFIED // CHECK BANK OPENING RECORD' in menu
assert 'onSourceKeyChanged: invalidate()' in service
assert 'onMonthChanged: invalidate()' in service
assert 'function scan() {' in service
assert 'if (worker.running || state === "reading"' in service
assert 'FINANCEW_HISTORY_MONTH: month' in service
assert 'Quickshell.shellPath("scripts/finance/read_opening_history.mjs")' in service
assert 'inflightSource !== history.sourceKey' in service
assert 'value.sourceKey!==history.sourceKey' in service
assert 'value.openingBalancesVerified!==false' in service
assert 'value.completeness!=="ledger-observation-only"' in service
assert 'property string state: "idle"' in service
assert 'getTransactions(account.id,start,month+"-31")' in module
assert 'const maxTransactionsPerAccount=10000' in module
assert 'const maxAccounts=30' in module
assert 'openingBalanceVerified:false' in module
assert 'openingBalancesVerified:false' in module
assert 'await api.getCategories()' in module
assert 'await api.getAccounts()' in module
assert 'await api.downloadBudget(syncId' in cli
assert 'const result=await takeOpeningHistory(api,month)' in cli
for src in (service,module,cli):
    for forbidden in ('setBudgetAmount(', 'updateTransaction(', 'addTransactions(',
                      'transaction-writes-enabled','allocation-writes-enabled'):
        assert forbidden not in src, forbidden
assert 'onMonitoringChanged' not in service
print("FinanceW D15 opening history source contracts: PASS")
