import QtQuick
import QtQuick.Dialogs
import Quickshell
import Quickshell.Io
import "../components"
import "FinanceBankingImportPolicy.js" as BankingPolicy

// Banking M1: single Linux user's ephemeral manual CSV review.
// No bank connection, bank balance, Actual mutation, storage, network or transfer writer.
Item {
    id: banking
    property bool active: false
    property string selectedTool: "accounts" // accounts | transfers | import
    property int importSourceIndex: 0
    property var ledger: []
    property var pending: null
    property var confirmed: []
    property int nextRowId: 1
    property bool clearArmed: false
    property string armedPairKey: ""
    property string notice: ""
    // M2 file selection: the picker chooses one local file and a bounded
    // subprocess reads it. Raw financial statement bytes are never logged.
    property int fileSequence: 0
    property int editorEpoch: 0
    property int fileEditorEpoch: -1
    property string fileToken: ""
    property string fileSource: ""
    property string pickerSource: ""
    property string fileFrame: ""
    property string fileOutput: ""
    property string fileState: "idle" // idle | pending | refused | ready | cancelled
    readonly property var sources: BankingPolicy.accounts()
    readonly property var summary: BankingPolicy.review(ledger,confirmed)
    readonly property var candidates: summary.ok ? summary.candidates : []

    function sourceId() {
        return sources[importSourceIndex].id;
    }
    function beginFileRead(fileUrl, selectedSource) {
        if(!active || selectedTool!=="import"
                || fileReader.running || fileState==="pending"
                || selectedSource!==sourceId()) {
            notice="FILE SELECTION CANCELLED // SOURCE OR VIEW CHANGED";
            return false;
        }
        fileSequence+=1;
        if(fileSequence>99999999)fileSequence=1;
        fileToken="file-"+fileSequence;
        fileSource=selectedSource;
        fileEditorEpoch=editorEpoch;
        fileFrame=JSON.stringify({version:1,token:fileToken,fileUrl:fileUrl})+"\n";
        fileOutput="";
        pending=null;
        armedPairKey="";
        clearArmed=false;
        fileState="pending";
        notice="READING SELECTED CSV // LOCAL ONLY // NO IMPORT YET";
        fileReader.exec({
            command:["/usr/bin/env","python3",
                Quickshell.shellPath("scripts/finance/banking_csv_reader.py")],
            environment: ({ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null})
        });
        return true;
    }
    function previewCsv() {
        clearArmed=false;
        armedPairKey="";
        pending=BankingPolicy.parseCsv(csvInput.text,sourceId());
        notice=pending.ok
            ? "READY TO IMPORT "+pending.rowsCount+" ROWS FROM "+pending.sourceName
            : pending.error;
    }
    function commitCsv() {
        if(!pending||!pending.ok||ledger.length+pending.rows.length>500) {
            notice="IMPORT REFUSED // LIMIT 500 SESSION ROWS";
            return false;
        }
        var copy=ledger.slice();
        var next=nextRowId;
        for(var i=0;i<pending.rows.length;i++) {
            var row=pending.rows[i];
            copy.push({id:"manual-"+next++,sourceId:row.sourceId,
                sourceName:row.sourceName,date:row.date,
                description:row.description,amountCents:row.amountCents,
                fingerprint:row.fingerprint});
        }
        var check=BankingPolicy.review(copy,confirmed);
        if(!check.ok) {
            notice="IMPORT REFUSED // "+check.error;
            return false;
        }
        var count=pending.rows.length;
        ledger=copy;
        nextRowId=next;
        pending=null;
        csvInput.text="";
        armedPairKey="";
        notice="IMPORTED "+count+" MANUAL ROWS // SESSION ONLY // NOT BANK SYNC";
        return true;
    }
    function confirmCandidate(candidate) {
        if(!candidate||!summary.ok)return false;
        var key=candidate.fromId+"|"+candidate.toId;
        if(armedPairKey!==key) {
            armedPairKey=key;
            notice="REVIEW BOTH OWNED ACCOUNTS // CLICK CONFIRM AGAIN";
            return false;
        }
        var stillPresent=candidates.some(function(c) {
            return c.fromId===candidate.fromId&&c.toId===candidate.toId
                &&c.amountCents===candidate.amountCents;
        });
        if(!stillPresent)return false;
        var next=confirmed.concat([[candidate.fromId,candidate.toId]]);
        var check=BankingPolicy.review(ledger,next);
        if(!check.ok)return false;
        confirmed=next;
        armedPairKey="";
        notice="CLASSIFIED ONE MATCHED PAIR AS YOUR OWN TRANSFER // NO MONEY MOVED";
        return true;
    }
    function undoLast() {
        if(confirmed.length===0)return;
        confirmed=confirmed.slice(0,-1);
        armedPairKey="";
        notice="LAST CLASSIFICATION UNDONE // DEBIT RESTORED TO SPENDING REVIEW";
    }
    function clearSession() {
        if(!clearArmed) {
            clearArmed=true;
            notice="CLICK CLEAR AGAIN TO DISCARD ALL UNSAVED SESSION DATA";
            return;
        }
        ledger=[];
        confirmed=[];
        pending=null;
        csvInput.text="";
        nextRowId=1;
        armedPairKey="";
        clearArmed=false;
        if(fileState==="pending")fileState="cancelled";
        fileFrame="";
        fileOutput="";
        notice="SESSION CLEARED // NO FILES WERE MODIFIED";
    }
    onImportSourceIndexChanged: {
        pending=null;
        armedPairKey="";
        if(fileState==="pending")fileState="cancelled";
    }
    onSelectedToolChanged: {
        armedPairKey="";
        clearArmed=false;
        if(fileState==="pending")fileState="cancelled";
        bankingScroll.flickable.contentY=0;
    }
    onActiveChanged: {
        if(!active && fileState==="pending")fileState="cancelled";
    }

    // A native Qt dialog selects one file. No requested paths are persisted.
    FileDialog {
        id: statementPicker
        title: "Select one local CSV statement"
        fileMode: FileDialog.OpenFile
        nameFilters: ["CSV statements (*.csv)"]
        options: FileDialog.ReadOnly
        onAccepted: banking.beginFileRead(String(selectedFile),banking.pickerSource)
        onRejected: banking.notice="FILE PICKER CANCELLED // NO CHANGE"
    }

    Process {
        id: fileReader
        stdinEnabled: true
        onStarted: {
            if(banking.fileFrame) {
                fileReader.write(banking.fileFrame);
                banking.fileFrame="";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                // No raw CSV or selected path is printed or sent to logs.
                const lines=String(text||"").split(/\r?\n/);
                for(let i=0;i<lines.length;i++) {
                    if(lines[i].startsWith("FINANCEW_BANKING_FILE_RESULT "))
                        banking.fileOutput=lines[i].slice(29);
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                const sameRequest=banking.fileState==="pending"
                    && banking.fileSource===banking.sourceId()
                    && banking.fileEditorEpoch===banking.editorEpoch
                    && banking.active && banking.selectedTool==="import";
                if(sameRequest) {
                    try {
                        if(exitCode!==0 || !banking.fileOutput
                                || banking.fileOutput.length>550000)
                            throw new Error("FILE_READ_REFUSED");
                        const payload=JSON.parse(banking.fileOutput);
                        if(!payload || payload.version!==1
                                || payload.token!==banking.fileToken
                                || payload.ok!==true
                                || typeof payload.csv!=="string"
                                || payload.csv.length>65536)
                            throw new Error("FILE_READ_REFUSED");
                        const result=BankingPolicy.parseCsv(
                            payload.csv,banking.fileSource);
                        banking.pending=result;
                        banking.notice=result.ok
                            ? "SELECTED CSV VERIFIED // "+result.rowsCount
                                +" ROWS // REVIEW BEFORE IMPORT"
                            : "SELECTED CSV REFUSED // "+result.error;
                        banking.fileState=result.ok?"ready":"refused";
                    } catch(error) {
                        banking.pending=null;
                        banking.fileState="refused";
                        banking.notice="LOCAL CSV COULD NOT BE READ OR VERIFIED";
                    }
                }
                banking.fileFrame="";
                banking.fileOutput="";
                banking.fileToken="";
                banking.fileSource="";
                banking.fileEditorEpoch=-1;
                if(!sameRequest && banking.fileState==="cancelled")
                    banking.notice="STALE FILE RESULT DISCARDED // NO IMPORT";
            });
        }
    }

    Row {
        id: toolTabs
        anchors.top: parent.top
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 5
        ActionButton {
            width: (toolTabs.width-10)/3
            height: 31
            label: "ACCOUNTS"
            labelPixelSize: 9
            accentColor: Colors.magenta
            selected: banking.selectedTool==="accounts"
            onLeftClicked: banking.selectedTool="accounts"
        }
        ActionButton {
            width: (toolTabs.width-10)/3
            height: 31
            label: "TRANSFERS"
            labelPixelSize: 9
            accentColor: Colors.cyan
            selected: banking.selectedTool==="transfers"
            onLeftClicked: banking.selectedTool="transfers"
        }
        ActionButton {
            width: (toolTabs.width-10)/3
            height: 31
            label: "IMPORT"
            labelPixelSize: 9
            accentColor: Colors.omnitrix
            selected: banking.selectedTool==="import"
            onLeftClicked: banking.selectedTool="import"
        }
    }

    NeonScrollPaneV2 {
        id: bankingScroll
        anchors.top: toolTabs.bottom
        anchors.topMargin: 3
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        availableExtent: height
        viewportPolicy: "fill"
        contentExtent: scrollBody.implicitHeight+18
        handleStyle: "bar"

        Column {
            id: scrollBody
            x: 8
            y: 7
            width: Math.max(0,bankingScroll.width-34)
            spacing: 8

            GohuText {
                width: parent.width
                text: banking.selectedTool==="accounts"
                      ? "BANKING // ACCOUNT MANAGER"
                      : banking.selectedTool==="transfers"
                        ? "BANKING // TRANSFER ASSISTANT" : "BANKING // TRANSACTION IMPORT"
                font.pixelSize: 12
                font.bold: true
                color: Colors.magenta
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "ONE-PERSON LOCAL WORKSPACE // NO CONNECTED ACCOUNTS // NO PAYMENTS"
                font.pixelSize: 9
                textFormat: Text.PlainText
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            FinanceBankingAccountsPane {
                width: parent.width
                visible: banking.selectedTool==="accounts"
                height: visible ? implicitHeight : 0
                active: banking.active && banking.selectedTool==="accounts"
                onReturnToTopRequested: bankingScroll.flickable.contentY=0
            }
            FinanceTransferGuidePane {
                width: parent.width
                visible: banking.selectedTool==="transfers"
            }
            // Import is deliberately opt-in. Do not ingest Actual transactions
            // or credentials, and never save statement contents to a log or disk.
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                text: "SELECT A LOCAL CSV FILE OR PASTE CSV TEXT EXPORTED BY YOUR BANKING APP. EXPECTED COLUMNS: DATE, DESCRIPTION, AMOUNT. NEGATIVE = MONEY OUT. ACCEPTS MM/DD/YYYY OR YYYY-MM-DD."
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                text: "SOURCE LABEL ONLY // YOUR OWN RECORDS // IN MEMORY UNTIL CLEAR OR APP RESTART"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: visible ? 30 : 0
                visible: banking.selectedTool==="import"
                label: "MANUAL SOURCE // "+banking.sources[banking.importSourceIndex].name.toUpperCase()
                labelPixelSize: 9
                accentColor: Colors.magenta
                onLeftClicked: banking.importSourceIndex=
                    (banking.importSourceIndex+1)%banking.sources.length
            }
            ActionButton {
                width: parent.width
                height: visible ? 29 : 0
                visible: banking.selectedTool==="import"
                label: banking.fileState==="pending"
                       ? "READING SELECTED CSV" : "SELECT LOCAL CSV FILE"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: banking.fileState!=="pending" && !fileReader.running
                onLeftClicked: {
                    banking.pickerSource=banking.sourceId();
                    statementPicker.open();
                }
            }
            Rectangle {
                id: pasteFrame
                width: parent.width
                height: visible ? 130 : 0
                visible: banking.selectedTool==="import"
                color: Colors.black
                border.color: Colors.cyan
                clip: true
                Flickable {
                    id: textScroll
                    anchors.fill: parent
                    anchors.margins: 5
                    clip: true
                    contentWidth: width
                    contentHeight: Math.max(height,csvInput.paintedHeight+8)
                    boundsBehavior: Flickable.StopAtBounds
                    TextEdit {
                        id: csvInput
                        width: textScroll.width
                        height: Math.max(textScroll.height,paintedHeight+8)
                        text: ""
                        textFormat: TextEdit.PlainText
                        wrapMode: TextEdit.Wrap
                        font.pixelSize: 10
                        color: Colors.white
                        selectByMouse: true
                        activeFocusOnPress: true
                        onTextChanged: {
                            banking.editorEpoch+=1;
                            banking.pending=null;
                            banking.clearArmed=false;
                            if(banking.fileState==="pending")
                                banking.fileState="cancelled";
                        }
                    }
                }
            }
            ActionButton {
                width: parent.width
                height: visible ? 29 : 0
                visible: banking.selectedTool==="import"
                label: "PREVIEW PASTED CSV"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onLeftClicked: banking.previewCsv()
            }
            ActionButton {
                width: parent.width
                height: visible ? 29 : 0
                visible: banking.selectedTool==="import"
                label: "IMPORT VERIFIED ROWS TO SESSION"
                labelPixelSize: 9
                accentColor: Colors.omnitrix
                available: !!banking.pending&&banking.pending.ok
                           && banking.fileState!=="pending"
                onLeftClicked: banking.commitCsv()
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"&&!!banking.notice
                text: banking.notice
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                text: "SESSION ROWS "+banking.ledger.length
                      +" // DEBITS TO REVIEW "+BankingPolicy.money(banking.summary.debitsCents)
                      +" // CREDITS "+BankingPolicy.money(banking.summary.creditsCents)
                font.pixelSize: 10
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                text: "SPENDING-LIKE DEBITS "+BankingPolicy.money(
                      banking.summary.spendingLikeDebitsCents)
                      +" // CONFIRMED OWN TRANSFERS "+BankingPolicy.money(
                      banking.summary.confirmedTransferOutCents)
                font.pixelSize: 10
                color: Colors.omnitrix
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                text: "DEBITS MAY INCLUDE TRANSFERS, FEES, REFUNDS OR PAYMENTS. CREDITS ARE NOT PROVEN INCOME. TRANSFER SUGGESTIONS ARE NOT AUTOMATICALLY EXCLUDED."
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                         &&banking.candidates.length>0
                text: "POSSIBLE MATCHED TRANSFERS // REVIEW AND CONFIRM EACH PAIR"
                font.pixelSize: 9
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: banking.selectedTool==="import"?banking.candidates:[]
                delegate: Column {
                    required property var modelData
                    width: scrollBody.width
                    spacing: 3
                    GohuText {
                        width: parent.width
                        text: modelData.fromSource+" → "+modelData.toSource
                              +" // "+BankingPolicy.money(modelData.amountCents)
                              +" // "+modelData.date
                        font.pixelSize: 9
                        color: Colors.white
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: parent.width
                        height: 27
                        label: banking.armedPairKey===
                               modelData.fromId+"|"+modelData.toId
                               ? "CONFIRM EXCLUDE AS OWN TRANSFER" : "REVIEW PAIR AS OWN TRANSFER"
                        labelPixelSize: 9
                        accentColor: Colors.orange
                        onLeftClicked: banking.confirmCandidate(modelData)
                    }
                }
            }
            ActionButton {
                width: parent.width
                height: visible ? 28 : 0
                visible: banking.selectedTool==="import"
                         &&banking.confirmed.length>0
                label: "UNDO LAST TRANSFER CLASSIFICATION"
                labelPixelSize: 9
                accentColor: Colors.orange
                onLeftClicked: banking.undoLast()
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"&&banking.ledger.length>0
                text: "LATEST IMPORTED ROWS // REVIEW ONLY // 30 SHOWN"
                font.pixelSize: 9
                color: Colors.cyan
            }
            Repeater {
                model: banking.selectedTool==="import"
                       ? banking.ledger.slice(Math.max(0,banking.ledger.length-30))
                       : []
                delegate: GohuText {
                    required property var modelData
                    width: scrollBody.width
                    text: modelData.date+" // "+modelData.sourceName+" // "
                          +BankingPolicy.money(modelData.amountCents)
                          +" // "+modelData.description
                    font.pixelSize: 9
                    color: modelData.amountCents<0?Colors.orange:Colors.omnitrix
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
            }
            ActionButton {
                width: parent.width
                height: visible ? 28 : 0
                visible: banking.selectedTool==="import"
                label: banking.clearArmed?"CONFIRM CLEAR UNSAVED SESSION":"CLEAR MANUAL SESSION"
                labelPixelSize: 9
                accentColor: banking.clearArmed?Colors.red:Colors.orange
                onLeftClicked: banking.clearSession()
            }
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                text: "SELECTED FILES ARE READ ONLY AND NEVER SAVED BY BANKING. NO ACTUAL/BANK WRITES, ACCOUNT SYNC, PAYMENT EXECUTION OR PERSONAL PROFILE IS ACTIVE."
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
        }
    }
}
