import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var projectService

    property string armedItemAction: ""
    property string armedItemId: ""

    readonly property var scheduled:
        root.projectService.scheduledItems()
    readonly property var unscheduled:
        root.projectService.unscheduledItems()

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

    component RoadAction: Rectangle {
        id: roadAction

        property string label: ""
        property bool enabledAction: true
        property bool destructive: false

        signal triggered()

        height: 24
        opacity: enabledAction ? 1.0 : 0.34
        color: Colors.black
        border.width: 1
        border.color: destructive ? Colors.red : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: roadAction.label
            font.pixelSize: 7
            color: roadAction.destructive ? Colors.red : Colors.cyan
        }

        MouseArea {
            anchors.fill: parent
            enabled: roadAction.enabledAction
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: roadAction.triggered()
        }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Row {
            width: parent.width
            height: 30
            spacing: 8

            GohuText {
                width: parent.width - 210
                anchors.verticalCenter: parent.verticalCenter
                text:
                    "ROADMAP // "
                    + String(root.scheduled.length)
                    + " SCHEDULED // "
                    + String(root.unscheduled.length)
                    + " UNSCHEDULED"
                font.pixelSize: 9
                color: Colors.magenta
                elide: Text.ElideRight
            }

            GohuText {
                width: 202
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text:
                    root.projectService.startDateFieldName()
                    && root.projectService.targetDateFieldName()
                    ? (
                        root.projectService.startDateFieldName()
                        + " → "
                        + root.projectService.targetDateFieldName()
                      )
                    : "DATE FIELDS NOT FOUND"
                font.pixelSize: 7
                color:
                    root.projectService.startDateFieldName()
                    ? Colors.cyan
                    : Colors.orange
                elide: Text.ElideRight
            }
        }

        Rectangle {
            width: parent.width
            height: parent.height - 38
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Flickable {
                id: roadmapScroll

                anchors {
                    fill: parent
                    margins: 8
                }

                clip: true
                contentWidth: width
                contentHeight: roadmapColumn.height

                Column {
                    id: roadmapColumn

                    width: roadmapScroll.width
                    spacing: 5

                    Row {
                        width: parent.width
                        height: 28
                        spacing: 8

                        Rectangle {
                            width: 190
                            height: parent.height
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.blue

                            GohuText {
                                anchors {
                                    left: parent.left
                                    verticalCenter: parent.verticalCenter
                                    leftMargin: 7
                                }

                                text: "WORK ITEM"
                                font.pixelSize: 8
                                color: Colors.cyan
                            }
                        }

                        Item {
                            id: timelineHeader

                            width: parent.width - 198
                            height: parent.height

                            Repeater {
                                model: 5

                                delegate: Item {
                                    required property int index

                                    x:
                                        timelineHeader.width
                                        * index
                                        / 4
                                    width: 1
                                    height: timelineHeader.height

                                    Rectangle {
                                        width: 1
                                        height: parent.height
                                        color: Colors.cyan
                                        opacity: 0.28
                                    }

                                    GohuText {
                                        x:
                                            index === 4
                                            ? -74
                                            : 4
                                        y: 4
                                        width: 70
                                        text:
                                            root.projectService.roadmapDateAt(
                                                index / 4
                                            )
                                            || "—"
                                        font.pixelSize: 7
                                        color: Colors.white
                                        opacity: 0.68
                                        horizontalAlignment:
                                            index === 4
                                            ? Text.AlignRight
                                            : Text.AlignLeft
                                    }
                                }
                            }
                        }
                    }

                    Repeater {
                        model: root.scheduled

                        delegate: Rectangle {
                            id: roadRow

                            required property var modelData

                            width: roadmapColumn.width
                            height: 48
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.blue

                            Row {
                                anchors {
                                    fill: parent
                                    margins: 5
                                }

                                spacing: 8

                                Column {
                                    width: 170
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2

                                    GohuText {
                                        width: parent.width
                                        text:
                                            root.projectService.itemTitle(
                                                roadRow.modelData
                                            )
                                        font.pixelSize: 8
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            (
                                                root.projectService.itemRepository(
                                                    roadRow.modelData
                                                )
                                                || root.projectService.itemType(
                                                    roadRow.modelData
                                                )
                                            )
                                            + " // "
                                            + (
                                                root.projectService.itemStatus(
                                                    roadRow.modelData
                                                )
                                                || "NO STATUS"
                                            )
                                        font.pixelSize: 7
                                        color: Colors.cyan
                                        opacity: 0.66
                                        elide: Text.ElideRight
                                    }
                                }

                                Item {
                                    id: timeline

                                    width: parent.width - 325
                                    height: parent.height

                                    Repeater {
                                        model: 5

                                        delegate: Rectangle {
                                            required property int index

                                            x:
                                                timeline.width
                                                * index
                                                / 4
                                            width: 1
                                            height: timeline.height
                                            color: Colors.cyan
                                            opacity: 0.12
                                        }
                                    }

                                    Rectangle {
                                        x:
                                            root.projectService.roadmapBarX(
                                                roadRow.modelData,
                                                timeline.width
                                            )
                                        y: 9
                                        width:
                                            Math.min(
                                                timeline.width - x,
                                                root.projectService.roadmapBarWidth(
                                                    roadRow.modelData,
                                                    timeline.width
                                                )
                                            )
                                        height: 20
                                        radius: 2
                                        color: Colors.black
                                        border.width: 2
                                        border.color:
                                            root.projectService.itemStatus(
                                                roadRow.modelData
                                            ).toLowerCase().indexOf("done") >= 0
                                            ? Colors.orange
                                            : Colors.magenta

                                        GohuText {
                                            anchors {
                                                fill: parent
                                                leftMargin: 5
                                                rightMargin: 5
                                            }

                                            verticalAlignment: Text.AlignVCenter
                                            text:
                                                root.projectService.itemStartDate(
                                                    roadRow.modelData
                                                )
                                                + (
                                                    root.projectService.itemTargetDate(
                                                        roadRow.modelData
                                                    )
                                                    ? " → "
                                                      + root.projectService.itemTargetDate(
                                                          roadRow.modelData
                                                      )
                                                    : ""
                                                  )
                                            font.pixelSize: 7
                                            color: Colors.white
                                            elide: Text.ElideRight
                                        }
                                    }
                                }

                                Row {
                                    width: 139
                                    height: parent.height
                                    spacing: 5

                                    RoadAction {
                                        width: 40
                                        anchors.verticalCenter: parent.verticalCenter
                                        label: "OPEN"
                                        enabledAction:
                                            !!root.projectService.itemUrl(
                                                roadRow.modelData
                                            )
                                        onTriggered:
                                            root.openProjectItem(
                                                roadRow.modelData
                                            )
                                    }

                                    RoadAction {
                                        width: 65
                                        anchors.verticalCenter: parent.verticalCenter
                                        label:
                                            root.itemActionArmed(
                                                "archive",
                                                roadRow.modelData
                                            )
                                            ? "CONFIRM"
                                            : "ARCHIVE"
                                        enabledAction:
                                            !root.projectService.busy
                                            && !!root.projectService.itemId(
                                                roadRow.modelData
                                            )
                                        onTriggered:
                                            root.armOrRunItem(
                                                "archive",
                                                roadRow.modelData,
                                                function() {
                                                    root.projectService.archiveItem(
                                                        roadRow.modelData,
                                                        true
                                                    );
                                                }
                                            )
                                    }

                                    RoadAction {
                                        width: 24
                                        anchors.verticalCenter: parent.verticalCenter
                                        label:
                                            root.itemActionArmed(
                                                "remove",
                                                roadRow.modelData
                                            )
                                            ? "!"
                                            : "X"
                                        destructive: true
                                        enabledAction:
                                            !root.projectService.busy
                                            && !!root.projectService.itemId(
                                                roadRow.modelData
                                            )
                                        onTriggered:
                                            root.armOrRunItem(
                                                "remove",
                                                roadRow.modelData,
                                                function() {
                                                    root.projectService.removeItem(
                                                        roadRow.modelData,
                                                        true
                                                    );
                                                }
                                            )
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 30
                        visible: root.unscheduled.length > 0
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.orange

                        GohuText {
                            anchors {
                                left: parent.left
                                verticalCenter: parent.verticalCenter
                                leftMargin: 7
                            }

                            text:
                                "UNSCHEDULED // "
                                + String(root.unscheduled.length)
                            font.pixelSize: 8
                            color: Colors.orange
                        }
                    }

                    Repeater {
                        model: root.unscheduled

                        delegate: Rectangle {
                            id: unscheduledRow

                            required property var modelData

                            width: roadmapColumn.width
                            height: 36
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan

                            Row {
                                anchors {
                                    fill: parent
                                    margins: 5
                                }

                                GohuText {
                                    width: parent.width - 254
                                    anchors.verticalCenter: parent.verticalCenter
                                    text:
                                        root.projectService.itemTitle(
                                            unscheduledRow.modelData
                                        )
                                    font.pixelSize: 8
                                    color: Colors.white
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: 100
                                    anchors.verticalCenter: parent.verticalCenter
                                    horizontalAlignment: Text.AlignRight
                                    text: "NO DATE"
                                    font.pixelSize: 7
                                    color: Colors.orange
                                }

                                Row {
                                    width: 154
                                    height: parent.height
                                    spacing: 4

                                    RoadAction {
                                        width: 40
                                        anchors.verticalCenter: parent.verticalCenter
                                        label: "OPEN"
                                        enabledAction:
                                            !!root.projectService.itemUrl(
                                                unscheduledRow.modelData
                                            )
                                        onTriggered:
                                            root.openProjectItem(
                                                unscheduledRow.modelData
                                            )
                                    }

                                    RoadAction {
                                        width: 76
                                        anchors.verticalCenter: parent.verticalCenter
                                        label:
                                            root.itemActionArmed(
                                                "archive",
                                                unscheduledRow.modelData
                                            )
                                            ? "CONFIRM"
                                            : "ARCHIVE"
                                        enabledAction:
                                            !root.projectService.busy
                                            && !!root.projectService.itemId(
                                                unscheduledRow.modelData
                                            )
                                        onTriggered:
                                            root.armOrRunItem(
                                                "archive",
                                                unscheduledRow.modelData,
                                                function() {
                                                    root.projectService.archiveItem(
                                                        unscheduledRow.modelData,
                                                        true
                                                    );
                                                }
                                            )
                                    }

                                    RoadAction {
                                        width: 26
                                        anchors.verticalCenter: parent.verticalCenter
                                        label:
                                            root.itemActionArmed(
                                                "remove",
                                                unscheduledRow.modelData
                                            )
                                            ? "!"
                                            : "X"
                                        destructive: true
                                        enabledAction:
                                            !root.projectService.busy
                                            && !!root.projectService.itemId(
                                                unscheduledRow.modelData
                                            )
                                        onTriggered:
                                            root.armOrRunItem(
                                                "remove",
                                                unscheduledRow.modelData,
                                                function() {
                                                    root.projectService.removeItem(
                                                        unscheduledRow.modelData,
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
                        width: parent.width
                        visible: root.projectService.items.length === 0
                        text: "NO WORK ITEMS"
                        font.pixelSize: 9
                        color: Colors.white
                        opacity: 0.38
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }
}
