import QtQuick
import "../components"
import "../services/time/AlarmManagerPolicy.js" as Policy

// Inline ALARM date selection. No external window, storage, timer or actuation.
// Choosing a day edits the existing text field; SAVE / PAUSE remains explicit.
Item {
    id: picker
    visible: false
    focus: visible
    clip: true

    signal dateChosen(string target, string dateKey)
    property string target: "once"
    property string selectedDate: ""
    property int alarmHour: 0
    property int alarmMinute: 0
    property int viewYear: new Date().getFullYear()
    property int viewMonth: new Date().getMonth()
    readonly property var monthNames: ["JANUARY", "FEBRUARY", "MARCH", "APRIL",
        "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER",
        "NOVEMBER", "DECEMBER"]
    readonly property var calendarCells: {
        const firstWeekday = new Date(viewYear, viewMonth, 1, 12).getDay();
        const cells = [];
        for (let i = 0; i < 42; i++) {
            // Local noon avoids turning calendar days into 24-hour DST math.
            const day = new Date(viewYear, viewMonth, 1 + i - firstWeekday, 12);
            cells.push({
                dateKey: Policy.dayKey(day.getTime()),
                day: day.getDate(),
                inMonth: day.getMonth() === viewMonth
                    && day.getFullYear() === viewYear
            });
        }
        return cells;
    }
    readonly property int dayHeight: Math.max(13, Math.min(23,
        Math.floor((calendarPanel.height - 126) / 6)))

    function openFor(kind, proposedDate, hour, minute) {
        if (kind !== "once" && kind !== "pause") return false;
        const initial = Policy.validDate(proposedDate, false)
            ? proposedDate : Policy.dayKey(Date.now());
        if (!Policy.validDate(initial, false)) return false;
        target = kind;
        selectedDate = initial;
        alarmHour = hour;
        alarmMinute = minute;
        viewYear = Number(initial.slice(0, 4));
        viewMonth = Number(initial.slice(5, 7)) - 1;
        visible = true;
        return true;
    }
    function dismiss() { visible = false; }
    function shiftMonth(delta) {
        if (delta !== 1 && delta !== -1) return;
        const next = new Date(viewYear, viewMonth + delta, 1, 12);
        if (next.getFullYear() < 1970 || next.getFullYear() > 9999) return;
        viewYear = next.getFullYear();
        viewMonth = next.getMonth();
    }
    function maySelect(key) {
        if (!Policy.validDate(key, false)) return false;
        const now = Date.now();
        if (target === "pause") return key > Policy.dayKey(now);
        if (target !== "once"
                || !Number.isInteger(alarmHour) || alarmHour < 0 || alarmHour > 23
                || !Number.isInteger(alarmMinute) || alarmMinute < 0
                || alarmMinute > 59) return false;
        return Policy.dayAt(key, alarmHour, alarmMinute) > now;
    }
    function chooseDay(key) {
        // Revalidate when clicked: the minute may have elapsed since opening.
        if (!maySelect(key)) return false;
        dateChosen(target, key);
        dismiss();
        return true;
    }
    Keys.onEscapePressed: dismiss()

    Rectangle {
        anchors.fill: parent
        color: Colors.black
        opacity: 0.77
        MouseArea {
            anchors.fill: parent
            onClicked: picker.dismiss()
        }
    }
    Rectangle {
        id: calendarPanel
        width: Math.max(0, Math.min(340, picker.width - 8))
        height: Math.max(0, Math.min(266, picker.height - 8))
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.max(0, picker.height - height - 4)
        color: Colors.black
        border.width: 2
        border.color: Colors.magenta
        clip: true
        Column {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 4
            Row {
                id: monthRail
                width: parent.width
                height: 28
                spacing: 4
                ActionButton {
                    width: 41
                    height: parent.height
                    label: "◀"
                    labelPixelSize: 11
                    accentColor: Colors.cyan
                    onLeftClicked: picker.shiftMonth(-1)
                }
                GohuText {
                    width: Math.max(0, monthRail.width - 82 - 2 * monthRail.spacing)
                    height: parent.height
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: picker.monthNames[picker.viewMonth] + " " + picker.viewYear
                    color: Colors.white
                    font.pixelSize: 12
                }
                ActionButton {
                    width: 41
                    height: parent.height
                    label: "▶"
                    labelPixelSize: 11
                    accentColor: Colors.cyan
                    onLeftClicked: picker.shiftMonth(1)
                }
            }
            Row {
                width: parent.width
                height: 18
                spacing: 2
                Repeater {
                    model: ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
                    delegate: GohuText {
                        width: (calendarPanel.width - 12 - 6 * 2) / 7
                        height: 18
                        text: modelData
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                }
            }
            Grid {
                id: dayGrid
                width: parent.width
                columns: 7
                rowSpacing: 2
                columnSpacing: 2
                Repeater {
                    model: picker.calendarCells
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.max(0, (dayGrid.width - 12) / 7)
                        height: picker.dayHeight
                        label: modelData.inMonth ? String(modelData.day) : ""
                        labelPixelSize: 10
                        accentColor: Colors.cyan
                        selected: modelData.inMonth
                            && modelData.dateKey === picker.selectedDate
                        available: modelData.inMonth && picker.maySelect(modelData.dateKey)
                        onLeftClicked: picker.chooseDay(modelData.dateKey)
                    }
                }
            }
            GohuText {
                width: parent.width
                height: 16
                text: picker.target === "pause" ? "PAUSE // FUTURE DATE ONLY"
                    : "ONE TIME // FUTURE ALARM TIME ONLY"
                horizontalAlignment: Text.AlignHCenter
                color: Colors.white
                font.pixelSize: 9
            }
            ActionButton {
                width: parent.width
                height: 22
                label: "CANCEL // KEEP EXISTING DATE"
                labelPixelSize: 10
                accentColor: Colors.red
                onLeftClicked: picker.dismiss()
            }
        }
    }
}
