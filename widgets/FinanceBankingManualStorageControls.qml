import QtQuick
import "../components"
import "../services/finance" as FinanceServices
import "FinanceBankingAccountsPolicy.js" as Accounts

// Banking M4o // Functional local Save/Restore controls, deliberately isolated
// from M3 manual ledger writers. No implicit save, import, bank connection,
// permission grant, or Actual Budget writer.
Item {
    id: persistence
    property var manualSession: Accounts.emptyState()
    property bool active: false
    property bool initialized: false
    property bool saveArmed: false
    property bool clearArmed: false
    property bool blocked: false // fail closed after an interrupted write
    property string notice: ""
    readonly property bool ready: initialized && !blocked
        && localStore.state==="ready"
    readonly property bool dirty: ready && manualSession.mode==="manual"
        && JSON.stringify(manualSession)!==JSON.stringify(localStore.savedSession)
    readonly property bool localSaved: ready && localStore.savedOnDisk
        && localStore.savedSession.mode==="manual"
    readonly property int savedRevision: localStore.revision
    signal sessionRestored(var session)
    implicitHeight: contents.implicitHeight

    onManualSessionChanged: {
        saveArmed=false;
        clearArmed=false;
    }
    FinanceServices.FinanceBankingManualStore {
        id: localStore
        monitoring: persistence.active
        onSessionLoaded: {
            // Load only once per component lifetime. Later refreshes cannot
            // silently replace manual edits in the visible account session.
            if(!persistence.initialized && !persistence.blocked) {
                persistence.initialized=true;
                persistence.sessionRestored(localStore.savedSession);
            }
        }
        onSessionSaved: {
            persistence.saveArmed=false;
            persistence.notice="LOCAL MANUAL SESSION SAVED // NOT BANK VERIFIED";
        }
        onSessionCleared: {
            persistence.clearArmed=false;
            persistence.notice="SAVED LOCAL MANUAL COPY CLEARED";
        }
        onStoreUnavailable: {
            // A failed write could indicate an external revision conflict.
            // Do not automatically retry with a newly observed revision.
            if(persistence.initialized)persistence.blocked=true;
            persistence.saveArmed=false;
            persistence.clearArmed=false;
            persistence.notice="LOCAL STORAGE REFUSED // MEMORY SESSION NOT SAVED";
        }
    }
    function saveNow() {
        if(!ready || !dirty || manualSession.mode!=="manual"
           || !Accounts.validState(manualSession))return false;
        if(!saveArmed) {
            saveArmed=true;
            notice="CLICK SAVE AGAIN // PRIVATE LOCAL COPY // NO BANK ACTION";
            return false;
        }
        saveArmed=false;
        if(!localStore.saveManual(manualSession)) {
            notice="LOCAL SAVE NOT STARTED";
            return false;
        }
        notice="LOCAL SAVE PENDING // DO NOT CLOSE UNTIL CONFIRMED";
        return true;
    }
    function clearSavedNow() {
        if(!ready||!localStore.savedOnDisk||manualSession.mode!=="empty")
            return false;
        if(!clearArmed) {
            clearArmed=true;
            notice="CLICK CLEAR AGAIN // ERASE SAVED LOCAL MANUAL COPY";
            return false;
        }
        clearArmed=false;
        if(!localStore.clearSaved()) {
            notice="LOCAL CLEAR NOT STARTED";
            return false;
        }
        notice="LOCAL CLEAR PENDING // DO NOT CLOSE UNTIL CONFIRMED";
        return true;
    }

    Column {
        id: contents
        width: persistence.width
        spacing: 5
        GohuText {
            width: parent.width
            text: !persistence.ready
                ? (persistence.blocked
                    ? "LOCAL BANKING STORAGE REFUSED // MEMORY DATA NOT SAVED"
                    : localStore.message)
                : persistence.dirty
                  ? "UNSAVED LOCAL MANUAL CHANGES // SAVE EXPLICITLY"
                  : persistence.localSaved
                    ? "PRIVATE LOCAL MANUAL COPY // REVISION "+persistence.savedRevision
                    : "NO LOCAL MANUAL COPY SAVED YET"
            font.pixelSize: 9
            color: persistence.blocked||persistence.dirty
                ? Colors.orange:Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "LOCAL DEVICE FILE // NOT ENCRYPTED // NOT A CONNECTED BANK // NO AUTOMATIC SAVE"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 29
            label: persistence.saveArmed
                ? "CONFIRM SAVE LOCAL MANUAL ACCOUNTS"
                : "SAVE LOCAL MANUAL ACCOUNTS // TWO CLICKS"
            labelPixelSize: 9
            accentColor: persistence.saveArmed?Colors.orange:Colors.magenta
            available: persistence.dirty
            onLeftClicked: persistence.saveNow()
        }
        ActionButton {
            width: parent.width
            height: 29
            visible: persistence.ready && persistence.localSaved
                && persistence.manualSession.mode==="empty"
            label: persistence.clearArmed
                ? "CONFIRM CLEAR SAVED MANUAL COPY"
                : "CLEAR SAVED MANUAL COPY // TWO CLICKS"
            labelPixelSize: 9
            accentColor: persistence.clearArmed?Colors.red:Colors.orange
            available: persistence.ready && persistence.localSaved
                && persistence.manualSession.mode==="empty"
            onLeftClicked: persistence.clearSavedNow()
        }
        ActionButton {
            width: parent.width
            height: 29
            visible: !persistence.initialized && localStore.state==="failed"
            label: "RETRY INITIAL LOCAL STORAGE LOAD"
            labelPixelSize: 9
            accentColor: Colors.cyan
            onLeftClicked: localStore.refresh()
        }
        GohuText {
            width: parent.width
            visible: persistence.notice!==""
            text: persistence.notice
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
