#!/usr/bin/env python3
"""Banking M4f: permission-safe manual correction/deletion and QML selection."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
accounts=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
provider=(root/"widgets/FinanceBankingProviderPane.qml").read_text()
journal=(root/"widgets/FinanceBankingSessionJournalPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
finance=(root/"widgets/FinanceW.qml").read_text()
official=(root/"widgets/FinanceBankingOfficialHandoff.qml").read_text()

for requirement in (
    "function matchManualEntry(state,fields)",
    'if(!validState(state)||state.mode!=="manual")',
    "entry.accountId!==fields.accountId",
    "entry.date!==fields.expectedDate",
    "entry.description!==fields.expectedDescription",
    "entry.amountCents!==fields.expectedAmountCents",
    "STALE MANUAL ENTRY // RESELECT BEFORE CHANGING",
    "function correctEntry(state,fields)",
    "function deleteEntry(state,fields)",
    "var match=matchManualEntry(state,fields);",
    "dateValid(fields.date)",
    "safeText(fields.description,120)",
    'fields.direction!=="in"&&fields.direction!=="out"',
    "parseCents(fields.amountText,false)",
    "id:match.entry.id,accountId:match.entry.accountId",
    'origin:"manual"',
    "entries[match.index]=fixed;",
    "entries.splice(match.index,1);",
    "nextId:state.nextId",
    "return validState(updated)?{ok:true,state:updated,corrected:fixed}",
    "return validState(updated)?{ok:true,state:updated,deleted:match.entry}"
):
    assert requirement in accounts,requirement

for requirement in (
    "function changeProviderEntry(draft,remove)",
    'view!=="provider"||providerMiniApp.sectionId!=="activity"',
    'session.mode!=="manual"',
    'draft.providerId!==selectedProviderId',
    "a.id===draft.accountId && a.providerId===selectedProviderId",
    "record.accountId!==owner.id",
    'record.origin!=="manual"',
    "Accounts.deleteEntry(session,draft)",
    "Accounts.correctEntry(session,draft)",
    "onManualCorrectionRequested: function(draft)",
    "onManualDeletionRequested: function(draft)",
    "manager.changeProviderEntry(draft,false)",
    "manager.changeProviderEntry(draft,true)",
    "providerMiniApp.clearSelectedEntry()",
    "MANUAL SESSION ENTRY CORRECTED // NO BANK RECORD CHANGED",
    "MANUAL SESSION ENTRY DELETED // NO BANK RECORD CHANGED"
):
    assert requirement in manager,requirement

for requirement in (
    "property var correctionCandidate: null",
    'property string correctionDirection: "out"',
    "property bool correctionDeleteArmed: false",
    "signal manualCorrectionRequested(var draft)",
    "signal manualDeletionRequested(var draft)",
    "function chooseManualEntry(row)",
    "function clearSelectedEntry()",
    "function requestCorrection()",
    "function requestDeletion()",
    'manualSession.mode!=="manual"',
    "filteredActivity.rows.some(function(e)",
    "expectedDate:row.date",
    "expectedDescription:row.description",
    "expectedAmountCents:row.amountCents",
    "entryId:row.id,accountId:row.accountId",
    "date:editDate.text,description:editDescription.text",
    "amountText:editAmount.text,direction:correctionDirection",
    "correctionDeleteArmed=true;",
    "correctionDeleteArmed=false;",
    "manualDeletionRequested({",
    "manualCorrectionRequested({",
    "onManualSessionChanged: {",
    "onActivityPageIndexChanged: clearSelectedEntry()",
    "CORRECT MANUAL ENTRY // SESSION ONLY // ACCOUNT ID IS LOCKED",
    "SAVE MANUAL ENTRY CORRECTION",
    "DELETE SELECTED MANUAL ENTRY // TWO CLICKS",
    "CONFIRM DELETE ORIGINAL MANUAL ENTRY",
    "SECOND CLICK PERMANENTLY REMOVES THIS ENTRY",
    "CORRECT / REMOVE THIS MANUAL ENTRY",
    "onLeftClicked: providerPane.chooseManualEntry(modelData)",
    "CANCEL MANUAL CORRECTION",
    "id: editDate",
    "id: editDescription",
    "id: editAmount",
    "visible: providerPane.manualSession.mode===\"manual\"",
    "providerPane.filteredActivity.ok?providerPane.filteredActivity.rows:[]"
):
    assert requirement in provider,requirement

assert 'max' in journal and "MAX_ENTRIES=300" in journal
assert 'FinanceBankingOfficialHandoff {' in provider
assert 'Qt.openUrlExternally' in official
assert 'Qt.openUrlExternally' not in provider
assert "Accounts.addEntry(session,{" in manager
assert "FinanceBankingAccountsPane {" in banking
assert '{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"' in finance
for text in (manager,accounts,provider):
    for forbidden in (
        "Process {","FileDialog {","FileView {","XMLHttpRequest","fetch(",
        "WebSocket","localStorage","FinanceServices.","financeWrite",
        "actual-cli","ACTUAL_PASSWORD","ACTUAL_SYNC","access_token",
        "client_secret","onPaymentSent","openDatabase","writeFile(",
        "paymentExecution","onTraderOrder","Quickshell.Io","Settings {"
    ):
        assert forbidden not in text,forbidden
print("FinanceW Banking M4f: M3-only correction authority, immutable record IDs, confirmed deletion and no financial execution PASS")
