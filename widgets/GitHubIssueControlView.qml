import QtQuick
import qs.components

Rectangle {
    id: root

    required property var lifecycleService
    property string repositorySlug: ""
    property bool createMode: false
    property int issueNumber: 0
    property string issueTitle: ""
    property string issueState: "OPEN"
    property bool externallyManagedTarget: false

    property string armedAction: ""
    property string closeReason: "completed"

    readonly property bool hasTarget:
        repositorySlug.trim().length > 0
        && issueNumber > 0
    readonly property bool closed:
        String(issueState || "").toUpperCase() === "CLOSED"

    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta

    signal closeRequested()
    signal targetRefreshRequested()

    function clearArm() {
        armedAction = "";
    }

    function refreshFacts() {
        targetRefreshRequested();
        return true;
    }

    Connections {
        target: root.lifecycleService
        ignoreUnknownSignals: true

        function onMutationFinished(
            mutationSucceeded,
            evidenceVerified,
            operation,
            evidence
        ) {
            root.clearArm();

            if (!mutationSucceeded)
                return;

            root.targetRefreshRequested();

            if (String(operation || "") === "create") {
                root.closeRequested();
                return;
            }

            if (evidenceVerified && !root.externallyManagedTarget) {
                const row = ((evidence || {}).issue) || {};

                if (row.state !== undefined)
                    root.issueState = String(row.state || "");
                if (row.title !== undefined)
                    root.issueTitle = String(row.title || "");
            }
        }
    }

    function armOrRun(token, callback) {
        if (armedAction !== token) {
            armedAction = token;
            return false;
        }

        armedAction = "";
        callback();
        return true;
    }

    component IssueButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool selectedAction: false

        signal triggered()

        height: 30
        opacity: enabledAction ? 1.0 : 0.36
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

    component IssueField: Rectangle {
        id: field

        property alias text: editor.text
        property string placeholder: ""

        height: 30
        color: Colors.black
        border.width: editor.activeFocus ? 2 : 1
        border.color:
            editor.activeFocus
            ? Colors.magenta
            : Colors.cyan

        TextInput {
            id: editor
            anchors.fill: parent
            anchors.leftMargin: 7
            anchors.rightMargin: 7
            verticalAlignment: TextInput.AlignVCenter
            activeFocusOnPress: true
            selectByMouse: true
            clip: true
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 9
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black

            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: !editor.text && !editor.activeFocus
                text: field.placeholder
                font.family: editor.font.family
                font.pixelSize: editor.font.pixelSize
                color: Colors.cyan
                opacity: 0.42
            }
        }
    }

    component IssueBody: Rectangle {
        id: field

        property alias text: editor.text
        property string placeholder: ""

        color: Colors.black
        border.width: editor.activeFocus ? 2 : 1
        border.color:
            editor.activeFocus
            ? Colors.magenta
            : Colors.cyan

        Flickable {
            anchors.fill: parent
            anchors.margins: 6
            clip: true
            contentWidth: width
            contentHeight: Math.max(height, editor.implicitHeight)

            TextEdit {
                id: editor
                width: parent.width
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 9
                color: Colors.white
                selectionColor: Colors.magenta
                selectedTextColor: Colors.black

                Text {
                    visible: !editor.text && !editor.activeFocus
                    text: field.placeholder
                    font.family: editor.font.family
                    font.pixelSize: editor.font.pixelSize
                    color: Colors.cyan
                    opacity: 0.42
                }
            }
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 7

        SectionFrame {
            width: parent.width
            height: 52
            fillColor: Colors.black
            borderWidth: 1
            borderColor: Colors.magenta
            inset: 7

            Row {
                anchors.fill: parent
                spacing: 7

                Column {
                    width: parent.width - 190
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    GohuText {
                        width: parent.width
                        text:
                            root.createMode
                            ? "ISSUE // CREATE"
                            : "ISSUE // #"
                                + String(root.issueNumber)
                                + " // "
                                + String(root.issueTitle || "UNTITLED")
                        font.pixelSize: 12
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            String(root.repositorySlug || "NO REPOSITORY")
                            + " // "
                            + (
                                root.createMode
                                ? "NEW"
                                : String(root.issueState || "UNKNOWN")
                              )
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                IssueButton {
                    width: 82
                    label: "← ISSUES"
                    enabledAction: !root.lifecycleService.busy
                    onTriggered: root.closeRequested()
                }

                IssueButton {
                    width: 94
                    label: root.lifecycleService.busy ? "WORKING" : "REFRESH"
                    accent: Colors.green
                    enabledAction:
                        !!root.repositorySlug
                        && !root.lifecycleService.busy
                    onTriggered: root.refreshFacts()
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 38
            color: Colors.black
            border.width: 1
            border.color:
                root.armedAction
                ? Colors.orange
                : root.lifecycleService.lastError
                ? Colors.red
                : Colors.cyan

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    root.armedAction
                    ? "ARMED // "
                        + root.armedAction.toUpperCase()
                        + " // PRESS AGAIN TO EXECUTE"
                    : root.lifecycleService.lastError
                    ? "ISSUE ACTION // " + root.lifecycleService.lastError
                    : String(root.lifecycleService.status || "READY")
                font.pixelSize: 9
                color:
                    root.armedAction
                    ? Colors.orange
                    : root.lifecycleService.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }

        Flickable {
            width: parent.width
            height: parent.height - 104
            clip: true
            contentWidth: width
            contentHeight: issueColumn.height

            Column {
                id: issueColumn
                width: parent.width
                spacing: 7

                Row {
                    width: parent.width
                    height: 31
                    spacing: 6

                    IssueField {
                        id: titleInput
                        width: parent.width - 116
                        placeholder:
                            root.createMode
                            ? "ISSUE TITLE"
                            : root.issueTitle
                    }

                    IssueButton {
                        width: 110
                        label:
                            root.createMode
                            ? "CREATE"
                            : "SET TITLE"
                        accent:
                            root.createMode
                            ? Colors.green
                            : Colors.cyan
                        enabledAction:
                            titleInput.text.trim().length > 0
                            && !!root.repositorySlug
                            && !root.lifecycleService.busy
                        onTriggered: {
                            root.clearArm();

                            if (root.createMode) {
                                root.lifecycleService.createIssue(
                                    root.repositorySlug,
                                    titleInput.text.trim(),
                                    bodyInput.text,
                                    metaInput.text.trim()
                                        ? [metaInput.text.trim()]
                                        : [],
                                    [],
                                    milestoneInput.text.trim()
                                );
                            } else {
                                root.lifecycleService.editIssue(
                                    root.repositorySlug,
                                    root.issueNumber,
                                    titleInput.text.trim(),
                                    null
                                );
                            }
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: 82
                    spacing: 6

                    IssueBody {
                        id: bodyInput
                        width: parent.width - 116
                        height: parent.height
                        placeholder:
                            root.createMode
                            ? "ISSUE BODY"
                            : "REPLACEMENT ISSUE BODY // EMPTY CLEARS"
                    }

                    IssueButton {
                        width: 110
                        anchors.verticalCenter: parent.verticalCenter
                        label: "SET BODY"
                        visible: !root.createMode
                        enabledAction:
                            root.hasTarget
                            && !root.lifecycleService.busy
                        onTriggered: {
                            root.clearArm();
                            root.lifecycleService.editIssue(
                                root.repositorySlug,
                                root.issueNumber,
                                null,
                                bodyInput.text
                            );
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: 31
                    spacing: 6

                    IssueField {
                        id: metaInput
                        width: parent.width - 484
                        placeholder: "LABEL / ASSIGNEE"
                    }

                    IssueButton {
                        width: 92
                        label: "+ LABEL"
                        enabledAction:
                            root.hasTarget
                            && metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateLabels(
                            root.repositorySlug,
                            root.issueNumber,
                            [metaInput.text.trim()],
                            []
                        )
                    }

                    IssueButton {
                        width: 92
                        label: "- LABEL"
                        accent: Colors.red
                        enabledAction:
                            root.hasTarget
                            && metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateLabels(
                            root.repositorySlug,
                            root.issueNumber,
                            [],
                            [metaInput.text.trim()]
                        )
                    }

                    IssueButton {
                        width: 110
                        label: "+ ASSIGNEE"
                        enabledAction:
                            root.hasTarget
                            && metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateAssignees(
                            root.repositorySlug,
                            root.issueNumber,
                            [metaInput.text.trim()],
                            []
                        )
                    }

                    IssueButton {
                        width: 110
                        label: "- ASSIGNEE"
                        accent: Colors.red
                        enabledAction:
                            root.hasTarget
                            && metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateAssignees(
                            root.repositorySlug,
                            root.issueNumber,
                            [],
                            [metaInput.text.trim()]
                        )
                    }
                }

                Row {
                    width: parent.width
                    height: 31
                    spacing: 6

                    IssueField {
                        id: milestoneInput
                        width: parent.width - 226
                        placeholder: "MILESTONE"
                    }

                    IssueButton {
                        width: 104
                        label: "SET"
                        enabledAction:
                            root.hasTarget
                            && milestoneInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.setMilestone(
                            root.repositorySlug,
                            root.issueNumber,
                            milestoneInput.text.trim()
                        )
                    }

                    IssueButton {
                        width: 110
                        label: "CLEAR"
                        accent: Colors.red
                        enabledAction:
                            root.hasTarget
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.clearMilestone(
                            root.repositorySlug,
                            root.issueNumber
                        )
                    }
                }

                Rectangle {
                    visible: !root.createMode
                    width: parent.width
                    height: 116
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors.fill: parent
                        anchors.margins: 7
                        spacing: 6

                        GohuText {
                            text: "COMMENT"
                            font.pixelSize: 10
                            color: Colors.magenta
                        }

                        IssueBody {
                            id: commentInput
                            width: parent.width
                            height: 54
                            placeholder: "ADD ISSUE COMMENT"
                        }

                        IssueButton {
                            width: 110
                            label: "POST COMMENT"
                            enabledAction:
                                commentInput.text.trim().length > 0
                                && !root.lifecycleService.busy
                            onTriggered: root.lifecycleService.commentIssue(
                                root.repositorySlug,
                                root.issueNumber,
                                commentInput.text.trim()
                            )
                        }
                    }
                }

                SectionFrame {
                    visible: !root.createMode
                    width: parent.width
                    height: 80
                    fillColor: Colors.black
                    borderWidth: 1
                    borderColor: Colors.red
                    inset: 8

                    Row {
                        anchors.fill: parent
                        spacing: 7

                        IssueButton {
                            width: 118
                            anchors.verticalCenter: parent.verticalCenter
                            label: "COMPLETED"
                            selectedAction:
                                root.closeReason === "completed"
                            accent: Colors.green
                            enabledAction: !root.closed
                            onTriggered: {
                                root.closeReason = "completed";
                                root.clearArm();
                            }
                        }

                        IssueButton {
                            width: 118
                            anchors.verticalCenter: parent.verticalCenter
                            label: "NOT PLANNED"
                            selectedAction:
                                root.closeReason === "not planned"
                            accent: Colors.orange
                            enabledAction: !root.closed
                            onTriggered: {
                                root.closeReason = "not planned";
                                root.clearArm();
                            }
                        }

                        IssueButton {
                            width: 150
                            anchors.verticalCenter: parent.verticalCenter
                            label:
                                root.closed
                                ? "REOPEN"
                                : root.armedAction === "close"
                                ? "CONFIRM CLOSE"
                                : "CLOSE ISSUE"
                            selectedAction:
                                root.armedAction === "close"
                            accent: Colors.red
                            enabledAction:
                                root.hasTarget
                                && !root.lifecycleService.busy
                            onTriggered: {
                                if (root.closed) {
                                    root.clearArm();
                                    root.lifecycleService.reopenIssue(
                                        root.repositorySlug,
                                        root.issueNumber,
                                        ""
                                    );
                                    return;
                                }

                                root.armOrRun(
                                    "close",
                                    function() {
                                        root.lifecycleService.closeIssue(
                                            root.repositorySlug,
                                            root.issueNumber,
                                            true,
                                            root.closeReason,
                                            ""
                                        );
                                    }
                                );
                            }
                        }

                        GohuText {
                            width: parent.width - 407
                            anchors.verticalCenter: parent.verticalCenter
                            horizontalAlignment: Text.AlignRight
                            text:
                                root.closed
                                ? "ISSUE CLOSED"
                                : "CLOSE REASON // "
                                    + root.closeReason.toUpperCase()
                            font.pixelSize: 9
                            color: Colors.red
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
