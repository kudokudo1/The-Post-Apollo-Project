import QtQuick
import "../../components"
import "TaskPlannerPolicy.js" as Planner

// PLANNER M1 is an isolated read-only consumer of the existing snapshot.
// Host wiring is intentionally deferred to the TasksW owner.
Item {
    id: planner
    property var todoSnapshot: null
    property string monthKey: ""
    property string selectedDate: ""
    property string todayKey: ""
    signal openTaskRequested(string taskId)

    readonly property var calendar: Planner.view(todoSnapshot, monthKey, selectedDate, todayKey)
    readonly property var weekdays: ["M", "T", "W", "T", "F", "S", "S"]

    function refreshLocalDate() {
        var d=new Date();
        var k=Planner.key(d.getFullYear(),d.getMonth()+1,d.getDate());
        todayKey=k;
        if (!monthKey) monthKey=k.slice(0,7)+"-01";
        if (!selectedDate) selectedDate=k;
    }
    function changeMonth(amount) {
        monthKey=Planner.moveMonth(monthKey,amount);
        selectedDate=monthKey;
    }
    onVisibleChanged: { if (visible) refreshLocalDate(); }
    Component.onCompleted: refreshLocalDate()
    Timer {
        interval: 60000
        running: planner.visible
        repeat: true
        onTriggered: planner.refreshLocalDate()
    }

    Column {
        id: heading
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 6

        GohuText {
            text: "PLANNER // LOCAL CALENDAR"
            font.pixelSize: 12
            font.bold: true
            color: Colors.magenta
        }
        Row {
            width: parent.width
            height: 29
            spacing: 5
            ActionButton {
                width: 32; height: 27
                label: "‹"; labelPixelSize: 18
                onLeftClicked: planner.changeMonth(-1)
            }
            GohuText {
                width: parent.width-74
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                text: planner.monthKey.slice(0,7)
                font.pixelSize: 13
                color: Colors.white
            }
            ActionButton {
                width: 32; height: 27
                label: "›"; labelPixelSize: 18
                onLeftClicked: planner.changeMonth(1)
            }
        }
        GohuText {
            width: parent.width
            text: planner.calendar.available
                ? planner.calendar.scheduled+" DATED // "+planner.calendar.undated+" UNDATED"
                : "STORAGE // "+planner.calendar.state.toUpperCase()
            font.pixelSize: 10
            color: Colors.cyan
        }
    }

    Item {
        id: calendarArea
        anchors.top: heading.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.right: parent.right
        height: 237

        Grid {
            id: weekdays
            columns: 7
            width: parent.width
            height: 22
            Repeater {
                model: planner.weekdays
                GohuText {
                    required property string modelData
                    width: weekdays.width/7
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData
                    font.pixelSize: 10
                    color: Colors.cyan
                }
            }
        }
        Grid {
            id: monthGrid
            anchors.top: weekdays.bottom
            columns: 7
            width: parent.width
            rowSpacing: 2
            columnSpacing: 2
            Repeater {
                model: planner.calendar.days
                Rectangle {
                    required property var modelData
                    width: (monthGrid.width-12)/7
                    height: 32
                    color: modelData.selected ? Colors.dark : "transparent"
                    border.width: modelData.selected || modelData.today ? 1 : 0
                    border.color: modelData.today ? Colors.orange : Colors.magenta
                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 3
                        text: parent.modelData.day
                        font.pixelSize: 10
                        color: parent.modelData.remaining>0 ? Colors.white : Colors.cyan
                        opacity: parent.modelData.inMonth ? 1 : 0
                    }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 3
                        width: Math.min(18,parent.modelData.remaining*5)
                        height: 2
                        color: Colors.orange
                        visible: parent.modelData.remaining>0
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: parent.modelData.inMonth
                        onClicked: planner.selectedDate=parent.modelData.date
                    }
                }
            }
        }
    }

    GohuText {
        id: agendaTitle
        anchors.top: calendarArea.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        text: "AGENDA // "+planner.selectedDate
        color: Colors.magenta
        font.pixelSize: 11
        font.bold: true
    }
    ListView {
        id: agendaList
        anchors.top: agendaTitle.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: 4
        model: planner.calendar.agenda
        delegate: Item {
            required property var modelData
            width: agendaList.width
            height: 42
            GohuText {
                anchors.left: parent.left
                anchors.right: openButton.left
                anchors.rightMargin: 5
                anchors.top: parent.top
                text: modelData.title
                elide: Text.ElideRight
                font.pixelSize: 11
                color: modelData.done ? Colors.cyan : Colors.white
            }
            GohuText {
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                text: (modelData.done ? "DONE" : "OPEN")+" // "+modelData.priority.toUpperCase()
                font.pixelSize: 9
                color: Colors.cyan
            }
            ActionButton {
                id: openButton
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 47; height: 26
                label: "OPEN"; labelPixelSize: 10
                onLeftClicked: planner.openTaskRequested(modelData.id)
            }
        }
    }
    GohuText {
        anchors.centerIn: agendaList
        visible: planner.calendar.available && planner.calendar.agenda.length===0
        text: "NO TASKS ON SELECTED DATE"
        color: Colors.cyan
        font.pixelSize: 10
    }
}
