import QtQuick
import "../components"

// Shared inline date editor for both worldwide providers. No reader or I/O.
Column {
    id: dates
    property var feed: null
    property bool active: false
    property bool singleDay: false
    readonly property bool editable: active && !!feed && !!feed.selectedListing && !feed.loading
    spacing: 5
    Row {
        width: parent.width
        height: 27
        spacing: 6
        ActionButton {
            width: (parent.width-6)/2
            height: 26
            label: "DAY DATE"
            accentColor: Colors.cyan
            labelPixelSize: 9
            available: dates.editable
            selected: dates.singleDay
            onLeftClicked: {
                if (dates.feed.selectSingleDate(dates.feed.endDate)) dates.singleDay=true;
            }
        }
        ActionButton {
            width: (parent.width-6)/2
            height: 26
            label: "START / END"
            accentColor: Colors.cyan
            labelPixelSize: 9
            available: dates.editable
            selected: !dates.singleDay
            onLeftClicked: dates.singleDay=false
        }
    }
    GohuText {
        width: parent.width
        text: dates.singleDay ? "DAY DATE" : "START DATE"
        font.pixelSize: 9
        color: Colors.cyan
    }
    FinanceDateInput {
        width: parent.width
        value: dates.feed ? dates.feed.startDate : ""
        fallbackDate: dates.feed ? dates.feed.endDate : ""
        canEdit: dates.editable
        onValueEdited: function(value) {
            if (dates.singleDay) dates.feed.selectSingleDate(value);
            else dates.feed.selectStartDate(value);
        }
    }
    GohuText {
        width: parent.width
        visible: !dates.singleDay
        text: "END DATE"
        font.pixelSize: 9
        color: Colors.cyan
    }
    FinanceDateInput {
        width: parent.width
        visible: !dates.singleDay
        value: dates.feed ? dates.feed.endDate : ""
        fallbackDate: dates.feed ? dates.feed.startDate : ""
        canEdit: dates.editable
        onValueEdited: function(value) { dates.feed.selectEndDate(value); }
    }
    // A preset is a range, never silently reinterpret it as a day.
    Connections {
        target: dates.feed
        function onSelectedListingChanged() {
            if (!dates.feed || !dates.feed.selectedListing) dates.singleDay=false;
        }
        function onPresetDaysChanged() {
            if (dates.feed && dates.feed.presetDays>0) dates.singleDay=false;
        }
    }
    GohuText {
        width: parent.width
        text: dates.feed && dates.feed.validWindow
            ? "INCLUSIVE // MAX 180-DAY SPAN // MANUAL LOAD"
            : "INVALID WINDOW // 2000 OR LATER, NOT FUTURE, MAX 180-DAY SPAN"
        font.pixelSize: 9
        color: dates.feed && dates.feed.validWindow ? Colors.orange : Colors.red
        wrapMode: Text.WordWrap
    }
}
