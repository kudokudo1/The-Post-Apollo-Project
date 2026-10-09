import QtQuick
import QtQuick.Effects
import qs.components

Item {
    id: root

    property var repositoryService: null
    property var gitService: null
    property var branchWorkspaceService: null
    property var keyboardHost: null

    property string subMode: "remotes"

    property int selectedRemoteIndex: -1
    property string selectedRemoteName: ""
    property string selectedRemoteBranch: ""
    property string selectedTag: ""
    property string tagMode: "lightweight"
    property string selectedWorktreePath: ""
    property bool selectedWorktreeLocked: false
    property string projectFileKind: "ignore"
    property int selectedProjectLine: -1
    property string selectedProjectText: ""
    property string projectLineFilterText: ""
    property string armedAction: ""
    property string configCategory: "all"
    property string configFilterText: ""
    property string selectedConfigKey: ""

    function selectRemote(index, row) {
        const data = row || {};
        root.selectedRemoteIndex = index;
        root.selectedRemoteName = String(data.name || "");
        remoteNameInput.text = root.selectedRemoteName;
        remoteUrlInput.text = String(data.url || "");
        pushUrlInput.text = String(data.pushUrl || "");
        fetchSpecInput.text = String(data.fetchSpec || "");
        pushSpecInput.text = String(data.pushSpec || "");
        root.selectedRemoteBranch = "";
        root.armedAction = "";
    }

    function remoteBranchRows() {
        if (!root.repositoryService)
            return [];

        const rows = root.repositoryService.remoteBranches || [];

        if (!root.selectedRemoteName)
            return rows;

        const out = [];

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (String(row.remote || "") === root.selectedRemoteName)
                out.push(row);
        }

        return out;
    }

    function armOrRun(key, callback) {
        if (root.armedAction !== key) {
            root.armedAction = key;
            return;
        }

        root.armedAction = "";
        callback();
    }

    function projectLines() {
        if (!root.repositoryService)
            return [];

        return root.projectFileKind === "attributes"
            ? root.repositoryService.attributeLines
            : root.repositoryService.ignoreLines;
    }

    function projectLineType(value) {
        const raw = String(value || "");
        const visible = raw.replace(/^\s+/, "");

        if (!raw.trim())
            return "blank";

        if (visible.indexOf("#") === 0)
            return "comment";

        if (root.projectFileKind === "ignore"
                && visible.indexOf("!") === 0)
            return "negate";

        if (root.projectFileKind === "attributes"
                && visible.indexOf("[attr]") === 0)
            return "macro";

        return "rule";
    }

    function projectLineTypeLabel(typeValue) {
        const type = String(typeValue || "rule");

        if (type === "comment")
            return "COMMENT";
        if (type === "blank")
            return "BLANK";
        if (type === "negate")
            return "NEGATE";
        if (type === "macro")
            return "MACRO";
        return "RULE";
    }

    function projectLineColor(typeValue) {
        const type = String(typeValue || "rule");

        if (type === "comment")
            return Colors.cyan;
        if (type === "blank")
            return Colors.blue;
        if (type === "negate")
            return Colors.orange;
        if (type === "macro")
            return Colors.magenta;
        return Colors.green;
    }

    function projectLinesForView() {
        const source = root.projectLines();
        const needle =
            String(root.projectLineFilterText || "")
            .trim()
            .toLowerCase();
        const out = [];

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const text = String(row.text || "");
            const type = root.projectLineType(text);

            if (needle) {
                const haystack = (
                    text
                    + " "
                    + root.projectLineTypeLabel(type)
                    + " "
                    + String(row.line || "")
                ).toLowerCase();

                if (haystack.indexOf(needle) < 0)
                    continue;
            }

            out.push({
                line: Number(row.line || 0),
                text: text,
                type: type
            });
        }

        return out;
    }

    function projectLineExists(value) {
        const text = String(value || "");
        const rows = root.projectLines();

        for (let i = 0; i < rows.length; ++i) {
            if (String(rows[i].text || "") === text)
                return true;
        }

        return false;
    }

    function projectLineCount(typeValue) {
        const rows = root.projectLines();
        const type = String(typeValue || "");
        let count = 0;

        for (let i = 0; i < rows.length; ++i) {
            if (root.projectLineType(rows[i].text) === type)
                count += 1;
        }

        return count;
    }

    function selectProjectLine(row) {
        const data = row || {};

        root.selectedProjectLine = Number(data.line || -1);
        root.selectedProjectText = String(data.text || "");
        projectLineInput.text = root.selectedProjectText;
        root.armedAction = "";
    }

    function clearProjectSelection(clearInput) {
        root.selectedProjectLine = -1;
        root.selectedProjectText = "";
        root.armedAction = "";

        if (clearInput)
            projectLineInput.text = "";
    }

    function reconcileProjectSelection() {
        if (!root.repositoryService
                || root.selectedProjectLine <= 0)
            return;

        const rows = root.projectLines();

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};

            if (Number(row.line || 0) === root.selectedProjectLine
                    && String(row.text || "")
                       === root.selectedProjectText)
                return;
        }

        let matchLine = -1;
        let matches = 0;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};

            if (String(row.text || "") !== root.selectedProjectText)
                continue;

            matches += 1;
            matchLine = Number(row.line || -1);
        }

        if (matches === 1) {
            root.selectedProjectLine = matchLine;
            return;
        }

        root.clearProjectSelection(false);
    }

    function projectInputChanged() {
        return root.selectedProjectLine > 0
            && String(projectLineInput.text || "")
               !== root.selectedProjectText;
    }

    function projectInputDuplicate() {
        const text = String(projectLineInput.text || "");

        if (!text)
            return false;

        if (root.selectedProjectLine > 0
                && text === root.selectedProjectText)
            return false;

        return root.projectLineExists(text);
    }

    function projectFileGuidance() {
        if (root.projectFileKind === "attributes") {
            return "RULE assigns Git attributes to a path pattern. MACRO defines a reusable [attr] name. Comments and blank lines are preserved exactly.";
        }

        return "RULE ignores matching untracked paths. NEGATE (!) re-includes a path after an earlier ignore. Comments and blank lines are preserved exactly.";
    }

    function healthStateColor() {
        if (!root.repositoryService)
            return Colors.cyan;

        const state =
            String(root.repositoryService.healthState || "");

        if (state === "PASS")
            return Colors.green;
        if (state === "RECOVERY")
            return Colors.magenta;
        if (state === "WARNING")
            return Colors.orange;
        if (state === "FAIL")
            return Colors.red;

        return Colors.cyan;
    }

    function objectConditionText() {
        if (!root.repositoryService)
            return "UNKNOWN";

        if (root.repositoryService.garbageObjectCount > 0)
            return "GARBAGE DETECTED";

        if (root.repositoryService.prunePackableCount > 0)
            return "CLEANUP AVAILABLE";

        return "NORMAL";
    }

    function objectConditionColor() {
        if (!root.repositoryService)
            return Colors.cyan;

        if (root.repositoryService.garbageObjectCount > 0)
            return Colors.red;

        if (root.repositoryService.prunePackableCount > 0)
            return Colors.orange;

        return Colors.green;
    }

    function healthCleanupBlocked() {
        return Boolean(
            root.repositoryService
            && root.repositoryService.healthState === "FAIL"
        );
    }

    function runHealthCleanup(kind) {
        if (!root.repositoryService
                || root.repositoryService.actionBusy
                || root.healthCleanupBlocked())
            return;

        const action = String(kind || "");
        const recovery =
            root.repositoryService.healthState === "RECOVERY";

        if (action === "gc") {
            if (recovery) {
                root.armOrRun(
                    "gc-recovery",
                    function() {
                        root.repositoryService.runGcAuto();
                    }
                );
                return;
            }

            root.repositoryService.runGcAuto();
            return;
        }

        if (action === "maintenance") {
            if (recovery) {
                root.armOrRun(
                    "maintenance-recovery",
                    function() {
                        root.repositoryService.runMaintenance();
                    }
                );
                return;
            }

            root.repositoryService.runMaintenance();
        }
    }

    function configCategoryForKey(keyValue) {
        const key = String(keyValue || "").trim().toLowerCase();

        if (!key)
            return "other";

        if (key.indexOf("user.") === 0
                || key.indexOf("author.") === 0
                || key.indexOf("committer.") === 0
                || key.indexOf("gpg.") === 0
                || key === "commit.gpgsign")
            return "identity";

        if (key.indexOf("remote.") === 0
                || key.indexOf("fetch.") === 0
                || key.indexOf("push.") === 0
                || key.indexOf("pull.") === 0
                || key.indexOf("url.") === 0
                || key.indexOf("http.") === 0)
            return "sync";

        if (key.indexOf("branch.") === 0
                || key.indexOf("checkout.") === 0
                || key.indexOf("worktree.") === 0
                || key === "init.defaultbranch")
            return "branch";

        if (key.indexOf("diff.") === 0
                || key.indexOf("merge.") === 0
                || key.indexOf("rebase.") === 0
                || key.indexOf("rerere.") === 0
                || key.indexOf("log.") === 0
                || key.indexOf("blame.") === 0
                || key.indexOf("color.") === 0)
            return "history";

        if (key.indexOf("core.") === 0
                || key.indexOf("extensions.") === 0
                || key.indexOf("gc.") === 0
                || key.indexOf("maintenance.") === 0
                || key.indexOf("submodule.") === 0
                || key.indexOf("lfs.") === 0)
            return "repo";

        return "other";
    }

    function configCategoryLabel(categoryValue) {
        const category = String(categoryValue || "other");

        if (category === "identity")
            return "IDENTITY";
        if (category === "sync")
            return "SYNC";
        if (category === "branch")
            return "BRANCH";
        if (category === "history")
            return "HISTORY";
        if (category === "repo")
            return "REPO";
        if (category === "all")
            return "ALL";
        return "OTHER";
    }

    function configCategoryColor(categoryValue) {
        const category = String(categoryValue || "other");

        if (category === "identity")
            return Colors.magenta;
        if (category === "sync")
            return Colors.cyan;
        if (category === "branch")
            return Colors.green;
        if (category === "history")
            return Colors.orange;
        if (category === "repo")
            return Colors.yellow;
        if (category === "all")
            return Colors.green;
        return Colors.blue;
    }

    function configRowsForView() {
        if (!root.repositoryService)
            return [];

        const source = root.repositoryService.configRows || [];
        const category = String(root.configCategory || "all");
        const needle =
            String(root.configFilterText || "")
            .trim()
            .toLowerCase();
        const out = [];

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const rowCategory =
                root.configCategoryForKey(row.key);

            if (category !== "all"
                    && rowCategory !== category)
                continue;

            if (needle) {
                const haystack = (
                    String(row.key || "")
                    + " "
                    + String(row.value || "")
                ).toLowerCase();

                if (haystack.indexOf(needle) < 0)
                    continue;
            }

            out.push({
                key: String(row.key || ""),
                value: String(row.value || ""),
                category: rowCategory
            });
        }

        const order = {
            identity: 0,
            sync: 1,
            branch: 2,
            history: 3,
            repo: 4,
            other: 5
        };

        out.sort(function(a, b) {
            const ca = order[a.category] !== undefined
                ? order[a.category]
                : 99;
            const cb = order[b.category] !== undefined
                ? order[b.category]
                : 99;

            if (ca !== cb)
                return ca - cb;

            return String(a.key || "").localeCompare(
                String(b.key || "")
            );
        });

        return out;
    }

    function configKeyExists(keyValue) {
        if (!root.repositoryService)
            return false;

        const key = String(keyValue || "").trim();
        const rows = root.repositoryService.configRows || [];

        for (let i = 0; i < rows.length; ++i) {
            if (String(rows[i].key || "") === key)
                return true;
        }

        return false;
    }

    function configGuidance(keyValue) {
        const key = String(keyValue || "").trim();
        const category = root.configCategoryForKey(key);

        if (!key)
            return "Select an existing key or type a new repo-local override.";

        if (key.indexOf("remote.") === 0)
            return "Remote transport keys are editable here, but REMOTES is the clearer surface for URLs, refspecs, fetch, prune, and remote HEAD.";

        if (key.indexOf("branch.") === 0)
            return "Branch tracking keys live in .git/config. BRANCHES is usually the clearer surface for upstream and stack relationships.";

        if (category === "identity")
            return "Repository-local identity/signing overrides apply only to this repository. Global identity remains untouched.";

        if (category === "sync")
            return "Controls this repository's fetch, pull, push, URL, or transport behavior.";

        if (category === "history")
            return "Controls diff, merge, rebase, rerere, log, blame, or display behavior for this repository.";

        if (category === "repo")
            return "Controls repository mechanics such as core behavior, extensions, maintenance, submodules, or LFS.";

        return "This editor writes only the repository-local .git/config scope.";
    }

    function selectConfigRow(row) {
        const data = row || {};
        root.selectedConfigKey = String(data.key || "");
        configKeyInput.text = root.selectedConfigKey;
        configValueInput.text = String(data.value || "");
        root.armedAction = "";
    }

    function cycleTagMode() {
        if (root.tagMode === "lightweight")
            root.tagMode = "annotated";
        else if (root.tagMode === "annotated")
            root.tagMode = "signed";
        else
            root.tagMode = "lightweight";
    }

    function tagModeLabel() {
        if (root.tagMode === "annotated")
            return "ANNOTATED";
        if (root.tagMode === "signed")
            return "SIGNED";
        return "LIGHTWEIGHT";
    }

    function selectedRemoteRow() {
        if (!root.repositoryService || !root.selectedRemoteName)
            return null;

        const rows = root.repositoryService.remotes || [];

        for (let i = 0; i < rows.length; ++i) {
            if (String(rows[i].name || "") === root.selectedRemoteName)
                return rows[i];
        }

        return null;
    }

    function selectedTagRow() {
        if (!root.repositoryService || !root.selectedTag)
            return null;

        const rows = root.repositoryService.tags || [];

        for (let i = 0; i < rows.length; ++i) {
            if (String(rows[i].name || "") === root.selectedTag)
                return rows[i];
        }

        return null;
    }

    function ageLabel(epochValue) {
        const epoch = Number(epochValue || 0);

        if (epoch <= 0)
            return "UNKNOWN";

        const seconds = Math.max(
            0,
            Math.floor(Date.now() / 1000) - epoch
        );

        if (seconds < 3600)
            return String(Math.max(1, Math.floor(seconds / 60))) + "M";
        if (seconds < 86400)
            return String(Math.floor(seconds / 3600)) + "H";
        if (seconds < 86400 * 90)
            return String(Math.floor(seconds / 86400)) + "D";
        if (seconds < 86400 * 365)
            return String(Math.floor(seconds / (86400 * 30))) + "MO";

        return String(Math.floor(seconds / (86400 * 365))) + "Y";
    }

    function remoteNewestEpoch(nameValue) {
        if (!root.repositoryService)
            return 0;

        const name = String(nameValue || "");
        const rows = root.repositoryService.remoteBranches || [];
        let newest = 0;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (String(row.remote || "") !== name)
                continue;

            newest = Math.max(newest, Number(row.epoch || 0));
        }

        return newest;
    }

    function remoteOldestEpoch(nameValue) {
        if (!root.repositoryService)
            return 0;

        const name = String(nameValue || "");
        const rows = root.repositoryService.remoteBranches || [];
        let oldest = 0;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            if (String(row.remote || "") !== name)
                continue;

            const epoch = Number(row.epoch || 0);
            if (epoch <= 0)
                continue;

            if (oldest <= 0 || epoch < oldest)
                oldest = epoch;
        }

        return oldest;
    }

    function remoteUpstreamCount(nameValue) {
        if (!root.repositoryService)
            return 0;

        const remote = String(nameValue || "");
        const rows = root.repositoryService.configRows || [];
        let count = 0;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            const key = String(row.key || "");
            const value = String(row.value || "");

            if (key.indexOf("branch.") === 0
                    && key.lastIndexOf(".remote")
                       === key.length - 7
                    && value === remote)
                count += 1;
        }

        return count;
    }

    function remoteTransportLabel(rowValue) {
        const row = rowValue || {};
        const fetchUrl = String(row.url || "");
        const pushUrl = String(row.pushUrl || "");

        if (!fetchUrl && !pushUrl)
            return "NO URL";

        return fetchUrl === pushUrl
            ? "SAME FETCH/PUSH"
            : "SPLIT FETCH/PUSH";
    }

    function tagKindLabel(rowValue) {
        const row = rowValue || {};
        const kind = String(row.kind || "lightweight");

        if (kind === "signed")
            return "SIGNED";
        if (kind === "annotated")
            return "ANNOTATED";
        return "LIGHTWEIGHT";
    }

    function tagKindColor(rowValue) {
        const kind = String((rowValue || {}).kind || "lightweight");

        if (kind === "signed")
            return Colors.magenta;
        if (kind === "annotated")
            return Colors.orange;
        return Colors.cyan;
    }

    function selectedTagRemoteState() {
        if (!root.repositoryService
                || !root.selectedTag
                || !tagRemoteInput.text.trim())
            return "UNCHECKED";

        if (root.repositoryService.tagRemoteCheckTag
                !== root.selectedTag
                || root.repositoryService.tagRemoteCheckRemote
                   !== tagRemoteInput.text.trim())
            return "UNCHECKED";

        return String(
            root.repositoryService.tagRemoteCheckState
            || "UNCHECKED"
        );
    }

    function tagRemoteStateColor() {
        const state = root.selectedTagRemoteState();

        if (state === "MATCH")
            return Colors.green;
        if (state === "MISSING")
            return Colors.orange;
        if (state === "DIVERGED" || state === "ERROR")
            return Colors.red;
        if (state === "CHECKING")
            return Colors.cyan;

        return Colors.blue;
    }

    function tagRemoteStatusText() {
        if (!root.repositoryService)
            return "NO REPOSITORY SERVICE";

        const state = root.selectedTagRemoteState();
        const remote = String(tagRemoteInput.text || "").trim();

        if (state === "MATCH")
            return (
                "MATCH // "
                + remote
                + " RESOLVES TO "
                + String(
                    root.repositoryService.tagRemoteTarget
                    || ""
                  ).slice(0, 10)
            );

        if (state === "MISSING")
            return "MISSING // PUSH SELECTED TAG WILL CREATE IT";

        if (state === "DIVERGED")
            return (
                "DIVERGED // LOCAL "
                + String(
                    root.repositoryService.tagRemoteLocalTarget
                    || ""
                  ).slice(0, 10)
                + " // REMOTE "
                + String(
                    root.repositoryService.tagRemoteTarget
                    || ""
                  ).slice(0, 10)
                + " // NORMAL PUSH WILL REFUSE"
            );

        if (state === "CHECKING")
            return "CHECKING REMOTE TAG // NETWORK READ";

        if (state === "ERROR")
            return "REMOTE TAG CHECK FAILED // SEE STATUS BAR";

        return "UNCHECKED // REMOTE PRESENCE REQUIRES EXPLICIT NETWORK READ";
    }

    component SectionLabel: GohuText {
        font.pixelSize: 14
        color: Colors.magenta
    }

    component MiniButton: ActionButton {
        id: button

        // Temporary lossless Git adapter. These are preserved historical
        // values, not canonical ActionButton policy; they can be synchronized
        // later once the user chooses the desired final look.
        property color accent: Colors.cyan
        property bool enabledAction: true

        height: 28

        accentColor: accent
        available: enabledAction
        interactive: enabledAction
        acceptedButtons: Qt.LeftButton

        idleFillColor: Colors.black
        hoverFillColor: Colors.dark
        pressedFillColor: accent
        selectedFillColor: Colors.dark

        idleForegroundColor: accent
        hoverForegroundColor: accent
        pressedForegroundColor: Colors.black
        selectedForegroundColor: Colors.white

        idleBorderColor: accent
        hoverBorderColor: accent
        pressedBorderColor: accent
        selectedBorderColor: accent

        idleBorderWidth: 1
        hoverBorderWidth: 1
        pressedBorderWidth: 1
        selectedBorderWidth: 2

        unavailableOpacity: 0.26

        // The original Git MiniButton family is intentionally flat.
        contentGlowEnabled: false
        softGlowEnabled: false
        wideGlowEnabled: false

        showLabel: false

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 10
            color: button.foregroundColor
        }
    }

    component EditorBox: Rectangle {
        id: editorBox

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan
        property var keyboardOwner: null

        height: 30
        color: Colors.black
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.orange
            : accent

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
                if (!editorBox.keyboardOwner)
                    return;

                if (activeFocus)
                    editorBox.keyboardOwner.activeTextEditor = editor;
                else if (
                    editorBox.keyboardOwner.activeTextEditor === editor
                )
                    editorBox.keyboardOwner.activeTextEditor = null;
            }
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 8
            }
            visible: editor.text.length === 0
            text: editorBox.placeholder
            font.pixelSize: 10
            color: Colors.white
            opacity: 0.30
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        SectionFrame {
            width: parent.width
            height: 62
            fillColor: Colors.dark
            borderWidth: 1
            borderColor: Colors.orange
            inset: 8

            Row {
                anchors.fill: parent
                spacing: 8

                Column {
                    width: parent.width - 236
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    SectionLabel {
                        text: "REPOSITORY // MECHANICS"
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.gitService
                            ? String(root.gitService.repoRoot || "NO LOCAL REPOSITORY")
                            : "NO LOCAL REPOSITORY"
                        font.pixelSize: 10
                        color: Colors.cyan
                        elide: Text.ElideMiddle
                    }
                }

                MiniButton {
                    width: 106
                    anchors.verticalCenter: parent.verticalCenter
                    label: "LAZYGIT"
                    accent: Colors.magenta
                    enabledAction:
                        root.gitService
                        && root.gitService.repoIsLocal
                    onTriggered: root.gitService.launchLazygit()
                }

                MiniButton {
                    width: 114
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.repositoryService
                        && root.repositoryService.refreshing
                        ? "READING"
                        : "REFRESH ALL"
                    accent: Colors.green
                    enabledAction:
                        root.repositoryService
                        && !root.repositoryService.refreshing
                        && !root.repositoryService.actionBusy
                    onTriggered: {
                        root.repositoryService.refresh();
                        if (root.branchWorkspaceService)
                            root.branchWorkspaceService.refresh();
                    }
                }
            }
        }

        Row {
            width: parent.width
            height: 34
            spacing: 5

            Repeater {
                model: [
                    { key: "remotes", label: "REMOTES", color: Colors.magenta },
                    { key: "tags", label: "TAGS", color: Colors.orange },
                    { key: "worktrees", label: "WORKTREES", color: Colors.cyan },
                    { key: "config", label: "CONFIG", color: Colors.green },
                    { key: "files", label: "FILES", color: Colors.yellow },
                    { key: "hooks", label: "HOOKS", color: Colors.blue },
                    { key: "health", label: "HEALTH", color: Colors.red }
                ]

                MiniButton {
                    required property var modelData
                    width:
                        (
                            parent.width
                            - parent.spacing * 6
                        ) / 7
                    height: 34
                    label: modelData.label
                    accent: modelData.color
                    selected: root.subMode === modelData.key
                    onTriggered: {
                        root.subMode = modelData.key;
                        root.armedAction = "";
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - 154

            // ===== REMOTES ===============================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "remotes"

                Rectangle {
                    width: 360
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        GohuText {
                            width: parent.width
                            text:
                                "REMOTES // "
                                + String(
                                    root.repositoryService
                                    ? root.repositoryService.remotes.length
                                    : 0
                                  )
                            font.pixelSize: 12
                            color: Colors.magenta
                        }

                        Flickable {
                            id: repositoryScroll1
                            width: parent.width
                            height: parent.height - 24
                            clip: true
                            contentWidth: width
                            contentHeight: remoteColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: remoteColumn
                                width: parent.width
                                spacing: 3

                                Repeater {
                                    model:
                                        root.repositoryService
                                        ? root.repositoryService.remotes
                                        : []

                                    Rectangle {
                                        id: remoteRow
                                        required property int index
                                        required property var modelData

                                        width: remoteColumn.width
                                        height: 70
                                        color:
                                            remoteMouse.containsMouse
                                            || root.selectedRemoteIndex === index
                                            ? Colors.black
                                            : "transparent"
                                        border.width:
                                            root.selectedRemoteIndex === index
                                            ? 1 : 0
                                        border.color: Colors.magenta

                                        Column {
                                            anchors {
                                                fill: parent
                                                margins: 7
                                            }
                                            spacing: 2

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        remoteRow.modelData.name
                                                        || ""
                                                    )
                                                font.pixelSize: 11
                                                color: Colors.magenta
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    "FETCH // "
                                                    + String(
                                                        remoteRow.modelData.url
                                                        || ""
                                                      )
                                                font.pixelSize: 9
                                                color: Colors.white
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    "PUSH  // "
                                                    + String(
                                                        remoteRow.modelData.pushUrl
                                                        || ""
                                                      )
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    "HEAD // "
                                                    + String(
                                                        remoteRow.modelData.defaultBranch
                                                        || "UNKNOWN"
                                                      )
                                                    + " // PRUNE "
                                                    + String(
                                                        remoteRow.modelData.prune
                                                        || "default"
                                                      ).toUpperCase()
                                                font.pixelSize: 8
                                                color: Colors.orange
                                                elide: Text.ElideRight
                                            }
                                        }

                                        MouseArea {
                                            id: remoteMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked:
                                                root.selectRemote(
                                                    remoteRow.index,
                                                    remoteRow.modelData
                                                )
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll1
                            }
}
                    }
                }

                Rectangle {
                    width: parent.width - 368
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: remoteNameInput
                                width: 160
                                placeholder: "REMOTE NAME"
                                accent: Colors.magenta
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 76
                                height: 30
                                label: "FETCH"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.fetchRemote(
                                        root.selectedRemoteName
                                    )
                            }

                            MiniButton {
                                width: 76
                                height: 30
                                label: "PRUNE"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.pruneRemote(
                                        root.selectedRemoteName
                                    )
                            }

                            MiniButton {
                                width: 88
                                height: 30
                                label: "SYNC HEAD"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.syncRemoteHead(
                                        root.selectedRemoteName
                                    )
                            }

                            MiniButton {
                                width: 94
                                height: 30
                                label:
                                    root.armedAction === "remove-remote"
                                    ? "CONFIRM"
                                    : "REMOVE"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "remove-remote",
                                        function() {
                                            root.repositoryService.removeRemote(
                                                root.selectedRemoteName,
                                                true
                                            );
                                            root.selectedRemoteIndex = -1;
                                            root.selectedRemoteName = "";
                                        }
                                    )
                            }

                            MiniButton {
                                width:
                                    parent.width
                                    - 160
                                    - 76
                                    - 76
                                    - 88
                                    - 94
                                    - 25
                                height: 30
                                label: "ADD / RENAME"
                                accent: Colors.cyan
                                enabledAction:
                                    root.repositoryService
                                    && remoteNameInput.text.trim().length > 0
                                    && !root.repositoryService.actionBusy
                                onTriggered: {
                                    if (root.selectedRemoteName
                                            && remoteNameInput.text.trim()
                                               !== root.selectedRemoteName) {
                                        root.repositoryService.renameRemote(
                                            root.selectedRemoteName,
                                            remoteNameInput.text.trim()
                                        );
                                        root.selectedRemoteName =
                                            remoteNameInput.text.trim();
                                    } else if (!root.selectedRemoteName
                                               && remoteUrlInput.text.trim()) {
                                        root.repositoryService.addRemote(
                                            remoteNameInput.text.trim(),
                                            remoteUrlInput.text.trim()
                                        );
                                    }
                                }
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: remoteUrlInput
                                width: parent.width - 112
                                placeholder: "FETCH URL"
                                accent: Colors.cyan
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 107
                                height: 30
                                label: "SET FETCH URL"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedRemoteName
                                    && remoteUrlInput.text.trim().length > 0
                                    && root.repositoryService
                                onTriggered:
                                    root.repositoryService.setRemoteUrl(
                                        root.selectedRemoteName,
                                        remoteUrlInput.text.trim()
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: pushUrlInput
                                width: parent.width - 112
                                placeholder: "PUSH URL"
                                accent: Colors.orange
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 107
                                height: 30
                                label: "SET PUSH URL"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedRemoteName
                                    && pushUrlInput.text.trim().length > 0
                                    && root.repositoryService
                                onTriggered:
                                    root.repositoryService.setPushUrl(
                                        root.selectedRemoteName,
                                        pushUrlInput.text.trim()
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            EditorBox {
                                id: fetchSpecInput
                                width: (parent.width - 112 - 5) / 2
                                placeholder: "FETCH REFSPEC"
                                accent: Colors.green
                                keyboardOwner: root.keyboardHost
                            }

                            EditorBox {
                                id: pushSpecInput
                                width: (parent.width - 112 - 5) / 2
                                placeholder: "PUSH REFSPEC"
                                accent: Colors.magenta
                                keyboardOwner: root.keyboardHost
                            }

                            MiniButton {
                                width: 107
                                height: 30
                                label: "SAVE SPECS"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedRemoteName
                                    && root.repositoryService
                                onTriggered: {
                                    if (fetchSpecInput.text.trim())
                                        root.repositoryService.setFetchSpec(
                                            root.selectedRemoteName,
                                            fetchSpecInput.text.trim()
                                        );
                                    if (pushSpecInput.text.trim())
                                        root.repositoryService.setPushSpec(
                                            root.selectedRemoteName,
                                            pushSpecInput.text.trim()
                                        );
                                }
                            }
                        }

                        SectionFrame {
                            width: parent.width
                            height: 82
                            fillColor: Colors.dark
                            borderWidth: 1
                            borderColor: Colors.magenta
                            inset: 7

                            Column {
                                anchors.fill: parent
                                spacing: 4

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.selectedRemoteName
                                        ? "REMOTE INTELLIGENCE // "
                                          + root.selectedRemoteName
                                        : "REMOTE INTELLIGENCE // SELECT REMOTE"
                                    font.pixelSize: 10
                                    color: Colors.magenta
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text: {
                                        const row =
                                            root.selectedRemoteRow();

                                        if (!row)
                                            return "HEAD UNKNOWN // 0 TRACKING REFS // 0 LOCAL UPSTREAMS";

                                        return (
                                            "HEAD "
                                            + String(
                                                row.defaultBranch
                                                || "UNKNOWN"
                                              )
                                            + " // "
                                            + String(
                                                root.remoteBranchRows().length
                                              )
                                            + " TRACKING REFS // "
                                            + String(
                                                root.remoteUpstreamCount(
                                                    root.selectedRemoteName
                                                )
                                              )
                                            + " LOCAL UPSTREAMS"
                                        );
                                    }
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text: {
                                        const row =
                                            root.selectedRemoteRow();

                                        if (!row)
                                            return "NO REMOTE SELECTED";

                                        return (
                                            root.remoteTransportLabel(row)
                                            + " // PRUNE "
                                            + String(
                                                row.prune || "default"
                                              ).toUpperCase()
                                            + " // NEWEST TIP "
                                            + root.ageLabel(
                                                root.remoteNewestEpoch(
                                                    root.selectedRemoteName
                                                )
                                              )
                                            + " // OLDEST TIP "
                                            + root.ageLabel(
                                                root.remoteOldestEpoch(
                                                    root.selectedRemoteName
                                                )
                                              )
                                        );
                                    }
                                    font.pixelSize: 9
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        "TIP ages describe remote-tracking commit activity, not time since last fetch."
                                    font.pixelSize: 8
                                    color: Colors.white
                                    opacity: 0.48
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.22
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "REMOTE BRANCHES // "
                                + String(root.remoteBranchRows().length)
                            font.pixelSize: 11
                            color: Colors.cyan
                        }

                        Flickable {
                            id: repositoryScroll2
                            width: parent.width
                            height: parent.height - 277
                            clip: true
                            contentWidth: width
                            contentHeight: remoteBranchColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: remoteBranchColumn
                                width: parent.width
                                spacing: 3

                                Repeater {
                                    model: root.remoteBranchRows()

                                    Rectangle {
                                        id: remoteBranchRow
                                        required property var modelData

                                        width: remoteBranchColumn.width
                                        height: 34
                                        color:
                                            remoteBranchMouse.containsMouse
                                            || root.selectedRemoteBranch
                                               === String(modelData.name || "")
                                            ? Colors.dark
                                            : "transparent"
                                        border.width:
                                            root.selectedRemoteBranch
                                            === String(modelData.name || "")
                                            ? 1 : 0
                                        border.color: Colors.orange

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            width: parent.width - 98
                                            text:
                                                String(
                                                    remoteBranchRow.modelData.name
                                                    || ""
                                                )
                                                + " // "
                                                + String(
                                                    remoteBranchRow.modelData.shortSha
                                                    || ""
                                                )
                                                + " // "
                                                + root.ageLabel(
                                                    remoteBranchRow.modelData.epoch
                                                )
                                            font.pixelSize: 10
                                            color: Colors.white
                                            elide: Text.ElideMiddle
                                        }

                                        MiniButton {
                                            width: 92
                                            height: 26
                                            anchors {
                                                right: parent.right
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            label:
                                                root.armedAction
                                                === "delete-rbranch:"
                                                   + String(
                                                       remoteBranchRow.modelData.name
                                                       || ""
                                                     )
                                                ? "CONFIRM"
                                                : "DELETE"
                                            accent: Colors.red
                                            enabledAction:
                                                root.repositoryService
                                                && !root.repositoryService.actionBusy
                                            onTriggered: {
                                                const full = String(
                                                    remoteBranchRow.modelData.name
                                                    || ""
                                                );
                                                const slash = full.indexOf("/");
                                                if (slash <= 0)
                                                    return;
                                                const remote = full.slice(0, slash);
                                                const branchName = full.slice(slash + 1);
                                                root.armOrRun(
                                                    "delete-rbranch:" + full,
                                                    function() {
                                                        root.repositoryService
                                                            .deleteRemoteBranch(
                                                                remote,
                                                                branchName,
                                                                true
                                                            );
                                                    }
                                                );
                                            }
                                        }

                                        MouseArea {
                                            id: remoteBranchMouse
                                            anchors {
                                                left: parent.left
                                                right: parent.right
                                                rightMargin: 98
                                                top: parent.top
                                                bottom: parent.bottom
                                            }
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked:
                                                root.selectedRemoteBranch =
                                                    String(
                                                        remoteBranchRow.modelData.name
                                                        || ""
                                                    )
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll2
                            }
}
                    }
                }
            }

            // ===== TAGS ==================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "tags"

                Rectangle {
                    width: 470
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

                    Flickable {
                        id: repositoryScroll3
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: tagColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: tagColumn
                            width: parent.width
                            spacing: 3

                            Repeater {
                                model:
                                    root.repositoryService
                                    ? root.repositoryService.tags
                                    : []

                                Rectangle {
                                    id: tagRow
                                    required property var modelData

                                    width: tagColumn.width
                                    height: 62
                                    color:
                                        tagMouse.containsMouse
                                        || root.selectedTag
                                           === String(modelData.name || "")
                                        ? Colors.black
                                        : "transparent"
                                    border.width:
                                        root.selectedTag
                                        === String(modelData.name || "")
                                        ? 1 : 0
                                    border.color: Colors.orange

                                    Column {
                                        anchors {
                                            fill: parent
                                            margins: 7
                                        }
                                        spacing: 2

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(tagRow.modelData.name || "")
                                                + " // "
                                                + root.tagKindLabel(
                                                    tagRow.modelData
                                                )
                                                + (
                                                    Boolean(
                                                        tagRow.modelData.atHead
                                                    )
                                                    ? " // HEAD ✓"
                                                    : ""
                                                  )
                                            font.pixelSize: 11
                                            color:
                                                root.tagKindColor(
                                                    tagRow.modelData
                                                )
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    tagRow.modelData.targetType
                                                    || "object"
                                                ).toUpperCase()
                                                + " // "
                                                + String(
                                                    tagRow.modelData.targetSha
                                                    || tagRow.modelData.shortSha
                                                    || ""
                                                  ).slice(0, 10)
                                                + " // AGE "
                                                + root.ageLabel(
                                                    tagRow.modelData.epoch
                                                )
                                            font.pixelSize: 8
                                            color: Colors.cyan
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    tagRow.modelData.subject || ""
                                                )
                                            font.pixelSize: 9
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: tagMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.selectedTag =
                                                String(
                                                    tagRow.modelData.name || ""
                                                );
                                            tagNameInput.text =
                                                root.selectedTag;
                                            if (root.repositoryService)
                                                root.repositoryService
                                                    .clearTagRemoteCheck();
                                            root.armedAction = "";
                                        }
                                    }
                                }
                            }
                        }
                    
                        NeonScrollBar {
                            flickable: repositoryScroll3
                        }
}
                }

                SectionFrame {
                    width: parent.width - 478
                    height: parent.height
                    fillColor: Colors.black
                    borderWidth: 1
                    borderColor: Colors.magenta
                    inset: 8

                    Column {
                        anchors.fill: parent
                        spacing: 7

                        SectionLabel {
                            text: "TAG OPERATIONS"
                        }

                        SectionFrame {
                            width: parent.width
                            height: 88
                            fillColor: Colors.dark
                            borderWidth: 1
                            borderColor:
                                root.selectedTag
                                ? root.tagKindColor(
                                    root.selectedTagRow()
                                  )
                                : Colors.orange
                            inset: 7

                            Column {
                                anchors.fill: parent
                                spacing: 4

                                GohuText {
                                    width: parent.width
                                    text: {
                                        const row =
                                            root.selectedTagRow();

                                        if (!row)
                                            return "TAG INTELLIGENCE // SELECT TAG";

                                        return (
                                            "TAG INTELLIGENCE // "
                                            + root.tagKindLabel(row)
                                            + (
                                                Boolean(row.atHead)
                                                ? " // POINTS AT HEAD"
                                                : ""
                                              )
                                        );
                                    }
                                    font.pixelSize: 10
                                    color:
                                        root.selectedTag
                                        ? root.tagKindColor(
                                            root.selectedTagRow()
                                          )
                                        : Colors.orange
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text: {
                                        const row =
                                            root.selectedTagRow();

                                        if (!row)
                                            return "NO TAG SELECTED";

                                        return (
                                            "TAG OBJECT "
                                            + String(
                                                row.shortSha || ""
                                              )
                                            + " // TARGET "
                                            + String(
                                                row.targetType || "object"
                                              ).toUpperCase()
                                            + " "
                                            + String(
                                                row.targetSha || ""
                                              ).slice(0, 10)
                                            + " // AGE "
                                            + root.ageLabel(row.epoch)
                                        );
                                    }
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text: {
                                        const row =
                                            root.selectedTagRow();

                                        if (!row)
                                            return "Lightweight tags point directly at an object; annotated and signed tags have their own tag object.";

                                        if (String(row.kind || "") === "signed")
                                            return "SIGNED tag object detected // remote comparison uses the peeled target.";

                                        if (String(row.kind || "") === "annotated")
                                            return "ANNOTATED tag object // remote comparison uses the peeled target.";

                                        return "LIGHTWEIGHT tag // tag ref points directly at its target object.";
                                    }
                                    font.pixelSize: 8
                                    color: Colors.white
                                    opacity: 0.60
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        EditorBox {
                            id: tagNameInput
                            width: parent.width
                            placeholder: "TAG NAME"
                            accent: Colors.orange
                            keyboardOwner: root.keyboardHost
                        }

                        EditorBox {
                            id: tagTargetInput
                            width: parent.width
                            placeholder: "TARGET // HEAD OR SHA"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                            text: "HEAD"
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: 136
                                height: 30
                                label:
                                    "MODE "
                                    + root.tagModeLabel()
                                accent:
                                    root.tagMode === "signed"
                                    ? Colors.magenta
                                    : root.tagMode === "annotated"
                                    ? Colors.orange
                                    : Colors.cyan
                                onTriggered: root.cycleTagMode()
                            }

                            EditorBox {
                                id: tagMessageInput
                                width: parent.width - 142
                                placeholder:
                                    root.tagMode === "lightweight"
                                    ? "MESSAGE // UNUSED FOR LIGHTWEIGHT"
                                    : "TAG MESSAGE"
                                accent: Colors.green
                                keyboardOwner: root.keyboardHost
                            }
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                "CREATE "
                                + root.tagModeLabel()
                                + " TAG"
                            accent: Colors.green
                            enabledAction:
                                root.repositoryService
                                && tagNameInput.text.trim().length > 0
                            onTriggered:
                                root.repositoryService.createTag(
                                    tagNameInput.text.trim(),
                                    tagTargetInput.text.trim(),
                                    root.tagMode,
                                    tagMessageInput.text
                                )
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            EditorBox {
                                id: tagRemoteInput
                                width: parent.width - 146
                                placeholder: "REMOTE FOR TAG PUSH"
                                accent: Colors.magenta
                                keyboardOwner: root.keyboardHost
                                text: "origin"

                                onTextChanged: {
                                    if (root.repositoryService)
                                        root.repositoryService
                                            .clearTagRemoteCheck();
                                    root.armedAction = "";
                                }
                            }

                            MiniButton {
                                width: 140
                                height: 30
                                label:
                                    root.selectedTagRemoteState()
                                    === "CHECKING"
                                    ? "CHECKING"
                                    : "CHECK REMOTE TAG"
                                accent: root.tagRemoteStateColor()
                                enabledAction:
                                    root.selectedTag
                                    && tagRemoteInput.text.trim()
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.checkRemoteTag(
                                        tagRemoteInput.text.trim(),
                                        root.selectedTag
                                    )
                            }
                        }

                        SectionFrame {
                            width: parent.width
                            height: 42
                            fillColor: Colors.dark
                            borderWidth: 1
                            borderColor:
                                root.tagRemoteStateColor()
                            inset: 7

                            GohuText {
                                anchors.fill: parent
                                verticalAlignment: Text.AlignVCenter
                                text: root.tagRemoteStatusText()
                                font.pixelSize: 9
                                color: root.tagRemoteStateColor()
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label: "PUSH SELECTED TAG"
                                accent: Colors.magenta
                                enabledAction:
                                    root.selectedTag
                                    && tagRemoteInput.text.trim()
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                    && root.selectedTagRemoteState()
                                       !== "MATCH"
                                    && root.selectedTagRemoteState()
                                       !== "DIVERGED"
                                onTriggered:
                                    root.repositoryService.pushTag(
                                        tagRemoteInput.text.trim(),
                                        root.selectedTag
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label: "PUSH ALL TAGS"
                                accent: Colors.cyan
                                enabledAction:
                                    tagRemoteInput.text.trim()
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.pushAllTags(
                                        tagRemoteInput.text.trim()
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label:
                                    root.armedAction === "delete-tag"
                                    ? "CONFIRM LOCAL"
                                    : "DELETE LOCAL TAG"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedTag
                                    && root.repositoryService
                                onTriggered:
                                    root.armOrRun(
                                        "delete-tag",
                                        function() {
                                            root.repositoryService.deleteTag(
                                                root.selectedTag,
                                                true
                                            );
                                            root.selectedTag = "";
                                        }
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 30
                                label:
                                    root.armedAction === "delete-remote-tag"
                                    ? "CONFIRM REMOTE"
                                    : "DELETE REMOTE TAG"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedTag
                                    && tagRemoteInput.text.trim()
                                    && root.repositoryService
                                    && !root.repositoryService.actionBusy
                                    && root.selectedTagRemoteState()
                                       !== "MISSING"
                                onTriggered:
                                    root.armOrRun(
                                        "delete-remote-tag",
                                        function() {
                                            root.repositoryService
                                                .deleteRemoteTag(
                                                    tagRemoteInput.text.trim(),
                                                    root.selectedTag,
                                                    true
                                                );
                                        }
                                    )
                            }
                        }
                    }
                }
            }

            // ===== WORKTREES + SUBMODULES ================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "worktrees"

                Rectangle {
                    width: 560
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        Row {
                            width: parent.width
                            height: 28

                            GohuText {
                                width: parent.width - 110
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "WORKTREES // "
                                    + String(
                                        root.branchWorkspaceService
                                        ? root.branchWorkspaceService.worktrees.length
                                        : 0
                                      )
                                font.pixelSize: 12
                                color: Colors.cyan
                            }

                            MiniButton {
                                width: 110
                                label: "PRUNE STALE"
                                accent: Colors.orange
                                enabledAction:
                                    root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.pruneWorktrees()
                            }
                        }

                        Flickable {
                            id: repositoryScroll4
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: worktreeColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: worktreeColumn
                                width: parent.width
                                spacing: 4

                                Repeater {
                                    model:
                                        root.branchWorkspaceService
                                        ? root.branchWorkspaceService.worktrees
                                        : []

                                    Rectangle {
                                        id: worktreeRow
                                        required property var modelData

                                        width: worktreeColumn.width
                                        height: 68
                                        color:
                                            worktreeMouse.containsMouse
                                            || root.selectedWorktreePath
                                               === String(modelData.path || "")
                                            ? Colors.black
                                            : "transparent"
                                        border.width:
                                            root.selectedWorktreePath
                                            === String(modelData.path || "")
                                            ? 1 : 0
                                        border.color:
                                            Number(modelData.dirtyCount || 0) > 0
                                            ? Colors.orange
                                            : Colors.green

                                        Column {
                                            anchors {
                                                left: parent.left
                                                right: lockButton.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 7
                                                rightMargin: 7
                                            }
                                            spacing: 3

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        worktreeRow.modelData.branch
                                                        || "DETACHED"
                                                    )
                                                    + " // "
                                                    + String(
                                                        worktreeRow.modelData.head
                                                        || ""
                                                      ).slice(0, 10)
                                                font.pixelSize: 11
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        worktreeRow.modelData.path
                                                        || ""
                                                    )
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    Number(
                                                        worktreeRow.modelData.dirtyCount
                                                        || 0
                                                    ) > 0
                                                    ? String(
                                                        worktreeRow.modelData.dirtyCount
                                                      ) + " CHANGES"
                                                    : "CLEAN"
                                                font.pixelSize: 9
                                                color:
                                                    Number(
                                                        worktreeRow.modelData.dirtyCount
                                                        || 0
                                                    ) > 0
                                                    ? Colors.orange
                                                    : Colors.green
                                            }
                                        }

                                        MiniButton {
                                            id: lockButton
                                            width: 88
                                            height: 28
                                            anchors {
                                                right: parent.right
                                                rightMargin: 6
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            label:
                                                Boolean(
                                                    worktreeRow.modelData.locked
                                                )
                                                ? "UNLOCK"
                                                : "LOCK"
                                            accent:
                                                Boolean(
                                                    worktreeRow.modelData.locked
                                                )
                                                ? Colors.orange
                                                : Colors.cyan
                                            enabledAction:
                                                root.repositoryService
                                                && !root.repositoryService.actionBusy
                                            onTriggered: {
                                                if (Boolean(
                                                        worktreeRow.modelData.locked
                                                    ))
                                                    root.repositoryService
                                                        .unlockWorktree(
                                                            worktreeRow.modelData.path
                                                        );
                                                else
                                                    root.repositoryService
                                                        .lockWorktree(
                                                            worktreeRow.modelData.path
                                                        );
                                            }
                                        }

                                        MouseArea {
                                            id: worktreeMouse
                                            anchors {
                                                left: parent.left
                                                right: lockButton.left
                                                top: parent.top
                                                bottom: parent.bottom
                                            }
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked:
                                                root.selectedWorktreePath =
                                                    String(
                                                        worktreeRow.modelData.path
                                                        || ""
                                                    )
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll4
                            }
}
                    }
                }

                Rectangle {
                    width: parent.width - 568
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 6

                        Row {
                            width: parent.width
                            height: 28

                            GohuText {
                                width: parent.width - 200
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    "SUBMODULES // "
                                    + String(
                                        root.repositoryService
                                        ? root.repositoryService.submodules.length
                                        : 0
                                      )
                                font.pixelSize: 12
                                color: Colors.magenta
                            }

                            MiniButton {
                                width: 92
                                label: "SYNC"
                                accent: Colors.cyan
                                enabledAction:
                                    root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.syncSubmodules()
                            }

                            MiniButton {
                                width: 104
                                label: "INIT + UPDATE"
                                accent: Colors.green
                                enabledAction:
                                    root.repositoryService
                                    && !root.repositoryService.actionBusy
                                onTriggered:
                                    root.repositoryService.updateSubmodules()
                            }
                        }

                        Flickable {
                            id: repositoryScroll5
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: submoduleColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: submoduleColumn
                                width: parent.width
                                spacing: 4

                                GohuText {
                                    visible:
                                        root.repositoryService
                                        && root.repositoryService.submodules.length === 0
                                    width: parent.width
                                    topPadding: 24
                                    text: "NO SUBMODULES"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 12
                                    color: Colors.cyan
                                }

                                Repeater {
                                    model:
                                        root.repositoryService
                                        ? root.repositoryService.submodules
                                        : []

                                    Rectangle {
                                        id: submoduleRow
                                        required property var modelData

                                        width: submoduleColumn.width
                                        height: 50
                                        color: Colors.dark
                                        border.width: 1
                                        border.color:
                                            String(modelData.state || "") === "-"
                                            ? Colors.orange
                                            : String(modelData.state || "") === "+"
                                            ? Colors.magenta
                                            : Colors.green

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
                                                        submoduleRow.modelData.path
                                                        || ""
                                                    )
                                                font.pixelSize: 11
                                                color: Colors.white
                                                elide: Text.ElideMiddle
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        submoduleRow.modelData.state
                                                        || " "
                                                    )
                                                    + " // "
                                                    + String(
                                                        submoduleRow.modelData.sha
                                                        || ""
                                                      ).slice(0, 10)
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                            }
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: repositoryScroll5
                            }
}
                    }
                }
            }

            // ===== CONFIG ================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "config"

                SectionFrame {
                    width: 560
                    height: parent.height
                    fillColor: Colors.dark
                    borderWidth: 1
                    borderColor: Colors.green
                    inset: 7

                    Column {
                        anchors.fill: parent
                        spacing: 5

                        Row {
                            width: parent.width
                            height: 24
                            spacing: 5

                            GohuText {
                                width: parent.width - 146
                                anchors.verticalCenter:
                                    parent.verticalCenter
                                text:
                                    "LOCAL CONFIG // "
                                    + String(
                                        root.configRowsForView().length
                                      )
                                    + " SHOWN / "
                                    + String(
                                        root.repositoryService
                                        ? root.repositoryService.configRows.length
                                        : 0
                                      )
                                font.pixelSize: 11
                                color: Colors.green
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: 140
                                anchors.verticalCenter:
                                    parent.verticalCenter
                                text:
                                    root.configCategoryLabel(
                                        root.configCategory
                                    )
                                horizontalAlignment:
                                    Text.AlignRight
                                font.pixelSize: 10
                                color:
                                    root.configCategoryColor(
                                        root.configCategory
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 4

                            Repeater {
                                model: [
                                    { key: "all", label: "ALL" },
                                    { key: "identity", label: "IDENTITY" },
                                    { key: "sync", label: "SYNC" },
                                    { key: "branch", label: "BRANCH" },
                                    { key: "history", label: "HISTORY" },
                                    { key: "repo", label: "REPO" },
                                    { key: "other", label: "OTHER" }
                                ]

                                MiniButton {
                                    required property var modelData
                                    width:
                                        (
                                            parent.width
                                            - parent.spacing * 6
                                        ) / 7
                                    height: 28
                                    label: modelData.label
                                    accent:
                                        root.configCategoryColor(
                                            modelData.key
                                        )
                                    selected:
                                        root.configCategory
                                        === modelData.key
                                    onTriggered: {
                                        root.configCategory =
                                            modelData.key;
                                        root.armedAction = "";
                                    }
                                }
                            }
                        }

                        EditorBox {
                            id: configFilterInput
                            width: parent.width
                            placeholder:
                                "FILTER CONFIG // KEY OR VALUE"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                            onTextChanged:
                                root.configFilterText = text
                        }

                        Flickable {
                            id: repositoryScroll6
                            width: parent.width
                            height:
                                Math.max(
                                    0,
                                    parent.height - 97
                                )
                            clip: true
                            contentWidth: width
                            contentHeight:
                                configColumn.implicitHeight
                            boundsBehavior:
                                Flickable.StopAtBounds

                            Column {
                                id: configColumn
                                width: parent.width
                                spacing: 2

                                GohuText {
                                    visible:
                                        root.configRowsForView().length
                                        === 0
                                    width: parent.width
                                    topPadding: 24
                                    text:
                                        root.configFilterText
                                        ? "NO CONFIG MATCHES"
                                        : "NO CONFIG IN THIS CATEGORY"
                                    horizontalAlignment:
                                        Text.AlignHCenter
                                    font.pixelSize: 11
                                    color: Colors.cyan
                                }

                                Repeater {
                                    model:
                                        root.configRowsForView()

                                    Rectangle {
                                        id: configRow
                                        required property var modelData

                                        width: configColumn.width
                                        height: 34
                                        color:
                                            configMouse.containsMouse
                                            || root.selectedConfigKey
                                               === String(
                                                   modelData.key
                                                   || ""
                                               )
                                            ? Colors.black
                                            : "transparent"
                                        border.width:
                                            root.selectedConfigKey
                                            === String(
                                                modelData.key
                                                || ""
                                            )
                                            ? 1
                                            : 0
                                        border.color:
                                            root.configCategoryColor(
                                                modelData.category
                                            )

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            width: 74
                                            text:
                                                root.configCategoryLabel(
                                                    configRow.modelData.category
                                                )
                                            font.pixelSize: 8
                                            color:
                                                root.configCategoryColor(
                                                    configRow.modelData.category
                                                )
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 80
                                            }
                                            width: 205
                                            text:
                                                String(
                                                    configRow.modelData.key
                                                    || ""
                                                )
                                            font.pixelSize: 10
                                            color: Colors.green
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                right: parent.right
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 292
                                                rightMargin: 8
                                            }
                                            text:
                                                String(
                                                    configRow.modelData.value
                                                    || ""
                                                )
                                            font.pixelSize: 10
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }

                                        MouseArea {
                                            id: configMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape:
                                                Qt.PointingHandCursor
                                            onClicked:
                                                root.selectConfigRow(
                                                    configRow.modelData
                                                )
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                flickable: repositoryScroll6
                                handleStyle: "star"
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 568
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text:
                                root.selectedConfigKey
                                ? "EDIT // "
                                  + root.selectedConfigKey
                                : "REPO-LOCAL CONFIG EDITOR"
                        }

                        Rectangle {
                            width: parent.width
                            height: 76
                            color: Colors.dark
                            border.width: 1
                            border.color:
                                root.configCategoryColor(
                                    root.configCategoryForKey(
                                        configKeyInput.text
                                    )
                                )

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 4

                                GohuText {
                                    width: parent.width
                                    text:
                                        "CATEGORY // "
                                        + root.configCategoryLabel(
                                            root.configCategoryForKey(
                                                configKeyInput.text
                                            )
                                        )
                                        + " // "
                                        + (
                                            root.configKeyExists(
                                                configKeyInput.text
                                            )
                                            ? "LOCAL OVERRIDE"
                                            : "NEW LOCAL KEY"
                                          )
                                    font.pixelSize: 10
                                    color:
                                        root.configCategoryColor(
                                            root.configCategoryForKey(
                                                configKeyInput.text
                                            )
                                        )
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        "SCOPE // .git/config ONLY"
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.configGuidance(
                                            configKeyInput.text
                                        )
                                    font.pixelSize: 8
                                    color: Colors.white
                                    opacity: 0.62
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        EditorBox {
                            id: configKeyInput
                            width: parent.width
                            placeholder:
                                "KEY // user.name / pull.ff / fetch.prune"
                            accent: Colors.green
                            keyboardOwner: root.keyboardHost
                            onTextChanged: {
                                if (text !== root.selectedConfigKey)
                                    root.selectedConfigKey = "";
                                root.armedAction = "";
                            }
                        }

                        EditorBox {
                            id: configValueInput
                            width: parent.width
                            placeholder: "VALUE"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                            onTextChanged:
                                root.armedAction = ""
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                root.configKeyExists(
                                    configKeyInput.text
                                )
                                ? "SET / REPLACE LOCAL CONFIG"
                                : "CREATE LOCAL CONFIG KEY"
                            accent: Colors.green
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                                && configKeyInput.text.trim().length > 0
                                && configValueInput.text.trim().length > 0
                            onTriggered: {
                                root.selectedConfigKey =
                                    configKeyInput.text.trim();
                                root.repositoryService.setConfig(
                                    configKeyInput.text.trim(),
                                    configValueInput.text
                                );
                            }
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                root.armedAction === "unset-config"
                                ? "CONFIRM UNSET LOCAL KEY"
                                : "UNSET LOCAL CONFIG KEY"
                            accent: Colors.red
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                                && root.configKeyExists(
                                    configKeyInput.text
                                )
                            onTriggered:
                                root.armOrRun(
                                    "unset-config",
                                    function() {
                                        root.repositoryService.unsetConfig(
                                            configKeyInput.text.trim()
                                        );
                                        root.selectedConfigKey = "";
                                    }
                                )
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "Global identity, credentials, and system configuration remain outside this surface. Selecting a row edits only its repository-local override."
                            font.pixelSize: 10
                            color: Colors.white
                            opacity: 0.50
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // ===== PROJECT FILES =========================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "files"

                Rectangle {
                    width: 560
                    height: parent.height
                    clip: true
                    color: Colors.dark
                    border.width: 1
                    border.color:
                        root.projectFileKind === "attributes"
                        ? Colors.cyan
                        : Colors.yellow

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 5

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 5

                            MiniButton {
                                width: 112
                                label: ".GITIGNORE"
                                accent: Colors.yellow
                                selected:
                                    root.projectFileKind === "ignore"
                                onTriggered: {
                                    root.projectFileKind = "ignore";
                                    root.clearProjectSelection(true);
                                }
                            }

                            MiniButton {
                                width: 132
                                label: ".GITATTRIBUTES"
                                accent: Colors.cyan
                                selected:
                                    root.projectFileKind === "attributes"
                                onTriggered: {
                                    root.projectFileKind = "attributes";
                                    root.clearProjectSelection(true);
                                }
                            }

                            GohuText {
                                width: parent.width - 254
                                anchors.verticalCenter:
                                    parent.verticalCenter
                                text:
                                    String(root.projectLinesForView().length)
                                    + " SHOWN / "
                                    + String(root.projectLines().length)
                                    + " LINES"
                                horizontalAlignment: Text.AlignRight
                                font.pixelSize: 9
                                color:
                                    root.projectFileKind === "attributes"
                                    ? Colors.cyan
                                    : Colors.yellow
                                elide: Text.ElideRight
                            }
                        }

                        EditorBox {
                            id: projectFilterInput
                            width: parent.width
                            placeholder:
                                "FILTER RULES // TEXT / TYPE / LINE"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                            onTextChanged:
                                root.projectLineFilterText = text
                        }

                        Item {
                            id: projectFilesViewport

                            width: parent.width
                            height: Math.max(0, parent.height - 68)
                            clip: false

                            Flickable {
                                id: repositoryScroll7

                                anchors.fill: parent
                                clip: true
                                contentWidth: width
                                contentHeight:
                                    projectLineColumn.implicitHeight
                                boundsBehavior:
                                    Flickable.StopAtBounds

                                Column {
                                    id: projectLineColumn
                                    width: parent.width
                                    spacing: 2

                                    GohuText {
                                        visible:
                                            root.projectLinesForView().length
                                            === 0
                                        width: parent.width
                                        topPadding: 24
                                        text:
                                            root.projectLineFilterText
                                            ? "NO RULES MATCH FILTER"
                                            : "FILE IS EMPTY"
                                        horizontalAlignment:
                                            Text.AlignHCenter
                                        font.pixelSize: 11
                                        color: Colors.cyan
                                    }

                                    Repeater {
                                        model: root.projectLinesForView()

                                        Rectangle {
                                            id: projectLineRow
                                            required property var modelData

                                            width: projectLineColumn.width
                                            height: 32
                                            color:
                                                projectLineMouse.containsMouse
                                                || (
                                                    root.selectedProjectLine
                                                    === Number(
                                                        modelData.line
                                                        || 0
                                                    )
                                                    && root.selectedProjectText
                                                       === String(
                                                           modelData.text
                                                           || ""
                                                       )
                                                   )
                                                ? Colors.black
                                                : "transparent"
                                            border.width:
                                                root.selectedProjectLine
                                                === Number(
                                                    modelData.line
                                                    || 0
                                                )
                                                && root.selectedProjectText
                                                   === String(
                                                       modelData.text
                                                       || ""
                                                   )
                                                ? 1
                                                : 0
                                            border.color:
                                                root.projectLineColor(
                                                    modelData.type
                                                )

                                            GohuText {
                                                anchors {
                                                    left: parent.left
                                                    verticalCenter:
                                                        parent.verticalCenter
                                                }
                                                width: 34
                                                text:
                                                    String(
                                                        projectLineRow.modelData.line
                                                        || 0
                                                    )
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                            }

                                            GohuText {
                                                anchors {
                                                    left: parent.left
                                                    verticalCenter:
                                                        parent.verticalCenter
                                                    leftMargin: 38
                                                }
                                                width: 68
                                                text:
                                                    root.projectLineTypeLabel(
                                                        projectLineRow.modelData.type
                                                    )
                                                font.pixelSize: 8
                                                color:
                                                    root.projectLineColor(
                                                        projectLineRow.modelData.type
                                                    )
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                anchors {
                                                    left: parent.left
                                                    right: parent.right
                                                    verticalCenter:
                                                        parent.verticalCenter
                                                    leftMargin: 112
                                                    rightMargin: 7
                                                }
                                                text:
                                                    String(
                                                        projectLineRow.modelData.text
                                                        || ""
                                                    )
                                                font.pixelSize: 10
                                                color:
                                                    projectLineRow.modelData.type
                                                    === "comment"
                                                    || projectLineRow.modelData.type
                                                       === "blank"
                                                    ? Colors.cyan
                                                    : Colors.white
                                                opacity:
                                                    projectLineRow.modelData.type
                                                    === "blank"
                                                    ? 0.38
                                                    : 1.0
                                                elide: Text.ElideRight
                                            }

                                            MouseArea {
                                                id: projectLineMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape:
                                                    Qt.PointingHandCursor
                                                onClicked:
                                                    root.selectProjectLine(
                                                        projectLineRow.modelData
                                                    )
                                            }
                                        }
                                    }
                                }

                                NeonScrollBar {
                                    flickable: repositoryScroll7
                                    handleStyle: "star"
                                    rightInset: 2
                                    trackTopExtension: 33
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 568
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color:
                        root.projectFileKind === "attributes"
                        ? Colors.cyan
                        : Colors.yellow

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text:
                                root.projectFileKind === "attributes"
                                ? ".GITATTRIBUTES // RULE EDITOR"
                                : ".GITIGNORE // RULE EDITOR"
                        }

                        Rectangle {
                            width: parent.width
                            height: 94
                            color: Colors.dark
                            border.width: 1
                            border.color:
                                root.projectLineColor(
                                    root.projectLineType(
                                        projectLineInput.text
                                    )
                                )

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 4

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.selectedProjectLine > 0
                                        ? (
                                            "SELECTED // LINE "
                                            + String(
                                                root.selectedProjectLine
                                              )
                                            + " // "
                                            + root.projectLineTypeLabel(
                                                root.projectLineType(
                                                    root.selectedProjectText
                                                )
                                              )
                                          )
                                        : (
                                            "NEW LINE // "
                                            + root.projectLineTypeLabel(
                                                root.projectLineType(
                                                    projectLineInput.text
                                                )
                                              )
                                          )
                                    font.pixelSize: 10
                                    color:
                                        root.projectLineColor(
                                            root.projectLineType(
                                                root.selectedProjectLine > 0
                                                ? root.selectedProjectText
                                                : projectLineInput.text
                                            )
                                        )
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        "RULE "
                                        + String(
                                            root.projectLineCount("rule")
                                          )
                                        + (
                                            root.projectFileKind === "ignore"
                                            ? " // NEGATE "
                                              + String(
                                                  root.projectLineCount(
                                                      "negate"
                                                  )
                                                )
                                            : " // MACRO "
                                              + String(
                                                  root.projectLineCount(
                                                      "macro"
                                                  )
                                                )
                                          )
                                        + " // COMMENT "
                                        + String(
                                            root.projectLineCount("comment")
                                          )
                                        + " // BLANK "
                                        + String(
                                            root.projectLineCount("blank")
                                          )
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.projectInputDuplicate()
                                        ? "ALREADY EXISTS // APPEND + REPLACE REFUSED"
                                        : root.projectInputChanged()
                                        ? "EDITED // REPLACE SELECTED LINE TO APPLY"
                                        : root.projectFileGuidance()
                                    font.pixelSize: 8
                                    color:
                                        root.projectInputDuplicate()
                                        ? Colors.red
                                        : root.projectInputChanged()
                                        ? Colors.orange
                                        : Colors.white
                                    opacity:
                                        root.projectInputDuplicate()
                                        || root.projectInputChanged()
                                        ? 1.0
                                        : 0.62
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        EditorBox {
                            id: projectLineInput
                            width: parent.width
                            placeholder:
                                root.projectFileKind === "attributes"
                                ? "RULE // *.png binary"
                                : "PATTERN // build/"
                            accent:
                                root.projectFileKind === "attributes"
                                ? Colors.cyan
                                : Colors.yellow
                            keyboardOwner: root.keyboardHost
                            onTextChanged:
                                root.armedAction = ""
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: 96
                                height: 30
                                label: "NEW LINE"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedProjectLine > 0
                                    || projectLineInput.text.length > 0
                                onTriggered:
                                    root.clearProjectSelection(true)
                            }

                            MiniButton {
                                width: parent.width - 102
                                height: 30
                                label:
                                    root.projectInputDuplicate()
                                    ? "ALREADY EXISTS"
                                    : "APPEND UNIQUE LINE"
                                accent: Colors.green
                                enabledAction:
                                    root.repositoryService
                                    && !root.repositoryService.actionBusy
                                    && root.selectedProjectLine <= 0
                                    && projectLineInput.text.trim().length > 0
                                    && !root.projectInputDuplicate()
                                onTriggered:
                                    root.repositoryService.appendProjectLine(
                                        root.projectFileKind,
                                        projectLineInput.text
                                    )
                            }
                        }

                        MiniButton {
                            width: parent.width
                            height: 30
                            label:
                                root.armedAction === "replace-project-line"
                                ? "CONFIRM REPLACE LINE "
                                  + String(root.selectedProjectLine)
                                : "REPLACE SELECTED LINE"
                            accent: Colors.orange
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                                && root.selectedProjectLine > 0
                                && root.projectInputChanged()
                                && projectLineInput.text.trim().length > 0
                                && !root.projectInputDuplicate()
                            onTriggered:
                                root.armOrRun(
                                    "replace-project-line",
                                    function() {
                                        root.repositoryService
                                            .replaceProjectLine(
                                                root.projectFileKind,
                                                root.selectedProjectLine,
                                                root.selectedProjectText,
                                                projectLineInput.text,
                                                true
                                            );
                                    }
                                )
                        }

                        MiniButton {
                            width: parent.width
                            height: 30
                            label:
                                root.armedAction === "remove-project-line"
                                ? "CONFIRM REMOVE LINE "
                                  + String(root.selectedProjectLine)
                                : "REMOVE SELECTED LINE"
                            accent: Colors.red
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                                && root.selectedProjectLine > 0
                            onTriggered:
                                root.armOrRun(
                                    "remove-project-line",
                                    function() {
                                        root.repositoryService
                                            .removeProjectLine(
                                                root.projectFileKind,
                                                root.selectedProjectLine,
                                                root.selectedProjectText,
                                                true
                                            );
                                    }
                                )
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "REPLACE and REMOVE verify the exact selected text before writing. If the file changed or the line moved unexpectedly, the operation refuses instead of modifying another rule."
                            font.pixelSize: 9
                            color: Colors.white
                            opacity: 0.52
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // ===== HOOKS =================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "hooks"

                Rectangle {
                    width: 520
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.blue

                    Flickable {
                        id: repositoryScroll8
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: hookColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: hookColumn
                            width: parent.width
                            spacing: 4

                            GohuText {
                                visible:
                                    root.repositoryService
                                    && root.repositoryService.hooks.length === 0
                                width: parent.width
                                topPadding: 24
                                text: "NO ACTIVE HOOK FILES"
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 12
                                color: Colors.cyan
                            }

                            Repeater {
                                model:
                                    root.repositoryService
                                    ? root.repositoryService.hooks
                                    : []

                                Rectangle {
                                    id: hookRow
                                    required property var modelData

                                    width: hookColumn.width
                                    height: 42
                                    color: Colors.black
                                    border.width: 1
                                    border.color:
                                        Boolean(modelData.enabled)
                                        ? Colors.green
                                        : Colors.orange

                                    GohuText {
                                        anchors {
                                            left: parent.left
                                            verticalCenter:
                                                parent.verticalCenter
                                            leftMargin: 7
                                        }
                                        width: parent.width - 112
                                        text:
                                            String(hookRow.modelData.name || "")
                                        font.pixelSize: 11
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }

                                    MiniButton {
                                        width: 98
                                        height: 28
                                        anchors {
                                            right: parent.right
                                            rightMargin: 6
                                            verticalCenter:
                                                parent.verticalCenter
                                        }
                                        label:
                                            Boolean(hookRow.modelData.enabled)
                                            ? "DISABLE"
                                            : "ENABLE"
                                        accent:
                                            Boolean(hookRow.modelData.enabled)
                                            ? Colors.orange
                                            : Colors.green
                                        enabledAction:
                                            root.repositoryService
                                            && !root.repositoryService.actionBusy
                                        onTriggered:
                                            root.repositoryService
                                                .setHookEnabled(
                                                    hookRow.modelData.name,
                                                    !Boolean(
                                                        hookRow.modelData.enabled
                                                    )
                                                )
                                    }
                                }
                            }
                        }
                    
                        NeonScrollBar {
                            flickable: repositoryScroll8
                        }
}
                }

                Rectangle {
                    width: parent.width - 528
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 8

                        SectionLabel {
                            text: "HOOK EXECUTION STATE"
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "This surface only enables/disables existing "
                                + "repository hook files by executable bit. "
                                + "It does not generate hook scripts or rewrite hook contents."
                            font.pixelSize: 11
                            color: Colors.white
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // ===== HEALTH ================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "health"

                Rectangle {
                    width: 520
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: root.healthStateColor()

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text: "REPOSITORY HEALTH"
                        }

                        Rectangle {
                            width: parent.width
                            height: 110
                            color: Colors.black
                            border.width: 1
                            border.color:
                                root.healthStateColor()

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 5

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.repositoryService
                                        ? (
                                            root.repositoryService.healthState
                                            + " // "
                                            + root.repositoryService.healthSummary
                                          )
                                        : "NO REPOSITORY SERVICE"
                                    font.pixelSize: 11
                                    color:
                                        root.healthStateColor()
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.repositoryService
                                        ? root.repositoryService
                                              .healthRecommendation
                                        : ""
                                    font.pixelSize: 9
                                    color: Colors.white
                                    opacity: 0.68
                                    wrapMode: Text.WordWrap
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.repositoryService
                                        ? (
                                            "FSCK // "
                                            + String(
                                                root.repositoryService
                                                    .fsckDanglingCount
                                              )
                                            + " DANGLING // "
                                            + String(
                                                root.repositoryService
                                                    .fsckUnreachableCount
                                              )
                                            + " UNREACHABLE // "
                                            + String(
                                                root.repositoryService
                                                    .fsckWarningCount
                                              )
                                            + " WARNING // "
                                            + String(
                                                root.repositoryService
                                                    .fsckErrorCount
                                              )
                                            + " ERROR"
                                          )
                                        : ""
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 126
                            color: Colors.black
                            border.width: 1
                            border.color:
                                root.objectConditionColor()

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 5

                                GohuText {
                                    width: parent.width
                                    text:
                                        "OBJECT DATABASE // "
                                        + root.objectConditionText()
                                    font.pixelSize: 10
                                    color:
                                        root.objectConditionColor()
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.repositoryService
                                        ? (
                                            "LOOSE // "
                                            + String(
                                                root.repositoryService
                                                    .looseObjectCount
                                              )
                                            + " OBJECTS // "
                                            + root.repositoryService
                                                  .looseObjectSize
                                          )
                                        : ""
                                    font.pixelSize: 9
                                    color: Colors.white
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.repositoryService
                                        ? (
                                            "PACKED // "
                                            + String(
                                                root.repositoryService
                                                    .packedObjectCount
                                              )
                                            + " OBJECTS // "
                                            + String(
                                                root.repositoryService
                                                    .packCount
                                              )
                                            + " PACKS // "
                                            + root.repositoryService
                                                  .packedObjectSize
                                          )
                                        : ""
                                    font.pixelSize: 9
                                    color: Colors.white
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.repositoryService
                                        ? (
                                            "PRUNE-PACKABLE // "
                                            + String(
                                                root.repositoryService
                                                    .prunePackableCount
                                              )
                                            + " // GARBAGE // "
                                            + String(
                                                root.repositoryService
                                                    .garbageObjectCount
                                              )
                                            + " // "
                                            + root.repositoryService
                                                  .garbageObjectSize
                                          )
                                        : ""
                                    font.pixelSize: 9
                                    color:
                                        root.objectConditionColor()
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.repositoryService
                                        && root.repositoryService
                                               .garbageObjectCount > 0
                                        ? "Garbage entries are not the same as dangling commits; inspect evidence before cleanup."
                                        : root.repositoryService
                                          && root.repositoryService
                                                 .prunePackableCount > 0
                                        ? "Git reports loose objects already duplicated in packs; cleanup may reclaim them."
                                        : "Object storage reports no obvious cleanup anomaly."
                                    font.pixelSize: 8
                                    color: Colors.white
                                    opacity: 0.58
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                root.repositoryService
                                && root.repositoryService.actionBusy
                                && root.repositoryService.actionName
                                   === "FSCK"
                                ? "FSCK // VERIFYING"
                                : "FSCK // VERIFY OBJECT GRAPH"
                            accent: Colors.red
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                            onTriggered: {
                                root.armedAction = "";
                                root.repositoryService.runFsck();
                            }
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                root.healthCleanupBlocked()
                                ? "GC --AUTO // BLOCKED BY FSCK FAIL"
                                : root.armedAction === "gc-recovery"
                                ? "CONFIRM GC // RECOVERY OBJECTS"
                                : root.repositoryService
                                  && root.repositoryService.healthState
                                     === "RECOVERY"
                                ? "GC --AUTO // RECOVERY OBJECTS"
                                : "GC --AUTO"
                            accent:
                                root.healthCleanupBlocked()
                                ? Colors.red
                                : Colors.orange
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                                && !root.healthCleanupBlocked()
                            onTriggered:
                                root.runHealthCleanup("gc")
                        }

                        MiniButton {
                            width: parent.width
                            label:
                                root.healthCleanupBlocked()
                                ? "MAINTENANCE // BLOCKED BY FSCK FAIL"
                                : root.armedAction
                                  === "maintenance-recovery"
                                ? "CONFIRM MAINTENANCE // RECOVERY OBJECTS"
                                : root.repositoryService
                                  && root.repositoryService.healthState
                                     === "RECOVERY"
                                ? "MAINTENANCE // RECOVERY OBJECTS"
                                : "MAINTENANCE RUN --AUTO"
                            accent:
                                root.healthCleanupBlocked()
                                ? Colors.red
                                : Colors.cyan
                            enabledAction:
                                root.repositoryService
                                && !root.repositoryService.actionBusy
                                && !root.healthCleanupBlocked()
                            onTriggered:
                                root.runHealthCleanup("maintenance")
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 528
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: root.healthStateColor()

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        Row {
                            width: parent.width
                            height: 24
                            spacing: 6

                            SectionLabel {
                                width: parent.width - 176
                                text: "RAW DIAGNOSTIC EVIDENCE"
                            }

                            GohuText {
                                width: 170
                                anchors.verticalCenter:
                                    parent.verticalCenter
                                text:
                                    root.repositoryService
                                    ? root.repositoryService.healthState
                                    : "UNAVAILABLE"
                                horizontalAlignment:
                                    Text.AlignRight
                                font.pixelSize: 10
                                color:
                                    root.healthStateColor()
                            }
                        }

                        GohuText {
                            width: parent.width
                            text:
                                root.repositoryService
                                ? (
                                    "Latest health action output is preserved below. Interpretation never replaces the raw Git evidence."
                                  )
                                : ""
                            font.pixelSize: 9
                            color: Colors.white
                            opacity: 0.52
                            wrapMode: Text.WordWrap
                        }

                        Flickable {
                            id: repositoryScroll10
                            width: parent.width
                            height:
                                Math.max(
                                    0,
                                    parent.height - 62
                                )
                            clip: true
                            contentWidth: width
                            contentHeight:
                                healthText.implicitHeight
                            boundsBehavior:
                                Flickable.StopAtBounds

                            GohuText {
                                id: healthText
                                width: parent.width
                                text:
                                    root.repositoryService
                                    ? root.repositoryService.healthOutput
                                    : "NO REPOSITORY SERVICE"
                                font.pixelSize: 10
                                color:
                                    root.repositoryService
                                    && root.repositoryService
                                           .healthState === "FAIL"
                                    ? Colors.red
                                    : Colors.white
                                wrapMode: Text.WrapAnywhere
                            }

                            NeonScrollBar {
                                flickable: repositoryScroll10
                                handleStyle: "star"
                            }
                        }
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
                root.repositoryService
                && root.repositoryService.lastError
                ? Colors.red
                : Colors.cyan

            GohuText {
                anchors {
                    fill: parent
                    leftMargin: 8
                    rightMargin: 8
                }
                verticalAlignment: Text.AlignVCenter
                text:
                    root.armedAction
                    ? "ARMED // "
                      + root.armedAction.toUpperCase()
                      + " // repeat destructive control to confirm"
                    : root.repositoryService
                    ? (
                        root.repositoryService.lastError
                        ? "REFUSED // " + root.repositoryService.lastError
                        : root.repositoryService.actionBusy
                        ? root.repositoryService.actionName + " // RUNNING"
                        : root.repositoryService.actionStatus
                      )
                    : "NO REPOSITORY SERVICE"
                font.pixelSize: 10
                color:
                    root.armedAction
                    ? Colors.orange
                    : root.repositoryService
                      && root.repositoryService.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    Connections {
        target: root.repositoryService
        enabled: root.repositoryService !== null
        ignoreUnknownSignals: true

        function onRefreshed() {
            root.reconcileProjectSelection();
        }

        function onActionFinished(action, success, detail) {
            if (!success)
                return;

            const name = String(action || "");

            if (name === "APPEND-FILE-LINE") {
                root.clearProjectSelection(true);
                return;
            }

            if (name === "REPLACE-FILE-LINE") {
                root.selectedProjectText =
                    String(projectLineInput.text || "");
                return;
            }

            if (name === "REMOVE-FILE-LINE")
                root.clearProjectSelection(true);
        }
    }

}
