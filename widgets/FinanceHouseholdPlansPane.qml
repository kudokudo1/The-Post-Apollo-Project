import QtQuick
import "../components"
import "../services/finance" as FinanceServices
import "FinanceHouseholdPlanningPolicy.js" as Planning

// FP1b: explicit local-only household planning, not verified financial access.
Item {
    id: plansPane
    property string contextId: "mine"
    property bool active: false
    property string section: "goals"
    property string entryTitle: ""
    property string targetText: "1000.00"
    property string savedText: "0.00"
    property string monthlyText: "100.00"
    property string armedDeleteId: ""
    readonly property var contexts: Planning.contexts()
    readonly property var goals: savedPlans.rows.filter(function(x){return x.kind==="goal";})
    readonly property var expenses: savedPlans.rows.filter(function(x){return x.kind==="expense";})
    signal contextRequested(string id)

    FinanceServices.FinanceHouseholdPlanStore {
        id: savedPlans
        contextId: plansPane.contextId
        monitoring: plansPane.active
        onEntrySaved: plansPane.clearEditor()
        onEntryDeleted: plansPane.armedDeleteId=""
    }
    function clearEditor() {
        entryTitle="";
        targetText="1000.00";
        savedText="0.00";
        monthlyText="100.00";
        armedDeleteId="";
    }
    function setSection(next) {
        if(next!=="goals" && next!=="expenses")return;
        section=next;
        clearEditor();
        plansScroll.flickable.contentY=0;
    }
    function submit() {
        if(savedPlans.state!=="ready" || !entryTitle.trim())return false;
        armedDeleteId="";
        return savedPlans.add(section==="goals"?"goal":"expense",
            entryTitle,section==="goals"?targetText:"0",
            section==="goals"?savedText:"0",monthlyText);
    }
    function requestDelete(id) {
        if(savedPlans.state!=="ready")return false;
        if(armedDeleteId!==id) {
            armedDeleteId=id;
            return false;
        }
        armedDeleteId="";
        return savedPlans.remove(id);
    }
    function dollars(cents) {
        return Number.isSafeInteger(cents)
            ? "$"+(cents/100).toFixed(2) : "INVALID";
    }
    function forecast(row) {
        if(row.kind!=="goal")return "";
        if(row.savedCents>=row.targetCents)return "TARGET REACHED (MANUAL)";
        if(row.monthlyCents===0)return "NO MONTHLY CONTRIBUTION";
        const remaining=row.targetCents-row.savedCents;
        return Math.ceil(remaining/row.monthlyCents)+" MONTHS AT PLANNED RATE";
    }
    onContextIdChanged: {
        clearEditor();
        plansScroll.flickable.contentY=0;
    }

    NeonScrollPaneV2 {
        id: plansScroll
        anchors.fill: parent
        availableExtent: height
        contentExtent: body.implicitHeight+18
        viewportPolicy: "fill"
        handleStyle: "bar"
        Column {
            id: body
            x: 9
            y: 9
            width: Math.max(0,plansScroll.width-35)
            spacing: 9
            GohuText {
                width: parent.width
                text: "LOCAL PLANS // GOALS + RECURRING COSTS"
                color: Colors.magenta
                font.pixelSize: 12
                font.bold: true
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "LOCAL FILES // NOT BANK VERIFIED // NO HOUSEHOLD ACCESS GRANT"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Flow {
                id: contextsRail
                width: parent.width
                spacing: 4
                Repeater {
                    model: plansPane.contexts
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(80,(contextsRail.width-8)/3)
                        height: 29
                        label: modelData.label
                        labelPixelSize: 9
                        selected: plansPane.contextId===modelData.id
                        available: savedPlans.state!=="pending"
                        accentColor: Colors.cyan
                        onLeftClicked: plansPane.contextRequested(modelData.id)
                    }
                }
            }
            Row {
                width: parent.width
                spacing: 5
                ActionButton {
                    width: (parent.width-5)/2
                    height: 30
                    label: "SAVINGS GOALS"
                    labelPixelSize: 9
                    selected: plansPane.section==="goals"
                    accentColor: Colors.omnitrix
                    onLeftClicked: plansPane.setSection("goals")
                }
                ActionButton {
                    width: (parent.width-5)/2
                    height: 30
                    label: "MONTHLY COSTS"
                    labelPixelSize: 9
                    selected: plansPane.section==="expenses"
                    accentColor: Colors.cyan
                    onLeftClicked: plansPane.setSection("expenses")
                }
            }
            GohuText {
                width: parent.width
                text: savedPlans.message
                font.pixelSize: 9
                color: savedPlans.state==="failed"?Colors.red:Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 27
                label: "REFRESH LOCAL PLANS"
                labelPixelSize: 9
                accentColor: Colors.cyan
                available: savedPlans.state!=="pending"
                            && savedPlans.state!=="loading"
                onLeftClicked: savedPlans.refresh()
            }
            GohuText {
                width: parent.width
                text: plansPane.section==="goals"
                    ? "ADD A MANUAL SAVINGS TARGET"
                    : "ADD A MANUAL MONTHLY COMMITMENT"
                font.pixelSize: 10
                color: Colors.white
            }
            Rectangle {
                width: body.width
                height: 31
                color: Colors.dark
                border.color: titleInput.activeFocus?Colors.magenta:Colors.cyan
                border.width: 1
                TextInput {
                    id: titleInput
                    anchors.fill: parent
                    anchors.margins: 6
                    text: plansPane.entryTitle
                    color: Colors.white
                    font.pixelSize: 11
                    maximumLength: 80
                    clip: true
                    selectByMouse: true
                    verticalAlignment: TextInput.AlignVCenter
                    onTextEdited: plansPane.entryTitle=text
                }
            }
            GohuText {
                width: parent.width
                text: "TITLE (E.G. CAR, RENT, EMERGENCY FUND)"
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Row {
                visible: plansPane.section==="goals"
                width: body.width
                height: visible?30:0
                spacing: 5
                GohuText {
                    width: Math.max(70,parent.width-145)
                    height: parent.height
                    text: "GOAL TARGET"
                    font.pixelSize: 9
                    color: Colors.cyan
                    verticalAlignment: Text.AlignVCenter
                }
                FinanceMoneyInput {
                    width: 140
                    value: plansPane.targetText
                    onValueEdited: function(v){plansPane.targetText=v;}
                }
            }
            Row {
                visible: plansPane.section==="goals"
                width: body.width
                height: visible?30:0
                spacing: 5
                GohuText {
                    width: Math.max(70,parent.width-145)
                    height: parent.height
                    text: "ALREADY SET ASIDE (MANUAL)"
                    font.pixelSize: 9
                    color: Colors.cyan
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                FinanceMoneyInput {
                    width: 140
                    value: plansPane.savedText
                    onValueEdited: function(v){plansPane.savedText=v;}
                }
            }
            Row {
                width: body.width
                height: 30
                spacing: 5
                GohuText {
                    width: Math.max(70,parent.width-145)
                    height: parent.height
                    text: plansPane.section==="goals"
                        ? "SAVE PER MONTH (PLAN)" : "MONTHLY COST (PLAN)"
                    font.pixelSize: 9
                    color: Colors.cyan
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                FinanceMoneyInput {
                    width: 140
                    value: plansPane.monthlyText
                    onValueEdited: function(v){plansPane.monthlyText=v;}
                }
            }
            ActionButton {
                width: body.width
                height: 31
                label: plansPane.section==="goals"?"SAVE LOCAL GOAL":"SAVE LOCAL COST"
                labelPixelSize: 10
                accentColor: Colors.omnitrix
                available: savedPlans.state==="ready"
                onLeftClicked: plansPane.submit()
            }
            GohuText {
                width: parent.width
                text: plansPane.section==="goals"
                    ? "MANUAL GOALS // NOT ACTUAL SAVINGS OR BALANCES"
                    : "MONTHLY ITEMS // NOT SYNCHRONIZED BANK PAYMENTS"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: plansPane.section==="goals"?plansPane.goals:plansPane.expenses
                delegate: Rectangle {
                    id: entryRow
                    required property var modelData
                    width: body.width
                    height: 92
                    color: Colors.black
                    border.color: Colors.cyan
                    border.width: 1
                    GohuText {
                        anchors.top: parent.top
                        anchors.topMargin: 6
                        anchors.left: parent.left
                        anchors.leftMargin: 7
                        anchors.right: deleteAction.left
                        anchors.rightMargin: 6
                        text: entryRow.modelData.title
                        font.pixelSize: 10
                        color: Colors.white
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                    }
                    GohuText {
                        anchors.left: parent.left
                        anchors.leftMargin: 7
                        anchors.right: deleteAction.left
                        anchors.rightMargin: 6
                        anchors.top: parent.top
                        anchors.topMargin: 29
                        text: entryRow.modelData.kind==="goal"
                            ? ("TARGET "+plansPane.dollars(entryRow.modelData.targetCents)
                               +" // SET ASIDE "+plansPane.dollars(entryRow.modelData.savedCents))
                            : "MONTHLY "+plansPane.dollars(entryRow.modelData.monthlyCents)
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                    GohuText {
                        anchors.left: parent.left
                        anchors.leftMargin: 7
                        anchors.right: deleteAction.left
                        anchors.rightMargin: 6
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 8
                        text: entryRow.modelData.kind==="goal"
                            ? plansPane.forecast(entryRow.modelData)
                            : "MANUAL RECURRING PLAN ONLY"
                        font.pixelSize: 9
                        color: Colors.orange
                        elide: Text.ElideRight
                    }
                    ActionButton {
                        id: deleteAction
                        anchors.right: parent.right
                        anchors.rightMargin: 7
                        anchors.verticalCenter: parent.verticalCenter
                        width: 77
                        height: 30
                        label: plansPane.armedDeleteId===entryRow.modelData.id
                            ? "CONFIRM" : "DELETE"
                        labelPixelSize: 9
                        destructive: true
                        accentColor: Colors.red
                        available: savedPlans.state==="ready"
                        onLeftClicked: plansPane.requestDelete(entryRow.modelData.id)
                    }
                }
            }
            GohuText {
                width: parent.width
                visible: (plansPane.section==="goals"
                          ?plansPane.goals.length:plansPane.expenses.length)===0
                text: "NO SAVED LOCAL ITEMS IN THIS PLANNING CONTEXT"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "FILES ARE PRIVATE TO THIS LOCAL UNIX USER, NOT SEPARATE PERSON LOGINS. ALL AMOUNTS ARE MANUAL. REAL HOUSEHOLD PERMISSIONS AND BANK DATA REQUIRE CONNECTIONS / IDENTITY."
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
    }
}
