import QtQuick
import "../components"
import "FinanceHouseholdTimelinePolicy.js" as Timeline

// FP1d: summary-only local timeline, installed inside the existing plans
// scroll viewport. The parent provides only the selected manual plan rows.
Item {
    id: timeline
    property string contextId: "mine"
    property string startMonth: ""
    property int horizonMonths: 6
    property bool active: false
    property var sourceRows: []
    property var scheduleRows: []
    property bool schedulesReady: false
    signal horizonRequested(int months)
    readonly property var projection: active && schedulesReady
        ? Timeline.project(sourceRows,scheduleRows,startMonth,horizonMonths,contextId)
        : null
    width: parent ? parent.width : 0
    implicitHeight: timelineBody.implicitHeight
    height: visible ? implicitHeight : 0

    function signed(cents) {
        if(!Number.isSafeInteger(cents))return "INVALID";
        return (cents<0?"-":"+")+"$"+(Math.abs(cents)/100).toFixed(2);
    }
    function money(cents) {
        if(!Number.isSafeInteger(cents))return "INVALID";
        return "$"+(cents/100).toFixed(2);
    }
    Column {
        id: timelineBody
        width: parent.width
        spacing: 9
        GohuText {
            width: parent.width
            text: "BUDGET TIMELINE // MANUAL MONTHLY PLANS"
            font.pixelSize: 11
            color: Colors.magenta
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "GOAL DEADLINES ARE MILESTONES. DATED ONE-TIME PAYMENTS ARE MODELED SEPARATELY."
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Flow {
            id: horizonRail
            width: parent.width
            spacing: 5
            Repeater {
                model: [
                    {months:6,label:"6 MONTHS"},
                    {months:12,label:"12 MONTHS"},
                    {months:24,label:"24 MONTHS"}
                ]
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(80,(horizonRail.width-10)/3)
                    height: 29
                    label: modelData.label
                    labelPixelSize: 9
                    selected: timeline.horizonMonths===modelData.months
                    accentColor: Colors.magenta
                    onLeftClicked: timeline.horizonRequested(modelData.months)
                }
            }
        }
        GohuText {
            width: parent.width
            text: !timeline.active || !timeline.schedulesReady
                ? "LOCAL PLANS OR SCHEDULES NOT READY"
                : timeline.projection && timeline.projection.ok
                  ? "LISTED INCOME / COSTS / GOAL CONTRIBUTIONS PER MONTH"
                  : "NO TIMELINE // "
                      +(timeline.projection?timeline.projection.reason:"NOT LOADED")
            color: timeline.projection && timeline.projection.ok
                ? Colors.cyan : Colors.orange
            font.pixelSize: 9
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: timeline.projection && timeline.projection.ok
                ? timeline.projection.priorDeadlines : []
            delegate: Rectangle {
                required property var modelData
                width: timelineBody.width
                height: warningLabel.implicitHeight+14
                color: Colors.black
                border.color: Colors.orange
                GohuText {
                    id: warningLabel
                    x: 7
                    y: 7
                    width: Math.max(0,parent.width-14)
                    text: "PAST TARGET "+modelData.deadlineMonth+" // "+modelData.title
                        +" // INITIAL SHORTFALL "+timeline.money(modelData.gapCents)
                    font.pixelSize: 9
                    color: Colors.orange
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
            }
        }
        Repeater {
            model: timeline.projection && timeline.projection.ok
                ? timeline.projection.priorSchedules : []
            delegate: Rectangle {
                required property var modelData
                width: timelineBody.width
                height: priorPaymentLabel.implicitHeight+14
                color: Colors.black
                border.color: Colors.orange
                GohuText {
                    id: priorPaymentLabel
                    x: 7
                    y: 7
                    width: Math.max(0,parent.width-14)
                    text: "PAST PLANNED PURCHASE "+modelData.date+" // "
                        +modelData.title+" // "+timeline.money(modelData.amountCents)
                        +" // NOT MARKED AS PAID"
                    font.pixelSize: 9
                    color: Colors.orange
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
            }
        }
        Repeater {
            model: timeline.projection && timeline.projection.ok
                ? timeline.projection.months : []
            delegate: Rectangle {
                id: monthCard
                required property var modelData
                width: timelineBody.width
                height: monthContent.implicitHeight+16
                color: Colors.black
                border.color: modelData.events.some(function(e) {
                    return e.status==="TARGET_SHORTFALL";
                }) ? Colors.orange : Colors.cyan
                border.width: 1
                Column {
                    id: monthContent
                    x: 8
                    y: 8
                    width: Math.max(0,parent.width-16)
                    spacing: 5
                    GohuText {
                        width: parent.width
                        text: monthCard.modelData.month+" // MANUAL MONTH PLAN"
                        font.pixelSize: 11
                        font.bold: true
                        color: Colors.magenta
                        textFormat: Text.PlainText
                    }
                    GohuText {
                        width: parent.width
                        text: "INCOME "+timeline.money(monthCard.modelData.incomeCents)
                            +" // COSTS "+timeline.money(monthCard.modelData.expenseCents)
                        font.pixelSize: 9
                        color: Colors.white
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "GOAL SAVINGS "+timeline.money(monthCard.modelData.contributionCents)
                            +" // NEW-CASH PURCHASES "+timeline.money(monthCard.modelData.purchaseNewCashCents)
                            +" // CHANGE "+timeline.signed(monthCard.modelData.changeCents)
                        font.pixelSize: 9
                        color: monthCard.modelData.changeCents<0
                            ? Colors.orange : Colors.omnitrix
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "CUMULATIVE MODEL CHANGE "
                            +timeline.signed(monthCard.modelData.cumulativeChangeCents)
                            +" // NOT AVAILABLE CASH"
                        font.pixelSize: 9
                        color: Colors.cyan
                        textFormat: Text.PlainText
                        wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: monthCard.modelData.events
                        delegate: GohuText {
                            required property var modelData
                            width: monthContent.width
                            text: modelData.status==="GOAL_SPENT_EARLIER"
                                ? "GOAL // "+modelData.title
                                  +" // RESERVED MONEY MODELED AS SPENT EARLIER"
                                : "TARGET // "+modelData.title
                                  +" // "+(modelData.gapCents>0
                                      ? "GAP "+timeline.money(modelData.gapCents)
                                      : "FUNDED IN MODEL")
                                  +" // NOT A PURCHASE PAYMENT"
                            font.pixelSize: 9
                            color: modelData.gapCents>0?Colors.orange:Colors.magenta
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                    }
                    Repeater {
                        model: monthCard.modelData.billEvents
                        delegate: GohuText {
                            required property var modelData
                            width: monthContent.width
                            text: "BILL DUE "+modelData.dueDate+" // "+modelData.title
                                +" // "+timeline.money(modelData.amountCents)
                                +(modelData.adjustedToMonthEnd?" (MONTH-END ADJUSTED)":"")
                                +" // INCLUDED IN COSTS ONCE"
                            font.pixelSize: 9
                            color: Colors.cyan
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                    }
                    Repeater {
                        model: monthCard.modelData.purchaseEvents
                        delegate: GohuText {
                            required property var modelData
                            width: monthContent.width
                            text: "PLANNED PURCHASE "+modelData.date+" // "+modelData.title
                                +" // TOTAL "+timeline.money(modelData.amountCents)
                                +" // GOAL RESERVE "+timeline.money(modelData.goalFundedCents)
                                +" // NEW CASH "+timeline.money(modelData.newCashCents)
                                +" // NOT ACTUALLY PAID"
                            font.pixelSize: 9
                            color: modelData.newCashCents>0?Colors.orange:Colors.magenta
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            text: "ESTIMATES ONLY: SCHEDULED BILL DAYS REFER TO COSTS ALREADY COUNTED ONCE. ONE-TIME PAYMENTS ARE MODELED ON THEIR DATES; GOAL-LINKED PURCHASES USE MODELED RESERVES FIRST, THEN NEW CASH. NOTHING IS PAID OR TRANSFERRED. TAX, DEBT, INFLATION, UNKNOWN BILLS AND INITIAL CASH ARE NOT INCLUDED."
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
