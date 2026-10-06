import QtQuick
import QtQuick.Effects
import qs.components

Item {
    id: root

    property var gitService: null
    property var historyService: null
    property var keyboardHost: null

    property string subMode: "log"
    property string searchQuery: ""
    property int scopeIndex: 0
    property string inspectorMode: "detail"
    property string resetMode: "mixed"
    property string armedAction: ""

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

    function currentScope() {
        const entries = root.scopeEntries();
        if (entries.length === 0)
            return { label: "ALL", ref: "ALL" };

        root.scopeIndex = Math.max(
            0,
            Math.min(entries.length - 1, root.scopeIndex)
        );

        return entries[root.scopeIndex];
    }

    function cycleScope(delta) {
        const entries = root.scopeEntries();
        if (entries.length <= 0)
            return;

        root.scopeIndex =
            (root.scopeIndex + Number(delta || 0) + entries.length)
            % entries.length;

        if (root.historyService)
            root.historyService.refresh(
                root.currentScope().ref
            );
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

    function selectCommit(sha) {
        if (!root.historyService)
            return;

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

                EditorBox {
                    id: searchInput
                    width: parent.width - 210 - 34 - 220 - 34 - 116 - 42
                    anchors.verticalCenter: parent.verticalCenter
                    placeholder: "SEARCH SHA / AUTHOR / SUBJECT / REF"
                    accent: Colors.orange
                    keyboardOwner: root.keyboardHost
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
                            root.currentScope().ref
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
                        label: "LOG // INSPECT",
                        color: Colors.cyan
                    },
                    {
                        key: "compare",
                        label: "COMPARE A ↔ B",
                        color: Colors.orange
                    },
                    {
                        key: "operate",
                        label: "OPERATE",
                        color: Colors.red
                    }
                ]

                MiniButton {
                    required property var modelData
                    width:
                        (
                            parent.width
                            - parent.spacing * 2
                        ) / 3
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
            height: parent.height - 150

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
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        clip: true
                        contentWidth: width
                        contentHeight: historyColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: historyColumn
                            width: parent.width
                            spacing: 3

                            Repeater {
                                model: root.filteredRows()

                                Rectangle {
                                    id: commitRow
                                    required property int index
                                    required property var modelData

                                    width: historyColumn.width
                                    height: 50
                                    color:
                                        commitMouse.containsMouse
                                        || (
                                            root.historyService
                                            && root.historyService.selectedSha
                                               === String(modelData.sha || "")
                                        )
                                        ? Colors.black
                                        : "transparent"
                                    border.width:
                                        modelData.isHead
                                        || (
                                            root.historyService
                                            && root.historyService.selectedSha
                                               === String(modelData.sha || "")
                                        )
                                        ? 1 : 0
                                    border.color:
                                        modelData.isHead
                                        ? Colors.magenta
                                        : Colors.orange

                                    Item {
                                        id: graphLane
                                        width: 64
                                        height: parent.height
                                        anchors.left: parent.left

                                        Rectangle {
                                            width: 1
                                            anchors {
                                                top: parent.top
                                                bottom: parent.bottom
                                            }
                                            x:
                                                12
                                                + Math.min(
                                                    6,
                                                    Number(
                                                        commitRow.modelData.lane
                                                        || 0
                                                    )
                                                  ) * 7
                                            color: Colors.cyan
                                            opacity: 0.40
                                        }

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
                                                        commitRow.modelData.lane
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
                                                        commitRow.modelData.shortSha
                                                        || ""
                                                    )
                                                font.pixelSize: 10
                                                color:
                                                    commitRow.modelData.isHead
                                                    ? Colors.magenta
                                                    : Colors.orange
                                            }

                                            GohuText {
                                                width: parent.width - 73
                                                text:
                                                    String(
                                                        commitRow.modelData.refsText
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
                                                    commitRow.modelData.subject
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
                                                    commitRow.modelData.author
                                                    || ""
                                                )
                                                + " // "
                                                + root.dateLabel(
                                                    commitRow.modelData.epoch
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
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked:
                                            root.selectCommit(
                                                commitRow.modelData.sha
                                            )
                                    }
                                }
                            }
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
                                width: 76
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
                                width: 76
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
                                width: 72
                                label: "SET A"
                                accent: Colors.cyan
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                onTriggered: root.setCompare("A")
                            }

                            MiniButton {
                                width: 72
                                label: "SET B"
                                accent: Colors.orange
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedSha
                                onTriggered: root.setCompare("B")
                            }

                            MiniButton {
                                width: 86
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
                    }
                }
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

                            MiniButton {
                                width: (parent.width - 5) / 2
                                label:
                                    "PARENT "
                                    + String(
                                        root.historyService
                                        ? root.historyService.selectedParents.length
                                        : 0
                                      )
                                accent: Colors.cyan
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedParents.length > 0
                                onTriggered:
                                    root.selectCommit(
                                        root.historyService.selectedParents[0]
                                    )
                            }

                            MiniButton {
                                width: (parent.width - 5) / 2
                                label:
                                    "CHILD "
                                    + String(
                                        root.historyService
                                        ? root.historyService.selectedChildren.length
                                        : 0
                                      )
                                accent: Colors.orange
                                enabledAction:
                                    root.historyService
                                    && root.historyService.selectedChildren.length > 0
                                onTriggered:
                                    root.selectCommit(
                                        root.historyService.selectedChildren[0]
                                    )
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

    Component.onCompleted: {
        if (root.historyService)
            root.historyService.refresh("ALL");
    }
}
