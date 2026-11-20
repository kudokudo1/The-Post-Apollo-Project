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
    readonly property var coverage: active && schedulesReady
        ? Timeline.coverage(sourceRows,scheduleRows) : null
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
        GohuText {
            width: parent.width
            text: timeline.coverage && timeline.coverage.ok
                ? "DUE-DAY COVERAGE // "+timeline.coverage.datedExpenseCount
                    +" / "+timeline.coverage.monthlyExpenseCount
                    +" ENTERED EXPENSES HAVE DUE-DAY SCHEDULES. "
                    +"UNLISTED HOUSEHOLD BILLS ARE UNKNOWN."
                : "COVERAGE UNAVAILABLE // "
                    +(timeline.coverage?timeline.coverage.reason:"LOCAL RECORDS NOT READY")
            font.pixelSize: 9
            color: timeline.coverage && timeline.coverage.ok
                && timeline.coverage.undatedExpenseCount===0
                ? Colors.cyan : Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: timeline.coverage && timeline.coverage.ok
                && timeline.coverage.cadenceCount>0
            text: timeline.coverage && timeline.coverage.ok
                ? "NONMONTHLY BILLING // "
                    +timeline.coverage.quarterlyBillCount+" QUARTERLY, "
                    +timeline.coverage.annualBillCount+" ANNUAL. "
                    +"THE ENTERED EXPENSE AMOUNT IS CHARGED PER OCCURRENCE, "
                    +"NOT AS A MONTHLY AVERAGE."
                : ""
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: timeline.coverage && timeline.coverage.ok
                && timeline.coverage.undatedExpenseCount>0
            text: timeline.coverage && timeline.coverage.ok
                ? "MISSING DUE DAYS // "
                    +timeline.coverage.undatedExpenseTitles.join(", ")
                    +" // AMOUNTS REMAIN COUNTED IN MONTHLY COSTS" : ""
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: timeline.coverage && timeline.coverage.ok
                && timeline.coverage.manualIncomeCount===0
            text: "NO MANUAL INCOME ENTRY // FORECAST REFUSES TO GUESS"
            font.pixelSize: 9
            color: Colors.orange
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
                            +" // DEFERRED BILL PAYMENTS "+timeline.money(monthCard.modelData.movedPaymentCents)
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
                                +(modelData.intervalMonths===3?" (QUARTERLY)"
                                    :modelData.intervalMonths===12?" (ANNUAL)":" (MONTHLY)")
                                +(modelData.adjustedToMonthEnd?" (MONTH-END ADJUSTED)":"")
                                +" // INCLUDED IN COSTS ONCE"
                            font.pixelSize: 9
                            color: Colors.cyan
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                    }
                    Repeater {
                        model: monthCard.modelData.exceptionEvents
                        delegate: GohuText {
                            required property var modelData
                            width: monthContent.width
                            text: "EXCLUDED FROM "+modelData.month+" MODEL // "
                                +modelData.title+" // "
                                +timeline.money(modelData.excludedCents)
                                +" // NOT CONFIRMED WAIVED OR PAID; NOT DEFERRED"
                            font.pixelSize: 9
                            color: Colors.orange
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                    }
                    Repeater {
                        model: monthCard.modelData.movedFromEvents
                        delegate: GohuText {
                            required property var modelData
                            width: monthContent.width
                            text: "MODELED BILL MOVED // "+modelData.title
                                +" // FROM "+modelData.sourceMonth+" TO "+modelData.targetDate
                                +" // "+timeline.money(modelData.movedCents)
                                +" // NOT WAIVED OR PAID"
                            font.pixelSize: 9
                            color: Colors.orange
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                    }
                    Repeater {
                        model: monthCard.modelData.movedToEvents
                        delegate: GohuText {
                            required property var modelData
                            width: monthContent.width
                            text: "MODELED DEFERRED PAYMENT "+modelData.targetDate
                                +" // "+modelData.title
                                +" // "+timeline.money(modelData.movedCents)
                                +" // PLUS CURRENT ORDINARY BILL // NOT PAID"
                            font.pixelSize: 9
                            color: Colors.magenta
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
            text: "NONMONTHLY BILLS USE PER-CHARGE AMOUNTS ONLY IN OCCURRENCE MONTHS; THIS IS NOT MONTHLY ACCRUAL. ESTIMATES ONLY: AN EXPLICIT DEFERRED BILL IS MODELED IN ITS NEW MONTH, ON TOP OF THAT MONTH\u0027S ORDINARY BILL. DEFERRED AMOUNTS TRACK THE CURRENT MANUAL MONTHLY COST, NOT A CONTRACTUAL PAYMENT. A BILL EXCLUDED FOR ONE MONTH IS NOT ASSUMED FORGIVEN, PAID OR DEFERRED. DUE DAYS LABEL MONTHLY COSTS COUNTED ONCE. ONE-TIME PURCHASES ARE SEPARATE; GOAL RESERVES ARE USED FIRST. UNKNOWN BILLS, TAX, DEBT, INFLATION AND STARTING CASH ARE OMITTED. NOTHING IS TRANSFERRED."
            font.pixelSize: 9
            color: Colors.orange
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
    }
}
