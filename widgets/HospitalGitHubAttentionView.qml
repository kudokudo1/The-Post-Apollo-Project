import QtQuick
import qs.components

Rectangle {
    id: root

    required property var attentionProvider
    property var responsibilityService: null

    property string stateFilter: "ALL"
    property int selectedIndex: -1

    readonly property var visibleItems: root.triageRows()

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

    function responsibilityFor(itemValue) {
        const item = itemValue || {};

        if (!responsibilityService)
            return null;

        return responsibilityService.contextFor(
            String(item.repository || ""),
            String(item.headRefName || "")
        );
    }

    function attentionStatesFor(itemValue) {
        const item = itemValue || {};
        return Array.isArray(item.attentionStates)
            ? item.attentionStates : [];
    }

    function filterMatches(itemValue) {
        const item = itemValue || {};
        const states = attentionStatesFor(item);
        const filter = String(stateFilter || "ALL").toUpperCase();

        if (filter === "ALL")
            return true;
        if (filter === "REVIEW")
            return !!item.needsMyReview
                || states.indexOf("NEEDS_REVIEW") >= 0;
        if (filter === "OWNED") {
            const context = responsibilityFor(item);
            return !!context
                && String(context.confidence || "") !== "UNMAPPED";
        }
        if (filter === "UNMAPPED") {
            const context = responsibilityFor(item);
            return !context
                || String(context.confidence || "") === "UNMAPPED";
        }

        return states.indexOf(filter) >= 0
            || String(item.primaryState || "") === filter;
    }

    function triageScore(itemValue) {
        const item = itemValue || {};
        const states = attentionStatesFor(item);
        let score = 0;

        if (states.indexOf("NEEDS_ME") >= 0)
            score += 120;
        if (states.indexOf("FAILED") >= 0)
            score += 105;
        if (states.indexOf("CHANGES_REQUESTED") >= 0)
            score += 100;
        if (states.indexOf("BLOCKED") >= 0)
            score += 90;
        if (states.indexOf("NEEDS_REVIEW") >= 0)
            score += 82;
        if (states.indexOf("READY") >= 0)
            score += 72;
        if (states.indexOf("PENDING_CHECKS") >= 0)
            score += 50;
        if (states.indexOf("WAITING_ON_REVIEWER") >= 0)
            score += 42;
        if (states.indexOf("WAITING") >= 0)
            score += 35;

        const context = responsibilityFor(item);
        if (context) {
            const confidence = String(context.confidence || "");
            if (confidence === "EXACT")
                score += 18;
            else if (confidence === "STRONG")
                score += 12;
            else if (confidence !== "UNMAPPED")
                score += 6;

            if (String(context.roomTeam || "")
                    === String(responsibilityService.currentRoomId || ""))
                score += 16;
        }

        return score;
    }

    function triageReason(itemValue) {
        const item = itemValue || {};
        const states = attentionStatesFor(item);
        const reasons = [];

        for (const state of [
            "NEEDS_ME",
            "FAILED",
            "CHANGES_REQUESTED",
            "BLOCKED",
            "NEEDS_REVIEW",
            "READY",
            "PENDING_CHECKS",
            "WAITING_ON_REVIEWER",
            "WAITING"
        ]) {
            if (states.indexOf(state) >= 0)
                reasons.push(state.replace(/_/g, " "));
        }

        const context = responsibilityFor(item);
        if (context
                && String(context.confidence || "") !== "UNMAPPED") {
            reasons.push(
                "OWNER " + String(context.ownerLabel || "MAPPED")
            );
        } else {
            reasons.push("OWNER UNMAPPED");
        }

        return reasons.join(" // ");
    }

    function triageRows() {
        if (!attentionProvider)
            return [];

        const source =
            Array.isArray(attentionProvider.items)
            ? attentionProvider.items.slice()
            : [];
        const filtered = source.filter(function(item) {
            return root.filterMatches(item);
        });

        filtered.sort(function(a, b) {
            const scoreDiff =
                root.triageScore(b) - root.triageScore(a);
            if (scoreDiff !== 0)
                return scoreDiff;

            const updatedA = Date.parse(String((a || {}).updatedAt || "")) || 0;
            const updatedB = Date.parse(String((b || {}).updatedAt || "")) || 0;
            if (updatedA !== updatedB)
                return updatedB - updatedA;

            return Number((a || {}).number || 0)
                - Number((b || {}).number || 0);
        });

        return filtered;
    }

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
                model: [
                    "ALL",
                    "NEEDS_ME",
                    "REVIEW",
                    "FAILED",
                    "BLOCKED",
                    "WAITING",
                    "READY",
                    "OWNED",
                    "UNMAPPED"
                ]

                delegate: AttnButton {
                    required property string modelData

                    width: (parent.width - 40) / 9
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
                height: 118
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
                                "TRIAGE "
                                + String(root.triageScore(modelData))
                                + " // "
                                + root.triageReason(modelData)
                            font.pixelSize: 8
                            color: Colors.magenta
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
