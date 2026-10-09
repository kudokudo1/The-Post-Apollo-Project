import QtQuick
import qs.components

SectionFrame {
    id: root

    required property var blameService

    property string pathText: ""
    property string revisionText: "WORKTREE"
    property string startLineText: ""
    property string endLineText: ""
    property bool groupedMode: true
    property int selectedIndex: -1

    signal closeRequested()

    fillColor: Colors.dark
    borderWidth: 1
    borderColor: Colors.cyan

    readonly property var visibleRows:
        groupedMode
        ? blameService.groups
        : blameService.rows

    function selectedRecord() {
        if (selectedIndex < 0 || selectedIndex >= visibleRows.length)
            return null;
        return visibleRows[selectedIndex];
    }

    function numericLine(value) {
        const parsed = Number(String(value || "").trim());
        return Number.isFinite(parsed) && parsed > 0
            ? Math.floor(parsed)
            : 0;
    }

    function requestLoad() {
        const path = String(pathText || "").trim();
        const revision =
            String(revisionText || "").trim() || "WORKTREE";
        const start = numericLine(startLineText);
        const end = numericLine(endLineText);

        if (!path)
            return false;

        selectedIndex = -1;

        if (start > 0)
            return blameService.loadRange(
                path,
                start,
                end > 0 ? end : start,
                revision
            );

        return blameService.loadFile(path, revision);
    }

    function openRecord(record) {
        const row = record || {};

        if (!row.sha || row.uncommitted)
            return false;

        const path =
            String(row.sourcePath || blameService.filePath || "");
        const line =
            groupedMode
            ? Number(row.startLine || 0)
            : Number(row.finalLine || 0);

        return blameService.requestHistory(row.sha, path, line);
    }

    function requestCommit(record) {
        const row = record || {};
        return blameService.requestCommit(row.sha);
    }

    function prettyEpoch(epoch) {
        const value = Number(epoch || 0);

        if (!value)
            return "UNKNOWN DATE";

        const date = new Date(value * 1000);
        return date.toLocaleString(Qt.locale(), "yyyy-MM-dd hh:mm");
    }

    function lineLabel(record) {
        const row = record || {};

        if (groupedMode) {
            const start = Number(row.startLine || 0);
            const end = Number(row.endLine || start);
            return start === end
                ? "L" + String(start)
                : "L" + String(start) + "–" + String(end);
        }

        return "L" + String(Number(row.finalLine || 0));
    }

    function originalLabel(record) {
        const row = record || {};
        const path = String(row.sourcePath || blameService.filePath || "");

        if (groupedMode) {
            const start = Number(row.originalStartLine || 0);
            const end = Number(row.originalEndLine || start);
            return path + ":" + (
                start === end
                ? String(start)
                : String(start) + "–" + String(end)
            );
        }

        return path + ":" + String(Number(row.originalLine || 0));
    }

    component ActionButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property bool warningAction: false

        signal triggered()

        height: 28
        opacity: enabledAction ? 1.0 : 0.34
        color:
            selectedAction
            ? Colors.yellow
            : Colors.black
        border.width: 1
        border.color:
            selectedAction
            ? Colors.orange
            : warningAction
            ? Colors.orange
            : mouse.containsMouse
            ? Colors.magenta
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 9
            color:
                button.selectedAction
                ? Colors.magenta
                : button.warningAction
                ? Colors.orange
                : Colors.cyan
            opacity: 1.0
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

    component Field: Rectangle {
        id: field

        property string placeholderText: ""
        property alias text: editor.text

        signal accepted()

        height: 30
        color: Colors.black
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.magenta
            : Colors.cyan

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 7
            }

            visible: editor.text.length === 0
            text: field.placeholderText
            font.pixelSize: 8
            color: Colors.white
            opacity: 0.38
        }

        TextInput {
            id: editor

            anchors {
                fill: parent
                margins: 6
            }

            activeFocusOnPress: true
            selectByMouse: true
            verticalAlignment: TextInput.AlignVCenter
            clip: true
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 9
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black

            onAccepted: {
                focus = false;
                field.accepted();
            }

            Keys.onEscapePressed: function(event) {
                focus = false;
                event.accepted = true;
            }
        }
    }

    Item {
        anchors {
            fill: parent
            margins: 10
        }

        Column {
            id: headerColumn
            width: parent.width
            spacing: 6

            Row {
                width: parent.width
                height: 30
                spacing: 8

                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "PROVENANCE // BLAME"
                    font.pixelSize: 13
                    color: Colors.magenta
                }

                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        blameService.busy
                        ? "READING"
                        : String(blameService.status || "READY")
                    font.pixelSize: 9
                    color:
                        blameService.lastError
                        ? Colors.orange
                        : Colors.cyan
                }

                Item {
                    width: Math.max(
                        0,
                        parent.width
                        - 238
                        - closeButton.width
                    )
                    height: 1
                }

                ActionButton {
                    id: closeButton
                    width: 32
                    label: "X"
                    onTriggered: root.closeRequested()
                }
            }

            Row {
                width: parent.width
                spacing: 6

                Field {
                    id: pathField
                    width: Math.max(180, parent.width - 242)
                    placeholderText: "REPOSITORY-RELATIVE FILE PATH"
                    text: root.pathText

                    onTextChanged: root.pathText = text
                    onAccepted: root.requestLoad()
                }

                Field {
                    id: revisionField
                    width: 132
                    placeholderText: "WORKTREE / REF"
                    text: root.revisionText

                    onTextChanged: root.revisionText = text
                    onAccepted: root.requestLoad()
                }

                ActionButton {
                    width: 92
                    label:
                        blameService.busy
                        ? "READING"
                        : "LOAD"
                    enabledAction:
                        !blameService.busy
                        && String(root.pathText || "").trim().length > 0
                    onTriggered: root.requestLoad()
                }
            }

            Row {
                width: parent.width
                spacing: 6

                Field {
                    width: 84
                    placeholderText: "START LINE"
                    text: root.startLineText
                    onTextChanged: root.startLineText = text
                    onAccepted: root.requestLoad()
                }

                Field {
                    width: 84
                    placeholderText: "END LINE"
                    text: root.endLineText
                    onTextChanged: root.endLineText = text
                    onAccepted: root.requestLoad()
                }

                ActionButton {
                    width: 86
                    label: "GROUPS"
                    selectedAction: root.groupedMode
                    onTriggered: {
                        root.groupedMode = true;
                        root.selectedIndex = -1;
                    }
                }

                ActionButton {
                    width: 86
                    label: "LINES"
                    selectedAction: !root.groupedMode
                    onTriggered: {
                        root.groupedMode = false;
                        root.selectedIndex = -1;
                    }
                }

                ActionButton {
                    width: 106
                    label:
                        blameService.followRenames
                        ? "FOLLOW // ON"
                        : "FOLLOW // OFF"
                    selectedAction: blameService.followRenames
                    onTriggered:
                        blameService.followRenames =
                            !blameService.followRenames
                }

                Item {
                    width: Math.max(0, parent.width - 492)
                    height: 1
                }

                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        String(blameService.lineCount)
                        + " LINES // "
                        + String(blameService.groupCount)
                        + " GROUPS"
                    font.pixelSize: 9
                    color: Colors.white
                    opacity: 0.68
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.32
            }

            GohuText {
                width: parent.width
                visible: blameService.lastError.length > 0
                text: "ERROR // " + blameService.lastError
                font.pixelSize: 9
                color: Colors.orange
                elide: Text.ElideRight
            }

            GohuText {
                width: parent.width
                visible:
                    blameService.lastError.length === 0
                    && blameService.filePath.length > 0
                text:
                    blameService.filePath
                    + " // "
                    + blameService.revision
                    + (
                        blameService.requestedStartLine > 0
                        ? " // L"
                            + String(blameService.requestedStartLine)
                            + "–"
                            + String(blameService.requestedEndLine)
                        : ""
                    )
                font.pixelSize: 9
                color: Colors.blue
                elide: Text.ElideMiddle
            }
        }

        Rectangle {
            id: listFrame

            anchors {
                top: headerColumn.bottom
                topMargin: 8
                left: parent.left
                right: parent.right
                bottom: detailFrame.top
                bottomMargin: 8
            }

            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            ListView {
                id: provenanceList

                anchors {
                    fill: parent
                    margins: 4
                }

                clip: true
                spacing: 3
                boundsBehavior: Flickable.StopAtBounds
                model: root.visibleRows

                delegate: Rectangle {
                    id: rowDelegate

                    width: provenanceList.width
                    height: root.groupedMode ? 54 : 48

                    property var record: modelData
                    readonly property bool selected:
                        index === root.selectedIndex

                    color:
                        selected
                        ? Colors.dark
                        : Colors.black
                    border.width: selected ? 2 : 1
                    border.color:
                        selected
                        ? Colors.orange
                        : hover.containsMouse
                        ? Colors.magenta
                        : record.uncommitted
                        ? Colors.orange
                        : Colors.cyan

                    MouseArea {
                        id: hover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked: root.selectedIndex = index

                        onDoubleClicked: {
                            root.selectedIndex = index;
                            root.openRecord(record);
                        }
                    }

                    Row {
                        anchors {
                            fill: parent
                            margins: 6
                        }

                        spacing: 8

                        GohuText {
                            width: 66
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.lineLabel(record)
                            font.pixelSize: 9
                            color: Colors.orange
                            horizontalAlignment: Text.AlignRight
                        }

                        Rectangle {
                            width: 1
                            height: parent.height - 4
                            anchors.verticalCenter: parent.verticalCenter
                            color: Colors.cyan
                            opacity: 0.25
                        }

                        Column {
                            width: 116
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            GohuText {
                                width: parent.width
                                text:
                                    record.uncommitted
                                    ? "WORKTREE"
                                    : String(record.shortSha || "")
                                font.pixelSize: 9
                                color:
                                    record.uncommitted
                                    ? Colors.orange
                                    : Colors.blue
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text: String(record.author || "UNKNOWN")
                                font.pixelSize: 8
                                color: Colors.white
                                elide: Text.ElideRight
                            }
                        }

                        Column {
                            width: Math.max(
                                120,
                                parent.width - 66 - 1 - 116 - 242
                            )
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            GohuText {
                                width: parent.width
                                text:
                                    root.groupedMode
                                    ? String(record.summary || "NO SUMMARY")
                                    : String(record.content || "")
                                font.pixelSize: 9
                                color:
                                    root.groupedMode
                                    ? Colors.cyan
                                    : Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text: root.originalLabel(record)
                                font.pixelSize: 8
                                color: Colors.white
                                opacity: 0.52
                                elide: Text.ElideMiddle
                            }
                        }

                        Column {
                            width: 118
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            GohuText {
                                width: parent.width
                                text: root.prettyEpoch(record.authorTime)
                                font.pixelSize: 8
                                color: Colors.white
                                opacity: 0.62
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideLeft
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.groupedMode
                                    ? String(record.lineCount || 1) + " LINES"
                                    : String(record.authorTimezone || "")
                                font.pixelSize: 8
                                color: Colors.cyan
                                horizontalAlignment: Text.AlignRight
                            }
                        }

                        Row {
                            width: 108
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4

                            ActionButton {
                                width: 50
                                label: "HIST"
                                enabledAction: !record.uncommitted
                                onTriggered: root.openRecord(record)
                            }

                            ActionButton {
                                width: 54
                                label: "COMMIT"
                                enabledAction: !record.uncommitted
                                onTriggered: root.requestCommit(record)
                            }
                        }
                    }
                }

                GohuText {
                    anchors.centerIn: parent
                    visible:
                        !blameService.busy
                        && root.visibleRows.length === 0
                    text:
                        blameService.filePath
                        ? "NO PROVENANCE ROWS"
                        : "LOAD A FILE TO INSPECT PROVENANCE"
                    font.pixelSize: 10
                    color: Colors.white
                    opacity: 0.42
                }
            }

            Rectangle {
                anchors {
                    right: parent.right
                    top: parent.top
                    bottom: parent.bottom
                    margins: 2
                }

                width: 4
                visible:
                    provenanceList.contentHeight
                    > provenanceList.height
                color: Colors.dark

                Rectangle {
                    width: parent.width
                    height: Math.max(
                        18,
                        parent.height
                        * provenanceList.height
                        / Math.max(
                            provenanceList.height,
                            provenanceList.contentHeight
                        )
                    )
                    y:
                        provenanceList.contentY <= 0
                        ? 0
                        : Math.min(
                            parent.height - height,
                            (
                                provenanceList.contentY
                                / Math.max(
                                    1,
                                    provenanceList.contentHeight
                                    - provenanceList.height
                                )
                            )
                            * (parent.height - height)
                        )
                    color: Colors.cyan
                    opacity: 0.48
                }
            }
        }

        SectionFrame {
            id: detailFrame

            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
            }

            height: 112
            fillColor: Colors.black
            borderWidth: 1
            borderColor: Colors.blue

            property var record: root.selectedRecord()

            GohuText {
                anchors {
                    top: parent.top
                    left: parent.left
                    margins: 7
                }

                text:
                    detailFrame.record
                    ? (
                        "SELECTED // "
                        + root.lineLabel(detailFrame.record)
                        + " // "
                        + (
                            detailFrame.record.uncommitted
                            ? "WORKTREE"
                            : String(detailFrame.record.shortSha || "")
                        )
                    )
                    : "SELECT A PROVENANCE ROW"
                font.pixelSize: 10
                color: Colors.magenta
            }

            GohuText {
                anchors {
                    top: parent.top
                    topMargin: 30
                    left: parent.left
                    right: parent.right
                    leftMargin: 7
                    rightMargin: 7
                }

                text:
                    detailFrame.record
                    ? (
                        String(detailFrame.record.author || "UNKNOWN")
                        + " // "
                        + root.prettyEpoch(detailFrame.record.authorTime)
                        + " // "
                        + root.originalLabel(detailFrame.record)
                    )
                    : "Double-click a committed row to request History."
                font.pixelSize: 8
                color: Colors.white
                opacity: 0.70
                elide: Text.ElideMiddle
            }

            GohuText {
                anchors {
                    top: parent.top
                    topMargin: 51
                    left: parent.left
                    right: parent.right
                    leftMargin: 7
                    rightMargin: 124
                }

                text:
                    detailFrame.record
                    ? String(detailFrame.record.summary || "")
                    : ""
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }

            GohuText {
                anchors {
                    top: parent.top
                    topMargin: 72
                    left: parent.left
                    right: parent.right
                    leftMargin: 7
                    rightMargin: 124
                }

                visible:
                    !!detailFrame.record
                    && !!detailFrame.record.previousPath
                text:
                    "PREVIOUS // "
                    + String(detailFrame.record.previousPath || "")
                    + (
                        detailFrame.record.previousSha
                        ? " // "
                            + String(detailFrame.record.previousSha).slice(0, 8)
                        : ""
                    )
                font.pixelSize: 8
                color: Colors.orange
                elide: Text.ElideMiddle
            }

            Column {
                anchors {
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                    rightMargin: 8
                }

                width: 104
                spacing: 6

                ActionButton {
                    width: parent.width
                    label: "OPEN HISTORY"
                    enabledAction:
                        !!detailFrame.record
                        && !detailFrame.record.uncommitted
                    onTriggered: root.openRecord(detailFrame.record)
                }

                ActionButton {
                    width: parent.width
                    label: "OPEN COMMIT"
                    enabledAction:
                        !!detailFrame.record
                        && !detailFrame.record.uncommitted
                    onTriggered: root.requestCommit(detailFrame.record)
                }
            }
        }
    }

    Connections {
        target: blameService

        function onLoaded() {
            root.pathText = blameService.filePath;
            root.revisionText = blameService.revision;

            if (blameService.requestedStartLine > 0) {
                root.startLineText =
                    String(blameService.requestedStartLine);
                root.endLineText =
                    String(blameService.requestedEndLine);
            } else {
                root.startLineText = "";
                root.endLineText = "";
            }
        }
    }
}
