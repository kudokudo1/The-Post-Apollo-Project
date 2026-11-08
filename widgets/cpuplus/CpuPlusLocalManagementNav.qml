import QtQuick
import "../../components"

// Compact navigation inside the EXISTING CPU++ left bay. None of these
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
            text: "SOCIAL // LOCAL MANAGEMENT"
            color: Colors.magenta
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        QuietText {
            width: parent.width
            text: "EDIT SAVED RECORDS // DOES NOT SWITCH LOGIN OR COMPANY ACCESS"
            color: Colors.orange
            font.pixelSize: 9
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
                    height: 33
                    label: modelData.title
                    labelPixelSize: 9
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
