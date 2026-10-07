import QtQuick
import qs.components

Item {
    id: root

    required property var chartService

    property string scopeMode: "ROOM"
    property string statusFilter: "ACTIVE"
    property int selectedIndex: -1
    property bool editorOpen: false
    property string editorMode: "NEW"
    property bool suggestionPanelOpen: false
    property int selectedSuggestionIndex: -1
    property string suggestionDecisionNote: ""

    readonly property var sourceSuggestions:
        scopeMode === "PATIENT"
        ? chartService.patientSuggestions
        : chartService.roomSuggestions

    readonly property var selectedSuggestion: {
        const rows = Array.isArray(sourceSuggestions)
            ? sourceSuggestions : [];
        if (selectedSuggestionIndex < 0
                || selectedSuggestionIndex >= rows.length)
            return null;
        return rows[selectedSuggestionIndex] || null;
    }

    readonly property var sourceEntries:
        scopeMode === "PATIENT"
        ? chartService.patientEntries
        : chartService.roomEntries

    readonly property var displayEntries: {
        const source = Array.isArray(sourceEntries)
            ? sourceEntries : [];

        if (statusFilter === "ALL")
            return source;

        return source.filter(function(entry) {
            return String((entry || {}).status || "") === statusFilter;
        });
    }

    readonly property var selectedEntry: {
        if (selectedIndex < 0
                || selectedIndex >= displayEntries.length)
            return null;
        return displayEntries[selectedIndex] || null;
    }

    signal closeRequested()

    function statusColor(value) {
        const status = String(value || "").toUpperCase();
        if (status === "ACTIVE")
            return Colors.green;
        if (status === "RESOLVED")
            return Colors.blue;
        if (status === "SUPERSEDED")
            return Colors.magenta;
        if (status === "ARCHIVED")
            return Colors.white;
        return Colors.cyan;
    }

    function resetSelection() {
        selectedIndex = displayEntries.length > 0 ? 0 : -1;
    }

    function resetSuggestionSelection() {
        const rows = Array.isArray(sourceSuggestions)
            ? sourceSuggestions : [];
        selectedSuggestionIndex = rows.length > 0 ? 0 : -1;
        suggestionDecisionNote = "";
    }

    function openSuggestionPanel() {
        editorOpen = false;
        suggestionPanelOpen = true;
        resetSuggestionSelection();
        chartService.refreshSuggestions();
    }

    function closeSuggestionPanel() {
        suggestionPanelOpen = false;
        suggestionDecisionNote = "";
    }

    function promoteSelectedSuggestion() {
        if (!selectedSuggestion)
            return false;
        return chartService.promoteSuggestion(
            String(selectedSuggestion.id || "")
        );
    }

    function rejectSelectedSuggestion() {
        if (!selectedSuggestion)
            return false;
        return chartService.rejectSuggestion(
            String(selectedSuggestion.id || ""),
            suggestionDecisionNote
        );
    }

    function openEditor(modeValue) {
        const mode = String(modeValue || "NEW");

        if (mode === "REPLACE"
                && (!selectedEntry
                    || String(selectedEntry.status) !== "ACTIVE"))
            return false;

        editorMode = mode;
        if (mode === "REPLACE") {
            kindInput.text = String(selectedEntry.kind || "NOTE");
            titleInput.text = String(selectedEntry.title || "");
            priorityInput.text = String(selectedEntry.priority || 50);
            bodyInput.text = String(selectedEntry.body || "");
        } else {
            kindInput.text = "NOTE";
            titleInput.text = "";
            priorityInput.text = "50";
            bodyInput.text = "";
        }

        editorOpen = true;
        Qt.callLater(function() {
            bodyInput.forceActiveFocus();
        });
        return true;
    }

    function saveEditor() {
        const supersedes =
            editorMode === "REPLACE" && selectedEntry
            ? String(selectedEntry.id || "")
            : "";

        return chartService.addEntry(
            scopeMode,
            kindInput.text,
            titleInput.text,
            Number(priorityInput.text || 50),
            bodyInput.text,
            supersedes
        );
    }

    onScopeModeChanged: {
        editorOpen = false;
        resetSelection();
        resetSuggestionSelection();
    }

    onStatusFilterChanged: {
        editorOpen = false;
        resetSelection();
    }

    onDisplayEntriesChanged: {
        if (displayEntries.length === 0) {
            selectedIndex = -1;
            return;
        }

        if (selectedIndex < 0
                || selectedIndex >= displayEntries.length)
            selectedIndex = 0;
    }

    Connections {
        target: chartService

        function onEntrySaved(entry) {
            root.editorOpen = false;
        }

        function onEntryStatusChanged(entry) {
            root.editorOpen = false;
        }

        function onSuggestionsRefreshed() {
            if (root.suggestionPanelOpen)
                root.resetSuggestionSelection();
        }

        function onSuggestionDecision(operation, result) {
            root.suggestionDecisionNote = "";
            chartService.refreshAll();

            if (String(operation || "") === "PROMOTE") {
                root.suggestionPanelOpen = false;
                root.statusFilter = "ACTIVE";
                root.resetSelection();
            } else {
                Qt.callLater(root.resetSuggestionSelection);
            }
        }
    }

    component ChartButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        property bool selectedAction: false

        signal triggered()

        height: 28
        color:
            selectedAction || buttonMouse.pressed
            ? accent : Colors.black
        border.width:
            selectedAction || buttonMouse.containsMouse
            ? 2 : 1
        border.color: accent
        opacity: enabledAction ? 1.0 : 0.35

        GohuText {
            anchors.centerIn: parent
            width: parent.width - 6
            text: button.label
            font.pixelSize: 8
            color:
                button.selectedAction || buttonMouse.pressed
                ? Colors.black : button.accent
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        MouseArea {
            id: buttonMouse
            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: button.triggered()
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
            border.color: Colors.green

            Row {
                anchors {
                    fill: parent
                    margins: 7
                }
                spacing: 6

                GohuText {
                    width: Math.max(150, parent.width - 638)
                    anchors.verticalCenter: parent.verticalCenter
                    text:
                        "HOSPITAL CHART // "
                        + root.scopeMode
                        + " // P"
                        + String(chartService.patientActiveCount)
                        + " R"
                        + String(chartService.roomActiveCount)
                    font.pixelSize: 11
                    color: Colors.green
                    elide: Text.ElideRight
                }

                Repeater {
                    model: ["PATIENT", "ROOM"]

                    ChartButton {
                        required property string modelData
                        width: 84
                        anchors.verticalCenter: parent.verticalCenter
                        label: modelData
                        accent:
                            modelData === "PATIENT"
                            ? Colors.cyan : Colors.green
                        selectedAction:
                            root.scopeMode === modelData
                        enabledAction:
                            modelData === "PATIENT"
                            ? chartService.patientId.length > 0
                            : chartService.roomId.length > 0
                        onTriggered:
                            root.scopeMode = modelData
                    }
                }

                Repeater {
                    model: ["ACTIVE", "ALL"]

                    ChartButton {
                        required property string modelData
                        width: 66
                        anchors.verticalCenter: parent.verticalCenter
                        label: modelData
                        accent:
                            modelData === "ACTIVE"
                            ? Colors.blue : Colors.magenta
                        selectedAction:
                            root.statusFilter === modelData
                        onTriggered:
                            root.statusFilter = modelData
                    }
                }

                ChartButton {
                    width: 96
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        "SUGGEST "
                        + String(chartService.pendingSuggestionCount)
                    accent: Colors.magenta
                    selectedAction: root.suggestionPanelOpen
                    enabledAction:
                        !chartService.suggestionWriting
                        && (
                            chartService.patientId.length > 0
                            || chartService.roomId.length > 0
                        )
                    onTriggered: root.openSuggestionPanel()
                }

                ChartButton {
                    width: 76
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        chartService.loading ? "LOADING" : "REFRESH"
                    accent: Colors.blue
                    enabledAction:
                        !chartService.loading && !chartService.writing
                    onTriggered: chartService.refreshAll()
                }

                ChartButton {
                    width: 68
                    anchors.verticalCenter: parent.verticalCenter
                    label: "CLOSE"
                    accent: Colors.orange
                    onTriggered: root.closeRequested()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 50
            spacing: 8

            Rectangle {
                width: Math.max(270, parent.width * 0.35)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                ListView {
                    id: entryList
                    anchors {
                        fill: parent
                        margins: 7
                    }
                    spacing: 6
                    clip: true
                    model: root.displayEntries

                    delegate: Rectangle {
                        required property var modelData
                        required property int index

                        width: entryList.width
                        height: 84
                        color:
                            root.selectedIndex === index
                            ? Colors.black : Colors.dark
                        border.width:
                            root.selectedIndex === index ? 2 : 1
                        border.color:
                            root.selectedIndex === index
                            ? Colors.orange
                            : root.statusColor(modelData.status)
                        opacity:
                            String(modelData.status) === "ARCHIVED"
                            ? 0.58 : 1.0

                        Column {
                            anchors {
                                fill: parent
                                margins: 7
                            }
                            spacing: 3

                            GohuText {
                                width: parent.width
                                text:
                                    "P"
                                    + String(modelData.priority || 0)
                                    + " // "
                                    + String(modelData.kind || "NOTE")
                                    + " // "
                                    + String(modelData.status || "ACTIVE")
                                font.pixelSize: 8
                                color:
                                    root.statusColor(modelData.status)
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        modelData.title
                                        || "(UNTITLED)"
                                    )
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text: String(modelData.body || "")
                                font.pixelSize: 8
                                color: Colors.cyan
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedIndex = index
                        }
                    }

                    GohuText {
                        anchors.centerIn: parent
                        visible:
                            !chartService.loading
                            && root.displayEntries.length === 0
                        text:
                            "NO "
                            + root.statusFilter
                            + " "
                            + root.scopeMode
                            + " CHART ENTRIES"
                        font.pixelSize: 9
                        color: Colors.blue
                    }
                }
            }

            Rectangle {
                width:
                    parent.width
                    - Math.max(270, parent.width * 0.35)
                    - parent.spacing
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color:
                    root.selectedEntry
                    ? root.statusColor(root.selectedEntry.status)
                    : Colors.green

                Column {
                    anchors {
                        fill: parent
                        margins: 10
                    }
                    spacing: 7

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedEntry
                            ? (
                                root.scopeMode
                                + " CHART // #"
                                + String(root.selectedEntry.id)
                                + " // "
                                + String(root.selectedEntry.status)
                              )
                            : root.scopeMode + " CHART // NONE SELECTED"
                        font.pixelSize: 12
                        color:
                            root.selectedEntry
                            ? root.statusColor(root.selectedEntry.status)
                            : Colors.green
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.selectedEntry
                            ? (
                                "P"
                                + String(root.selectedEntry.priority || 0)
                                + " // "
                                + String(root.selectedEntry.kind || "NOTE")
                                + " // "
                                + String(
                                    root.selectedEntry.title
                                    || "(UNTITLED)"
                                  )
                              )
                            : ""
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        visible: root.selectedEntry !== null
                        text:
                            root.selectedEntry
                            ? (
                                "SOURCE // "
                                + String(
                                    root.selectedEntry.sourceType
                                    || "MANUAL"
                                  )
                                + " // ROOM "
                                + String(
                                    root.selectedEntry.sourceRoomId
                                    || "-"
                                  )
                                + " // SESSION "
                                + String(
                                    root.selectedEntry.sourceSessionId
                                    || "-"
                                  )
                              )
                            : ""
                        font.pixelSize: 8
                        color: Colors.blue
                        elide: Text.ElideMiddle
                    }

                    GohuText {
                        width: parent.width
                        visible: root.selectedEntry !== null
                        text:
                            root.selectedEntry
                            ? (
                                "HISTORY // SUPERSEDES #"
                                + String(
                                    root.selectedEntry.supersedesId
                                    || "-"
                                  )
                                + " // SUPERSEDED BY #"
                                + String(
                                    root.selectedEntry.supersededById
                                    || "-"
                                  )
                              )
                            : ""
                        font.pixelSize: 8
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    Flickable {
                        width: parent.width
                        height: Math.max(
                            110,
                            parent.height
                            - 168
                            - (editorPanel.visible ? 190 : 0)
                        )
                        clip: true
                        contentWidth: width
                        contentHeight: detailBody.implicitHeight + 8

                        GohuText {
                            id: detailBody
                            width: parent.width
                            text:
                                root.selectedEntry
                                ? String(root.selectedEntry.body || "")
                                : "SELECT AN ENTRY OR CREATE A NEW ONE"
                            textFormat: Text.MarkdownText
                            font.pixelSize: 10
                            color: Colors.white
                            wrapMode: Text.Wrap
                        }
                    }

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 5

                        Repeater {
                            model: [
                                "NEW",
                                "REPLACE",
                                "RESOLVE",
                                "ARCHIVE",
                                "RESTORE"
                            ]

                            ChartButton {
                                required property string modelData

                                readonly property string state:
                                    root.selectedEntry
                                    ? String(root.selectedEntry.status)
                                    : ""

                                width:
                                    (
                                        parent.width
                                        - parent.spacing * 4
                                    ) / 5
                                height: parent.height
                                label: modelData
                                accent:
                                    modelData === "NEW"
                                    ? Colors.green
                                    : modelData === "REPLACE"
                                    ? Colors.orange
                                    : modelData === "RESOLVE"
                                    ? Colors.blue
                                    : modelData === "ARCHIVE"
                                    ? Colors.magenta
                                    : Colors.cyan
                                enabledAction:
                                    !chartService.writing
                                    && (
                                        modelData === "NEW"
                                        || (
                                            modelData === "REPLACE"
                                            && state === "ACTIVE"
                                        )
                                        || (
                                            modelData === "RESOLVE"
                                            && state === "ACTIVE"
                                        )
                                        || (
                                            modelData === "ARCHIVE"
                                            && (
                                                state === "ACTIVE"
                                                || state === "RESOLVED"
                                            )
                                        )
                                        || (
                                            modelData === "RESTORE"
                                            && (
                                                state === "RESOLVED"
                                                || state === "ARCHIVED"
                                            )
                                        )
                                    )

                                onTriggered: {
                                    if (modelData === "NEW") {
                                        root.openEditor("NEW");
                                        return;
                                    }
                                    if (modelData === "REPLACE") {
                                        root.openEditor("REPLACE");
                                        return;
                                    }

                                    chartService.setEntryStatus(
                                        root.selectedEntry.id,
                                        modelData === "RESTORE"
                                        ? "ACTIVE"
                                        : modelData + "D"
                                    );
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: editorPanel
                        width: parent.width
                        height: 182
                        visible: root.editorOpen
                        color: Colors.black
                        border.width: 1
                        border.color:
                            root.editorMode === "REPLACE"
                            ? Colors.orange : Colors.green

                        Column {
                            anchors {
                                fill: parent
                                margins: 7
                            }
                            spacing: 6

                            GohuText {
                                width: parent.width
                                text:
                                    root.editorMode === "REPLACE"
                                    && root.selectedEntry
                                    ? (
                                        "REPLACE // SUPERSEDES #"
                                        + String(root.selectedEntry.id)
                                      )
                                    : "NEW CHART ENTRY"
                                font.pixelSize: 8
                                color:
                                    root.editorMode === "REPLACE"
                                    ? Colors.orange : Colors.green
                            }

                            Row {
                                width: parent.width
                                height: 28
                                spacing: 6

                                Rectangle {
                                    width: 105
                                    height: parent.height
                                    color: Colors.dark
                                    border.width: 1
                                    border.color: Colors.cyan

                                    TextInput {
                                        id: kindInput
                                        anchors {
                                            fill: parent
                                            margins: 5
                                        }
                                        text: "NOTE"
                                        color: Colors.white
                                        font.family:
                                            "GohuFont 11 Nerd Font Mono"
                                        font.pixelSize: 9
                                        selectByMouse: true
                                    }
                                }

                                Rectangle {
                                    width: parent.width - 181
                                    height: parent.height
                                    color: Colors.dark
                                    border.width: 1
                                    border.color: Colors.cyan

                                    TextInput {
                                        id: titleInput
                                        anchors {
                                            fill: parent
                                            margins: 5
                                        }
                                        color: Colors.white
                                        font.family:
                                            "GohuFont 11 Nerd Font Mono"
                                        font.pixelSize: 9
                                        selectByMouse: true
                                    }
                                }

                                Rectangle {
                                    width: 64
                                    height: parent.height
                                    color: Colors.dark
                                    border.width: 1
                                    border.color: Colors.orange

                                    TextInput {
                                        id: priorityInput
                                        anchors {
                                            fill: parent
                                            margins: 5
                                        }
                                        text: "50"
                                        color: Colors.orange
                                        font.family:
                                            "GohuFont 11 Nerd Font Mono"
                                        font.pixelSize: 9
                                        inputMethodHints: Qt.ImhDigitsOnly
                                        horizontalAlignment:
                                            TextInput.AlignHCenter
                                        selectByMouse: true
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 86
                                color: Colors.dark
                                border.width: 1
                                border.color:
                                    bodyInput.activeFocus
                                    ? Colors.orange : Colors.blue

                                TextEdit {
                                    id: bodyInput
                                    anchors {
                                        fill: parent
                                        margins: 6
                                    }
                                    color: Colors.white
                                    font.family:
                                        "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 9
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                }
                            }

                            Row {
                                width: parent.width
                                height: 28
                                spacing: 6

                                GohuText {
                                    width: parent.width - 176
                                    anchors.verticalCenter:
                                        parent.verticalCenter
                                    text: "KIND // TITLE // PRIORITY // BODY"
                                    font.pixelSize: 8
                                    color: Colors.blue
                                }

                                ChartButton {
                                    width: 82
                                    height: parent.height
                                    label:
                                        chartService.writing
                                        ? "SAVING" : "SAVE"
                                    accent: Colors.green
                                    enabledAction:
                                        !chartService.writing
                                        && bodyInput.text.trim().length > 0
                                    onTriggered: root.saveEditor()
                                }

                                ChartButton {
                                    width: 82
                                    height: parent.height
                                    label: "CANCEL"
                                    accent: Colors.orange
                                    enabledAction: !chartService.writing
                                    onTriggered: root.editorOpen = false
                                }
                            }
                        }
                    }

                    GohuText {
                        width: parent.width
                        visible: chartService.lastError.length > 0
                        text: chartService.lastError
                        font.pixelSize: 8
                        color: Colors.red
                        wrapMode: Text.Wrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }

    Rectangle {
        id: suggestionOverlay
        z: 900
        anchors.fill: parent
        visible: root.suggestionPanelOpen
        color: Colors.dark
        border.width: 2
        border.color: Colors.magenta

        Column {
            anchors {
                fill: parent
                margins: 10
            }
            spacing: 8

            Rectangle {
                width: parent.width
                height: 42
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta

                Row {
                    anchors {
                        fill: parent
                        margins: 7
                    }
                    spacing: 6

                    GohuText {
                        width: Math.max(120, parent.width - 420)
                        anchors.verticalCenter: parent.verticalCenter
                        text:
                            "MEMORY SUGGESTIONS // "
                            + root.scopeMode
                            + " // PENDING "
                            + String(
                                Array.isArray(root.sourceSuggestions)
                                ? root.sourceSuggestions.length
                                : 0
                              )
                        font.pixelSize: 11
                        color: Colors.magenta
                        elide: Text.ElideRight
                    }

                    Repeater {
                        model: ["PATIENT", "ROOM"]

                        ChartButton {
                            required property string modelData
                            width: 82
                            anchors.verticalCenter: parent.verticalCenter
                            label: modelData
                            accent:
                                modelData === "PATIENT"
                                ? Colors.cyan : Colors.green
                            selectedAction:
                                root.scopeMode === modelData
                            enabledAction:
                                modelData === "PATIENT"
                                ? chartService.patientId.length > 0
                                : chartService.roomId.length > 0
                            onTriggered:
                                root.scopeMode = modelData
                        }
                    }

                    ChartButton {
                        width: 78
                        anchors.verticalCenter: parent.verticalCenter
                        label:
                            chartService.patientSuggestionLoading
                            || chartService.roomSuggestionLoading
                            ? "READING" : "REFRESH"
                        accent: Colors.blue
                        enabledAction:
                            !chartService.patientSuggestionLoading
                            && !chartService.roomSuggestionLoading
                            && !chartService.suggestionWriting
                        onTriggered: chartService.refreshSuggestions()
                    }

                    ChartButton {
                        width: 68
                        anchors.verticalCenter: parent.verticalCenter
                        label: "BACK"
                        accent: Colors.orange
                        enabledAction: !chartService.suggestionWriting
                        onTriggered: root.closeSuggestionPanel()
                    }
                }
            }

            Row {
                width: parent.width
                height: parent.height - 50
                spacing: 8

                Rectangle {
                    width: Math.max(280, parent.width * 0.36)
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.magenta

                    ListView {
                        id: suggestionList
                        anchors {
                            fill: parent
                            margins: 7
                        }
                        spacing: 6
                        clip: true
                        model: root.sourceSuggestions

                        delegate: Rectangle {
                            required property var modelData
                            required property int index

                            width: suggestionList.width
                            height: 94
                            color:
                                root.selectedSuggestionIndex === index
                                ? Colors.dark : Colors.black
                            border.width:
                                root.selectedSuggestionIndex === index
                                ? 2 : 1
                            border.color:
                                root.selectedSuggestionIndex === index
                                ? Colors.orange : Colors.magenta

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 7
                                }
                                spacing: 3

                                GohuText {
                                    width: parent.width
                                    text:
                                        "#"
                                        + String(modelData.id || "?")
                                        + " // P"
                                        + String(modelData.priority || 0)
                                        + " // "
                                        + String(modelData.kind || "NOTE")
                                    font.pixelSize: 8
                                    color: Colors.magenta
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        String(
                                            modelData.title
                                            || "(UNTITLED SUGGESTION)"
                                        )
                                    font.pixelSize: 10
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        "DR "
                                        + String(modelData.doctorId || "?")
                                        + " // "
                                        + String(modelData.providerId || "?")
                                    font.pixelSize: 8
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text: String(modelData.body || "")
                                    font.pixelSize: 8
                                    color: Colors.blue
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked:
                                    root.selectedSuggestionIndex = index
                            }
                        }

                        GohuText {
                            anchors.centerIn: parent
                            visible:
                                !chartService.patientSuggestionLoading
                                && !chartService.roomSuggestionLoading
                                && (
                                    !Array.isArray(root.sourceSuggestions)
                                    || root.sourceSuggestions.length === 0
                                )
                            text:
                                "NO PENDING "
                                + root.scopeMode
                                + " MEMORY SUGGESTIONS"
                            font.pixelSize: 9
                            color: Colors.magenta
                        }
                    }
                }

                Rectangle {
                    width:
                        parent.width
                        - Math.max(280, parent.width * 0.36)
                        - parent.spacing
                    height: parent.height
                    color: Colors.black
                    border.width: 1
                    border.color:
                        root.selectedSuggestion
                        ? Colors.magenta : Colors.blue

                    Column {
                        anchors {
                            fill: parent
                            margins: 10
                        }
                        spacing: 7

                        GohuText {
                            width: parent.width
                            text:
                                root.selectedSuggestion
                                ? (
                                    "DOCTOR MEMORY PROPOSAL // #"
                                    + String(root.selectedSuggestion.id)
                                    + " // "
                                    + String(root.selectedSuggestion.scope)
                                  )
                                : "DOCTOR MEMORY PROPOSAL // NONE SELECTED"
                            font.pixelSize: 12
                            color: Colors.magenta
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            visible: root.selectedSuggestion !== null
                            text:
                                root.selectedSuggestion
                                ? (
                                    "P"
                                    + String(root.selectedSuggestion.priority || 0)
                                    + " // "
                                    + String(root.selectedSuggestion.kind || "NOTE")
                                    + " // "
                                    + String(
                                        root.selectedSuggestion.title
                                        || "(UNTITLED)"
                                      )
                                  )
                                : ""
                            font.pixelSize: 9
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            visible: root.selectedSuggestion !== null
                            text:
                                root.selectedSuggestion
                                ? (
                                    "DOCTOR // "
                                    + String(root.selectedSuggestion.doctorId || "-")
                                    + " // PROVIDER // "
                                    + String(root.selectedSuggestion.providerId || "-")
                                  )
                                : ""
                            font.pixelSize: 8
                            color: Colors.green
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            visible: root.selectedSuggestion !== null
                            text:
                                root.selectedSuggestion
                                ? (
                                    "PROVENANCE // ROOM "
                                    + String(root.selectedSuggestion.sourceRoomId || "-")
                                    + " // SESSION "
                                    + String(root.selectedSuggestion.sourceSessionId || "-")
                                    + " // MSG "
                                    + String(root.selectedSuggestion.sourceMessageId || "-")
                                    + " // REPORT "
                                    + String(root.selectedSuggestion.sourceReportId || "-")
                                    + " // CHECKPOINT "
                                    + String(root.selectedSuggestion.sourceCheckpointId || "-")
                                  )
                                : ""
                            font.pixelSize: 8
                            color: Colors.orange
                            elide: Text.ElideRight
                        }

                        Flickable {
                            width: parent.width
                            height: Math.max(120, parent.height - 238)
                            clip: true
                            contentWidth: width
                            contentHeight: suggestionBody.implicitHeight

                            GohuText {
                                id: suggestionBody
                                width: parent.width
                                text:
                                    root.selectedSuggestion
                                    ? String(root.selectedSuggestion.body || "")
                                    : ""
                                font.pixelSize: 10
                                color: Colors.white
                                wrapMode: Text.Wrap
                            }

                            NeonScrollBar {
                                flickable: parent
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 54
                            color: Colors.dark
                            border.width: 1
                            border.color:
                                suggestionNote.activeFocus
                                ? Colors.orange : Colors.blue

                            TextEdit {
                                id: suggestionNote
                                anchors {
                                    fill: parent
                                    margins: 6
                                }
                                text: root.suggestionDecisionNote
                                color: Colors.white
                                font.family:
                                    "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 9
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                onTextChanged:
                                    root.suggestionDecisionNote = text
                            }
                        }

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 6

                            GohuText {
                                width: parent.width - 188
                                anchors.verticalCenter:
                                    parent.verticalCenter
                                text:
                                    "OPERATOR DECISION NOTE // OPTIONAL"
                                font.pixelSize: 8
                                color: Colors.blue
                            }

                            ChartButton {
                                width: 88
                                height: parent.height
                                label:
                                    chartService.suggestionWriting
                                    && chartService.pendingSuggestionOperation
                                       === "PROMOTE"
                                    ? "PROMOTING" : "PROMOTE"
                                accent: Colors.green
                                enabledAction:
                                    root.selectedSuggestion !== null
                                    && !chartService.suggestionWriting
                                onTriggered:
                                    root.promoteSelectedSuggestion()
                            }

                            ChartButton {
                                width: 88
                                height: parent.height
                                label:
                                    chartService.suggestionWriting
                                    && chartService.pendingSuggestionOperation
                                       === "REJECT"
                                    ? "REJECTING" : "REJECT"
                                accent: Colors.red
                                enabledAction:
                                    root.selectedSuggestion !== null
                                    && !chartService.suggestionWriting
                                onTriggered:
                                    root.rejectSelectedSuggestion()
                            }
                        }

                        GohuText {
                            width: parent.width
                            visible: chartService.lastError.length > 0
                            text: chartService.lastError
                            font.pixelSize: 8
                            color: Colors.red
                            wrapMode: Text.Wrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

}
