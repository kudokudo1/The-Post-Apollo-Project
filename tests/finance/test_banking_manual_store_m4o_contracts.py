#!/usr/bin/env python3
"""Banking M4o: local manual session storage authority and QML acceptance gates."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
manager=(root/"widgets/FinanceBankingAccountsPane.qml").read_text()
controls=(root/"widgets/FinanceBankingManualStorageControls.qml").read_text()
service=(root/"services/finance/FinanceBankingManualStore.qml").read_text()
backend=(root/"scripts/finance/banking_manual_store.py").read_text()
policy=(root/"widgets/FinanceBankingAccountsPolicy.js").read_text()
banking=(root/"widgets/FinanceBankingPane.qml").read_text()

for x in (
    'MAX_BYTES = 262144',
    'MAX_ACCOUNTS = 12',
    'MAX_ENTRIES = 300',
    'MAX_CENTS = 999999999',
    'def validate_session(session):',
    'def validate_doc(doc):',
    'def read_doc(directory: Path):',
    'def write_doc(directory: Path, doc):',
    'def run(directory: Path, command):',
    'def store_dir():',
    'banking-manual',
    'manual-session.json',
    '"version": 1',
    '"source": "LOCAL_OPERATOR_BANKING"',
    '"bankVerified": False',
    '"identityVerified": False',
    '"connected": False',
    'os.O_NOFOLLOW',
    'os.O_NONBLOCK',
    'os.O_EXCL',
    'fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)',
    'os.fsync(fd)',
    'os.replace(temp, path)',
    'os.fsync(dfd)',
    '0o700',
    '0o600',
    'previous["revision"] != command["expectedRevision"]',
    'STALE_REVISION',
    'WRITE_BUSY',
    'UNSAFE_RECORD',
    'UNSAFE_DIRECTORY',
    'ONLY_MANUAL_ACCOUNTS_CAN_BE_SAVED',
    'CLEAR_CONFIRMATION_REQUIRED',
    'confirmClear',
    'BROKEN_MANUAL_TRANSFER_PAIR',
    'INVALID_MANUAL_SESSION',
):
    assert x in backend,x

# Service alone holds the child process; manual Accounts QML/policy remain
# free of any filesystem, bank, Actual or network authority.
for x in (
    "import Quickshell.Io",
    'import "../../widgets/FinanceBankingAccountsPolicy.js" as Accounts',
    'property bool monitoring: false',
    'onMonitoringChanged:',
    'Component.onCompleted:',
    'if(!monitoring)return false;',
    'Quickshell.shellPath("scripts/finance/banking_manual_store.py")',
    'ACTUAL_PASSWORD_FILE:null',
    'ACTUAL_SYNC_ID:null',
    'ACTUAL_SERVER_URL:null',
    'ACTUAL_SYNC_ID_FILE:null',
    'function saveManual(session)',
    'function clearSaved()',
    'function acceptOutput(raw,code)',
    'result.source!=="LOCAL_OPERATOR_BANKING"',
    'result.connected!==false',
    'result.bankVerified!==false',
    'result.identityVerified!==false',
    '!Accounts.validState(result.session)',
    '["manual","empty"].includes(result.session.mode)',
    'result.savedOnDisk!==(result.revision>0)',
    'state="ready";',
    'store.state="failed";',
    'store.storeUnavailable();'
):
    assert x in service,x
assert service.count('Process {')==1

for x in (
    'property bool active: false',
    'property bool blocked: false',
    'property var manualSession: Accounts.emptyState()',
    'property bool initialized: false',
    'FinanceServices.FinanceBankingManualStore {',
    'monitoring: persistence.active',
    'onSessionLoaded:',
    'if(!persistence.initialized && !persistence.blocked)',
    'persistence.sessionRestored(localStore.savedSession);',
    'onStoreUnavailable:',
    'if(persistence.initialized)persistence.blocked=true;',
    'JSON.stringify(manualSession)!==JSON.stringify(localStore.savedSession)',
    'function saveNow()',
    'if(!saveArmed)',
    'localStore.saveManual(manualSession)',
    'function clearSavedNow()',
    'manualSession.mode!=="empty"',
    'localStore.clearSaved()',
    'SAVE LOCAL MANUAL ACCOUNTS // TWO CLICKS',
    'CONFIRM SAVE LOCAL MANUAL ACCOUNTS',
    'CLEAR SAVED MANUAL COPY // TWO CLICKS',
    'CONFIRM CLEAR SAVED MANUAL COPY',
    'LOCAL DEVICE FILE // NOT ENCRYPTED',
    'NO AUTOMATIC SAVE',
    'RETRY INITIAL LOCAL STORAGE LOAD',
):
    assert x in controls,x

for x in (
    'FinanceBankingManualStorageControls {',
    'id: storageControls',
    'active: manager.active',
    'manualSession: manager.session',
    'onSessionRestored: function(restored) {',
    'manager.session=restored;',
    'manager.selectedId="";',
    'manager.view="overview";',
    'enabled: storageControls.ready',
    'CHANGES NOT SAVED AUTOMATICALLY',
    'Accounts.emptyState()',
):
    assert x in manager,x
assert manager.count('enabled: storageControls.ready')==3
assert manager.index('FinanceBankingManualStorageControls {') < manager.index('visible: manager.view==="overview"')
assert 'FinanceBankingAccountsPane {' in banking

# The existing M3/M4i/M4j/M4l session writer and its bank-disconnected
# snapshots remain unchanged; disk availability is not bank connection.
assert 'mode:"empty",accounts:[],entries:[],nextId:1' in policy
assert 'function addManualTransfer(state,fields)' in policy
assert 'function correctManualTransfer(state,fields)' in policy
assert 'function correctAccountDetails(state,fields)' in policy
assert 'connected:false,persisted:false' in policy
for source in (manager,controls,backend):
    for forbidden in (
        "XMLHttpRequest","WebSocket","access_token","client_secret",
        "onPaymentSent","paymentExecution","onTraderOrder","actual-cli",
        "financeWrite","ACTUAL_SYNC=", "banking_csv_reader",
    ):
        assert forbidden not in source,forbidden
assert 'Process {' not in manager
assert 'Process {' not in controls
assert 'FinanceServices.' not in manager

print("Banking M4o: private manual Save/Restore/Clear authority, no-demo/real-bank boundaries, guarded QML controller and prior session isolation PASS")
