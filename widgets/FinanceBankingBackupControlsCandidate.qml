import QtQuick
import "../components"
import "../services/finance" as FinanceServices
import "FinanceBankingBackupControlsPolicy.js" as Policy

// M4s1 // Detached functional candidate. Review enablement is a presentation
// gate, not a storage authorization boundary. No primary restore/import.
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
    property var rows: []
    property bool rowsLoaded: false
    property string selectedId: ""
    property var armed: null
    property string notice: "REFRESH TO INSPECT LOCAL BACKUPS"
    readonly property var selected: rows.find(function(row) {
        return row.backupId===panel.selectedId;
    }) || null
    implicitHeight: contents.implicitHeight

    onAvailableChanged: { discardContext(); invalidate(); }
    onSavedRevisionChanged: discardContext()
    onDirtyChanged: discardContext()
    onStoreReadyChanged: discardContext()
    onLocalSavedChanged: discardContext()
    onSelectedIdChanged: discardContext()

    function discardContext() {
        armed=null;
        if(bridge)bridge.discardContext();
    }

    function invalidate() {
        armed=null;
        rowsLoaded=false;
        rows=[];
        selectedId="";
    }
    function context() {
        return {enabled:reviewEnabled,active:active,busy:bridge.busy,
                ready:storeReady,dirty:dirty,localSaved:localSaved,
                revision:savedRevision};
    }
    function refresh() {
        if(!available||bridge.busy)return false;
        invalidate();
        notice="READING BACKUP METADATA";
        return bridge.invoke({action:"list"});
    }
    function createRequest() {
        if(!rowsLoaded||rows.length>=8)return null;
        return Policy.createCandidate(context());
    }
    function deleteRequest() {
        if(!rowsLoaded)return null;
        return Policy.deleteCandidate(context(),selected);
    }
    function confirm(request) {
        if(request===null||!available||bridge.busy)return false;
        var current=request.action==="create"?createRequest():request.action==="delete"?deleteRequest():null;
        if(!Policy.sameRequest(current,request))return false;
        if(!Policy.sameRequest(armed,request)) {
            armed=request;
            notice=request.action==="create"
                ?"CONFIRM PRIVATE PLAINTEXT BACKUP OF SAVED REVISION "+request.expectedRevision
                :"CONFIRM DELETION OF SELECTED BACKUP";
            return false;
        }
        // The second click obtains a newly validated candidate. Changing
        // selection, revision, visibility or save state cancels the first.
        armed=null;
        if(!bridge.invoke(request)) {
            notice="REQUEST NOT STARTED";
            return false;
        }
        notice="REQUEST PENDING // DO NOT REPEAT";
        return true;
    }
    FinanceServices.FinanceBankingBackupCandidateService {
        id: bridge
        allowed: panel.available
        onCompleted: function(receipt) {
            if(!panel.available) {
                panel.invalidate();
                return;
            }
            if(receipt.action==="list"){
                panel.rows=receipt.rows;
                panel.rowsLoaded=true;
                panel.notice=receipt.rows.length+" LOCAL BACKUPS";
            } else {
                panel.invalidate();
                panel.notice=receipt.action==="create"
                    ?"BACKUP CREATED // REFRESH LIST"
                    :"BACKUP DELETED // REFRESH LIST";
            }
        }
        onRefused: {
            panel.invalidate();
            panel.notice=bridge.retired?"REQUEST TIMED OUT // RESTART BANKING SESSION AND INSPECT FILES // NO RETRY":
                "RESULT NOT CONFIRMED // REFRESH BEFORE ANY NEW ACTION";
        }
    }

    Column {
        id: contents
        width: panel.width
        spacing: 5
        GohuText {
            width: parent.width
            text: "LOCAL MANUAL BACKUPS // "+(panel.reviewEnabled?"REVIEW CANDIDATE":"NOT ENABLED")
            color: Colors.magenta
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "PLAINTEXT PRIVATE COPIES // RESTORE AND IMPORT REQUIRE SEPARATE OFFLINE HANDOFF"
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 29
            label: "REFRESH BACKUPS"
            available: panel.available&&!bridge.busy
            onLeftClicked: panel.refresh()
        }
        Repeater {
            model: panel.available&&panel.rowsLoaded?panel.rows:[]
            delegate: ActionButton {
                required property var modelData
                width: contents.width
                height: 29
                labelPixelSize: 9
                label: modelData.createdUtc+" // R"+modelData.sourceRevision
                    +" // "+modelData.accountCount+" ACC // "+modelData.entryCount+" ENTRIES"
                selected: panel.selectedId===modelData.backupId
                available: panel.available&&!bridge.busy
                onLeftClicked: panel.selectedId=modelData.backupId
            }
        }
        ActionButton {
            width: parent.width
            height: 29
            label: panel.armed&&panel.armed.action==="create"
                ?"CONFIRM CREATE BACKUP":"CREATE SAVED BACKUP"
            accentColor: Colors.magenta
            available: panel.createRequest()!==null
            onLeftClicked: panel.confirm(panel.createRequest())
        }
        ActionButton {
            width: parent.width
            height: 29
            label: panel.armed&&panel.armed.action==="delete"
                ?"CONFIRM DELETE BACKUP":"DELETE SELECTED BACKUP"
            destructive: true
            accentColor: Colors.orange
            available: panel.deleteRequest()!==null
            onLeftClicked: panel.confirm(panel.deleteRequest())
        }
        ActionButton {
            width: parent.width
            height: 29
            label: "CANCEL CONFIRMATION"
            visible: panel.armed!==null
            available: panel.available&&!bridge.busy
            onLeftClicked: {
                panel.armed=null;
                panel.notice="CONFIRMATION CANCELLED";
            }
        }
        GohuText {
            width: parent.width
            text: panel.notice
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
