#!/usr/bin/env python3
"""Boundary contracts: new first Banking menu and private in-memory CSV review."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
finance=(root/"widgets/FinanceW.qml").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()
parser=(root/"widgets/FinanceBankingImportPolicy.js").read_text()
accounts=(root/"widgets/FinanceAccountsPane.qml").read_text()
guide=(root/"widgets/FinanceTransferGuidePane.qml").read_text()

first=finance.index('readonly property var mainModes:')
banking_mode=finance.index('{ id: "banking", name: "Banking", icon: "₊˚⋆🏛⊹"', first)
budget_mode=finance.index('{ id: "budget", name: "Budget"', first)
assert first<banking_mode<budget_mode
assert 'prefix: "₊˚⋆", core: "🏛", suffix: "⊹", coreSize: 30' in finance
assert 'selectedMainMode === "banking" ? "MANUAL"' in finance
assert 'root.selectedMainMode !== "banking"' in finance
assert 'visible: root.selectedMainMode === "banking"' in finance
assert 'FinanceBankingPane {' in finance
assert 'FinanceHouseholdPlanningPane {' in finance
assert 'FinanceTransferGuidePane {' in banking
assert 'FinanceTransferGuidePane {' not in accounts
assert 'FinanceBankingImportPolicy.js' in banking
assert 'selectedTool==="import"' in banking
assert 'PREVIEW PASTED CSV' in banking
assert 'IMPORT VERIFIED ROWS TO SESSION' in banking
assert 'CONFIRM EXCLUDE AS OWN TRANSFER' in banking
assert 'UNDO LAST TRANSFER CLASSIFICATION' in banking
assert 'CONFIRM CLEAR UNSAVED SESSION' in banking
assert 'NO ACCOUNTS CONNECTED // NO PAYMENT EXECUTED' in guide
assert 'TextEdit.PlainText' in banking
assert 'textFormat: Text.PlainText' in banking
assert 'confirmed=next;' in banking
assert 'ledger=copy;' in banking
assert 'MAX_CSV_CHARS=65536' in parser
assert 'MAX_IMPORT_ROWS=200' in parser
assert 'MAX_SESSION_ROWS=500' in parser
assert 'spendingLikeDebitsCents:debits-excluded' in parser
assert 'return {ok:false,error:"CSV MISSING OR OVER 64K CHARACTERS"}' in parser
assert 'connected:false,persisted:false' in parser
assert "onTextChanged:" in banking and "banking.pending=null" in banking
# These are not public service calls or import-to-Actual features.
for source in (banking,parser):
    for forbidden in (
        "FileView {", "XMLHttpRequest", "Qt.openUrlExternally",
        "financeFundingWrite", "financeWrite", "actual-cli", "access_token",
        "client_secret", "credentialStore", "onPaymentSent", "localStorage",
        "writeFile", "fetch(", "WebSocket"
    ):
        assert forbidden not in source, forbidden
# M2 adds one strictly read-only file-picker Process, not a bank action.
assert banking.count("Process {") == 1
assert banking.count("FileDialog {") == 1
assert "Process {" not in parser
assert "FinanceServices." not in banking
assert "sourceKey" not in banking
assert "FinanceAllocationWriteService" not in banking
assert "FinanceTransactionWriteService" not in banking
print("FinanceW Banking M1: menu order, icon and source isolation PASS")
