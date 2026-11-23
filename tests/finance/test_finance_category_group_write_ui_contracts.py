#!/usr/bin/env python3
"""FinanceW M6 category-group save is explicitly confirmed and separately locked."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceCategoriesPane.qml").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()
service=(root/"services/finance/FinanceCategoryGroupWriteService.qml").read_text()
plan=(root/"services/finance/FinanceCategoryGroupPlan.js").read_text()
writer=(root/"scripts/finance/write_category_group.mjs").read_text()
guard=(root/"scripts/finance/category_group_guard.mjs").read_text()

for required in (
    'property bool groupApprovalArmed: false',
    'property bool groupSubmitted: false',
    'property bool externalWriteBusy: false',
    'property string groupWriteState: "idle"',
    'property string groupWriteMessage: ""',
    'signal groupSaveRequested(var payload)',
    'readonly property bool groupProposalEligible:',
    'groupPreviewVisible',
    'groupPlan.ok && !busy && !externalWriteBusy',
    'groupPlan.sourceKey===groupSourceAtOpen',
    'groupPlan.sourceKey===snapshot.sourceKey',
    'groupPlan.month===groupMonthAtOpen',
    'groupPlan.month===snapshot.month',
    'function requestGroupSave()',
    'if(!groupProposalEligible || !groupApprovalArmed)return false;',
    'groupSubmitted=true;',
    'groupSaveRequested({',
    'mode:groupPlan.mode, requestId:requestId',
    'sourceKey:groupPlan.sourceKey, month:groupPlan.month',
    'groupId:groupPlan.groupId, expectedName:groupPlan.originalName',
    'proposedName:groupPlan.proposedName',
    'function clearGroupDraft()',
    'groupApprovalArmed=false;',
    'groupSubmitted=false;',
    'onGroupDraftNameChanged:',
    'onSnapshotChanged:',
    'onVisibleChanged: if(!visible)clearDraft()',
    ': categoryPane.groupApprovalArmed',
    '? "CONFIRM GROUP SAVE" : "ARM GROUP SAVE"',
    'available: categoryPane.groupProposalEligible',
    'categoryPane.requestGroupSave();',
    'categoryPane.groupWriteMessage',
    'GROUP SAVE REQUEST SENT // CHECK WRITER STATUS',
    'NOT SAVED // ACTUAL GROUP UNCHANGED',
    'property string writeState: "idle"',
    'signal saveRequested(var payload)',
    '"CONFIRM SAVE" : "ARM SAVE"',
):
    assert required in pane, required

assert pane.count('label: "PREVIEW GROUP"') == 1
assert pane.count('label: "CANCEL GROUP"') == 1
assert pane.count('label: "RENAME GROUP"') == 1

for required in (
    'FinanceServices.FinanceCategoryGroupWriteService {',
    'id: financeCategoryGroupWrite',
    'financeCategoriesPane.clearGroupDraft();',
    'financeBudget.refresh();',
    'groupWriteState: financeCategoryGroupWrite.state',
    'groupWriteMessage: financeCategoryGroupWrite.message',
    'externalWriteBusy: financeWrite.state==="pending"',
    'onGroupSaveRequested: function(payload)',
    'payload.sourceKey===financeBudget.snapshot.sourceKey',
    'payload.month===financeBudget.snapshot.month',
    'financeCategoryGroupWrite.submit(payload);',
    'financeCategoryWrite.state!=="pending"',
    'financeCategoryWrite.state!=="uncertain"',
    'financeWrite.state!=="pending"',
    'financeAllocationWrite.state!=="pending"',
    'financeFundingWrite.state!=="pending"',
    'financeCategoryGroupWrite.state!=="pending"',
    'financeCategoryGroupWrite.state!=="uncertain"',
    'financeCategoryGroupWrite.state==="pending"',
    'financeCategoryGroupWrite.state==="uncertain"',
    'financeCategoryWrite.submit(payload);',
):
    assert required in menu, required

for required in (
    'signal saved()',
    'function submit(command)',
    'if(state==="pending" || state==="uncertain" || worker.running',
    'command.mode!=="create" && command.mode!=="rename"',
    'stdinEnabled: true',
    'Quickshell.shellPath("scripts/finance/write_category_group.mjs")',
    'inputFrame=JSON.stringify(command)+"\\n";',
    'FINANCEW_CATEGORY_GROUP_RESULT',
    'bridge.outputStatus==="committed" && exitCode===0',
    'bridge.outputStatus==="blocked:writes-disabled"',
    'bridge.state="blocked";',
    'bridge.state="uncertain";',
    'GROUP WRITES LOCKED // OPERATOR ACTIVATION REQUIRED',
    'CHECK ACTUAL AND JOURNAL. DO NOT RETRY.',
    'bridge.saved();',
):
    assert required in service, required

for forbidden in (
    'Process {', 'LocalStorage', 'Settings {', 'writeFile(',
    'createCategoryGroup(', 'updateCategoryGroup(', 'deleteCategoryGroup(',
    'FINANCEW_CATEGORY_GROUP_WRITES_APPROVED',
    'category-group-writes-enabled', 'api.', 'Qt.openUrlExternally',
):
    assert forbidden not in pane, forbidden
    assert forbidden not in service, forbidden

for forbidden in (
    'createCategoryGroup(', 'updateCategoryGroup(', 'deleteCategoryGroup(',
    'FINANCEW_CATEGORY_GROUP_WRITES_APPROVED', 'category-group-writes-enabled',
    'Process {', 'writeFile(', 'api.',
):
    assert forbidden not in plan, forbidden

for required in (
    'privateFile(join(config,"category-group-writes-enabled"))',
    'FINANCEW_CATEGORY_GROUP_WRITES_APPROVED',
    'const lockPath=join(journalDir,".write-lock")',
    'if(attempted)return "uncertain";',
    'await executeGroup({api,input:command,recordAttempt})',
):
    assert required in writer, required

for required in (
    'await recordAttempt(cmd);',
    'await api.sync();',
    'await api.getCategoryGroups();',
):
    assert required in guard, required

print("FinanceW M6 group preview/arm/confirm independent-write-gate contracts: PASS")
