import QtQuick
import qs.components

Rectangle {
    id: root

    required property var sessionService
    property var keyboardHost: null
    property bool abortArmed: false

    signal openChangesRequested(string path)

    color: Colors.dark
    border.width: 1
    border.color:
        sessionService.state === "CONFLICT"
        ? Colors.red
        : sessionService.state === "PAUSED_EDIT"
        ? Colors.orange
        : Colors.magenta

    function firstConflictPath() {
        const rows =
            sessionService
            && Array.isArray(sessionService.conflictFiles)
            ? sessionService.conflictFiles
            : [];

        return rows.length > 0
            ? String(rows[0] || "")
            : "";
    }

    component SessionButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property color accent: Colors.cyan

        signal triggered()

        height: 34
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
        anchors.margins: 10
        spacing: 8

        Row {
            width: parent.width
            height: 42
            spacing: 8

            Column {
                width: parent.width - 160
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3

                GohuText {
                    text:
                        sessionService.foreignSession
                        ? "LIVE REBASE // EXTERNAL SESSION"
                        : "LIVE REBASE // PERSISTENT SESSION"
                    font.pixelSize: 13
                    color: Colors.magenta
                }

                GohuText {
                    width: parent.width
                    text:
                        String(sessionService.state || "NONE")
                        + (
                            sessionService.sessionId
                            ? " // " + String(sessionService.sessionId)
                            : ""
                          )
                    font.pixelSize: 9
                    color:
                        sessionService.state === "CONFLICT"
                        ? Colors.red
                        : sessionService.state === "PAUSED_EDIT"
                        ? Colors.orange
                        : Colors.cyan
                    elide: Text.ElideRight
                }
            }

            SessionButton {
                width: 152
                label:
                    sessionService.refreshing
                    ? "READING GIT STATE"
                    : "REFRESH SESSION"
                accent: Colors.cyan
                enabledAction:
                    !sessionService.busy
                    && !sessionService.refreshing
                onTriggered: sessionService.refresh()
            }
        }

        SectionFrame {
            width: parent.width
            height: 84
            fillColor: Colors.black
            borderWidth: 1
            borderColor: Colors.cyan
            inset: 7

            Grid {
                anchors.fill: parent
                columns: 2
                columnSpacing: 12
                rowSpacing: 4

                GohuText {
                    width: 112
                    text: "BRANCH"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    width: parent.width - 124
                    text:
                        sessionService.originalBranch
                        || "UNKNOWN"
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                }

                GohuText {
                    width: 112
                    text: "HEAD / BASE"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    width: parent.width - 124
                    text:
                        String(sessionService.currentHead || "").slice(0, 10)
                        + " / "
                        + String(sessionService.baseSha || "").slice(0, 10)
                    font.pixelSize: 9
                    color: Colors.white
                    elide: Text.ElideRight
                }

                GohuText {
                    width: 112
                    text: "PROGRESS"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    width: parent.width - 124
                    text:
                        String(sessionService.progressCurrent || 0)
                        + " / "
                        + String(sessionService.progressTotal || 0)
                        + " // TODO "
                        + String(sessionService.todoRemaining || 0)
                    font.pixelSize: 9
                    color: Colors.white
                }

                GohuText {
                    width: 112
                    text: "STOPPED"
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                GohuText {
                    width: parent.width - 124
                    text:
                        sessionService.stoppedSha
                        ? String(sessionService.stoppedSha).slice(0, 12)
                        : "—"
                    font.pixelSize: 9
                    color:
                        sessionService.state === "PAUSED_EDIT"
                        ? Colors.orange
                        : Colors.white
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 50
            color: Colors.black
            border.width: 1
            border.color:
                sessionService.state === "CONFLICT"
                ? Colors.red
                : Colors.orange

            GohuText {
                anchors.fill: parent
                anchors.margins: 7
                verticalAlignment: Text.AlignVCenter
                text:
                    sessionService.state === "CONFLICT"
                    ? (
                        "CONFLICT // RESOLVE IN CHANGES, STAGE THE RESULT, "
                        + "THEN RETURN HERE AND CONTINUE"
                      )
                    : sessionService.state === "PAUSED_EDIT"
                    ? (
                        "EDIT PAUSE // MODIFY OR AMEND THE STOPPED COMMIT "
                        + "IN CHANGES, THEN CONTINUE"
                      )
                    : sessionService.foreignSession
                    ? (
                        "EXTERNAL REBASE // CONTROLS ARE AVAILABLE, "
                        + "BUT POST-APOLLO HAS NO ORIGINAL JOURNAL SNAPSHOT"
                      )
                    : (
                        "GIT REBASE STATE IS DURABLE // THIS SESSION "
                        + "CAN SURVIVE A QUICKSHELL RELOAD"
                      )
                font.pixelSize: 9
                color:
                    sessionService.state === "CONFLICT"
                    ? Colors.red
                    : Colors.orange
                wrapMode: Text.Wrap
            }
        }

        Row {
            width: parent.width
            height: parent.height - 276
            spacing: 8

            Rectangle {
                width: Math.floor(parent.width * 0.56)
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color:
                    sessionService.conflictFiles.length > 0
                    ? Colors.red
                    : Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 7
                    spacing: 5

                    GohuText {
                        width: parent.width
                        text:
                            "CONFLICT FILES // "
                            + String(sessionService.conflictFiles.length)
                        font.pixelSize: 10
                        color:
                            sessionService.conflictFiles.length > 0
                            ? Colors.red
                            : Colors.cyan
                    }

                    Flickable {
                        id: conflictScroll

                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        contentWidth: width
                        contentHeight: conflictColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: conflictColumn

                            width: parent.width
                            spacing: 4

                            GohuText {
                                visible:
                                    sessionService.conflictFiles.length === 0
                                width: parent.width
                                topPadding: 24
                                horizontalAlignment: Text.AlignHCenter
                                text:
                                    sessionService.state === "PAUSED_EDIT"
                                    ? "NO CONFLICTS // EDIT PAUSE"
                                    : "NO UNRESOLVED CONFLICTS"
                                font.pixelSize: 10
                                color: Colors.cyan
                            }

                            Repeater {
                                model: sessionService.conflictFiles

                                Rectangle {
                                    id: conflictRow

                                    required property var modelData

                                    width: conflictColumn.width
                                    height: 36
                                    color:
                                        conflictMouse.containsMouse
                                        ? Colors.dark
                                        : "transparent"
                                    border.width: 1
                                    border.color: Colors.red

                                    GohuText {
                                        anchors {
                                            fill: parent
                                            leftMargin: 7
                                            rightMargin: 7
                                        }
                                        verticalAlignment: Text.AlignVCenter
                                        text: String(conflictRow.modelData || "")
                                        font.pixelSize: 9
                                        color: Colors.white
                                        elide: Text.ElideMiddle
                                    }

                                    MouseArea {
                                        id: conflictMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked:
                                            root.openChangesRequested(
                                                String(
                                                    conflictRow.modelData || ""
                                                )
                                            )
                                    }
                                }
                            }
                        }

                        NeonScrollBar {
                            flickable: conflictScroll
                        }
                    }
                }
            }

            SectionFrame {
                width: parent.width - Math.floor(parent.width * 0.56) - 8
                height: parent.height
                fillColor: Colors.black
                borderWidth: 1
                borderColor: Colors.magenta
                inset: 8

                Column {
                    anchors.fill: parent
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text: "SESSION CONTROL"
                        font.pixelSize: 10
                        color: Colors.magenta
                    }

                    SessionButton {
                        width: parent.width
                        label:
                            sessionService.state === "CONFLICT"
                            ? "OPEN CONFLICTS IN CHANGES"
                            : "OPEN CHANGES / AMEND"
                        accent:
                            sessionService.state === "CONFLICT"
                            ? Colors.red
                            : Colors.orange
                        enabledAction:
                            sessionService.active
                            && !sessionService.busy
                        onTriggered:
                            root.openChangesRequested(
                                root.firstConflictPath()
                            )
                    }

                    Row {
                        width: parent.width
                        height: 34
                        spacing: 6

                        SessionButton {
                            width: (parent.width - 6) / 2
                            label:
                                sessionService.busy
                                && sessionService.state === "CONTINUING"
                                ? "CONTINUING"
                                : "CONTINUE"
                            accent: Colors.green
                            enabledAction:
                                sessionService.canContinue
                                && !sessionService.busy
                            onTriggered: {
                                root.abortArmed = false;
                                sessionService.continueSession();
                            }
                        }

                        SessionButton {
                            width: (parent.width - 6) / 2
                            label:
                                sessionService.busy
                                && sessionService.state === "SKIPPING"
                                ? "SKIPPING"
                                : "SKIP STEP"
                            accent: Colors.orange
                            enabledAction:
                                sessionService.canSkip
                                && !sessionService.busy
                            onTriggered: {
                                root.abortArmed = false;
                                sessionService.skipSession();
                            }
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(0, parent.height - 190)
                    }

                    SessionButton {
                        width: parent.width
                        height: 38
                        label:
                            root.abortArmed
                            ? "CONFIRM ABORT REBASE"
                            : "ARM ABORT"
                        accent: Colors.red
                        selectedAction: root.abortArmed
                        enabledAction:
                            sessionService.canAbort
                            && !sessionService.busy
                        onTriggered: {
                            if (!root.abortArmed) {
                                root.abortArmed = true;
                                return;
                            }

                            root.abortArmed = false;
                            sessionService.abortSession(true);
                        }
                    }
                }
            }
        }

        SectionFrame {
            width: parent.width
            height: 42
            fillColor: Colors.black
            borderWidth: 1
            borderColor:
                sessionService.lastError
                ? Colors.red
                : Colors.cyan
            inset: 7

            GohuText {
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                text:
                    sessionService.lastError
                    ? "SESSION // " + sessionService.lastError
                    : (
                        "CURRENT GIT STATE // "
                        + String(sessionService.state || "NONE")
                      )
                font.pixelSize: 9
                color:
                    sessionService.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    Connections {
        target: sessionService
        ignoreUnknownSignals: true

        function onSessionChanged() {
            if (!sessionService.active)
                root.abortArmed = false;
        }
    }
}
