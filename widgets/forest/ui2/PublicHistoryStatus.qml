import QtQuick

// Isolated public fixture presentation. Not a runtime wire consumer.
// No arbitrary host/error text is rendered; no controls dispatch an action.
Item {
    id: root
    property bool fixtureVisible: false
    property string historyState: "CLOSED"
    property string historyReason: ""
    property color statusColor: "#ED981A"
    property string statusFontFamily: "GohuFont 11 Nerd Font Mono"
    readonly property bool sendEnabled: false
    readonly property bool stopEnabled: false
    readonly property bool sourceAuthenticated: false
    readonly property bool permissionGranted: false

    readonly property string statusText: !fixtureVisible ? "" : statusFor(historyState, historyReason)
    readonly property string executionText: fixtureVisible
        ? "PUBLIC FIXTURE // SEND / STOP LOCKED" : ""

    function statusFor(state, reason) {
        switch (state) {
        case "CLOSED": return "HISTORY NOT OPEN";
        case "PENDING": return "HISTORY PAGE PENDING";
        case "PARTIAL": return "PARTIAL HISTORY // NEXT PAGE AVAILABLE";
        case "COMPLETE": return "HISTORY SNAPSHOT COMPLETE";
        case "UNAVAILABLE":
            if (reason === "DISPLAY_LIMIT")
                return "HISTORY DISPLAY LIMIT // SNAPSHOT CLEARED";
            if (reason === "INVALID_OR_EXHAUSTED_REQUEST")
                return "HISTORY REQUEST REFUSED // NEW VIEW REQUIRED";
            return "HISTORY UNAVAILABLE // OPEN AGAIN";
        default: return "HISTORY UNAVAILABLE";
        }
    }

    visible: fixtureVisible
    implicitWidth: 240
    implicitHeight: labels.implicitHeight
    clip: true

    Column {
        id: labels
        width: parent.width
        spacing: 2

        Text {
            width: parent.width
            text: root.executionText
            textFormat: Text.PlainText
            color: root.statusColor
            font.family: root.statusFontFamily
            font.pixelSize: 10
            elide: Text.ElideRight
        }

        Text {
            width: parent.width
            text: root.statusText
            textFormat: Text.PlainText
            color: root.statusColor
            font.family: root.statusFontFamily
            font.pixelSize: 10
            elide: Text.ElideRight
        }
    }
}
