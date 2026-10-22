#!/usr/bin/env python3
"""FinanceW transaction draft staging contracts. Fictional data only."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
menu = (root / "widgets/FinanceW.qml").read_text()
pane = (root / "widgets/FinanceTransactionDraftPane.qml").read_text()
read_service = (root / "services/finance/FinanceBudgetReadService.qml").read_text()

# UI is genuinely connected to the existing authenticated read-only snapshot.
assert 'FinanceTransactionDraftPane {' in menu
assert 'id: transactionDraftPane' in menu
assert 'accounts: financeBudget.snapshot' in menu
assert 'selectedMonth: financeBudget.selectedMonth' in menu
assert 'id: newTransactionDraft' in menu
assert 'onLeftClicked: transactionDraftPane.begin()' in menu
assert 'transactionDraftPane.clear();' in menu[menu.index("onMenuOpenChanged:"):
                                            menu.index("onKeyboardActiveChanged:")]
assert 'menuOpen && keyboardActive && !transactionDraftPane.open' in menu
assert 'financeBudget.state === "ready"' in menu
assert 'financeBudget.snapshot.accounts.length > 0' in menu

# No mutations, persistence, API, shell calls, or unauthorized save controls.
assert 'import "../components"' in pane
assert 'ActionButton {' in pane
assert 'property bool reviewed: false' in pane
assert 'function begin() {' in pane
assert 'function clear() {' in pane
assert 'onSelectedMonthChanged: clear()' in pane
assert 'onAccountsChanged:' in pane
assert 'draft.reviewed = false;' in pane
assert 'dateText = selectedMonth + "-01";' in pane
assert 'function parseCents(text)' in pane
assert 'Number.isSafeInteger(pennies)' in pane
assert r'/^\d{1,9}(?:\.\d{1,2})?$/' in pane
assert r'/^\d{4}-\d{2}-\d{2}$/' in pane
assert 'Date.UTC(parts[0], parts[1] - 1, parts[2])' in pane
assert 'input.slice(0, 7) !== selectedMonth' in pane
assert 'String(payeeText).trim().length > 120' in pane
assert 'available: !draft.validationError' in pane
assert 'onLeftClicked: draft.reviewed = true' in pane
assert 'onLeftClicked: draft.clear()' in pane
assert 'NOT SENT // NO SAVE OR EDIT PERMISSION' in pane
for forbidden in (
    "Process {", "Timer {", "LocalStorage", "Settings {",
    "getTransactions(", "updateTransaction(", "addTransaction(",
    "runBankSync(", "downloadBudget(", "api.", "fetch(", "XmlHttpRequest",
    "function commit(", "function save(", "onClicked: ",
):
    assert forbidden not in pane, forbidden
assert 'setBudgetAmount(' not in read_service
print("FinanceW draft UI staging contracts: PASS")
