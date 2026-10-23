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
        expanded=false;
        anchoredSource="";
        anchoredMonth="";
        setupMode="";
        accountId="";
        categoryId="";
        dateText="";
        amountText="";
        proposal=null;
        errorText="";
    }
    function begin() {
        if(!snapshot || snapshot.readOnly!==true
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
        if(!expanded || (nextMode!=="opening" && nextMode!=="income"))
            return false;
        setupMode=nextMode;
        accountId="";
        categoryId="";
        dateText="";
        amountText="";
        proposal=null;
        errorText="";
        return true;
    }
    function calculate() {
        proposal=null;
        if(!expanded || !snapshot
                || snapshot.sourceKey!==anchoredSource
                || snapshot.month!==anchoredMonth) {
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
        return true;
    }
    onSnapshotChanged: {
        if(!expanded)return;
        if(!snapshot || snapshot.sourceKey!==anchoredSource
                || snapshot.month!==anchoredMonth){
            clear();
        }else{
            proposal=null;
            errorText="SOURCE REFRESHED // PREVIEW AGAIN BEFORE CONTINUING";
        }
    }
    onAccountIdChanged: proposal=null
    onCategoryIdChanged: proposal=null
    onDateTextChanged: proposal=null
    onAmountTextChanged: proposal=null

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
        GohuText {
            width: parent.width
            text: "NO SAVE / NO WRITES // CHECK EXISTING RECORDS IN ACTUAL"
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
            onLeftClicked: setup.clear()
        }
    }
}
