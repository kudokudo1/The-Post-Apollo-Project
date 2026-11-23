import QtQuick
import "../components"
import "tasks" as TaskFields
import "tasks/TaskDateSegments.js" as Segments

// Shared Post-Apollo month/day/year date editor.
//
// Uses the ACTUAL TASKS numeric arrow control and Gregorian arithmetic.
// Does not copy a spinbox, run a timer, store a date or mutate a domain record.
// The caller owns the ISO YYYY-MM-DD value and handles dateEdited.
// Empty dates remain empty until the user clicks TODAY or edits/steps a field.
// On first edit/step, an empty field uses a valid fallbackDate or today's date.
// Different consumers can choose local or UTC TODAY without adding a clock.
Item {
    id: picker

    property string dateValue: ""
    property string fallbackDate: ""
    property bool useUtcToday: false
    property bool canEdit: true
    property bool showToday: true
    property bool allowClear: true
    property string minDate: "0001-01-01"
    property string maxDate: "9999-12-31"

    signal dateEdited(string isoDate)

    implicitHeight: 26
    height: implicitHeight
    width: parent ? parent.width : 320

    function dateWithinBounds(value) {
        return !!Segments.parse(value)
            && !!Segments.parse(minDate)
            && !!Segments.parse(maxDate)
            && minDate <= maxDate
            && value >= minDate && value <= maxDate;
    }
    function todayDate() {
        const now = new Date();
        const year = useUtcToday ? now.getUTCFullYear() : now.getFullYear();
        const month = (useUtcToday ? now.getUTCMonth() : now.getMonth()) + 1;
        const day = useUtcToday ? now.getUTCDate() : now.getDate();
        return Segments.format({year: year, month: month, day: day});
    }
    function baseDate() {
        if(dateWithinBounds(dateValue))return dateValue;
        if(dateWithinBounds(fallbackDate))return fallbackDate;
        const today = todayDate();
        if(dateWithinBounds(today))return today;
        return dateWithinBounds(minDate) ? minDate : "";
    }
    function emitDate(candidate) {
        if(!canEdit||!dateWithinBounds(candidate))return false;
        if(candidate !== dateValue)dateEdited(candidate);
        return true;
    }
    function commitPart(part,value) {
        if(!canEdit)return false;
        const base = baseDate();
        if(!base)return false;
        const next = Segments.setPart(base,part,value);
        return next.accepted && emitDate(next.date);
    }
    function stepPart(part,direction) {
        if(!canEdit)return false;
        const base = baseDate();
        if(!base)return false;
        const next = Segments.step(base,part,direction);
        return next !== base && emitDate(next);
    }
    function setToday() {
        return emitDate(todayDate());
    }
    function clearDate() {
        if(!canEdit||!allowClear)return false;
        if(dateValue!=="")dateEdited("");
        return true;
    }
    function releaseFocus() {
        monthSegment.releaseFocus();
        daySegment.releaseFocus();
        yearSegment.releaseFocus();
    }

    Row {
        id: controls
        anchors.fill: parent
        spacing: 3
        readonly property int actionCount:
            (picker.showToday?1:0)+(picker.allowClear?1:0)
        readonly property real segmentSpace: Math.max(0,
            width - actionCount*49 - (2+actionCount)*spacing)

        TaskFields.TaskDateSegment {
            id: monthSegment
            width: controls.segmentSpace*0.29
            height: picker.height
            part: "month"
            placeholder: "MM"
            digitCount: 2
            displayValue: Segments.part(picker.dateValue,"month")
            canEdit: picker.canEdit
            onEditCommitted: function(part,value) {
                picker.commitPart(part,value);
            }
            onStepRequested: function(part,direction) {
                picker.stepPart(part,direction);
            }
        }
        TaskFields.TaskDateSegment {
            id: daySegment
            width: controls.segmentSpace*0.29
            height: picker.height
            part: "day"
            placeholder: "DD"
            digitCount: 2
            displayValue: Segments.part(picker.dateValue,"day")
            canEdit: picker.canEdit
            onEditCommitted: function(part,value) {
                picker.commitPart(part,value);
            }
            onStepRequested: function(part,direction) {
                picker.stepPart(part,direction);
            }
        }
        TaskFields.TaskDateSegment {
            id: yearSegment
            width: controls.segmentSpace*0.42
            height: picker.height
            part: "year"
            placeholder: "YYYY"
            digitCount: 4
            displayValue: Segments.part(picker.dateValue,"year")
            canEdit: picker.canEdit
            onEditCommitted: function(part,value) {
                picker.commitPart(part,value);
            }
            onStepRequested: function(part,direction) {
                picker.stepPart(part,direction);
            }
        }
        ActionButton {
            visible: picker.showToday
            width: visible?49:0
            height: picker.height
            label: "TODAY"
            labelPixelSize: 9
            accentColor: Colors.yellow
            available: picker.canEdit
            onLeftClicked: picker.setToday()
        }
        ActionButton {
            visible: picker.allowClear
            width: visible?49:0
            height: picker.height
            label: "CLEAR"
            labelPixelSize: 9
            accentColor: Colors.cyan
            available: picker.canEdit && picker.dateValue!==""
            onLeftClicked: picker.clearDate()
        }
    }
}
