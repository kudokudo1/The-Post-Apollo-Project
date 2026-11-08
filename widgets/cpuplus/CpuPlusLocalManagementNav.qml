import QtQuick
import "../../components"

// Compact category filters in the EXISTING CPU++ middle selector bay. None of these
// local-editing sections switches a verified company or provider account.
Item {
    id: nav
    property string section: "IDS"
    // Secondary edit filters stay with the category filters in the MIDDLE bay.
    property string task: "EDITOR"
    signal sectionRequested(string section)
    signal taskRequested(string task)
    readonly property var sectionTasks: section === "ORGANIZATIONS" ? [
        {id:"EDITOR", title:"EDIT ORGS"},
        {id:"BRANCH_LOCATIONS", title:"BRANCH LOCATIONS"}
    ] : section === "STRUCTURE" ? [
        {id:"EDITOR", title:"EDIT UNITS"},
        {id:"UNIT_LOCATIONS", title:"UNIT LOCATIONS"},
        {id:"REPORTING", title:"REPORTING"}
    ] : []
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
        Column {
            width: parent.width
            spacing: 6
            visible: nav.sectionTasks.length > 0
            GohuText {
                width: parent.width
                text: "EDIT // LOCAL RELATIONSHIPS"
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Grid {
                width: parent.width
                columns: 2
                spacing: 5
                Repeater {
                    model: nav.sectionTasks
                    delegate: ActionButton {
                        required property var modelData
                        width: Math.floor((navigation.width - 5) / 2)
                        height: 31
                        label: modelData.title
                        labelPixelSize: 8
                        selected: nav.task === modelData.id
                        accentColor: selected ? Colors.magenta : Colors.cyan
                        onClicked: nav.taskRequested(modelData.id)
                    }
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
