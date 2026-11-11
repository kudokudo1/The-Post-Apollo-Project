import QtQuick
import "../components"

// Presentation-only Brave tab counts: no browser access, identity claims,
// persistence, or SAVE/RESTORE operations. Caller must supply real counts.
Row {
    id: pattern
    property var counts: []
    property color labelColor: Colors.cyan
    property color separatorColor: Colors.white
    property color numberColor: Colors.orange
    property int textSize: 11
    spacing: 7
    height: 20

    GohuText {
        text: "TABS"
        color: pattern.labelColor
        font.pixelSize: pattern.textSize
        anchors.verticalCenter: parent.verticalCenter
    }

    Repeater {
        model: Array.isArray(pattern.counts) ? pattern.counts.length : 0
        delegate: Row {
            spacing: 7
            height: pattern.height
            GohuText {
                text: "//"
                color: pattern.separatorColor
                font.pixelSize: pattern.textSize
                anchors.verticalCenter: parent.verticalCenter
            }
            GohuText {
                text: String(pattern.counts[index])
                color: pattern.numberColor
                font.pixelSize: pattern.textSize
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
