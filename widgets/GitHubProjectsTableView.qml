import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var projectService

    readonly property int titleWidth: 250
    readonly property int typeWidth: 70
    readonly property int repoWidth: 190
    readonly property int statusWidth: 105
    readonly property int priorityWidth: 90
    readonly property int iterationWidth: 110
    readonly property int dateWidth: 92
    readonly property int totalWidth:
        titleWidth
        + typeWidth
        + repoWidth
        + statusWidth
        + priorityWidth
        + iterationWidth
        + dateWidth * 2

    component Cell: Rectangle {
        id: cell

        property string value: ""
        property bool header: false
        property color accent: Colors.cyan

        height: header ? 28 : 34
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
            font.pixelSize: cell.header ? 8 : 7
            color: cell.header ? cell.accent : Colors.white
            opacity: cell.value ? 1.0 : 0.34
            elide: Text.ElideRight
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
                font.pixelSize: 9
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
                font.pixelSize: 7
                color: Colors.cyan
                opacity: 0.68
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
                        }
                    }

                    GohuText {
                        width: tableScroll.width
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
