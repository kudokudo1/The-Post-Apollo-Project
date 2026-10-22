#!/usr/bin/env python3
"""FinanceW transaction draft staging contracts. Fictional data only."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
menu = (root / "widgets/FinanceW.qml").read_text()
pane = (root / "widgets/FinanceTransactionDraftPane.qml").read_text()
read_service = (root / "services/finance/FinanceBudgetReadService.qml").read_text()

# Prevent double/ghosted glow on NEW DRAFT and the five staged action
# labels. These use ActionButton's existing opt-in local source tracking.
# Preserve the existing non-mutating draft and account-cycle behavior.
import re
action_blocks = re.findall(
    r"\bActionButton\s*\{\s*(?:\/\/[^\n]*\n\s*)?"
    r"trackLabelGlowLocally:\s*true",
    pane,
)
assert pane.count("ActionButton {") == 5
assert len(action_blocks) == 5, (
    "All five staged draft controls need reactive label/glow alignment"
)
new_button = menu[menu.index("id: newTransactionDraft"):
                  menu.index("onLeftClicked: transactionDraftPane.begin()")]
assert "trackLabelGlowLocally: true" in new_button
for label in (
    'label: "ACCOUNT // " + draft.accountName',
    'label: draft.direction === "expense" ? "EXPENSE" : "INCOME"',
    'label: draft.reviewed ? "CONFIRM SAVE" : "PREVIEW"',
    'label: "CANCEL"',
):
    assert label in pane, f"Draft button changed: {label}"
assert 'label: "NEW DRAFT"' in new_button
action_shared = (root / "components/ActionButton.qml").read_text()
assert 'signal draftSaveRequested(var payload)' in pane
assert 'function requestDraftSave() {' in pane
assert 'function beginStored(record) {' in pane
assert 'label: draft.localDraftId ? "UPDATE DRAFT" : "SAVE DRAFT"' in pane
assert 'onLeftClicked: draft.requestDraftSave()' in pane
assert 'FinanceServices.FinanceLocalDraftStore {' in menu
assert 'id: financeDrafts' in menu
assert 'onDraftSaveRequested: function(payload)' in menu
assert 'financeDrafts.upsert(payload);' in menu
assert 'financeDrafts.remove(modelData.id);' in menu
assert 'transactionDraftPane.beginStored(modelData)' in menu
assert 'SAVED DRAFTS // ' in menu
# Shared ActionButton now tracks labels by default; FinanceW still opts in explicitly.
assert "property bool trackLabelGlowLocally: true" in action_shared
assert "contentHost.x + labelText.x" in action_shared
assert "contentHost.y + labelText.y" in action_shared

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
assert 'draft.reviewed = true;' in pane
assert 'draft.requestCommit();' in pane
assert 'onLeftClicked: draft.clear()' in pane
assert 'PREVIEW ONLY // NO CHANGES YET' in pane
assert 'signal saveRequested(var payload)' in pane
assert 'function requestCommit() {' in pane
assert 'saveRequested(payload);' in pane
assert 'onLeftClicked: transactionDraftPane.beginEdit(modelData)' in menu
assert 'id: editTransaction' in menu
assert 'FinanceServices.FinanceTransactionWriteService {' in menu
assert 'onSaved:' in menu
assert 'saveState: financeWrite.state' in menu
for forbidden in (
    "Process {", "Timer {", "LocalStorage", "Settings {",
    "getTransactions(", "updateTransaction(", "addTransaction(",
    "runBankSync(", "downloadBudget(", "api.", "fetch(", "XmlHttpRequest",
    "function commit(", "function save(", "onClicked: ",
):
    assert forbidden not in pane, forbidden
assert 'setBudgetAmount(' not in read_service
print("FinanceW draft UI staging contracts: PASS")
