import QtQuick
import qs.components

Rectangle {
    id: root

    required property var chartService

    property string scopeFilter: "ALL"
    property int selectedIndex: -1

    readonly property var suggestions: {
        const rows = [];
        const patient = Array.isArray(chartService.patientSuggestions)
            ? chartService.patientSuggestions : [];
        const room = Array.isArray(chartService.roomSuggestions)
            ? chartService.roomSuggestions : [];

        if (scopeFilter === "ALL" || scopeFilter === "ROOM") {
            for (let i = 0; i < room.length; ++i)
                rows.push(room[i]);
        }

        if (scopeFilter === "ALL" || scopeFilter === "PATIENT") {
            for (let i = 0; i < patient.length; ++i)
                rows.push(patient[i]);
        }

        rows.sort(function(a, b) {
            const priorityDelta =
                Number((b || {}).priority || 0)
                - Number((a || {}).priority || 0);
            if (priorityDelta !== 0)
                return priorityDelta;

            return Number((b || {}).id || 0)
                - Number((a || {}).id || 0);
        });

        return rows;
    }

    readonly property var selectedSuggestion:
        selectedIndex >= 0
        && selectedIndex < suggestions.length
        ? suggestions[selectedIndex]
        : null

    signal closeRequested()

    color: Colors.dark
    border.width: 1
    border.color: Colors.orange

    function resetSelection() {
        selectedIndex = suggestions.length > 0 ? 0 : -1;
    }

    onScopeFilterChanged: resetSelection()
    onSuggestionsChanged: {
        if (suggestions.length === 0)
            selectedIndex = -1;
        else if (selectedIndex < 0 || selectedIndex >= suggestions.length)
            selectedIndex = 0;
    }

    Connections {
        target: chartService

        function onSuggestionDecision(operation, result) {
            root.resetSelection();
        }
    }

    component SuggestionButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool selectedAction: false

        signal triggered()

        height: 28
        opacity: enabledAction ? 1.0 : 0.35
        color:
            selectedAction || mouse.pressed
            ? accent
            : Colors.black
        border.width:
            selectedAction || mouse.containsMouse
            ? 2 : 1
        border.color: accent

        GohuText {
            anchors.centerIn: parent
            width: parent.width - 6
            text: button.label
            font.pixelSize: 8
            color:
                button.selectedAction || mouse.pressed
                ? Colors.black
                : button.accent
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: button.triggered()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 8

        Rectangle {
            width: parent.width
            height: 54
            color: Colors.black
            border.width: 1
            border.color: Colors.orange

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 7

                Column {
                    width: parent.width - 360
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    GohuText {
                        width: parent.width
                        text: "CHART MEMORY SUGGESTIONS // OPERATOR REVIEW"
                        font.pixelSize: 12
                        color: Colors.orange
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            String(root.suggestions.length)
                            + " PENDING // DOCTORS PROPOSE // OPERATOR PROMOTES"
                        font.pixelSize: 8
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                Repeater {
                    model: ["ALL", "ROOM", "PATIENT"]

                    SuggestionButton {
                        required property string modelData
                        width: 70
                        label: modelData
                        selectedAction: root.scopeFilter === modelData
                        accent:
                            modelData === "ROOM"
                            ? Colors.cyan
                            : modelData === "PATIENT"
                            ? Colors.green
                            : Colors.orange
                        onTriggered: root.scopeFilter = modelData
                    }
                }

                SuggestionButton {
                    width: 70
                    label:
                        chartService.loading
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.green
                    enabledAction:
                        !chartService.loading
                        && !chartService.suggestionWriting
                    onTriggered: chartService.refreshSuggestions()
                }

                SuggestionButton {
                    width: 34
                    label: "X"
                    accent: Colors.red
                    onTriggered: root.closeRequested()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 62
            spacing: 8

            Rectangle {
                width: Math.max(300, parent.width * 0.42)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                ListView {
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    spacing: 4
                    model: root.suggestions

                    delegate: Rectangle {
                        required property var modelData
                        required property int index

                        width: ListView.view.width
                        height: 78
                        color:
                            root.selectedIndex === index
                            ? Colors.dark
                            : Colors.black
                        border.width:
                            root.selectedIndex === index
                            ? 2 : 1
                        border.color:
                            String(modelData.scope || "") === "PATIENT"
                            ? Colors.green
                            : Colors.cyan

                        Column {
                            anchors {
                                fill: parent
                                margins: 6
                            }
                            spacing: 2

                            GohuText {
                                width: parent.width
                                text:
                                    String(modelData.scope || "ROOM")
                                    + " // P"
                                    + String(modelData.priority || 0)
                                    + " // "
                                    + String(modelData.kind || "NOTE")
                                    + " // #"
                                    + String(modelData.id || "?")
                                font.pixelSize: 8
                                color:
                                    String(modelData.scope || "") === "PATIENT"
                                    ? Colors.green
                                    : Colors.cyan
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        modelData.title
                                        || "DOCTOR MEMORY SUGGESTION"
                                    )
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    "DOCTOR "
                                    + String(modelData.doctorId || "-")
                                    + " // "
                                    + String(modelData.providerId || "-")
                                font.pixelSize: 8
                                color: Colors.orange
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedIndex = index
                        }
                    }

                    GohuText {
                        anchors.centerIn: parent
                        visible:
                            !chartService.loading
                            && root.suggestions.length === 0
                        text: "NO PENDING MEMORY SUGGESTIONS"
                        font.pixelSize: 10
                        color: Colors.blue
                    }
                }
            }

            Rectangle {
                width: parent.width
                    - Math.max(300, parent.width * 0.42)
                    - parent.spacing
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color:
                    root.selectedSuggestion
                    ? Colors.orange
                    : Colors.blue

                Column {
                    anchors {
                        fill: parent
                        margins: 10
                    }
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedSuggestion
                            ? (
                                "PROPOSAL // #"
                                + String(root.selectedSuggestion.id)
                                + " // "
                                + String(root.selectedSuggestion.scope)
                                + " CHART"
                              )
                            : "NO SUGGESTION SELECTED"
                        font.pixelSize: 12
                        color: Colors.orange
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        visible: root.selectedSuggestion !== null
                        text:
                            root.selectedSuggestion
                            ? (
                                "P"
                                + String(root.selectedSuggestion.priority || 0)
                                + " // "
                                + String(root.selectedSuggestion.kind || "NOTE")
                                + " // "
                                + String(root.selectedSuggestion.title || "")
                              )
                            : ""
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        visible: root.selectedSuggestion !== null
                        text:
                            root.selectedSuggestion
                            ? (
                                "PROVENANCE // ROOM "
                                + String(
                                    root.selectedSuggestion.sourceRoomId
                                    || "-"
                                  )
                                + " // SESSION "
                                + String(
                                    root.selectedSuggestion.sourceSessionId
                                    || "-"
                                  )
                                + " // MESSAGE #"
                                + String(
                                    root.selectedSuggestion.sourceMessageId
                                    || "-"
                                  )
                              )
                            : ""
                        font.pixelSize: 8
                        color: Colors.blue
                        elide: Text.ElideMiddle
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.orange
                        opacity: 0.4
                    }

                    Flickable {
                        width: parent.width
                        height: Math.max(140, parent.height - 170)
                        clip: true
                        contentWidth: width
                        contentHeight: proposalBody.implicitHeight + 8

                        GohuText {
                            id: proposalBody
                            width: parent.width
                            text:
                                root.selectedSuggestion
                                ? String(root.selectedSuggestion.body || "")
                                : (
                                    "Select a Doctor proposal to review. "
                                    + "PROMOTE creates a normal durable Chart "
                                    + "entry. REJECT preserves the proposal "
                                    + "history without changing the Chart."
                                  )
                            textFormat: Text.MarkdownText
                            font.pixelSize: 10
                            color: Colors.white
                            wrapMode: Text.Wrap
                        }
                    }

                    Row {
                        width: parent.width
                        height: 32
                        spacing: 8

                        SuggestionButton {
                            width: (parent.width - parent.spacing) / 2
                            height: parent.height
                            label:
                                chartService.suggestionWriting
                                && chartService.pendingSuggestionOperation
                                   === "PROMOTE"
                                ? "PROMOTING…"
                                : "PROMOTE TO CHART"
                            accent: Colors.green
                            enabledAction:
                                root.selectedSuggestion !== null
                                && !chartService.suggestionWriting
                            onTriggered:
                                chartService.promoteSuggestion(
                                    root.selectedSuggestion.id
                                )
                        }

                        SuggestionButton {
                            width: (parent.width - parent.spacing) / 2
                            height: parent.height
                            label:
                                chartService.suggestionWriting
                                && chartService.pendingSuggestionOperation
                                   === "REJECT"
                                ? "REJECTING…"
                                : "REJECT"
                            accent: Colors.red
                            enabledAction:
                                root.selectedSuggestion !== null
                                && !chartService.suggestionWriting
                            onTriggered:
                                chartService.rejectSuggestion(
                                    root.selectedSuggestion.id,
                                    "Rejected by Hospital operator"
                                )
                        }
                    }

                    GohuText {
                        width: parent.width
                        visible: chartService.lastError.length > 0
                        text: chartService.lastError
                        font.pixelSize: 8
                        color: Colors.red
                        wrapMode: Text.Wrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
