import QtQuick
import QtQuick.Effects
import qs.components

Item {
    id: root

    property var gitService: null
    property var historyService: null

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

    function historyRows() {
        const rows = [];
        if (!root.gitService)
            return rows;

        const revision = root.gitService.topologyRevision;
        const count = root.gitService.commitCount;

        for (let i = 0; i < count; ++i) {
            const row = root.gitService.commitAt(i);
            if (!row)
                continue;

            rows.push({
                sha: String(row.sha || ""),
                shortSha: String(row.shortSha || ""),
                parents: String(row.parents || ""),
                refsText: String(row.refsText || ""),
                epoch: Number(row.epoch || 0),
                author: String(row.author || ""),
                subject: String(row.subject || ""),
                lane: Number(row.lane || 0),
                isHead: Boolean(row.isHead)
            });
        }

        return rows;
    }


    component SectionLabel: GohuText {
        font.pixelSize: 12
        color: Colors.magenta
    }

    component OrangeLabel: GohuText {
        font.pixelSize: 10
        color: Colors.orange
    }

    component MiniButton: Rectangle {
        id: button

        property string label: ""
        property color accent: Colors.cyan
        property bool enabledAction: true
        signal triggered()

        height: 28
        color:
            mouse.pressed
            ? accent
            : mouse.containsMouse
            ? Colors.dark
            : Colors.black
        border.width: 1
        border.color: accent
        opacity: enabledAction ? 1.0 : 0.28

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 9
            color:
                mouse.pressed
                ? Colors.black
                : mouse.containsMouse
                ? Colors.orange
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

    Column {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            width: parent.width
            height: 66
            color: Colors.dark
            border.width: 1
            border.color: Colors.magenta

            Row {
                anchors {
                    fill: parent
                    margins: 9
                }
                spacing: 12

                Column {
                    width: parent.width - 220
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    SectionLabel {
                        text: "COMMIT HISTORY"
                    }

                    GohuText {
                        width: parent.width
                        text:
                            root.gitService
                            ? (
                                String(root.gitService.branch || "DETACHED")
                                + "  //  "
                                + String(root.gitService.commitCount || 0)
                                + " RECENT COMMITS"
                              )
                            : "NO REPOSITORY"
                        font.pixelSize: 9
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }
                }

                Rectangle {
                    width: 108
                    height: 28
                    anchors.verticalCenter: parent.verticalCenter
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.orange

                    GohuText {
                        anchors.centerIn: parent
                        text:
                            root.gitService
                            ? "HEAD " + String(root.gitService.head || "").slice(0, 8)
                            : "NO HEAD"
                        font.pixelSize: 8
                        color: Colors.orange
                    }
                }

                MiniButton {
                    width: 88
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.gitService
                        && root.gitService.refreshing
                        ? "READING"
                        : "REFRESH"
                    accent: Colors.cyan
                    enabledAction:
                        root.gitService
                        && !root.gitService.refreshing
                    onTriggered: root.gitService.refresh()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 76
            spacing: 10

            Rectangle {
                width: 526
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Flickable {
                    id: historyFlick

                    anchors {
                        fill: parent
                        margins: 8
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
                            model: root.historyRows()

                            Rectangle {
                                id: commitRow

                                required property int index
                                required property var modelData

                                width: historyColumn.width
                                height: 48
                                color:
                                    commitMouse.containsMouse
                                    || (
                                        root.historyService
                                        && root.historyService.selectedSha
                                           === String(model.sha || "")
                                    )
                                    ? Colors.black
                                    : "transparent"
                                border.width:
                                    model.isHead
                                    || (
                                        root.historyService
                                        && root.historyService.selectedSha
                                           === String(model.sha || "")
                                    )
                                    ? 1 : 0
                                border.color:
                                    model.isHead
                                    ? Colors.magenta
                                    : Colors.orange

                                Item {
                                    id: graphLane
                                    width: 66
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
                                                Number(commitRow.modelData.lane || 0)
                                              ) * 7
                                        color: Colors.cyan
                                        opacity: 0.46
                                    }

                                    Rectangle {
                                        width: commitRow.modelData.isHead ? 9 : 7
                                        height: width
                                        radius: width / 2
                                        anchors.verticalCenter: parent.verticalCenter
                                        x:
                                            8
                                            + Math.min(
                                                6,
                                                Number(commitRow.modelData.lane || 0)
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

                                        RectangularShadow {
                                            anchors.fill: parent
                                            z: -1
                                            spread: 2
                                            opacity:
                                                commitRow.modelData.isHead
                                                ? 0.54 : 0.24
                                            color:
                                                commitRow.modelData.isHead
                                                ? Colors.magenta
                                                : Colors.cyan
                                        }
                                    }
                                }

                                Column {
                                    anchors {
                                        left: graphLane.right
                                        right: parent.right
                                        verticalCenter: parent.verticalCenter
                                        leftMargin: 4
                                        rightMargin: 7
                                    }
                                    spacing: 2

                                    Row {
                                        width: parent.width
                                        height: 16
                                        spacing: 8

                                        GohuText {
                                            width: 70
                                            text:
                                                String(
                                                    commitRow.modelData.shortSha || ""
                                                )
                                            font.pixelSize: 8
                                            color:
                                                commitRow.modelData.isHead
                                                ? Colors.magenta
                                                : Colors.orange
                                        }

                                        GohuText {
                                            width: parent.width - 78
                                            text:
                                                String(
                                                    commitRow.modelData.refsText || ""
                                                )
                                            font.pixelSize: 7
                                            color: Colors.cyan
                                            elide: Text.ElideRight
                                        }
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            String(
                                                commitRow.modelData.subject || ""
                                            )
                                        font.pixelSize: 9
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }

                                    GohuText {
                                        width: parent.width
                                        text:
                                            String(
                                                commitRow.modelData.author || ""
                                            )
                                            + "  //  "
                                            + root.dateLabel(
                                                commitRow.modelData.epoch
                                              )
                                        font.pixelSize: 7
                                        color: Colors.white
                                        opacity: 0.52
                                        elide: Text.ElideRight
                                    }
                                }

                                MouseArea {
                                    id: commitMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked:
                                        root.historyService.showCommit(
                                            commitRow.modelData.sha
                                        )
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width - 536
                height: parent.height
                color: Colors.black
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors {
                        fill: parent
                        margins: 8
                    }
                    spacing: 6

                    Row {
                        width: parent.width
                        height: 22

                        OrangeLabel {
                            width: parent.width - 120
                            text:
                                root.historyService
                                && root.historyService.selectedSha
                                ? "COMMIT // "
                                  + root.historyService.selectedSha.slice(0, 10)
                                : "COMMIT DETAIL"
                        }

                        GohuText {
                            width: 120
                            horizontalAlignment: Text.AlignRight
                            text:
                                root.historyService
                                && root.historyService.detailBusy
                                ? "READING"
                                : "LOCAL HISTORY"
                            font.pixelSize: 8
                            color: Colors.cyan
                        }
                    }

                    Flickable {
                        width: parent.width
                        height: parent.height - 28
                        clip: true
                        contentWidth: width
                        contentHeight: detailText.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds

                        GohuText {
                            id: detailText
                            width: parent.width
                            text:
                                root.historyService
                                ? root.historyService.detailText
                                : "NO HISTORY SERVICE"
                            font.pixelSize: 9
                            color:
                                root.historyService
                                && root.historyService.lastError
                                ? Colors.red
                                : Colors.white
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }
        }
    }
}
