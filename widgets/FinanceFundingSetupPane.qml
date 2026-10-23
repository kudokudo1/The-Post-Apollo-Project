import QtQuick
import "../components"
import "../services/finance/FinanceFundingSetupPlan.js" as FundingRules

// D17 guided plan. No Process, Actual mutation, persistence or save buttons.
Item {
    id: setup
    property var snapshot: null
    property bool expanded: false
    property string anchoredSource: ""
    property string anchoredMonth: ""
    property string setupMode: ""
    property string accountId: ""
    property string categoryId: ""
    property string dateText: ""
    property string amountText: ""
    property string descriptionText: ""
    property string writeState: "idle"
    property string writeMessage: ""
    property bool approvalArmed: false
    property bool submitted: false
    property string requestId: ""
    signal saveRequested(var payload)
    readonly property bool writePending: writeState === "pending"
    readonly property bool writeUncertain: writeState === "uncertain"
    readonly property bool incomeProposalEligible: !!proposal && proposal.ok
        && proposal.mode === "income" && proposal.writeAllowed === false
        && !!snapshot && snapshot.sourceKey === anchoredSource
        && snapshot.month === anchoredMonth
        && proposal.sourceKey === snapshot.sourceKey
        && proposal.month === snapshot.month
        && proposal.accountId === accountId
        && proposal.categoryId === categoryId
        && proposal.date === dateText
        && FundingRules.parseFundingAmountCents(amountText) === proposal.amountCents
        && descriptionText.trim().length > 0
        && descriptionText.trim().length <= 120
    property var proposal: null
    property string errorText: ""
    readonly property var selectedAccount: {
        const a=snapshot && Array.isArray(snapshot.accounts)
            ? snapshot.accounts.filter(function(x){return x && x.id===accountId;}) : [];
        return a.length===1 ? a[0] : null;
    }
    readonly property var categoryOptions:
        snapshot && snapshot.incomeReview
            && snapshot.incomeReview.categoriesOverflow!==true
            && Array.isArray(snapshot.incomeReview.incomeCategories)
        ? snapshot.incomeReview.incomeCategories : []

    width: parent ? parent.width : 0
    height: expanded ? setupBody.implicitHeight+14 : 0
    visible: expanded

    function clear() {
        if(writePending || writeUncertain)return false;
        expanded=false;
        anchoredSource="";
        anchoredMonth="";
        setupMode="";
        accountId="";
        categoryId="";
        dateText="";
        amountText="";
        descriptionText="";
        proposal=null;
        errorText="";
        approvalArmed=false;
        submitted=false;
        requestId="";
        return true;
    }
    function newRequestId() {
        let result="";
        for(let i=0;i<32;i++)
            result+=Math.floor(Math.random()*16).toString(16);
        return result;
    }
    function begin() {
        if(writePending || writeUncertain || !snapshot || snapshot.readOnly!==true
                || snapshot.source!=="actual-budget"
                || !/^[a-f0-9]{64}$/.test(snapshot.sourceKey||""))
            return false;
        clear();
        anchoredSource=snapshot.sourceKey;
        anchoredMonth=snapshot.month;
        expanded=true;
        return true;
    }
    function chooseMode(nextMode) {
        if(writePending || writeUncertain || !expanded
                || (nextMode!=="opening" && nextMode!=="income"))
            return false;
        setupMode=nextMode;
        accountId="";
        categoryId="";
        dateText="";
        amountText="";
        descriptionText="";
        proposal=null;
        approvalArmed=false;
        submitted=false;
        requestId="";
        errorText="";
        return true;
    }
    function invalidatePreview() {
        proposal=null;
        approvalArmed=false;
        requestId="";
        // Submitted requests cannot be undone by changing local fields.
    }
    function calculate() {
        if(writePending || writeUncertain || submitted)return false;
        invalidatePreview();
        if(!expanded || !snapshot
                || snapshot.sourceKey!==anchoredSource
                || snapshot.month!==anchoredMonth){
            errorText="SOURCE CHANGED // OPEN GUIDED SETUP AGAIN";
            return false;
        }
        const next=FundingRules.previewFundingSetup(snapshot,setupMode,
            accountId,dateText,amountText,categoryId);
        if(!next.ok){
            errorText=next.reason;
            return false;
        }
        errorText="";
        proposal=next;
        if(next.mode==="income")requestId=newRequestId();
        return true;
    }
    function requestSave() {
        if(!expanded || !incomeProposalEligible || !approvalArmed
                || submitted || writePending || writeUncertain || !requestId)
            return false;
        submitted=true;
        approvalArmed=false;
        saveRequested({
            mode:"income",requestId:requestId,
            sourceKey:proposal.sourceKey,accountId:proposal.accountId,
            month:proposal.month,date:proposal.date,
            amountCents:proposal.amountCents,categoryId:proposal.categoryId,
            description:descriptionText.trim()
        });
        return true;
    }
    onSnapshotChanged: {
        if(!expanded)return;
        if(!snapshot || snapshot.sourceKey!==anchoredSource
                || snapshot.month!==anchoredMonth) {
            if(!writePending && !writeUncertain)clear();
            else invalidatePreview();
        } else {
            invalidatePreview();
            errorText="SOURCE REFRESHED // PREVIEW AGAIN BEFORE CONTINUING";
        }
    }
    onAccountIdChanged: invalidatePreview()
    onCategoryIdChanged: invalidatePreview()
    onDateTextChanged: invalidatePreview()
    onAmountTextChanged: invalidatePreview()
    onDescriptionTextChanged: invalidatePreview()
    onWriteStateChanged: {
        if(writeState==="uncertain" || writeState==="committed")
            approvalArmed=false;
    }

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
    }
    Column {
        id: setupBody
        x: 7
        y: 7
        width: Math.max(0,setup.width-14)
        spacing: 7
        GohuText {
            width: parent.width
            text: "GUIDED FUNDING // PREVIEW ONLY"
            font.pixelSize: 11
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "CHOOSE // WHAT ARE YOU RECORDING?"
            font.pixelSize: 9
            color: Colors.white
            textFormat: Text.PlainText
        }
        Row {
            width: parent.width
            spacing: 5
            ActionButton {
                width: (parent.width-5)/2
                height: 29
                label: "OPENING BALANCE"
                labelPixelSize: 9
                accentColor: setup.setupMode==="opening" ? Colors.magenta : Colors.cyan
                trackLabelGlowLocally: true
                onLeftClicked: setup.chooseMode("opening")
            }
            ActionButton {
                width: (parent.width-5)/2
                height: 29
                label: "INCOME"
                labelPixelSize: 9
                accentColor: setup.setupMode==="income" ? Colors.magenta : Colors.cyan
                trackLabelGlowLocally: true
                onLeftClicked: setup.chooseMode("income")
            }
        }
        GohuText {
            width: parent.width
            visible: !!setup.setupMode
            text: setup.setupMode==="opening"
                ? "EXISTING ACCOUNTS // REVIEW HISTORY BEFORE ENTERING STARTING MONEY"
                : "INCOME // A POSITIVE DEPOSIT MAY NEED ACTUAL INCOME CATEGORIZATION"
            font.pixelSize: 9
            textFormat: Text.PlainText
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: !!setup.setupMode
            text: "ACCOUNT // SELECT"
            font.pixelSize: 9
            color: Colors.cyan
        }
        Repeater {
            model: setup.setupMode && setup.snapshot
                && Array.isArray(setup.snapshot.accounts)
                && setup.snapshot.accounts.length<=12
                ? setup.snapshot.accounts : []
            delegate: ActionButton {
                required property var modelData
                width: setupBody.width
                height: 26
                label: modelData.name
                labelPixelSize: 9
                accentColor: setup.accountId===modelData.id ? Colors.magenta : Colors.cyan
                trackLabelGlowLocally: true
                onLeftClicked: {
                    setup.accountId=modelData.id;
                    setup.categoryId="";
                    setup.errorText="";
                }
            }
        }
        GohuText {
            width: parent.width
            visible: !!setup.setupMode && !!setup.snapshot
                && setup.snapshot.accounts.length>12
            text: "MORE THAN 12 ACCOUNTS // REVIEW IN ACTUAL"
            textFormat: Text.PlainText
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: !!setup.selectedAccount
            text: setup.selectedAccount
                  ? "RECORDED ACCOUNT BALANCE // "
                    + root.moneyText(setup.selectedAccount.balanceCents)
                  : ""
            font.pixelSize: 9
            color: Colors.white
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: !!setup.setupMode
            text: setup.setupMode==="opening"
                ? "REFERENCE DATE // MONTH / DAY / YEAR" : "INCOME DATE // MONTH / DAY / YEAR"
            font.pixelSize: 9
            color: Colors.cyan
        }
        FinanceDateInput {
            width: parent.width
            visible: !!setup.setupMode
            value: setup.dateText
            fallbackDate: setup.anchoredMonth
                          ? setup.anchoredMonth + "-01" : ""
            onValueEdited: function(value) {setup.dateText=value;}
        }
        GohuText {
            width: parent.width
            visible: !!setup.setupMode
            text: "REFERENCE AMOUNT // USD (POSITIVE)"
            font.pixelSize: 9
            color: Colors.cyan
        }
        FinanceMoneyInput {
            width: parent.width
            visible: !!setup.setupMode
            value: setup.amountText
            onValueEdited: function(value) {setup.amountText=value;}
        }
        GohuText {
            width: parent.width
            visible: setup.setupMode==="income"
            text: "INCOME CATEGORY // SELECT EXISTING"
            font.pixelSize: 9
            color: Colors.cyan
        }
        Repeater {
            model: setup.setupMode==="income" ? setup.categoryOptions : []
            delegate: ActionButton {
                required property var modelData
                width: setupBody.width
                height: 26
                label: modelData.name
                labelPixelSize: 9
                accentColor: setup.categoryId===modelData.id ? Colors.magenta : Colors.cyan
                trackLabelGlowLocally: true
                onLeftClicked: {
                    setup.categoryId=modelData.id;
                    setup.errorText="";
                }
            }
        }
        GohuText {
            width: parent.width
            visible: setup.setupMode==="income"
            text: "DESCRIPTION / PAYEE // REQUIRED FOR NEW INCOME"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 29
            visible: setup.setupMode==="income"
            color: Colors.dark
            border.color: Colors.cyan
            TextInput {
                anchors.fill: parent
                anchors.margins: 6
                text: setup.descriptionText
                readOnly: setup.writePending || setup.writeUncertain || setup.submitted
                color: Colors.white
                font.pixelSize: 11
                selectByMouse: true
                onTextEdited: setup.descriptionText=text
            }
        }
        GohuText {
            width: parent.width
            visible: setup.setupMode==="income" && setup.categoryOptions.length===0
            text: "NO COMPLETE INCOME CATEGORY LIST // REVIEW IN ACTUAL"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 29
            label: "PREVIEW SETUP"
            labelPixelSize: 10
            accentColor: Colors.cyan
            trackLabelGlowLocally: true
            available: !!setup.setupMode && !!setup.selectedAccount
                       && !setup.writePending && !setup.writeUncertain && !setup.submitted
            onLeftClicked: setup.calculate()
        }
        GohuText {
            width: parent.width
            visible: !!setup.errorText
            text: setup.errorText
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Column {
            width: parent.width
            spacing: 5
            visible: !!setup.proposal && setup.proposal.ok
            GohuText {
                width: parent.width
                text: setup.proposal
                    ? "PLAN // "+setup.proposal.accountName+" / "+setup.proposal.date
                      +" / "+root.moneyText(setup.proposal.amountCents) : ""
                font.pixelSize: 9
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: setup.proposal && setup.proposal.mode==="income"
                    ? "PROPOSED CATEGORY // "+setup.proposal.categoryName
                    : "OPENING BALANCE // EXTERNAL RECORD REQUIRED"
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "TO BUDGET AFTER // UNKNOWN UNTIL ACTUAL RECONCILES"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
        ActionButton {
            width: parent.width
            height: 29
            visible: setup.setupMode==="income"
            label: setup.submitted ? "REQUEST SUBMITTED"
                : setup.approvalArmed ? "CONFIRM SAVE" : "ARM SAVE"
            labelPixelSize: 10
            accentColor: setup.approvalArmed ? Colors.magenta : Colors.orange
            trackLabelGlowLocally: true
            available: setup.incomeProposalEligible && !setup.submitted
                       && !setup.writePending && !setup.writeUncertain
            onLeftClicked: {
                if(setup.approvalArmed)
                    setup.requestSave();
                else
                    setup.approvalArmed=true;
            }
        }
        GohuText {
            width: parent.width
            visible: setup.setupMode==="income"
            text: setup.writeMessage
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: setup.setupMode==="opening"
                ? "OPENING BALANCE // NO SAVE / NO WRITES // EXISTING ACCOUNT REQUIRES RECONCILIATION"
                : setup.approvalArmed
                ? "NEXT STEP MAY CHANGE ACTUAL IF SEPARATELY AUTHORIZED"
                : "FUNDING PREVIEW SAFE // SAVE REQUIRES SEPARATE OPERATOR PERMISSION"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 28
            label: "CLOSE SETUP"
            labelPixelSize: 9
            accentColor: Colors.orange
            trackLabelGlowLocally: true
            available: !setup.writePending && !setup.writeUncertain
            onLeftClicked: setup.clear()
        }
    }
}
