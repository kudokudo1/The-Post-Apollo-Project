import QtQuick
import "../../components"
import "TaskGitHubMappingPolicy.js" as MappingPolicy

// M8 SYNC: no network, no mutation, no account assumptions.
// A future Git-owned adapter can supply verified IDs / field metadata after
// an operator-approved mapping and conflict policy.
Item {
    id: syncPreview

    property var todoSnapshot: null
    readonly property var plan: MappingPolicy.preview(todoSnapshot)

    Column {
        id: statusHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 7

        GohuText {
            width: parent.width
            text: "GITHUB // MAPPING PREVIEW"
            color: Colors.magenta
            font.pixelSize: 12
            font.bold: true
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            text: "LOCAL ONLY // NO REMOTE ACTIONS"
            color: Colors.orange
            font.pixelSize: 10
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Colors.white
            font.pixelSize: 10
            text: syncPreview.plan.available
                  ? syncPreview.plan.localProjects + " LOCAL PROJECTS // "
                    + syncPreview.plan.localTasks + " TASKS"
                  : "CHECKLIST // "
                    + String(syncPreview.plan.state).toUpperCase()
        }

        GohuText {
            width: parent.width
            color: Colors.cyan
            font.pixelSize: 10
            text: "REMOTE LINKS // 0 VERIFIED"
            elide: Text.ElideRight
        }

        GohuText {
            width: parent.width
            color: Colors.cyan
            font.pixelSize: 10
            text: "WRITE READY // " + syncPreview.plan.writeReady
            elide: Text.ElideRight
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }

        GohuText {
            width: parent.width
            text: "FIELD REQUIREMENTS"
            color: Colors.magenta
            font.pixelSize: 11
            font.bold: true
        }

        Repeater {
            model: syncPreview.plan.fieldRows
            delegate: Column {
                required property var modelData
                width: statusHeader.width
                spacing: 2
                GohuText {
                    width: parent.width
                    font.pixelSize: 10
                    color: Colors.white
                    text: modelData.local.toUpperCase() + " // "
                          + modelData.remoteCandidate
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    font.pixelSize: 9
                    color: Colors.orange
                    text: modelData.readiness.replace(/_/g, " ")
                    elide: Text.ElideRight
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }

        GohuText {
            width: parent.width
            wrapMode: Text.WordWrap
            color: Colors.cyan
            font.pixelSize: 9
            text: "Title matches are NOT identity matches. "
                  + "Remote Project, Item, Field and Option IDs "
                  + "must be verified before linking."
        }

        GohuText {
            width: parent.width
            text: "LOCAL INVENTORY // NO UPLOAD"
            color: Colors.magenta
            font.pixelSize: 11
            font.bold: true
        }

        GohuText {
            width: parent.width
            color: Colors.white
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            text: syncPreview.plan.tasksWithDate + " DATED // "
                  + syncPreview.plan.tasksWithPriority + " PRIORITIZED // "
                  + syncPreview.plan.tasksWithDescription + " DESCRIBED // "
                  + syncPreview.plan.tasksDone + " DONE"
        }
    }

    ListView {
        id: localInventory
        anchors.top: statusHeader.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        spacing: 5
        boundsBehavior: Flickable.StopAtBounds
        model: syncPreview.plan.projectRows.concat(syncPreview.plan.taskRows)

        delegate: Item {
            required property var modelData
            width: localInventory.width
            height: 42

            readonly property bool isProject:
                String(modelData.linkage).indexOf("REMOTE_PROJECT") >= 0

            GohuText {
                anchors.top: parent.top
                width: parent.width
                text: (parent.isProject ? "PROJECT // " : "TASK // ")
                      + modelData.title
                font.pixelSize: 10
                color: parent.isProject ? Colors.magenta : Colors.white
                elide: Text.ElideRight
            }
            GohuText {
                anchors.bottom: parent.bottom
                width: parent.width
                text: "NOT LINKED // " + (parent.isProject
                      ? "REMOTE PROJECT ID" : "REMOTE ITEM ID")
                font.pixelSize: 9
                color: Colors.orange
                elide: Text.ElideRight
            }
        }
    }

    GohuText {
        anchors.centerIn: localInventory
        visible: syncPreview.plan.available
                 && syncPreview.plan.projectRows.length === 0
                 && syncPreview.plan.taskRows.length === 0
        width: parent.width
        text: "NO LOCAL TASKS OR PROJECTS"
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        font.pixelSize: 10
        color: Colors.cyan
    }
}
