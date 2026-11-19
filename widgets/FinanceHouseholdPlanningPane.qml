import QtQuick
import "../components"
import "FinanceHouseholdPlanningPolicy.js" as Planning

// FP1a: in-memory scenario lab. Not an Actual, Connections or account reader.
Item {
    id: planner
    property string activeContextId: "mine"
    property string upfrontText: "1800.00"
    property string operatingText: "85.00"
    property string alternativeText: "140.00"
    property string hourValueText: "12.00"
    property int extraHours: 2
    property int horizonMonths: 36
    property var preview: null
    readonly property var contexts: Planning.contexts()
    readonly property var activeContext: Planning.context(activeContextId)
    readonly property var inputRows: [
        {key:"upfrontText",label:"UPFRONT INVESTMENT"},
        {key:"operatingText",label:"OPTION / MONTH"},
        {key:"alternativeText",label:"ALTERNATIVE / MONTH"},
        {key:"hourValueText",label:"TIME VALUE / HOUR"}
    ]

    function resetExample(){
        upfrontText="1800.00";
        operatingText="85.00";
        alternativeText="140.00";
        hourValueText="12.00";
        extraHours=2;
        horizonMonths=36;
        preview=null;
    }
    function chooseContext(id){
        if(!Planning.context(id))return false;
        if(activeContextId===id)return true;
        activeContextId=id;
        resetExample();
        plannerScroll.flickable.contentY=0;
        return true;
    }
    function calculate(){
        preview=Planning.compare({
            contextId:activeContextId,upfrontText:upfrontText,
            operatingText:operatingText,alternativeText:alternativeText,
            hourValueText:hourValueText,extraHours:extraHours,
            horizonMonths:horizonMonths
        });
        return preview.ok===true;
    }
    function money(cents){
        if(!Number.isSafeInteger(cents))return "INVALID";
        return (cents<0?"-$":"$")+(Math.abs(cents)/100).toFixed(2);
    }
    onUpfrontTextChanged: preview=null
    onOperatingTextChanged: preview=null
    onAlternativeTextChanged: preview=null
    onHourValueTextChanged: preview=null
    onExtraHoursChanged: preview=null
    onHorizonMonthsChanged: preview=null

    NeonScrollPaneV2 {
        id: plannerScroll
        anchors.fill: parent
        availableExtent: height
        viewportPolicy: "fill"
        contentExtent: body.implicitHeight+20
        handleStyle: "bar"
        Column {
            id: body
            x: 9
            y: 9
            width: Math.max(0,plannerScroll.width-35)
            spacing: 10
            GohuText {
                width: parent.width
                text: "HOUSEHOLDS // SCENARIO LAB"
                font.pixelSize: 13
                font.bold: true
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                text: "SIMULATION ONLY // NO BANK DATA // NOTHING SAVED"
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Flow {
                id: profileRail
                width: parent.width
                spacing: 5
                Repeater {
                    model: planner.contexts
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(82,(profileRail.width-10)/3)
                        height: 31
                        label: modelData.label
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        selected: planner.activeContextId===modelData.id
                        onLeftClicked: planner.chooseContext(modelData.id)
                    }
                }
            }
            GohuText {
                width: parent.width
                text: planner.activeContext
                    ? planner.activeContext.purpose.toUpperCase()
                        +" // LABEL ONLY // NOT AUTHENTICATED"
                    : "UNKNOWN CONTEXT"
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "UPFRONT PURCHASE VS. MONTHLY ALTERNATIVE"
                font.pixelSize: 10
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: planner.inputRows
                delegate: Row {
                    id: inputRow
                    required property var modelData
                    width: body.width
                    height: 29
                    spacing: 6
                    GohuText {
                        width: Math.max(80,inputRow.width-144)
                        height: parent.height
                        text: inputRow.modelData.label
                        font.pixelSize: 9
                        verticalAlignment: Text.AlignVCenter
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                    FinanceMoneyInput {
                        width: 138
                        value: planner[inputRow.modelData.key]
                        onValueEdited: function(next) {
                            planner[inputRow.modelData.key]=next;
                        }
                    }
                }
            }
            Row {
                width: parent.width
                spacing: 6
                GohuText {
                    width: Math.max(90,parent.width-126)
                    height: 28
                    text: "EXTRA TIME / MONTH"
                    font.pixelSize: 9
                    verticalAlignment: Text.AlignVCenter
                    color: Colors.cyan
                }
                ActionButton {
                    width: 31
                    height: 28
                    label: "-"
                    accentColor: Colors.magenta
                    available: planner.extraHours>0
                    onLeftClicked: planner.extraHours=Math.max(0,planner.extraHours-1)
                }
                GohuText {
                    width: 42
                    height: 28
                    text: planner.extraHours+" h"
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: Colors.white
                }
                ActionButton {
                    width: 31
                    height: 28
                    label: "+"
                    accentColor: Colors.magenta
                    available: planner.extraHours<168
                    onLeftClicked: planner.extraHours=Math.min(168,planner.extraHours+1)
                }
            }
            GohuText {
                width: parent.width
                text: "PLANNING HORIZON"
                font.pixelSize: 10
                color: Colors.cyan
            }
            Flow {
                id: horizonRail
                width: parent.width
                spacing: 5
                Repeater {
                    model: [
                        {months:12,label:"1 YEAR"},
                        {months:36,label:"3 YEARS"},
                        {months:60,label:"5 YEARS"},
                        {months:120,label:"10 YEARS"},
                        {months:360,label:"30 YEARS"}
                    ]
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(65,(horizonRail.width-15)/4)
                        height: 28
                        label: modelData.label
                        labelPixelSize: 8
                        accentColor: Colors.magenta
                        selected: planner.horizonMonths===modelData.months
                        onLeftClicked: planner.horizonMonths=modelData.months
                    }
                }
            }
            ActionButton {
                width: body.width
                height: 33
                label: "CALCULATE HYPOTHETICAL COSTS"
                labelPixelSize: 10
                accentColor: Colors.omnitrix
                onLeftClicked: planner.calculate()
            }
            GohuText {
                width: parent.width
                visible: !!planner.preview && planner.preview.ok===false
                text: planner.preview ? "INPUT REFUSED // "+planner.preview.reason : ""
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
            }
            Rectangle {
                width: body.width
                height: visible ? resultColumn.implicitHeight+16 : 0
                visible: !!planner.preview && planner.preview.ok===true
                color: Colors.black
                border.color: Colors.magenta
                border.width: 1
                Column {
                    id: resultColumn
                    x: 8
                    y: 8
                    width: Math.max(0,parent.width-16)
                    spacing: 7
                    GohuText {
                        width: parent.width
                        text: "HYPOTHETICAL COSTS // NOT BANK BALANCES"
                        color: Colors.orange
                        font.pixelSize: 9
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: planner.preview&&planner.preview.ok
                            ? "INVESTMENT TOTAL // "+planner.money(planner.preview.optionTotalCents) : ""
                        color: Colors.white
                        font.pixelSize: 10
                    }
                    GohuText {
                        width: parent.width
                        text: planner.preview&&planner.preview.ok
                            ? "ALTERNATIVE TOTAL // "+planner.money(planner.preview.alternativeTotalCents) : ""
                        color: Colors.white
                        font.pixelSize: 10
                    }
                    GohuText {
                        width: parent.width
                        text: planner.preview&&planner.preview.ok
                            ? (planner.preview.optionSavingsCents>=0
                                ? "INVESTMENT SAVES // " : "ALTERNATIVE SAVES // ")
                                +planner.money(Math.abs(planner.preview.optionSavingsCents)) : ""
                        color: Colors.omnitrix
                        font.pixelSize: 10
                    }
                    GohuText {
                        width: parent.width
                        text: planner.preview&&planner.preview.ok
                            ? "INVESTMENT BREAK-EVEN // "
                                +(planner.preview.breakEvenMonths===null
                                    ? "NOT REACHED"
                                    : planner.preview.breakEvenMonths+" MONTHS")
                            : ""
                        color: Colors.cyan
                        font.pixelSize: 9
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "FIXED PRICES. NO FINANCING, TAX, INFLATION OR RESALE. SWITCHING CONTEXT RESETS THE EXAMPLE. NO ACCOUNTS OR HOUSEHOLDS ARE CONNECTED."
                font.pixelSize: 9
                color: Colors.orange
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
        }
    }
}
