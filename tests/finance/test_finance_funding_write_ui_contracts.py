#!/usr/bin/env python3
"""D17d: staged income write UI, independent authorization and refusal."""
from pathlib import Path
base=Path(__file__).resolve().parents[2]
pane=(base/"widgets/FinanceFundingSetupPane.qml").read_text()
menu=(base/"widgets/FinanceW.qml").read_text()
service=(base/"services/finance/FinanceFundingWriteService.qml").read_text()
writer=(base/"scripts/finance/write_funding.mjs").read_text()
policy=(base/"scripts/finance/FinanceFundingSetupPlan.js").read_text() if (base/"scripts/finance/FinanceFundingSetupPlan.js").exists() else (base/"services/finance/FinanceFundingSetupPlan.js").read_text()

for marker in (
    'property string writeState: "idle"',
    'property bool approvalArmed: false',
    'property bool submitted: false',
    'property string descriptionText: ""',
    'signal saveRequested(var payload)',
    'readonly property bool incomeProposalEligible:',
    'proposal.mode === "income"',
    'proposal.sourceKey === snapshot.sourceKey',
    'proposal.month === snapshot.month',
    'proposal.accountId === accountId',
    'proposal.categoryId === categoryId',
    'proposal.date === dateText',
    'FundingRules.parseFundingAmountCents(amountText) === proposal.amountCents',
    'descriptionText.trim().length <= 120',
    'function newRequestId()',
    'function requestSave()',
    'if(!expanded || !incomeProposalEligible || !approvalArmed',
    'submitted=true;',
    'mode:"income",requestId:requestId,',
    'sourceKey:proposal.sourceKey,accountId:proposal.accountId,',
    'month:proposal.month,date:proposal.date,',
    'amountCents:proposal.amountCents,categoryId:proposal.categoryId,',
    'description:descriptionText.trim()',
    'onSnapshotChanged:',
    'onDescriptionTextChanged: invalidatePreview()',
    'approvalArmed=false;',
    'onWriteStateChanged:',
    'label: setup.submitted ? "REQUEST SUBMITTED"',
    '"CONFIRM SAVE" : "ARM SAVE"',
    'available: setup.incomeProposalEligible && !setup.submitted',
    'if(setup.approvalArmed)',
    'setup.requestSave();',
    'readOnly: setup.writePending || setup.writeUncertain || setup.submitted',
    'visible: setup.setupMode==="income"',
    'OPENING BALANCE // NO SAVE / NO WRITES',
    'NEXT STEP MAY CHANGE ACTUAL IF SEPARATELY AUTHORIZED',
    'available: !setup.writePending && !setup.writeUncertain',
): assert marker in pane, marker

# On the existing-account opening route there is no save control.
save_button = pane[pane.index('label: setup.submitted ?'):pane.index('onLeftClicked: {',pane.index('label: setup.submitted ?'))]
assert 'visible: setup.setupMode==="income"' in pane[pane.rfind('ActionButton {',0,pane.index('label: setup.submitted ?')):pane.index('label: setup.submitted ?')]
assert 'new-account-opening' not in pane
assert 'new-account-opening' not in menu
for marker in (
    'FinanceServices.FinanceFundingWriteService {',
    'id: financeFundingWrite',
    'writeState: financeFundingWrite.state',
    'writeMessage: financeFundingWrite.message',
    'onSaveRequested: function(payload)',
    'payload.mode === "income"',
    'payload.sourceKey === financeBudget.snapshot.sourceKey',
    'payload.month === financeBudget.snapshot.month',
    'financeFundingWrite.state !== "uncertain"',
    'financeFundingWrite.state !== "pending"',
    'financeFundingWrite.submit(payload);',
    'guidedFundingPane.clear();',
    'financeBudget.refresh();'
): assert marker in menu, marker
for marker in (
    'signal saved()',
    'if(state === "pending" || state === "uncertain"',
    'command.mode !== "income"',
    'stdinEnabled: true',
    'worker.write(bridge.inputFrame);',
    'Quickshell.shellPath("scripts/finance/write_funding.mjs")',
    'FINANCEW_FUNDING_RESULT',
    'bridge.state="blocked";',
    'bridge.message="FUNDING WRITES LOCKED // OPERATOR ACTIVATION REQUIRED";',
    'bridge.state="uncertain";',
    'DO NOT RETRY.',
    'bridge.saved();',
): assert marker in service, marker
for forbidden in (
    'Process {', 'writeFile(', 'setBudgetAmount(', 'addTransactions(',
    'createAccount(', 'LocalStorage', 'Settings {',
    'funding-writes-enabled', 'FINANCEW_FUNDING_WRITES_APPROVED',
    'ACTUAL_PASSWORD', 'Qt.openUrlExternally'
): assert forbidden not in pane, forbidden
for forbidden in (
    'writeFile(', 'setBudgetAmount(', 'addTransactions(',
    'createAccount(', 'funding-writes-enabled', 'FINANCEW_FUNDING_WRITES_APPROVED',
    'LocalStorage', 'Settings {'
): assert forbidden not in service, forbidden
assert 'privateFile(join(config,"funding-writes-enabled"))' in writer
assert 'FINANCEW_FUNDING_WRITES_APPROVED' in writer
assert '"operations"' in writer and '".write-lock"' in writer
assert 'existing-account-opening' not in menu
assert 'writeAllowed:false,saveAvailable:false' in policy
print("FinanceW D17d guarded income confirmation UI contracts: PASS")
