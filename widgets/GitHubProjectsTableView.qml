import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var projectService

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
        }

        function onProjectRefreshed() {
            root.clearItemArm();
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
            font.pixelSize: 8
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
                font.pixelSize: 11
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
                font.pixelSize: 8
                color: Colors.cyan
                opacity: 0.74
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - 38
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Flickable {
                id: tableScroll

                anchors {
                    fill: parent
                    margins: 8
                }

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
                        }

                        Cell {
                            width: root.priorityWidth
                            value: "PRIORITY"
                            header: true
                        }

                        Cell {
                            width: root.iterationWidth
                            value: "ITERATION"
                            header: true
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
                                width: root.titleWidth
                                value:
                                    root.projectService.itemTitle(
                                        tableRow.modelData
                                    )
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

                            Cell {
                                width: root.statusWidth
                                value:
                                    root.projectService.itemStatus(
                                        tableRow.modelData
                                    )
                            }

                            Cell {
                                width: root.priorityWidth
                                value:
                                    root.projectService.itemPriority(
                                        tableRow.modelData
                                    )
                            }

                            Cell {
                                width: root.iterationWidth
                                value:
                                    root.projectService.itemIteration(
                                        tableRow.modelData
                                    )
                            }

                            Cell {
                                width: root.dateWidth
                                value:
                                    root.projectService.itemStartDate(
                                        tableRow.modelData
                                    )
                            }

                            Cell {
                                width: root.dateWidth
                                value:
                                    root.projectService.itemTargetDate(
                                        tableRow.modelData
                                    )
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

                                    ItemAction {
                                        width: 26
                                        label:
                                            root.itemActionArmed(
                                                "remove",
                                                tableRow.modelData
                                            )
                                            ? "!"
                                            : "X"
                                        destructive: true
                                        enabledAction:
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
                        font.pixelSize: 10
                        color: Colors.white
                        opacity: 0.38
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
}
