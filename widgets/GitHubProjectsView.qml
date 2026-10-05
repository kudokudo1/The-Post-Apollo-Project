import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var gitService
    required property var projectService
    required property var keyboardHost

    property string projectCamera: "board"
    property bool projectExpanded: false

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
            : mouse.containsMouse
            ? Colors.orange
            : primaryBlue
            ? Colors.blue
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 8
            color:
                !button.enabledAction
                ? Colors.cyan
                : button.selectedAction
                ? Colors.magenta
                : button.primaryBlue
                ? Colors.blue
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

    component ProjectInput: Rectangle {
        id: field

        property string placeholderText: ""
        property alias text: editor.text

        signal edited()

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

            visible: editor.text.length === 0 && !editor.activeFocus
            text: field.placeholderText
            font.pixelSize: 8
            color: Colors.white
            opacity: 0.42
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
            if (!success)
                return;

            if (operation === "create-project")
                projectTitleInput.text = "";

            if (operation === "create-draft") {
                itemTitleInput.text = "";
                itemBodyInput.text = "";
            }
        }
    }

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
            font.pixelSize: 8
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

                Behavior on x {
                    NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
                }

                Behavior on width {
                    NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
                }

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
                            font.pixelSize: 10
                            color: Colors.cyan
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
                                    font.pixelSize: 11
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
                                    font.pixelSize: 8
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

        Rectangle {
                x: root.projectExpanded ? 0 : 190
                y: 0
                width: root.projectExpanded ? parent.width : parent.width - 190
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors {
                        fill: parent
                        margins: 10
                    }

                    spacing: 6

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 8

                        Column {
                            width: parent.width - 256
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            Row {
                                width: parent.width
                                height: 24
                                spacing: 5

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

                                ActionButton {
                                    width: 24
                                    height: 24
                                    label: root.projectExpanded ? "↙" : "↗"
                                    enabledAction: true
                                    selectedAction: root.projectExpanded
                                    onTriggered:
                                        root.projectExpanded = !root.projectExpanded
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
                                font.pixelSize: 7
                                color: Colors.cyan
                                opacity: 0.58
                                elide: Text.ElideRight
                            }
                        }

                        ActionButton {
                            width: 78
                            anchors.verticalCenter: parent.verticalCenter
                            label: "< PROJECT"
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.projects.length > 1
                            onTriggered: root.projectService.cycleProject(-1)
                        }

                        ActionButton {
                            width: 78
                            anchors.verticalCenter: parent.verticalCenter
                            label: "PROJECT >"
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
                            font.pixelSize: 8
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
                        spacing: 6

                        ProjectInput {
                            id: itemTitleInput
                            width: parent.width * 0.43
                            height: parent.height
                            placeholderText: "NEW WORK ITEM"
                        }

                        ProjectInput {
                            id: itemBodyInput
                            width: parent.width * 0.39
                            height: parent.height
                            placeholderText: "CONTEXT // optional"
                        }

                        ActionButton {
                            width:
                                parent.width
                                - itemTitleInput.width
                                - itemBodyInput.width
                                - 12
                            height: parent.height
                            label: "ADD WORK"
                            primaryBlue: true
                            enabledAction:
                                !root.projectService.busy
                                && root.projectService.selectedNumber() > 0
                                && itemTitleInput.text.trim().length > 0
                            onTriggered:
                                root.projectService.createDraft(
                                    itemTitleInput.text,
                                    itemBodyInput.text
                                )
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

                            width: mapScroll.width
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
                                                font.pixelSize: 9
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
                                                font.pixelSize: 7
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
                                                height: 66
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

                                                    GohuText {
                                                        width: parent.width
                                                        text:
                                                            root.projectService.itemTitle(
                                                                itemCard.modelData
                                                            )
                                                        font.pixelSize: 9
                                                        color: Colors.white
                                                        elide: Text.ElideRight
                                                    }

                                                    Row {
                                                        width: parent.width
                                                        height: 18
                                                        spacing: 8

                                                        GohuText {
                                                            width: parent.width - 190
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
                                                            font.pixelSize: 7
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
                                                            font.pixelSize: 7
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
                                            font.pixelSize: 8
                                            color: Colors.white
                                            opacity: 0.32
                                        }
                                    }
                                }
                            }
                        }
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
