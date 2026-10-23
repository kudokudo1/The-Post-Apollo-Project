import QtQuick
import "../../components"
import "TaskDateSegments.js" as DateSegments
import "TaskTodayPolicy.js" as TodayPolicy

// TASKS M5: a read-only local due-date view of the shared Hub/TASKS store.
// No second store, completion timestamps, network, or automatic actions.
Item {
    id: todayPane

    property var todoSnapshot: null
    property string todayKey: ""
    signal openTaskRequested(string taskId)

    readonly property var projection: TodayPolicy.view(todoSnapshot, todayKey)
    readonly property string storeState:
        todoSnapshot && todoSnapshot.state ? String(todoSnapshot.state)
        : "unavailable"

    function refreshToday() {
        const now = new Date();
        todayKey = DateSegments.format({
            year: now.getFullYear(), month: now.getMonth() + 1,
            day: now.getDate()
        });
    }
    onVisibleChanged: {
        if (visible) refreshToday();
    }
    Component.onCompleted: {
        if (visible) refreshToday();
    }

    // Date changes while the menu is left open; this does not poll files
    // or network. The timer is inactive when TODAY is not displayed.
    Timer {
        interval: 60000
        running: todayPane.visible
        repeat: true
        onTriggered: todayPane.refreshToday()
    }

    Column {
        id: summary
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 5

        GohuText {
            width: parent.width
            text: "TODAY // " + (todayPane.todayKey || "LOCAL DATE")
            color: Colors.magenta
            font.pixelSize: 12
            font.bold: true
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            font.pixelSize: 10
            color: Colors.cyan
            text: todayPane.projection.available
                  ? todayPane.projection.overdue + " OVERDUE // "
                    + todayPane.projection.dueToday + " DUE"
                  : todayPane.storeState === "loading" ? "READING CHECKLIST..."
                  : "STORAGE // " + todayPane.storeState.toUpperCase()
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.white
            opacity: 0.68
            text: todayPane.projection.available
                  ? todayPane.projection.completedDueToday + " DONE (DUE TODAY) // "
                    + todayPane.projection.unscheduled + " UNDATED"
                  : "NO SCHEDULED TASKS AVAILABLE"
            elide: Text.ElideRight
        }
    }

    ListView {
        id: dueList
        anchors.top: summary.bottom
        anchors.topMargin: 11
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
        spacing: 3
        boundsBehavior: Flickable.StopAtBounds
        visible: todayPane.projection.available
        model: todayPane.projection.rows

        delegate: Item {
            id: rowItem
            required property var modelData
            width: dueList.width
            height: modelData.kind === "header" ? 26 : 42

            GohuText {
                visible: rowItem.modelData.kind === "header"
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width
                font.pixelSize: 10
                font.bold: true
                color: rowItem.modelData.category === "overdue"
                       ? Colors.orange
                       : rowItem.modelData.category === "completed"
                       ? Colors.magenta : Colors.cyan
                text: rowItem.modelData.kind === "header"
                      ? rowItem.modelData.text : ""
            }

            Item {
                id: taskRow
                anchors.fill: parent
                visible: rowItem.modelData.kind === "task"

                GohuText {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: openButton.left
                    anchors.rightMargin: 6
                    font.pixelSize: 11
                    color: rowItem.modelData.done ? Colors.cyan : Colors.white
                    opacity: rowItem.modelData.done ? 0.66 : 1
                    text: rowItem.modelData.title || ""
                    elide: Text.ElideRight
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    width: parent.width - 58
                    font.pixelSize: 9
                    color: rowItem.modelData.category === "overdue"
                           ? Colors.orange : Colors.cyan
                    text: (rowItem.modelData.dueDate || "") + " // "
                          + (rowItem.modelData.priority || "none").toUpperCase()
                    elide: Text.ElideRight
                }
                ActionButton {
                    id: openButton
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 48
                    height: 25
                    label: "OPEN"
                    labelPixelSize: 10
                    onLeftClicked: todayPane.openTaskRequested(rowItem.modelData.id)
                }
            }
        }
    }

    GohuText {
        anchors.centerIn: dueList
        visible: todayPane.projection.available
                 && todayPane.projection.rows.length === 0
        width: parent.width
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        font.pixelSize: 11
        color: Colors.cyan
        text: "NO OVERDUE OR DUE-TODAY TASKS"
    }
}
