import QtQuick
import "../../components"

// M6 local Projects. One injected ApolloHubTodoStore remains the only writer.
// Project IDs are local, never implied to be GitHub Project identifiers.
Item {
    id: projectsPane

    property var todoStore: null
    property var todoSnapshot: null
    property string selectedProjectId: ""
    property bool pendingWrite: false
    property string pendingKind: ""
    property string pendingProjectName: ""
    property string pendingTaskId: ""
    property var pendingTargetProjectId: null
    property string feedback: ""
    signal openTaskRequested(string taskId)

    readonly property string storeState:
        todoSnapshot && todoSnapshot.state ? String(todoSnapshot.state) : "loading"
    readonly property var projects:
        todoSnapshot && Array.isArray(todoSnapshot.projects) ? todoSnapshot.projects : []
    readonly property var tasks:
        todoSnapshot && Array.isArray(todoSnapshot.items) ? todoSnapshot.items : []
    readonly property bool writable:
        todoStore !== null && todoSnapshot && todoSnapshot.writable === true
        && (storeState === "ready" || storeState === "empty")
        && !pendingWrite
    readonly property var selectedProject: {
        for (let i = 0; i < projects.length; ++i)
            if (projects[i].id === selectedProjectId)
                return projects[i];
        return null;
    }
    readonly property var orderedTasks: {
        let assigned = [];
        let other = [];
        for (let i = 0; i < tasks.length; ++i) {
            if (tasks[i].projectId === selectedProjectId) assigned.push(tasks[i]);
            else other.push(tasks[i]);
        }
        return assigned.concat(other);
    }
    readonly property bool validProjectName:
        newProjectInput.text.trim().length > 0
        && newProjectInput.text.trim().length <= 64
        && !/[\x00-\x1f\x7f]/.test(newProjectInput.text)
        && !projects.some(function(p) {
            return p.name.toLowerCase() === newProjectInput.text.trim().toLowerCase();
        })

    function createProject() {
        if (!writable || !validProjectName) return;
        pendingProjectName = newProjectInput.text.trim();
        pendingKind = "create";
        pendingWrite = true;
        feedback = "SAVING";
        if (!todoStore.createProject(pendingProjectName)) {
            pendingWrite = false;
            pendingKind = "";
            feedback = "CREATE REJECTED";
        }
    }
    function setProject(task) {
        if (!writable || !selectedProject || !task) return;
        pendingTaskId = task.id;
        pendingTargetProjectId = task.projectId === selectedProjectId
                                 ? null : selectedProjectId;
        pendingKind = "assign";
        pendingWrite = true;
        feedback = "SAVING";
        if (!todoStore.assignTaskProject(task.id, pendingTargetProjectId)) {
            pendingWrite = false;
            pendingKind = "";
            feedback = "ASSIGN REJECTED";
        }
    }

    onTodoSnapshotChanged: {
        if (pendingWrite) {
            if (storeState === "error" || storeState === "unsupported") {
                pendingWrite = false;
                pendingKind = "";
                feedback = "SAVE FAILED // INPUT KEPT";
            } else if (storeState === "ready" || storeState === "empty") {
                if (pendingKind === "create") {
                    const found = projects.find(function(p) {
                        return p.name === pendingProjectName;
                    });
                    if (found) {
                        selectedProjectId = found.id;
                        newProjectInput.text = "";
                        pendingWrite = false;
                        pendingKind = "";
                        feedback = "SAVED";
                    }
                } else if (pendingKind === "assign") {
                    const task = tasks.find(function(t) {
                        return t.id === pendingTaskId;
                    });
                    if (task && task.projectId === pendingTargetProjectId) {
                        pendingWrite = false;
                        pendingKind = "";
                        feedback = "SAVED";
                    }
                }
            }
        }
        if (selectedProjectId && !selectedProject && !pendingWrite) {
            selectedProjectId = "";
            feedback = "PROJECT UNAVAILABLE";
        }
    }
    onVisibleChanged: {
        if (!visible) newProjectInput.focus = false;
    }

    Column {
        id: createArea
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 5

        GohuText {
            width: parent.width
            text: "LOCAL PROJECTS // " + projectsPane.projects.length + " / 30"
            color: Colors.magenta
            font.pixelSize: 12
            font.bold: true
            elide: Text.ElideRight
        }

        Row {
            width: parent.width
            height: 26
            spacing: 5

            Rectangle {
                width: parent.width - createButton.width - parent.spacing
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: newProjectInput.activeFocus ? Colors.magenta : Colors.cyan

                TextInput {
                    id: newProjectInput
                    anchors.fill: parent
                    anchors.leftMargin: 5
                    anchors.rightMargin: 5
                    verticalAlignment: TextInput.AlignVCenter
                    color: Colors.white
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 11
                    maximumLength: 64
                    selectByMouse: true
                    clip: true
                    enabled: projectsPane.writable
                    onAccepted: projectsPane.createProject()
                }
                GohuText {
                    anchors.centerIn: parent
                    visible: !newProjectInput.activeFocus && newProjectInput.text.length === 0
                    text: "NEW PROJECT NAME"
                    font.pixelSize: 10
                    color: Colors.cyan
                    opacity: 0.6
                }
            }
            ActionButton {
                id: createButton
                width: 48
                height: parent.height
                label: "ADD"
                labelPixelSize: 10
                available: projectsPane.writable && projectsPane.validProjectName
                onLeftClicked: projectsPane.createProject()
            }
        }
        GohuText {
            width: parent.width
            height: 18
            font.pixelSize: 9
            color: projectsPane.storeState === "error"
                   || projectsPane.storeState === "unsupported"
                   ? Colors.orange : Colors.cyan
            text: projectsPane.feedback
                  || (projectsPane.storeState === "saving" ? "SAVING // NOT CONFIRMED"
                      : projectsPane.storeState === "loading" ? "READING CHECKLIST..."
                      : projectsPane.storeState === "error"
                        || projectsPane.storeState === "unsupported"
                      ? "STORAGE LOCKED // RELOAD IN TASKS" : "CREATE OR SELECT A PROJECT")
            elide: Text.ElideRight
        }
    }

    ListView {
        id: projectList
        anchors.top: createArea.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        height: 156
        model: projectsPane.projects
        clip: true
        spacing: 3
        boundsBehavior: Flickable.StopAtBounds

        delegate: ActionButton {
            required property var modelData
            width: projectList.width
            height: 29
            label: modelData.name + " // " + modelData.remaining
                   + " OPEN / " + modelData.total
            labelPixelSize: 10
            selected: projectsPane.selectedProjectId === modelData.id
            onLeftClicked: projectsPane.selectedProjectId = modelData.id
        }
    }

    GohuText {
        id: selectedLabel
        anchors.top: projectList.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        font.pixelSize: 10
        color: Colors.magenta
        elide: Text.ElideRight
        text: projectsPane.selectedProject
              ? projectsPane.selectedProject.name + " // TASK ASSIGNMENTS"
              : "SELECT A LOCAL PROJECT ABOVE"
    }

    ListView {
        id: taskList
        anchors.top: selectedLabel.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        spacing: 4
        boundsBehavior: Flickable.StopAtBounds
        model: projectsPane.orderedTasks

        delegate: Item {
            id: row
            required property var modelData
            width: taskList.width
            height: 48

            GohuText {
                anchors.left: parent.left
                anchors.right: assignButton.left
                anchors.rightMargin: 5
                anchors.top: parent.top
                font.pixelSize: 11
                color: row.modelData.done ? Colors.cyan : Colors.white
                opacity: row.modelData.done ? 0.65 : 1
                text: row.modelData.title
                elide: Text.ElideRight
            }
            GohuText {
                anchors.left: parent.left
                anchors.right: assignButton.left
                anchors.rightMargin: 5
                anchors.bottom: parent.bottom
                font.pixelSize: 9
                color: row.modelData.projectId === projectsPane.selectedProjectId
                       ? Colors.magenta : Colors.cyan
                text: row.modelData.projectId === null ? "UNASSIGNED"
                      : row.modelData.projectId === projectsPane.selectedProjectId
                      ? "THIS PROJECT" : "OTHER PROJECT"
                elide: Text.ElideRight
            }
            ActionButton {
                id: assignButton
                anchors.right: openButton.left
                anchors.rightMargin: 3
                anchors.verticalCenter: parent.verticalCenter
                width: 50
                height: 25
                labelPixelSize: 9
                label: row.modelData.projectId === projectsPane.selectedProjectId
                       ? "CLEAR" : "ASSIGN"
                available: projectsPane.writable && projectsPane.selectedProject !== null
                onLeftClicked: projectsPane.setProject(row.modelData)
            }
            ActionButton {
                id: openButton
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 40
                height: 25
                label: "OPEN"
                labelPixelSize: 9
                onLeftClicked: projectsPane.openTaskRequested(row.modelData.id)
            }
        }
    }

    GohuText {
        anchors.centerIn: taskList
        visible: projectsPane.tasks.length === 0
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        font.pixelSize: 11
        color: Colors.cyan
        text: "NO LOCAL TASKS"
    }
}
