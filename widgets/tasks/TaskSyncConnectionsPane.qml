import QtQuick
import "../../components"
import "TaskGitHubMappingPolicy.js" as MappingPolicy

// M9a: Connections/Overview and mode navigation.
// GitW retains the ONLY GitHubProjectsService. This pane receives no remote
// credentials, service reference, project identities, or mutation capability.
Item {
    id: syncConnections

    property var todoSnapshot: null
    property string selectedSubmode: "overview"
    signal openGithubProjectsRequested()

    readonly property var plan: MappingPolicy.preview(todoSnapshot)
    readonly property var submodes: [
        {id:"overview", label:"OVERVIEW"},
        {id:"mappings", label:"MAP"},
        {id:"review", label:"REVIEW"},
        {id:"history", label:"HISTORY"}
    ]

    Column {
        id: connectionsHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 5

        GohuText {
            width: parent.width
            text: "SYNC // CONNECTIONS"
            color: Colors.magenta
            font.pixelSize: 12
            font.bold: true
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: "LOCAL PREVIEW // REMOTE VIA GIT"
            color: Colors.cyan
            font.pixelSize: 9
            elide: Text.ElideRight
        }

        Row {
            id: syncTabRail
            width: parent.width
            height: 31
            spacing: 3
            Repeater {
                model: syncConnections.submodes
                ModeButton {
                    required property var modelData
                    width: Math.floor((syncTabRail.width - syncTabRail.spacing * 3) / 4)
                    height: syncTabRail.height
                    textOnly: true
                    labelText: modelData.label
                    labelFontSize: 9
                    bordered: false
                    selected: syncConnections.selectedSubmode === modelData.id
                    onTriggered: syncConnections.selectedSubmode = modelData.id
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
    }

    Item {
        id: submodeContent
        anchors.top: connectionsHeader.bottom
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        Column {
            id: connectionOverview
            visible: syncConnections.selectedSubmode === "overview"
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 12

            GohuText {
                width: parent.width
                text: "GITHUB PROJECTS // READ PATH"
                font.pixelSize: 11
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                text: "TASKS LINK // NOT ATTACHED"
                font.pixelSize: 10
                color: Colors.orange
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                text: "SERVICE OWNER // GIT MENU"
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                text: "REMOTE PROJECTS // NOT READ HERE"
                font.pixelSize: 10
                color: Colors.white
                elide: Text.ElideRight
            }

            ActionButton {
                width: parent.width
                height: 32
                label: "OPEN GITHUB PROJECTS"
                labelPixelSize: 10
                accentColor: Colors.cyan
                onLeftClicked: syncConnections.openGithubProjectsRequested()
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }

            GohuText {
                width: parent.width
                text: "LOCAL INVENTORY"
                font.pixelSize: 11
                color: Colors.magenta
                font.bold: true
            }

            GohuText {
                width: parent.width
                text: syncConnections.plan.available
                      ? syncConnections.plan.localProjects + " PROJECTS // "
                        + syncConnections.plan.localTasks + " TASKS"
                      : "LOCAL STORAGE // "
                        + String(syncConnections.plan.state).toUpperCase()
                color: Colors.white
                font.pixelSize: 10
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                text: "REMOTE LINKS // 0 VERIFIED"
                color: Colors.cyan
                font.pixelSize: 10
            }

            GohuText {
                width: parent.width
                text: "WRITE READY // 0"
                color: Colors.orange
                font.pixelSize: 10
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }

            GohuText {
                width: parent.width
                text: "NEXT // VERIFY PROJECT & ITEM IDS"
                font.pixelSize: 10
                color: Colors.magenta
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: "Open the existing GitHub menu to inspect remote data. "
                      + "TASKS has no remote link or sync authority yet."
                font.pixelSize: 10
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: "NO PULL // NO PUSH // NO AUTO-SYNC"
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
        }

        // Preserve the M8 field/identity preview intact and accessible.
        TaskSyncPreviewPane {
            anchors.fill: parent
            visible: syncConnections.selectedSubmode === "mappings"
            todoSnapshot: syncConnections.todoSnapshot
        }

        Column {
            visible: syncConnections.selectedSubmode === "review"
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 12

            GohuText {
                width: parent.width
                text: "REVIEW // NO COMPARISON"
                font.pixelSize: 12
                color: Colors.magenta
                font.bold: true
            }

            GohuText {
                width: parent.width
                text: "No local-to-remote identities are verified. "
                      + "There are no approved changes to review."
                font.pixelSize: 10
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }

            GohuText {
                width: parent.width
                text: "PULL / PUSH // DISABLED"
                font.pixelSize: 10
                color: Colors.orange
            }
        }

        Column {
            visible: syncConnections.selectedSubmode === "history"
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            spacing: 12

            GohuText {
                width: parent.width
                text: "HISTORY // NOT CONNECTED"
                font.pixelSize: 12
                color: Colors.magenta
                font.bold: true
            }

            GohuText {
                width: parent.width
                text: "TASKS has not performed or recorded synchronization "
                      + "operations. GitHub operations in GitW are separate."
                font.pixelSize: 10
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }
        }
    }
}
