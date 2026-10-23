#!/usr/bin/env python3
"""FinanceW shared date and money input controls: UI and safety contracts."""
from pathlib import Path
base=Path(__file__).resolve().parents[2]
date=(base/"widgets/FinanceDateInput.qml").read_text()
money=(base/"widgets/FinanceMoneyInput.qml").read_text()
policy=(base/"services/finance/FinanceInputPolicy.js").read_text()
fund=(base/"widgets/FinanceFundingSetupPane.qml").read_text()
tx=(base/"widgets/FinanceTransactionDraftPane.qml").read_text()
allocation=(base/"widgets/FinanceCategoryAllocationPane.qml").read_text()
assert 'import "tasks" as TaskFields' in date
assert 'TaskFields.TaskDateSegment {' in date
assert 'onEditCommitted:' in date and 'onStepRequested:' in date
assert 'Rules.editDatePart(' in date and 'Rules.stepDatePart(' in date
assert 'signal valueEdited(string value)' in date
for item in ('"month"','"day"','"year"','"MM"','"DD"','"YYYY"'):
    assert item in date,item
assert 'text: "$"' in money
assert 'onEditingFinished: money.normalize()' in money
assert 'onTextEdited: money.valueEdited(text)' in money
assert 'Rules.normalizeAmount(' in money
assert 'readOnly: !money.canEdit' in money
assert "String(parts[1]||\"\").padEnd(2,\"0\")" in policy
assert 'new Date(Date.UTC(' in policy
assert 'function editDatePart(' in policy
assert 'function stepDatePart(' in policy
for name,text in (
 ("funding",fund),("transaction",tx)
):
    assert 'FinanceDateInput {' in text,name
    assert 'FinanceMoneyInput {' in text,name
    assert 'onValueEdited: function(value)' in text,name
assert 'FinanceMoneyInput {' in allocation
assert 'FinanceDateInput {' not in allocation
assert 'canEdit: !allocation.writePending && !allocation.writeUncertain' in allocation
assert 'canEdit: !draft.savePending' in tx
assert 'FundingRules.previewFundingSetup(snapshot,setupMode' in fund
assert 'PreviewRules.previewAllocation(snapshot, categoryId, targetText)' in allocation
assert 'function requestCommit() {' in tx
for text in (date,money,policy):
    for forbidden in ("setBudgetAmount(","updateTransaction(","addTransactions(",
      "writeFile(","Process {","LocalStorage","Settings {",
      "allocation-writes-enabled","transaction-writes-enabled"):
        assert forbidden not in text, forbidden
print("FinanceW shared numeric/date input controls: PASS")
