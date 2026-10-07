import QtQuick
import qs.components

Item {
    id: root

    required property var reportService
    required property var runtimeService

    property int selectedIndex: -1

    readonly property var displayReports: {
        const source =
            reportService
            && Array.isArray(reportService.reports)
            ? reportService.reports
            : [];

        return source.slice().reverse();
    }

    readonly property var selectedReport: {
        if (selectedIndex < 0
                || selectedIndex >= displayReports.length)
            return null;

        return displayReports[selectedIndex] || null;
    }

    signal closeRequested()
    signal chatRequested()

    function shortSha(value) {
        const sha = String(value || "");
        return sha.length > 12 ? sha.slice(0, 12) : sha;
    }

    function evidenceColor(report) {
        return String((report || {}).gitEvidenceStatus || "")
               === "VERIFIED"
               ? Colors.green
               : Colors.orange;
    }

    function feedbackSessionMatches(report) {
        const row = report || {};
        const reportSession =
            String(row.sessionId || "").trim();
        const activeSession =
            String(runtimeService.sessionId || "").trim();

        return reportSession.length > 0
            && activeSession.length > 0
            && reportSession === activeSession;
    }

    function filesSummary(report) {
        const row = report || {};
        const count = Number(row.changedFileCount || 0);
        const insertions = Number(row.insertions || 0);
        const deletions = Number(row.deletions || 0);

        return String(count)
            + " FILE"
            + (count === 1 ? "" : "S")
            + " // +"
            + String(insertions)
            + " / -"
            + String(deletions);
    }

    onDisplayReportsChanged: {
        if (displayReports.length === 0) {
            selectedIndex = -1;
            return;
        }

        if (selectedIndex < 0
                || selectedIndex >= displayReports.length)
            selectedIndex = 0;
    }

    onSelectedIndexChanged: {
        feedbackEditor.text = "";
    }

    component ReportButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true

        signal triggered()

        height: 28
        color:
            mouse.pressed
            ? accent
            : Colors.black
        border.width:
            mouse.containsMouse ? 2 : 1
        border.color: accent
        opacity: enabledAction ? 1.0 : 0.38

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 9
            color:
                mouse.pressed
                ? Colors.black
                : button.accent
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
        spacing: 8

        Rectangle {
            width: parent.width
            height: 42
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta

            Row {
                anchors {
                    fill: parent
                    margins: 7
                }
                spacing: 8

                GohuText {
                    width: parent.width - 284
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        "ROOM REPORTS // "
                        + (
                            reportService.roomId
                            ? reportService.roomId
                            : "NO ROOM"
                          )
                        + " // "
                        + String(reportService.reportCount)
                    font.pixelSize: 12
                    color: Colors.magenta
                    elide: Text.ElideRight
                }

                ReportButton {
                    width: 86
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        reportService.loading
                        ? "REFRESHING"
                        : "REFRESH"
                    accent: Colors.blue
                    enabledAction: !reportService.loading
                    onTriggered: reportService.refresh()
                }

                ReportButton {
                    width: 82
                    anchors.verticalCenter: parent.verticalCenter
                    label: "CHAT"
                    accent: Colors.cyan
                    onTriggered: root.chatRequested()
                }

                ReportButton {
                    width: 92
                    anchors.verticalCenter: parent.verticalCenter
                    label: "CLOSE"
                    accent: Colors.orange
                    onTriggered: root.closeRequested()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 50
            spacing: 8

            Rectangle {
                width: Math.max(260, parent.width * 0.32)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.blue

                ListView {
                    id: reportList

                    anchors {
                        fill: parent
                        margins: 7
                    }
                    spacing: 6
                    clip: true
                    model: root.displayReports

                    delegate: Rectangle {
                        required property var modelData
                        required property int index

                        width: reportList.width
                        height: 92
                        color:
                            root.selectedIndex === index
                            ? Colors.black
                            : Colors.dark
                        border.width:
                            root.selectedIndex === index
                            ? 2 : 1
                        border.color:
                            root.selectedIndex === index
                            ? Colors.magenta
                            : root.evidenceColor(modelData)

                        Column {
                            anchors {
                                fill: parent
                                margins: 7
                            }
                            spacing: 3

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        modelData.title
                                        || "DOCTOR NOTE"
                                    )
                                font.pixelSize: 10
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        modelData.providerId
                                        || "NO PROVIDER"
                                    ).toUpperCase()
                                    + " // "
                                    + String(
                                        modelData.gitEvidenceStatus
                                        || "UNAVAILABLE"
                                    )
                                font.pixelSize: 8
                                color:
                                    root.evidenceColor(modelData)
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.filesSummary(modelData)
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        modelData.createdAt
                                        || ""
                                    )
                                font.pixelSize: 8
                                color: Colors.white
                                opacity: 0.72
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked:
                                root.selectedIndex = index
                        }
                    }

                    GohuText {
                        anchors.centerIn: parent
                        visible:
                            !reportService.loading
                            && root.displayReports.length === 0
                            && !reportService.lastError
                        text: "NO ROOM REPORTS // USE QUICK REPORT"
                        font.pixelSize: 10
                        color: Colors.blue
                    }

                    GohuText {
                        anchors.centerIn: parent
                        visible: reportService.loading
                        text: "LOADING ROOM REPORTS…"
                        font.pixelSize: 10
                        color: Colors.cyan
                    }
                }
            }

            Rectangle {
                width: parent.width
                       - Math.max(260, parent.width * 0.32)
                       - parent.spacing
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color:
                    root.selectedReport
                    ? root.evidenceColor(root.selectedReport)
                    : Colors.magenta

                Column {
                    anchors {
                        fill: parent
                        margins: 10
                    }
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedReport
                            ? String(
                                root.selectedReport.title
                                || "DOCTOR NOTE"
                              )
                            : "ROOM REPORT // NONE SELECTED"
                        font.pixelSize: 13
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedReport
                            ? (
                                String(
                                    root.selectedReport.doctorId
                                    || "DOCTOR"
                                  ).toUpperCase()
                                + " // "
                                + String(
                                    root.selectedReport.providerId
                                    || "NO PROVIDER"
                                  ).toUpperCase()
                                + " // "
                                + String(
                                    root.selectedReport.kind
                                    || "DOCTOR_NOTE"
                                  )
                              )
                            : ""
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        width: parent.width
                        height: 72
                        visible: root.selectedReport !== null
                        color: Colors.black
                        border.width: 1
                        border.color:
                            root.evidenceColor(root.selectedReport)

                        Column {
                            anchors {
                                fill: parent
                                margins: 7
                            }
                            spacing: 3

                            GohuText {
                                width: parent.width
                                text:
                                    "GIT EVIDENCE // "
                                    + String(
                                        root.selectedReport
                                            .gitEvidenceStatus
                                        || "UNAVAILABLE"
                                      )
                                    + " // "
                                    + (
                                        root.selectedReport.dirty
                                        ? "DIRTY"
                                        : "CLEAN"
                                      )
                                font.pixelSize: 9
                                color:
                                    root.evidenceColor(
                                        root.selectedReport
                                    )
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        root.selectedReport.repository
                                        || "NO REPOSITORY"
                                      )
                                    + " // "
                                    + String(
                                        root.selectedReport.branch
                                        || "NO BRANCH"
                                      )
                                    + " // "
                                    + root.shortSha(
                                        root.selectedReport.headSha
                                      )
                                font.pixelSize: 8
                                color: Colors.white
                                elide: Text.ElideMiddle
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.filesSummary(
                                        root.selectedReport
                                    )
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Flickable {
                        id: detailFlick

                        width: parent.width
                        height:
                            Math.max(
                                80,
                                parent.height
                                - (
                                    root.selectedReport
                                    ? 222 : 138
                                  )
                            )
                        clip: true
                        contentWidth: width
                        contentHeight:
                            reportBody.implicitHeight
                            + changedFilesText.implicitHeight
                            + 18

                        Column {
                            id: detailColumn

                            width: detailFlick.width
                            spacing: 10

                            GohuText {
                                id: changedFilesText

                                width: parent.width
                                visible:
                                    root.selectedReport
                                    && Array.isArray(
                                        root.selectedReport.changedFiles
                                    )
                                    && root.selectedReport.changedFiles.length > 0
                                text:
                                    root.selectedReport
                                    ? (
                                        "CHANGED FILES\n"
                                        + root.selectedReport.changedFiles
                                            .map(function(path) {
                                                return "• " + path;
                                            })
                                            .join("\n")
                                      )
                                    : ""
                                font.pixelSize: 8
                                color: Colors.blue
                                wrapMode: Text.WrapAnywhere
                            }

                            GohuText {
                                id: reportBody

                                width: parent.width
                                text:
                                    root.selectedReport
                                    ? String(
                                        root.selectedReport.body
                                        || ""
                                      )
                                    : (
                                        reportService.lastError
                                        ? reportService.lastError
                                        : "SELECT A ROOM REPORT"
                                      )
                                textFormat: Text.MarkdownText
                                font.pixelSize: 10
                                color:
                                    reportService.lastError
                                    && !root.selectedReport
                                    ? Colors.red
                                    : Colors.white
                                wrapMode: Text.Wrap
                                onLinkActivated: function(link) {
                                    Qt.openUrlExternally(link);
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: feedbackComposer

                        width: parent.width
                        height: 88
                        visible: root.selectedReport !== null
                        color: Colors.black
                        border.width: 1
                        border.color:
                            root.feedbackSessionMatches(
                                root.selectedReport
                            )
                            ? Colors.red
                            : Colors.orange

                        Column {
                            anchors {
                                fill: parent
                                margins: 7
                            }
                            spacing: 5

                            GohuText {
                                width: parent.width
                                text: {
                                    if (!root.selectedReport)
                                        return "";

                                    if (!root.feedbackSessionMatches(
                                                root.selectedReport))
                                        return "REPORT BUG // ARCHIVED SESSION // FEEDBACK DISABLED";

                                    if (runtimeService.feedbackRunning
                                            && runtimeService.feedbackReportId
                                               === String(
                                                    root.selectedReport.id
                                                  ))
                                        return "REPORT BUG // SENDING TO SAME DOCTOR SESSION…";

                                    return "REPORT BUG // SEND FEEDBACK TO SAME DOCTOR SESSION";
                                }
                                font.pixelSize: 8
                                color:
                                    root.feedbackSessionMatches(
                                        root.selectedReport
                                    )
                                    ? Colors.red
                                    : Colors.orange
                                elide: Text.ElideRight
                            }

                            Row {
                                width: parent.width
                                height: 54
                                spacing: 7

                                Rectangle {
                                    width: parent.width - 124
                                    height: parent.height
                                    color: Colors.dark
                                    border.width: 1
                                    border.color:
                                        feedbackEditor.activeFocus
                                        ? Colors.orange
                                        : Colors.cyan

                                    TextEdit {
                                        id: feedbackEditor

                                        anchors {
                                            fill: parent
                                            margins: 6
                                        }
                                        color: Colors.white
                                        font.family:
                                            "GohuFont 11 Nerd Font Mono"
                                        font.pixelSize: 9
                                        wrapMode: TextEdit.Wrap
                                        selectByMouse: true
                                        enabled:
                                            root.feedbackSessionMatches(
                                                root.selectedReport
                                            )
                                            && !runtimeService.feedbackRunning
                                    }

                                    GohuText {
                                        anchors {
                                            left: parent.left
                                            right: parent.right
                                            top: parent.top
                                            margins: 7
                                        }
                                        visible:
                                            !feedbackEditor.text.length
                                            && !feedbackEditor.activeFocus
                                        text:
                                            "Describe the bug, regression, missing verification, or correction…"
                                        font.pixelSize: 8
                                        color: Colors.white
                                        opacity: 0.45
                                        elide: Text.ElideRight
                                    }
                                }

                                ReportButton {
                                    width: 117
                                    height: parent.height
                                    anchors.verticalCenter: parent.verticalCenter
                                    label:
                                        runtimeService.feedbackRunning
                                        && runtimeService.feedbackReportId
                                           === String(
                                                root.selectedReport.id
                                              )
                                        ? "SENDING…"
                                        : "REPORT BUG"
                                    accent: Colors.red
                                    enabledAction:
                                        root.selectedReport !== null
                                        && root.feedbackSessionMatches(
                                            root.selectedReport
                                        )
                                        && feedbackEditor.text.trim().length > 0
                                        && !runtimeService.feedbackRunning
                                        && !runtimeService.operating
                                        && !runtimeService.quickRunning
                                        && !runtimeService.cancelling

                                    onTriggered: {
                                        runtimeService.reportFeedback(
                                            root.selectedReport.id,
                                            feedbackEditor.text
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: runtimeService

        function onReportFeedbackCompleted(reportId, result) {
            if (root.selectedReport
                    && String(root.selectedReport.id)
                       === String(reportId))
                feedbackEditor.text = "";

            reportService.refresh();
        }
    }
}
