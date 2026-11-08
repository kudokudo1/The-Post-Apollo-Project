import QtQuick
import qs.components
import "../services/hospital"
import "../services/hospital/HospitalRoomContinuityPolicy.js" as ContinuityPolicy

// A permanent Room's readable continuity, even when no Session exists.
// Records are loaded only while this screen is open; no PX writer is used.
Item {
    id: root
    property bool active: false
    property string roomId: ""
    property var roomData: ({})
    property var allSessions: []
    property bool sessionsLoaded: false
    readonly property var overview: ContinuityPolicy.project({
        roomId: root.roomId,
        snapshot: continuity.snapshot,
        loaded: continuity.loaded,
        sessions: root.allSessions,
        sessionsLoaded: root.sessionsLoaded
    })
    readonly property color recoveryColor:
        overview.recovery.severity >= 3 ? Colors.red
        : overview.recovery.severity === 2 ? Colors.orange
        : overview.recovery.severity === 1 ? Colors.yellow : Colors.cyan

    function refresh() { return continuity.refresh(); }
    function preview(value, maximum) {
        return ContinuityPolicy.excerpt(value, maximum || 700);
    }

    HospitalRoomContinuityService {
        id: continuity
        roomId: root.active ? root.roomId : ""
        enabled: root.active && root.roomId.length > 0
    }

    Flickable {
        id: contentScroll
        anchors.fill: parent
        visible: root.active
        clip: true
        contentWidth: width
        contentHeight: contentColumn.implicitHeight + 12
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: contentScroll.width
            spacing: 9

            Row {
                width: parent.width
                height: 29
                spacing: 8
                GohuText {
                    width: parent.width - 91
                    height: parent.height
                    text: "PERMANENT ROOM // CONTINUITY"
                    font.pixelSize: 12
                    color: Colors.magenta
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
                HospitalActionButton {
                    width: 83
                    height: 27
                    label: continuity.loading ? "READING" : "REFRESH"
                    compactIcon: "↻"
                    accent: Colors.cyan
                    enabledAction: !continuity.loading
                    onTriggered: root.refresh()
                }
            }
            GohuText {
                width: parent.width
                text: "ROOM // " + root.roomId + "  //  SESSION NOT REQUIRED TO READ"
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideMiddle
            }
            GohuText {
                width: parent.width
                visible: continuity.loading || !!continuity.lastError
                    || !root.overview.verified
                text: continuity.lastError ||
                    (continuity.loading
                        ? "READING PX " + continuity.readStage.toUpperCase() + "..."
                        : "ROOM SNAPSHOT NOT VERIFIED // REFRESH OR REGISTER THIS ROOM")
                font.pixelSize: 10
                color: continuity.lastError ? Colors.red : Colors.orange
                wrapMode: Text.Wrap
            }

            Rectangle {
                width: parent.width
                height: recoveryDetails.implicitHeight + 37
                color: Colors.black
                border.width: 1
                border.color: root.recoveryColor
                Column {
                    id: recoveryDetails
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 8
                    spacing: 5
                    GohuText {
                        width: parent.width
                        text: "RECOVERY // " + root.overview.recovery.label
                        color: root.recoveryColor
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                    GohuText {
                        width: parent.width
                        text: root.overview.recovery.detail
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.Wrap
                    }
                    GohuText {
                        width: parent.width
                        text: "REVIEW NEXT // " + root.overview.recovery.action
                        color: Colors.blue
                        font.pixelSize: 9
                        wrapMode: Text.Wrap
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "PATIENT // " + (root.overview.repository || "UNVERIFIED")
                    + "   BRANCH // " + (root.overview.branch || "UNKNOWN")
                font.pixelSize: 9
                color: Colors.blue
                elide: Text.ElideMiddle
            }

            GohuText {
                width: parent.width
                text: "CURRENT ASSIGNMENT"
                font.pixelSize: 12
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                text: root.overview.assignment
                    ? String(root.overview.assignment.title || "UNTITLED")
                        + " // " + String(root.overview.assignment.status || "UNKNOWN")
                        + " // " + String(root.overview.assignment.phase || "")
                    : "NO LINKED ASSIGNMENT // VIEW IS READ-ONLY"
                color: root.overview.assignment ? Colors.white : Colors.orange
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                visible: !!root.overview.assignment
                text: "GOAL // " + root.preview(
                    root.overview.assignment ? root.overview.assignment.goal : "", 800)
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                visible: !!root.overview.assignment
                text: "DONE WHEN // " + root.preview(
                    root.overview.assignment
                        ? root.overview.assignment.definitionOfDone : "", 650)
                font.pixelSize: 9
                color: Colors.blue
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: "CHECKLIST // " +
                    (root.overview.progress.total
                        ? root.overview.progress.done + " / " + root.overview.progress.total
                        + " CHECKBOXES RECORDED"
                        : "NOT MEASURABLE")
                font.pixelSize: 10
                color: Colors.cyan
            }
            Rectangle {
                width: parent.width
                height: 11
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 1
                    width: Math.max(0, (parent.width - 2)
                        * (root.overview.progress.percent || 0) / 100)
                    color: Colors.cyan
                }
            }
            GohuText {
                width: parent.width
                text: root.overview.progress.evidence
                font.pixelSize: 8
                color: Colors.blue
                wrapMode: Text.Wrap
            }
            Repeater {
                model: root.overview.progress.items.slice(0, 12)
                GohuText {
                    required property var modelData
                    width: contentColumn.width
                    text: (modelData.done ? "[x] " : "[ ] ") + modelData.label
                    color: modelData.done ? Colors.green : Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.Wrap
                }
            }
            GohuText {
                width: parent.width
                visible: root.overview.progress.items.length > 12
                text: "CHECKLIST PREVIEW // " +
                    (root.overview.progress.items.length - 12)
                    + " MORE IN ASSIGNMENT"
                font.pixelSize: 8
                color: Colors.blue
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                text: "LAST CHECKPOINT // " +
                    (root.overview.checkpoint
                        ? String(root.overview.checkpoint.kind || "PROGRESS")
                            + " // #" + root.overview.checkpoint.id
                        : "NONE RECORDED")
                font.pixelSize: 11
                color: Colors.orange
            }
            GohuText {
                width: parent.width
                text: root.overview.checkpoint
                    ? root.preview(root.overview.checkpoint.body, 1000)
                    : "There is no saved checkpoint for this Room."
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: "LAST HANDOFF // " +
                    (root.overview.handoff
                        ? String(root.overview.handoff.title || "HANDOFF")
                            + " // REPORT #" + root.overview.handoff.id
                        : "NONE RECORDED")
                font.pixelSize: 11
                color: Colors.orange
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: root.overview.handoff
                    ? root.preview(root.overview.handoff.body, 1200)
                    : "No HANDOFF report. Recovery context may be incomplete."
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: "RECENT ROOM REPORT // " +
                    (root.overview.report
                        ? String(root.overview.report.kind || "NOTE")
                            + " // #" + root.overview.report.id
                        : "NONE RECORDED")
                font.pixelSize: 10
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                visible: !!root.overview.report
                text: root.overview.report
                    ? root.preview(root.overview.report.body, 800) : ""
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.Wrap
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                text: "OPERATOR-APPROVED CHART // " + root.overview.decisions.length
                    + " ACTIVE VISIBLE"
                font.pixelSize: 11
                color: Colors.orange
            }
            Repeater {
                model: root.overview.decisions
                Column {
                    required property var modelData
                    width: contentColumn.width
                    spacing: 3
                    GohuText {
                        width: parent.width
                        text: String(modelData.scope || "")
                            + " // " + String(modelData.kind || "")
                            + " // " + String(modelData.title || "UNTITLED")
                        font.pixelSize: 9
                        color: Colors.cyan
                        wrapMode: Text.Wrap
                    }
                    GohuText {
                        width: parent.width
                        text: root.preview(modelData.body, 650)
                        font.pixelSize: 9
                        color: Colors.white
                        wrapMode: Text.Wrap
                    }
                }
            }
            GohuText {
                width: parent.width
                visible: root.overview.decisions.length === 0
                text: "NO ACTIVE OPERATOR-AUTHORED CHART ENTRIES IN THIS PREVIEW"
                font.pixelSize: 9
                color: Colors.blue
                wrapMode: Text.Wrap
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.magenta
            }
            GohuText {
                width: parent.width
                text: "NEXT RECORDED INPUT // " + root.overview.next.source
                font.pixelSize: 11
                color: Colors.orange
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: root.preview(root.overview.next.body, 1000)
                font.pixelSize: 9
                color: Colors.white
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: root.overview.verified ? root.overview.source
                    : "PX ROOM SNAPSHOT // NOT VERIFIED"
                font.pixelSize: 8
                color: Colors.blue
                wrapMode: Text.Wrap
            }
            GohuText {
                width: parent.width
                text: "PX READS ARE SEQUENTIAL, NOT A DATABASE-ATOMIC SNAPSHOT. REFRESH AFTER EXTERNAL CHANGES. No browser ChatGPT recovery, automatic Doctor replacement, provider heartbeat, or permission grant."
                font.pixelSize: 8
                color: Colors.blue
                wrapMode: Text.Wrap
            }
        }
    }

    NeonScrollBar {
        flickable: contentScroll
        handleStyle: "star"
        visible: root.active && scrollable
    }
}
