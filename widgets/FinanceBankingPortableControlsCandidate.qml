import QtQuick
import "../components"
import "../services/finance" as FinanceServices
import "FinanceBankingPortableControlsPolicy.js" as Policy

// Detached and disabled by default. No live mount or import control.
Item {
    id: panel
    property bool reviewEnabled: false
    property bool active: false
    property bool storeReady: false
    property bool dirty: true
    property bool localSaved: false
    property int savedRevision: 0
    readonly property bool available: reviewEnabled&&active&&visible
    readonly property bool requestBusy: bridge.busy
    readonly property bool requestRetired: bridge.retired
    readonly property bool requestDrained: bridge.drained
    property var armed: null
    property var receipt: null
    property string notice: "PORTABLE EXPORT / PREVIEW ONLY"
    implicitHeight: contents.implicitHeight

    onAvailableChanged: clearSensitive()
    onSavedRevisionChanged: clearSensitive()
    onDirtyChanged: clearSensitive()
    onStoreReadyChanged: clearSensitive()
    onLocalSavedChanged: clearSensitive()

    function clearSensitive() {
        if(bridge)bridge.discardContext();
        armed=null;
        receipt=null;
        if(secret)secret.text="";
    }
    function context() {
        return {enabled:reviewEnabled,active:available,busy:bridge.busy,
            ready:storeReady,dirty:dirty,localSaved:localSaved,revision:savedRevision};
    }
    function candidate(action) {
        return Policy.validPassword(secret.text)?Policy.candidate(context(),action,fileId.text):null;
    }
    function confirm(action) {
        var intent=candidate(action);
        if(intent===null)return false;
        receipt=null;
        if(!Policy.sameIntent(armed,intent)){
            armed=intent;
            notice=action==="export"?"CONFIRM ENCRYPTED COPY OF SAVED R"+intent.expectedRevision:
                "CONFIRM AUTHENTICATED PREVIEW OF SELECTED FILE";
            return false;
        }
        armed=null;
        var started=bridge.invoke(intent,secret.text);
        secret.text="";
        notice=started?"REQUEST PENDING // DO NOT REPEAT":"REQUEST NOT STARTED";
        return started;
    }
    FinanceServices.FinanceBankingPortableCandidateService {
        id: bridge
        allowed: panel.available
        onCompleted: function(result) {
            // Inactive responses are refused by the bridge. Preview is bound
            // to the currently displayed file; export identifies saved R.
            if(!panel.available)return;
            if(result.action==="preview"&&result.portableId!==fileId.text)return;
            if(result.action==="export"&&result.sourceRevision!==panel.savedRevision)return;
            panel.receipt=result;
            panel.notice=result.action==="export"?"ENCRYPTED COPY CREATED":
                "CIPHERTEXT AUTHENTICATED // ORIGIN NOT VERIFIED";
        }
        onRefused: {
            panel.receipt=null;
            panel.armed=null;
            secret.text="";
            panel.notice=bridge.retired?"REQUEST TIMED OUT // RESTART BANKING SESSION AND INSPECT FILES // NO RETRY":
                "RESULT NOT CONFIRMED // INSPECT FILES BEFORE RETRY";
        }
    }
    Column {
        id: contents
        width: panel.width
        spacing: 5
        GohuText {
            width: parent.width
            text: "ENCRYPTED PORTABLE MANUAL ACCOUNTS // "+(panel.reviewEnabled?"REVIEW CANDIDATE":"NOT ENABLED")
            color: Colors.magenta
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "ONLY THE PORTABLE COPY IS ENCRYPTED. LOCAL LEDGER AND BACKUPS REMAIN PLAINTEXT. LOST PASSPHRASE CANNOT BE RECOVERED."
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText { text: "SEALED FILE ID // PREVIEW ONLY"; color: Colors.magenta }
        TextInput {
            id: fileId
            width: parent.width
            height: 28
            color: Colors.cyan
            maximumLength: 53
            clip: true
            enabled: panel.available&&!bridge.busy
            selectByMouse: true
            onTextChanged: panel.clearSensitive()
        }
        GohuText { text: "PASSPHRASE // AT LEAST 12 CHARACTERS"; color: Colors.magenta }
        TextInput {
            id: secret
            width: parent.width
            height: 28
            color: Colors.cyan
            maximumLength: 1025
            clip: true
            enabled: panel.available&&!bridge.busy
            echoMode: TextInput.Password
            inputMethodHints: Qt.ImhHiddenText | Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
            onTextChanged: {
                panel.armed=null;
                panel.receipt=null;
            }
            onActiveFocusChanged: {
                // Keep input while moving focus to explicit confirmation.
                // Availability, cancel, submission and ledger changes clear it.
                if(!panel.available)text="";
            }
        }
        ActionButton {
            width: parent.width
            height: 29
            label: panel.armed&&panel.armed.action==="export"?"CONFIRM EXPORT":"EXPORT SAVED MANUAL LEDGER"
            available: panel.candidate("export")!==null
            onLeftClicked: panel.confirm("export")
        }
        ActionButton {
            width: parent.width
            height: 29
            label: panel.armed&&panel.armed.action==="preview"?"CONFIRM PREVIEW":"AUTHENTICATE / PREVIEW SEALED FILE"
            available: panel.candidate("preview")!==null
            onLeftClicked: panel.confirm("preview")
        }
        ActionButton {
            width: parent.width
            height: 29
            label: "CANCEL / CLEAR PASSPHRASE"
            available: panel.available&&!bridge.busy
            onLeftClicked: {
                panel.clearSensitive();
                panel.notice="INPUT CLEARED";
            }
        }
        GohuText {
            width: parent.width
            text: panel.notice
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: panel.receipt!==null
            text: panel.receipt===null?"": "SOURCE R"+panel.receipt.sourceRevision+
                (panel.receipt.action==="preview"?" // "+panel.receipt.accountCount+" ACC // "+panel.receipt.entryCount+" ENTRIES":" // PRIVATE portable DIRECTORY")
            wrapMode: Text.WordWrap
        }
        TextInput {
            width: parent.width
            height: 28
            visible: panel.receipt!==null
            readOnly: true
            selectByMouse: true
            color: Colors.cyan
            clip: true
            text: panel.receipt===null?"":panel.receipt.portableId
        }
        GohuText {
            width: parent.width
            text: "IMPORT / RESTORE NOT AVAILABLE IN THIS CANDIDATE"
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
    }
}
