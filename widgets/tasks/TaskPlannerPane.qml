import QtQuick
import "../../components"
import "TaskPlannerPolicy.js" as Planner

// PLANNER M5a: calendar remains read-only; deliberate scheduling uses
// the already-guarded shared todo writer passed by TASKS, never a new store.
Item {
    id: planner
    property var todoSnapshot: null
    property var todoStore: null
    property bool scheduleMode: false
    property string monthKey: ""
    property string selectedDate: ""
    property string todayKey: ""
    property string viewMode: "month"
    signal openTaskRequested(string taskId)

    readonly property var calendar: Planner.view(todoSnapshot, monthKey, selectedDate, todayKey)
    readonly property var weekRows: Planner.weekDays(todoSnapshot, selectedDate, todayKey)
    readonly property var weekdays: ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

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
    function selectDate(dateKey) {
        if (!Planner.parse(dateKey)) return;
        selectedDate = dateKey;
        monthKey = dateKey.slice(0,7) + "-01";
    }
    function navigate(amount) {
        if (viewMode === "month") changeMonth(amount);
        else selectDate(Planner.moveDay(selectedDate, amount*(viewMode === "week" ? 7 : 1)));
    }
    function jumpToday() {
        refreshLocalDate();
        selectDate(todayKey);
        viewMode = "day";
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
        // Read-only view selection. Operator has deferred cosmetic polish.
        Row {
            id: viewSwitcher
            width: parent.width
            height: 27
            spacing: 4
            Repeater {
                model: ["MONTH", "WEEK", "DAY", "TODAY"]
                ActionButton {
                    required property string modelData
                    width: (viewSwitcher.width - 12) / 4
                    height: 26
                    label: modelData
                    labelPixelSize: 9
                    selected: modelData.toLowerCase() === planner.viewMode
                    onLeftClicked: {
                        if (modelData === "TODAY") planner.jumpToday();
                        else planner.viewMode = modelData.toLowerCase();
                    }
                }
            }
        }
        Row {
            width: parent.width
            height: 29
            spacing: 5
            ActionButton {
                width: 32; height: 27
                label: "‹"; labelPixelSize: 18
                onLeftClicked: planner.navigate(-1)
            }
            GohuText {
                width: parent.width-74
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                text: planner.viewMode === "month" ? planner.monthKey.slice(0,7)
                      : planner.viewMode === "week" ? "WEEK // " + planner.selectedDate
                      : planner.selectedDate
                font.pixelSize: 13
                color: Colors.white
            }
            ActionButton {
                width: 32; height: 27
                label: "›"; labelPixelSize: 18
                onLeftClicked: planner.navigate(1)
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
        Row {
            width: parent.width
            height: 26
            spacing: 5
            ActionButton {
                width: (parent.width - 5) / 2
                height: 26
                label: "AGENDA"
                labelPixelSize: 10
                selected: !planner.scheduleMode
                onLeftClicked: planner.scheduleMode = false
            }
            ActionButton {
                width: (parent.width - 5) / 2
                height: 26
                label: "SCHEDULE"
                labelPixelSize: 10
                selected: planner.scheduleMode
                onLeftClicked: planner.scheduleMode = true
            }
        }
    }

    Item {
        id: calendarArea
        anchors.top: heading.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.right: parent.right
        // Keep a useful agenda viewport when the host is shorter than the M1 pilot.
        height: planner.viewMode === "day" ? 0
                : Math.min(237, Math.max(150, planner.height * 0.38))

        Grid {
            id: weekdays
            visible: planner.viewMode === "month"
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
            visible: planner.viewMode === "month"
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
                    height: Math.max(19, Math.min(32, (calendarArea.height - weekdays.height - 10) / 6))
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
                        onClicked: planner.selectDate(parent.modelData.date)
                    }
                }
            }
        }
        Column {
            id: weekColumn
            anchors.fill: parent
            spacing: 2
            visible: planner.viewMode === "week"
            Repeater {
                model: planner.calendar.available ? planner.weekRows : []
                Rectangle {
                    id: weekRow
                    required property var modelData
                    width: weekColumn.width
                    height: Math.max(0, (calendarArea.height - 12) / 7)
                    color: modelData.selected ? Colors.dark : "transparent"
                    border.width: modelData.selected || modelData.today ? 1 : 0
                    border.color: modelData.today ? Colors.orange : Colors.magenta
                    GohuText {
                        anchors.left: parent.left
                        anchors.leftMargin: 5
                        anchors.verticalCenter: parent.verticalCenter
                        text: weekRow.modelData.weekday + " // " + weekRow.modelData.date
                        font.pixelSize: 10
                        color: weekRow.modelData.selected ? Colors.white : Colors.cyan
                    }
                    GohuText {
                        anchors.right: parent.right
                        anchors.rightMargin: 5
                        anchors.verticalCenter: parent.verticalCenter
                        text: weekRow.modelData.remaining + " OPEN"
                        font.pixelSize: 9
                        color: weekRow.modelData.remaining > 0 ? Colors.orange : Colors.cyan
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: weekRow.modelData.date !== ""
                        onClicked: planner.selectDate(weekRow.modelData.date)
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
        text: (planner.scheduleMode ? "SCHEDULE // " : "AGENDA // ") + planner.selectedDate
        color: Colors.magenta
        font.pixelSize: 11
        font.bold: true
    }
    ListView {
        id: agendaList
        visible: !planner.scheduleMode
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
    TaskPlannerSchedulePane {
        id: schedulePane
        anchors.top: agendaTitle.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: planner.scheduleMode
        todoSnapshot: planner.todoSnapshot
        todoStore: planner.todoStore
        selectedDate: planner.selectedDate
    }
    GohuText {
        anchors.centerIn: agendaList
        visible: !planner.scheduleMode && planner.calendar.available
                 && planner.calendar.agenda.length===0
        text: "NO TASKS ON SELECTED DATE"
        color: Colors.cyan
        font.pixelSize: 10
    }
}
