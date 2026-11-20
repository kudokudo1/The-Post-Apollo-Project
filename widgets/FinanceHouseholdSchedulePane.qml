import QtQuick
import "../components"
import "../services/finance" as FinanceServices

// FP1e: local schedule entry surface. Reuses already-entered monthly costs
// and goal references, never imports or copies banking account records.
Item {
    id: schedules
    property string contextId: "mine"
    property bool active: false
    property var expenses: []
    property var goals: []
    property string editorKind: "bill"
    property string selectedExpenseId: ""
    property int dueDay: 15
    property string purchaseTitle: ""
    property string purchaseDate: Qt.formatDate(new Date(),"yyyy-MM-dd")
    property string purchaseAmountText: "100.00"
    property string fundingGoalId: ""
    property string armedDeleteId: ""
    readonly property var scheduleRows: scheduleStore.rows
    readonly property bool ready: scheduleStore.state==="ready"
    readonly property string statusMessage: scheduleStore.message
    width: parent ? parent.width : 0
    implicitHeight: editor.implicitHeight
    height: visible ? implicitHeight : 0

    FinanceServices.FinanceHouseholdScheduleStore {
        id: scheduleStore
        contextId: schedules.contextId
        monitoring: schedules.active
        onScheduleSaved: schedules.clearEditor()
        onScheduleDeleted: schedules.armedDeleteId=""
    }

    function clearEditor() {
        selectedExpenseId="";
        dueDay=15;
        purchaseTitle="";
        purchaseDate=Qt.formatDate(new Date(),"yyyy-MM-dd");
        purchaseAmountText="100.00";
        fundingGoalId="";
        armedDeleteId="";
    }
    onContextIdChanged: clearEditor()
    function setKind(kind) {
        if(kind!=="bill"&&kind!=="purchase")return;
        editorKind=kind;
        clearEditor();
    }
    function billLabel(id) {
        for(let i=0;i<expenses.length;i++)
            if(expenses[i].id===id)return expenses[i].title;
        return "MISSING MONTHLY COST // REPAIR SCHEDULE";
    }
    function goalLabel(id) {
        if(!id)return "NEW CASH (NOT RESERVED GOAL FUNDS)";
        for(let i=0;i<goals.length;i++)
            if(goals[i].id===id)return "SAVED GOAL // "+goals[i].title;
        return "MISSING GOAL // REPAIR SCHEDULE";
    }
    function money(cents) {
        return Number.isSafeInteger(cents)?"$"+(cents/100).toFixed(2):"INVALID";
    }
    function save() {
        if(!ready || !active)return false;
        armedDeleteId="";
        if(editorKind==="bill") {
            if(!expenses.some(function(e){return e.id===selectedExpenseId;}))
                return false;
            return scheduleStore.addBill(selectedExpenseId,dueDay);
        }
        if(!purchaseTitle.trim() || (fundingGoalId
                && !goals.some(function(g){return g.id===fundingGoalId;})))
            return false;
        return scheduleStore.addPurchase(purchaseTitle,purchaseDate,
            purchaseAmountText,fundingGoalId);
    }
    function requestDelete(id) {
        if(!ready)return false;
        if(armedDeleteId!==id) {
            armedDeleteId=id;
            return false;
        }
        armedDeleteId="";
        return scheduleStore.remove(id);
    }

    Column {
        id: editor
        width: parent.width
        spacing: 9
        GohuText {
            width: parent.width
            text: "SCHEDULED BILLS + ONE-TIME PURCHASES"
            font.pixelSize: 11
            color: Colors.magenta
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "BILL DUE DAYS REUSE MONTHLY COSTS. PURCHASES USE EXPLICIT NEW CASH OR SAVINGS-GOAL FUNDING."
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Row {
            width: parent.width
            spacing: 5
            ActionButton {
                width: (parent.width-5)/2
                height: 29
                label: "BILL DUE DAY"
                labelPixelSize: 9
                accentColor: Colors.cyan
                selected: schedules.editorKind==="bill"
                onLeftClicked: schedules.setKind("bill")
            }
            ActionButton {
                width: (parent.width-5)/2
                height: 29
                label: "ONE-TIME PURCHASE"
                labelPixelSize: 9
                accentColor: Colors.omnitrix
                selected: schedules.editorKind==="purchase"
                onLeftClicked: schedules.setKind("purchase")
            }
        }
        GohuText {
            width: parent.width
            text: schedules.statusMessage
            font.pixelSize: 9
            color: scheduleStore.state==="failed"?Colors.red:Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: parent.width
            height: 27
            label: "REFRESH LOCAL SCHEDULE"
            labelPixelSize: 9
            accentColor: Colors.cyan
            available: scheduleStore.state!=="pending"
                && scheduleStore.state!=="loading"
            onLeftClicked: scheduleStore.refresh()
        }
        GohuText {
            width: parent.width
            visible: schedules.editorKind==="bill"
            text: "SELECT EXISTING MONTHLY COST (AMOUNT NOT DUPLICATED)"
            font.pixelSize: 9
            color: Colors.white
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Flow {
            id: expenseRail
            visible: schedules.editorKind==="bill"
            width: parent.width
            spacing: 5
            Repeater {
                model: schedules.expenses
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(110,(expenseRail.width-5)/2)
                    height: 29
                    label: modelData.title
                    labelPixelSize: 9
                    selected: schedules.selectedExpenseId===modelData.id
                    accentColor: Colors.cyan
                    onLeftClicked: schedules.selectedExpenseId=modelData.id
                }
            }
        }
        Row {
            width: parent.width
            visible: schedules.editorKind==="bill"
            height: visible?31:0
            spacing: 6
            GohuText {
                width: Math.max(85,parent.width-132)
                height: 29
                text: "MONTHLY DUE DAY"
                font.pixelSize: 9
                color: Colors.cyan
                verticalAlignment: Text.AlignVCenter
            }
            ActionButton {
                width: 29
                height: 29
                label: "-"
                labelPixelSize: 12
                accentColor: Colors.magenta
                available: schedules.dueDay>1
                onLeftClicked: schedules.dueDay=Math.max(1,schedules.dueDay-1)
            }
            GohuText {
                width: 51
                height: 29
                text: String(schedules.dueDay)
                font.pixelSize: 12
                color: Colors.white
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            ActionButton {
                width: 29
                height: 29
                label: "+"
                labelPixelSize: 12
                accentColor: Colors.magenta
                available: schedules.dueDay<31
                onLeftClicked: schedules.dueDay=Math.min(31,schedules.dueDay+1)
            }
        }
        GohuText {
            width: parent.width
            visible: schedules.editorKind==="bill"
            text: "DAYS 29-31 MOVE TO MONTH END WHEN A MONTH IS SHORTER."
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: schedules.editorKind==="purchase"
            text: "PURCHASE DESCRIPTION"
            font.pixelSize: 9
            color: Colors.cyan
        }
        Rectangle {
            visible: schedules.editorKind==="purchase"
            width: parent.width
            height: visible?30:0
            color: Colors.dark
            border.color: purchaseTitleInput.activeFocus?Colors.magenta:Colors.cyan
            TextInput {
                id: purchaseTitleInput
                anchors.fill: parent
                anchors.margins: 6
                text: schedules.purchaseTitle
                font.pixelSize: 11
                color: Colors.white
                maximumLength: 80
                clip: true
                selectByMouse: true
                verticalAlignment: TextInput.AlignVCenter
                onTextEdited: schedules.purchaseTitle=text
            }
        }
        GohuText {
            width: parent.width
            visible: schedules.editorKind==="purchase"
            text: "PAYMENT DATE YYYY-MM-DD"
            font.pixelSize: 9
            color: Colors.cyan
        }
        Rectangle {
            visible: schedules.editorKind==="purchase"
            width: parent.width
            height: visible?30:0
            color: Colors.dark
            border.color: purchaseDateInput.activeFocus?Colors.magenta:Colors.cyan
            TextInput {
                id: purchaseDateInput
                anchors.fill: parent
                anchors.margins: 6
                text: schedules.purchaseDate
                font.pixelSize: 11
                color: Colors.white
                maximumLength: 10
                selectByMouse: true
                verticalAlignment: TextInput.AlignVCenter
                onTextEdited: schedules.purchaseDate=text
            }
        }
        Row {
            visible: schedules.editorKind==="purchase"
            width: parent.width
            height: visible?30:0
            spacing: 5
            GohuText {
                width: Math.max(80,parent.width-145)
                height: parent.height
                text: "PLANNED ONE-TIME AMOUNT"
                font.pixelSize: 9
                color: Colors.cyan
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            FinanceMoneyInput {
                width: 140
                value: schedules.purchaseAmountText
                onValueEdited: function(value) {
                    schedules.purchaseAmountText=value;
                }
            }
        }
        GohuText {
            width: parent.width
            visible: schedules.editorKind==="purchase"
            text: "FUNDING SOURCE (MANUAL PLANNING ONLY)"
            font.pixelSize: 9
            color: Colors.cyan
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            visible: schedules.editorKind==="purchase"
            width: parent.width
            height: visible?29:0
            label: "NEW CASH // NOT FROM SAVINGS GOALS"
            labelPixelSize: 9
            selected: schedules.fundingGoalId===""
            accentColor: Colors.orange
            onLeftClicked: schedules.fundingGoalId=""
        }
        Flow {
            id: goalsRail
            visible: schedules.editorKind==="purchase"
            width: parent.width
            spacing: 5
            Repeater {
                model: schedules.goals
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(110,(goalsRail.width-5)/2)
                    height: 29
                    label: "GOAL: "+modelData.title
                    labelPixelSize: 9
                    selected: schedules.fundingGoalId===modelData.id
                    accentColor: Colors.omnitrix
                    onLeftClicked: schedules.fundingGoalId=modelData.id
                }
            }
        }
        ActionButton {
            width: parent.width
            height: 31
            label: schedules.editorKind==="bill"
                ? "SAVE BILL DUE DAY" : "SAVE PLANNED PURCHASE"
            labelPixelSize: 10
            accentColor: Colors.omnitrix
            available: schedules.ready
            onLeftClicked: schedules.save()
        }
        GohuText {
            width: parent.width
            text: "SCHEDULE ENTRIES // MANUAL, NOT ACTUAL PAYMENTS"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: schedules.scheduleRows
            delegate: Rectangle {
                id: scheduleRow
                required property var modelData
                width: editor.width
                height: 77
                color: Colors.black
                border.color: Colors.cyan
                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 7
                    anchors.left: parent.left
                    anchors.leftMargin: 7
                    anchors.right: removeButton.left
                    anchors.rightMargin: 5
                    text: scheduleRow.modelData.kind==="bill_due"
                        ? "BILL // "+schedules.billLabel(scheduleRow.modelData.expenseId)
                        : "PURCHASE // "+scheduleRow.modelData.title
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
                GohuText {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    anchors.left: parent.left
                    anchors.leftMargin: 7
                    anchors.right: removeButton.left
                    anchors.rightMargin: 5
                    text: scheduleRow.modelData.kind==="bill_due"
                        ? "DAY "+scheduleRow.modelData.dueDay
                          +" // "+schedules.money(schedules.billAmount(scheduleRow.modelData.expenseId))
                        : scheduleRow.modelData.date
                          +" // "+schedules.money(scheduleRow.modelData.amountCents)
                          +" // "+schedules.goalLabel(scheduleRow.modelData.fundingGoalId)
                    font.pixelSize: 9
                    color: Colors.cyan
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
                ActionButton {
                    id: removeButton
                    anchors.right: parent.right
                    anchors.rightMargin: 7
                    anchors.verticalCenter: parent.verticalCenter
                    width: 78
                    height: 30
                    label: schedules.armedDeleteId===scheduleRow.modelData.id
                        ? "CONFIRM":"DELETE"
                    labelPixelSize: 9
                    accentColor: Colors.red
                    destructive: true
                    available: schedules.ready
                    onLeftClicked: schedules.requestDelete(scheduleRow.modelData.id)
                }
            }
        }
        GohuText {
            visible: schedules.ready && schedules.scheduleRows.length===0
            width: parent.width
            text: "NO LOCAL BILL DUE DAYS OR ONE-TIME PURCHASES"
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "ALL RECORDS ARE OPERATOR-ENTERED ON THIS LINUX LOGIN. UNLINKED PURCHASES REDUCE PLANNED FREE CASH; GOAL-LINKED PURCHASES FIRST USE THE MODELED RESERVED GOAL AMOUNT. NO BANK PAYMENTS OR ACTUAL TRANSFERS."
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
    function billAmount(id) {
        for(let i=0;i<expenses.length;i++)
            if(expenses[i].id===id)return expenses[i].monthlyCents;
        return 0;
    }
}
