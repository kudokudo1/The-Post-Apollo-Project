import QtQuick
import "../../components"
import "TaskProjectsAck.js" as ProjectAck

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
    property string pendingProjectId: ""
    property int pendingTaskTotal: 0
    property bool confirmDeleteProject: false
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
    readonly property bool renameDirty:
        selectedProject !== null && renameInput.text.trim() !== selectedProject.name
    readonly property bool validRename:
        selectedProject !== null && renameDirty
        && renameInput.text.trim().length > 0
        && renameInput.text.trim().length <= 64
        && !/[\x00-\x1f\x7f]/.test(renameInput.text)
        && !projects.some(function(p) {
            return p.id !== selectedProjectId
                   && p.name.toLowerCase() === renameInput.text.trim().toLowerCase();
        })
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
    function chooseProject(projectId) {
        if (pendingWrite) {
            feedback = "SAVE PENDING";
            return;
        }
        if (renameDirty) {
            feedback = "SAVE OR RESET RENAME FIRST";
            return;
        }
        confirmDeleteProject = false;
        if (selectedProjectId !== projectId) {
            selectedProjectId = projectId;
            renameInput.text = selectedProject ? selectedProject.name : "";
        }
        feedback = "";
    }
    function renameSelectedProject() {
        if (!writable || !validRename || !selectedProject)
            return;
        pendingKind = "rename";
        pendingProjectId = selectedProjectId;
        pendingProjectName = renameInput.text.trim();
        pendingWrite = true;
        confirmDeleteProject = false;
        feedback = "SAVING";
        if (!todoStore.renameProject(pendingProjectId, pendingProjectName)) {
            pendingWrite = false;
            pendingKind = "";
            feedback = "RENAME REJECTED";
        }
    }
    function discardRename() {
        if (!writable || !selectedProject) return;
        renameInput.text = selectedProject.name;
        feedback = "RENAME RESET";
    }
    function deleteSelectedProject() {
        if (!writable || !selectedProject || !confirmDeleteProject) return;
        pendingKind = "delete";
        pendingProjectId = selectedProjectId;
        pendingTaskTotal = tasks.length;
        pendingWrite = true;
        feedback = "SAVING";
        if (!todoStore.deleteProject(pendingProjectId, true)) {
            pendingWrite = false;
            pendingKind = "";
            feedback = "DELETE REJECTED";
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

    // Reconcile only the actual incoming snapshot. Reading projects/tasks
    // through separate QML derived properties could miss a successful save
    // and leave pendingWrite stuck true after a project rename.
    function reconcilePending() {
        const snap = todoSnapshot;
        if (!snap) return;
        const state = String(snap.state || "loading");
        const rawProjects = Array.isArray(snap.projects) ? snap.projects : [];
        if (!pendingWrite) {
            // Don't clear the selection just because the store is loading.
            if ((state === "ready" || state === "empty")
                    && selectedProjectId
                    && !rawProjects.some(function(p) {
                        return p.id === selectedProjectId;
                    })) {
                selectedProjectId = "";
                feedback = "PROJECT UNAVAILABLE";
            }
            return;
        }
        const outcome = ProjectAck.status(
            snap, pendingKind, pendingProjectId, pendingProjectName,
            pendingTaskId, pendingTargetProjectId, pendingTaskTotal);
        if (outcome === "waiting")
            return;
        if (outcome === "failed") {
            pendingWrite = false;
            pendingKind = "";
            feedback = "SAVE FAILED // INPUT KEPT";
            return;
        }
        if (outcome !== "confirmed") {
            // Fail open for editing, fail closed for "SAVED": a completed
            // store lifecycle with a mismatched result must not disable
            // the editor forever or silently pretend to have committed.
            pendingWrite = false;
            pendingKind = "";
            feedback = "SAVE NOT VERIFIED // INPUT KEPT";
            return;
        }

        if (pendingKind === "create") {
            const found = rawProjects.find(function(p) {
                return p.name === pendingProjectName;
            });
            if (found) {
                selectedProjectId = found.id;
                renameInput.text = found.name;
                newProjectInput.text = "";
            }
        } else if (pendingKind === "rename") {
            const renamed = rawProjects.find(function(p) {
                return p.id === pendingProjectId;
            });
            if (renamed) renameInput.text = renamed.name;
        } else if (pendingKind === "delete") {
            selectedProjectId = "";
            renameInput.text = "";
            confirmDeleteProject = false;
        }
        const wasDelete = pendingKind === "delete";
        pendingWrite = false;
        pendingKind = "";
        feedback = wasDelete ? "PROJECT REMOVED // TASKS UNASSIGNED" : "SAVED";
    }

    onTodoSnapshotChanged: reconcilePending()
    // Extra signal protects against property-notification ordering within
    // QML. reconcilePending still inspects only todoSnapshot itself.
    onStoreStateChanged: reconcilePending()
    onVisibleChanged: {
        if (!visible) {
            newProjectInput.focus = false;
            renameInput.focus = false;
        }
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
            onLeftClicked: projectsPane.chooseProject(modelData.id)
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

    // Rename the selected catalog entry, without changing its stable ID.
    Row {
        id: projectRenameRow
        anchors.top: selectedLabel.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        height: 27
        spacing: 4

        Rectangle {
            width: Math.max(45, parent.width - saveProjectButton.width
                            - resetProjectButton.width - 2 * parent.spacing)
            height: parent.height
            color: Colors.black
            border.width: 1
            border.color: renameInput.activeFocus ? Colors.magenta : Colors.cyan
            TextInput {
                id: renameInput
                anchors.fill: parent
                anchors.leftMargin: 4
                anchors.rightMargin: 4
                verticalAlignment: TextInput.AlignVCenter
                color: Colors.white
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 10
                maximumLength: 64
                selectByMouse: true
                clip: true
                enabled: projectsPane.writable && projectsPane.selectedProject !== null
                onAccepted: projectsPane.renameSelectedProject()
            }
        }
        ActionButton {
            id: saveProjectButton
            width: 51
            height: parent.height
            label: "RENAME"
            labelPixelSize: 9
            available: projectsPane.writable && projectsPane.validRename
            onLeftClicked: projectsPane.renameSelectedProject()
        }
        ActionButton {
            id: resetProjectButton
            width: 44
            height: parent.height
            label: "RESET"
            labelPixelSize: 9
            available: projectsPane.writable && projectsPane.renameDirty
            onLeftClicked: projectsPane.discardRename()
        }
    }

    // Explicit two-step confirmation. Removing a project does NOT remove tasks.
    Row {
        id: projectDeleteRow
        anchors.top: projectRenameRow.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        height: 26
        spacing: 5

        ActionButton {
            id: deleteProjectButton
            width: projectsPane.confirmDeleteProject ? 63 : 94
            height: parent.height
            destructive: true
            accentColor: Colors.red
            label: projectsPane.confirmDeleteProject ? "YES" : "DEL PROJECT"
            labelPixelSize: 9
            available: projectsPane.writable
                       && projectsPane.selectedProject !== null
                       && !projectsPane.renameDirty
            onLeftClicked: {
                if (projectsPane.confirmDeleteProject)
                    projectsPane.deleteSelectedProject();
                else {
                    projectsPane.confirmDeleteProject = true;
                    projectsPane.feedback = "DELETE PROJECT? TASKS KEPT";
                }
            }
        }
        ActionButton {
            id: cancelDeleteButton
            width: 47
            height: parent.height
            label: "NO"
            labelPixelSize: 9
            visible: projectsPane.confirmDeleteProject
            available: projectsPane.writable
            onLeftClicked: {
                projectsPane.confirmDeleteProject = false;
                projectsPane.feedback = "DELETE CANCELED";
            }
        }
        GohuText {
            width: Math.max(20, parent.width - deleteProjectButton.width
                            - (cancelDeleteButton.visible ? cancelDeleteButton.width : 0)
                            - 2 * parent.spacing)
            height: parent.height
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 9
            color: projectsPane.confirmDeleteProject ? Colors.orange : Colors.cyan
            text: projectsPane.confirmDeleteProject
                  ? "TASKS BECOME UNASSIGNED" : "PROJECT ONLY"
            elide: Text.ElideRight
        }
    }

    ListView {
        id: taskList
        anchors.top: projectDeleteRow.bottom
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
