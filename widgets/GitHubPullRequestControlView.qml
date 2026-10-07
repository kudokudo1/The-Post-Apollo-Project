import QtQuick
import qs.components

Rectangle {
    id: root

    required property var lifecycleService
    required property var queueProvider
    required property var queueLifecycleService
    required property var threadProvider
    required property var threadLifecycleService

    property string repositorySlug: ""
    property int pullRequestNumber: 0
    property string pullRequestTitle: ""
    property string pullRequestState: ""
    property bool pullRequestDraft: false
    property string pullRequestHeadSha: ""
    property string pullRequestBaseRef: ""
    property string pullRequestHeadRef: ""
    property bool externallyManagedTarget: false

    property string mode: "control"
    property string armedAction: ""
    property int selectedThreadIndex: -1

    readonly property bool hasTarget:
        repositorySlug.trim().length > 0
        && pullRequestNumber > 0
    readonly property var queueEntry:
        queueProvider && hasTarget
        ? queueProvider.entryForPullRequest(pullRequestNumber)
        : null
    readonly property var selectedThread:
        threadProvider
        && selectedThreadIndex >= 0
        && selectedThreadIndex < threadProvider.threads.length
        ? threadProvider.threadAt(selectedThreadIndex)
        : null
    readonly property bool anyBusy:
        (lifecycleService && lifecycleService.busy)
        || (queueProvider && queueProvider.busy)
        || (queueLifecycleService && queueLifecycleService.busy)
        || (threadProvider && threadProvider.busy)
        || (threadLifecycleService && threadLifecycleService.busy)

    color: Colors.dark
    border.width: 1
    border.color: Colors.magenta

    signal targetRefreshRequested()
    signal closeRequested()

    function clearArm() {
        armedAction = "";
    }

    function refreshFacts() {
        clearArm();

        if (!hasTarget)
            return false;

        if (queueProvider && !queueProvider.busy)
            queueProvider.refresh(repositorySlug, pullRequestBaseRef);

        if (threadProvider && !threadProvider.busy)
            threadProvider.refresh(repositorySlug, pullRequestNumber);

        targetRefreshRequested();
        return true;
    }

    function syncEvidence(value) {
        const row = ((value || {}).pullRequest) || {};

        if (Number(row.number || 0) !== pullRequestNumber)
            return;

        if (externallyManagedTarget)
            return;

        if (row.title !== undefined)
            pullRequestTitle = String(row.title || "");
        if (row.state !== undefined)
            pullRequestState = String(row.state || "");
        if (row.isDraft !== undefined)
            pullRequestDraft = Boolean(row.isDraft);
        if (row.headRefOid)
            pullRequestHeadSha = String(row.headRefOid);
        if (row.baseRefName)
            pullRequestBaseRef = String(row.baseRefName);
        if (row.headRefName)
            pullRequestHeadRef = String(row.headRefName);
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

    function topCommentId(thread) {
        const comments =
            thread && Array.isArray(thread.comments)
            ? thread.comments
            : [];

        if (comments.length === 0)
            return "";

        return String((comments[0] || {}).fullDatabaseId || "");
    }

    onRepositorySlugChanged: {
        clearArm();
        selectedThreadIndex = -1;
    }

    onPullRequestNumberChanged: {
        clearArm();
        selectedThreadIndex = -1;
    }

    onVisibleChanged: {
        if (visible && hasTarget)
            refreshFacts();
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

            if (mutationSucceeded && evidenceVerified)
                root.syncEvidence(evidence);

            if (mutationSucceeded)
                root.refreshFacts();
        }
    }

    Connections {
        target: root.queueLifecycleService
        ignoreUnknownSignals: true

        function onQueueChanged(repository, number, queued, evidence) {
            if (String(repository || "") !== root.repositorySlug
                    || Number(number || 0) !== root.pullRequestNumber)
                return;

            if (root.queueProvider && !root.queueProvider.busy)
                root.queueProvider.refresh(
                    root.repositorySlug,
                    root.pullRequestBaseRef
                );
        }

        function onMutationFinished(
            mutationSucceeded,
            evidenceVerified,
            operation,
            evidence
        ) {
            root.clearArm();
        }
    }

    Connections {
        target: root.threadLifecycleService
        ignoreUnknownSignals: true

        function onThreadChanged(repository, number, threadId, evidence) {
            if (String(repository || "") !== root.repositorySlug
                    || Number(number || 0) !== root.pullRequestNumber)
                return;

            if (root.threadProvider && !root.threadProvider.busy)
                root.threadProvider.refresh(
                    root.repositorySlug,
                    root.pullRequestNumber
                );
        }

        function onMutationFinished(
            mutationSucceeded,
            evidenceVerified,
            operation,
            evidence
        ) {
            root.clearArm();
        }
    }

    component ActionButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool selectedAction: false

        signal triggered()

        height: 29
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
            text: button.label
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 9
            color: button.accent
            elide: Text.ElideRight
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: button.triggered()
        }
    }

    component InputField: Rectangle {
        id: field

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan

        height: 29
        color: Colors.black
        border.width: editor.activeFocus ? 2 : 1
        border.color: editor.activeFocus ? Colors.magenta : accent

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
                color: field.accent
                opacity: 0.42
            }
        }
    }

    component MultiLineField: Rectangle {
        id: field

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan

        color: Colors.black
        border.width: editor.activeFocus ? 2 : 1
        border.color: editor.activeFocus ? Colors.magenta : accent

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
                    color: field.accent
                    opacity: 0.42
                }
            }
        }
    }

    component StatusBox: Rectangle {
        property string text: ""
        property color accent: Colors.cyan

        height: 38
        color: Colors.black
        border.width: 1
        border.color: accent

        GohuText {
            anchors.fill: parent
            anchors.margins: 7
            verticalAlignment: Text.AlignVCenter
            text: parent.text
            font.pixelSize: 9
            color: parent.accent
            elide: Text.ElideRight
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 7

        Rectangle {
            width: parent.width
            height: 52
            color: Colors.black
            border.width: 1
            border.color: Colors.magenta

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 6

                Column {
                    width: parent.width - 470
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    GohuText {
                        width: parent.width
                        text:
                            root.hasTarget
                            ? "PULL REQUEST // #"
                                + String(root.pullRequestNumber)
                                + " // "
                                + String(root.pullRequestTitle || "UNTITLED")
                            : "PULL REQUEST // NO TARGET"
                        font.pixelSize: 12
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            String(root.repositorySlug || "NO REPOSITORY")
                            + " // "
                            + String(root.pullRequestHeadRef || "HEAD")
                            + " -> "
                            + String(root.pullRequestBaseRef || "BASE")
                            + " // "
                            + (
                                root.pullRequestDraft
                                ? "DRAFT"
                                : String(root.pullRequestState || "UNKNOWN")
                              )
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                ActionButton {
                    width: 82
                    label: "← PULLS"
                    accent: Colors.cyan
                    enabledAction: !root.anyBusy
                    onTriggered: root.closeRequested()
                }

                Repeater {
                    model: ["control", "queue", "threads"]

                    delegate: ActionButton {
                        required property string modelData

                        width: 86
                        label: modelData.toUpperCase()
                        selectedAction: root.mode === modelData
                        accent:
                            modelData === "control"
                            ? Colors.cyan
                            : modelData === "queue"
                            ? Colors.blue
                            : Colors.magenta
                        onTriggered: {
                            root.mode = modelData;
                            root.clearArm();
                        }
                    }
                }

                ActionButton {
                    width: 90
                    label: root.anyBusy ? "WORKING" : "REFRESH"
                    accent: Colors.green
                    enabledAction: root.hasTarget && !root.anyBusy
                    onTriggered: root.refreshFacts()
                }
            }
        }

        StatusBox {
            width: parent.width
            text:
                root.armedAction
                ? "ARMED // "
                    + root.armedAction.toUpperCase()
                    + " // PRESS AGAIN TO EXECUTE"
                : root.mode === "queue"
                ? String(root.queueLifecycleService.status || "QUEUE READY")
                : root.mode === "threads"
                ? (
                    root.threadLifecycleService.lastError
                    ? "THREAD ACTION // "
                        + root.threadLifecycleService.lastError
                    : String(root.threadProvider.status || "THREADS READY")
                  )
                : (
                    root.lifecycleService.lastError
                    ? "PR ACTION // " + root.lifecycleService.lastError
                    : String(root.lifecycleService.status || "READY")
                  )
            accent:
                root.armedAction
                ? Colors.orange
                : root.mode === "threads"
                ? Colors.magenta
                : root.mode === "queue"
                ? Colors.blue
                : Colors.cyan
        }

        Loader {
            width: parent.width
            height: parent.height - 111
            sourceComponent:
                root.mode === "queue"
                ? queuePane
                : root.mode === "threads"
                ? threadsPane
                : controlPane
        }
    }

    Component {
        id: controlPane

        Flickable {
            clip: true
            contentWidth: width
            contentHeight: controlColumn.height

            Column {
                id: controlColumn
                width: parent.width
                spacing: 7

                Row {
                    width: parent.width
                    height: 31
                    spacing: 6

                    ActionButton {
                        width: 100
                        label:
                            root.pullRequestDraft
                            ? "MARK READY"
                            : "MAKE DRAFT"
                        accent: Colors.cyan
                        enabledAction:
                            root.hasTarget
                            && !root.lifecycleService.busy
                        onTriggered: {
                            root.clearArm();

                            if (root.pullRequestDraft) {
                                root.lifecycleService.markReady(
                                    root.repositorySlug,
                                    root.pullRequestNumber
                                );
                            } else {
                                root.lifecycleService.convertToDraft(
                                    root.repositorySlug,
                                    root.pullRequestNumber
                                );
                            }
                        }
                    }

                    ActionButton {
                        width: 110
                        label:
                            root.armedAction === "update-branch"
                            ? "CONFIRM UPDATE"
                            : "UPDATE BRANCH"
                        selectedAction:
                            root.armedAction === "update-branch"
                        accent: Colors.orange
                        enabledAction:
                            root.hasTarget
                            && !root.lifecycleService.busy
                        onTriggered: root.armOrRun(
                            "update-branch",
                            function() {
                                root.lifecycleService.updateBranch(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    false,
                                    true
                                );
                            }
                        )
                    }

                    ActionButton {
                        width: 112
                        label:
                            root.armedAction === "update-rebase"
                            ? "CONFIRM REBASE"
                            : "UPDATE REBASE"
                        selectedAction:
                            root.armedAction === "update-rebase"
                        accent: Colors.orange
                        enabledAction:
                            root.hasTarget
                            && !root.lifecycleService.busy
                        onTriggered: root.armOrRun(
                            "update-rebase",
                            function() {
                                root.lifecycleService.updateBranch(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    true,
                                    true
                                );
                            }
                        )
                    }

                    ActionButton {
                        width: 100
                        label:
                            String(root.pullRequestState || "").toUpperCase()
                                === "CLOSED"
                            ? "REOPEN"
                            : root.armedAction === "close"
                            ? "CONFIRM CLOSE"
                            : "CLOSE"
                        selectedAction: root.armedAction === "close"
                        accent: Colors.red
                        enabledAction:
                            root.hasTarget
                            && !root.lifecycleService.busy
                        onTriggered: {
                            if (String(root.pullRequestState || "").toUpperCase()
                                    === "CLOSED") {
                                root.clearArm();
                                root.lifecycleService.reopenPullRequest(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    ""
                                );
                                return;
                            }

                            root.armOrRun(
                                "close",
                                function() {
                                    root.lifecycleService.closePullRequest(
                                        root.repositorySlug,
                                        root.pullRequestNumber,
                                        true,
                                        ""
                                    );
                                }
                            );
                        }
                    }

                    Item { width: 1; height: 1 }

                    GohuText {
                        width: parent.width - 446
                        anchors.verticalCenter: parent.verticalCenter
                        horizontalAlignment: Text.AlignRight
                        text:
                            root.pullRequestHeadSha
                            ? "HEAD // "
                                + root.pullRequestHeadSha.slice(0, 12)
                            : "HEAD // UNKNOWN"
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                Row {
                    width: parent.width
                    height: 31
                    spacing: 6

                    InputField {
                        id: titleInput
                        width: parent.width - 116
                        placeholder:
                            root.pullRequestTitle
                            ? root.pullRequestTitle
                            : "NEW TITLE"
                    }

                    ActionButton {
                        width: 110
                        label: "SET TITLE"
                        accent: Colors.cyan
                        enabledAction:
                            root.hasTarget
                            && titleInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: {
                            root.clearArm();
                            root.lifecycleService.editPullRequest(
                                root.repositorySlug,
                                root.pullRequestNumber,
                                titleInput.text.trim(),
                                null,
                                null
                            );
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: 31
                    spacing: 6

                    InputField {
                        id: baseInput
                        width: parent.width - 116
                        placeholder:
                            root.pullRequestBaseRef
                            ? "BASE // " + root.pullRequestBaseRef
                            : "NEW BASE BRANCH"
                    }

                    ActionButton {
                        width: 110
                        label: "SET BASE"
                        accent: Colors.cyan
                        enabledAction:
                            root.hasTarget
                            && baseInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: {
                            root.clearArm();
                            root.lifecycleService.editPullRequest(
                                root.repositorySlug,
                                root.pullRequestNumber,
                                null,
                                null,
                                baseInput.text.trim()
                            );
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: 72
                    spacing: 6

                    MultiLineField {
                        id: bodyInput
                        width: parent.width - 116
                        height: parent.height
                        placeholder: "REPLACEMENT PR BODY // EMPTY CLEARS BODY"
                    }

                    ActionButton {
                        width: 110
                        anchors.verticalCenter: parent.verticalCenter
                        label: "SET BODY"
                        accent: Colors.cyan
                        enabledAction:
                            root.hasTarget
                            && !root.lifecycleService.busy
                        onTriggered: {
                            root.clearArm();
                            root.lifecycleService.editPullRequest(
                                root.repositorySlug,
                                root.pullRequestNumber,
                                null,
                                bodyInput.text,
                                null
                            );
                        }
                    }
                }

                Row {
                    width: parent.width
                    height: 31
                    spacing: 5

                    InputField {
                        id: metaInput
                        width: parent.width - 574
                        placeholder: "LABEL / ASSIGNEE / REVIEWER / MILESTONE"
                    }

                    ActionButton {
                        width: 88
                        label: "+ LABEL"
                        enabledAction:
                            metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateLabels(
                            root.repositorySlug,
                            root.pullRequestNumber,
                            [metaInput.text.trim()],
                            []
                        )
                    }

                    ActionButton {
                        width: 88
                        label: "- LABEL"
                        accent: Colors.red
                        enabledAction:
                            metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateLabels(
                            root.repositorySlug,
                            root.pullRequestNumber,
                            [],
                            [metaInput.text.trim()]
                        )
                    }

                    ActionButton {
                        width: 104
                        label: "+ ASSIGNEE"
                        enabledAction:
                            metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateAssignees(
                            root.repositorySlug,
                            root.pullRequestNumber,
                            [metaInput.text.trim()],
                            []
                        )
                    }

                    ActionButton {
                        width: 104
                        label: "+ REVIEWER"
                        enabledAction:
                            metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.updateReviewers(
                            root.repositorySlug,
                            root.pullRequestNumber,
                            [metaInput.text.trim()],
                            []
                        )
                    }

                    ActionButton {
                        width: 92
                        label: "MILESTONE"
                        enabledAction:
                            metaInput.text.trim().length > 0
                            && !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.setMilestone(
                            root.repositorySlug,
                            root.pullRequestNumber,
                            metaInput.text.trim()
                        )
                    }

                    ActionButton {
                        width: 76
                        label: "CLEAR"
                        accent: Colors.red
                        enabledAction: !root.lifecycleService.busy
                        onTriggered: root.lifecycleService.clearMilestone(
                            root.repositorySlug,
                            root.pullRequestNumber
                        )
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 132
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    Column {
                        anchors.fill: parent
                        anchors.margins: 7
                        spacing: 6

                        GohuText {
                            text: "REVIEW / COMMENT"
                            font.pixelSize: 10
                            color: Colors.magenta
                        }

                        MultiLineField {
                            id: reviewInput
                            width: parent.width
                            height: 58
                            placeholder: "COMMENT OR REVIEW BODY"
                            accent: Colors.magenta
                        }

                        Row {
                            width: parent.width
                            height: 29
                            spacing: 6

                            ActionButton {
                                width: 94
                                label: "COMMENT"
                                accent: Colors.cyan
                                enabledAction:
                                    reviewInput.text.trim().length > 0
                                    && !root.lifecycleService.busy
                                onTriggered: root.lifecycleService.commentPullRequest(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    reviewInput.text.trim()
                                )
                            }

                            ActionButton {
                                width: 94
                                label: "APPROVE"
                                accent: Colors.green
                                enabledAction: !root.lifecycleService.busy
                                onTriggered: root.lifecycleService.reviewPullRequest(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    "approve",
                                    reviewInput.text.trim()
                                )
                            }

                            ActionButton {
                                width: 106
                                label: "REVIEW COMMENT"
                                accent: Colors.cyan
                                enabledAction:
                                    reviewInput.text.trim().length > 0
                                    && !root.lifecycleService.busy
                                onTriggered: root.lifecycleService.reviewPullRequest(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    "comment",
                                    reviewInput.text.trim()
                                )
                            }

                            ActionButton {
                                width: 126
                                label: "REQUEST CHANGES"
                                accent: Colors.orange
                                enabledAction:
                                    reviewInput.text.trim().length > 0
                                    && !root.lifecycleService.busy
                                onTriggered: root.lifecycleService.reviewPullRequest(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    "request-changes",
                                    reviewInput.text.trim()
                                )
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 78
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.red

                    Row {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 7

                        GohuText {
                            width: parent.width - 390
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                "MERGE // PINNED TO "
                                + (
                                    root.pullRequestHeadSha
                                    ? root.pullRequestHeadSha.slice(0, 12)
                                    : "UNKNOWN HEAD"
                                  )
                            font.pixelSize: 10
                            color: Colors.red
                            elide: Text.ElideRight
                        }

                        Repeater {
                            model: ["merge", "squash", "rebase"]

                            delegate: ActionButton {
                                required property string modelData

                                width: 120
                                anchors.verticalCenter: parent.verticalCenter
                                label:
                                    root.armedAction
                                        === "merge-" + modelData
                                    ? "CONFIRM "
                                        + modelData.toUpperCase()
                                    : modelData.toUpperCase()
                                selectedAction:
                                    root.armedAction
                                        === "merge-" + modelData
                                accent: Colors.red
                                enabledAction:
                                    root.hasTarget
                                    && /^[0-9a-fA-F]{40}$/.test(
                                        root.pullRequestHeadSha
                                       )
                                    && !root.lifecycleService.busy
                                onTriggered: root.armOrRun(
                                    "merge-" + modelData,
                                    function() {
                                        root.lifecycleService.mergePullRequest(
                                            root.repositorySlug,
                                            root.pullRequestNumber,
                                            modelData,
                                            root.pullRequestHeadSha,
                                            true,
                                            "",
                                            ""
                                        );
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: queuePane

        Column {
            spacing: 8

            Row {
                width: parent.width
                height: 34
                spacing: 7

                ActionButton {
                    width: 118
                    label: "REFRESH QUEUE"
                    accent: Colors.blue
                    enabledAction:
                        root.hasTarget
                        && !root.queueProvider.busy
                    onTriggered: root.queueProvider.refresh(
                        root.repositorySlug,
                        root.pullRequestBaseRef
                    )
                }

                ActionButton {
                    width: 126
                    label: "PREVIEW ENQUEUE"
                    accent: Colors.blue
                    enabledAction:
                        root.hasTarget
                        && /^[0-9a-fA-F]{40}$/.test(
                            root.pullRequestHeadSha
                           )
                        && !root.queueLifecycleService.busy
                    onTriggered: {
                        root.clearArm();
                        root.queueLifecycleService.previewEnqueue(
                            root.repositorySlug,
                            root.pullRequestNumber,
                            root.pullRequestHeadSha
                        );
                    }
                }

                ActionButton {
                    width: 126
                    label: "PREVIEW DEQUEUE"
                    accent: Colors.orange
                    enabledAction:
                        root.hasTarget
                        && !root.queueLifecycleService.busy
                    onTriggered: {
                        root.clearArm();
                        root.queueLifecycleService.previewDequeue(
                            root.repositorySlug,
                            root.pullRequestNumber
                        );
                    }
                }

                Item { width: 1; height: 1 }

                GohuText {
                    width: parent.width - 392
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        root.queueProvider.queueAvailable
                        ? "QUEUE // "
                            + String(
                                root.queueProvider.resolvedBranch
                                || root.pullRequestBaseRef
                              )
                            + " // "
                            + String(root.queueProvider.totalCount)
                            + " ENTRIES"
                        : "QUEUE // NOT CONFIGURED / NOT READ"
                    font.pixelSize: 9
                    color: Colors.blue
                    elide: Text.ElideRight
                }
            }

            StatusBox {
                width: parent.width
                accent: Colors.blue
                text:
                    root.queueEntry
                    ? "THIS PR // POSITION "
                        + String(root.queueEntry.position || "?")
                        + " // "
                        + String(root.queueEntry.stateLabel || root.queueEntry.state || "")
                    : "THIS PR // NOT CURRENTLY VISIBLE IN QUEUE"
            }

            Rectangle {
                width: parent.width
                height: 118
                color: Colors.black
                border.width: 1
                border.color:
                    root.queueLifecycleService.preview
                    && root.queueLifecycleService.preview.action
                    ? Colors.orange
                    : Colors.blue

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6

                    GohuText {
                        text:
                            root.queueLifecycleService.preview
                            && root.queueLifecycleService.preview.action
                            ? "PREVIEW // "
                                + String(
                                    root.queueLifecycleService.preview.action
                                  ).toUpperCase()
                            : "PREVIEW // NONE"
                        font.pixelSize: 11
                        color: Colors.orange
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.queueLifecycleService.preview
                            && root.queueLifecycleService.preview.pullRequestId
                            ? "BASE // "
                                + String(
                                    root.queueLifecycleService.preview.baseBranch
                                    || ""
                                  )
                                + " // HEAD // "
                                + String(
                                    root.queueLifecycleService.preview.headSha
                                    || ""
                                  ).slice(0, 12)
                            : "BUILD A FRESH PREVIEW BEFORE EXECUTION"
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 7

                        ActionButton {
                            width: 150
                            label: "EXECUTE ENQUEUE"
                            accent: Colors.green
                            enabledAction:
                                String(
                                    (root.queueLifecycleService.preview || {}).action
                                    || ""
                                ) === "enqueue"
                                && !root.queueLifecycleService.busy
                            onTriggered:
                                root.queueLifecycleService.executeEnqueue()
                        }

                        ActionButton {
                            width: 150
                            label:
                                root.armedAction === "dequeue"
                                ? "CONFIRM DEQUEUE"
                                : "EXECUTE DEQUEUE"
                            selectedAction:
                                root.armedAction === "dequeue"
                            accent: Colors.red
                            enabledAction:
                                String(
                                    (root.queueLifecycleService.preview || {}).action
                                    || ""
                                ) === "dequeue"
                                && !root.queueLifecycleService.busy
                            onTriggered: root.armOrRun(
                                "dequeue",
                                function() {
                                    root.queueLifecycleService.executeDequeue(
                                        true
                                    );
                                }
                            )
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: parent.height - 176
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue

                ListView {
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    spacing: 4
                    model:
                        root.queueProvider
                        ? root.queueProvider.entries
                        : []

                    delegate: Rectangle {
                        required property var modelData

                        width: ListView.view.width
                        height: 48
                        color: Colors.black
                        border.width: 1
                        border.color:
                            Number(
                                ((modelData || {}).pullRequest || {}).number
                                || 0
                            ) === root.pullRequestNumber
                            ? Colors.orange
                            : Colors.blue

                        Row {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 8

                            GohuText {
                                width: 62
                                anchors.verticalCenter: parent.verticalCenter
                                text: "#" + String(
                                    ((modelData || {}).pullRequest || {}).number
                                    || "?"
                                )
                                font.pixelSize: 10
                                color: Colors.magenta
                            }

                            GohuText {
                                width: parent.width - 210
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    String(
                                        ((modelData || {}).pullRequest || {}).title
                                        || "UNTITLED"
                                    )
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 126
                                anchors.verticalCenter: parent.verticalCenter
                                horizontalAlignment: Text.AlignRight
                                text:
                                    "POS "
                                    + String(modelData.position || "?")
                                    + " // "
                                    + String(
                                        modelData.stateLabel
                                        || modelData.state
                                        || ""
                                      )
                                font.pixelSize: 9
                                color: Colors.blue
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: threadsPane

        Row {
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.42)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta

                Column {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 6

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 6

                        GohuText {
                            width: parent.width - 112
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                "THREADS // "
                                + String(root.threadProvider.unresolvedCount)
                                + " UNRESOLVED // "
                                + String(root.threadProvider.threadCount)
                                + " TOTAL"
                            font.pixelSize: 9
                            color: Colors.magenta
                            elide: Text.ElideRight
                        }

                        ActionButton {
                            width: 106
                            label: "REFRESH"
                            accent: Colors.magenta
                            enabledAction:
                                root.hasTarget
                                && !root.threadProvider.busy
                            onTriggered: root.threadProvider.refresh(
                                root.repositorySlug,
                                root.pullRequestNumber
                            )
                        }
                    }

                    ListView {
                        id: threadList
                        width: parent.width
                        height: parent.height - 36
                        clip: true
                        spacing: 4
                        model:
                            root.threadProvider
                            ? root.threadProvider.threads
                            : []
                        currentIndex: root.selectedThreadIndex

                        delegate: Rectangle {
                            required property int index
                            required property var modelData

                            width: threadList.width
                            height: 62
                            color:
                                root.selectedThreadIndex === index
                                ? Colors.black
                                : Colors.dark
                            border.width:
                                root.selectedThreadIndex === index
                                ? 2
                                : 1
                            border.color:
                                modelData.isResolved
                                ? Colors.green
                                : modelData.isOutdated
                                ? Colors.orange
                                : Colors.magenta

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    root.selectedThreadIndex = index;
                                    root.clearArm();
                                }
                            }

                            Column {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 2

                                GohuText {
                                    width: parent.width
                                    text:
                                        String(modelData.primaryState || "")
                                        + " // "
                                        + String(modelData.path || "NO PATH")
                                    font.pixelSize: 9
                                    color:
                                        modelData.isResolved
                                        ? Colors.green
                                        : modelData.isOutdated
                                        ? Colors.orange
                                        : Colors.magenta
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        "LINE "
                                        + String(
                                            modelData.line >= 0
                                            ? modelData.line
                                            : modelData.originalLine
                                          )
                                        + " // "
                                        + String(modelData.commentCount || 0)
                                        + " COMMENTS // "
                                        + String(
                                            modelData.latestCommentAuthor
                                            || "UNKNOWN"
                                          )
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        String(
                                            (
                                                modelData.latestComment
                                                || {}
                                            ).bodyText
                                            || ""
                                        )
                                    font.pixelSize: 8
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - Math.floor(parent.width * 0.42) - 8
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 6

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedThread
                            ? String(root.selectedThread.path || "NO PATH")
                                + " // LINE "
                                + String(
                                    root.selectedThread.line >= 0
                                    ? root.selectedThread.line
                                    : root.selectedThread.originalLine
                                  )
                                + " // "
                                + String(
                                    root.selectedThread.primaryState || ""
                                  )
                            : "SELECT A REVIEW THREAD"
                        font.pixelSize: 10
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    ListView {
                        width: parent.width
                        height: parent.height - 150
                        clip: true
                        spacing: 4
                        model:
                            root.selectedThread
                            ? root.selectedThread.comments
                            : []

                        delegate: Rectangle {
                            required property var modelData

                            width: ListView.view.width
                            height: Math.max(52, commentText.implicitHeight + 28)
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan

                            Column {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 3

                                GohuText {
                                    width: parent.width
                                    text:
                                        String(modelData.authorLogin || "UNKNOWN")
                                        + " // "
                                        + String(modelData.updatedAt || modelData.createdAt || "")
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    id: commentText
                                    width: parent.width
                                    text: String(modelData.bodyText || modelData.body || "")
                                    font.pixelSize: 9
                                    color: Colors.white
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }

                    MultiLineField {
                        id: replyInput
                        width: parent.width
                        height: 58
                        placeholder: "REPLY TO SELECTED REVIEW THREAD"
                        accent: Colors.magenta
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 7

                        ActionButton {
                            width: 112
                            label: "REPLY"
                            accent: Colors.cyan
                            enabledAction:
                                !!root.selectedThread
                                && Boolean(root.selectedThread.viewerCanReply)
                                && root.topCommentId(root.selectedThread)
                                && replyInput.text.trim().length > 0
                                && !root.threadLifecycleService.busy
                            onTriggered: {
                                root.clearArm();
                                root.threadLifecycleService.replyToThread(
                                    root.repositorySlug,
                                    root.pullRequestNumber,
                                    root.selectedThread.id,
                                    root.topCommentId(root.selectedThread),
                                    replyInput.text.trim()
                                );
                            }
                        }

                        ActionButton {
                            width: 142
                            label:
                                root.selectedThread
                                && root.selectedThread.isResolved
                                ? (
                                    root.armedAction
                                        === "thread-unresolve"
                                    ? "CONFIRM UNRESOLVE"
                                    : "UNRESOLVE"
                                  )
                                : (
                                    root.armedAction
                                        === "thread-resolve"
                                    ? "CONFIRM RESOLVE"
                                    : "RESOLVE"
                                  )
                            selectedAction:
                                root.armedAction === "thread-resolve"
                                || root.armedAction === "thread-unresolve"
                            accent:
                                root.selectedThread
                                && root.selectedThread.isResolved
                                ? Colors.orange
                                : Colors.green
                            enabledAction:
                                !!root.selectedThread
                                && !root.threadLifecycleService.busy
                                && (
                                    root.selectedThread.isResolved
                                    ? Boolean(
                                        root.selectedThread.viewerCanUnresolve
                                      )
                                    : Boolean(
                                        root.selectedThread.viewerCanResolve
                                      )
                                   )
                            onTriggered: {
                                if (!root.selectedThread)
                                    return;

                                const resolving =
                                    !root.selectedThread.isResolved;
                                const token =
                                    resolving
                                    ? "thread-resolve"
                                    : "thread-unresolve";

                                root.armOrRun(
                                    token,
                                    function() {
                                        if (resolving) {
                                            root.threadLifecycleService.resolveThread(
                                                root.repositorySlug,
                                                root.pullRequestNumber,
                                                root.selectedThread.id,
                                                true
                                            );
                                        } else {
                                            root.threadLifecycleService.unresolveThread(
                                                root.repositorySlug,
                                                root.pullRequestNumber,
                                                root.selectedThread.id,
                                                true
                                            );
                                        }
                                    }
                                );
                            }
                        }

                        GohuText {
                            width: parent.width - 268
                            anchors.verticalCenter: parent.verticalCenter
                            horizontalAlignment: Text.AlignRight
                            text:
                                root.threadProvider.threadsTruncated
                                || root.threadProvider.commentsTruncated
                                ? "BOUNDED READ // MORE THREAD DATA EXISTS"
                                : "THREAD READ COMPLETE"
                            font.pixelSize: 8
                            color:
                                root.threadProvider.threadsTruncated
                                || root.threadProvider.commentsTruncated
                                ? Colors.orange
                                : Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
