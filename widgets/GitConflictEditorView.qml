import QtQuick
import qs.components

Rectangle {
    id: root

    required property var conflictService
    property var keyboardHost: null

    property string mode: "result"
    property bool syncingResult: false
    property bool stageArmed: false

    color: Colors.black
    border.width: 1
    border.color:
        conflictService.lastError
        ? Colors.red
        : conflictService.unresolvedCount > 0
        ? Colors.orange
        : conflictService.loaded
        ? Colors.green
        : Colors.cyan

    function modeText() {
        if (!conflictService)
            return "";

        if (mode === "base")
            return String(conflictService.baseText || "");
        if (mode === "ours")
            return String(conflictService.oursText || "");
        if (mode === "theirs")
            return String(conflictService.theirsText || "");
        return String(conflictService.resultText || "");
    }

    function currentBlock() {
        if (!conflictService)
            return null;

        const rows = conflictService.blocks || [];
        const index = Number(conflictService.selectedBlockIndex || 0);

        if (index < 0 || index >= rows.length)
            return null;

        return rows[index];
    }

    function syncResultEditor() {
        if (!conflictService || !resultEditor)
            return;

        const next = String(conflictService.resultText || "");

        if (resultEditor.text === next)
            return;

        syncingResult = true;
        resultEditor.text = next;
        syncingResult = false;
    }

    function moveBlock(delta) {
        if (!conflictService || conflictService.blocks.length <= 0)
            return;

        const count = conflictService.blocks.length;
        const current =
            Math.max(
                0,
                Number(conflictService.selectedBlockIndex || 0)
            );
        const next =
            (current + Number(delta || 0) + count) % count;
        conflictService.selectBlock(next);
    }

    component EditorButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool selectedAction: false

        signal triggered()

        height: 28
        color:
            selectedAction || mouse.containsMouse
            ? Colors.dark
            : Colors.black
        border.width: selectedAction ? 2 : 1
        border.color: accent
        opacity: enabledAction ? 1.0 : 0.28

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

    Column {
        anchors.fill: parent
        anchors.margins: 7
        spacing: 6

        Row {
            width: parent.width
            height: 28
            spacing: 5

            EditorButton {
                width: (parent.width - 15) / 4
                label: "BASE"
                accent: Colors.cyan
                selectedAction: root.mode === "base"
                enabledAction: conflictService.loaded
                onTriggered: root.mode = "base"
            }

            EditorButton {
                width: (parent.width - 15) / 4
                label: "OURS"
                accent: Colors.cyan
                selectedAction: root.mode === "ours"
                enabledAction: conflictService.loaded
                onTriggered: root.mode = "ours"
            }

            EditorButton {
                width: (parent.width - 15) / 4
                label: "THEIRS"
                accent: Colors.magenta
                selectedAction: root.mode === "theirs"
                enabledAction: conflictService.loaded
                onTriggered: root.mode = "theirs"
            }

            EditorButton {
                width: (parent.width - 15) / 4
                label: "RESULT"
                accent: Colors.green
                selectedAction: root.mode === "result"
                enabledAction: conflictService.loaded
                onTriggered: {
                    root.mode = "result";
                    root.syncResultEditor();
                }
            }
        }

        SectionFrame {
            width: parent.width
            height: 40
            fillColor: Colors.dark
            borderWidth: 1
            borderColor:
                conflictService.unresolvedCount > 0
                ? Colors.orange
                : Colors.green
            inset: 6

            Row {
                anchors.fill: parent
                spacing: 8

                GohuText {
                    width: parent.width - 210
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        conflictService.loaded
                        ? (
                            String(conflictService.path || "")
                            + " // "
                            + String(conflictService.operationState || "NONE")
                          )
                        : (
                            conflictService.loading
                            ? "LOADING THREE-WAY STAGES"
                            : "SELECT A CONFLICT"
                          )
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideMiddle
                }

                GohuText {
                    width: 202
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        String(conflictService.unresolvedCount || 0)
                        + " UNRESOLVED"
                    font.pixelSize: 9
                    color:
                        conflictService.unresolvedCount > 0
                        ? Colors.orange
                        : Colors.green
                }
            }
        }

        Row {
            width: parent.width
            height: 30
            spacing: 5

            EditorButton {
                width: 34
                label: "←"
                accent: Colors.cyan
                enabledAction:
                    conflictService.loaded
                    && conflictService.blocks.length > 0
                    && !conflictService.busy
                onTriggered: root.moveBlock(-1)
            }

            GohuText {
                width: 92
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignHCenter
                text:
                    conflictService.blocks.length > 0
                    ? (
                        "BLOCK "
                        + String(
                            Number(conflictService.selectedBlockIndex || 0)
                            + 1
                          )
                        + "/"
                        + String(conflictService.blocks.length)
                      )
                    : "NO BLOCKS"
                font.pixelSize: 8
                color: Colors.orange
            }

            EditorButton {
                width: 34
                label: "→"
                accent: Colors.cyan
                enabledAction:
                    conflictService.loaded
                    && conflictService.blocks.length > 0
                    && !conflictService.busy
                onTriggered: root.moveBlock(1)
            }

            EditorButton {
                width: (parent.width - 190) / 4
                label: "TAKE OURS"
                accent: Colors.cyan
                enabledAction:
                    conflictService.blocks.length > 0
                    && !conflictService.busy
                onTriggered: {
                    conflictService.takeOurs(
                        conflictService.selectedBlockIndex
                    );
                    root.mode = "result";
                    root.syncResultEditor();
                }
            }

            EditorButton {
                width: (parent.width - 190) / 4
                label: "TAKE THEIRS"
                accent: Colors.magenta
                enabledAction:
                    conflictService.blocks.length > 0
                    && !conflictService.busy
                onTriggered: {
                    conflictService.takeTheirs(
                        conflictService.selectedBlockIndex
                    );
                    root.mode = "result";
                    root.syncResultEditor();
                }
            }

            EditorButton {
                width: (parent.width - 190) / 4
                label: "TAKE BOTH"
                accent: Colors.orange
                enabledAction:
                    conflictService.blocks.length > 0
                    && !conflictService.busy
                onTriggered: {
                    conflictService.takeBoth(
                        conflictService.selectedBlockIndex
                    );
                    root.mode = "result";
                    root.syncResultEditor();
                }
            }

            EditorButton {
                width: (parent.width - 190) / 4
                label: "TAKE BASE"
                accent: Colors.cyan
                enabledAction:
                    conflictService.blocks.length > 0
                    && root.currentBlock()
                    && (
                        root.currentBlock().baseLines || []
                       ).length > 0
                    && !conflictService.busy
                onTriggered: {
                    conflictService.takeBase(
                        conflictService.selectedBlockIndex
                    );
                    root.mode = "result";
                    root.syncResultEditor();
                }
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - 150
            color: Colors.black
            border.width: 1
            border.color:
                root.mode === "result"
                ? Colors.green
                : root.mode === "theirs"
                ? Colors.magenta
                : Colors.cyan

            Flickable {
                id: sourceScroll

                anchors.fill: parent
                anchors.margins: 5
                visible: root.mode !== "result"
                clip: true
                contentWidth: width
                contentHeight: sourceText.implicitHeight
                boundsBehavior: Flickable.StopAtBounds

                GohuText {
                    id: sourceText

                    width: sourceScroll.width
                    text: root.modeText()
                    font.pixelSize: 9
                    color: Colors.white
                    wrapMode: Text.WrapAnywhere
                }

                NeonScrollBar {
                    flickable: sourceScroll
                }
            }

            Flickable {
                id: resultScroll

                anchors.fill: parent
                anchors.margins: 5
                visible: root.mode === "result"
                clip: true
                contentWidth: width
                contentHeight:
                    Math.max(
                        height,
                        resultEditor.implicitHeight
                    )
                boundsBehavior: Flickable.StopAtBounds

                TextEdit {
                    id: resultEditor

                    width: resultScroll.width
                    height:
                        Math.max(
                            resultScroll.height,
                            implicitHeight
                        )
                    color: Colors.white
                    selectionColor: Colors.magenta
                    selectedTextColor: Colors.black
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 9
                    wrapMode: TextEdit.WrapAnywhere
                    readOnly:
                        !conflictService.loaded
                        || conflictService.busy

                    onActiveFocusChanged: {
                        if (!root.keyboardHost)
                            return;

                        if (activeFocus)
                            root.keyboardHost.activeTextEditor = resultEditor;
                        else if (
                            root.keyboardHost.activeTextEditor
                            === resultEditor
                        )
                            root.keyboardHost.activeTextEditor = null;
                    }

                    onTextChanged: {
                        if (root.syncingResult
                                || !activeFocus
                                || !conflictService.loaded)
                            return;

                        conflictService.setResultText(text);
                    }
                }

                NeonScrollBar {
                    flickable: resultScroll
                }
            }
        }

        Row {
            width: parent.width
            height: 32
            spacing: 6

            GohuText {
                width: parent.width - 282
                anchors.verticalCenter: parent.verticalCenter
                text:
                    conflictService.lastError
                    ? conflictService.lastError
                    : String(conflictService.state || "READY")
                font.pixelSize: 8
                color:
                    conflictService.lastError
                    ? Colors.red
                    : conflictService.unresolvedCount > 0
                    ? Colors.orange
                    : Colors.green
                elide: Text.ElideRight
            }

            EditorButton {
                width: 132
                height: 32
                label:
                    conflictService.busy
                    ? "SAVING"
                    : "SAVE DRAFT"
                accent: Colors.cyan
                enabledAction:
                    conflictService.loaded
                    && !conflictService.busy
                onTriggered: {
                    root.stageArmed = false;
                    conflictService.saveDraft();
                }
            }

            EditorButton {
                width: 144
                height: 32
                label:
                    root.stageArmed
                    ? "CONFIRM STAGE"
                    : "STAGE RESOLVED"
                accent: Colors.green
                selectedAction: root.stageArmed
                enabledAction:
                    conflictService.canStage
                    && !conflictService.busy
                onTriggered: {
                    if (!root.stageArmed) {
                        root.stageArmed = true;
                        return;
                    }

                    root.stageArmed = false;
                    conflictService.stageResolved();
                }
            }
        }
    }

    Connections {
        target: conflictService
        ignoreUnknownSignals: true

        function onLoadedConflict(path) {
            root.mode = "result";
            root.stageArmed = false;
            root.syncResultEditor();
        }

        function onResultTextChanged() {
            if (!resultEditor.activeFocus)
                root.syncResultEditor();
        }

        function onResultSaved(path, staged, success, detail) {
            if (success && staged)
                root.stageArmed = false;
        }
    }
}
