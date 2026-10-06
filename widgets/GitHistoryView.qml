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
    property string selectedQuerySha: ""
    property string selectedReflogSha: ""
    property string armedAction: ""

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
                root.currentScope().ref,
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
                    }
                ]

                MiniButton {
                    required property var modelData
                    width:
                        (
                            parent.width
                            - parent.spacing * 4
                        ) / 5
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
                                                    .sha
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
                                onTriggered: {
                                    root.selectedQuerySha = "";
                                    root.historyService.runQuery(
                                        queryPathInput.text,
                                        queryAuthorInput.text,
                                        querySinceInput.text,
                                        queryUntilInput.text,
                                        queryRangeInput.text
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
                                    querySinceInput.text = "";
                                    queryUntilInput.text = "";
                                    queryRangeInput.text = "";
                                    root.selectedQuerySha = "";
                                    root.historyService.clearQuery();
                                }
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
                                width: parent.width - 250
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.historyService
                                    ? root.historyService.queryStatus
                                    : "NO HISTORY SERVICE"
                                font.pixelSize: 10
                                color: Colors.green
                                elide: Text.ElideRight
                            }

                            MiniButton {
                                width: 118
                                label: "OPEN IN LOG"
                                accent: Colors.cyan
                                enabledAction:
                                    root.selectedQuerySha.length > 0
                                onTriggered: {
                                    searchInput.text =
                                        root.selectedQuerySha.slice(0, 8);
                                    root.subMode = "log";
                                }
                            }

                            MiniButton {
                                width: 122
                                label: "SET COMPARE A"
                                accent: Colors.orange
                                enabledAction:
                                    root.selectedQuerySha.length > 0
                                    && root.historyService
                                onTriggered:
                                    root.historyService.compareA =
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
                                                root.historyService.showCommit(
                                                    root.selectedQuerySha
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

                        Flickable {
                            id: historyScroll7

                            width: parent.width
                            height: parent.height - 34
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
                                        height: 52
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
                                                    String(
                                                        reflogRow.modelData.selector
                                                        || ""
                                                    )
                                                    + " // "
                                                    + String(
                                                        reflogRow.modelData.shortSha
                                                        || ""
                                                    )
                                                font.pixelSize: 10
                                                color: Colors.magenta
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

                                            onClicked: {
                                                root.selectedReflogSha =
                                                    String(
                                                        reflogRow.modelData.sha
                                                        || ""
                                                    );
                                                root.historyService.showCommit(
                                                    root.selectedReflogSha
                                                );
                                            }
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                flickable: historyScroll7
                                starHandle: true
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

                        EditorBox {
                            id: recoveryBranchInput

                            width: parent.width
                            placeholder: "RECOVERY BRANCH NAME"
                            accent: Colors.green
                            keyboardOwner: root.keyboardHost
                            editorFontSize: 10
                            placeholderFontSize: 9
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            MiniButton {
                                width: (parent.width - 12) / 3
                                height: 30
                                label: "RECOVER BRANCH"
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
                                onTriggered: {
                                    searchInput.text =
                                        root.selectedReflogSha.slice(0, 8);
                                    root.subMode = "log";
                                }
                            }
                        }

                        Flickable {
                            id: historyScroll8

                            width: parent.width
                            height: parent.height - 106
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

    Component.onCompleted: {
        if (root.historyService)
            root.historyService.refresh(
                "ALL",
                root.historyService.selectedMode
            );
    }
}
