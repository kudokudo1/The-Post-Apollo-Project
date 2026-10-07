import QtQuick
import qs.components

Rectangle {
    id: root

    required property var queueProvider

    property string repositorySlug: ""
    property string branchName: ""

    signal closeRequested()
    signal pullRequestRequested(string repository, int number)

    color: Colors.dark
    border.width: 1
    border.color: Colors.blue

    function stateColor(value) {
        const state = String(value || "").toUpperCase();

        if (state === "UNMERGEABLE" || state === "BLOCKED")
            return Colors.red;
        if (state === "AWAITING_CHECKS" || state === "LOCKED")
            return Colors.orange;
        if (state === "MERGEABLE" || state === "READY")
            return Colors.green;

        return Colors.blue;
    }

    function refresh() {
        if (!repositorySlug || queueProvider.busy)
            return false;

        return queueProvider.refresh(repositorySlug, branchName);
    }

    component QueueButton: Rectangle {
        id: button
        property string label: ""
        property color accent: Colors.blue
        property bool enabledAction: true
        signal triggered()

        height: 28
        opacity: enabledAction ? 1.0 : 0.34
        color: mouse.containsMouse ? Colors.black : Colors.dark
        border.width: 1
        border.color: accent

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
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: button.triggered()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 7

        Rectangle {
            width: parent.width
            height: 56
            color: Colors.black
            border.width: 1
            border.color: Colors.blue

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 7

                Column {
                    width: parent.width - 184
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    GohuText {
                        width: parent.width
                        text:
                            "MERGE QUEUE // "
                            + String(root.repositorySlug || "NO REPOSITORY")
                        font.pixelSize: 12
                        color: Colors.blue
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            "BRANCH // "
                            + String(
                                root.queueProvider.resolvedBranch
                                || root.branchName
                                || "DEFAULT"
                              )
                            + " // "
                            + String(root.queueProvider.totalCount)
                            + " ENTRIES"
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                QueueButton {
                    width: 82
                    label: "← ATTENTION"
                    onTriggered: root.closeRequested()
                }

                QueueButton {
                    width: 82
                    label:
                        root.queueProvider.busy
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.green
                    enabledAction: !root.queueProvider.busy
                    onTriggered: root.refresh()
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 38
            color: Colors.black
            border.width: 1
            border.color:
                root.queueProvider.lastError
                ? Colors.red
                : Colors.cyan

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    root.queueProvider.lastError
                    ? "QUEUE ERROR // " + root.queueProvider.lastError
                    : root.queueProvider.queueAvailable
                    ? (
                        "READY "
                        + String(root.queueProvider.mergeableCount)
                        + " // CHECKS "
                        + String(root.queueProvider.awaitingChecksCount)
                        + " // BLOCKED "
                        + String(root.queueProvider.unmergeableCount)
                        + " // LOCKED "
                        + String(root.queueProvider.lockedCount)
                      )
                    : "NATIVE MERGE QUEUE NOT CONFIGURED"
                font.pixelSize: 9
                color:
                    root.queueProvider.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }

        Rectangle {
            width: parent.width
            height: 42
            color: Colors.black
            border.width: 1
            border.color: Colors.blue

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    "METHOD // "
                    + String(
                        (root.queueProvider.configuration || {}).mergeMethod
                        || "UNKNOWN"
                      )
                    + " // STRATEGY // "
                    + String(
                        (root.queueProvider.configuration || {}).mergingStrategy
                        || "UNKNOWN"
                      )
                    + " // NEXT ETA // "
                    + String(
                        root.queueProvider.nextEntryEstimatedTimeToMerge >= 0
                        ? root.queueProvider.nextEntryEstimatedTimeToMerge
                        : "UNKNOWN"
                      )
                font.pixelSize: 9
                color: Colors.blue
                elide: Text.ElideRight
            }
        }

        ListView {
            width: parent.width
            height: parent.height - 157
            clip: true
            spacing: 5
            model: root.queueProvider.entries

            delegate: Rectangle {
                id: row
                required property var modelData

                width: ListView.view.width
                height: 92
                color: Colors.black
                border.width: 1
                border.color: root.stateColor(modelData.state)

                Row {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 8

                    Column {
                        width: parent.width - 108
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        GohuText {
                            width: parent.width
                            text:
                                "POSITION "
                                + String(row.modelData.position || "?")
                                + " // "
                                + String(
                                    row.modelData.stateLabel
                                    || row.modelData.state
                                    || "UNKNOWN"
                                  )
                                + " // #"
                                + String(
                                    (row.modelData.pullRequest || {}).number
                                    || "?"
                                  )
                            font.pixelSize: 9
                            color: root.stateColor(row.modelData.state)
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                String(
                                    (row.modelData.pullRequest || {}).title
                                    || "UNTITLED"
                                  )
                            font.pixelSize: 10
                            color: Colors.white
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "MERGE // "
                                + String(
                                    (row.modelData.pullRequest || {}).mergeStateStatus
                                    || (row.modelData.pullRequest || {}).mergeable
                                    || "UNKNOWN"
                                  )
                                + " // REVIEW // "
                                + String(
                                    (row.modelData.pullRequest || {}).reviewDecision
                                    || "NONE"
                                  )
                            font.pixelSize: 8
                            color:
                                root.stateColor(
                                    row.modelData.state
                                )
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "ENQUEUER // "
                                + String(row.modelData.enqueuer || "UNKNOWN")
                                + " // ETA // "
                                + String(
                                    row.modelData.estimatedTimeToMerge >= 0
                                    ? row.modelData.estimatedTimeToMerge
                                    : "UNKNOWN"
                                  )
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }

                    QueueButton {
                        width: 100
                        anchors.verticalCenter: parent.verticalCenter
                        label: "OPEN PULLS"
                        accent: root.stateColor(row.modelData.state)
                        enabledAction:
                            Number(
                                (row.modelData.pullRequest || {}).number
                                || 0
                            ) > 0
                        onTriggered:
                            root.pullRequestRequested(
                                root.repositorySlug,
                                Number(
                                    (row.modelData.pullRequest || {}).number
                                    || 0
                                )
                            )
                    }
                }
            }

            GohuText {
                anchors.centerIn: parent
                visible:
                    !root.queueProvider.busy
                    && root.queueProvider.entries.length === 0
                text:
                    root.queueProvider.queueAvailable
                    ? "MERGE QUEUE EMPTY"
                    : "NO MERGE QUEUE DATA"
                font.pixelSize: 10
                color: Colors.white
                opacity: 0.44
            }
        }
    }
}
