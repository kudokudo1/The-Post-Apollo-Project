import QtQuick
import qs.components

Rectangle {
    id: root

    required property var assignmentService

    property int selectedIndex: -1
    property bool editorOpen: false
    property string editorMode: "NEW"

    readonly property var selectedAssignment:
        selectedIndex >= 0
        && selectedIndex < assignmentService.assignments.length
        ? assignmentService.assignments[selectedIndex]
        : null

    signal closeRequested()

    color: Colors.dark
    border.width: 1
    border.color: Colors.orange

    function statusColor(value) {
        const status = String(value || "").toUpperCase();
        if (status === "ACTIVE")
            return Colors.green;
        if (status === "READY")
            return Colors.cyan;
        if (status === "PAUSED")
            return Colors.orange;
        if (status === "COMPLETE")
            return Colors.blue;
        if (status === "CANCELLED")
            return Colors.red;
        return Colors.magenta;
    }

    function resetSelection() {
        const rows = assignmentService.assignments || [];
        selectedIndex = rows.length > 0 ? 0 : -1;
    }

    function permissionsText(row) {
        const values = row && Array.isArray(row.permissions)
            ? row.permissions : [];
        return values.join(", ");
    }

    function openEditor(modeValue) {
        const mode = String(modeValue || "NEW").toUpperCase();

        if (mode === "EDIT" && !selectedAssignment)
            return false;

        editorMode = mode;

        if (mode === "EDIT") {
            titleInput.text = String(selectedAssignment.title || "");
            phaseInput.text = String(selectedAssignment.phase || "PLANNING");
            permissionsInput.text = root.permissionsText(selectedAssignment);
            goalInput.text = String(selectedAssignment.goal || "");
            constraintsInput.text = String(selectedAssignment.constraints || "");
            doneInput.text =
                String(selectedAssignment.definitionOfDone || "");
            checklistInput.text = String(selectedAssignment.checklist || "");
            questionsInput.text =
                String(selectedAssignment.openQuestions || "");
        } else {
            titleInput.text = "";
            phaseInput.text = "PLANNING";
            permissionsInput.text = "READ, EDIT, TEST";
            goalInput.text = "";
            constraintsInput.text = "";
            doneInput.text = "";
            checklistInput.text = "";
            questionsInput.text = "";
        }

        editorOpen = true;
        Qt.callLater(function() {
            goalInput.forceActiveFocus();
        });
        return true;
    }

    function saveEditor() {
        if (editorMode === "EDIT" && selectedAssignment) {
            return assignmentService.updateAssignment(
                selectedAssignment.id,
                titleInput.text,
                goalInput.text,
                constraintsInput.text,
                doneInput.text,
                permissionsInput.text,
                checklistInput.text,
                questionsInput.text,
                phaseInput.text
            );
        }

        return assignmentService.createAssignment(
            titleInput.text,
            goalInput.text,
            constraintsInput.text,
            doneInput.text,
            permissionsInput.text,
            checklistInput.text,
            questionsInput.text,
            phaseInput.text
        );
    }

    onSelectedAssignmentChanged: {
        if (editorMode === "EDIT")
            editorOpen = false;
    }

    Connections {
        target: assignmentService

        function onAssignmentsRefreshed() {
            if (root.selectedIndex < 0
                    || root.selectedIndex
                       >= assignmentService.assignments.length)
                root.resetSelection();
        }

        function onAssignmentSaved(assignment) {
            root.editorOpen = false;
        }

        function onAssignmentActivated(result) {
            root.editorOpen = false;
        }

        function onAssignmentStatusChanged(assignment) {
            root.editorOpen = false;
        }
    }

    component OrderButton: Rectangle {
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

    component EditField: Rectangle {
        id: field

        property alias text: input.text
        property string label: ""
        property color accent: Colors.cyan

        height: 30
        color: Colors.black
        border.width: 1
        border.color: input.activeFocus ? Colors.orange : accent

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 6
            }
            width: 82
            text: field.label
            font.pixelSize: 8
            color: field.accent
            elide: Text.ElideRight
        }

        TextInput {
            id: input
            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: 88
                rightMargin: 6
            }
            color: Colors.white
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 9
            selectByMouse: true
            clip: true
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 9
        spacing: 8

        Rectangle {
            width: parent.width
            height: 52
            color: Colors.black
            border.width: 1
            border.color: Colors.orange

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 7

                Column {
                    width: parent.width - 298
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    GohuText {
                        width: parent.width
                        text: "HOSPITAL // ORDERS // ROOM ASSIGNMENTS"
                        font.pixelSize: 12
                        color: Colors.orange
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            String(assignmentService.assignmentCount)
                            + " TOTAL // "
                            + (
                                assignmentService.activeAssignment
                                ? (
                                    "ACTIVE #"
                                    + String(
                                        assignmentService.activeAssignment.id
                                      )
                                    + " // "
                                    + String(
                                        assignmentService.activeAssignment.phase
                                        || ""
                                      )
                                  )
                                : "NO ACTIVE ASSIGNMENT"
                              )
                        font.pixelSize: 8
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                OrderButton {
                    width: 78
                    label:
                        assignmentService.loading
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.cyan
                    enabledAction: !assignmentService.loading
                    onTriggered: assignmentService.refresh()
                }

                OrderButton {
                    width: 78
                    label: "NEW"
                    accent: Colors.green
                    enabledAction: !assignmentService.writing
                    onTriggered: root.openEditor("NEW")
                }

                OrderButton {
                    width: 78
                    label: "EDIT"
                    accent: Colors.orange
                    enabledAction:
                        root.selectedAssignment !== null
                        && !assignmentService.writing
                    onTriggered: root.openEditor("EDIT")
                }

                OrderButton {
                    width: 34
                    label: "X"
                    accent: Colors.red
                    onTriggered: root.closeRequested()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 60
            spacing: 8

            Rectangle {
                width: Math.max(305, parent.width * 0.36)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                ListView {
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    spacing: 4
                    model: assignmentService.assignments

                    delegate: Rectangle {
                        required property var modelData
                        required property int index

                        width: ListView.view.width
                        height: 82
                        color:
                            root.selectedIndex === index
                            ? Colors.dark
                            : Colors.black
                        border.width:
                            root.selectedIndex === index
                            ? 2 : 1
                        border.color:
                            root.statusColor(modelData.status)

                        Column {
                            anchors {
                                fill: parent
                                margins: 6
                            }
                            spacing: 2

                            GohuText {
                                width: parent.width
                                text:
                                    "#"
                                    + String(modelData.id || "?")
                                    + " // "
                                    + String(modelData.status || "DRAFT")
                                    + " // "
                                    + String(modelData.phase || "PLANNING")
                                font.pixelSize: 8
                                color: root.statusColor(modelData.status)
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        modelData.title
                                        || "UNTITLED ASSIGNMENT"
                                    )
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text: String(modelData.goal || "")
                                font.pixelSize: 8
                                color: Colors.cyan
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
                            !assignmentService.loading
                            && assignmentService.assignments.length === 0
                        text: "NO ORDERS // CREATE AN ASSIGNMENT"
                        font.pixelSize: 10
                        color: Colors.blue
                    }
                }
            }

            Rectangle {
                width:
                    parent.width
                    - Math.max(305, parent.width * 0.36)
                    - parent.spacing
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color:
                    root.selectedAssignment
                    ? root.statusColor(root.selectedAssignment.status)
                    : Colors.blue

                Column {
                    anchors {
                        fill: parent
                        margins: 10
                    }
                    spacing: 6

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedAssignment
                            ? (
                                "ORDER #"
                                + String(root.selectedAssignment.id)
                                + " // "
                                + String(root.selectedAssignment.status)
                                + " // "
                                + String(root.selectedAssignment.phase)
                              )
                            : "NO ASSIGNMENT SELECTED"
                        font.pixelSize: 12
                        color:
                            root.selectedAssignment
                            ? root.statusColor(root.selectedAssignment.status)
                            : Colors.blue
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        visible: root.selectedAssignment !== null
                        text:
                            root.selectedAssignment
                            ? (
                                "PERMISSIONS // "
                                + root.permissionsText(root.selectedAssignment)
                              )
                            : ""
                        font.pixelSize: 8
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    Flickable {
                        width: parent.width
                        height:
                            editorPanel.visible
                            ? Math.max(90, parent.height - 356)
                            : Math.max(180, parent.height - 152)
                        clip: true
                        contentWidth: width
                        contentHeight: orderDetail.implicitHeight + 8

                        GohuText {
                            id: orderDetail
                            width: parent.width
                            text:
                                root.selectedAssignment
                                ? (
                                    "## GOAL\n"
                                    + String(root.selectedAssignment.goal || "")
                                    + "\n\n## CONSTRAINTS\n"
                                    + String(
                                        root.selectedAssignment.constraints
                                        || "NONE"
                                      )
                                    + "\n\n## DEFINITION OF DONE\n"
                                    + String(
                                        root.selectedAssignment.definitionOfDone
                                        || "NONE"
                                      )
                                    + "\n\n## CHECKLIST\n"
                                    + String(
                                        root.selectedAssignment.checklist
                                        || "NONE"
                                      )
                                    + "\n\n## OPEN QUESTIONS\n"
                                    + String(
                                        root.selectedAssignment.openQuestions
                                        || "NONE"
                                      )
                                  )
                                : (
                                    "Create an Assignment to give the Doctor "
                                    + "a durable supervised Order."
                                  )
                            textFormat: Text.MarkdownText
                            font.pixelSize: 9
                            color: Colors.white
                            wrapMode: Text.Wrap
                        }
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 5

                        Repeater {
                            model: [
                                "READY",
                                "ACTIVATE",
                                "PAUSE",
                                "COMPLETE",
                                "CANCEL"
                            ]

                            OrderButton {
                                required property string modelData
                                readonly property string state:
                                    root.selectedAssignment
                                    ? String(root.selectedAssignment.status)
                                    : ""

                                width:
                                    (parent.width - parent.spacing * 4) / 5
                                height: parent.height
                                label: modelData
                                accent:
                                    modelData === "ACTIVATE"
                                    ? Colors.green
                                    : modelData === "PAUSE"
                                    ? Colors.orange
                                    : modelData === "COMPLETE"
                                    ? Colors.blue
                                    : modelData === "CANCEL"
                                    ? Colors.red
                                    : Colors.cyan
                                enabledAction:
                                    root.selectedAssignment !== null
                                    && !assignmentService.writing
                                    && (
                                        modelData === "ACTIVATE"
                                        ? state !== "COMPLETE"
                                          && state !== "CANCELLED"
                                          && state !== "ACTIVE"
                                        : modelData === "READY"
                                        ? state === "DRAFT"
                                          || state === "PAUSED"
                                        : modelData === "PAUSE"
                                        ? state === "ACTIVE"
                                        : modelData === "COMPLETE"
                                        ? state === "ACTIVE"
                                          || state === "PAUSED"
                                          || state === "READY"
                                        : state !== "COMPLETE"
                                          && state !== "CANCELLED"
                                      )
                                onTriggered: {
                                    if (modelData === "ACTIVATE") {
                                        assignmentService.activateAssignment(
                                            root.selectedAssignment.id
                                        );
                                        return;
                                    }

                                    assignmentService.setAssignmentStatus(
                                        root.selectedAssignment.id,
                                        modelData === "CANCEL"
                                        ? "CANCELLED"
                                        : modelData
                                    );
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: editorPanel

                        width: parent.width
                        height: 196
                        visible: root.editorOpen
                        color: Colors.black
                        border.width: 1
                        border.color:
                            root.editorMode === "EDIT"
                            ? Colors.orange
                            : Colors.green

                        Column {
                            anchors {
                                fill: parent
                                margins: 6
                            }
                            spacing: 4

                            Row {
                                width: parent.width
                                height: 30
                                spacing: 6

                                EditField {
                                    id: titleInput
                                    width: parent.width * 0.55
                                    label: "TITLE"
                                    accent: Colors.cyan
                                }

                                EditField {
                                    id: phaseInput
                                    width: parent.width * 0.20
                                    label: "PHASE"
                                    accent: Colors.orange
                                }

                                EditField {
                                    id: permissionsInput
                                    width:
                                        parent.width
                                        - titleInput.width
                                        - phaseInput.width
                                        - parent.spacing * 2
                                    label: "AUTH"
                                    accent: Colors.magenta
                                }
                            }

                            Row {
                                width: parent.width
                                height: 106
                                spacing: 5

                                Repeater {
                                    model: [
                                        { label: "GOAL", key: "goal" },
                                        { label: "CONSTRAINTS", key: "constraints" },
                                        { label: "DONE", key: "done" },
                                        { label: "CHECKLIST", key: "checklist" },
                                        { label: "QUESTIONS", key: "questions" }
                                    ]

                                    Rectangle {
                                        required property var modelData

                                        width:
                                            (parent.width
                                             - parent.spacing * 4) / 5
                                        height: parent.height
                                        color: Colors.dark
                                        border.width: 1
                                        border.color: Colors.blue

                                        GohuText {
                                            anchors {
                                                top: parent.top
                                                left: parent.left
                                                right: parent.right
                                                margins: 4
                                            }
                                            height: 14
                                            text: modelData.label
                                            font.pixelSize: 7
                                            color: Colors.blue
                                        }

                                        TextEdit {
                                            anchors {
                                                top: parent.top
                                                left: parent.left
                                                right: parent.right
                                                bottom: parent.bottom
                                                topMargin: 20
                                                leftMargin: 4
                                                rightMargin: 4
                                                bottomMargin: 4
                                            }
                                            id: genericEditor
                                            color: Colors.white
                                            font.family:
                                                "GohuFont 11 Nerd Font Mono"
                                            font.pixelSize: 8
                                            wrapMode: TextEdit.Wrap
                                            selectByMouse: true

                                            Component.onCompleted: {
                                                if (modelData.key === "goal")
                                                    goalInput = genericEditor;
                                                else if (modelData.key === "constraints")
                                                    constraintsInput = genericEditor;
                                                else if (modelData.key === "done")
                                                    doneInput = genericEditor;
                                                else if (modelData.key === "checklist")
                                                    checklistInput = genericEditor;
                                                else
                                                    questionsInput = genericEditor;
                                            }
                                        }
                                    }
                                }
                            }

                            Row {
                                width: parent.width
                                height: 30
                                spacing: 6

                                Item {
                                    width: parent.width - 174
                                    height: 1
                                }

                                OrderButton {
                                    width: 82
                                    height: parent.height
                                    label:
                                        assignmentService.writing
                                        ? "SAVING"
                                        : "SAVE"
                                    accent: Colors.green
                                    enabledAction:
                                        !assignmentService.writing
                                        && root.goalInput
                                        && root.goalInput.text.trim().length > 0
                                    onTriggered: root.saveEditor()
                                }

                                OrderButton {
                                    width: 82
                                    height: parent.height
                                    label: "CANCEL"
                                    accent: Colors.orange
                                    enabledAction: !assignmentService.writing
                                    onTriggered: root.editorOpen = false
                                }
                            }
                        }
                    }

                    GohuText {
                        width: parent.width
                        visible: assignmentService.lastError.length > 0
                        text: assignmentService.lastError
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

    property var goalInput: null
    property var constraintsInput: null
    property var doneInput: null
    property var checklistInput: null
    property var questionsInput: null
}
