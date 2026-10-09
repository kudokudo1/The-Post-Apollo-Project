import QtQuick
import qs.components

SectionFrame {
    id: root

    required property var fileService
    required property var hunkService
    required property var lineService
    property var historyService: null
    property var keyboardHost: null
    property string mode: "file"

    fillColor: Colors.dark
    borderWidth: 1
    borderColor: Colors.orange

    component ScopeButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property color accent: Colors.cyan

        signal triggered()

        height: 30
        opacity: enabledAction ? 1.0 : 0.30
        color:
            selectedAction || mouse.containsMouse
            ? Colors.black
            : Colors.dark
        border.width: selectedAction ? 2 : 1
        border.color: selectedAction ? Colors.orange : accent

        GohuText {
            anchors.centerIn: parent
            width: parent.width - 8
            horizontalAlignment: Text.AlignHCenter
            text: button.label
            font.pixelSize: 9
            color: button.accent
            elide: Text.ElideRight
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor
            onClicked: button.triggered()
        }
    }

    Row {
        id: modeRow

        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 8
        }

        height: 30
        spacing: 6

        ScopeButton {
            width: (parent.width - 12) / 3
            label: "FILE"
            accent: Colors.cyan
            selectedAction: root.mode === "file"
            enabledAction:
                !fileService.executionBusy
                && !hunkService.executionBusy
                && !lineService.executionBusy
            onTriggered: root.mode = "file"
        }

        ScopeButton {
            width: (parent.width - 12) / 3
            label: "HUNK"
            accent: Colors.orange
            selectedAction: root.mode === "hunk"
            enabledAction:
                !fileService.executionBusy
                && !hunkService.executionBusy
                && !lineService.executionBusy
            onTriggered: root.mode = "hunk"
        }

        ScopeButton {
            width: (parent.width - 12) / 3
            label: "LINE"
            accent: Colors.magenta
            selectedAction: root.mode === "line"
            enabledAction:
                !fileService.executionBusy
                && !hunkService.executionBusy
                && !lineService.executionBusy
            onTriggered: root.mode = "line"
        }
    }

    GitHistorySplitView {
        anchors {
            top: modeRow.bottom
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            topMargin: 7
            leftMargin: 8
            rightMargin: 8
            bottomMargin: 8
        }

        visible: root.mode === "file"

        splitService: root.fileService
        historyService: root.historyService
        keyboardHost: root.keyboardHost
    }

    GitHistorySplitHunkView {
        anchors {
            top: modeRow.bottom
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            topMargin: 7
            leftMargin: 8
            rightMargin: 8
            bottomMargin: 8
        }

        visible: root.mode === "hunk"

        hunkService: root.hunkService
        historyService: root.historyService
        keyboardHost: root.keyboardHost
    }

    GitHistorySplitLineView {
        anchors {
            top: modeRow.bottom
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            topMargin: 7
            leftMargin: 8
            rightMargin: 8
            bottomMargin: 8
        }

        visible: root.mode === "line"

        lineService: root.lineService
        historyService: root.historyService
        keyboardHost: root.keyboardHost
    }
}
