import QtQuick
import "../components"
import "../services/finance/FinanceFundingSetupPlan.js" as FundingRules
import "../services/finance/FinanceSpreadsheetPolicy.js" as StepRules

// Fast entry surface. Back-end permit/recovery checks are unchanged.
// Existing-account opening balance is intentionally never writable here.
Item {
    id: quick
    property var snapshot: null
    property bool open: false
    property string kind: "income"
    property string accountId: ""
    property string categoryId: ""
    property string dateText: ""
    property string amountText: "1.00"
    property string descriptionText: ""
    property string writeState: "idle"
    property string writeMessage: ""
    property bool submitted: false
    signal saveRequested(var payload)
    readonly property bool busy: writeState==="pending" || writeState==="uncertain"
    readonly property var proposal: kind==="income"
        ? FundingRules.previewFundingSetup(snapshot,"income",accountId,
            dateText,amountText,categoryId) : null
    readonly property bool canSubmit: !!proposal && proposal.ok
        && proposal.mode==="income" && proposal.writeAllowed===false
        && snapshot && snapshot.readOnly===true
        && proposal.sourceKey===snapshot.sourceKey && proposal.month===snapshot.month
        && !!descriptionText.trim() && descriptionText.trim().length<=120
        && !busy && !submitted
    readonly property var accounts: snapshot && Array.isArray(snapshot.accounts)
        ? snapshot.accounts : []
    readonly property var incomeCategories: snapshot && snapshot.incomeReview
        && snapshot.incomeReview.categoriesOverflow!==true
        && Array.isArray(snapshot.incomeReview.incomeCategories)
        ? snapshot.incomeReview.incomeCategories : []
    width: parent ? parent.width : 0
    height: open ? formBody.implicitHeight+12 : 0
    visible: open

    function clear(){
        if(busy)return false;
        open=false;
        submitted=false;
        accountId="";
        categoryId="";
        dateText="";
        amountText="1.00";
        descriptionText="";
        kind="income";
        return true;
    }
    function begin(){
        if(busy || !snapshot || snapshot.readOnly!==true
                || snapshot.source!=="actual-budget")return false;
        clear();
        const today=Qt.formatDate(new Date(),"yyyy-MM-dd");
        dateText=today.startsWith(snapshot.month+"-") ? today : snapshot.month+"-01";
        accountId=accounts.length===1 ? accounts[0].id : "";
        categoryId=incomeCategories.length===1 ? incomeCategories[0].id : "";
        open=true;
        return true;
    }
    function step(delta) {
        if(busy || submitted)return;
        const next=StepRules.stepAmount(amountText,delta,false);
        if(next!==null)amountText=next;
    }
    function submit(){
        if(!canSubmit)return false;
        let id="";
        for(let i=0;i<32;i++)id+=Math.floor(Math.random()*16).toString(16);
        submitted=true;
        saveRequested({
            mode:"income",requestId:id,sourceKey:proposal.sourceKey,
            accountId:proposal.accountId,month:proposal.month,
            date:proposal.date,amountCents:proposal.amountCents,
            categoryId:proposal.categoryId,description:descriptionText.trim()
        });
        return true;
    }
    onSnapshotChanged: {
        if(!busy && open)clear();
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.color: Colors.cyan
        border.width: 1
    }
    Column {
        id: formBody
        x: 6
        y: 6
        width: Math.max(0,quick.width-12)
        spacing: 5
        Row {
            width: parent.width
            spacing: 4
            GohuText {
                width: parent.width-65
                text: "ADD MONEY"
                font.pixelSize: 11
                color: Colors.cyan
            }
            ActionButton {
                width: 61
                height: 22
                label: "× CLOSE"
                labelPixelSize: 9
                accentColor: Colors.orange
                available: !quick.busy
                onLeftClicked: quick.clear()
            }
        }
        Row {
            width: parent.width
            spacing: 4
            ActionButton {
                width: (parent.width-4)/2
                height: 25
                label: "INCOME"
                labelPixelSize: 9
                accentColor: quick.kind==="income" ? Colors.magenta : Colors.cyan
                onLeftClicked: quick.kind="income"
            }
            ActionButton {
                width: (parent.width-4)/2
                height: 25
                label: "START BALANCE"
                labelPixelSize: 9
                accentColor: quick.kind==="opening" ? Colors.magenta : Colors.cyan
                onLeftClicked: quick.kind="opening"
            }
        }
        GohuText {
            width: parent.width
            visible: quick.kind==="opening"
            text: "EXISTING BALANCES NEED RECONCILIATION. SEE ADVANCED."
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        Column {
            width: parent.width
            spacing: 5
            visible: quick.kind==="income"
            GohuText {
                text: "ACCOUNT"
                font.pixelSize: 9
                color: Colors.cyan
            }
            Repeater {
                model: quick.accounts.length<=12 ? quick.accounts : []
                delegate: ActionButton {
                    required property var modelData
                    width: formBody.width
                    height: 24
                    label: modelData.name
                    labelPixelSize: 9
                    accentColor: quick.accountId===modelData.id ? Colors.magenta : Colors.cyan
                    available: !quick.busy && !quick.submitted
                    onLeftClicked: quick.accountId=modelData.id
                }
            }
            GohuText {
                width: parent.width
                visible: quick.accounts.length>12
                text: "ACCOUNT LIST TOO LONG // USE ADVANCED"
                font.pixelSize: 9
                color: Colors.orange
            }
            GohuText {
                text: "DATE"
                font.pixelSize: 9
                color: Colors.cyan
            }
            FinanceDateInput {
                width: parent.width
                value: quick.dateText
                fallbackDate: quick.snapshot ? quick.snapshot.month+"-01" : ""
                canEdit: !quick.busy && !quick.submitted
                onValueEdited: function(value) {quick.dateText=value;}
            }
            GohuText {
                text: "AMOUNT"
                font.pixelSize: 9
                color: Colors.cyan
            }
            Row {
                width: parent.width
                spacing: 4
                ActionButton {
                    width: 29
                    height: 28
                    label: "−"
                    labelPixelSize: 15
                    accentColor: Colors.cyan
                    available: !quick.busy && !quick.submitted
                    onLeftClicked: quick.step(-100)
                }
                FinanceMoneyInput {
                    width: Math.max(36,parent.width-66)
                    height: 28
                    value: quick.amountText
                    canEdit: !quick.busy && !quick.submitted
                    onValueEdited: function(value) {quick.amountText=value;}
                }
                ActionButton {
                    width: 29
                    height: 28
                    label: "+"
                    labelPixelSize: 15
                    accentColor: Colors.cyan
                    available: !quick.busy && !quick.submitted
                    onLeftClicked: quick.step(100)
                }
            }
            GohuText {
                text: "INCOME CATEGORY"
                font.pixelSize: 9
                color: Colors.cyan
            }
            Repeater {
                model: quick.incomeCategories
                delegate: ActionButton {
                    required property var modelData
                    width: formBody.width
                    height: 24
                    label: modelData.name
                    labelPixelSize: 9
                    accentColor: quick.categoryId===modelData.id
                        ? Colors.magenta : Colors.cyan
                    available: !quick.busy && !quick.submitted
                    onLeftClicked: quick.categoryId=modelData.id
                }
            }
            GohuText {
                width: parent.width
                visible: quick.incomeCategories.length===0
                text: "NO INCOME CATEGORY AVAILABLE"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.orange
            }
            GohuText {
                text: "DESCRIPTION"
                font.pixelSize: 9
                color: Colors.cyan
            }
            Rectangle {
                width: parent.width
                height: 28
                color: Colors.dark
                border.color: Colors.cyan
                TextInput {
                    anchors.fill: parent
                    anchors.margins: 5
                    text: quick.descriptionText
                    readOnly: quick.busy || quick.submitted
                    color: Colors.white
                    font.pixelSize: 11
                    selectByMouse: true
                    onTextEdited: quick.descriptionText=text
                }
            }
            ActionButton {
                width: parent.width
                height: 30
                label: quick.submitted ? "REQUEST SENT"
                    : quick.canSubmit ? "ADD "+(quick.proposal.amountCents/100).toFixed(2)
                    : "ADD MONEY"
                labelPixelSize: 11
                accentColor: Colors.orange
                trackLabelGlowLocally: true
                available: quick.canSubmit
                onLeftClicked: quick.submit()
            }
            GohuText {
                width: parent.width
                visible: quick.writeState==="blocked" || quick.busy
                text: quick.writeState==="blocked" && quick.writeMessage.indexOf("WRITES LOCKED")>=0
                    ? "SAVING LOCKED"
                    : quick.writeState==="pending" ? "SAVING..."
                    : "CHECK ACTUAL BEFORE TRYING AGAIN"
                textFormat: Text.PlainText
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
        }
    }
}
