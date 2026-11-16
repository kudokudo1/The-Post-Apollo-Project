import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// W23 // Share the exact C44 title/tab/divider vertical grammar.
// Keep W22's 8px optical horizontal gaps and real route ownership.
Item {
    id: overviewRail
    objectName: "station-w21-shared-overview-rail"
    property var routes: []
    property string titleText: ""
    property bool condensed: false
    readonly property real buttonGap: HeaderGeometry.tabSpacing + 4
    readonly property real dividerGap: HeaderGeometry.tabsToRule
    signal routeRequested(string path)
    readonly property alias buttonRepeater: actionRepeater
    readonly property alias titleItem: railHeading
    readonly property alias dividerItem: rule
    // Normal: 18px title + 4px gap + 27px tabs + 5px gap + 2px rule.
    // Compact: 24px tabs + 5px gap + 2px rule (no title).
    height: visible ? (condensed ? 31
        : HeaderGeometry.titleHeight + HeaderGeometry.titleToTabs
          + HeaderGeometry.tabHeight + dividerGap
          + HeaderGeometry.ruleHeight) : 0

    GohuText {
        id: railHeading
        objectName: "station-w22-c44-overview-title"
        visible: !overviewRail.condensed
        x: 0
        y: 0
        width: parent.width
        height: visible ? HeaderGeometry.titleHeight : 0
        verticalAlignment: Text.AlignVCenter
        text: overviewRail.titleText
        font.pixelSize: 12
        color: Colors.magenta
        elide: Text.ElideRight
    }

    Row {
        id: longButtons
        objectName: "station-w21-full-width-buttons"
        anchors.left: parent.left
        anchors.right: parent.right
        y: overviewRail.condensed ? 0
           : HeaderGeometry.titleHeight + HeaderGeometry.titleToTabs
        height: overviewRail.condensed ? 24 : HeaderGeometry.tabHeight
        spacing: overviewRail.buttonGap
        Repeater {
            id: actionRepeater
            model: overviewRail.routes
            delegate: ActionButton {
                required property var modelData
                objectName: "station-w21-overview-route"
                width: Math.max(1,(longButtons.width -
                       (overviewRail.routes.length-1)*overviewRail.buttonGap)
                       /Math.max(1,overviewRail.routes.length))
                height: longButtons.height
                label: modelData.label
                labelPixelSize: 10
                contentPadding: 1
                accentColor: Colors.cyan
                onClicked: overviewRail.routeRequested(modelData.path)
            }
        }
    }
    Rectangle {
        id: rule
        objectName: "station-w21-overview-divider"
        anchors.left: longButtons.left
        anchors.right: longButtons.right
        y: longButtons.y + longButtons.height + overviewRail.dividerGap
        height: HeaderGeometry.ruleHeight
        color: Colors.cyan
    }
}
