import QtQuick
import Quickshell
import qs.components
import qs.components as Components

Item {
    id: root

    required property var projectService
    property var keyboardHost: null
    property Item editorHost: null

    // The Table is a small, clipped pane. The modal belongs to the complete
    // Projects surface, not to the Table viewport itself.
    onVisibleChanged: { if (!visible) closeEditor(); }

    property bool editOpen: false
    property var editItem: null
    property string editKind: ""
    property int editProjectNumber: 0

    function beginEdit(item, kind) {
        if (projectService.busy || !projectService.itemId(item))
            return;
        editItem = item;
        editKind = kind;
        editProjectNumber = projectService.selectedNumber();
        editOpen = true;
    }

    function closeEditor() {
        editOpen = false;
        editItem = null;
    }

    property string armedItemAction: ""
    property string armedItemId: ""

    readonly property int titleWidth: 250
    readonly property int typeWidth: 70
    readonly property int repoWidth: 190
    readonly property int statusWidth: 105
    readonly property int priorityWidth: 90
    readonly property int iterationWidth: 110
    readonly property int dateWidth: 92
    readonly property int actionWidth: 154
    readonly property int totalWidth:
        titleWidth
        + typeWidth
        + repoWidth
        + statusWidth
        + priorityWidth
        + iterationWidth
        + dateWidth * 2
        + actionWidth

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

    Connections {
        target: root.projectService

        function onMutationFinished(success, operation) {
            root.clearItemArm();
            if (success && (operation === "edit-field"
                            || operation === "edit-title"))
                root.closeEditor();
        }

        function onProjectRefreshed() {
            root.clearItemArm();
            root.closeEditor();
        }

        function onSelectedProjectIndexChanged() {
            if (root.editOpen
                    && root.projectService.selectedNumber() !== root.editProjectNumber)
                root.closeEditor();
        }
    }

    component Cell: Rectangle {
        id: cell

        property string value: ""
        property bool header: false
        property color accent: Colors.cyan

        height: header ? 32 : 38
        color: header ? Colors.black : Colors.dark
        border.width: 1
        border.color: header ? accent : Colors.blue

        GohuText {
            anchors {
                fill: parent
                leftMargin: 6
                rightMargin: 6
            }

            verticalAlignment: Text.AlignVCenter
            text: cell.value || "—"
            font.pixelSize: cell.header ? 10 : 9
            color: cell.header ? cell.accent : Colors.white
            opacity: cell.value ? 1.0 : 0.34
            elide: Text.ElideRight
        }
    }

    component EditableCell: Item {
        id: editCell

        property string value: ""
        property color accent: Colors.magenta
        signal triggered()

        height: 38

        Components.ActionButton {
            anchors.fill: parent
            label: editCell.value || "—"
            labelPixelSize: 9
            labelHorizontalAlignment: Text.AlignLeft
            labelElide: Text.ElideRight
            contentPadding: 10
            idleFillColor: Colors.dark
            hoverFillColor: Colors.yellow
            idleForegroundColor: editCell.value ? Colors.white : Colors.magenta
            hoverForegroundColor: Colors.magenta
            idleBorderColor: editCell.accent
            hoverBorderColor: editCell.accent
            accentColor: editCell.accent
            contentGlowEnabled: false
            softGlowEnabled: false
            available: !root.projectService.busy
            onTriggered: editCell.triggered()
        }

        // Keep the pencil's relational yellow independent of the cell text,
        // hover highlight, and selected field value.
        GohuText {
            anchors {
                right: parent.right
                verticalCenter: parent.verticalCenter
                rightMargin: 6
            }
            text: "✎"
            font.pixelSize: 13
            color: Colors.yellow
            z: 2
        }
    }

    component ItemAction: Rectangle {
        id: itemAction

        property string label: ""
        property bool enabledAction: true
        property bool destructive: false

        signal triggered()

        height: 26
        opacity: enabledAction ? 1.0 : 0.34
        color: Colors.black
        border.width: 1
        border.color: destructive ? Colors.red : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: itemAction.label
            font.pixelSize: 10
            color: itemAction.destructive ? Colors.red : Colors.cyan
        }

        MouseArea {
            anchors.fill: parent
            enabled: itemAction.enabledAction
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: itemAction.triggered()
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Row {
            width: parent.width
            height: 30

            GohuText {
                width: parent.width - 180
                anchors.verticalCenter: parent.verticalCenter
                text:
                    "TABLE // "
                    + String(root.projectService.items.length)
                    + " WORK ITEM"
                    + (root.projectService.items.length === 1 ? "" : "S")
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }

            GohuText {
                width: 180
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text:
                    String(root.projectService.projectFieldNames().length)
                    + " PROJECT FIELDS"
                font.pixelSize: 10
                color: Colors.cyan
                opacity: 0.74
            }
        }

        SectionFrame {
            id: tableFrame
            width: parent.width
            height: parent.height - 38
            fillColor: Colors.black
            borderWidth: 1
            borderColor: Colors.cyan
            inset: 8

            Flickable {
                id: tableScroll

                anchors.fill: parent
                anchors.rightMargin: 20

                clip: true
                contentWidth: Math.max(width, root.totalWidth)
                contentHeight: tableColumn.height

                Column {
                    id: tableColumn

                    width: tableScroll.contentWidth
                    spacing: 2

                    Row {
                        width: root.totalWidth
                        spacing: 0

                        Cell {
                            width: root.titleWidth
                            value: "TITLE"
                            header: true
                            accent: Colors.magenta
                        }

                        Cell {
                            width: root.typeWidth
                            value: "TYPE"
                            header: true
                        }

                        Cell {
                            width: root.repoWidth
                            value: "REPOSITORY"
                            header: true
                        }

                        Cell {
                            width: root.statusWidth
                            value: "STATUS"
                            header: true
                            accent: Colors.yellow
                        }

                        Cell {
                            width: root.priorityWidth
                            value: "PRIORITY"
                            header: true
                            accent: Colors.magenta
                        }

                        Cell {
                            width: root.iterationWidth
                            value: "ITERATION"
                            header: true
                            accent: Colors.orange
                        }

                        Cell {
                            width: root.dateWidth
                            value: "START"
                            header: true
                        }

                        Cell {
                            width: root.dateWidth
                            value: "TARGET"
                            header: true
                        }

                        Cell {
                            width: root.actionWidth
                            value: "ACTIONS"
                            header: true
                            accent: Colors.orange
                        }
                    }

                    Repeater {
                        model: root.projectService.items

                        delegate: Row {
                            id: tableRow

                            required property var modelData

                            width: root.totalWidth
                            spacing: 0

                            Cell {
                                visible: !root.projectService.isDraftItem(tableRow.modelData)
                                width: root.titleWidth
                                value:
                                    root.projectService.itemTitle(
                                        tableRow.modelData
                                    )
                            }

                            EditableCell {
                                visible: root.projectService.isDraftItem(tableRow.modelData)
                                width: root.titleWidth
                                accent: Colors.magenta
                                value:
                                    root.projectService.itemTitle(
                                        tableRow.modelData
                                    )
                                onTriggered: root.beginEdit(tableRow.modelData, "title")
                            }

                            Cell {
                                width: root.typeWidth
                                value:
                                    root.projectService.itemType(
                                        tableRow.modelData
                                    )
                            }

                            Cell {
                                width: root.repoWidth
                                value:
                                    root.projectService.itemRepository(
                                        tableRow.modelData
                                    )
                            }

                            EditableCell {
                                width: root.statusWidth
                                accent: Colors.yellow
                                value:
                                    root.projectService.itemStatus(
                                        tableRow.modelData
                                    )
                                onTriggered: root.beginEdit(tableRow.modelData, "status")
                            }

                            EditableCell {
                                width: root.priorityWidth
                                accent: Colors.magenta
                                value:
                                    root.projectService.itemPriority(
                                        tableRow.modelData
                                    )
                                onTriggered: root.beginEdit(tableRow.modelData, "priority")
                            }

                            EditableCell {
                                width: root.iterationWidth
                                accent: Colors.orange
                                value:
                                    root.projectService.itemIteration(
                                        tableRow.modelData
                                    )
                                onTriggered: root.beginEdit(tableRow.modelData, "iteration")
                            }

                            EditableCell {
                                width: root.dateWidth
                                accent: Colors.cyan
                                value:
                                    root.projectService.itemStartDate(
                                        tableRow.modelData
                                    )
                                onTriggered: root.beginEdit(tableRow.modelData, "start")
                            }

                            EditableCell {
                                width: root.dateWidth
                                accent: Colors.cyan
                                value:
                                    root.projectService.itemTargetDate(
                                        tableRow.modelData
                                    )
                                onTriggered: root.beginEdit(tableRow.modelData, "target")
                            }

                            Rectangle {
                                width: root.actionWidth
                                height: 38
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.orange

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 4

                                    ItemAction {
                                        width: 40
                                        label: "OPEN"
                                        enabledAction:
                                            !!root.projectService.itemUrl(
                                                tableRow.modelData
                                            )
                                        onTriggered:
                                            root.openProjectItem(
                                                tableRow.modelData
                                            )
                                    }

                                    ItemAction {
                                        width: 76
                                        label:
                                            root.itemActionArmed(
                                                "archive",
                                                tableRow.modelData
                                            )
                                            ? "CONFIRM"
                                            : "ARCHIVE"
                                        enabledAction:
                                            !root.projectService.busy
                                            && !!root.projectService.itemId(
                                                tableRow.modelData
                                            )
                                        onTriggered:
                                            root.armOrRunItem(
                                                "archive",
                                                tableRow.modelData,
                                                function() {
                                                    root.projectService.archiveItem(
                                                        tableRow.modelData,
                                                        true
                                                    );
                                                }
                                            )
                                    }

                                    Components.ActionButton {
                                        width: 26
                                        height: 26
                                        label:
                                            root.itemActionArmed(
                                                "remove",
                                                tableRow.modelData
                                            )
                                            ? "⚠︎"
                                            : "×"
                                        destructive: true
                                        labelPixelSize: 11
                                        idleForegroundColor: Colors.red
                                        idleBorderColor: Colors.red
                                        idleContentGlowColor: Colors.red
                                        idleSoftGlowColor: Colors.red
                                        hoverForegroundColor: Colors.red
                                        hoverBorderColor: Colors.red
                                        hoverContentGlowColor: Colors.red
                                        hoverSoftGlowColor: Colors.red
                                        selected: root.itemActionArmed("remove", tableRow.modelData)
                                        selectedForegroundColor: Colors.red
                                        selectedBorderColor: Colors.red
                                        selectedContentGlowColor: Colors.red
                                        selectedSoftGlowColor: Colors.red
                                        available:
                                            !root.projectService.busy
                                            && !!root.projectService.itemId(
                                                tableRow.modelData
                                            )
                                        onTriggered:
                                            root.armOrRunItem(
                                                "remove",
                                                tableRow.modelData,
                                                function() {
                                                    root.projectService.removeItem(
                                                        tableRow.modelData,
                                                        true
                                                    );
                                                }
                                            )
                                    }
                                }
                            }
                        }
                    }

                    GohuText {
                        width: tableScroll.width
                        visible: root.projectService.items.length === 0
                        text: "NO WORK ITEMS"
                        font.pixelSize: 11
                        color: Colors.white
                        opacity: 0.38
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
            NeonScrollBar {
                flickable: tableScroll
                handleStyle: "star"
                x: tableScroll.x + tableScroll.width
                   + Math.round((20 + tableFrame.rightInset - width) / 2)
            }
            NeonScrollBar { flickable: tableScroll; handleStyle: "star"; orientation: Qt.Horizontal }
        }
    }
    GitHubProjectsFieldEditor {
        id: fieldEditor
        parent: root.editorHost ? root.editorHost : root
        anchors.fill: parent
        z: 2000
        visible: root.editOpen
        projectService: root.projectService
        keyboardHost: root.keyboardHost
        targetItem: root.editItem
        targetProjectNumber: root.editProjectNumber
        fieldKind: root.editKind
        onDismissRequested: root.closeEditor()
    }

}
