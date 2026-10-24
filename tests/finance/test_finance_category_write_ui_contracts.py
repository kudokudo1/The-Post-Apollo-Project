#!/usr/bin/env python3
"""M3 category confirmation: independent permit and no automatic retries."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceCategoriesPane.qml").read_text()
service=(root/"services/finance/FinanceCategoryWriteService.qml").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
writer=(root/"scripts/finance/write_category.mjs").read_text()
policy=(root/"scripts/finance/category_guard.mjs").read_text()

for item in (
    'signal saveRequested(var payload)',
    'property bool approvalArmed: false',
    'property bool submitted: false',
    'readonly property bool proposalEligible:',
    'previewVisible && !!plan && plan.ok',
    'plan.sourceKey===sourceAtOpen',
    'plan.sourceKey===snapshot.sourceKey',
    'plan.month===monthAtOpen',
    'plan.month===snapshot.month',
    'function requestSave()',
    'if(!proposalEligible || !approvalArmed)return false;',
    'submitted=true;',
    'mode:plan.mode, requestId:requestId, sourceKey:plan.sourceKey',
    'groupId:plan.groupId',
    'categoryId:plan.categoryId, expectedName:plan.originalName',
    'proposedName:plan.proposedName',
    'onDraftNameChanged:',
    'onSelectedGroupIdChanged:',
    'onSnapshotChanged:',
    'approvalArmed=false;',
    'label: categoryPane.submitted ? "REQUEST SUBMITTED"',
    '"CONFIRM SAVE" : "ARM SAVE"',
    'onLeftClicked: {',
    'categoryPane.requestSave();',
    'saveRequested({',
    'writeState==="pending" || writeState==="uncertain"',
    'available: !categoryPane.busy',
    'SAVE REQUIRES A SEPARATE OPERATOR PERMIT',
):
    assert item in pane, item

assert 'onVisibleChanged: if(!visible)clearDraft()' in pane
assert pane.count('label: "PREVIEW"')==1
assert pane.count('label: "CANCEL"')==1
assert pane.count('label: "RENAME"')==1
assert pane.count('label: "EDIT SET"')==1

for item in (
    'signal saved()',
    'function submit(command)',
    'if(state==="pending" || state==="uncertain" || worker.running',
    'stdinEnabled: true',
    'Quickshell.shellPath("scripts/finance/write_category.mjs")',
    'FINANCEW_CATEGORY_RESULT',
    'bridge.state="blocked";',
    'bridge.state="uncertain";',
    'bridge.saved();',
    'bridge.message="CATEGORY WRITES LOCKED // OPERATOR ACTIVATION REQUIRED";',
    'CHECK ACTUAL AND JOURNAL. DO NOT RETRY.',
):
    assert item in service,item

for item in (
    'FinanceServices.FinanceCategoryWriteService {',
    'id: financeCategoryWrite',
    'financeCategoriesPane.clearDraft();',
    'financeBudget.refresh();',
    'id: financeCategoriesPane',
    'writeState: financeCategoryWrite.state',
    'writeMessage: financeCategoryWrite.message',
    'onSaveRequested: function(payload)',
    'payload.sourceKey===financeBudget.snapshot.sourceKey',
    'payload.month===financeBudget.snapshot.month',
    'financeCategoryWrite.submit(payload);',
    'financeCategoryWrite.state==="pending"',
    'financeCategoryWrite.state==="uncertain"',
    'financeWrite.state!=="pending"',
    'financeAllocationWrite.state!=="pending"',
    'financeFundingWrite.state!=="pending"',
):
    assert item in menu,item

for forbidden in (
    'Process {','LocalStorage','Settings {','writeFile(',
    'createCategory(','updateCategory(','deleteCategory(',
    'FINANCEW_CATEGORY_WRITES_APPROVED','category-writes-enabled',
    'api.','Qt.openUrlExternally'
):
    assert forbidden not in pane,forbidden

for forbidden in (
    'FINANCEW_CATEGORY_WRITES_APPROVED','category-writes-enabled',
    'writeFile(','LocalStorage','Settings {','Qt.openUrlExternally',
    'createCategory(','updateCategory(','deleteCategory('
):
    assert forbidden not in service,forbidden

assert 'privateFile(join(config,"category-writes-enabled"))' in writer
assert 'FINANCEW_CATEGORY_WRITES_APPROVED' in writer
assert 'const lockPath=join(journalDir,".write-lock")' in writer
assert 'await recordAttempt(cmd);' in policy
assert 'await api.sync();' in policy
print("FinanceW M3 category preview/arm/confirm and separate-write-gate contracts: PASS")
