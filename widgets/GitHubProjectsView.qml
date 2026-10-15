import QtQuick
import Quickshell
import qs.components
import qs.components as Components

Item {
    id: root

    required property var gitService
    required property var projectService
    required property var keyboardHost

    property string projectCamera: "board"
    property string itemCreateMode: "work"
    property bool projectExpanded: false
    property string armedItemAction: ""
    property string armedItemId: ""

    signal projectExpandedRequested(bool expanded)

    function selectItemCreateMode(mode) {
        const next = String(mode || "work");

        if (itemCreateMode === next)
            return;

        itemCreateMode = next;
        itemTitleInput.text = "";
        itemBodyInput.text = "";
    }

    function itemActionArmed(action, item) {
        return root.armedItemAction === String(action || "")
            && root.armedItemId
               === root.projectService.itemId(item);
    }

    function armOrRunItem(action, item, callback) {
        const id = root.projectService.itemId(item);

        if (!id)
            return;

        if (root.itemActionArmed(action, item)) {
            root.armedItemAction = "";
            root.armedItemId = "";

            if (callback)
                callback();

            return;
        }

        root.armedItemAction = String(action || "");
        root.armedItemId = id;
    }

    function clearItemArm() {
        root.armedItemAction = "";
        root.armedItemId = "";
    }

    function openProjectItem(item) {
        const url = root.projectService.itemUrl(item);

        if (url)
            Qt.openUrlExternally(url);
    }

    function moveItem(item, delta) {
        const options = root.projectService.statusOptions();

        if (options.length < 2)
            return;

        const current = root.projectService.itemStatus(item);
        let index = options.indexOf(current);

        if (index < 0)
            index = 0;

        index =
            (
                index
                + Number(delta || 0)
                + options.length
            )
            % options.length;

        root.projectService.setItemStatus(item, options[index]);
    }

    component ActionButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property bool primaryBlue: false
        property color accentColor: Colors.cyan
        property bool preserveIdentity: false

        signal triggered()

        height: 28
        opacity: enabledAction ? 1.0 : 0.34
        color:
            selectedAction
            ? Colors.yellow
            : Colors.black
        border.width: 1
        border.color:
            preserveIdentity ? accentColor
            : selectedAction ? Colors.orange
            : mouse.containsMouse ? Colors.orange
            : primaryBlue ? Colors.blue
            : accentColor

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 10
            color:
                button.preserveIdentity ? button.accentColor
                : button.selectedAction ? Colors.magenta
                : button.primaryBlue ? Colors.blue
                : button.accentColor
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

    component ProjectInput: Rectangle {
        id: field

        property string placeholderText: ""
        property alias text: editor.text
        property color accentColor: Colors.magenta

        signal edited()

        height: 30
        color: Colors.black
        border.width: editor.activeFocus ? 2 : 1
        border.color: field.accentColor

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 7
            }

            visible: editor.text.length === 0 && !editor.activeFocus
            text: field.placeholderText
            font.pixelSize: 10
            color: Colors.magenta
            opacity: 0.76
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
            font.pixelSize: 11
            color: Colors.magenta
            cursorDelegate: Rectangle {
                width: 2
                color: Colors.orange
            }
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black

            onTextChanged: field.edited()

            onAccepted: {
                focus = false;

                if (root.keyboardHost) {
                    root.keyboardHost.activeTextEditor = null;
                    root.keyboardHost.restoreGitKeyboardFocus(false);
                }
            }

            Keys.onEscapePressed: function(event) {
                focus = false;

                if (root.keyboardHost) {
                    root.keyboardHost.activeTextEditor = null;
                    root.keyboardHost.restoreGitKeyboardFocus(false);
                }

                event.accepted = true;
            }

            onActiveFocusChanged: {
                if (!root.keyboardHost)
                    return;

                if (activeFocus)
                    root.keyboardHost.activeTextEditor = editor;
                else if (root.keyboardHost.activeTextEditor === editor)
                    root.keyboardHost.activeTextEditor = null;
            }
        }
    }

    Connections {
        target: root.projectService

        function onMutationFinished(success, operation) {
            root.clearItemArm();

            if (!success)
                return;

            if (operation === "create-project")
                projectTitleInput.text = "";

            if (operation === "create-draft"
                    || operation === "create-issue"
                    || operation === "add-pr") {
                itemTitleInput.text = "";
                itemBodyInput.text = "";
            }
        }
    }

    onProjectCameraChanged: root.clearItemArm()

    onVisibleChanged: {
        if (visible
                && !root.projectService.busy
                && root.projectService.projects.length === 0) {
            root.projectService.refreshProjects();
        }
    }

    Item {
        anchors.fill: parent

        GohuText {
            visible: !root.projectExpanded
            x: 0
            y: 0
            width: 180
            height: 26
            verticalAlignment: Text.AlignVCenter
            text: "PROJECTS // OPERATING MAP"
            font.pixelSize: 10
            color: Colors.magenta
            elide: Text.ElideRight
        }

        Rectangle {
                visible: !root.projectExpanded
                x: 0
                y: 34
                width: 180
                height: parent.height - 34
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors {
                        fill: parent
                        margins: 8
                    }

                    spacing: 7

                    Row {
                        width: parent.width
                        height: 28
                        spacing: 6

                        GohuText {
                            width: parent.width - 66
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                "PROJECT INDEX // "
                                + String(root.projectService.projects.length)
                            font.pixelSize: 11
                            color: Colors.magenta
                            opacity: 0.82
                            elide: Text.ElideRight
                        }

                        ActionButton {
                            width: 60
                            label: root.projectService.busy ? "..." : "REFRESH"
                            enabledAction: !root.projectService.busy
                            onTriggered: root.projectService.refreshProjects()
                        }
                    }

                    ListView {
                        id: projectList

                        width: parent.width
                        height: parent.height - 112
                        spacing: 5
                        clip: true
                        model: root.projectService.projects

                        delegate: Rectangle {
                            id: projectCard

                            required property int index
                            required property var modelData

                            readonly property bool selected:
                                root.projectService.selectedProjectIndex === index

                            width: projectList.width
                            height: 64
                            color:
                                selected
                                ? Colors.yellow
                                : Colors.dark
                            border.width: selected ? 2 : 1
                            border.color:
                                selected
                                ? Colors.orange
                                : cardMouse.containsMouse
                                ? Colors.orange
                                : Colors.cyan

                            Column {
                                anchors {
                                    fill: parent
                                    margins: 6
                                }

                                spacing: 2

                                GohuText {
                                    width: parent.width
                                    text:
                                        "#"
                                        + String(root.projectService.projectNumber(projectCard.modelData))
                                        + " // "
                                        + root.projectService.projectTitle(projectCard.modelData)
                                    font.pixelSize: 12
                                    color:
                                        projectCard.selected
                                        ? Colors.magenta
                                        : Colors.white
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        String(
                                            projectCard.modelData.shortDescription
                                            || projectCard.modelData.description
                                            || "OPERATING MAP"
                                        )
                                    font.pixelSize: 10
                                    color: Colors.cyan
                                    opacity: 0.72
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: cardMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked:
                                    root.projectService.selectProject(projectCard.index)
                            }
                        }
                    }
                    NeonScrollBar {
                        flickable: projectList
                        handleStyle: "star"
                        // The bar is mounted outside the Column, so align it
                        // using reactive x/y properties, not a mapToItem()
                        // snapshot that can become stale when Column relayouts.
                        mountingParent: projectList.parent.parent
                        x: projectList.parent.x + projectList.x
                           + projectList.width - width - rightInset
                        y: projectList.parent.y + projectList.y + effectiveTopInset
                        visible: projectList.visible && scrollable
                    }

                    ProjectInput {
                        id: projectTitleInput
                        width: parent.width
                        placeholderText: "NEW PROJECT TITLE"
                    }

                    ActionButton {
                        width: parent.width
                        label: "CREATE PROJECT"
                        primaryBlue: true
                        enabledAction:
                            !root.projectService.busy
                            && projectTitleInput.text.trim().length > 0
                        onTriggered:
                            root.projectService.createProject(projectTitleInput.text)
                    }
                }
            }

        SectionFrame {
                id: projectsFrame
                x: root.projectExpanded ? 0 : 190
                y: 0
                width: root.projectExpanded ? parent.width : parent.width - 190
                height: parent.height
                fillColor: Colors.dark
                borderWidth: 1
                borderColor: Colors.cyan
                inset: 10

                Behavior on x {
                    NumberAnimation {
                        duration: 120
                        easing.type: Easing.OutQuad
                    }
                }

                Behavior on width {
                    NumberAnimation {
                        duration: 120
                        easing.type: Easing.OutQuad
                    }
                }

                Column {
                    anchors.fill: parent

                    spacing: 6

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 8

                        Column {
                            width: parent.width - 264
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            Row {
                                width: parent.width
                                height: 24
                                spacing: 5

                                ActionButton {
                                    width: 24
                                    height: 24
                                    label: root.projectExpanded ? "↙" : "↗"
                                    enabledAction: true
                                    selectedAction: root.projectExpanded
                                    onTriggered:
                                        root.projectExpandedRequested(
                                            !root.projectExpanded
                                        )
                                }

                                GohuText {
                                    width: parent.width - 29
                                    anchors.verticalCenter: parent.verticalCenter
                                    text:
                                        root.projectService.selectedNumber() > 0
                                        ? (
                                            "#"
                                            + String(root.projectService.selectedNumber())
                                            + " // "
                                            + root.projectService.selectedTitle()
                                          )
                                        : "NO PROJECT SELECTED"
                                    font.pixelSize: 13
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }
                            }

                            GohuText {
                                width: parent.width
                                text:
                                    String(
                                        root.projectService.projectView.shortDescription
                                        || root.projectService.projectView.description
                                        || "SELECT A PROJECT TO OPEN ITS OPERATING MAP"
                                    )
                                font.pixelSize: 9
                                color: Colors.cyan
                                opacity: 0.58
                                elide: Text.ElideRight
                            }
                        }

                        ActionButton {
                            width: 78
                            anchors.verticalCenter: parent.verticalCenter
                            label: "< PROJECT"
                            accentColor: Colors.orange
                            preserveIdentity: true
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.projects.length > 1
                            onTriggered: root.projectService.cycleProject(-1)
                        }

                        ActionButton {
                            width: 78
                            anchors.verticalCenter: parent.verticalCenter
                            label: "PROJECT >"
                            accentColor: Colors.orange
                            preserveIdentity: true
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.projects.length > 1
                            onTriggered: root.projectService.cycleProject(1)
                        }

                        ActionButton {
                            width: 84
                            anchors.verticalCenter: parent.verticalCenter
                            label: "REFRESH MAP"
                            primaryBlue: true
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.selectedNumber() > 0
                            onTriggered: root.projectService.refreshSelectedProject()
                        }
                    }

                    Row {
                        width: parent.width
                        height: 24
                        spacing: 8

                        GohuText {
                            width: parent.width - 150
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                root.gitService.repoRemoteSlug
                                ? "ACTIVE REPOSITORY // " + root.gitService.repoRemoteSlug
                                : "ACTIVE REPOSITORY // NOT CONNECTED"
                            font.pixelSize: 10
                            color:
                                root.gitService.repoRemoteSlug
                                ? Colors.blue
                                : Colors.cyan
                            opacity: root.gitService.repoRemoteSlug ? 1.0 : 0.46
                            elide: Text.ElideMiddle
                        }

                        ActionButton {
                            width: 142
                            height: parent.height
                            label: "LINK CURRENT REPO"
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.selectedNumber() > 0
                                && !!root.gitService.repoRemoteSlug
                            onTriggered:
                                root.projectService.linkRepository(
                                    root.gitService.repoRemoteSlug
                                )
                        }
                    }

                    Row {
                        width: parent.width
                        height: 26
                        spacing: 5

                        ActionButton {
                            width: 46
                            height: parent.height
                            label: "WORK"
                            accentColor: Colors.orange
                            preserveIdentity: true
                            selectedAction: root.itemCreateMode === "work"
                            onTriggered: root.selectItemCreateMode("work")
                        }

                        ActionButton {
                            width: 46
                            height: parent.height
                            label: "ISSUE"
                            accentColor: Colors.red
                            preserveIdentity: true
                            selectedAction: root.itemCreateMode === "issue"
                            onTriggered: root.selectItemCreateMode("issue")
                        }

                        ActionButton {
                            width: 46
                            height: parent.height
                            label: "PR"
                            accentColor: Colors.green
                            preserveIdentity: true
                            selectedAction: root.itemCreateMode === "pr"
                            onTriggered: root.selectItemCreateMode("pr")
                        }

                        ProjectInput {
                            id: itemTitleInput
                            width:
                                root.itemCreateMode === "pr"
                                ? parent.width - 268
                                : parent.width * 0.28
                            height: parent.height
                            placeholderText:
                                root.itemCreateMode === "pr"
                                ? "PULL REQUEST URL"
                                : root.itemCreateMode === "issue"
                                ? "NEW ISSUE TITLE"
                                : "NEW WORK ITEM"
                        }

                        ProjectInput {
                            id: itemBodyInput
                            accentColor: Colors.orange
                            visible: root.itemCreateMode !== "pr"
                            width:
                                root.itemCreateMode === "pr"
                                ? 0
                                : parent.width * 0.27
                            height: parent.height
                            placeholderText:
                                root.itemCreateMode === "issue"
                                ? "ISSUE CONTEXT // optional"
                                : "CONTEXT // optional"
                        }

                        ActionButton {
                            width:
                                parent.width
                                - 138
                                - itemTitleInput.width
                                - itemBodyInput.width
                                - (
                                    root.itemCreateMode === "pr"
                                    ? 20
                                    : 25
                                  )
                            height: parent.height
                            label:
                                root.itemCreateMode === "issue"
                                ? "ADD ISSUE"
                                : root.itemCreateMode === "pr"
                                ? "ADD PR"
                                : "ADD WORK"
                            primaryBlue: true
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.selectedNumber() > 0
                                && itemTitleInput.text.trim().length > 0
                                && (
                                    root.itemCreateMode !== "issue"
                                    || !!root.gitService.repoRemoteSlug
                                   )
                            onTriggered: {
                                if (root.itemCreateMode === "issue") {
                                    root.projectService.createIssue(
                                        root.gitService.repoRemoteSlug,
                                        itemTitleInput.text,
                                        itemBodyInput.text
                                    );
                                } else if (root.itemCreateMode === "pr") {
                                    root.projectService.addPullRequest(
                                        itemTitleInput.text
                                    );
                                } else {
                                    root.projectService.createDraft(
                                        itemTitleInput.text,
                                        itemBodyInput.text
                                    );
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.44
                    }

                    Row {
                        width: parent.width
                        height: 24
                        spacing: 6

                        ActionButton {
                            width: (parent.width - 12) / 3
                            height: parent.height
                            label: "BOARD"
                            selectedAction: root.projectCamera === "board"
                            onTriggered: root.projectCamera = "board"
                        }

                        ActionButton {
                            width: (parent.width - 12) / 3
                            height: parent.height
                            label: "ROADMAP"
                            selectedAction: root.projectCamera === "roadmap"
                            onTriggered: root.projectCamera = "roadmap"
                        }

                        ActionButton {
                            width: (parent.width - 12) / 3
                            height: parent.height
                            label: "TABLE"
                            selectedAction: root.projectCamera === "table"
                            onTriggered: root.projectCamera = "table"
                        }
                    }

                    Flickable {
                        id: mapScroll

                        width: parent.width
                        height:
                            root.projectCamera === "board"
                            ? parent.height - 135
                            : 0
                        visible: root.projectCamera === "board"
                        clip: true
                        contentWidth: width
                        contentHeight: laneColumn.height

                        Column {
                            id: laneColumn

                            // Reserve the existing star-scrollbar zone.
                            width: Math.max(0, mapScroll.width - 20)
                            spacing: 8

                            Repeater {
                                model: root.projectService.laneNames()

                                delegate: Rectangle {
                                    id: lane

                                    required property var modelData

                                    readonly property string laneName:
                                        String(modelData || "NO STATUS")
                                    readonly property var laneItems:
                                        root.projectService.itemsForStatus(laneName)

                                    width: laneColumn.width
                                    height: laneBody.implicitHeight + 14
                                    color: Colors.black
                                    border.width: 1
                                    border.color:
                                        laneName.toLowerCase().indexOf("done") >= 0
                                        ? Colors.orange
                                        : laneName.toLowerCase().indexOf("progress") >= 0
                                        ? Colors.magenta
                                        : Colors.cyan

                                    Column {
                                        id: laneBody

                                        width: parent.width - 14
                                        anchors {
                                            top: parent.top
                                            left: parent.left
                                            margins: 7
                                        }

                                        spacing: 5

                                        Row {
                                            width: parent.width
                                            height: 24

                                            GohuText {
                                                width: parent.width - 80
                                                anchors.verticalCenter: parent.verticalCenter
                                                text:
                                                    lane.laneName.toUpperCase()
                                                    + " // "
                                                    + String(lane.laneItems.length)
                                                font.pixelSize: 11
                                                color:
                                                    lane.laneName.toLowerCase().indexOf("done") >= 0
                                                    ? Colors.orange
                                                    : lane.laneName.toLowerCase().indexOf("progress") >= 0
                                                    ? Colors.magenta
                                                    : Colors.cyan
                                                elide: Text.ElideRight
                                            }

                                            GohuText {
                                                width: 80
                                                anchors.verticalCenter: parent.verticalCenter
                                                horizontalAlignment: Text.AlignRight
                                                text: "WORK STATE"
                                                font.pixelSize: 9
                                                color: Colors.white
                                                opacity: 0.38
                                            }
                                        }

                                        Repeater {
                                            model: lane.laneItems

                                            delegate: Rectangle {
                                                id: itemCard

                                                required property var modelData

                                                width: laneBody.width
                                                height: 70
                                                color: Colors.dark
                                                border.width: 1
                                                border.color:
                                                    itemMouse.containsMouse
                                                    ? Colors.orange
                                                    : Colors.blue

                                                Column {
                                                    anchors {
                                                        fill: parent
                                                        margins: 6
                                                    }

                                                    spacing: 3

                                                    Row {
                                                        width: parent.width
                                                        height: 20
                                                        spacing: 5

                                                        GohuText {
                                                            width: parent.width - 151
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            text:
                                                                root.projectService.itemTitle(
                                                                    itemCard.modelData
                                                                )
                                                            font.pixelSize: 11
                                                            color: Colors.white
                                                            elide: Text.ElideRight
                                                        }

                                                        ActionButton {
                                                            width: 42
                                                            height: 20
                                                            label: "OPEN"
                                                            enabledAction:
                                                                !!root.projectService.itemUrl(
                                                                    itemCard.modelData
                                                                )
                                                            onTriggered:
                                                                root.openProjectItem(
                                                                    itemCard.modelData
                                                                )
                                                        }

                                                        ActionButton {
                                                            width: 70
                                                            height: 20
                                                            label:
                                                                root.itemActionArmed(
                                                                    "archive",
                                                                    itemCard.modelData
                                                                )
                                                                ? "CONFIRM"
                                                                : "ARCHIVE"
                                                            enabledAction:
                                                                !root.projectService.busy
                                                                && !!root.projectService.itemId(
                                                                    itemCard.modelData
                                                                )
                                                            onTriggered:
                                                                root.armOrRunItem(
                                                                    "archive",
                                                                    itemCard.modelData,
                                                                    function() {
                                                                        root.projectService.archiveItem(
                                                                            itemCard.modelData,
                                                                            true
                                                                        );
                                                                    }
                                                                )
                                                        }

                                                        Components.ActionButton {
                                                            width: 24
                                                            height: 20
                                                            label:
                                                                root.itemActionArmed(
                                                                    "remove",
                                                                    itemCard.modelData
                                                                )
                                                                ? "⚠︎"
                                                                : "×"
                                                            labelPixelSize: 11
                                                            destructive: true
                                                            idleForegroundColor: Colors.red
                                                            idleBorderColor: Colors.red
                                                            idleContentGlowColor: Colors.red
                                                            idleSoftGlowColor: Colors.red
                                                            hoverForegroundColor: Colors.red
                                                            hoverBorderColor: Colors.red
                                                            hoverContentGlowColor: Colors.red
                                                            hoverSoftGlowColor: Colors.red
                                                            selected: root.itemActionArmed(
                                                                "remove", itemCard.modelData)
                                                            selectedForegroundColor: Colors.red
                                                            selectedBorderColor: Colors.red
                                                            selectedContentGlowColor: Colors.red
                                                            selectedSoftGlowColor: Colors.red
                                                            available:
                                                                !root.projectService.busy
                                                                && !!root.projectService.itemId(
                                                                    itemCard.modelData
                                                                )
                                                            onTriggered:
                                                                root.armOrRunItem(
                                                                    "remove",
                                                                    itemCard.modelData,
                                                                    function() {
                                                                        root.projectService.removeItem(
                                                                            itemCard.modelData,
                                                                            true
                                                                        );
                                                                    }
                                                                )
                                                        }
                                                    }

                                                    Row {
                                                        width: parent.width
                                                        height: 18
                                                        spacing: 8

                                                        GohuText {
                                                            // Control widths + three 8px gaps require 198px.
                                                            width: Math.max(0, parent.width - 198)
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            text:
                                                                root.projectService.itemType(
                                                                    itemCard.modelData
                                                                )
                                                                + (
                                                                    root.projectService.itemRepository(
                                                                        itemCard.modelData
                                                                    )
                                                                    ? " // "
                                                                      + root.projectService.itemRepository(
                                                                          itemCard.modelData
                                                                      )
                                                                    : ""
                                                                  )
                                                            font.pixelSize: 9
                                                            color: Colors.cyan
                                                            opacity: 0.70
                                                            elide: Text.ElideMiddle
                                                        }

                                                        ActionButton {
                                                            width: 34
                                                            height: 18
                                                            label: "<"
                                                            enabledAction:
                                                                !root.projectService.busy
                                                                && root.projectService.statusOptions().length > 1
                                                            onTriggered:
                                                                root.moveItem(
                                                                    itemCard.modelData,
                                                                    -1
                                                                )
                                                        }

                                                        GohuText {
                                                            width: 106
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            horizontalAlignment: Text.AlignHCenter
                                                            text:
                                                                root.projectService.itemStatus(
                                                                    itemCard.modelData
                                                                )
                                                                || "NO STATUS"
                                                            font.pixelSize: 9
                                                            color: Colors.magenta
                                                            elide: Text.ElideRight
                                                        }

                                                        ActionButton {
                                                            width: 34
                                                            height: 18
                                                            label: ">"
                                                            enabledAction:
                                                                !root.projectService.busy
                                                                && root.projectService.statusOptions().length > 1
                                                            onTriggered:
                                                                root.moveItem(
                                                                    itemCard.modelData,
                                                                    1
                                                                )
                                                        }
                                                    }
                                                }

                                                MouseArea {
                                                    id: itemMouse

                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    acceptedButtons: Qt.NoButton
                                                }
                                            }
                                        }

                                        GohuText {
                                            width: parent.width
                                            visible: lane.laneItems.length === 0
                                            text: "NO WORK IN THIS STATE"
                                            font.pixelSize: 10
                                            color: Colors.white
                                            opacity: 0.32
                                        }
                                    }
                                }
                            }
                        }
                    }
                    NeonScrollBar {
                        flickable: mapScroll
                        handleStyle: "star"
                        // The board starts below the mode controls. Tracking
                        // its live Column y keeps the star rail beside the
                        // cards, not up among the project title/buttons.
                        mountingParent: mapScroll.parent.parent
                        // The visible gap includes the content's 20px lane
                        // AND SectionFrame's unused right inset. Center in
                        // that full optical gap, without changing card widths.
                        x: mapScroll.parent.x + mapScroll.x + laneColumn.width
                           + Math.round((mapScroll.width - laneColumn.width
                                         + projectsFrame.rightInset - width) / 2)
                        y: mapScroll.parent.y + mapScroll.y + effectiveTopInset
                        visible: mapScroll.visible && scrollable
                    }

                    GitHubProjectsRoadmapView {
                        width: parent.width
                        height:
                            root.projectCamera === "roadmap"
                            ? parent.height - 135
                            : 0
                        visible: root.projectCamera === "roadmap"
                        projectService: root.projectService
                    }

                    GitHubProjectsTableView {
                        keyboardHost: root.keyboardHost
                        width: parent.width
                        height:
                            root.projectCamera === "table"
                            ? parent.height - 135
                            : 0
                        visible: root.projectCamera === "table"
                        projectService: root.projectService
                    }
                }
            }
    }
}
