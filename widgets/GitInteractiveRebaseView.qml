import QtQuick
import qs.components

Rectangle {
    id: root

    required property var rebaseService
    required property var rebaseSessionService
    property var keyboardHost: null

    property int selectedIndex: -1

    signal openChangesRequested(string path)

    readonly property bool sessionVisible:
        rebaseSessionService
        && (
            rebaseSessionService.active
            || rebaseSessionService.busy
            || rebaseSessionService.state === "CONFLICT"
            || rebaseSessionService.state === "PAUSED_EDIT"
            || rebaseSessionService.state === "PAUSED"
            || rebaseSessionService.state === "UNCERTAIN"
        )

    onVisibleChanged: {
        if (visible
                && rebaseSessionService
                && !rebaseSessionService.busy
                && !rebaseSessionService.refreshing)
            rebaseSessionService.refresh();
    }

    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta

    function selectedRow() {
        const rows = rebaseService ? rebaseService.plan : [];

        if (selectedIndex < 0 || selectedIndex >= rows.length)
            return null;

        return rows[selectedIndex];
    }

    function cycleAction(delta) {
        const row = selectedRow();
        if (!row || !rebaseService)
            return;

        const actions = [
            "pick",
            "reword",
            "squash",
            "fixup",
            "drop",
            "edit"
        ];
        const current = actions.indexOf(String(row.action || "pick"));
        const start = current >= 0 ? current : 0;
        const next =
            actions[
                (start + Number(delta || 0) + actions.length)
                % actions.length
            ];

        rebaseService.setAction(selectedIndex, next);
    }

    function moveSelected(delta) {
        if (!rebaseService || selectedIndex < 0)
            return;

        const target = selectedIndex + Number(delta || 0);

        if (target < 0 || target >= rebaseService.plan.length)
            return;

        if (rebaseService.moveEntry(selectedIndex, target))
            selectedIndex = target;
    }

    component EditorBox: Rectangle {
        id: editorBox

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan
        property var keyboardOwner: null
        property int editorFontSize: 11
        property int placeholderFontSize: 10

        height: 30
        clip: true
        color: Colors.black
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.orange
            : accent

        TextInput {
            id: editor

            anchors {
                fill: parent
                leftMargin: 8
                rightMargin: 8
            }

            verticalAlignment: Text.AlignVCenter
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: editorBox.editorFontSize
            clip: true

            onActiveFocusChanged: {
                if (!editorBox.keyboardOwner)
                    return;

                if (activeFocus)
                    editorBox.keyboardOwner.activeTextEditor = editor;
                else if (
                    editorBox.keyboardOwner.activeTextEditor === editor
                )
                    editorBox.keyboardOwner.activeTextEditor = null;
            }
        }

        GohuText {
            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: 8
                rightMargin: 8
            }

            visible: editor.text.length === 0
            text: editorBox.placeholder
            font.pixelSize: editorBox.placeholderFontSize
            color: Colors.white
            opacity: 0.30
            elide: Text.ElideRight
        }
    }

    component RebaseButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property color accent: Colors.cyan

        signal triggered()

        height: 30
        opacity: enabledAction ? 1.0 : 0.34
        color:
            selectedAction || mouse.containsMouse
            ? Colors.black
            : Colors.dark
        border.width: 1
        border.color:
            selectedAction || mouse.containsMouse
            ? accent
            : Colors.cyan

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
        anchors.margins: 8
        spacing: 7

        Row {
            width: parent.width
            height: 34
            spacing: 6

            GohuText {
                width: parent.width - 490
                anchors.verticalCenter: parent.verticalCenter
                text: "INTERACTIVE REBASE // REHEARSED"
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }

            EditorBox {
                id: baseInput

                width: 240
                height: 30
                placeholder: "BASE REF / SHA"
                accent: Colors.cyan
                keyboardOwner: root.keyboardHost
            }

            RebaseButton {
                width: 112
                label:
                    rebaseService.previewBusy
                    ? "READING"
                    : "BUILD PLAN"
                accent: Colors.cyan
                enabledAction:
                    !rebaseService.previewBusy
                    && !rebaseService.executionBusy
                    && baseInput.text.trim().length > 0
                onTriggered: {
                    root.selectedIndex = -1;
                    rebaseService.preview(baseInput.text.trim());
                }
            }

            RebaseButton {
                width: 112
                label: "CLEAR"
                accent: Colors.red
                enabledAction:
                    !rebaseService.previewBusy
                    && !rebaseService.executionBusy
                onTriggered: {
                    root.selectedIndex = -1;
                    rewordInput.text = "";
                    rebaseService.clearPlan();
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 46
            color: Colors.black
            border.width: 1
            border.color:
                rebaseService.lastError
                ? Colors.red
                : rebaseService.armed
                ? Colors.orange
                : Colors.cyan

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 8

                GohuText {
                    width: parent.width - 270
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        rebaseService.lastError
                        ? "REFUSED // " + rebaseService.lastError
                        : String(rebaseService.state || "READY")
                    font.pixelSize: 9
                    color:
                        rebaseService.lastError
                        ? Colors.red
                        : rebaseService.armed
                        ? Colors.orange
                        : Colors.cyan
                    elide: Text.ElideRight
                }

                GohuText {
                    width: 254
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        rebaseService.branchName
                        ? (
                            String(rebaseService.branchName)
                            + " // "
                            + String(rebaseService.headSha || "").slice(0, 10)
                          )
                        : "NO PLAN"
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 176
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.57)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    GohuText {
                        width: parent.width
                        text:
                            "PLAN // "
                            + String(rebaseService.plan.length)
                            + " COMMIT"
                            + (rebaseService.plan.length === 1 ? "" : "S")
                        font.pixelSize: 10
                        color: Colors.cyan
                    }

                    Flickable {
                        id: planScroll

                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        contentWidth: width
                        contentHeight: planColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: planColumn

                            width: parent.width
                            spacing: 4

                            GohuText {
                                visible:
                                    !rebaseService.previewBusy
                                    && rebaseService.plan.length === 0
                                width: parent.width
                                topPadding: 28
                                horizontalAlignment: Text.AlignHCenter
                                text:
                                    "BUILD A PLAN FROM AN ANCESTOR BASE"
                                font.pixelSize: 10
                                color: Colors.orange
                            }

                            Repeater {
                                model: rebaseService.plan

                                Rectangle {
                                    id: planRow

                                    required property int index
                                    required property var modelData

                                    width: planColumn.width
                                    height: 58
                                    color:
                                        root.selectedIndex === index
                                        || rowMouse.containsMouse
                                        ? Colors.dark
                                        : "transparent"
                                    border.width:
                                        root.selectedIndex === index
                                        ? 1
                                        : 0
                                    border.color:
                                        String(modelData.action || "")
                                        === "drop"
                                        ? Colors.red
                                        : String(modelData.action || "")
                                        === "fixup"
                                        || String(modelData.action || "")
                                           === "squash"
                                        ? Colors.orange
                                        : String(modelData.action || "")
                                          === "reword"
                                        ? Colors.magenta
                                        : Colors.cyan

                                    Column {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 3

                                        Row {
                                            width: parent.width

                                            GohuText {
                                                width: 94
                                                text:
                                                    String(
                                                        modelData.action
                                                        || "pick"
                                                    ).toUpperCase()
                                                font.pixelSize: 9
                                                color:
                                                    String(modelData.action || "")
                                                    === "drop"
                                                    ? Colors.red
                                                    : Colors.orange
                                            }

                                            GohuText {
                                                width: parent.width - 100
                                                text:
                                                    String(
                                                        modelData.sha || ""
                                                    ).slice(0, 10)
                                                    + " // "
                                                    + String(
                                                        modelData.subject || ""
                                                    )
                                                font.pixelSize: 9
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }
                                        }

                                        GohuText {
                                            visible:
                                                String(
                                                    modelData.action || ""
                                                ) === "reword"
                                            width: parent.width
                                            text:
                                                "NEW // "
                                                + String(
                                                    modelData.message || ""
                                                )
                                            font.pixelSize: 8
                                            color: Colors.magenta
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: rowMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.selectedIndex = index;
                                            rewordInput.text =
                                                String(
                                                    planRow.modelData.message
                                                    || planRow.modelData.subject
                                                    || ""
                                                );
                                        }
                                    }
                                }
                            }
                        }

                        NeonScrollBar {
                            flickable: planScroll
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - Math.floor(parent.width * 0.57) - 8
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedRow()
                            ? (
                                "SELECTED // "
                                + String(
                                    root.selectedRow().sha || ""
                                  ).slice(0, 10)
                              )
                            : "SELECT A PLAN ROW"
                        font.pixelSize: 10
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 5

                        RebaseButton {
                            width: 42
                            label: "←"
                            accent: Colors.cyan
                            enabledAction:
                                root.selectedIndex >= 0
                                && !rebaseService.executionBusy
                            onTriggered: root.cycleAction(-1)
                        }

                        Rectangle {
                            width: parent.width - 94
                            height: 30
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.orange

                            GohuText {
                                anchors.centerIn: parent
                                text:
                                    root.selectedRow()
                                    ? String(
                                        root.selectedRow().action
                                        || "pick"
                                      ).toUpperCase()
                                    : "ACTION"
                                font.pixelSize: 10
                                color: Colors.orange
                            }
                        }

                        RebaseButton {
                            width: 42
                            label: "→"
                            accent: Colors.cyan
                            enabledAction:
                                root.selectedIndex >= 0
                                && !rebaseService.executionBusy
                            onTriggered: root.cycleAction(1)
                        }
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 6

                        RebaseButton {
                            width: (parent.width - 6) / 2
                            label: "MOVE UP"
                            accent: Colors.cyan
                            enabledAction:
                                root.selectedIndex > 0
                                && !rebaseService.executionBusy
                            onTriggered: root.moveSelected(-1)
                        }

                        RebaseButton {
                            width: (parent.width - 6) / 2
                            label: "MOVE DOWN"
                            accent: Colors.cyan
                            enabledAction:
                                root.selectedIndex >= 0
                                && root.selectedIndex
                                   < rebaseService.plan.length - 1
                                && !rebaseService.executionBusy
                            onTriggered: root.moveSelected(1)
                        }
                    }

                    EditorBox {
                        id: rewordInput

                        width: parent.width
                        placeholder: "REWORD MESSAGE"
                        accent: Colors.magenta
                        keyboardOwner: root.keyboardHost
                    }

                    RebaseButton {
                        width: parent.width
                        label: "APPLY REWORD MESSAGE"
                        accent: Colors.magenta
                        enabledAction:
                            root.selectedIndex >= 0
                            && root.selectedRow()
                            && String(root.selectedRow().action || "")
                               === "reword"
                            && rewordInput.text.trim().length > 0
                            && !rebaseService.executionBusy
                        onTriggered:
                            rebaseService.setMessage(
                                root.selectedIndex,
                                rewordInput.text.trim()
                            )
                    }

                    Rectangle {
                        width: parent.width
                        height: 58
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange

                        GohuText {
                            anchors.fill: parent
                            anchors.margins: 7
                            text:
                                "AVAILABLE // PICK · REWORD · SQUASH · "
                                + "FIXUP · DROP · EDIT\n"
                                + "EDIT STARTS A DURABLE LIVE REBASE SESSION "
                                + "WITH CONTINUE / SKIP / ABORT"
                            font.pixelSize: 8
                            color: Colors.orange
                            wrapMode: Text.Wrap
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 314)
                    }

                    RebaseButton {
                        width: parent.width
                        height: 34
                        label:
                            rebaseService.armed
                            ? "ARMED // PLAN FROZEN"
                            : "ARM REBASE"
                        accent: Colors.orange
                        selectedAction: rebaseService.armed
                        enabledAction:
                            rebaseService.plan.length > 0
                            && !rebaseService.previewBusy
                            && !rebaseService.executionBusy
                        onTriggered: rebaseService.arm()
                    }

                    RebaseButton {
                        width: parent.width
                        height: 38
                        label:
                            rebaseSessionService.busy
                            ? "STARTING / RECONCILING SESSION"
                            : rebaseService.executionBusy
                            ? "REHEARSING / EXECUTING"
                            : rebaseService.requiresPersistentSession()
                            ? "START PERSISTENT REBASE"
                            : "EXECUTE REHEARSED REBASE"
                        accent:
                            rebaseService.requiresPersistentSession()
                            ? Colors.magenta
                            : Colors.red
                        enabledAction:
                            rebaseService.armed
                            && !root.sessionVisible
                            && !rebaseService.previewBusy
                            && !rebaseService.executionBusy
                            && !rebaseSessionService.busy
                        onTriggered: {
                            if (rebaseService.requiresPersistentSession()) {
                                rebaseSessionService.start(
                                    rebaseService.armedBaseSha,
                                    rebaseService.armedBranch,
                                    rebaseService.armedHeadSha,
                                    rebaseService.plan
                                );
                                return;
                            }

                            rebaseService.executeArmed();
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 40
            color: Colors.black
            border.width: 1
            border.color:
                rebaseService.lastError
                ? Colors.red
                : rebaseService.armed
                ? Colors.orange
                : Colors.cyan

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    rebaseService.lastError
                    ? rebaseService.lastError
                    : (
                        "REHEARSAL FIRST // LIVE BRANCH MOVES ONLY "
                        + "AFTER A CLEAN TEMP-WORKTREE REWRITE"
                      )
                font.pixelSize: 9
                color:
                    rebaseService.lastError
                    ? Colors.red
                    : rebaseService.armed
                    ? Colors.orange
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    GitInteractiveRebaseSessionView {
        anchors.fill: parent
        visible: root.sessionVisible
        z: 5000

        sessionService: root.rebaseSessionService
        keyboardHost: root.keyboardHost

        onOpenChangesRequested: function(path) {
            root.openChangesRequested(path);
        }
    }
}
