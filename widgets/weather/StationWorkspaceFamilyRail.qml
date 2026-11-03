import QtQuick
import "../../components"
import "StationWorkspaceNavigationPolicy.js" as Workspace

// W1r // AppControl-style main family buttons in the original 160px
// Station left rail. Routes belong to StationSubjectNavigator, not here.
Column {
    id: familyRail
    property var navigator: null
    spacing: 6

    Repeater {
        model: Workspace.FAMILIES
        delegate: ModeButton {
            required property var modelData
            width: familyRail.width
            height: 48
            textOnly: true
            horizontalContent: true
            bordered: false
            labelFontSize: 17
            labelText: modelData.label
            selected: familyRail.navigator
                      && Workspace.familyFor(familyRail.navigator.currentPath)
                         === modelData.id
            onTriggered: {
                if (familyRail.navigator)
                    familyRail.navigator.chooseRoute(modelData.landing);
            }
        }
    }
}
