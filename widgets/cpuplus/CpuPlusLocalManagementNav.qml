import QtQuick
import "../../components"

// Compact category filters in the EXISTING CPU++ middle selector bay. None of these
// local-editing sections switches a verified company or provider account.
Item {
    id: nav
    property string section: "IDS"
    signal sectionRequested(string section)
    implicitHeight: navigation.implicitHeight

    readonly property var tabs: [
        {id:"IDS", title:"IDS / PROFILES"},
        {id:"ORGANIZATIONS", title:"ORGS / BRANCHES"},
        {id:"STRUCTURE", title:"STRUCTURE / UNITS"},
        {id:"PORTFOLIOS", title:"PORTFOLIOS"}
    ]

    Column {
        id: navigation
        width: parent.width
        spacing: 7

        GohuText {
            width: parent.width
            text: "FILTER // LOCAL RECORDS"
            color: Colors.cyan
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Grid {
            width: parent.width
            columns: 2
            spacing: 5
            Repeater {
                model: nav.tabs
                delegate: ActionButton {
                    required property var modelData
                    width: Math.floor((navigation.width - 5) / 2)
                    height: 31
                    label: modelData.title
                    labelPixelSize: 8
                    selected: nav.section === modelData.id
                    accentColor: selected ? Colors.magenta : Colors.cyan
                    onClicked: nav.sectionRequested(modelData.id)
                }
            }
        }
        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
        }
    }
}
