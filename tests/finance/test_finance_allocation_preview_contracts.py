#!/usr/bin/env python3
"""D11 category preview remains pure after D12d guarded confirmation UI."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
widget = (root / "widgets/FinanceW.qml").read_text()
pane = (root / "widgets/FinanceCategoryAllocationPane.qml").read_text()
math = (root / "services/finance/FinanceAllocationPreview.js").read_text()
read = (root / "services/finance/FinanceBudgetReadService.qml").read_text()

assert 'FinanceCategoryAllocationPane {' in widget
assert 'id: allocationPreviewPane' in widget
assert 'snapshot: financeBudget.snapshot' in widget
assert 'id: allocationButton' in widget
assert 'label: "ALLOCATE"' in widget
assert 'onLeftClicked: allocationPreviewPane.begin(modelData)' in widget
assert 'id: allocationPreviewPane' in widget[widget.index('text: "CATEGORIES"'):widget.index('text: "TRANSACTIONS // "')]
assert 'onSnapshotChanged: clear()' in pane
assert 'readonly property bool sourceReady:' in pane
assert 'function begin(categoryRow)' in pane
assert 'function calculate()' in pane
assert 'PreviewRules.previewAllocation(snapshot, categoryId, targetText)' in pane
assert 'onTargetTextChanged:' in pane
assert 'label: "PREVIEW"' in pane
assert 'label: "CANCEL"' in pane
assert "PREVIEW IS SAFE // SAVING REQUIRES OPERATOR ACTIVATION" in pane
assert 'exceedsUnallocatedFunds' in pane
assert 'categoryRemainsOverspent' in pane
assert 'FinanceMoneyInput {' in pane
assert pane.count('ActionButton {') == 3
assert pane.count('trackLabelGlowLocally: true') == 3
assert 'category.availableCents + deltaCents' in math
assert 'snapshot.toBudgetCents - deltaCents' in math
assert 'Number.isSafeInteger' in math
assert 'sourceKey' in math
assert 'snapshot.readOnly !== true' in math
assert 'property var snapshot: null' in read
for forbidden in ("Process {", "LocalStorage", "Settings {", "financeWrite.submit",
                  "setBudgetAmount(", "api.", "addTransactions(",
                  "updateTransaction(", "onSaveRequested",
                  "Qt.openUrlExternally", "fetch("):
    assert forbidden not in pane, forbidden
for forbidden in ("fetch(", "api.", "setBudgetAmount(", "writeFile(",
                  "addTransactions(", "updateTransaction("):
    assert forbidden not in math, forbidden
print("FinanceW D11 read-only allocation preview contracts: PASS")
