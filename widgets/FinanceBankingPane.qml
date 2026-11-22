import QtQuick
import "../components"
import "FinanceBankingImportPolicy.js" as BankingPolicy

// Banking M1: single Linux user's ephemeral manual CSV review.
// No bank connection, bank balance, Actual mutation, storage, network or transfer writer.
Item {
    id: banking
    property bool active: false
    property string selectedTool: "transfers"
    property int importSourceIndex: 0
    property var ledger: []
    property var pending: null
    property var confirmed: []
    property int nextRowId: 1
    property bool clearArmed: false
    property string armedPairKey: ""
    property string notice: ""
    readonly property var sources: BankingPolicy.accounts()
    readonly property var summary: BankingPolicy.review(ledger,confirmed)
    readonly property var candidates: summary.ok ? summary.candidates : []

    function sourceId() {
        return sources[importSourceIndex].id;
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
        notice="SESSION CLEARED // NO FILES WERE MODIFIED";
    }
    onImportSourceIndexChanged: {
        pending=null;
        armedPairKey="";
    }
    onSelectedToolChanged: {
        armedPairKey="";
        clearArmed=false;
    }

    Row {
        id: toolTabs
        anchors.top: parent.top
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 6
        ActionButton {
            width: (toolTabs.width-6)/2
            height: 31
            label: "TRANSFERS"
            labelPixelSize: 10
            accentColor: Colors.cyan
            selected: banking.selectedTool==="transfers"
            onLeftClicked: banking.selectedTool="transfers"
        }
        ActionButton {
            width: (toolTabs.width-6)/2
            height: 31
            label: "IMPORT / REVIEW"
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
                text: banking.selectedTool==="transfers"
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
            FinanceTransferGuidePane {
                width: parent.width
                visible: banking.selectedTool==="transfers"
            }
            // Import is deliberately opt-in. Do not ingest Actual transactions
            // or credentials, and never save statement contents to a log or disk.
            GohuText {
                width: parent.width
                visible: banking.selectedTool==="import"
                text: "PASTE CSV TEXT EXPORTED BY YOUR BANKING APP. EXPECTED COLUMNS: DATE, DESCRIPTION, AMOUNT. NEGATIVE = MONEY OUT. ACCEPTS MM/DD/YYYY OR YYYY-MM-DD."
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
                            banking.pending=null;
                            banking.clearArmed=false;
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
                text: "NO RECORDS ARE WRITTEN TO ACTUAL OR BANKS. NO FILE ACCESS, ACCOUNT SYNC, PAYMENT EXECUTION OR PERSONAL PROFILE IS ACTIVE."
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
        }
    }
}
