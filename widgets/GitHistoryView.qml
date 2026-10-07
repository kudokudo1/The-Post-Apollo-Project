import QtQuick
import QtQuick.Effects
import qs.components

Item {
    id: root

    property var gitService: null
    property var historyService: null
    property var interactiveRebaseService: null
    property var keyboardHost: null

    property string subMode: "log"
    property string searchQuery: ""
    property int scopeIndex: 0
    property string pendingScopeRef: ""
    property string inspectorMode: "detail"
    property string resetMode: "mixed"
    property string selectedQuerySha: ""
    property string selectedReflogSha: ""
    property string selectedReflogSelector: ""
    property string selectedReflogSubject: ""
    property bool selectedReflogReachable: false
    property bool selectedReflogIsHead: false
    property string selectedCommitRefs: ""
    property string armedAction: ""
    property int ancestryParentIndex: 0
    property int ancestryChildIndex: 0

    signal changesRequested(string path)
    signal branchesRequested(string branch, string sha)

    readonly property var displayedRows: root.filteredRows()

    function pad2(value) {
        const text = String(Number(value || 0));
        return text.length < 2 ? "0" + text : text;
    }

    function dateLabel(epoch) {
        const value = Number(epoch || 0);
        if (value <= 0)
            return "";

        const d = new Date(value * 1000);
        return d.getFullYear()
            + "-" + root.pad2(d.getMonth() + 1)
            + "-" + root.pad2(d.getDate())
            + "  " + root.pad2(d.getHours())
            + ":" + root.pad2(d.getMinutes());
    }

    function scopeEntries() {
        const out = [{
            label: "ALL",
            ref: "ALL"
        }];

        if (!root.historyService)
            return out;

        const branches = root.historyService.branchRefs || [];
        const tags = root.historyService.tagRefs || [];

        for (let i = 0; i < branches.length; ++i) {
            out.push({
                label: "BRANCH " + String(branches[i]),
                ref: "refs/heads/" + String(branches[i])
            });
        }

        for (let i = 0; i < tags.length; ++i) {
            out.push({
                label: "TAG " + String(tags[i]),
                ref: "refs/tags/" + String(tags[i])
            });
        }

        return out;
    }

    function scopeLabelForRef(refValue) {
        const ref = String(refValue || "ALL");

        if (!ref || ref === "ALL")
            return "ALL";

        if (ref.indexOf("refs/heads/") === 0)
            return "BRANCH " + ref.slice("refs/heads/".length);

        if (ref.indexOf("refs/tags/") === 0)
            return "TAG " + ref.slice("refs/tags/".length);

        return ref;
    }

    function scopeIndexForRef(refValue) {
        const ref = String(refValue || "ALL");
        const entries = root.scopeEntries();

        for (let i = 0; i < entries.length; ++i) {
            if (String(entries[i].ref || "") === ref)
                return i;
        }

        return -1;
    }

    function syncScopeIndex(refValue) {
        const ref = String(refValue || "ALL");
        const index = root.scopeIndexForRef(ref);

        if (index >= 0) {
            root.scopeIndex = index;
            root.pendingScopeRef = "";
            return true;
        }

        if (ref === "ALL") {
            root.scopeIndex = 0;
            root.pendingScopeRef = "";
            return true;
        }

        root.pendingScopeRef = ref;
        return false;
    }

    function currentScope() {
        const entries = root.scopeEntries();
        if (entries.length === 0)
            return { label: "ALL", ref: "ALL" };

        const activeRef =
            String(root.pendingScopeRef || "")
            || (
                root.historyService
                ? String(root.historyService.selectedRef || "")
                : ""
               );

        if (activeRef) {
            const activeIndex = root.scopeIndexForRef(activeRef);

            if (activeIndex >= 0)
                return entries[activeIndex];

            return {
                label: root.scopeLabelForRef(activeRef),
                ref: activeRef
            };
        }

        const index = Math.max(
            0,
            Math.min(entries.length - 1, root.scopeIndex)
        );

        return entries[index];
    }

    function cycleScope(delta) {
        const entries = root.scopeEntries();
        if (entries.length <= 0)
            return;

        const activeRef =
            String(root.pendingScopeRef || "")
            || (
                root.historyService
                ? String(root.historyService.selectedRef || "")
                : ""
               );
        const activeIndex = root.scopeIndexForRef(activeRef);
        const startIndex =
            activeIndex >= 0
            ? activeIndex
            : Math.max(
                0,
                Math.min(entries.length - 1, root.scopeIndex)
              );

        root.scopeIndex =
            (startIndex + Number(delta || 0) + entries.length)
            % entries.length;
        root.pendingScopeRef = "";

        if (root.historyService)
            root.historyService.refresh(
                entries[root.scopeIndex].ref,
                root.historyService.selectedMode
            );
    }

    function cycleHistoryMode() {
        if (!root.historyService)
            return;

        const current = String(
            root.historyService.selectedMode || "all"
        );

        if (current === "all")
            root.historyService.selectedMode = "first-parent";
        else if (current === "first-parent")
            root.historyService.selectedMode = "merges";
        else if (current === "merges")
            root.historyService.selectedMode = "no-merges";
        else
            root.historyService.selectedMode = "all";

        root.historyService.refresh(
            root.currentScope().ref,
            root.historyService.selectedMode
        );
    }

    function historyModeLabel() {
        if (!root.historyService)
            return "ALL";

        const mode = String(
            root.historyService.selectedMode || "all"
        );

        if (mode === "first-parent")
            return "FIRST PARENT";
        if (mode === "merges")
            return "MERGES";
        if (mode === "no-merges")
            return "NO MERGES";
        return "ALL";
    }

    function filteredRows() {
        if (!root.historyService)
            return [];

        const source = root.historyService.rows || [];
        const needle = String(root.searchQuery || "")
            .trim()
            .toLowerCase();

        if (!needle)
            return source;

        const out = [];

        for (let i = 0; i < source.length; ++i) {
            const row = source[i] || {};
            const haystack = (
                String(row.sha || "")
                + " "
                + String(row.author || "")
                + " "
                + String(row.subject || "")
                + " "
                + String(row.refsText || "")
            ).toLowerCase();

            if (haystack.indexOf(needle) >= 0)
                out.push(row);
        }

        return out;
    }

    function selectedBranchContext() {
        const raw = String(root.selectedCommitRefs || "");
        if (!raw)
            return "";

        const refs = raw.split(" • ");

        for (let i = 0; i < refs.length; ++i) {
            const candidate = String(refs[i] || "").trim();

            if (!candidate
                    || candidate.indexOf("TAG ") === 0
                    || candidate.indexOf("origin/") === 0)
                continue;

            return candidate;
        }

        return "";
    }

    function openBranchScope(branchName) {
        const branch = String(branchName || "").trim();

        if (!branch || !root.historyService)
            return;

        root.subMode = "log";
        root.searchQuery = "";
        searchInput.text = "";
        root.selectedCommitRefs = "";

        const target = "refs/heads/" + branch;
        root.pendingScopeRef = target;
        root.syncScopeIndex(target);

        root.historyService.refresh(
            target,
            root.historyService.selectedMode
        );
    }

    function openPathQuery(path) {
        const target = String(path || "").trim();

        if (!target || !root.historyService)
            return;

        root.subMode = "query";
        queryPathInput.text = target;
        queryAuthorInput.text = "";
        queryMessageInput.text = "";
        querySinceInput.text = "";
        queryUntilInput.text = "";
        queryRangeInput.text = "";
        root.selectedQuerySha = "";

        root.historyService.runQuery(
            target,
            "",
            "",
            "",
            "",
            ""
        );
    }

    function queryHasFilters() {
        return Boolean(
            String(queryPathInput.text || "").trim()
            || String(queryAuthorInput.text || "").trim()
            || String(queryMessageInput.text || "").trim()
            || String(querySinceInput.text || "").trim()
            || String(queryUntilInput.text || "").trim()
            || String(queryRangeInput.text || "").trim()
        );
    }

    function queryFilterSummary() {
        const parts = [];

        const path = String(queryPathInput.text || "").trim();
        const author = String(queryAuthorInput.text || "").trim();
        const message = String(queryMessageInput.text || "").trim();
        const since = String(querySinceInput.text || "").trim();
        const until = String(queryUntilInput.text || "").trim();
        const range = String(queryRangeInput.text || "").trim();

        if (path)
            parts.push("PATH " + path);
        if (author)
            parts.push(
                "AUTHOR "
                + (author === "@me" ? "ME" : author)
            );
        if (message)
            parts.push("MESSAGE " + message);
        if (since)
            parts.push("SINCE " + since);
        if (until)
            parts.push("UNTIL " + until);
        if (range)
            parts.push("RANGE " + range);

        return parts.length > 0
            ? parts.join(" // ")
            : "NO FILTERS // LOG ALREADY SHOWS GENERAL HISTORY";
    }

    function queryInputsMatchExecuted() {
        if (!root.historyService)
            return true;

        return (
            String(queryPathInput.text || "").trim()
            === String(root.historyService.queryPath || "")
            && String(queryAuthorInput.text || "").trim()
               === String(root.historyService.queryAuthor || "")
            && String(queryMessageInput.text || "").trim()
               === String(root.historyService.queryMessage || "")
            && String(querySinceInput.text || "").trim()
               === String(root.historyService.querySince || "")
            && String(queryUntilInput.text || "").trim()
               === String(root.historyService.queryUntil || "")
            && String(queryRangeInput.text || "").trim()
               === String(root.historyService.queryRange || "")
        );
    }

    function recoveryDefaultName() {
        if (!root.selectedReflogSha)
            return "";

        return "recovery/" + root.selectedReflogSha.slice(0, 8);
    }

    function reflogStateLabel(row) {
        const item = row || {};

        if (Boolean(item.isHead))
            return "CURRENT HEAD";
        if (Boolean(item.reachable))
            return "REACHABLE";
        return "RECOVERY CANDIDATE";
    }

    function selectedReflogStateLabel() {
        if (!root.selectedReflogSha)
            return "NO SELECTION";

        if (root.selectedReflogIsHead)
            return "CURRENT HEAD";
        if (root.selectedReflogReachable)
            return "REACHABLE";
        return "RECOVERY CANDIDATE";
    }

    function selectReflogEntry(row) {
        const item = row || {};

        root.selectedReflogSha = String(item.sha || "");
        root.selectedReflogSelector =
            String(item.selector || "");
        root.selectedReflogSubject =
            String(item.subject || "");
        root.selectedReflogReachable =
            Boolean(item.reachable);
        root.selectedReflogIsHead =
            Boolean(item.isHead);
        root.selectedCommitRefs = "";

        if (root.historyService && root.selectedReflogSha)
            root.historyService.showCommit(
                root.selectedReflogSha
            );
    }

    function reconcileSelectedReflog() {
        if (!root.historyService || !root.selectedReflogSha)
            return;

        const rows = root.historyService.reflogRows || [];

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};

            if (String(row.sha || "") !== root.selectedReflogSha)
                continue;

            root.selectedReflogSelector =
                String(row.selector || "");
            root.selectedReflogSubject =
                String(row.subject || "");
            root.selectedReflogReachable =
                Boolean(row.reachable);
            root.selectedReflogIsHead =
                Boolean(row.isHead);
            return;
        }

        root.selectedReflogSha = "";
        root.selectedReflogSelector = "";
        root.selectedReflogSubject = "";
        root.selectedReflogReachable = false;
        root.selectedReflogIsHead = false;
    }

    function openReflogResultInLog() {
        if (!root.historyService || !root.selectedReflogSha)
            return;

        const sha = root.selectedReflogSha;

        root.pendingScopeRef = "ALL";
        root.syncScopeIndex("ALL");
        root.searchQuery = sha.slice(0, 8);
        searchInput.text = root.searchQuery;
        root.subMode = "log";

        root.historyService.refresh(
            "ALL",
            root.historyService.selectedMode
        );

        root.historyService.showCommit(sha);
    }

    function compareReflogWithHead() {
        if (!root.historyService
                || !root.selectedReflogSha
                || !root.historyService.reflogHeadSha
                || root.selectedReflogSha
                   === root.historyService.reflogHeadSha)
            return;

        root.historyService.compareA =
            root.historyService.reflogHeadSha;
        root.historyService.compareB =
            root.selectedReflogSha;
        root.subMode = "compare";
        root.historyService.compareCommits(
            root.historyService.compareA,
            root.historyService.compareB
        );
    }

    function openQueryResultInLog() {
        if (!root.historyService || !root.selectedQuerySha)
            return;

        const sha = root.selectedQuerySha;

        root.pendingScopeRef = "ALL";
        root.syncScopeIndex("ALL");
        root.searchQuery = sha.slice(0, 8);
        searchInput.text = root.searchQuery;
        root.subMode = "log";

        root.historyService.refresh(
            "ALL",
            root.historyService.selectedMode
        );

        root.historyService.showCommit(sha);
    }

    function applyQueryPreset(kind) {
        const preset = String(kind || "");

        if (preset === "today") {
            querySinceInput.text = "midnight";
            queryUntilInput.text = "";
        } else if (preset === "7d") {
            querySinceInput.text = "7 days ago";
            queryUntilInput.text = "";
        } else if (preset === "30d") {
            querySinceInput.text = "30 days ago";
            queryUntilInput.text = "";
        } else if (preset === "me") {
            queryAuthorInput.text = "@me";
        }
    }

    function navigationContext() {
        return {
            subMode: root.subMode,
            searchQuery: root.searchQuery,
            scopeRef:
                root.historyService
                ? String(root.historyService.selectedRef || "ALL")
                : root.currentScope().ref,
            historyMode:
                root.historyService
                ? String(root.historyService.selectedMode || "all")
                : "all",
            selectedSha:
                root.historyService
                ? String(root.historyService.selectedSha || "")
                : "",
            selectedFile:
                root.historyService
                ? String(root.historyService.selectedFile || "")
                : "",
            selectedQuerySha: root.selectedQuerySha,
            selectedReflogSha: root.selectedReflogSha,
            queryPath:
                root.historyService
                ? String(root.historyService.queryPath || "")
                : "",
            queryAuthor:
                root.historyService
                ? String(root.historyService.queryAuthor || "")
                : "",
            queryMessage:
                root.historyService
                ? String(root.historyService.queryMessage || "")
                : "",
            querySince:
                root.historyService
                ? String(root.historyService.querySince || "")
                : "",
            queryUntil:
                root.historyService
                ? String(root.historyService.queryUntil || "")
                : "",
            queryRange:
                root.historyService
                ? String(root.historyService.queryRange || "")
                : ""
        };
    }

    function restoreNavigationContext(context) {
        const ctx = context || {};

        root.armedAction = "";
        root.subMode = String(ctx.subMode || "log");
        root.searchQuery = String(ctx.searchQuery || "");
        searchInput.text = root.searchQuery;
        root.selectedQuerySha = String(ctx.selectedQuerySha || "");
        root.selectedReflogSha = String(ctx.selectedReflogSha || "");

        if (!root.historyService)
            return;

        if (root.subMode === "query") {
            queryPathInput.text = String(ctx.queryPath || "");
            queryAuthorInput.text = String(ctx.queryAuthor || "");
            queryMessageInput.text = String(ctx.queryMessage || "");
            querySinceInput.text = String(ctx.querySince || "");
            queryUntilInput.text = String(ctx.queryUntil || "");
            queryRangeInput.text = String(ctx.queryRange || "");

            root.historyService.runQuery(
                queryPathInput.text,
                queryAuthorInput.text,
                querySinceInput.text,
                queryUntilInput.text,
                queryRangeInput.text,
                queryMessageInput.text
            );
        } else if (root.subMode === "reflog") {
            root.historyService.loadReflog();
        } else {
            const scopeRef = String(ctx.scopeRef || "ALL");
            root.pendingScopeRef = scopeRef;
            root.syncScopeIndex(scopeRef);
            root.historyService.refresh(
                scopeRef,
                String(
                    ctx.historyMode
                    || root.historyService.selectedMode
                    || "all"
                )
            );
        }

        const selectedSha = String(ctx.selectedSha || "");
        if (selectedSha)
            root.historyService.showCommit(selectedSha);
    }

    function ancestryChoice(kind) {
        if (!root.historyService)
            return "";

        const source =
            kind === "parent"
            ? root.historyService.selectedParents
            : root.historyService.selectedChildren;
        const count = source ? source.length : 0;

        if (count <= 0)
            return "";

        const rawIndex =
            kind === "parent"
            ? root.ancestryParentIndex
            : root.ancestryChildIndex;
        const index = Math.max(
            0,
            Math.min(count - 1, Number(rawIndex || 0))
        );

        return String(source[index] || "");
    }

    function cycleAncestry(kind, delta) {
        if (!root.historyService)
            return;

        const source =
            kind === "parent"
            ? root.historyService.selectedParents
            : root.historyService.selectedChildren;
        const count = source ? source.length : 0;

        if (count <= 1)
            return;

        if (kind === "parent") {
            root.ancestryParentIndex =
                (
                    root.ancestryParentIndex
                    + Number(delta || 0)
                    + count
                ) % count;
        } else {
            root.ancestryChildIndex =
                (
                    root.ancestryChildIndex
                    + Number(delta || 0)
                    + count
                ) % count;
        }
    }

    function openAncestry(kind) {
        const sha = root.ancestryChoice(kind);

        if (!sha)
            return;

        root.selectCommit(sha, "");
    }

    function selectCommit(sha, refsText) {
        if (!root.historyService)
            return;

        root.selectedCommitRefs =
            String(refsText || "");
        root.inspectorMode = "detail";
        root.historyService.showCommit(sha);
        root.armedAction = "";
    }

    function setCompare(slot) {
        if (!root.historyService
                || !root.historyService.selectedSha)
            return;

        if (slot === "A")
            root.historyService.compareA =
                root.historyService.selectedSha;
        else
            root.historyService.compareB =
                root.historyService.selectedSha;
    }

    function runCompare() {
        if (!root.historyService)
            return;

        root.historyService.compareCommits(
            root.historyService.compareA,
            root.historyService.compareB
        );
    }

    function cycleResetMode() {
        if (root.resetMode === "soft")
            root.resetMode = "mixed";
        else if (root.resetMode === "mixed")
            root.resetMode = "hard";
        else
            root.resetMode = "soft";

        root.armedAction = "";
    }

    function armOrRun(key, callback) {
        if (root.armedAction !== key) {
            root.armedAction = key;
            return;
        }

        root.armedAction = "";
        callback();
    }

    component SectionLabel: GohuText {
        font.pixelSize: 14
        color: Colors.magenta
    }

    component MiniButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool selected: false
        signal triggered()

        height: 28
        color:
            mouse.pressed
            ? accent
            : selected
            ? Colors.dark
            : mouse.containsMouse
            ? Colors.dark
            : Colors.black
        border.width: selected ? 2 : 1
        border.color: accent
        opacity: enabledAction ? 1.0 : 0.26

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 10
            color:
                mouse.pressed
                ? Colors.black
                : selected
                ? Colors.white
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

    component EditorBox: Rectangle {
        id: editorBox

        property alias text: editor.text
        property string placeholder: ""
        property color accent: Colors.cyan
        property var keyboardOwner: null
        property int editorFontSize: 11
        property int placeholderFontSize: 10

        height: 30
        clip: true
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
            font.pixelSize: editorBox.editorFontSize
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
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: 8
                rightMargin: 8
            }
            visible: editor.text.length === 0
            text: editorBox.placeholder
            font.pixelSize: editorBox.placeholderFontSize
            color: Colors.white
            opacity: 0.30
            elide: Text.ElideRight
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Rectangle {
            width: parent.width
            height: 66
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta

            Row {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 7

                Column {
                    width: 210
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    SectionLabel {
                        text: "COMMIT HISTORY"
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.historyService
                            ? String(root.historyService.rows.length)
                              + " LOADED"
                            : "NO HISTORY"
                        font.pixelSize: 10
                        color: Colors.cyan
                    }
                }

                MiniButton {
                    width: 34
                    anchors.verticalCenter: parent.verticalCenter
                    label: "<"
                    accent: Colors.cyan
                    onTriggered: root.cycleScope(-1)
                }

                Rectangle {
                    width: 220
                    height: 30
                    anchors.verticalCenter: parent.verticalCenter
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    GohuText {
                        anchors {
                            fill: parent
                            leftMargin: 7
                            rightMargin: 7
                        }
                        verticalAlignment: Text.AlignVCenter
                        text: root.currentScope().label
                        font.pixelSize: 10
                        color: Colors.white
                        elide: Text.ElideMiddle
                    }
                }

                MiniButton {
                    width: 34
                    anchors.verticalCenter: parent.verticalCenter
                    label: ">"
                    accent: Colors.cyan
                    onTriggered: root.cycleScope(1)
                }

                MiniButton {
                    width: 118
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        "MODE "
                        + root.historyModeLabel()
                    accent: Colors.magenta
                    onTriggered: root.cycleHistoryMode()
                }

                EditorBox {
                    id: searchInput
                    width:
                        parent.width
                        - 210
                        - 34
                        - 220
                        - 34
                        - 118
                        - 110
                        - 56
                    anchors.verticalCenter: parent.verticalCenter
                    placeholder: "SEARCH SHA / AUTHOR / SUBJECT"
                    accent: Colors.orange
                    keyboardOwner: root.keyboardHost
                    editorFontSize: 10
                    placeholderFontSize: 9
                    onTextChanged:
                        root.searchQuery = text
                }

                MiniButton {
                    width: 110
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.historyService
                        && root.historyService.refreshing
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.green
                    enabledAction:
                        root.historyService
                        && !root.historyService.refreshing
                        && !root.historyService.actionBusy
                    onTriggered:
                        root.historyService.refresh(
                            root.currentScope().ref,
                            root.historyService.selectedMode
                        )
                }
            }
        }

        Row {
            width: parent.width
            height: 34
            spacing: 7

            Repeater {
                model: [
                    {
                        key: "log",
                        label: "LOG",
                        color: Colors.cyan
                    },
                    {
                        key: "query",
                        label: "QUERY",
                        color: Colors.green
                    },
                    {
                        key: "reflog",
                        label: "REFLOG",
                        color: Colors.magenta
                    },
                    {
                        key: "compare",
                        label: "COMPARE",
                        color: Colors.orange
                    },
                    {
                        key: "operate",
                        label: "OPERATE",
                        color: Colors.red
                    },
                    {
                        key: "rebase",
                        label: "REBASE",
                        color: Colors.magenta
                    }
                ]

                MiniButton {
                    required property var modelData
                    width:
                        (
                            parent.width
                            - parent.spacing * 5
                        ) / 6
                    height: 34
                    label: modelData.label
                    accent: modelData.color
                    selected: root.subMode === modelData.key
                    onTriggered: {
                        root.subMode = modelData.key;
                        root.armedAction = "";

                        if (
                            modelData.key === "reflog"
                            && root.historyService
                        )
                            root.historyService.loadReflog();
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - 158

            // ===== LOG ===================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "log"

                Rectangle {
                    width: 520
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    Flickable {
                        id: historyScroll1
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: historyColumn.height
                        boundsBehavior: Flickable.StopAtBounds

                        Item {
                            id: historyColumn

                            width: parent.width
                            height:
                                Math.max(
                                    1,
                                    root.displayedRows.length * 50
                                )

                            Canvas {
                                id: topologyCanvas

                                anchors.fill: parent
                                z: 0
                                antialiasing: true

                                property var rowsSnapshot:
                                    root.displayedRows

                                onRowsSnapshotChanged: requestPaint()
                                onWidthChanged: requestPaint()
                                onHeightChanged: requestPaint()

                                onPaint: {
                                    const ctx = getContext("2d");
                                    ctx.reset();
                                    ctx.clearRect(
                                        0,
                                        0,
                                        width,
                                        height
                                    );

                                    const rows =
                                        root.displayedRows || [];
                                    const bySha = {};

                                    for (
                                        let i = 0;
                                        i < rows.length;
                                        ++i
                                    ) {
                                        bySha[
                                            String(
                                                rows[i].sha || ""
                                            )
                                        ] = i;
                                    }

                                    // Continuous visual history spine.
                                    // Real parent/merge edges are drawn over this.
                                    ctx.strokeStyle =
                                        Colors.cyan.toString();
                                    ctx.lineWidth = 1;
                                    ctx.globalAlpha = 0.20;
                                    ctx.beginPath();
                                    ctx.moveTo(12, 0);
                                    ctx.lineTo(12, height);
                                    ctx.stroke();

                                    ctx.globalAlpha = 0.54;

                                    for (
                                        let i = 0;
                                        i < rows.length;
                                        ++i
                                    ) {
                                        const row = rows[i] || {};
                                        const parents =
                                            row.parents || [];
                                        const x1 =
                                            12
                                            + Math.min(
                                                6,
                                                Number(
                                                    row.lane || 0
                                                )
                                              ) * 7;
                                        const y1 =
                                            i * 50 + 25;

                                        for (
                                            let p = 0;
                                            p < parents.length;
                                            ++p
                                        ) {
                                            const parentSha =
                                                String(
                                                    parents[p] || ""
                                                );
                                            const parentIndex =
                                                bySha[parentSha];

                                            if (
                                                parentIndex === undefined
                                                || parentIndex <= i
                                            )
                                                continue;

                                            const parentRow =
                                                rows[parentIndex]
                                                || {};
                                            const x2 =
                                                12
                                                + Math.min(
                                                    6,
                                                    Number(
                                                        parentRow.lane
                                                        || 0
                                                    )
                                                  ) * 7;
                                            const y2 =
                                                parentIndex * 50
                                                + 25;

                                            ctx.beginPath();
                                            ctx.moveTo(x1, y1);

                                            if (x1 === x2) {
                                                ctx.lineTo(
                                                    x2,
                                                    y2
                                                );
                                            } else {
                                                const bendY =
                                                    y1
                                                    + (
                                                        y2 - y1
                                                      ) * 0.55;

                                                ctx.lineTo(
                                                    x1,
                                                    bendY
                                                );
                                                ctx.lineTo(
                                                    x2,
                                                    bendY
                                                );
                                                ctx.lineTo(
                                                    x2,
                                                    y2
                                                );
                                            }

                                            ctx.stroke();
                                        }
                                    }

                                    ctx.globalAlpha = 1.0;
                                }
                            }

                            Repeater {
                                model: root.displayedRows

                                Rectangle {
                                    id: commitRow

                                    required property int index
                                    required property var modelData

                                    x: 0
                                    y: index * 50
                                    z: 1
                                    width: historyColumn.width
                                    height: 50

                                    color:
                                        commitMouse.containsMouse
                                        || (
                                            root.historyService
                                            && root.historyService.selectedSha
                                               === String(
                                                   modelData.sha || ""
                                               )
                                        )
                                        ? Colors.black
                                        : "transparent"

                                    Item {
                                        id: graphLane

                                        width: 64
                                        height: parent.height
                                        anchors.left: parent.left

                                        Rectangle {
                                            width:
                                                commitRow.modelData.isHead
                                                ? 9 : 7
                                            height: width
                                            radius: width / 2
                                            anchors.verticalCenter:
                                                parent.verticalCenter
                                            x:
                                                8
                                                + Math.min(
                                                    6,
                                                    Number(
                                                        commitRow
                                                            .modelData
                                                            .lane
                                                        || 0
                                                    )
                                                  ) * 7
                                            color:
                                                commitRow.modelData.isHead
                                                ? Colors.magenta
                                                : Colors.black
                                            border.width: 1
                                            border.color:
                                                commitRow.modelData.isHead
                                                ? Colors.magenta
                                                : Colors.cyan
                                        }
                                    }

                                    Column {
                                        anchors {
                                            left: graphLane.right
                                            right: parent.right
                                            verticalCenter:
                                                parent.verticalCenter
                                            leftMargin: 4
                                            rightMargin: 6
                                        }
                                        spacing: 2

                                        Row {
                                            width: parent.width
                                            height: 15
                                            spacing: 7

                                            GohuText {
                                                width: 66
                                                text:
                                                    String(
                                                        commitRow
                                                            .modelData
                                                            .shortSha
                                                        || ""
                                                    )
                                                font.pixelSize: 10
                                                color:
                                                    commitRow
                                                        .modelData
                                                        .isHead
                                                    ? Colors.magenta
                                                    : Colors.orange
                                            }

                                            GohuText {
                                                width:
                                                    parent.width - 73
                                                text:
                                                    String(
                                                        commitRow
                                                            .modelData
                                                            .refsText
                                                        || ""
                                                    )
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                                elide:
                                                    Text.ElideRight
                                            }
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    commitRow
                                                        .modelData
                                                        .subject
                                                    || ""
                                                )
                                            font.pixelSize: 11
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }

                                        GohuText {
                                            width: parent.width
                                            text:
                                                String(
                                                    commitRow
                                                        .modelData
                                                        .author
                                                    || ""
                                                )
                                                + " // "
                                                + root.dateLabel(
                                                    commitRow
                                                        .modelData
                                                        .epoch
                                                  )
                                            font.pixelSize: 9
                                            color: Colors.white
                                            opacity: 0.50
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: commitMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape:
                                            Qt.PointingHandCursor

                                        onClicked:
                                            root.selectCommit(
                                                commitRow
                                                    .modelData
                                                    .sha,
                                                commitRow
                                                    .modelData
                                                    .refsText
                                            )
                                    }
                                }
                            }
                        }

                        NeonScrollBar {
                            flickable: historyScroll1
                            starHandle: true
                        }
}
                }

                Rectangle {
                    width: parent.width - 528
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

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
                                width: 62
                                label: "DETAIL"
                                accent: Colors.cyan
                                selected: root.inspectorMode === "detail"
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                onTriggered:
                                    root.inspectorMode = "detail"
                            }

                            MiniButton {
                                width: 58
                                label: "FILE"
                                accent: Colors.orange
                                selected: root.inspectorMode === "file"
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedFile
                                onTriggered:
                                    root.inspectorMode = "file"
                            }

                            MiniButton {
                                width: 54
                                label: "SET A"
                                accent: Colors.cyan
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                onTriggered: root.setCompare("A")
                            }

                            MiniButton {
                                width: 54
                                label: "SET B"
                                accent: Colors.orange
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                onTriggered: root.setCompare("B")
                            }

                            MiniButton {
                                width: 82
                                label: "BRANCHES"
                                accent: Colors.green
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                onTriggered:
                                    root.branchesRequested(
                                        root.selectedBranchContext(),
                                        root.historyService.selectedSha
                                    )
                            }

                            MiniButton {
                                width: 82
                                label: "CHANGES"
                                accent: Colors.orange
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedFile
                                onTriggered:
                                    root.changesRequested(
                                        root.historyService.selectedFile
                                    )
                            }

                            MiniButton {
                                width: 78
                                label: "COPY SHA"
                                accent: Colors.magenta
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                    && !root.historyService.actionBusy
                                onTriggered:
                                    root.historyService.copySha(
                                        root.historyService.selectedSha
                                    )
                            }
                        }

                        Flickable {
                            id: historyScroll2
                            width: parent.width
                            height: parent.height - 154
                            clip: true
                            contentWidth: width
                            contentHeight: inspectorText.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            GohuText {
                                id: inspectorText
                                width: parent.width
                                text:
                                    !root.historyService
                                    ? "NO HISTORY SERVICE"
                                    : root.inspectorMode === "file"
                                    ? root.historyService.fileDiffText
                                    : root.historyService.detailText
                                font.pixelSize: 11
                                color:
                                    root.historyService
                                    && root.historyService.lastError
                                    ? Colors.red
                                    : Colors.white
                                wrapMode: Text.WrapAnywhere
                            }
                        
                            NeonScrollBar {
                                flickable: historyScroll2
                            }
}

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.26
                        }

                        GohuText {
                            width: parent.width
                            height: 16
                            text:
                                "FILES // "
                                + String(
                                    root.historyService
                                    ? root.historyService.changedFiles.length
                                    : 0
                                  )
                            font.pixelSize: 10
                            color: Colors.cyan
                        }

                        Flickable {
                            id: historyScroll3
                            width: parent.width
                            height: 92
                            clip: true
                            contentWidth: width
                            contentHeight: fileColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: fileColumn
                                width: parent.width
                                spacing: 2

                                Repeater {
                                    model:
                                        root.historyService
                                        ? root.historyService.changedFiles
                                        : []

                                    Rectangle {
                                        id: changedFileRow
                                        required property var modelData

                                        width: fileColumn.width
                                        height: 27
                                        color:
                                            changedFileMouse.containsMouse
                                            ? Colors.dark
                                            : "transparent"

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                verticalCenter:
                                                    parent.verticalCenter
                                            }
                                            width: 36
                                            text:
                                                String(
                                                    changedFileRow.modelData.status
                                                    || ""
                                                )
                                            font.pixelSize: 10
                                            color: Colors.orange
                                        }

                                        GohuText {
                                            anchors {
                                                left: parent.left
                                                right: parent.right
                                                verticalCenter:
                                                    parent.verticalCenter
                                                leftMargin: 40
                                            }
                                            text:
                                                String(
                                                    changedFileRow.modelData.path
                                                    || ""
                                                )
                                            font.pixelSize: 10
                                            color: Colors.white
                                            elide: Text.ElideMiddle
                                        }

                                        MouseArea {
                                            id: changedFileMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                root.inspectorMode = "file";
                                                root.historyService.showFileDiff(
                                                    root.historyService.selectedSha,
                                                    changedFileRow.modelData.path
                                                );
                                            }
                                        }
                                    }
                                }
                            }
                        
                            NeonScrollBar {
                                flickable: historyScroll3
                            }
}
                    }
                }
            }

            // ===== QUERY =================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "query"

                Rectangle {
                    width: 330
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.green

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 6

                        SectionLabel {
                            text: "HISTORY // QUERY"
                            color: Colors.green
                        }

                        EditorBox {
                            id: queryPathInput
                            width: parent.width
                            placeholder: "PATH // widgets/GitW.qml"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                            editorFontSize: 10
                            placeholderFontSize: 9
                        }

                        MiniButton {
                            width: parent.width
                            label: "USE SELECTED FILE"
                            accent: Colors.cyan
                            enabledAction:
                                root.historyService
                                && root.historyService.selectedFile
                            onTriggered:
                                queryPathInput.text =
                                    root.historyService.selectedFile
                        }

                        EditorBox {
                            id: queryAuthorInput
                            width: parent.width
                            placeholder: "AUTHOR // NAME OR EMAIL"
                            accent: Colors.magenta
                            keyboardOwner: root.keyboardHost
                            editorFontSize: 10
                            placeholderFontSize: 9
                        }

                        EditorBox {
                            id: queryMessageInput
                            width: parent.width
                            placeholder: "MESSAGE // WORDS IN COMMIT MESSAGE"
                            accent: Colors.green
                            keyboardOwner: root.keyboardHost
                            editorFontSize: 10
                            placeholderFontSize: 9
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            EditorBox {
                                id: querySinceInput
                                width: (parent.width - 6) / 2
                                placeholder: "SINCE"
                                accent: Colors.orange
                                keyboardOwner: root.keyboardHost
                                editorFontSize: 10
                                placeholderFontSize: 9
                            }

                            EditorBox {
                                id: queryUntilInput
                                width: (parent.width - 6) / 2
                                placeholder: "UNTIL"
                                accent: Colors.orange
                                keyboardOwner: root.keyboardHost
                                editorFontSize: 10
                                placeholderFontSize: 9
                            }
                        }

                        EditorBox {
                            id: queryRangeInput
                            width: parent.width
                            placeholder: "RANGE // A..B OR SHA..SHA"
                            accent: Colors.yellow
                            keyboardOwner: root.keyboardHost
                            editorFontSize: 10
                            placeholderFontSize: 9
                        }

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 5

                            MiniButton {
                                width: (parent.width - 15) / 4
                                label: "TODAY"
                                accent: Colors.orange
                                selected:
                                    querySinceInput.text === "midnight"
                                onTriggered:
                                    root.applyQueryPreset("today")
                            }

                            MiniButton {
                                width: (parent.width - 15) / 4
                                label: "7 DAYS"
                                accent: Colors.orange
                                selected:
                                    querySinceInput.text === "7 days ago"
                                onTriggered:
                                    root.applyQueryPreset("7d")
                            }

                            MiniButton {
                                width: (parent.width - 15) / 4
                                label: "30 DAYS"
                                accent: Colors.orange
                                selected:
                                    querySinceInput.text === "30 days ago"
                                onTriggered:
                                    root.applyQueryPreset("30d")
                            }

                            MiniButton {
                                width: (parent.width - 15) / 4
                                label: "ME"
                                accent: Colors.magenta
                                selected:
                                    queryAuthorInput.text === "@me"
                                onTriggered:
                                    root.applyQueryPreset("me")
                            }
                        }

                        Row {
                            width: parent.width
                            height: 32
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 32
                                label:
                                    root.historyService
                                    && root.historyService.queryBusy
                                    ? "QUERYING"
                                    : "RUN QUERY"
                                accent: Colors.green
                                enabledAction:
                                    root.historyService
                                    && !root.historyService.queryBusy
                                    && root.queryHasFilters()
                                onTriggered: {
                                    root.selectedQuerySha = "";
                                    root.historyService.runQuery(
                                        queryPathInput.text,
                                        queryAuthorInput.text,
                                        querySinceInput.text,
                                        queryUntilInput.text,
                                        queryRangeInput.text,
                                        queryMessageInput.text
                                    );
                                }
                            }

                            MiniButton {
                                width: (parent.width - 6) / 2
                                height: 32
                                label: "CLEAR"
                                accent: Colors.cyan
                                enabledAction:
                                    root.historyService
                                onTriggered: {
                                    queryPathInput.text = "";
                                    queryAuthorInput.text = "";
                                    queryMessageInput.text = "";
                                    querySinceInput.text = "";
                                    queryUntilInput.text = "";
                                    queryRangeInput.text = "";
                                    root.selectedQuerySha = "";
                                    root.historyService.clearQuery();
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 52
                            color: Colors.black
                            border.width: 1
                            border.color:
                                root.queryHasFilters()
                                ? Colors.green
                                : Colors.cyan

                            GohuText {
                                anchors {
                                    fill: parent
                                    margins: 6
                                }
                                text: root.queryFilterSummary()
                                font.pixelSize: 9
                                color:
                                    root.queryHasFilters()
                                    ? Colors.green
                                    : Colors.cyan
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                            }
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "DATES ACCEPT GIT SYNTAX // "
                                + "2026-10-01, 2 weeks ago, yesterday"
                            font.pixelSize: 9
                            color: Colors.white
                            opacity: 0.48
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 338
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.green

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

                            GohuText {
                                width: parent.width - 322
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    !root.historyService
                                    ? "NO HISTORY SERVICE"
                                    : root.historyService.queryBusy
                                    ? root.historyService.queryStatus
                                    : !root.queryInputsMatchExecuted()
                                    ? "CHANGED // RUN TO APPLY"
                                    : root.historyService.queryStatus
                                font.pixelSize: 10
                                color:
                                    !root.queryInputsMatchExecuted()
                                    ? Colors.orange
                                    : Colors.green
                                elide: Text.ElideRight
                            }

                            MiniButton {
                                width: 108
                                label: "OPEN IN LOG"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedQuerySha.length > 0
                                onTriggered:
                                    root.openQueryResultInLog()
                            }

                            MiniButton {
                                width: 96
                                label: "SET A"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedQuerySha.length > 0
                                    && root.historyService
                                onTriggered:
                                    root.historyService.compareA =
                                        root.selectedQuerySha
                            }

                            MiniButton {
                                width: 96
                                label: "SET B"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedQuerySha.length > 0
                                    && root.historyService
                                onTriggered:
                                    root.historyService.compareB =
                                        root.selectedQuerySha
                            }
                        }

                        Flickable {
                            id: historyScroll6

                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: queryResultColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: queryResultColumn

                                width: parent.width
                                spacing: 3

                                GohuText {
                                    visible:
                                        root.historyService
                                        && !root.historyService.queryBusy
                                        && root.historyService.queryRows.length === 0
                                    width: parent.width
                                    topPadding: 24
                                    text: "NO QUERY RESULTS"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 11
                                    color: Colors.cyan
                                }

                                Repeater {
                                    model:
                                        root.historyService
                                        ? root.historyService.queryRows
                                        : []

                                    Rectangle {
                                        id: queryRow

                                        required property var modelData

                                        width: queryResultColumn.width
                                        height: 58
                                        color:
                                            queryMouse.containsMouse
                                            || root.selectedQuerySha
                                               === String(modelData.sha || "")
                                            ? Colors.dark
                                            : "transparent"
                                        border.width:
                                            root.selectedQuerySha
                                            === String(modelData.sha || "")
                                            ? 1 : 0
                                        border.color: Colors.green

                                        Column {
                                            anchors {
                                                fill: parent
                                                margins: 6
                                            }
                                            spacing: 2

                                            Row {
                                                width: parent.width
                                                height: 15
                                                spacing: 7

                                                GohuText {
                                                    width: 68
                                                    text:
                                                        String(
                                                            queryRow.modelData.shortSha
                                                            || ""
                                                        )
                                                    font.pixelSize: 10
                                                    color: Colors.orange
                                                }

                                                GohuText {
                                                    width: parent.width - 75
                                                    text:
                                                        String(
                                                            queryRow.modelData.refsText
                                                            || ""
                                                        )
                                                    font.pixelSize: 9
                                                    color: Colors.cyan
                                                    elide: Text.ElideRight
                                                }
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        queryRow.modelData.subject
                                                        || ""
                                                    )
                                                font.pixelSize: 11
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: parent.width
                                                text:
                                                    String(
                                                        queryRow.modelData.author
                                                        || ""
                                                    )
                                                    + " // "
                                                    + root.dateLabel(
                                                        queryRow.modelData.epoch
                                                      )
                                                font.pixelSize: 9
                                                color: Colors.white
                                                opacity: 0.50
                                                elide: Text.ElideRight
                                            }
                                        }

                                        MouseArea {
                                            id: queryMouse

                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor

                                            onClicked: {
                                                root.selectedQuerySha =
                                                    String(
                                                        queryRow.modelData.sha
                                                        || ""
                                                    );
                                                root.selectCommit(
                                                    root.selectedQuerySha,
                                                    queryRow.modelData.refsText
                                                );
                                            }
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                flickable: historyScroll6
                            }
                        }
                    }
                }
            }

            // ===== REFLOG ================================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "reflog"

                Rectangle {
                    width: 470
                    height: parent.height
                    clip: true
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

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
                                width: parent.width - 112
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.historyService
                                    ? root.historyService.reflogStatus
                                    : "NO HISTORY SERVICE"
                                font.pixelSize: 10
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }

                            MiniButton {
                                width: 108
                                label:
                                    root.historyService
                                    && root.historyService.reflogBusy
                                    ? "READING"
                                    : "REFRESH"
                                accent: Colors.cyan
                                enabledAction:
                                    root.historyService
                                    && !root.historyService.reflogBusy
                                onTriggered:
                                    root.historyService.loadReflog()
                            }
                        }

                        Item {
                            id: reflogViewport

                            width: parent.width
                            height: Math.max(0, parent.height - 33)
                            clip: false

                            Flickable {
                                id: historyScroll7

                                anchors.fill: parent
                                clip: true
                                contentWidth: width
                                contentHeight: reflogColumn.implicitHeight
                                boundsBehavior: Flickable.StopAtBounds

                                Column {
                                    id: reflogColumn

                                    width: parent.width
                                    spacing: 3

                                    Repeater {
                                        model:
                                            root.historyService
                                            ? root.historyService.reflogRows
                                            : []

                                        Rectangle {
                                            id: reflogRow

                                            required property var modelData

                                            width: reflogColumn.width
                                            height: 62
                                            color:
                                                reflogMouse.containsMouse
                                                || root.selectedReflogSha
                                                   === String(modelData.sha || "")
                                                ? Colors.black
                                                : "transparent"
                                            border.width:
                                                root.selectedReflogSha
                                                === String(modelData.sha || "")
                                                ? 1 : 0
                                            border.color: Colors.magenta

                                            Column {
                                                anchors {
                                                    fill: parent
                                                    margins: 6
                                                }
                                                spacing: 2

                                                GohuText {
                                                    width: parent.width
                                                    text:
                                                        root.reflogStateLabel(
                                                            reflogRow.modelData
                                                        )
                                                        + " // "
                                                        + String(
                                                            reflogRow.modelData.shortSha
                                                            || ""
                                                        )
                                                    font.pixelSize: 10
                                                    color:
                                                        Boolean(
                                                            reflogRow.modelData.isHead
                                                        )
                                                        ? Colors.green
                                                        : Boolean(
                                                            reflogRow.modelData.reachable
                                                          )
                                                        ? Colors.cyan
                                                        : Colors.magenta
                                                    elide: Text.ElideRight
                                                }

                                                GohuText {
                                                    width: parent.width
                                                    text:
                                                        String(
                                                            reflogRow.modelData.selector
                                                            || ""
                                                        )
                                                    font.pixelSize: 9
                                                    color: Colors.orange
                                                    opacity: 0.78
                                                    elide: Text.ElideRight
                                                }

                                                GohuText {
                                                    width: parent.width
                                                    text:
                                                        String(
                                                            reflogRow.modelData.subject
                                                            || ""
                                                        )
                                                    font.pixelSize: 10
                                                    color: Colors.white
                                                    elide: Text.ElideRight
                                                }
                                            }

                                            MouseArea {
                                                id: reflogMouse

                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor

                                                onClicked:
                                                    root.selectReflogEntry(
                                                        reflogRow.modelData
                                                    )
                                            }
                                        }
                                    }
                                }

                                NeonScrollBar {
                                    flickable: historyScroll7
                                    starHandle: true
                                    rightInset: 2
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 478
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
                            text: "RECOVERY // SAFE BRANCH"
                        }

                        GohuText {
                            width: parent.width
                            text:
                                root.selectedReflogSha
                                ? root.selectedReflogSha
                                : "SELECT A REFLOG ENTRY"
                            font.pixelSize: 10
                            color: Colors.orange
                            elide: Text.ElideMiddle
                        }

                        Rectangle {
                            width: parent.width
                            height: 68
                            color: Colors.dark
                            border.width: 1
                            border.color:
                                root.selectedReflogIsHead
                                ? Colors.green
                                : root.selectedReflogReachable
                                ? Colors.cyan
                                : root.selectedReflogSha
                                ? Colors.magenta
                                : Colors.cyan

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 4

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.selectedReflogStateLabel()
                                        + (
                                            root.selectedReflogSelector
                                            ? " // "
                                              + root.selectedReflogSelector
                                            : ""
                                          )
                                    font.pixelSize: 10
                                    color:
                                        root.selectedReflogIsHead
                                        ? Colors.green
                                        : root.selectedReflogReachable
                                        ? Colors.cyan
                                        : root.selectedReflogSha
                                        ? Colors.magenta
                                        : Colors.cyan
                                    elide: Text.ElideMiddle
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.selectedReflogIsHead
                                        ? "This entry is the current HEAD."
                                        : root.selectedReflogReachable
                                        ? "This commit is already reachable from a current ref. A new branch is optional."
                                        : root.selectedReflogSha
                                        ? "This commit is not reachable from current refs. Creating a branch preserves it without moving HEAD."
                                        : "Select an entry to inspect its recovery state."
                                    font.pixelSize: 9
                                    color: Colors.white
                                    opacity: 0.66
                                    wrapMode: Text.WordWrap
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.historyService
                                        ? (
                                            "LIVE // "
                                            + (
                                                root.historyService.reflogBranch
                                                || "DETACHED"
                                              )
                                            + " @ "
                                            + String(
                                                root.historyService.reflogHeadSha
                                                || ""
                                              ).slice(0, 8)
                                          )
                                        : ""
                                    font.pixelSize: 8
                                    color: Colors.orange
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            EditorBox {
                                id: recoveryBranchInput

                                width: parent.width - 96
                                placeholder: "RECOVERY BRANCH NAME"
                                accent: Colors.green
                                keyboardOwner: root.keyboardHost
                                editorFontSize: 10
                                placeholderFontSize: 9
                            }

                            MiniButton {
                                width: 90
                                height: 30
                                label: "AUTO NAME"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedReflogSha.length > 0
                                onTriggered:
                                    recoveryBranchInput.text =
                                        root.recoveryDefaultName()
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 12) / 3
                                height: 30
                                label:
                                    root.selectedReflogIsHead
                                    ? "BRANCH HEAD"
                                    : root.selectedReflogReachable
                                    ? "SAVE BRANCH"
                                    : "RECOVER BRANCH"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedReflogSha.length > 0
                                    && recoveryBranchInput.text.trim().length > 0
                                    && root.historyService
                                    && !root.historyService.actionBusy
                                onTriggered:
                                    root.historyService.createBranch(
                                        recoveryBranchInput.text.trim(),
                                        root.selectedReflogSha
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 12) / 3
                                height: 30
                                label: "COPY SHA"
                                accent: Colors.magenta
                                enabledAction:
                                    root.selectedReflogSha.length > 0
                                    && root.historyService
                                onTriggered:
                                    root.historyService.copySha(
                                        root.selectedReflogSha
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 12) / 3
                                height: 30
                                label: "OPEN LOG"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedReflogSha.length > 0
                                onTriggered:
                                    root.openReflogResultInLog()
                            }
                        }

                        MiniButton {
                            width: parent.width
                            height: 30
                            label: "COMPARE WITH LIVE HEAD"
                            accent: Colors.orange
                            enabledAction:
                                root.selectedReflogSha.length > 0
                                && root.historyService
                                && root.historyService.reflogHeadSha
                                && root.selectedReflogSha
                                   !== root.historyService.reflogHeadSha
                                && !root.historyService.diffBusy
                            onTriggered:
                                root.compareReflogWithHead()
                        }

                        Flickable {
                            id: historyScroll8

                            width: parent.width
                            height: Math.max(0, parent.height - y)
                            clip: true
                            contentWidth: width
                            contentHeight: reflogDetail.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds

                            GohuText {
                                id: reflogDetail

                                width: parent.width
                                text:
                                    root.historyService
                                    ? root.historyService.detailText
                                    : "NO HISTORY SERVICE"
                                font.pixelSize: 10
                                color: Colors.white
                                wrapMode: Text.WrapAnywhere
                            }

                            NeonScrollBar {
                                flickable: historyScroll8
                            }
                        }
                    }
                }
            }

            // ===== COMPARE ===============================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "compare"

                Rectangle {
                    width: 360
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 8

                        SectionLabel {
                            text: "COMPARE COMMITS"
                        }

                        Rectangle {
                            width: parent.width
                            height: 76
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 4

                                GohuText {
                                    text: "A // BASE"
                                    font.pixelSize: 10
                                    color: Colors.cyan
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.historyService
                                        && root.historyService.compareA
                                        ? root.historyService.compareA
                                        : "NOT SET"
                                    font.pixelSize: 11
                                    color: Colors.white
                                    elide: Text.ElideMiddle
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 76
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.orange

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 4

                                GohuText {
                                    text: "B // TARGET"
                                    font.pixelSize: 10
                                    color: Colors.orange
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        root.historyService
                                        && root.historyService.compareB
                                        ? root.historyService.compareB
                                        : "NOT SET"
                                    font.pixelSize: 11
                                    color: Colors.white
                                    elide: Text.ElideMiddle
                                }
                            }
                        }

                        MiniButton {
                            width: parent.width
                            height: 34
                            label: "COMPARE A → B"
                            accent: Colors.green
                            enabledAction:
                                root.historyService
                                && root.historyService.compareA
                                && root.historyService.compareB
                                && !root.historyService.diffBusy
                            onTriggered: root.runCompare()
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "Select commits in LOG, press SET A / SET B, then compare. "
                                + "A and B remain pinned while you browse."
                            font.pixelSize: 10
                            color: Colors.white
                            opacity: 0.56
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 368
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    Flickable {
                        id: historyScroll4
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: compareText.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        GohuText {
                            id: compareText
                            width: parent.width
                            text:
                                root.historyService
                                ? root.historyService.compareText
                                : "NO HISTORY SERVICE"
                            font.pixelSize: 11
                            color: Colors.white
                            wrapMode: Text.WrapAnywhere
                        }
                    
                        NeonScrollBar {
                            flickable: historyScroll4
                        }
}
                }
            }

            // ===== REBASE ================================================
            GitInteractiveRebaseView {
                anchors.fill: parent
                visible: root.subMode === "rebase"

                rebaseService: root.interactiveRebaseService
                keyboardHost: root.keyboardHost
            }

            // ===== OPERATE ===============================================
            Row {
                anchors.fill: parent
                spacing: 8
                visible: root.subMode === "operate"

                Rectangle {
                    width: 430
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.red

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        spacing: 7

                        SectionLabel {
                            text: "COMMIT OPERATIONS"
                        }

                        GohuText {
                            width: parent.width
                            text:
                                root.historyService
                                && root.historyService.selectedSha
                                ? root.historyService.selectedSha
                                : "SELECT A COMMIT IN LOG"
                            font.pixelSize: 11
                            color: Colors.orange
                            elide: Text.ElideMiddle
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            MiniButton {
                                width: (parent.width - 10) / 3
                                height: 30
                                label: "CHERRY-PICK"
                                accent: Colors.green
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                    && !root.historyService.actionBusy
                                onTriggered:
                                    root.historyService.cherryPick(
                                        root.historyService.selectedSha
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 10) / 3
                                height: 30
                                label: "REVERT"
                                accent: Colors.orange
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                    && !root.historyService.actionBusy
                                onTriggered:
                                    root.historyService.revertCommit(
                                        root.historyService.selectedSha
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 10) / 3
                                height: 30
                                label: "DETACH"
                                accent: Colors.magenta
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                    && !root.historyService.actionBusy
                                onTriggered:
                                    root.historyService.detachAt(
                                        root.historyService.selectedSha
                                    )
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            MiniButton {
                                width: 112
                                height: 30
                                label:
                                    "RESET "
                                    + root.resetMode.toUpperCase()
                                accent:
                                    root.resetMode === "hard"
                                    ? Colors.red
                                    : Colors.orange
                                onTriggered: root.cycleResetMode()
                            }

                            MiniButton {
                                width: parent.width - 117
                                height: 30
                                label:
                                    root.armedAction === "reset"
                                    ? "CONFIRM RESET TO SELECTED COMMIT"
                                    : "ARM RESET"
                                accent: Colors.red
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                    && !root.historyService.actionBusy
                                onTriggered:
                                    root.armOrRun(
                                        "reset",
                                        function() {
                                            root.historyService.resetTo(
                                                root.historyService.selectedSha,
                                                root.resetMode,
                                                true
                                            );
                                        }
                                    )
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.22
                        }

                        EditorBox {
                            id: branchNameInput
                            width: parent.width
                            placeholder: "NEW BRANCH NAME FROM SELECTED COMMIT"
                            accent: Colors.cyan
                            keyboardOwner: root.keyboardHost
                        }

                        MiniButton {
                            width: parent.width
                            label: "CREATE BRANCH AT COMMIT"
                            accent: Colors.cyan
                            enabledAction:
                                root.historyService
                                && root.historyService.selectedSha
                                && branchNameInput.text.trim().length > 0
                                && !root.historyService.actionBusy
                            onTriggered:
                                root.historyService.createBranch(
                                    branchNameInput.text.trim(),
                                    root.historyService.selectedSha
                                )
                        }

                        EditorBox {
                            id: tagNameInput
                            width: parent.width
                            placeholder: "NEW TAG NAME FROM SELECTED COMMIT"
                            accent: Colors.magenta
                            keyboardOwner: root.keyboardHost
                        }

                        MiniButton {
                            width: parent.width
                            label: "CREATE TAG AT COMMIT"
                            accent: Colors.magenta
                            enabledAction:
                                root.historyService
                                && root.historyService.selectedSha
                                && tagNameInput.text.trim().length > 0
                                && !root.historyService.actionBusy
                            onTriggered:
                                root.historyService.createTag(
                                    tagNameInput.text.trim(),
                                    root.historyService.selectedSha
                                )
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: Colors.cyan
                            opacity: 0.22
                        }

                        GohuText {
                            text: "ANCESTRY NAVIGATION"
                            font.pixelSize: 11
                            color: Colors.cyan
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            Row {
                                width: (parent.width - 5) / 2
                                height: 30
                                spacing: 3

                                MiniButton {
                                    width: 28
                                    height: 30
                                    label: "‹"
                                    accent: Colors.cyan
                                    enabledAction:
                                        root.historyService
                                        && root.historyService.selectedParents.length > 1
                                    onTriggered:
                                        root.cycleAncestry("parent", -1)
                                }

                                MiniButton {
                                    width: parent.width - 62
                                    height: 30
                                    label:
                                        root.historyService
                                        && root.historyService.selectedParents.length > 0
                                        ? "PARENT "
                                          + String(root.ancestryParentIndex + 1)
                                          + "/"
                                          + String(root.historyService.selectedParents.length)
                                        : "PARENT 0"
                                    accent: Colors.cyan
                                    enabledAction:
                                        root.historyService
                                        && root.historyService.selectedParents.length > 0
                                    onTriggered:
                                        root.openAncestry("parent")
                                }

                                MiniButton {
                                    width: 28
                                    height: 30
                                    label: "›"
                                    accent: Colors.cyan
                                    enabledAction:
                                        root.historyService
                                        && root.historyService.selectedParents.length > 1
                                    onTriggered:
                                        root.cycleAncestry("parent", 1)
                                }
                            }

                            Row {
                                width: (parent.width - 5) / 2
                                height: 30
                                spacing: 3

                                MiniButton {
                                    width: 28
                                    height: 30
                                    label: "‹"
                                    accent: Colors.orange
                                    enabledAction:
                                        root.historyService
                                        && root.historyService.selectedChildren.length > 1
                                    onTriggered:
                                        root.cycleAncestry("child", -1)
                                }

                                MiniButton {
                                    width: parent.width - 62
                                    height: 30
                                    label:
                                        root.historyService
                                        && root.historyService.selectedChildren.length > 0
                                        ? "CHILD "
                                          + String(root.ancestryChildIndex + 1)
                                          + "/"
                                          + String(root.historyService.selectedChildren.length)
                                        : "CHILD 0"
                                    accent: Colors.orange
                                    enabledAction:
                                        root.historyService
                                        && root.historyService.selectedChildren.length > 0
                                    onTriggered:
                                        root.openAncestry("child")
                                }

                                MiniButton {
                                    width: 28
                                    height: 30
                                    label: "›"
                                    accent: Colors.orange
                                    enabledAction:
                                        root.historyService
                                        && root.historyService.selectedChildren.length > 1
                                    onTriggered:
                                        root.cycleAncestry("child", 1)
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 438
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

                    Flickable {
                        id: historyScroll5
                        anchors {
                            fill: parent
                            margins: 8
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: operationDetail.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        GohuText {
                            id: operationDetail
                            width: parent.width
                            text:
                                root.armedAction
                                ? "ARMED // "
                                  + root.armedAction.toUpperCase()
                                  + "\nPress the same destructive control again to execute.\n\n"
                                  + (
                                      root.historyService
                                      ? root.historyService.detailText
                                      : ""
                                    )
                                : root.historyService
                                ? root.historyService.detailText
                                : "NO HISTORY SERVICE"
                            font.pixelSize: 11
                            color:
                                root.armedAction
                                ? Colors.orange
                                : Colors.white
                            wrapMode: Text.WrapAnywhere
                        }
                    
                        NeonScrollBar {
                            flickable: historyScroll5
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
                root.historyService
                && root.historyService.lastError
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
                      + " // repeat control to confirm"
                    : root.historyService
                    ? (
                        root.historyService.lastError
                        ? "REFUSED // " + root.historyService.lastError
                        : root.historyService.actionBusy
                        ? root.historyService.actionName + " // RUNNING"
                        : root.historyService.queryBusy
                          && root.subMode === "query"
                        ? "QUERY // RUNNING"
                        : root.historyService.reflogBusy
                          && root.subMode === "reflog"
                        ? "REFLOG // READING"
                        : root.subMode === "query"
                        ? root.historyService.queryStatus
                        : root.subMode === "reflog"
                        ? root.historyService.reflogStatus
                        : root.historyService.refreshing
                        ? "READING HISTORY"
                        : root.historyService.actionStatus
                      )
                    : "NO HISTORY SERVICE"
                font.pixelSize: 10
                color:
                    root.armedAction
                    ? Colors.orange
                    : root.historyService
                      && root.historyService.lastError
                    ? Colors.red
                    : Colors.cyan
                elide: Text.ElideRight
            }
        }
    }

    Connections {
        target: root.historyService
        enabled: root.historyService !== null
        ignoreUnknownSignals: true

        function onRefreshed() {
            root.syncScopeIndex(
                root.historyService.selectedRef || "ALL"
            );
        }

        function onSelectedParentsChanged() {
            root.ancestryParentIndex = 0;
        }

        function onSelectedChildrenChanged() {
            root.ancestryChildIndex = 0;
        }

        function onBranchRefsChanged() {
            root.syncScopeIndex(
                root.pendingScopeRef
                || root.historyService.selectedRef
                || "ALL"
            );
        }

        function onTagRefsChanged() {
            root.syncScopeIndex(
                root.pendingScopeRef
                || root.historyService.selectedRef
                || "ALL"
            );
        }

        function onReflogRowsChanged() {
            root.reconcileSelectedReflog();
        }

        function onActionFinished(action, success, detail) {
            if (!success)
                return;

            if (String(action || "") === "BRANCH"
                    && root.subMode === "reflog") {
                recoveryBranchInput.text = "";
                root.historyService.loadReflog();
            }
        }
    }

    Component.onCompleted: {
        if (root.historyService)
            root.historyService.refresh(
                "ALL",
                root.historyService.selectedMode
            );
    }
}
