import QtQuick
import "../../components"
import "../tasks/TaskPlannerPolicy.js" as Planner

// B9 local civil-date calendar presentation. The shared bridge already
// computes month cells from its existing clock; do not create another
// timer, event service, date calculation, or calendar data store here.
Item {
    id: calendarMini

    property var calendarSnapshot: null
    property var calendarBridge: null
    // Level 2 is a read-only projection over the existing TASKS store.
    property var todoSnapshot: null
    property string selectedView: "month"
    property string selectedTaskDate: ""
    // Stage 7C: use the space already assigned by H:1/H:2/H:3.
    // No new time source, calendar service, or event data.
    readonly property int densityLevel: height >= 300 ? 3
                                        : height >= 180 ? 2 : 1

    readonly property string calendarState:
        calendarSnapshot && calendarSnapshot.state
        ? String(calendarSnapshot.state) : "unavailable"
    readonly property bool calendarReady:
        calendarState === "ready"
        && calendarSnapshot !== null
        && Array.isArray(calendarSnapshot.weekdayLabels)
        && calendarSnapshot.weekdayLabels.length === 7
        && Array.isArray(calendarSnapshot.cells)
        && calendarSnapshot.weeks >= 4
        && calendarSnapshot.weeks <= 6
        && calendarSnapshot.cells.length === calendarSnapshot.weeks * 7
    readonly property var weekdayLabels:
        calendarReady ? calendarSnapshot.weekdayLabels : []
    readonly property var monthCells:
        calendarReady ? calendarSnapshot.cells : []
    readonly property int monthOffset:
        calendarBridge && typeof calendarBridge.calendarMonthOffset === "number"
        ? calendarBridge.calendarMonthOffset : 0
    readonly property int weekStart:
        calendarSnapshot && calendarSnapshot.weekStartsOn === 1 ? 1 : 0
    readonly property string taskMonthKey:
        calendarReady && typeof calendarSnapshot.month === "string"
        ? calendarSnapshot.month + "-01" : ""
    readonly property string taskTodayKey:
        calendarReady && typeof calendarSnapshot.today === "string"
        ? calendarSnapshot.today : ""
    readonly property string taskFocusDateKey: {
        if (!calendarReady)
            return "";
        if (Planner.parse(selectedTaskDate)
                && selectedTaskDate.slice(0, 7) === calendarSnapshot.month)
            return selectedTaskDate;
        return taskTodayKey.slice(0, 7) === calendarSnapshot.month
               ? taskTodayKey : taskMonthKey;
    }
    readonly property var taskView: Planner.view(
        todoSnapshot, taskMonthKey, taskFocusDateKey, taskTodayKey)
    // The mini exposes owner-provided projections, not full TASKS screens.
    readonly property bool agendaMode:
        densityLevel >= 2 && (selectedView === "agenda"
                              || selectedView === "week"
                              || selectedView === "day")
    readonly property var weekEntries:
        taskView && taskView.available
        ? Planner.weekDays(todoSnapshot, taskFocusDateKey, taskTodayKey) : []
    readonly property var agendaEntries:
        taskView && taskView.available ? taskView.agenda : []
    readonly property string statusLine:
        agendaMode
        ? (taskView.available
           ? "TASKS // LOCAL DUE DATES // READ ONLY"
           : "TASKS // " + String(taskView.state).toUpperCase())
        : calendarReady ? "CALENDAR // EVENTS NOT CONNECTED"
        : "CALENDAR // " + calendarState.toUpperCase()
          + (calendarSnapshot && calendarSnapshot.error
             ? " // " + String(calendarSnapshot.error) : "")

    function remainingTasksOn(dateKey) {
        if (!taskView || !taskView.available || !Array.isArray(taskView.days))
            return -1;
        for (let i = 0; i < taskView.days.length; ++i) {
            if (taskView.days[i].date === dateKey)
                return taskView.days[i].remaining;
        }
        return 0;
    }

    // A date tap selects only the Hub view, never edits a task or event.
    function selectTaskDate(dateKey) {
        if (densityLevel < 2 || !calendarReady || !Planner.parse(dateKey)
                || dateKey.slice(0, 7) !== calendarSnapshot.month)
            return;
        selectedTaskDate = dateKey;
    }

    // Reuse TASKS' civil-day arithmetic. Keep the visible month and selected
    // date aligned across month/year boundaries, without a new clock/store.
    function stepTaskDate(direction) {
        if (!calendarReady || !taskView.available || !calendarBridge
                || !Planner.parse(taskFocusDateKey)
                || (direction !== -1 && direction !== 1))
            return;
        const step = selectedView === "week" ? direction * 7 : direction;
        const next = Planner.moveDay(taskFocusDateKey, step);
        const from = Planner.parse(taskMonthKey);
        const to = Planner.parse(next);
        if (!from || !to || next === taskFocusDateKey)
            return;
        const delta = (to.year - from.year) * 12 + (to.month - from.month);
        const newOffset = monthOffset + delta;
        if (newOffset < -120 || newOffset > 120)
            return;
        selectedTaskDate = next;
        if (delta !== 0)
            calendarBridge.calendarMonthOffset = newOffset;
    }

    // These functions only run on an explicit button click. They alter the
    // bridge's view parameters, never the system clock or any calendar event.
    function moveMonth(direction) {
        if (!calendarReady || !calendarBridge)
            return;
        const next = monthOffset + direction;
        if (next < -120 || next > 120)
            return;
        calendarBridge.calendarMonthOffset = next;
        selectedTaskDate = "";
    }

    function showToday() {
        if (calendarBridge && monthOffset !== 0)
            calendarBridge.calendarMonthOffset = 0;
        selectedTaskDate = "";
    }

    function toggleWeekStart() {
        if (!calendarReady || !calendarBridge)
            return;
        calendarBridge.calendarWeekStartsOn = weekStart === 0 ? 1 : 0;
    }

    // H:1 remains compact. H:2/H:3 add bounded read-only views derived
    // from the existing TASKS snapshot; no new background activity.
    Row {
        id: viewSelector
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: calendarMini.densityLevel === 3 ? 29 : 25
        spacing: 4
        visible: calendarMini.densityLevel >= 2

        Repeater {
            model: ["MONTH", "WEEK", "DAY", "AGENDA"]
            ActionButton {
                required property string modelData
                width: Math.max(0, (viewSelector.width - 3 * viewSelector.spacing) / 4)
                height: viewSelector.height
                label: modelData
                labelPixelSize: 10
                selected: modelData.toLowerCase() === calendarMini.selectedView
                available: modelData === "MONTH"
                           ? calendarMini.calendarReady
                           : calendarMini.calendarReady && calendarMini.taskView.available
                trackLabelGlowLocally: true
                softGlowEnabled: false
                onLeftClicked: calendarMini.selectedView = modelData.toLowerCase()
            }
        }
    }

    Column {
        id: monthPane
        visible: !calendarMini.agendaMode
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: viewSelector.visible ? viewSelector.bottom : parent.top
        anchors.topMargin: viewSelector.visible ? 5 : 0
        spacing: calendarMini.densityLevel === 3 ? 7
                 : calendarMini.densityLevel === 2 ? 5 : 2

        Row {
            id: monthHeader
            width: parent.width
            height: calendarMini.densityLevel === 3 ? 32
                    : calendarMini.densityLevel === 2 ? 26 : 20
            spacing: 3

            ActionButton {
                width: 22
                height: parent.height
                label: "<"
                labelPixelSize: 12
                trackLabelGlowLocally: true
                softGlowEnabled: false
                available: calendarMini.calendarReady
                           && calendarMini.calendarBridge !== null
                           && calendarMini.monthOffset > -120
                onLeftClicked: calendarMini.moveMonth(-1)
            }

            GohuText {
                width: Math.max(20, monthHeader.width - 22 * 2
                                - 41 - 38 - 4 * monthHeader.spacing)
                height: parent.height
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: calendarMini.densityLevel === 3 ? 17
                                : calendarMini.densityLevel === 2 ? 14 : 11
                color: Colors.white
                elide: Text.ElideRight
                text: calendarMini.calendarReady
                      ? String(calendarMini.calendarSnapshot.monthLabel)
                      : "UNAVAILABLE"
            }

            ActionButton {
                width: 22
                height: parent.height
                label: ">"
                labelPixelSize: 12
                trackLabelGlowLocally: true
                softGlowEnabled: false
                available: calendarMini.calendarReady
                           && calendarMini.calendarBridge !== null
                           && calendarMini.monthOffset < 120
                onLeftClicked: calendarMini.moveMonth(1)
            }

            ActionButton {
                width: 41
                height: parent.height
                label: "TODAY"
                labelPixelSize: 9
                trackLabelGlowLocally: true
                softGlowEnabled: false
                available: calendarMini.calendarBridge !== null
                           && calendarMini.monthOffset !== 0
                onLeftClicked: calendarMini.showToday()
            }

            ActionButton {
                width: 38
                height: parent.height
                label: calendarMini.weekStart === 0 ? "SUN" : "MON"
                labelPixelSize: 10
                trackLabelGlowLocally: true
                softGlowEnabled: false
                available: calendarMini.calendarReady
                           && calendarMini.calendarBridge !== null
                onLeftClicked: calendarMini.toggleWeekStart()
            }
        }

        Grid {
            id: weekdayGrid
            width: parent.width
            height: calendarMini.densityLevel === 3 ? 21
                    : calendarMini.densityLevel === 2 ? 17 : 11
            columns: 7
            columnSpacing: 1
            Repeater {
                model: calendarMini.weekdayLabels
                delegate: GohuText {
                    required property var modelData
                    width: Math.max(1, (weekdayGrid.width
                                       - weekdayGrid.columnSpacing * 6) / 7)
                    height: weekdayGrid.height
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: calendarMini.densityLevel === 3 ? 14
                                    : calendarMini.densityLevel === 2 ? 12 : 9
                    color: Colors.cyan
                    text: String(modelData)
                }
            }
        }

        Grid {
            id: dayGrid
            width: parent.width
            height: Math.max(0, parent.height - monthHeader.height
                             - weekdayGrid.height - 2 * parent.spacing)
            visible: calendarMini.calendarReady
            columns: 7
            columnSpacing: 1
            rowSpacing: 1
            readonly property real dayHeight:
                calendarMini.calendarReady
                ? Math.max(1, (height - (calendarMini.calendarSnapshot.weeks - 1)
                               * rowSpacing) / calendarMini.calendarSnapshot.weeks)
                : 1

            Repeater {
                model: calendarMini.monthCells
                delegate: Rectangle {
                    id: dayCell
                    required property var modelData
                    readonly property bool today: modelData.isToday === true
                    readonly property bool currentMonth: modelData.inMonth === true
                    width: Math.max(1, (dayGrid.width - dayGrid.columnSpacing * 6) / 7)
                    height: dayGrid.dayHeight
                    radius: 0
                    color: today ? Colors.magenta : "transparent"
                    readonly property bool selectedTaskDay:
                        calendarMini.densityLevel >= 2
                        && calendarMini.taskView.available
                        && currentMonth
                        && modelData.date === calendarMini.taskFocusDateKey
                    border.width: today || selectedTaskDay ? 1 : 0
                    border.color: today ? Colors.orange : Colors.magenta

                    TapHandler {
                        enabled: calendarMini.densityLevel >= 2
                                 && dayCell.currentMonth
                        acceptedButtons: Qt.LeftButton
                        onTapped: calendarMini.selectTaskDate(dayCell.modelData.date)
                    }

                    // Orange marks TASKS due dates, never appointment events.
                    Rectangle {
                        anchors.right: parent.right
                        anchors.rightMargin: 2
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 2
                        width: 5
                        height: 5
                        radius: 0
                        color: Colors.orange
                        visible: calendarMini.densityLevel >= 2
                                 && calendarMini.remainingTasksOn(
                                     dayCell.modelData.date) > 0
                    }

                    GohuText {
                        anchors.fill: parent
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        // Preserve original compact six-week typography;
                        // taller layouts spend their extra room on legibility.
                        font.pixelSize: calendarMini.densityLevel === 3 ? 17
                                        : calendarMini.densityLevel === 2 ? 13
                                        : calendarMini.calendarSnapshot.weeks === 6 ? 9 : 10
                        color: dayCell.today ? Colors.black
                               : dayCell.currentMonth ? Colors.white : Colors.cyan
                        opacity: dayCell.today ? 1.0
                                 : dayCell.currentMonth ? 1.0 : 0.42
                        text: String(dayCell.modelData.day)
                    }
                }
            }
        }
    }

    Item {
        id: agendaPane
        visible: calendarMini.agendaMode
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: viewSelector.bottom
        anchors.topMargin: 6

        Column {
            anchors.fill: parent
            spacing: 6

            // WEEK advances seven days; DAY advances one. AGENDA retains
            // its original fixed selected-day overview.
            Row {
                id: dateNavigation
                width: parent.width
                height: 27
                spacing: 5
                visible: calendarMini.selectedView === "week"
                         || calendarMini.selectedView === "day"

                ActionButton {
                    width: 29
                    height: parent.height
                    label: "‹"
                    labelPixelSize: 17
                    available: calendarMini.taskView.available
                    onLeftClicked: calendarMini.stepTaskDate(-1)
                }
                GohuText {
                    width: Math.max(0, dateNavigation.width - 29 * 2 - 74
                                    - 3 * dateNavigation.spacing)
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    font.pixelSize: 11
                    color: Colors.cyan
                    text: calendarMini.selectedView.toUpperCase() + " // "
                          + calendarMini.taskFocusDateKey
                }
                ActionButton {
                    width: 29
                    height: parent.height
                    label: "›"
                    labelPixelSize: 17
                    available: calendarMini.taskView.available
                    onLeftClicked: calendarMini.stepTaskDate(1)
                }
                ActionButton {
                    width: 74
                    height: parent.height
                    label: "TODAY"
                    available: calendarMini.calendarReady
                    onLeftClicked: calendarMini.showToday()
                }
            }

            // Existing TASKS Policy returns Monday-first rows. The local
            // month view separately preserves its SUN/MON toggle.
            Row {
                id: weekStrip
                width: parent.width
                height: calendarMini.densityLevel === 3 ? 77 : 61
                spacing: 3
                visible: calendarMini.selectedView === "week"
                         && calendarMini.weekEntries.length === 7

                Repeater {
                    model: calendarMini.weekEntries
                    delegate: Rectangle {
                        id: weekDay
                        required property var modelData
                        width: Math.max(1, (weekStrip.width - 6 * weekStrip.spacing) / 7)
                        height: weekStrip.height
                        radius: 0
                        color: modelData.selected ? Colors.dark : "transparent"
                        border.width: modelData.selected || modelData.today ? 1 : 0
                        border.color: modelData.today ? Colors.orange : Colors.magenta

                        Column {
                            anchors.fill: parent
                            anchors.margins: 2
                            spacing: 1
                            GohuText {
                                width: parent.width
                                height: 16
                                font.pixelSize: 10
                                horizontalAlignment: Text.AlignHCenter
                                color: Colors.cyan
                                text: weekDay.modelData.weekday
                            }
                            GohuText {
                                width: parent.width
                                height: 22
                                font.pixelSize: 16
                                horizontalAlignment: Text.AlignHCenter
                                color: Colors.white
                                text: String(weekDay.modelData.day)
                            }
                            GohuText {
                                width: parent.width
                                height: 15
                                font.pixelSize: 9
                                horizontalAlignment: Text.AlignHCenter
                                color: weekDay.modelData.remaining > 0
                                       ? Colors.orange : Colors.cyan
                                text: weekDay.modelData.remaining + " OPEN"
                            }
                        }
                        TapHandler {
                            acceptedButtons: Qt.LeftButton
                            enabled: calendarMini.taskView.available
                                     && weekDay.modelData.date.length > 0
                            onTapped: calendarMini.selectedTaskDate = weekDay.modelData.date
                        }
                    }
                }
            }

            GohuText {
                width: parent.width
                height: 24
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: calendarMini.densityLevel === 3 ? 17 : 13
                color: Colors.magenta
                elide: Text.ElideRight
                text: "TASKS // " + calendarMini.taskFocusDateKey
            }
            GohuText {
                width: parent.width
                height: 19
                font.pixelSize: 11
                color: Colors.cyan
                text: calendarMini.taskView.available
                      ? calendarMini.agendaEntries.length + " DATED TASKS"
                      : "TASK STORAGE // " + String(
                          calendarMini.taskView.state).toUpperCase()
            }
            ListView {
                id: agendaList
                width: parent.width
                height: Math.max(0, agendaPane.height - 24 - 19 - 12
                                 - (dateNavigation.visible
                                    ? dateNavigation.height + 6 : 0)
                                 - (weekStrip.visible ? weekStrip.height + 6 : 0))
                model: calendarMini.agendaEntries
                clip: true
                spacing: 3
                boundsBehavior: Flickable.StopAtBounds
                delegate: Rectangle {
                    required property var modelData
                    width: agendaList.width
                    height: calendarMini.selectedView === "day" ? 47 : 29
                    radius: 0
                    color: "transparent"
                    GohuText {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        height: calendarMini.selectedView === "day" ? 26 : 29
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: parent.modelData.done ? Colors.cyan : Colors.white
                        text: (parent.modelData.done ? "DONE // " : "OPEN // ")
                              + parent.modelData.title
                    }
                    GohuText {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 17
                        visible: calendarMini.selectedView === "day"
                        font.pixelSize: 10
                        color: Colors.orange
                        elide: Text.ElideRight
                        text: "PRIORITY // " + String(parent.modelData.priority)
                              + "  //  PROJECT " + String(parent.modelData.projectId || "NONE")
                    }
                }
            }
        }

        GohuText {
            anchors.centerIn: parent
            width: parent.width
            height: 22
            visible: calendarMini.taskView.available
                     && calendarMini.agendaEntries.length === 0
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            color: Colors.orange
            text: "NO TASKS DUE ON SELECTED DATE"
        }
    }

    GohuText {
        anchors.centerIn: parent
        width: parent.width
        height: 18
        visible: !calendarMini.calendarReady
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: 11
        color: Colors.orange
        text: "CALENDAR UNAVAILABLE"
    }
}
