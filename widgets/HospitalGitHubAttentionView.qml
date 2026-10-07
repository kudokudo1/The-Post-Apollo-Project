import QtQuick
import qs.components

Rectangle {
    id: root

    required property var attentionProvider
    property var responsibilityService: null

    property string stateFilter: "ALL"
    property int selectedIndex: -1

    readonly property var visibleItems:
        !attentionProvider
        ? []
        : stateFilter === "ALL"
        ? attentionProvider.items
        : attentionProvider.itemsForState(stateFilter)

    readonly property var selectedItem:
        selectedIndex >= 0
        && selectedIndex < visibleItems.length
        ? visibleItems[selectedIndex]
        : null

    signal closeRequested()
    signal pullRequestRequested(string repository, int number)
    signal queueRequested(string repository, string branch)

    color: Colors.dark
    border.width: 1
    border.color: Colors.red

    function stateColor(value) {
        const state = String(value || "").toUpperCase();

        if (["NEEDS_ME", "FAILED", "BLOCKED", "CHANGES_REQUESTED"]
                .indexOf(state) >= 0)
            return Colors.red;

        if (["WAITING", "NEEDS_REVIEW", "WAITING_ON_REVIEWER", "PENDING_CHECKS"]
                .indexOf(state) >= 0)
            return Colors.orange;

        return state === "READY" ? Colors.green : Colors.cyan;
    }

    function refresh() {
        if (!attentionProvider || attentionProvider.busy)
            return false;

        return attentionProvider.refresh();
    }

    component AttnButton: Rectangle {
        id: button

        property string label: ""
        property bool selectedAction: false
        property bool enabledAction: true
        property color accent: Colors.cyan

        signal triggered()

        height: 28
        opacity: enabledAction ? 1.0 : 0.34
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

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 7

        Rectangle {
            width: parent.width
            height: 54
            color: Colors.black
            border.width: 1
            border.color: Colors.red

            Row {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 7

                Column {
                    width: parent.width - 260
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    GohuText {
                        width: parent.width
                        text:
                            "GITHUB ATTENTION // "
                            + String(root.visibleItems.length)
                            + " VISIBLE"
                        font.pixelSize: 12
                        color: Colors.red
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            "NEEDS ME "
                            + String(root.attentionProvider.requestedFromMeCount)
                            + " // FAILED "
                            + String(root.attentionProvider.failedCount)
                            + " // BLOCKED "
                            + String(root.attentionProvider.blockedCount)
                            + " // WAITING "
                            + String(root.attentionProvider.waitingCount)
                            + " // READY "
                            + String(root.attentionProvider.readyCount)
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                AttnButton {
                    width: 82
                    label: "← SURGERY"
                    enabledAction: !root.attentionProvider.busy
                    onTriggered: root.closeRequested()
                }

                AttnButton {
                    width: 82
                    label:
                        root.attentionProvider.busy
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.green
                    enabledAction: !root.attentionProvider.busy
                    onTriggered: root.refresh()
                }

                GohuText {
                    width: 82
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        root.attentionProvider.viewerLogin
                        ? "@" + root.attentionProvider.viewerLogin
                        : "NO VIEWER"
                    font.pixelSize: 9
                    color: Colors.magenta
                    elide: Text.ElideLeft
                }
            }
        }

        Row {
            width: parent.width
            height: 28
            spacing: 5

            Repeater {
                model: ["ALL", "NEEDS_ME", "FAILED", "BLOCKED", "WAITING", "READY"]

                delegate: AttnButton {
                    required property string modelData

                    width: (parent.width - 25) / 6
                    label: modelData.replace("_", " ")
                    selectedAction: root.stateFilter === modelData
                    accent: root.stateColor(modelData)

                    onTriggered: {
                        root.stateFilter = modelData;
                        root.selectedIndex = -1;
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 34
            color: Colors.black
            border.width: 1
            border.color:
                root.attentionProvider.lastError
                ? Colors.red
                : Colors.cyan

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    root.attentionProvider.lastError
                    ? "ERROR // " + root.attentionProvider.lastError
                    : String(root.attentionProvider.status || "ATTENTION // READY")
                font.pixelSize: 9
                color:
                    root.attentionProvider.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }

        ListView {
            id: attentionList

            width: parent.width
            height: parent.height - 130
            clip: true
            spacing: 5
            model: root.visibleItems

            delegate: Rectangle {
                id: row

                required property int index
                required property var modelData

                width: ListView.view.width
                height: 104
                color: Colors.black
                border.width: 1
                border.color:
                    root.stateColor(modelData.primaryState)

                Row {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 8

                    Column {
                        width: parent.width - 106
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        GohuText {
                            width: parent.width
                            text:
                                String(modelData.repository || "UNKNOWN")
                                + " // #"
                                + String(modelData.number || "?")
                                + " // "
                                + String(modelData.primaryState || "CLEAR")
                            font.pixelSize: 9
                            color:
                                root.stateColor(modelData.primaryState)
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text: String(modelData.title || "UNTITLED")
                            font.pixelSize: 10
                            color: Colors.white
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "CHECKS "
                                + String(modelData.checkPassed || 0)
                                + " PASS · "
                                + String(modelData.checkFailed || 0)
                                + " FAIL · "
                                + String(modelData.checkPending || 0)
                                + " PENDING // REVIEW "
                                + String(
                                    modelData.reviewDecision
                                    || (
                                        modelData.needsReview
                                        ? "REQUIRED"
                                        : "NONE"
                                      )
                                  )
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text:
                                String(modelData.headRefName || "?")
                                + " → "
                                + String(modelData.baseRefName || "?")
                                + " // MERGE "
                                + String(
                                    modelData.mergeStateStatus
                                    || modelData.mergeable
                                    || "UNKNOWN"
                                  )
                                + " // "
                                + (
                                    Array.isArray(modelData.attentionStates)
                                    ? modelData.attentionStates.join(" // ")
                                    : ""
                                  )
                            font.pixelSize: 8
                            color: Colors.orange
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            property var responsibility:
                                root.responsibilityService
                                ? root.responsibilityService.contextFor(
                                    String(row.modelData.repository || ""),
                                    String(row.modelData.headRefName || "")
                                  )
                                : null
                            text:
                                !responsibility
                                ? "OWNER // UNMAPPED"
                                : (
                                    "OWNER // "
                                    + String(
                                        responsibility.ownerLabel
                                        || "UNMAPPED"
                                      )
                                    + (
                                        responsibility.roomTeam
                                        ? " // ROOM "
                                          + String(responsibility.roomTeam)
                                        : ""
                                      )
                                    + " // "
                                    + String(
                                        responsibility.confidence
                                        || "UNMAPPED"
                                      )
                                  )
                            font.pixelSize: 8
                            color:
                                responsibility
                                && responsibility.confidence === "EXACT"
                                ? Colors.green
                                : responsibility
                                  && responsibility.confidence !== "UNMAPPED"
                                ? Colors.blue
                                : Colors.magenta
                            elide: Text.ElideRight
                        }
                    }

                    Column {
                        width: 98
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 5

                        AttnButton {
                            width: parent.width
                            label: "OPEN PULLS"
                            accent:
                                root.stateColor(row.modelData.primaryState)
                            enabledAction:
                                Number(row.modelData.number || 0) > 0
                                && String(row.modelData.repository || "").length > 0
                            onTriggered:
                                root.pullRequestRequested(
                                    String(row.modelData.repository || ""),
                                    Number(row.modelData.number || 0)
                                )
                        }

                        AttnButton {
                            width: parent.width
                            label: "QUEUE"
                            accent: Colors.blue
                            enabledAction:
                                String(row.modelData.repository || "").length > 0
                                && String(row.modelData.baseRefName || "").length > 0
                            onTriggered:
                                root.queueRequested(
                                    String(row.modelData.repository || ""),
                                    String(row.modelData.baseRefName || "")
                                )
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.NoButton
                    hoverEnabled: true
                }
            }

            GohuText {
                anchors.centerIn: parent
                visible:
                    !root.attentionProvider.busy
                    && root.visibleItems.length === 0
                text:
                    root.stateFilter === "ALL"
                    ? "NO OPEN PULL REQUESTS NEEDING TRIAGE"
                    : "NO ITEMS // " + root.stateFilter
                font.pixelSize: 10
                color: Colors.white
                opacity: 0.44
            }
        }
    }
}
