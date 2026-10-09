import QtQuick
import qs.components

// Readable operation-journal surface. Mutations remain owned by the recovery
// service; this view only previews and explicitly requests guarded Undo.
Item {
    id: root

    property var operationJournal: null
    property var recoveryService: null
    property var keyboardHost: null
    property int selectedIndex: 0
    property string statusText: ""

    readonly property var entries:
        operationJournal
        ? operationJournal.repositoryEntries
        : []
    readonly property var selectedRecord:
        entries.length > 0
        ? entries[Math.min(selectedIndex, entries.length - 1)]
        : null
    readonly property var selectedPreview:
        recoveryService && selectedRecord
        ? recoveryService.preview(selectedRecord)
        : ({
            allowed: false,
            strategy: "REFUSE",
            reason: "NO OPERATION SELECTED"
        })

    function shortSha(value) {
        const text = String(value || "");
        return text ? text.slice(0, 12) : "—";
    }

    function refreshSelection() {
        if (entries.length === 0)
            selectedIndex = 0;
        else if (selectedIndex >= entries.length)
            selectedIndex = entries.length - 1;
    }

    Connections {
        target: operationJournal
        ignoreUnknownSignals: true

        function onOperationStarted(operationId, record) {
            root.selectedIndex = 0;
        }

        function onOperationFinished(operationId, success, record) {
            root.selectedIndex = 0;
        }
    }

    Connections {
        target: recoveryService
        ignoreUnknownSignals: true

        function onRecoveryStarted(operationId) {
            root.statusText = "UNDO // RUNNING";
        }

        function onRecoveryFinished(operationId, success, detail) {
            root.statusText =
                (success ? "UNDO // COMPLETE // " : "UNDO // REFUSED // ")
                + String(detail || "");
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            width: parent.width
            height: 54
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta

            Row {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 10

                Column {
                    width: parent.width - 200
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3

                    GohuText {
                        text: "OPERATIONS // REPOSITORY TIME"
                        font.pixelSize: 12
                        color: Colors.magenta
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.entries.length
                            + " RECORDED // "
                            + (
                                root.selectedRecord
                                ? String(root.selectedRecord.kind || "UNKNOWN")
                                : "NO OPERATION"
                              )
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                Rectangle {
                    width: 190
                    height: 36
                    anchors.verticalCenter: parent.verticalCenter
                    color: Colors.black
                    border.width: 1
                    border.color:
                        root.selectedPreview.allowed
                        ? Colors.orange
                        : Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        width: parent.width - 12
                        horizontalAlignment: Text.AlignHCenter
                        text:
                            root.selectedPreview.allowed
                            ? "UNDO READY // "
                                + String(root.selectedPreview.strategy || "")
                            : "UNDO GUARDED"
                        font.pixelSize: 8
                        color:
                            root.selectedPreview.allowed
                            ? Colors.orange
                            : Colors.cyan
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 116
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.46)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                ListView {
                    id: operationList

                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    spacing: 4
                    model: root.entries
                    currentIndex: root.selectedIndex

                    delegate: Rectangle {
                        required property int index
                        required property var modelData

                        width: operationList.width
                        height: 66
                        color:
                            root.selectedIndex === index
                            ? Colors.black
                            : Colors.dark
                        border.width: 1
                        border.color:
                            root.selectedIndex === index
                            ? Colors.orange
                            : Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 3

                            Row {
                                width: parent.width

                                GohuText {
                                    width: parent.width - 92
                                    text: String(modelData.kind || "UNKNOWN")
                                    font.pixelSize: 9
                                    color:
                                        root.selectedIndex === index
                                        ? Colors.orange
                                        : Colors.white
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: 92
                                    text: String(modelData.status || "")
                                    horizontalAlignment: Text.AlignRight
                                    font.pixelSize: 8
                                    color:
                                        String(modelData.status || "") === "COMPLETE"
                                        ? Colors.cyan
                                        : Colors.red
                                }
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.shortSha((modelData.before || {}).head)
                                    + "  →  "
                                    + root.shortSha((modelData.after || {}).head)
                                font.pixelSize: 9
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(modelData.startedAt || "")
                                    + " // "
                                    + String(modelData.undoState || "NOT_IMPLEMENTED")
                                font.pixelSize: 8
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.selectedIndex = index;
                                operationList.currentIndex = index;
                            }
                        }
                    }

                    onCountChanged: root.refreshSelection()
                }
            }

            SectionFrame {
                width: parent.width - operationList.parent.width - 8
                height: parent.height
                fillColor: Colors.dark
                borderWidth: 1
                borderColor: Colors.magenta
                inset: 9

                Column {
                    anchors.fill: parent
                    spacing: 8

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedRecord
                            ? String(root.selectedRecord.kind || "UNKNOWN")
                            : "NO OPERATION SELECTED"
                        font.pixelSize: 12
                        color: Colors.orange
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedRecord
                            ? (
                                "STATUS "
                                + String(root.selectedRecord.status || "")
                                + " // RECOVERY "
                                + String(root.selectedRecord.recoveryClass || "")
                                + " // UNDO "
                                + String(root.selectedRecord.undoState || "")
                              )
                            : "—"
                        font.pixelSize: 9
                        color: Colors.cyan
                        wrapMode: Text.Wrap
                    }

                    SectionFrame {
                        width: parent.width
                        height: 72
                        fillColor: Colors.black
                        borderWidth: 1
                        borderColor: Colors.cyan
                        inset: 7

                        Column {
                            anchors.fill: parent
                            spacing: 4

                            GohuText {
                                text: "BEFORE → AFTER"
                                font.pixelSize: 9
                                color: Colors.magenta
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.selectedRecord
                                    ? (
                                        String((root.selectedRecord.before || {}).branch || "DETACHED")
                                        + " @ "
                                        + root.shortSha((root.selectedRecord.before || {}).head)
                                        + "  →  "
                                        + String((root.selectedRecord.after || {}).branch || "DETACHED")
                                        + " @ "
                                        + root.shortSha((root.selectedRecord.after || {}).head)
                                      )
                                    : "—"
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideMiddle
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.selectedRecord
                                    ? String(root.selectedRecord.detail || "")
                                    : ""
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 88
                        color: Colors.black
                        border.width: 1
                        border.color:
                            root.selectedPreview.allowed
                            ? Colors.orange
                            : Colors.red

                        Column {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 4

                            GohuText {
                                text:
                                    root.selectedPreview.allowed
                                    ? "UNDO PREVIEW"
                                    : "UNDO REFUSED"
                                font.pixelSize: 9
                                color:
                                    root.selectedPreview.allowed
                                    ? Colors.orange
                                    : Colors.red
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.selectedPreview.allowed
                                    ? String(root.selectedPreview.summary || "")
                                    : String(root.selectedPreview.reason || "")
                                font.pixelSize: 9
                                color: Colors.white
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 304)
                    }

                    Rectangle {
                        id: undoButton

                        width: parent.width
                        height: 42
                        color:
                            undoMouse.pressed
                            ? Colors.orange
                            : undoMouse.containsMouse
                            ? Colors.dark
                            : Colors.black
                        border.width: 1
                        border.color:
                            root.selectedPreview.allowed
                            && !root.recoveryService.busy
                            ? Colors.orange
                            : Colors.cyan
                        opacity:
                            root.selectedPreview.allowed
                            && !root.recoveryService.busy
                            ? 1.0
                            : 0.38

                        GohuText {
                            anchors.centerIn: parent
                            text:
                                root.recoveryService && root.recoveryService.busy
                                ? "UNDO // RUNNING"
                                : "EXECUTE GUARDED UNDO"
                            font.pixelSize: 10
                            color: Colors.orange
                        }

                        MouseArea {
                            id: undoMouse
                            anchors.fill: parent
                            enabled:
                                !!root.recoveryService
                                && !!root.selectedRecord
                                && root.selectedPreview.allowed
                                && !root.recoveryService.busy
                            hoverEnabled: true
                            cursorShape:
                                enabled
                                ? Qt.PointingHandCursor
                                : Qt.ArrowCursor

                            onClicked: {
                                root.statusText = "UNDO // ARMING";
                                root.recoveryService.execute(
                                    String(root.selectedRecord.id || ""),
                                    root.selectedRecord
                                );
                            }
                        }
                    }
                }
            }
        }

        SectionFrame {
            width: parent.width
            height: 46
            fillColor: Colors.black
            borderWidth: 1
            borderColor:
                root.statusText.indexOf("REFUSED") >= 0
                ? Colors.red
                : Colors.cyan
            inset: 8

            GohuText {
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                text:
                    root.statusText
                    || "SELECT AN OPERATION // PREVIEW BEFORE UNDO"
                font.pixelSize: 9
                color:
                    root.statusText.indexOf("REFUSED") >= 0
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }
}
