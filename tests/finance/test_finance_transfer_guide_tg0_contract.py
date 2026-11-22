#!/usr/bin/env python3
"""Ensure FinanceW transfer help cannot claim connection or execute money movement."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
policy = (root / "widgets/FinanceTransferGuidePolicy.js").read_text()
pane = (root / "widgets/FinanceTransferGuidePane.qml").read_text()
accounts = (root / "widgets/FinanceAccountsPane.qml").read_text()
banking = (root / "widgets/FinanceBankingPane.qml").read_text()

assert "FinanceTransferGuidePane {" in banking
assert "FinanceTransferGuidePane {" not in accounts
assert 'import "FinanceTransferGuidePolicy.js" as TransferGuidePolicy' in pane
assert "GUIDANCE ONLY // NO ACCOUNTS CONNECTED // NO PAYMENT EXECUTED" in pane
assert "PREVIEW TRANSFER INSTRUCTIONS" in pane
assert "FICTIONAL SPENDING EXAMPLE" in pane
assert "moneyMoved:false" in policy
assert "connected:false" in policy
assert "providerConfirmed:false" in policy
for forbidden in (
    "Process {", "FileView {", "XMLHttpRequest", "Qt.openUrlExternally",
    "financeFundingWrite", "financeWrite", "actual-cli", "/transfer/create",
    "access_token", "client_secret", "passwordInput", "credentialStore",
    "onPaymentSent"
):
    assert forbidden not in policy + pane, forbidden
assert "FinanceServices." not in pane
assert "sourceKey" not in pane
print("FinanceW TG0 isolated no-transfer-writer source boundary PASS")
