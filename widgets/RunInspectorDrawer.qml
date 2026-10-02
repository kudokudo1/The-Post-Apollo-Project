import QtQuick
import Quickshell
import qs.components
import QtQuick.Effects

Item {
    id: root

    required property var githubService
    required property var runSummary

    property int selectedStepIndex: -1

    signal closeRequested()
    signal heightRequested(real height)

    readonly property var detail:
        githubService && githubService.inspectedRun
        ? githubService.inspectedRun
        : ({})

    readonly property var jobs:
        githubService && Array.isArray(githubService.inspectorJobs)
        ? githubService.inspectorJobs
        : []

    readonly property var stepRows: {
        const rows = [];

        for (let jobIndex = 0; jobIndex < jobs.length; ++jobIndex) {
            const job = jobs[jobIndex] || {};
            const steps = Array.isArray(job.steps) ? job.steps : [];

            if (steps.length === 0) {
                rows.push({
                    job: String(job.name || "JOB"),
                    name: String(job.name || "JOB"),
                    status: String(job.status || ""),
                    conclusion: String(job.conclusion || "")
                });
                continue;
            }

            for (let stepIndex = 0; stepIndex < steps.length; ++stepIndex) {
                const step = steps[stepIndex] || {};

                rows.push({
                    job: String(job.name || "JOB"),
                    name: String(step.name || ("STEP " + String(stepIndex + 1))),
                    status: String(step.status || ""),
                    conclusion: String(step.conclusion || "")
                });
            }
        }

        return rows;
    }

    function field(name, fallback) {
        const primary = detail && detail[name] !== undefined
                        ? detail[name]
                        : undefined;

        if (primary !== undefined && primary !== null && String(primary) !== "")
            return String(primary);

        if (runSummary && runSummary[name] !== undefined
                && runSummary[name] !== null
                && String(runSummary[name]) !== "")
            return String(runSummary[name]);

        return fallback || "";
    }

    function compactSha(value) {
        const text = String(value || "");
        return text.length > 10 ? text.slice(0, 10) : text;
    }

    function readableTime(value) {
        const text = String(value || "");

        if (!text)
            return "—";

        return text
            .replace("T", " ")
            .replace("Z", " UTC");
    }

    function durationText() {
        const start = Date.parse(field("startedAt", field("createdAt", "")));
        const end = Date.parse(field("updatedAt", ""));

        if (!isFinite(start) || !isFinite(end) || end < start)
            return "—";

        const seconds = Math.max(0, Math.round((end - start) / 1000));

        if (seconds < 60)
            return String(seconds) + "s";

        const minutes = Math.floor(seconds / 60);
        const remainder = seconds % 60;

        return String(minutes) + "m " + String(remainder) + "s";
    }

    function resultColor(status, conclusion) {
        const state = String(status || "").toLowerCase();
        const result = String(conclusion || "").toLowerCase();

        if (result === "success")
            return Colors.green;

        if (result === "failure"
                || result === "cancelled"
                || result === "timed_out")
            return Colors.red;

        if (state === "in_progress" || state === "queued")
            return Colors.orange;

        return Colors.cyan;
    }

    function selectedStepRow() {
        if (selectedStepIndex < 0 || selectedStepIndex >= stepRows.length)
            return null;

        return stepRows[selectedStepIndex];
    }

    function focusedLogText() {
        const full = String(
            githubService && githubService.inspectorLogText
            ? githubService.inspectorLogText
            : ""
        );

        const row = selectedStepRow();

        if (!row || !full)
            return full;

        const jobNeedle = String(row.job || "").trim().toLowerCase();
        const stepNeedle = String(row.name || "").trim().toLowerCase();
        const lines = full.split("\n");
        const matches = [];

        for (let i = 0; i < lines.length; ++i) {
            const line = String(lines[i] || "");
            const lower = line.toLowerCase();
            const fields = line.split("\t");

            if (fields.length >= 2) {
                const jobField = String(fields[0] || "").trim().toLowerCase();
                const stepField = String(fields[1] || "").trim().toLowerCase();

                if (
                    (!jobNeedle || jobField === jobNeedle)
                    && (!stepNeedle || stepField === stepNeedle)
                ) {
                    matches.push(line);
                    continue;
                }
            }

            if (
                (!jobNeedle || lower.indexOf(jobNeedle) >= 0)
                && (!stepNeedle || lower.indexOf(stepNeedle) >= 0)
            )
                matches.push(line);
        }

        if (matches.length > 0)
            return matches.join("\n");

        return "NO MATCHING LOG LINES // "
             + String(row.name || "STEP")
             + "\n\n"
             + full;
    }

    onStepRowsChanged: {
        if (selectedStepIndex >= stepRows.length)
            selectedStepIndex = -1;
    }

    onSelectedStepIndexChanged: {
        Qt.callLater(function() {
            if (logFlickable)
                logFlickable.contentY = 0;
        });
    }

    Connections {
        target: root.githubService

        function onInspectorRunIdChanged() {
            root.selectedStepIndex = -1;
        }
    }

    component DrawerButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool danger: false

        signal triggered()

        height: 28
        color:
            danger && mouse.containsMouse && enabledAction
            ? Colors.red
            : mouse.containsMouse && enabledAction
            ? Colors.yellow
            : Colors.black

        border.width: 1
        border.color:
            danger
            ? Colors.red
            : !enabledAction
            ? Colors.cyan
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 10
            color:
                button.danger
                ? (mouse.containsMouse && button.enabledAction
                   ? Colors.black
                   : Colors.red)
                : !button.enabledAction
                ? Colors.cyan
                : mouse.containsMouse
                ? Colors.orange
                : Colors.cyan
            opacity: button.enabledAction ? 1.0 : 0.34
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

    Rectangle {
        anchors.fill: parent

        color: Colors.black
        border.width: 1
        border.color: Colors.magenta

        RectangularShadow {
            anchors.fill: parent
            spread: 6
            z: -2
            opacity: 0.42
            color: Colors.magenta
        }

        Column {
            anchors {
                fill: parent
                margins: 9
            }

            spacing: 7

            // ===== DRAWER HEADER ==================================

            Row {
                width: parent.width
                height: 30
                spacing: 7
                z: 2

                GohuText {
                    width: parent.width - 276
                    anchors.verticalCenter: parent.verticalCenter

                    text:
                        "RUN INSPECTOR // #"
                        + root.field("databaseId", "?")
                        + " // "
                        + root.field("workflowName", "UNKNOWN WORKFLOW")

                    font.pixelSize: 15
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                GohuText {
                    width: 104
                    anchors.verticalCenter: parent.verticalCenter

                    text:
                        root.githubService.inspectorBusy
                        ? "READING"
                        : root.field("conclusion", root.field("status", "READY")).toUpperCase()

                    horizontalAlignment: Text.AlignRight
                    font.pixelSize: 10

                    color:
                        root.githubService.inspectorBusy
                        ? Colors.orange
                        : root.resultColor(
                              root.field("status", ""),
                              root.field("conclusion", "")
                          )
                }

                DrawerButton {
                    width: 76
                    label: "REFRESH"
                    enabledAction:
                        root.runSummary
                        && !root.githubService.inspectorBusy

                    onTriggered:
                        root.githubService.inspectRun(
                            root.field("databaseId", "")
                        )
                }

                DrawerButton {
                    width: 74
                    label: "CLOSE"
                    danger: true

                    onTriggered: root.closeRequested()
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.7
            }

            // ===== BODY ===========================================

            Row {
                width: parent.width
                height: parent.height - 45
                spacing: 8

                // LEFT = identity + steps.
                Rectangle {
                    width: 336
                    height: parent.height

                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.blue

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }

                        spacing: 5

                        GohuText {
                            text: "RUN IDENTITY"
                            font.pixelSize: 13
                            color: Colors.magenta
                        }

                        Grid {
                            width: parent.width
                            columns: 2
                            columnSpacing: 7
                            rowSpacing: 3

                            GohuText {
                                width: 72
                                text: "BRANCH"
                                font.pixelSize: 9
                                color: Colors.orange
                            }

                            GohuText {
                                width: 238
                                text: root.field("headBranch", "—")
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 72
                                text: "COMMIT"
                                font.pixelSize: 9
                                color: Colors.orange
                            }

                            GohuText {
                                width: 238
                                text: root.compactSha(root.field("headSha", "—"))
                                font.pixelSize: 10
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 72
                                text: "EVENT"
                                font.pixelSize: 9
                                color: Colors.orange
                            }

                            GohuText {
                                width: 238
                                text: root.field("event", "—").toUpperCase()
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 72
                                text: "DURATION"
                                font.pixelSize: 9
                                color: Colors.orange
                            }

                            GohuText {
                                width: 238
                                text: root.durationText()
                                font.pixelSize: 10
                                color: Colors.white
                            }

                            GohuText {
                                width: 72
                                text: "STARTED"
                                font.pixelSize: 8
                                color: Colors.orange
                            }

                            GohuText {
                                width: 238
                                text: root.readableTime(
                                    root.field(
                                        "startedAt",
                                        root.field("createdAt", "")
                                    )
                                )
                                font.pixelSize: 9
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.blue
                            opacity: 0.55
                        }

                        Row {
                            width: parent.width
                            height: 18

                            GohuText {
                                width: parent.width - 66
                                text: "JOBS / STEPS"
                                font.pixelSize: 11
                                color: Colors.magenta
                            }

                            GohuText {
                                width: 66
                                text: String(root.stepRows.length)
                                horizontalAlignment: Text.AlignRight
                                font.pixelSize: 10
                                color: Colors.orange
                            }
                        }

                        Flickable {
                            width: parent.width
                            height: parent.height - 157

                            clip: true
                            contentWidth: width
                            contentHeight: stepColumn.height
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: stepColumn

                                width: parent.width
                                spacing: 3

                                Repeater {
                                    model: root.stepRows

                                    Rectangle {
                                        id: stepRow

                                        required property int index
                                        required property var modelData

                                        readonly property bool selected:
                                            root.selectedStepIndex === index
                                        readonly property bool hovered:
                                            stepMouse.containsMouse

                                        width: stepColumn.width
                                        height: 29

                                        color:
                                            selected
                                            ? Colors.dark
                                            : hovered
                                            ? "#17121D"
                                            : Colors.black

                                        border.width: selected ? 2 : 1
                                        border.color:
                                            selected
                                            ? Colors.magenta
                                            : hovered
                                            ? Colors.orange
                                            : root.resultColor(
                                                  modelData.status,
                                                  modelData.conclusion
                                              )

                                        RectangularShadow {
                                            anchors.fill: parent
                                            spread: 3
                                            z: -1
                                            opacity:
                                                stepRow.selected
                                                ? 0.42
                                                : stepRow.hovered
                                                ? 0.22
                                                : 0.0
                                            color:
                                                stepRow.selected
                                                ? Colors.magenta
                                                : Colors.orange
                                        }

                                        Row {
                                            anchors {
                                                fill: parent
                                                margins: 4
                                            }

                                            spacing: 5

                                            GohuText {
                                                width: 22
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: String(index + 1)
                                                font.pixelSize: 9
                                                color:
                                                    stepRow.selected
                                                    ? Colors.magenta
                                                    : Colors.orange
                                            }

                                            GohuText {
                                                width: parent.width - 96
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: String(modelData.name || "STEP")
                                                font.pixelSize: 9
                                                color:
                                                    stepRow.selected
                                                    ? Colors.magenta
                                                    : stepRow.hovered
                                                    ? Colors.orange
                                                    : Colors.white
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: 64
                                                anchors.verticalCenter: parent.verticalCenter
                                                text:
                                                    String(
                                                        modelData.conclusion
                                                        || modelData.status
                                                        || "UNKNOWN"
                                                    ).toUpperCase()
                                                horizontalAlignment: Text.AlignRight
                                                font.pixelSize: 8
                                                color:
                                                    root.resultColor(
                                                        modelData.status,
                                                        modelData.conclusion
                                                    )
                                            }
                                        }

                                        MouseArea {
                                            id: stepMouse

                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor

                                            onClicked: {
                                                root.selectedStepIndex =
                                                    stepRow.selected
                                                    ? -1
                                                    : stepRow.index;
                                            }
                                        }
                                    }
                                }

                                GohuText {
                                    width: parent.width
                                    visible:
                                        !root.githubService.inspectorBusy
                                        && root.stepRows.length === 0

                                    text:
                                        root.githubService.inspectorError
                                        ? "STEP DATA UNAVAILABLE"
                                        : "NO STEP DATA"

                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 9
                                    color:
                                        root.githubService.inspectorError
                                        ? Colors.red
                                        : Colors.cyan
                                    opacity: 0.55
                                }
                            }
                        }
                    }
                }

                // RIGHT = raw run log stream.
                Rectangle {
                    width: parent.width - 344
                    height: parent.height

                    color: Colors.dark
                    border.width: 1
                    border.color:
                        root.githubService.inspectorError
                        ? Colors.red
                        : Colors.orange

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }

                        spacing: 5

                        Row {
                            width: parent.width
                            height: 24
                            spacing: 6

                            GohuText {
                                width: parent.width - 188
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.selectedStepIndex >= 0
                                    ? "OUTPUT // STEP FOCUS"
                                    : "OUTPUT // LOG STREAM"
                                font.pixelSize: 13
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 112
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.githubService.inspectorBusy
                                    ? "READING"
                                    : root.githubService.inspectorError
                                    ? "ERROR"
                                    : root.selectedStepIndex >= 0
                                    ? (
                                          "STEP "
                                          + String(root.selectedStepIndex + 1)
                                      )
                                    : "RUN LOG"
                                horizontalAlignment: Text.AlignRight
                                font.pixelSize: 9
                                color:
                                    root.githubService.inspectorError
                                    ? Colors.red
                                    : Colors.orange
                            }

                            DrawerButton {
                                width: 58
                                height: 22
                                label: "ALL"
                                enabledAction: root.selectedStepIndex >= 0

                                onTriggered:
                                    root.selectedStepIndex = -1
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.orange
                            opacity: 0.5
                        }

                        Flickable {
                            id: logFlickable

                            width: parent.width
                            height: parent.height - 30

                            clip: true
                            contentWidth: width
                            contentHeight: Math.max(height, logText.implicitHeight)
                            boundsBehavior: Flickable.StopAtBounds

                            GohuText {
                                id: logText

                                width: parent.width

                                text:
                                    root.githubService.inspectorBusy
                                    ? "PX // READING RUN METADATA + LOGS…"
                                    : root.githubService.inspectorError
                                    ? (
                                          "INSPECTOR ERROR // "
                                          + root.githubService.inspectorError
                                          + "\n\n"
                                          + root.githubService.inspectorLogText
                                      )
                                    : root.focusedLogText()
                                      ? root.focusedLogText()
                                      : "NO LOG OUTPUT"

                                textFormat: Text.PlainText
                                wrapMode: Text.WrapAnywhere
                                font.pixelSize: 11
                                color:
                                    root.githubService.inspectorError
                                    ? Colors.red
                                    : Colors.white
                            }
                        }
                    }
                }
            }
        }

        // Overlay the title area without consuming Column height.
        MouseArea {
            id: resizeHandle

            anchors {
                left: parent.left
                top: parent.top
                leftMargin: 9
                topMargin: 9
            }

            width: parent.width - 294
            height: 30
            z: 20

            hoverEnabled: true
            cursorShape: Qt.SizeVerCursor

            property real startHeight: 0
            property real startSceneY: 0

            onPressed: function(mouse) {
                startHeight = root.height;
                startSceneY = mapToItem(null, mouse.x, mouse.y).y;
            }

            onPositionChanged: function(mouse) {
                if (!pressed)
                    return;

                const sceneY = mapToItem(null, mouse.x, mouse.y).y;

                root.heightRequested(
                    startHeight + (startSceneY - sceneY)
                );
            }
        }
    }
}
