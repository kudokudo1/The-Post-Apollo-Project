import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import qs.components

Item {
    id: root

    required property var gitService
    required property var branchWorkspaceService
    required property var branchStackStore
    required property var stackPlanner
    required property var stackExecutor
    property var keyboardHost: null

    property string selectedBranch: ""
    property string selectedSha: ""
    property string pendingFocusBranch: ""
    property string pendingFocusSha: ""
    property string editMode: "NAME"
    property string newBranchMode: "ABOVE"
    property string managementMode: ""
    property string managementMessage: ""
    property string managementArm: ""
    property string pendingRenameOld: ""
    property string pendingRenameNew: ""
    property string pendingDeleteBranch: ""
    property string pendingCreateName: ""
    property string pendingCreateAnchor: ""
    property string pendingCreateMode: ""
    property string workspaceMode: "ATTACH"
    property string pendingWorkspaceBranch: ""
    property string pendingWorkspaceAnchor: ""
    property string pendingWorkspacePath: ""

    readonly property var selectedBranchData:
        branchWorkspaceService && selectedBranch
        ? branchWorkspaceService.branchForName(selectedBranch)
        : null

    readonly property var selectedWorkspace:
        branchWorkspaceService && selectedBranch
        ? branchWorkspaceService.worktreeForBranch(selectedBranch)
        : null

    readonly property bool selectedIsCurrent:
        selectedBranch.length > 0
        && branchWorkspaceService
        && selectedBranch === branchWorkspaceService.currentBranch

    readonly property bool selectedIsOccupied:
        selectedWorkspace !== null

    readonly property bool selectedIsMerged:
        Boolean(selectedBranchData && selectedBranchData.merged)

    readonly property bool selectedIsTrunk:
        selectedBranch.length > 0
        && branchStackStore
        && selectedBranch === String(branchStackStore.trunkBranch || "main")

    readonly property string selectedStackParent:
        branchStackStore && selectedBranch
        ? branchStackStore.parentOf(selectedBranch)
        : ""

    readonly property var selectedStackChildren:
        branchStackStore && selectedBranch
        ? branchStackStore.childrenOf(selectedBranch)
        : []

    readonly property string selectedStackRoot:
        branchStackStore && selectedBranch
        ? branchStackStore.stackRoot(selectedBranch)
        : ""

    readonly property var selectedStackDescendants:
        branchStackStore && selectedBranch
        ? branchStackStore.descendantsOf(selectedBranch)
        : []

    signal createBranchRequested(string startPoint)
    signal renameBranchRequested(string branch)
    signal deleteBranchRequested(string branch)
    signal upstreamRequested(string branch)
    signal workspaceRequested(string branch)
    signal stackAboveRequested(string branch)
    signal stackBelowRequested(string branch)
    signal stackParentRequested(string branch)
    signal restackRequested(string branch)
    signal submitStackRequested(string branch)
    signal compareRequested(string branch)
    signal historyRequested(string branch)

    onSelectedBranchChanged: {
        root.managementMode = "";
        root.managementMessage = "";
        root.managementArm = "";

        if (stackPlanner)
            stackPlanner.clear();

        if (stackExecutor)
            stackExecutor.disarm("BRANCH SELECTION CHANGED");
    }

    Connections {
        target: root.branchStackStore
        enabled: root.branchStackStore !== null
        ignoreUnknownSignals: true

        function onRelationsChanged() {
            if (root.stackPlanner)
                root.stackPlanner.clear();

            if (root.stackExecutor)
                root.stackExecutor.disarm("STACK RELATIONSHIPS CHANGED");
        }
    }

    Connections {
        target: root.branchWorkspaceService
        enabled: root.branchWorkspaceService !== null
        ignoreUnknownSignals: true

        function onRefreshed() {
            if (root.stackPlanner)
                root.stackPlanner.clear();

            if (root.stackExecutor)
                root.stackExecutor.disarm("BRANCH STATE CHANGED");

            root.applyFocusContext();

            if (root.managementMode === "edit"
                    && root.editMode === "UP"
                    && root.selectedBranchData)
                upstreamEditor.text =
                    String(root.selectedBranchData.upstream || "");
        }

        function onActionFinished(action, success, detail) {
            const kind = String(action || "");
            const message = String(detail || "");

            if (kind !== "RENAME"
                    && kind !== "SET-UPSTREAM"
                    && kind !== "CLEAR-UPSTREAM"
                    && kind !== "DELETE"
                    && kind !== "CREATE"
                    && kind !== "ADD-WORKTREE"
                    && kind !== "NEW-WORKTREE"
                    && kind !== "REMOVE-WORKTREE")
                return;

            root.managementMessage =
                (success ? "OK // " : "REFUSED // ")
                + message;

            if (!success) {
                if (kind === "CREATE") {
                    root.pendingCreateName = "";
                    root.pendingCreateAnchor = "";
                    root.pendingCreateMode = "";
                    root.pendingFocusBranch = "";
                    root.pendingFocusSha = "";
                }

                if (kind === "ADD-WORKTREE"
                        || kind === "NEW-WORKTREE"
                        || kind === "REMOVE-WORKTREE") {
                    root.pendingWorkspaceBranch = "";
                    root.pendingWorkspaceAnchor = "";
                    root.pendingWorkspacePath = "";
                    root.pendingFocusBranch = "";
                    root.pendingFocusSha = "";
                }

                root.managementArm = "";
                return;
            }

            if (kind === "RENAME") {
                if (root.branchStackStore
                        && root.pendingRenameOld
                        && root.pendingRenameNew)
                    root.branchStackStore.renameBranch(
                        root.pendingRenameOld,
                        root.pendingRenameNew
                    );

                root.pendingFocusBranch = root.pendingRenameNew;
                root.pendingFocusSha = "";
                root.managementMode = "";
                root.managementArm = "";
                return;
            }

            if (kind === "DELETE") {
                if (root.branchStackStore && root.pendingDeleteBranch)
                    root.branchStackStore.removeBranch(
                        root.pendingDeleteBranch
                    );

                root.selectedBranch = "";
                root.selectedSha = "";
                root.pendingDeleteBranch = "";
                root.managementMode = "";
                root.managementArm = "";
                return;
            }

            if (kind === "CREATE") {
                let linked = true;

                if (root.branchStackStore)
                    linked = root.branchStackStore.attachCreatedBranch(
                        root.pendingCreateAnchor,
                        root.pendingCreateName,
                        root.pendingCreateMode
                    );

                if (linked) {
                    root.pendingFocusBranch = root.pendingCreateName;
                    root.pendingFocusSha = "";
                    root.managementMessage =
                        "OK // CREATED + STACK LINKED";
                    root.managementMode = "";
                } else {
                    root.pendingFocusBranch = "";
                    root.pendingFocusSha = "";
                    root.managementMessage =
                        "CREATED // STACK LINK REFUSED // "
                        + "BRANCH EXISTS BUT NEEDS STACK REPAIR";
                }

                root.pendingCreateName = "";
                root.pendingCreateAnchor = "";
                root.pendingCreateMode = "";
                root.managementArm = "";
                return;
            }

            if (kind === "ADD-WORKTREE") {
                root.pendingFocusBranch = root.pendingWorkspaceBranch;
                root.pendingFocusSha = "";
                root.managementMessage =
                    "OK // WORKSPACE ATTACHED // "
                    + root.pendingWorkspacePath;
                root.pendingWorkspaceBranch = "";
                root.pendingWorkspaceAnchor = "";
                root.pendingWorkspacePath = "";
                root.managementArm = "";
                return;
            }

            if (kind === "NEW-WORKTREE") {
                let linked = true;

                if (root.branchStackStore)
                    linked = root.branchStackStore.attachCreatedBranch(
                        root.pendingWorkspaceAnchor,
                        root.pendingWorkspaceBranch,
                        "ABOVE"
                    );

                root.pendingFocusBranch = root.pendingWorkspaceBranch;
                root.pendingFocusSha = "";
                root.managementMessage =
                    linked
                    ? "OK // NEW WORKSPACE + STACK LINKED"
                    : "WORKSPACE CREATED // STACK LINK REFUSED";

                root.pendingWorkspaceBranch = "";
                root.pendingWorkspaceAnchor = "";
                root.pendingWorkspacePath = "";
                root.managementArm = "";
                return;
            }

            if (kind === "REMOVE-WORKTREE") {
                root.pendingFocusBranch = root.selectedBranch;
                root.pendingFocusSha = "";
                root.managementMessage =
                    "OK // WORKSPACE REMOVED";
                root.pendingWorkspaceBranch = "";
                root.pendingWorkspaceAnchor = "";
                root.pendingWorkspacePath = "";
                root.managementArm = "";
                return;
            }

            root.pendingFocusBranch = root.selectedBranch;
            root.pendingFocusSha = "";
            root.managementArm = "";
        }
    }

    function focusContext(branchName, sha) {
        root.pendingFocusBranch = String(branchName || "");
        root.pendingFocusSha = String(sha || "");
        root.applyFocusContext();
    }

    function applyFocusContext() {
        const branch = String(root.pendingFocusBranch || "");
        const sha = String(root.pendingFocusSha || "");

        if (!branch && !sha)
            return;

        if (branch && root.branchWorkspaceService) {
            const row =
                root.branchWorkspaceService.branchForName(branch);

            if (row) {
                root.selectBranch(branch);

                if (sha)
                    root.selectedSha = sha;

                root.pendingFocusBranch = "";
                root.pendingFocusSha = "";
                return;
            }
        }

        if (sha) {
            root.selectedSha = sha;

            const headBranch = root.branchForHead(sha);
            if (headBranch)
                root.selectedBranch = headBranch;

            // A non-tip commit still remains selected as commit context.
            root.pendingFocusSha = "";

            if (!branch)
                root.pendingFocusBranch = "";
        }
    }

    function branchForHead(sha) {
        const needle = String(sha || "");

        if (!needle || !branchWorkspaceService)
            return "";

        const rows = branchWorkspaceService.branches || [];

        for (let i = 0; i < rows.length; ++i) {
            if (String((rows[i] || {}).head || "") === needle)
                return String((rows[i] || {}).name || "");
        }

        return "";
    }

    function selectBranch(name) {
        const candidate = String(name || "");

        selectedBranch = candidate;

        const row = branchWorkspaceService
            ? branchWorkspaceService.branchForName(candidate)
            : null;

        selectedSha = row ? String(row.head || "") : "";
    }

    function selectCommit(sha) {
        const candidate = String(sha || "");
        selectedSha = selectedSha === candidate ? "" : candidate;

        if (!selectedSha)
            return;

        const branch = branchForHead(selectedSha);

        if (branch)
            selectedBranch = branch;
    }

    function shortSha(value) {
        const sha = String(value || "");
        return sha.length > 10 ? sha.slice(0, 10) : sha;
    }

    function cycleEditMode() {
        editMode = editMode === "NAME" ? "UP" : "NAME";

        if (root.managementMode === "edit")
            root.syncManagementEditors();
    }

    function cycleNewBranchMode() {
        newBranchMode =
            newBranchMode === "ABOVE"
            ? "BELOW"
            : "ABOVE";
    }

    function syncManagementEditors() {
        if (!root.selectedBranch)
            return;

        renameEditor.text = root.selectedBranch;
        upstreamEditor.text =
            root.selectedBranchData
            ? String(root.selectedBranchData.upstream || "")
            : "";
    }

    function openEditManager() {
        if (!root.selectedBranch || !root.branchWorkspaceService)
            return;

        root.managementMode = "edit";
        root.managementMessage = "";
        root.managementArm = "";
        root.syncManagementEditors();

        Qt.callLater(function() {
            if (root.editMode === "NAME")
                renameEditor.focusEditor();
            else
                upstreamEditor.focusEditor();
        });
    }

    function openDeleteManager() {
        if (!root.selectedBranch || !root.branchWorkspaceService)
            return;

        root.managementMode = "delete";
        root.managementMessage = "";
        root.managementArm = "";
        deleteConfirmEditor.text = "";
    }

    function openNewManager() {
        if (!root.selectedBranch || !root.branchWorkspaceService)
            return;

        root.managementMode = "new";
        root.managementMessage = "";
        root.managementArm = "";
        newBranchEditor.text = "";

        Qt.callLater(function() {
            newBranchEditor.focusEditor();
        });
    }

    function workspaceDefaultPath(branchName) {
        const repo =
            root.branchWorkspaceService
            ? String(root.branchWorkspaceService.repositoryPath || "").trim()
            : "";
        const branch =
            String(branchName || "")
            .split("/")
            .join("-");

        if (!repo || !branch)
            return "";

        return repo + "-wt-" + branch;
    }

    function openWorkspaceManager() {
        if (!root.selectedBranch || !root.branchWorkspaceService)
            return;

        root.managementMode = "workspace";
        root.managementMessage = "";
        root.managementArm = "";
        root.workspaceMode =
            root.selectedWorkspace
            ? "ATTACHED"
            : "ATTACH";

        workspacePathEditor.text =
            root.selectedWorkspace
            ? String(root.selectedWorkspace.path || "")
            : root.workspaceDefaultPath(root.selectedBranch);
        workspaceBranchEditor.text = "";
    }

    function closeManager() {
        root.managementMode = "";
        root.managementMessage = "";
        root.managementArm = "";

        if (root.keyboardHost
                && root.keyboardHost.activeTextEditor)
            root.keyboardHost.activeTextEditor = null;
    }

    function newBranchBlockReason() {
        if (!root.selectedBranch)
            return "SELECT A BRANCH";

        if (!root.branchWorkspaceService)
            return "BRANCH CORE NOT CONNECTED";

        if (root.branchWorkspaceService.actionBusy
                || root.branchWorkspaceService.refreshing)
            return "BRANCH CORE BUSY";

        if (root.newBranchMode === "BELOW"
                && !root.selectedStackParent)
            return "BELOW NEEDS AN EXISTING STACK PARENT";

        return "";
    }

    function newBranchStartPoint() {
        if (root.newBranchMode === "BELOW")
            return root.selectedStackParent;

        return root.selectedBranch;
    }

    function newBranchPreview(nameValue) {
        const name = String(nameValue || "").trim() || "NEW";

        if (root.newBranchMode === "BELOW") {
            return (
                (root.selectedStackParent || "NO PARENT")
                + " → "
                + name
                + " → "
                + root.selectedBranch
            );
        }

        return root.selectedBranch + " → " + name;
    }

    function applyCreateBranch() {
        if (!root.branchWorkspaceService || !root.selectedBranch)
            return;

        const blocked = root.newBranchBlockReason();

        if (blocked) {
            root.managementMessage = "REFUSED // " + blocked;
            return;
        }

        const name = String(newBranchEditor.text || "").trim();

        if (!name) {
            root.managementMessage = "REFUSED // BRANCH NAME REQUIRED";
            return;
        }

        if (root.branchWorkspaceService.branchForName(name)) {
            root.managementMessage =
                "REFUSED // LOCAL BRANCH ALREADY EXISTS";
            return;
        }

        root.pendingCreateName = name;
        root.pendingCreateAnchor = root.selectedBranch;
        root.pendingCreateMode = root.newBranchMode;
        root.pendingFocusBranch = name;
        root.pendingFocusSha = "";

        if (!root.branchWorkspaceService.createBranch(
                name,
                root.newBranchStartPoint()
            )) {
            root.pendingCreateName = "";
            root.pendingCreateAnchor = "";
            root.pendingCreateMode = "";
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
        }
    }

    function workspacePrimary() {
        if (!root.selectedWorkspace || !root.branchWorkspaceService)
            return false;

        return String(root.selectedWorkspace.path || "")
            === String(root.branchWorkspaceService.repositoryPath || "");
    }

    function workspaceRemoveBlockReason(forceRemove) {
        if (!root.selectedWorkspace)
            return "NO WORKSPACE ATTACHED";

        if (root.workspacePrimary())
            return "PRIMARY WORKTREE PROTECTED";

        if (Boolean(root.selectedWorkspace.locked))
            return "WORKTREE LOCKED // UNLOCK IN REPOSITORY";

        const dirty =
            Number(root.selectedWorkspace.dirtyCount || 0);

        if (!forceRemove && dirty > 0)
            return "DIRTY WORKTREE // FORCE REQUIRED";

        return "";
    }

    function applyAttachWorkspace() {
        if (!root.branchWorkspaceService || !root.selectedBranch)
            return;

        if (root.selectedWorkspace) {
            root.managementMessage =
                "REFUSED // BRANCH ALREADY HAS A WORKSPACE";
            return;
        }

        const path = String(workspacePathEditor.text || "").trim();

        if (!path) {
            root.managementMessage =
                "REFUSED // WORKSPACE PATH REQUIRED";
            return;
        }

        root.pendingWorkspaceBranch = root.selectedBranch;
        root.pendingWorkspaceAnchor = root.selectedBranch;
        root.pendingWorkspacePath = path;
        root.pendingFocusBranch = root.selectedBranch;
        root.pendingFocusSha = "";

        if (!root.branchWorkspaceService.addWorktree(
                path,
                root.selectedBranch
            )) {
            root.pendingWorkspaceBranch = "";
            root.pendingWorkspaceAnchor = "";
            root.pendingWorkspacePath = "";
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
        }
    }

    function applyNewWorkspace() {
        if (!root.branchWorkspaceService || !root.selectedBranch)
            return;

        const path = String(workspacePathEditor.text || "").trim();
        const branch =
            String(workspaceBranchEditor.text || "").trim();

        if (!branch) {
            root.managementMessage =
                "REFUSED // NEW BRANCH NAME REQUIRED";
            return;
        }

        if (!path) {
            root.managementMessage =
                "REFUSED // WORKSPACE PATH REQUIRED";
            return;
        }

        if (root.branchWorkspaceService.branchForName(branch)) {
            root.managementMessage =
                "REFUSED // LOCAL BRANCH ALREADY EXISTS";
            return;
        }

        root.pendingWorkspaceBranch = branch;
        root.pendingWorkspaceAnchor = root.selectedBranch;
        root.pendingWorkspacePath = path;
        root.pendingFocusBranch = branch;
        root.pendingFocusSha = "";

        if (!root.branchWorkspaceService.createWorktree(
                path,
                branch,
                root.selectedBranch
            )) {
            root.pendingWorkspaceBranch = "";
            root.pendingWorkspaceAnchor = "";
            root.pendingWorkspacePath = "";
            root.pendingFocusBranch = "";
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
        }
    }

    function requestRemoveWorkspace(forceRemove) {
        if (!root.branchWorkspaceService || !root.selectedWorkspace)
            return;

        const reason = root.workspaceRemoveBlockReason(forceRemove);

        if (reason) {
            root.managementMessage = "REFUSED // " + reason;
            root.managementArm = "";
            return;
        }

        const armKey =
            forceRemove
            ? "workspace-force-remove"
            : "workspace-remove";

        if (forceRemove
                && String(workspaceConfirmEditor.text || "").trim()
                   !== root.selectedBranch) {
            root.managementMessage =
                "TYPE THE EXACT BRANCH NAME TO FORCE REMOVE";
            root.managementArm = "";
            return;
        }

        if (root.managementArm !== armKey) {
            root.managementArm = armKey;
            root.managementMessage =
                forceRemove
                ? "ARMED // FORCE REMOVE WORKSPACE // PRESS AGAIN"
                : "ARMED // REMOVE WORKSPACE // PRESS AGAIN";
            return;
        }

        root.pendingWorkspaceBranch = root.selectedBranch;
        root.pendingWorkspaceAnchor = root.selectedBranch;
        root.pendingWorkspacePath =
            String(root.selectedWorkspace.path || "");
        root.managementArm = "";

        if (!root.branchWorkspaceService.removeWorktree(
                root.pendingWorkspacePath,
                forceRemove
            ))
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
    }

    function deleteBlockReason(forceDelete) {
        if (!root.selectedBranch)
            return "SELECT A BRANCH";

        if (root.selectedIsTrunk)
            return "TRUNK BRANCH PROTECTED";

        if (root.selectedIsCurrent)
            return "CURRENT BRANCH // SWITCH FIRST";

        if (root.selectedIsOccupied)
            return "BRANCH HAS A WORKTREE // REMOVE IT FIRST";

        if (!forceDelete && !root.selectedIsMerged)
            return "NOT MERGED // SAFE DELETE REFUSED";

        return "";
    }

    function applyRename() {
        if (!root.branchWorkspaceService || !root.selectedBranch)
            return;

        const nextName = String(renameEditor.text || "").trim();

        if (!nextName) {
            root.managementMessage = "REFUSED // NEW NAME REQUIRED";
            return;
        }

        if (nextName === root.selectedBranch) {
            root.managementMessage = "NO CHANGE // NAME IS THE SAME";
            return;
        }

        root.pendingRenameOld = root.selectedBranch;
        root.pendingRenameNew = nextName;
        root.pendingFocusBranch = nextName;
        root.pendingFocusSha = "";

        if (!root.branchWorkspaceService.renameBranch(
                root.pendingRenameOld,
                root.pendingRenameNew
            ))
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
    }

    function applyUpstream() {
        if (!root.branchWorkspaceService || !root.selectedBranch)
            return;

        const upstream = String(upstreamEditor.text || "").trim();

        if (!upstream) {
            root.managementMessage =
                "REFUSED // UPSTREAM REQUIRED OR USE CLEAR";
            return;
        }

        root.pendingFocusBranch = root.selectedBranch;
        root.pendingFocusSha = "";

        if (!root.branchWorkspaceService.setUpstream(
                root.selectedBranch,
                upstream
            ))
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
    }

    function clearUpstream() {
        if (!root.branchWorkspaceService || !root.selectedBranch)
            return;

        root.pendingFocusBranch = root.selectedBranch;
        root.pendingFocusSha = "";

        if (!root.branchWorkspaceService.clearUpstream(
                root.selectedBranch
            ))
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
    }

    function requestDelete(forceDelete) {
        if (!root.branchWorkspaceService || !root.selectedBranch)
            return;

        const reason = root.deleteBlockReason(forceDelete);

        if (reason) {
            root.managementMessage = "REFUSED // " + reason;
            root.managementArm = "";
            return;
        }

        const armKey = forceDelete ? "delete-force" : "delete-safe";

        if (forceDelete
                && String(deleteConfirmEditor.text || "").trim()
                   !== root.selectedBranch) {
            root.managementMessage =
                "TYPE THE EXACT BRANCH NAME TO FORCE DELETE";
            root.managementArm = "";
            return;
        }

        if (root.managementArm !== armKey) {
            root.managementArm = armKey;
            root.managementMessage =
                forceDelete
                ? "ARMED // FORCE DELETE // PRESS AGAIN"
                : "ARMED // SAFE DELETE // PRESS AGAIN";
            return;
        }

        root.pendingDeleteBranch = root.selectedBranch;
        root.managementArm = "";

        if (!root.branchWorkspaceService.deleteBranch(
                root.pendingDeleteBranch,
                forceDelete
            ))
            root.managementMessage = "REFUSED // BRANCH CORE BUSY";
    }

    function triggerEditMode() {
        root.openEditManager();
    }

    function triggerNewBranchMode() {
        root.openNewManager();
    }

    function triggerRestackActuator() {
        if (!selectedBranch || !stackPlanner || !stackExecutor)
            return;

        if (stackExecutor.running)
            return;

        if (stackExecutor.armed) {
            stackExecutor.executeArmed();
            return;
        }

        if (stackPlanner.startBranch === selectedBranch
                && stackPlanner.executable
                && stackPlanner.requiredCount > 0) {
            stackExecutor.armFromPlanner();
            return;
        }

        stackExecutor.disarm("NEW PREVIEW");
        stackPlanner.buildPlan(selectedBranch, true);
    }

    function restackActuatorLabel() {
        if (!stackPlanner || !stackExecutor)
            return "RESTACK";

        if (stackExecutor.running)
            return "RESTACKING";

        if (stackPlanner.busy)
            return "READING";

        if (stackExecutor.armed)
            return "RESTACK";

        if (stackPlanner.startBranch === selectedBranch
                && stackPlanner.executable
                && stackPlanner.requiredCount > 0)
            return "ARM";

        return "PREVIEW";
    }

    component BranchButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool destructive: false
        property bool selectedAction: false
        signal triggered()

        height: 30
        color:
            !enabledAction
            ? Colors.black
            : mouse.pressed
            ? destructive ? Colors.red : Colors.orange
            : selectedAction
            ? Colors.dark
            : Colors.black

        border.width:
            enabledAction && (mouse.containsMouse || selectedAction)
            ? 2
            : 1

        border.color:
            !enabledAction
            ? Colors.cyan
            : destructive
            ? Colors.red
            : selectedAction
            ? Colors.magenta
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 10
            color:
                mouse.pressed
                ? Colors.black
                : button.destructive
                ? Colors.red
                : button.selectedAction
                ? Colors.magenta
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

    component CompoundButton: Rectangle {
        id: compoundButton

        property string actionLabel: ""
        property string modeLabel: ""
        property bool enabledAction: true
        property bool modeEnabled: true
        property bool destructive: false

        signal triggered()
        signal modeTriggered()

        height: 30
        color:
            actionMouse.pressed
            ? destructive ? Colors.red : Colors.orange
            : Colors.black

        border.width:
            actionMouse.containsMouse || modeMouse.containsMouse
            ? 2
            : 1

        border.color:
            destructive
            ? Colors.red
            : actionMouse.containsMouse || modeMouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors {
                left: parent.left
                leftMargin: 8
                verticalCenter: parent.verticalCenter
            }
            text: compoundButton.actionLabel
            font.pixelSize: 10
            color:
                compoundButton.destructive
                ? Colors.red
                : Colors.cyan
            opacity: compoundButton.enabledAction ? 1.0 : 0.38
        }

        Rectangle {
            id: modeTag

            anchors {
                right: parent.right
                rightMargin: 5
                verticalCenter: parent.verticalCenter
            }

            width: Math.max(52, modeText.implicitWidth + 16)
            height: 22
            color:
                modeMouse.pressed
                ? Colors.magenta
                : modeMouse.containsMouse
                ? Colors.dark
                : Colors.black
            border.width: 1
            border.color:
                modeMouse.containsMouse
                ? Colors.orange
                : Colors.magenta
            opacity: compoundButton.modeEnabled ? 1.0 : 0.34

            GohuText {
                id: modeText
                anchors.centerIn: parent
                text: compoundButton.modeLabel
                font.pixelSize: 10
                color: Colors.magenta
            }

            MouseArea {
                id: modeMouse
                anchors.fill: parent
                enabled: compoundButton.modeEnabled
                hoverEnabled: true
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: compoundButton.modeTriggered()
                onWheel: function(wheel) {
                    compoundButton.modeTriggered();
                    wheel.accepted = true;
                }
            }
        }

        MouseArea {
            id: actionMouse

            anchors {
                left: parent.left
                top: parent.top
                bottom: parent.bottom
                right: modeTag.left
            }

            enabled: compoundButton.enabledAction
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

            onClicked: function(mouse) {
                if (mouse.button === Qt.RightButton)
                    compoundButton.modeTriggered();
                else
                    compoundButton.triggered();
            }

            onWheel: function(wheel) {
                if (compoundButton.modeEnabled) {
                    compoundButton.modeTriggered();
                    wheel.accepted = true;
                }
            }
        }
    }

    component BranchEditor: Rectangle {
        id: editorBox

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan

        function focusEditor() {
            editor.forceActiveFocus();
            editor.selectAll();
        }

        height: 34
        color: Colors.black
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.orange
            : editorBox.accent
        clip: true

        TextInput {
            id: editor

            anchors {
                fill: parent
                leftMargin: 8
                rightMargin: 8
            }

            verticalAlignment: Text.AlignVCenter
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 11
            clip: true

            onActiveFocusChanged: {
                if (!root.keyboardHost)
                    return;

                if (activeFocus)
                    root.keyboardHost.activeTextEditor = editor;
                else if (root.keyboardHost.activeTextEditor === editor)
                    root.keyboardHost.activeTextEditor = null;
            }
        }

        GohuText {
            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: 8
                rightMargin: 8
            }

            visible: editor.text.length === 0
            text: editorBox.placeholder
            font.pixelSize: 10
            color: Colors.white
            opacity: 0.34
            elide: Text.ElideRight
        }
    }

    component FactRow: Row {
        property string label: ""
        property string value: ""
        property color valueColor: Colors.white

        width: parent ? parent.width : 0
        height: 22
        spacing: 8

        GohuText {
            width: 62
            anchors.verticalCenter: parent.verticalCenter
            text: parent.label
            font.pixelSize: 10
            color: Colors.magenta
        }

        GohuText {
            width: parent.width - 70
            anchors.verticalCenter: parent.verticalCenter
            text: parent.value || "—"
            font.pixelSize: 11
            color: parent.valueColor
            elide: Text.ElideMiddle
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
                    margins: 8
                }
                spacing: 12

                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "BRANCHES // OPERATING MAP"
                    font.pixelSize: 12
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 7
                        samples: 9
                        opacity: 0.48
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }

                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        branchWorkspaceService
                        ? String((branchWorkspaceService.branches || []).length)
                          + " LOCAL // "
                          + String((branchWorkspaceService.worktrees || []).length)
                          + " WORKSPACES"
                          + (
                              branchStackStore
                              ? " // "
                                + String(
                                    (branchStackStore.repositoryRelations || []).length
                                  )
                                + " STACK LINKS"
                              : ""
                            )
                        : "NO BRANCH SERVICE"
                    font.pixelSize: 10
                    color: Colors.cyan
                }

                Item {
                    width: Math.max(
                        0,
                        parent.width
                        - parent.children[0].implicitWidth
                        - parent.children[1].implicitWidth
                        - refreshButton.width
                        - parent.spacing * 3
                    )
                    height: 1
                }

                BranchButton {
                    id: refreshButton
                    width: 92
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        branchWorkspaceService
                        && branchWorkspaceService.refreshing
                        ? "READING"
                        : "REFRESH"
                    enabledAction:
                        branchWorkspaceService
                        && !branchWorkspaceService.refreshing
                        && !branchWorkspaceService.actionBusy

                    onTriggered: branchWorkspaceService.refresh()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 50
            spacing: 8

            Rectangle {
                id: mapPane

                width: parent.width * 0.70
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                BranchMap {
                    anchors {
                        fill: parent
                        margins: 1
                    }

                    topologyService: root.gitService
                    titleText:
                        root.selectedBranch
                        ? "REPOSITORY TOPOLOGY // " + root.selectedBranch
                        : "REPOSITORY TOPOLOGY"
                    selectedSha: root.selectedSha

                    onCommitSelected: function(sha) {
                        root.selectCommit(sha);
                    }
                }

                Rectangle {
                    id: branchSelectorStrip

                    anchors {
                        left: parent.left
                        right: parent.right
                        bottom: parent.bottom
                        leftMargin: 12
                        rightMargin: 12
                        bottomMargin: 10
                    }

                    height: 52
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.blue
                    z: 80
                    clip: true

                    Flickable {
                        id: branchStripFlick

                        anchors {
                            left: parent.left
                            right: parent.right
                            top: parent.top
                            bottom: branchStripRail.top
                            margins: 5
                            bottomMargin: 3
                        }

                        contentWidth: Math.max(width, branchStripRow.implicitWidth)
                        contentHeight: height
                        flickableDirection: Flickable.HorizontalFlick
                        boundsBehavior: Flickable.StopAtBounds
                        clip: true

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.NoButton
                            propagateComposedEvents: true

                            onWheel: function(wheel) {
                                const step =
                                    wheel.angleDelta.y > 0
                                    ? -72
                                    : 72;

                                branchStripFlick.contentX =
                                    Math.max(
                                        0,
                                        Math.min(
                                            branchStripRail.maxContentX,
                                            branchStripFlick.contentX + step
                                        )
                                    );
                                wheel.accepted = true;
                            }
                        }

                        Row {
                            id: branchStripRow

                            height: parent.height
                            spacing: 5

                            Repeater {
                                model:
                                    branchWorkspaceService
                                    ? branchWorkspaceService.branches
                                    : []

                                Rectangle {
                                    required property var modelData

                                    height: 32
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: Math.max(
                                        112,
                                        Math.min(
                                            260,
                                            branchName.implicitWidth + 24
                                        )
                                    )

                                    readonly property bool isSelected:
                                        root.selectedBranch
                                        === String(modelData.name || "")

                                    readonly property bool isCurrent:
                                        branchWorkspaceService
                                        && String(modelData.name || "")
                                        === branchWorkspaceService.currentBranch

                                    readonly property var workspace:
                                        branchWorkspaceService
                                        ? branchWorkspaceService.worktreeForBranch(
                                              String(modelData.name || "")
                                          )
                                        : null

                                    color:
                                        isSelected
                                        ? Colors.dark
                                        : Colors.black
                                    border.width: isSelected ? 2 : 1
                                    border.color:
                                        isCurrent
                                        ? Colors.yellow
                                        : workspace
                                        ? Colors.magenta
                                        : isSelected
                                        ? Colors.orange
                                        : Colors.blue

                                    GohuText {
                                        id: branchName

                                        anchors {
                                            left: parent.left
                                            right: parent.right
                                            verticalCenter: parent.verticalCenter
                                            leftMargin: 8
                                            rightMargin: 8
                                        }

                                        text:
                                            (parent.isCurrent ? "★ " : "")
                                            + String(parent.modelData.name || "")
                                        font.pixelSize: 13
                                        color:
                                            parent.isCurrent
                                            ? Colors.yellow
                                            : parent.workspace
                                            ? Colors.magenta
                                            : parent.isSelected
                                            ? Colors.orange
                                            : Colors.cyan
                                        elide: Text.ElideMiddle
                                        horizontalAlignment: Text.AlignHCenter
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked:
                                            root.selectBranch(
                                                String(parent.modelData.name || "")
                                            )

                                        onWheel: function(wheel) {
                                            const step =
                                                wheel.angleDelta.y > 0
                                                ? -72
                                                : 72;

                                            branchStripFlick.contentX =
                                                Math.max(
                                                    0,
                                                    Math.min(
                                                        branchStripRail.maxContentX,
                                                        branchStripFlick.contentX + step
                                                    )
                                                );
                                            wheel.accepted = true;
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: branchStripRail

                        anchors {
                            left: parent.left
                            right: parent.right
                            bottom: parent.bottom
                            leftMargin: 5
                            rightMargin: 5
                            bottomMargin: 4
                        }

                        height: 6
                        color: Colors.cyan
                        opacity: 1.0
                        border.width: 1
                        border.color: Colors.cyan

                        Rectangle {
                            anchors.fill: parent
                            color: Colors.black
                            opacity:
                                branchStripFlick.contentWidth
                                > branchStripFlick.width + 1
                                ? 0.18
                                : 0.62
                        }

                        readonly property real maxContentX:
                            Math.max(
                                0,
                                branchStripFlick.contentWidth
                                - branchStripFlick.width
                            )

                        Rectangle {
                            id: branchStripHandle

                            height: parent.height
                            width:
                                Math.max(
                                    34,
                                    parent.width
                                    * Math.min(
                                        1,
                                        branchStripFlick.width
                                        / Math.max(
                                            branchStripFlick.contentWidth,
                                            1
                                        )
                                    )
                                )
                            x:
                                branchStripRail.maxContentX > 0
                                ? (
                                    branchStripFlick.contentX
                                    / branchStripRail.maxContentX
                                  )
                                  * Math.max(0, parent.width - width)
                                : 0
                            color: Colors.magenta
                            opacity: 1.0
                            border.width: 1
                            border.color: Colors.magenta

                            RectangularShadow {
                                anchors.fill: parent
                                spread: 1
                                z: -1
                                opacity: 0.50
                                color: Colors.magenta
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled:
                                branchStripRail.maxContentX > 0
                            hoverEnabled: true
                            cursorShape:
                                enabled
                                ? Qt.PointingHandCursor
                                : Qt.ArrowCursor

                            function scrollTo(mouseX) {
                                const travel =
                                    branchStripRail.width
                                    - branchStripHandle.width;
                                const target =
                                    mouseX
                                    - branchStripHandle.width / 2;
                                const ratio =
                                    travel > 0
                                    ? Math.max(
                                        0,
                                        Math.min(
                                            1,
                                            target / travel
                                        )
                                      )
                                    : 0;

                                branchStripFlick.contentX =
                                    ratio
                                    * branchStripRail.maxContentX;
                            }

                            onPressed: function(mouse) {
                                scrollTo(mouse.x);
                            }

                            onPositionChanged: function(mouse) {
                                if (pressed)
                                    scrollTo(mouse.x);
                            }
                        }
                    }
                }

            }

            Rectangle {
                id: inspector

                width: parent.width - mapPane.width - parent.spacing
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color:
                    root.selectedBranch
                    ? Colors.magenta
                    : Colors.cyan

                Column {
                    anchors {
                        fill: parent
                        margins: 10
                    }
                    spacing: 6

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedBranch
                            ? "SELECTED // " + root.selectedBranch
                            : "SELECT A BRANCH"
                        font.pixelSize: 14
                        color:
                            root.selectedBranch
                            ? Colors.magenta
                            : Colors.cyan
                        elide: Text.ElideMiddle
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.36
                    }

                    Column {
                        width: parent.width
                        spacing: 1

                        FactRow {
                            label: "STATE"
                            value:
                                (
                                    root.selectedBranchData
                                    ? root.shortSha(root.selectedBranchData.head)
                                    : "—"
                                )
                                + " // "
                                + (
                                    root.selectedIsCurrent
                                    ? "LIVE"
                                    : root.selectedIsOccupied
                                    ? "WORKTREE"
                                    : "IDLE"
                                  )
                                + (
                                    root.selectedWorkspace
                                    ? " // "
                                      + String(
                                          root.selectedWorkspace.dirtyCount || 0
                                        )
                                      + " DIRTY"
                                    : ""
                                  )
                            valueColor:
                                root.selectedIsCurrent
                                ? Colors.yellow
                                : root.selectedIsOccupied
                                ? Colors.magenta
                                : Colors.orange
                        }

                        FactRow {
                            label: "UP"
                            value:
                                root.selectedBranchData
                                ? String(
                                    root.selectedBranchData.upstream
                                    || "NONE"
                                  )
                                : ""
                            valueColor: Colors.cyan
                        }

                        FactRow {
                            label: "WORK"
                            value:
                                root.selectedWorkspace
                                ? String(root.selectedWorkspace.path || "")
                                : "NONE"
                            valueColor:
                                root.selectedWorkspace
                                ? Colors.magenta
                                : Colors.white
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.24
                    }

                    GohuText {
                        text: "BRANCH"
                        font.pixelSize: 10
                        color: Colors.orange
                    }

                    Grid {
                        width: parent.width
                        columns: 2
                        columnSpacing: 6
                        rowSpacing: 5

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label:
                                root.selectedIsCurrent
                                ? "LIVE"
                                : "SWITCH"
                            selectedAction: root.selectedIsCurrent
                            enabledAction:
                                root.selectedBranch.length > 0
                                && !root.selectedIsCurrent
                                && !root.selectedIsOccupied
                                && branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !branchWorkspaceService.refreshing
                            onTriggered:
                                branchWorkspaceService.switchBranch(
                                    root.selectedBranch,
                                    "origin",
                                    false
                                )
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "HISTORY"
                            enabledAction:
                                root.selectedBranch.length > 0
                            onTriggered:
                                root.historyRequested(
                                    root.selectedBranch
                                )
                        }

                        CompoundButton {
                            width: (inspector.width - 26) / 2
                            actionLabel: "EDIT"
                            modeLabel: root.editMode
                            enabledAction:
                                root.selectedBranch.length > 0
                                && branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !branchWorkspaceService.refreshing
                            modeEnabled:
                                root.selectedBranch.length > 0
                                && !branchWorkspaceService.actionBusy
                            onTriggered: root.triggerEditMode()
                            onModeTriggered: root.cycleEditMode()
                        }

                        CompoundButton {
                            width: (inspector.width - 26) / 2
                            actionLabel: "NEW"
                            modeLabel: root.newBranchMode
                            enabledAction:
                                root.selectedBranch.length > 0
                                && branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !branchWorkspaceService.refreshing
                            modeEnabled:
                                root.selectedBranch.length > 0
                                && branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !branchWorkspaceService.refreshing
                            onTriggered: root.triggerNewBranchMode()
                            onModeTriggered: root.cycleNewBranchMode()
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label:
                                root.selectedWorkspace
                                ? "WORKSPACE ✓"
                                : "WORKSPACE"
                            selectedAction:
                                root.selectedWorkspace !== null
                            enabledAction:
                                root.selectedBranch.length > 0
                                && branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !branchWorkspaceService.refreshing
                            onTriggered: root.openWorkspaceManager()
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "DELETE"
                            destructive: true
                            enabledAction:
                                root.selectedBranch.length > 0
                                && branchWorkspaceService
                                && !branchWorkspaceService.actionBusy
                                && !branchWorkspaceService.refreshing
                            onTriggered: root.openDeleteManager()
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.24
                    }

                    GohuText {
                        text: "STACK"
                        font.pixelSize: 10
                        color: Colors.orange
                    }

                    Column {
                        width: parent.width
                        spacing: 1

                        FactRow {
                            label: "CHAIN"
                            value:
                                root.selectedBranch
                                ? (
                                    (
                                        root.selectedStackParent
                                        || (
                                            root.selectedBranch
                                            === String(
                                                branchStackStore
                                                ? branchStackStore.trunkBranch
                                                : ""
                                            )
                                            ? "TRUNK"
                                            : "UNSET"
                                        )
                                    )
                                    + " → "
                                    + root.selectedBranch
                                    + (
                                        root.selectedStackChildren.length > 0
                                        ? " → "
                                          + root.selectedStackChildren.join(" • ")
                                        : ""
                                      )
                                  )
                                : ""
                            valueColor: Colors.cyan
                        }

                        FactRow {
                            label: "TREE"
                            value:
                                root.selectedBranch
                                ? (
                                    "ROOT "
                                    + (root.selectedStackRoot || "—")
                                    + " // "
                                    + String(
                                        root.selectedStackDescendants.length
                                      )
                                    + " BELOW"
                                  )
                                : ""
                            valueColor:
                                root.selectedStackDescendants.length > 0
                                ? Colors.magenta
                                : Colors.white
                        }
                    }

                    Grid {
                        width: parent.width
                        columns: 2
                        columnSpacing: 6
                        rowSpacing: 5

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: root.restackActuatorLabel()
                            selectedAction:
                                stackExecutor && stackExecutor.armed
                            enabledAction:
                                root.selectedBranch.length > 0
                                && stackPlanner
                                && stackExecutor
                                && !stackExecutor.running
                                && !stackPlanner.busy
                                && (
                                    stackExecutor.armed
                                    || (
                                        stackPlanner.startBranch
                                        === root.selectedBranch
                                        && stackPlanner.executable
                                        && stackPlanner.requiredCount > 0
                                       )
                                    || root.selectedStackParent.length > 0
                                    || root.selectedStackDescendants.length > 0
                                )
                            onTriggered:
                                root.triggerRestackActuator()
                        }

                        BranchButton {
                            width: (inspector.width - 26) / 2
                            label: "SUBMIT STACK"
                            enabledAction: false
                            onTriggered:
                                root.submitStackRequested(root.selectedBranch)
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height:
                            stackPlanner
                            && stackPlanner.plan.length > 0
                            ? Math.min(
                                78,
                                26 + stackPlanColumn.implicitHeight
                              )
                            : 26
                        color: Colors.black
                        border.width: 1
                        border.color:
                            stackPlanner && stackPlanner.invalidCount > 0
                            ? Colors.red
                            : stackPlanner && stackPlanner.requiredCount > 0
                            ? Colors.orange
                            : Colors.cyan
                        clip: true

                        Column {
                            anchors {
                                fill: parent
                                margins: 6
                            }
                            spacing: 3

                            GohuText {
                                width: parent.width
                                text:
                                    stackExecutor && stackExecutor.running
                                    ? stackExecutor.stateText
                                    : stackExecutor && stackExecutor.armed
                                    ? stackExecutor.armStatus
                                    : stackExecutor && stackExecutor.lastError
                                    ? stackExecutor.lastError
                                    : stackPlanner
                                    ? stackPlanner.stateText
                                    : "RESTACK PREVIEW // NOT CONNECTED"
                                font.pixelSize: 7
                                color:
                                    stackPlanner && stackPlanner.invalidCount > 0
                                    ? Colors.red
                                    : stackPlanner && stackPlanner.requiredCount > 0
                                    ? Colors.orange
                                    : Colors.cyan
                                elide: Text.ElideRight
                            }

                            Column {
                                id: stackPlanColumn

                                width: parent.width
                                spacing: 1

                                Repeater {
                                    model:
                                        stackPlanner
                                        ? stackPlanner.plan.slice(0, 3)
                                        : []

                                    GohuText {
                                        required property var modelData

                                        width: stackPlanColumn.width
                                        text:
                                            String(modelData.branch || "")
                                            + " → "
                                            + String(modelData.parent || "")
                                            + " // "
                                            + String(modelData.status || "")
                                        font.pixelSize: 7
                                        color:
                                            String(modelData.status || "")
                                            === "RESTACK_REQUIRED"
                                            ? Colors.orange
                                            : String(modelData.status || "")
                                              === "UP_TO_DATE"
                                            ? Colors.cyan
                                            : Colors.red
                                        elide: Text.ElideMiddle
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        width: 1
                        height: Math.max(
                            0,
                            parent.height - y - serviceState.height
                        )
                    }

                    GohuText {
                        id: serviceState

                        width: parent.width
                        text:
                            !branchWorkspaceService
                            ? "BRANCH CORE // NOT CONNECTED"
                            : branchWorkspaceService.lastError
                            ? "ERR // " + branchWorkspaceService.lastError
                            : branchWorkspaceService.actionBusy
                            ? branchWorkspaceService.actionStatus
                            : branchWorkspaceService.refreshing
                            ? "READING BRANCH + WORKTREE STATE"
                            : "BRANCH CORE // READY"
                        font.pixelSize: 7
                        color:
                            branchWorkspaceService
                            && branchWorkspaceService.lastError
                            ? Colors.red
                            : Colors.cyan
                        wrapMode: Text.WrapAnywhere
                    }
                }

                Rectangle {
                    id: branchManager

                    anchors {
                        fill: parent
                        margins: 6
                    }

                    visible: root.managementMode.length > 0
                    z: 500
                    color: Colors.black
                    border.width: 2
                    border.color:
                        root.managementMode === "delete"
                        ? Colors.red
                        : root.managementMode === "new"
                        ? Colors.green
                        : Colors.magenta
                    clip: true

                    Column {
                        anchors {
                            fill: parent
                            margins: 10
                        }
                        spacing: 8

                        Row {
                            width: parent.width
                            height: 32
                            spacing: 6

                            GohuText {
                                width: parent.width - 82
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.managementMode === "delete"
                                    ? "DELETE // " + root.selectedBranch
                                    : root.managementMode === "new"
                                    ? "NEW // " + root.selectedBranch
                                    : "EDIT // " + root.selectedBranch
                                font.pixelSize: 13
                                color:
                                    root.managementMode === "delete"
                                    ? Colors.red
                                    : root.managementMode === "new"
                                    ? Colors.green
                                    : Colors.magenta
                                elide: Text.ElideMiddle
                            }

                            BranchButton {
                                width: 76
                                height: 32
                                label: "CLOSE"
                                onTriggered: root.closeManager()
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color:
                                root.managementMode === "delete"
                                ? Colors.red
                                : root.managementMode === "new"
                                ? Colors.green
                                : Colors.cyan
                            opacity: 0.46
                        }

                        Column {
                            width: parent.width
                            spacing: 8
                            visible: root.managementMode === "edit"

                            Row {
                                width: parent.width
                                height: 30
                                spacing: 6

                                BranchButton {
                                    width: (parent.width - 6) / 2
                                    label: "NAME"
                                    selectedAction: root.editMode === "NAME"
                                    onTriggered: {
                                        root.editMode = "NAME";
                                        root.syncManagementEditors();
                                        Qt.callLater(function() {
                                            renameEditor.focusEditor();
                                        });
                                    }
                                }

                                BranchButton {
                                    width: (parent.width - 6) / 2
                                    label: "UPSTREAM"
                                    selectedAction: root.editMode === "UP"
                                    onTriggered: {
                                        root.editMode = "UP";
                                        root.syncManagementEditors();
                                        Qt.callLater(function() {
                                            upstreamEditor.focusEditor();
                                        });
                                    }
                                }
                            }

                            GohuText {
                                width: parent.width
                                visible: root.editMode === "NAME"
                                text:
                                    "RENAME LOCAL BRANCH // "
                                    + root.selectedBranch
                                font.pixelSize: 10
                                color: Colors.cyan
                                elide: Text.ElideMiddle
                            }

                            BranchEditor {
                                id: renameEditor
                                width: parent.width
                                visible: root.editMode === "NAME"
                                placeholder: "NEW BRANCH NAME"
                                accent: Colors.magenta
                            }

                            BranchButton {
                                width: parent.width
                                visible: root.editMode === "NAME"
                                label:
                                    branchWorkspaceService
                                    && branchWorkspaceService.actionBusy
                                    ? "RENAMING"
                                    : "APPLY RENAME"
                                enabledAction:
                                    root.editMode === "NAME"
                                    && branchWorkspaceService
                                    && !branchWorkspaceService.actionBusy
                                    && String(renameEditor.text || "").trim().length > 0
                                onTriggered: root.applyRename()
                            }

                            GohuText {
                                width: parent.width
                                visible: root.editMode === "UP"
                                text:
                                    "CURRENT // "
                                    + (
                                        root.selectedBranchData
                                        ? String(
                                            root.selectedBranchData.upstream
                                            || "NONE"
                                          )
                                        : "NONE"
                                      )
                                font.pixelSize: 10
                                color: Colors.cyan
                                elide: Text.ElideMiddle
                            }

                            BranchEditor {
                                id: upstreamEditor
                                width: parent.width
                                visible: root.editMode === "UP"
                                placeholder: "UPSTREAM // origin/main"
                                accent: Colors.cyan
                            }

                            Row {
                                width: parent.width
                                height: 32
                                spacing: 6
                                visible: root.editMode === "UP"

                                BranchButton {
                                    width: (parent.width - 6) / 2
                                    height: 32
                                    label: "SET UPSTREAM"
                                    enabledAction:
                                        branchWorkspaceService
                                        && !branchWorkspaceService.actionBusy
                                        && String(upstreamEditor.text || "").trim().length > 0
                                    onTriggered: root.applyUpstream()
                                }

                                BranchButton {
                                    width: (parent.width - 6) / 2
                                    height: 32
                                    label: "CLEAR"
                                    destructive: true
                                    enabledAction:
                                        branchWorkspaceService
                                        && !branchWorkspaceService.actionBusy
                                        && root.selectedBranchData
                                        && String(
                                            root.selectedBranchData.upstream
                                            || ""
                                          ).length > 0
                                    onTriggered: root.clearUpstream()
                                }
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.editMode === "NAME"
                                    ? "Git renames the local branch. Stack links follow the new name automatically."
                                    : "Use an existing remote ref such as origin/main. CLEAR removes tracking only."
                                font.pixelSize: 9
                                color: Colors.white
                                opacity: 0.58
                                wrapMode: Text.WordWrap
                            }
                        }

                        Column {
                            width: parent.width
                            spacing: 8
                            visible: root.managementMode === "new"

                            GohuText {
                                width: parent.width
                                text:
                                    "CREATE RELATIVE TO // "
                                    + root.selectedBranch
                                font.pixelSize: 10
                                color: Colors.cyan
                                elide: Text.ElideMiddle
                            }

                            Row {
                                width: parent.width
                                height: 32
                                spacing: 6

                                BranchButton {
                                    width: (parent.width - 6) / 2
                                    height: 32
                                    label: "ABOVE"
                                    selectedAction:
                                        root.newBranchMode === "ABOVE"
                                    onTriggered:
                                        root.newBranchMode = "ABOVE"
                                }

                                BranchButton {
                                    width: (parent.width - 6) / 2
                                    height: 32
                                    label: "BELOW"
                                    selectedAction:
                                        root.newBranchMode === "BELOW"
                                    enabledAction:
                                        root.selectedStackParent.length > 0
                                    onTriggered:
                                        root.newBranchMode = "BELOW"
                                }
                            }

                            BranchEditor {
                                id: newBranchEditor
                                width: parent.width
                                placeholder: "NEW BRANCH NAME"
                                accent: Colors.green
                            }

                            Rectangle {
                                width: parent.width
                                height: 72
                                color: Colors.dark
                                border.width: 1
                                border.color:
                                    root.newBranchBlockReason()
                                    ? Colors.orange
                                    : Colors.green

                                Column {
                                    anchors {
                                        fill: parent
                                        margins: 7
                                    }
                                    spacing: 4

                                    GohuText {
                                        width: parent.width
                                        text:
                                            root.newBranchMode
                                            + " // "
                                            + root.newBranchPreview(
                                                newBranchEditor.text
                                              )
                                        font.pixelSize: 10
                                        color: Colors.green
                                        elide: Text.ElideMiddle
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            root.newBranchBlockReason()
                                            ? root.newBranchBlockReason()
                                            : (
                                                "START // "
                                                + root.newBranchStartPoint()
                                              )
                                        font.pixelSize: 9
                                        color:
                                            root.newBranchBlockReason()
                                            ? Colors.orange
                                            : Colors.cyan
                                        elide: Text.ElideMiddle
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            root.newBranchMode === "ABOVE"
                                            ? "NEW BECOMES A CHILD OF THE SELECTED BRANCH"
                                            : "NEW IS INSERTED BETWEEN THE SELECTED BRANCH AND ITS PARENT"
                                        font.pixelSize: 8
                                        color: Colors.white
                                        opacity: 0.58
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            BranchButton {
                                width: parent.width
                                height: 36
                                label:
                                    branchWorkspaceService
                                    && branchWorkspaceService.actionBusy
                                    ? "CREATING"
                                    : "CREATE BRANCH"
                                enabledAction:
                                    branchWorkspaceService
                                    && !branchWorkspaceService.actionBusy
                                    && !branchWorkspaceService.refreshing
                                    && root.newBranchBlockReason().length === 0
                                    && String(
                                        newBranchEditor.text || ""
                                      ).trim().length > 0
                                onTriggered: root.applyCreateBranch()
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    "CREATE ONLY // LIVE CHECKOUT DOES NOT SWITCH. "
                                    + "The new branch is selected here after Git confirms creation."
                                font.pixelSize: 9
                                color: Colors.white
                                opacity: 0.62
                                wrapMode: Text.WordWrap
                            }
                        }

                        Column {
                            width: parent.width
                            spacing: 8
                            visible: root.managementMode === "delete"

                            FactRow {
                                label: "STATE"
                                value:
                                    root.selectedIsCurrent
                                    ? "CURRENT // PROTECTED"
                                    : root.selectedIsOccupied
                                    ? "WORKTREE // PROTECTED"
                                    : root.selectedIsTrunk
                                    ? "TRUNK // PROTECTED"
                                    : root.selectedIsMerged
                                    ? "MERGED // SAFE DELETE AVAILABLE"
                                    : "UNMERGED // FORCE REQUIRED"
                                valueColor:
                                    root.deleteBlockReason(false)
                                    ? Colors.orange
                                    : Colors.green
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.deleteBlockReason(false)
                                    ? root.deleteBlockReason(false)
                                    : "SAFE DELETE USES GIT -d AND REFUSES UNMERGED WORK"
                                font.pixelSize: 10
                                color:
                                    root.deleteBlockReason(false)
                                    ? Colors.orange
                                    : Colors.cyan
                                wrapMode: Text.WordWrap
                            }

                            BranchButton {
                                width: parent.width
                                height: 34
                                label:
                                    root.managementArm === "delete-safe"
                                    ? "CONFIRM SAFE DELETE"
                                    : "SAFE DELETE"
                                destructive: true
                                enabledAction:
                                    branchWorkspaceService
                                    && !branchWorkspaceService.actionBusy
                                    && root.deleteBlockReason(false).length === 0
                                onTriggered: root.requestDelete(false)
                            }

                            Rectangle {
                                width: parent.width
                                height: 1
                                color: Colors.red
                                opacity: 0.42
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    "FORCE DELETE BYPASSES MERGE SAFETY. "
                                    + "TYPE THE EXACT BRANCH NAME:"
                                font.pixelSize: 10
                                color: Colors.red
                                wrapMode: Text.WordWrap
                            }

                            BranchEditor {
                                id: deleteConfirmEditor
                                width: parent.width
                                placeholder:
                                    root.selectedBranch
                                    ? root.selectedBranch
                                    : "BRANCH NAME"
                                accent: Colors.red
                            }

                            BranchButton {
                                width: parent.width
                                height: 34
                                label:
                                    root.managementArm === "delete-force"
                                    ? "CONFIRM FORCE DELETE"
                                    : "FORCE DELETE"
                                destructive: true
                                enabledAction:
                                    branchWorkspaceService
                                    && !branchWorkspaceService.actionBusy
                                    && root.deleteBlockReason(true).length === 0
                                    && String(
                                        deleteConfirmEditor.text || ""
                                      ).trim() === root.selectedBranch
                                onTriggered: root.requestDelete(true)
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 52
                            color: Colors.dark
                            border.width: 1
                            border.color:
                                root.managementMessage.indexOf("REFUSED") === 0
                                ? Colors.red
                                : root.managementMessage.indexOf("ARMED") === 0
                                ? Colors.orange
                                : Colors.cyan

                            GohuText {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                text:
                                    root.managementMessage
                                    || (
                                        root.managementMode === "delete"
                                        ? "DELETE WAITS FOR EXPLICIT CONFIRMATION"
                                        : root.managementMode === "new"
                                        ? "CREATE DOES NOT SWITCH THE LIVE CHECKOUT"
                                        : "EDIT CHANGES ONLY THE SELECTED LOCAL BRANCH"
                                       )
                                font.pixelSize: 9
                                color:
                                    root.managementMessage.indexOf("REFUSED") === 0
                                    ? Colors.red
                                    : root.managementMessage.indexOf("ARMED") === 0
                                    ? Colors.orange
                                    : Colors.cyan
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }
}
