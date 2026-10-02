import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import qs.components
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    required property var githubService
    property bool menuOpen: false

    property var queue: []
    property var savedSets: []
    property string setNameDraft: ""

    readonly property string repoSlug:
        githubService ? String(githubService.repoSlug || "") : ""

    readonly property var workflows:
        githubService && Array.isArray(githubService.workflows)
        ? githubService.workflows
        : []

    readonly property var repoSets:
        savedSets.filter(function(set) {
            return String(set.repository || "") === root.repoSlug;
        })

    readonly property int missingQueueCount:
        queue.filter(function(item) {
            return !root.workflowAvailable(item.path);
        }).length

    signal workflowSelected(int index)

    property int panelWidth: 1120
    property int panelHeight: 760
    property int panelTopMargin: 72
    property int panelLeftMargin: 360
    property int glowGutter: 14

    implicitWidth: panelWidth + glowGutter * 2
    implicitHeight: panelHeight + glowGutter * 2

    anchors {
        top: true
        left: true
    }

    margins {
        top: panelTopMargin - glowGutter
        left: panelLeftMargin - glowGutter
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay

    color: "transparent"
    surfaceFormat.opaque: false
    visible: true
    focusable: menuOpen

    mask: Region {
        x: 0
        y: 0
        width: root.menuOpen ? root.width : 0
        height: root.menuOpen ? root.height : 0
    }

    function open() {
        menuOpen = true;
    }

    function close() {
        menuOpen = false;
    }

    function toggle() {
        menuOpen = !menuOpen;
    }

    function workflowAvailable(path) {
        const target = String(path || "");

        for (let i = 0; i < workflows.length; ++i) {
            if (String(workflows[i].path || "") === target)
                return true;
        }

        return false;
    }

    function workflowIndexForPath(path) {
        const target = String(path || "");

        for (let i = 0; i < workflows.length; ++i) {
            if (String(workflows[i].path || "") === target)
                return i;
        }

        return -1;
    }

    function addWorkflow(workflow) {
        if (!workflow)
            return;

        const path = String(workflow.path || "");
        if (!path)
            return;

        queue = queue.concat([{
            path: path,
            name: String(workflow.name || path)
        }]);
    }

    function removeQueueIndex(index) {
        const next = queue.slice();
        next.splice(index, 1);
        queue = next;
    }

    function moveQueueIndex(index, delta) {
        const target = index + delta;

        if (index < 0 || index >= queue.length
                || target < 0 || target >= queue.length)
            return;

        const next = queue.slice();
        const item = next[index];
        next.splice(index, 1);
        next.splice(target, 0, item);
        queue = next;
    }

    function clearQueue() {
        queue = [];
    }

    function runQueue() {
        if (!githubService || queue.length === 0 || missingQueueCount > 0)
            return;

        githubService.runWorkflowBatch(
            queue.map(function(item) { return String(item.path || ""); })
        );
    }

    function globalSetIndex(repository, name) {
        for (let i = 0; i < savedSets.length; ++i) {
            if (String(savedSets[i].repository || "") === repository
                    && String(savedSets[i].name || "") === name)
                return i;
        }

        return -1;
    }

    function saveQueueAsSet(name) {
        const clean = String(name || "").trim();

        if (!clean || !repoSlug || queue.length === 0)
            return;

        const record = {
            repository: repoSlug,
            name: clean,
            items: queue.map(function(item) {
                return {
                    path: String(item.path || ""),
                    name: String(item.name || item.path || "")
                };
            })
        };

        const next = savedSets.slice();
        const existing = globalSetIndex(repoSlug, clean);

        if (existing >= 0)
            next[existing] = record;
        else
            next.push(record);

        savedSets = next;
        setNameDraft = "";
        persistSets();
    }

    function loadSet(setRecord) {
        if (!setRecord || !Array.isArray(setRecord.items))
            return;

        queue = setRecord.items.map(function(item) {
            return {
                path: String(item.path || ""),
                name: String(item.name || item.path || "")
            };
        });
    }

    function deleteSet(setRecord) {
        if (!setRecord)
            return;

        const index = globalSetIndex(
            String(setRecord.repository || ""),
            String(setRecord.name || "")
        );

        if (index < 0)
            return;

        const next = savedSets.slice();
        next.splice(index, 1);
        savedSets = next;
        persistSets();
    }

    function setMissingCount(setRecord) {
        if (!setRecord || !Array.isArray(setRecord.items))
            return 0;

        return setRecord.items.filter(function(item) {
            return !workflowAvailable(item.path);
        }).length;
    }

    function runSet(setRecord) {
        if (!githubService || !setRecord
                || !Array.isArray(setRecord.items)
                || setRecord.items.length === 0
                || setMissingCount(setRecord) > 0)
            return;

        githubService.runWorkflowBatch(
            setRecord.items.map(function(item) {
                return String(item.path || "");
            })
        );
    }

    function loadSetsFromDisk() {
        const raw = String(setsFile.text() || "").trim();

        if (!raw) {
            savedSets = [];
            return;
        }

        try {
            const parsed = JSON.parse(raw);
            savedSets = parsed && Array.isArray(parsed.sets)
                        ? parsed.sets
                        : [];
        } catch (error) {
            savedSets = [];
        }
    }

    function persistSets() {
        setsFile.setText(JSON.stringify({
            version: 1,
            sets: savedSets
        }, null, 2));
    }

    FileView {
        id: setsFile
        path: Qt.resolvedUrl("../workflow-sets.json")
        blockWrites: true
        atomicWrites: true
        printErrors: false

        onLoaded: root.loadSetsFromDisk()
    }

    component LibraryButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        signal triggered()

        height: 30
        color:
            !enabledAction
            ? Colors.black
            : selectedAction || mouse.containsMouse
            ? Colors.yellow
            : Colors.black
        border.width: 1
        border.color:
            !enabledAction
            ? Colors.cyan
            : selectedAction
            ? Colors.magenta
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 9
            color:
                !button.enabledAction
                ? Colors.cyan
                : button.selectedAction
                ? Colors.magenta
                : mouse.containsMouse
                ? Colors.orange
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

    Rectangle {
        id: frame

        width: root.panelWidth
        height: root.panelHeight
        anchors.centerIn: parent

        color: Colors.black
        opacity: root.menuOpen ? 0.98 : 0.0
        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent
            spread: 8
            z: -2
            opacity: root.menuOpen ? 0.28 : 0.0
            color: Colors.orange
        }

        Column {
            anchors {
                fill: parent
                margins: 16
            }

            spacing: 12

            Row {
                width: parent.width
                height: 52

                Column {
                    width: parent.width - 120
                    spacing: 4

                    GohuText {
                        text: "WORKFLOW LIBRARY // MACHINE ROOM"
                        font.pixelSize: 19
                        color: Colors.magenta
                    }

                    GohuText {
                        text: root.repoSlug || "NO REPOSITORY"
                        font.pixelSize: 9
                        color: Colors.cyan
                    }
                }

                LibraryButton {
                    width: 120
                    height: 34
                    label: "CLOSE"
                    anchors.verticalCenter: parent.verticalCenter
                    onTriggered: root.close()
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan
            }

            Row {
                width: parent.width
                height: parent.height - 66
                spacing: 12

                // LEFT: complete workflow library.
                Rectangle {
                    width: (parent.width - 12) / 2
                    height: parent.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 10
                        }

                        spacing: 8

                        Row {
                            width: parent.width
                            height: 26

                            GohuText {
                                width: parent.width - 110
                                text: "ALL WORKFLOWS"
                                font.pixelSize: 12
                                color: Colors.magenta
                            }

                            GohuText {
                                width: 110
                                text: String(root.workflows.length) + " MACHINES"
                                horizontalAlignment: Text.AlignRight
                                font.pixelSize: 8
                                color: Colors.orange
                            }
                        }

                        Flickable {
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: workflowColumn.height
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: workflowColumn
                                width: parent.width
                                spacing: 6

                                Repeater {
                                    model: root.workflows

                                    Rectangle {
                                        required property int index
                                        required property var modelData

                                        width: workflowColumn.width
                                        height: 54
                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.cyan

                                        Row {
                                            anchors {
                                                fill: parent
                                                margins: 7
                                            }
                                            spacing: 7

                                            Column {
                                                width: parent.width - 154
                                                anchors.verticalCenter: parent.verticalCenter
                                                spacing: 3

                                                GohuText {
                                                    width: parent.width
                                                    text: String(modelData.name || modelData.path || "UNKNOWN")
                                                    font.pixelSize: 10
                                                    color: Colors.white
                                                    elide: Text.ElideRight
                                                }

                                                GohuText {
                                                    width: parent.width
                                                    text: String(modelData.path || "")
                                                    font.pixelSize: 7
                                                    color: Colors.cyan
                                                    opacity: 0.72
                                                    elide: Text.ElideMiddle
                                                }
                                            }

                                            LibraryButton {
                                                width: 66
                                                label: "LOAD"
                                                onTriggered: root.workflowSelected(index)
                                            }

                                            LibraryButton {
                                                width: 74
                                                label: "+ QUEUE"
                                                onTriggered: root.addWorkflow(modelData)
                                            }
                                        }
                                    }
                                }

                                GohuText {
                                    width: parent.width
                                    visible: root.workflows.length === 0
                                    text: "NO SAVED WORKFLOWS"
                                    horizontalAlignment: Text.AlignHCenter
                                    font.pixelSize: 10
                                    color: Colors.cyan
                                    opacity: 0.44
                                }
                            }
                        }
                    }
                }

                // RIGHT: current execution queue + reusable saved sets.
                Column {
                    width: (parent.width - 12) / 2
                    height: parent.height
                    spacing: 12

                    Rectangle {
                        id: queuePane

                        width: parent.width
                        height: (parent.height - 12) * 0.58
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange

                        Column {
                            anchors {
                                fill: parent
                                margins: 10
                            }

                            spacing: 7

                            Row {
                                width: parent.width
                                height: 28
                                spacing: 7

                                GohuText {
                                    width: parent.width - 180
                                    text: "RUN QUEUE // ORDER"
                                    font.pixelSize: 12
                                    color: Colors.magenta
                                }

                                LibraryButton {
                                    width: 78
                                    label: "CLEAR"
                                    enabledAction: root.queue.length > 0
                                    onTriggered: root.clearQueue()
                                }

                                LibraryButton {
                                    width: 95
                                    label: githubService && githubService.actionBusy
                                           ? "RUNNING"
                                           : "RUN QUEUE"
                                    enabledAction:
                                        root.queue.length > 0
                                        && root.missingQueueCount === 0
                                        && githubService
                                        && !githubService.actionBusy
                                    onTriggered: root.runQueue()
                                }
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    root.missingQueueCount > 0
                                    ? String(root.missingQueueCount) + " MISSING WORKFLOW(S) // RUN BLOCKED"
                                    : githubService && githubService.actionResult !== "READY"
                                    ? githubService.actionResult
                                    : String(root.queue.length) + " READY"
                                font.pixelSize: 8
                                color: root.missingQueueCount > 0 ? Colors.red : Colors.cyan
                            }

                            Flickable {
                                width: parent.width
                                height: parent.height - 105
                                clip: true
                                contentWidth: width
                                contentHeight: queueColumn.height
                                boundsBehavior: Flickable.StopAtBounds

                                Column {
                                    id: queueColumn
                                    width: parent.width
                                    spacing: 5

                                    Repeater {
                                        model: root.queue

                                        Rectangle {
                                            required property int index
                                            required property var modelData

                                            width: queueColumn.width
                                            height: 38
                                            color: Colors.black
                                            border.width: 1
                                            border.color:
                                                root.workflowAvailable(modelData.path)
                                                ? Colors.cyan
                                                : Colors.red

                                            Row {
                                                anchors {
                                                    fill: parent
                                                    margins: 4
                                                }
                                                spacing: 4

                                                GohuText {
                                                    width: parent.width - 126
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text:
                                                        String(index + 1)
                                                        + " // "
                                                        + String(modelData.name || modelData.path || "UNKNOWN")
                                                        + (
                                                            root.workflowAvailable(modelData.path)
                                                            ? ""
                                                            : " // MISSING"
                                                        )
                                                    font.pixelSize: 8
                                                    color:
                                                        root.workflowAvailable(modelData.path)
                                                        ? Colors.white
                                                        : Colors.red
                                                    elide: Text.ElideRight
                                                }

                                                LibraryButton {
                                                    width: 36
                                                    height: 28
                                                    label: "↑"
                                                    enabledAction: index > 0
                                                    onTriggered: root.moveQueueIndex(index, -1)
                                                }

                                                LibraryButton {
                                                    width: 36
                                                    height: 28
                                                    label: "↓"
                                                    enabledAction: index < root.queue.length - 1
                                                    onTriggered: root.moveQueueIndex(index, 1)
                                                }

                                                LibraryButton {
                                                    width: 42
                                                    height: 28
                                                    label: "×"
                                                    onTriggered: root.removeQueueIndex(index)
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Row {
                                width: parent.width
                                height: 30
                                spacing: 7

                                Rectangle {
                                    width: parent.width - 112
                                    height: 30
                                    color: Colors.black
                                    border.width: 1
                                    border.color: setNameInput.activeFocus
                                                  ? Colors.magenta
                                                  : Colors.orange

                                    GohuText {
                                        anchors {
                                            left: parent.left
                                            verticalCenter: parent.verticalCenter
                                            leftMargin: 7
                                        }
                                        visible: setNameInput.text.length === 0
                                                 && !setNameInput.activeFocus
                                        text: "SET NAME"
                                        font.pixelSize: 8
                                        color: Colors.white
                                        opacity: 0.42
                                    }

                                    TextInput {
                                        id: setNameInput
                                        anchors {
                                            fill: parent
                                            margins: 6
                                        }
                                        activeFocusOnPress: true
                                        selectByMouse: true
                                        verticalAlignment: TextInput.AlignVCenter
                                        font.family: "GohuFont 11 Nerd Font Mono"
                                        font.pixelSize: 9
                                        color: Colors.white
                                        selectionColor: Colors.magenta
                                        selectedTextColor: Colors.black
                                        text: root.setNameDraft
                                        onTextChanged: root.setNameDraft = text
                                    }
                                }

                                LibraryButton {
                                    width: 105
                                    label: "SAVE SET"
                                    enabledAction:
                                        root.queue.length > 0
                                        && root.setNameDraft.trim().length > 0
                                    onTriggered: root.saveQueueAsSet(root.setNameDraft)
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: parent.height - queuePane.height - 12
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.blue

                        Column {
                            anchors {
                                fill: parent
                                margins: 10
                            }

                            spacing: 7

                            Row {
                                width: parent.width
                                height: 24

                                GohuText {
                                    width: parent.width - 100
                                    text: "SAVED SETS // REUSABLE ORDERS"
                                    font.pixelSize: 12
                                    color: Colors.magenta
                                }

                                GohuText {
                                    width: 100
                                    text: String(root.repoSets.length) + " SETS"
                                    horizontalAlignment: Text.AlignRight
                                    font.pixelSize: 8
                                    color: Colors.orange
                                }
                            }

                            Flickable {
                                width: parent.width
                                height: parent.height - 31
                                clip: true
                                contentWidth: width
                                contentHeight: setColumn.height
                                boundsBehavior: Flickable.StopAtBounds

                                Column {
                                    id: setColumn
                                    width: parent.width
                                    spacing: 5

                                    Repeater {
                                        model: root.repoSets

                                        Rectangle {
                                            required property int index
                                            required property var modelData

                                            width: setColumn.width
                                            height: 44
                                            color: Colors.black
                                            border.width: 1
                                            border.color:
                                                root.setMissingCount(modelData) > 0
                                                ? Colors.red
                                                : Colors.blue

                                            Row {
                                                anchors {
                                                    fill: parent
                                                    margins: 5
                                                }
                                                spacing: 5

                                                Column {
                                                    width: parent.width - 206
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    spacing: 2

                                                    GohuText {
                                                        width: parent.width
                                                        text: String(modelData.name || "UNNAMED SET")
                                                        font.pixelSize: 9
                                                        color: Colors.white
                                                        elide: Text.ElideRight
                                                    }

                                                    GohuText {
                                                        width: parent.width
                                                        text:
                                                            String(
                                                                Array.isArray(modelData.items)
                                                                ? modelData.items.length
                                                                : 0
                                                            )
                                                            + " WORKFLOWS"
                                                            + (
                                                                root.setMissingCount(modelData) > 0
                                                                ? " // MISSING "
                                                                  + String(root.setMissingCount(modelData))
                                                                : ""
                                                            )
                                                        font.pixelSize: 7
                                                        color:
                                                            root.setMissingCount(modelData) > 0
                                                            ? Colors.red
                                                            : Colors.cyan
                                                    }
                                                }

                                                LibraryButton {
                                                    width: 58
                                                    label: "LOAD"
                                                    onTriggered: root.loadSet(modelData)
                                                }

                                                LibraryButton {
                                                    width: 58
                                                    label: "RUN"
                                                    enabledAction:
                                                        root.setMissingCount(modelData) === 0
                                                        && githubService
                                                        && !githubService.actionBusy
                                                    onTriggered: root.runSet(modelData)
                                                }

                                                LibraryButton {
                                                    width: 70
                                                    label: "DELETE"
                                                    onTriggered: root.deleteSet(modelData)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
