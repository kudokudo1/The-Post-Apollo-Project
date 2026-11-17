import QtQuick
import QtQuick.Window
import "../../widgets" as FinanceWidgets

// A real FinanceBudgetScrollRail instance inside a Budget-like Column.
// Dynamic header/summary heights and window resizing must move the rail.
Window {
    id: root
    width: 360
    height: 520
    color: "#170d21"
    visible: true
    property int headerHeight: 78
    property int summaryHeight: 46
    property real dataHeight: 1000
    property bool budgetActive: true

    Rectangle {
        id: emptyPage
        objectName: "budgetFrame"
        x: 10
        y: 16
        width: root.width - 20
        height: root.height - 28
        color: "#21112e"

        Column {
            id: actualBudgetPage
            objectName: "budgetColumn"
            anchors.fill: parent
            anchors.margins: 9
            spacing: 9
            visible: root.budgetActive

            Rectangle {
                id: controls
                width: parent.width
                height: root.headerHeight
                color: "#351d47"
            }
            Rectangle {
                id: summaries
                width: parent.width
                height: root.summaryHeight
                color: "#453059"
            }
            Flickable {
                id: budgetScroll
                objectName: "budgetViewport"
                width: parent.width
                height: Math.max(0, actualBudgetPage.height - y - 4)
                contentWidth: width
                contentHeight: root.dataHeight
                boundsBehavior: Flickable.StopAtBounds
                clip: true
                Rectangle {
                    width: budgetScroll.width - 22
                    height: root.dataHeight
                    color: "#312040"
                }
            }
        }

        FinanceWidgets.FinanceBudgetScrollRail {
            id: budgetScrollBar
            objectName: "budgetRailHost"
            scrollTarget: budgetScroll
            layoutHost: actualBudgetPage
        }
    }
}
