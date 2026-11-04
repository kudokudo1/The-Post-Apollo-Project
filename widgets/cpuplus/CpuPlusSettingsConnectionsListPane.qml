import QtQuick
import "../../components"
import qs.services.connections

// CPU++ center target bay. Selection is local UI state, not provider login.
Item {
    id: selector
    property string selectedId: "social"
    signal providerSelected(string providerId)

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, column.y + column.implicitHeight + 12)

        Column {
            id: column
            x: 3
            y: 7
            width: Math.max(0, scroll.width - 9)
            spacing: 5

            QuietText {
                width: parent.width
                text: "SELECT SERVICE // INSPECT ACCESS"
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: ConnectionsRegistry.rows

                delegate: ActionButton {
                    id: sourceChoice
                    required property var modelData
                    width: column.width
                    height: 53
                    label: ""
                    selected: selector.selectedId === modelData.id
                    accentColor: selected ? Colors.magenta
                                 : modelData.accent === "orange" ? Colors.orange
                                 : modelData.accent === "yellow" ? Colors.yellow
                                 : Colors.cyan
                    onClicked: selector.providerSelected(modelData.id)

                    Column {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 4
                        GohuText {
                            width: parent.width
                            text: sourceChoice.modelData.title
                            color: sourceChoice.selected ? Colors.magenta : Colors.white
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            text: sourceChoice.modelData.status
                            font.pixelSize: 9
                            color: sourceChoice.modelData.accent === "orange" ? Colors.orange
                                   : sourceChoice.modelData.accent === "yellow" ? Colors.yellow
                                   : Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
