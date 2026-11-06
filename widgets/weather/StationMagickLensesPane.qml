import QtQuick
import "../../components"

// M30-F // Replaces the duplicate solar-hours bottom button with a
// source-honest cross-domain lens selector. No traditional correspondences,
// belief claims, personal journal writes or independent astronomy collector.
Rectangle {
    id: lenses
    color: Colors.black
    clip: true

    property var celestialSource: null
    signal routeRequested(string path)
    // M6e // Preserve the complete original LENSES landing.
    property string lensView: "index"

    readonly property var entries: [
        {
            title:"ASTRONOMICAL",
            description:"JPL POSITIONS / MOTION / ASPECTS",
            status:celestialSource && celestialSource.ready
                   ? "JPL LOADED" : "ON-DEMAND / NOT LOADED",
            path:"magick/astrology/charts",
            color:Colors.cyan
        },
        {
            title:"LUNAR + SOLAR",
            description:"MOON CYCLES / SOLAR WINDOWS",
            status:"OBSERVATION / MODEL",
            path:"magick/lunar-solar/moon",
            color:Colors.orange
        },
        {
            title:"SYMBOLIC REFERENCES",
            description:"CULTURAL CORRESPONDENCES / TEXTS",
            status:"AGRIPPA INDEX / READ-ONLY",
            path:"magick/grimoire/references",
            color:Colors.magenta
        }
    ]

    Column {
        anchors.fill: parent
        anchors.margins: 7
        spacing: 5
        visible: lenses.lensView==="index"

        Row {
            width: parent.width
            height: 19
            spacing: 5
            GohuText {
                width: 145
                font.pixelSize: 11
                color: Colors.magenta
                text: "MAGICK // LENSES"
            }
            QuietText {
                width: Math.max(0,parent.width-235)
                font.pixelSize: 9
                color: Colors.yellow
                text: "INTERPRETATION NOT CONNECTED"
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
            }
            ActionButton {
                width: 78
                height: 19
                label: "AGRIPPA"
                labelPixelSize: 9
                accentColor: Colors.magenta
                onClicked: lenses.lensView="agrippa"
            }
        }

        Repeater {
            model: lenses.entries
            delegate: Rectangle {
                required property var modelData
                width: parent.width
                height: 53
                color: Colors.dark
                border.width: 1
                border.color: modelData.color
                clip: true

                Row {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 7
                    Column {
                        width: Math.max(0,parent.width-68)
                        spacing: 2
                        GohuText {
                            width: parent.width
                            font.pixelSize: 10
                            text: modelData.title
                            color: modelData.color
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.description
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            font.pixelSize: 8
                            text: modelData.status
                            color: Colors.yellow
                            elide: Text.ElideRight
                        }
                    }
                    ActionButton {
                        width: 61
                        height: 26
                        anchors.verticalCenter: parent.verticalCenter
                        label: "OPEN"
                        labelPixelSize: 9
                        accentColor: modelData.color
                        onClicked: lenses.routeRequested(modelData.path)
                    }
                }
            }
        }
        QuietText {
            width: parent.width
            font.pixelSize: 8
            color: Colors.orange
            text: "SCIENTIFIC OBSERVATIONS ARE NOT EVIDENCE OF SYMBOLIC CAUSATION"
            elide: Text.ElideRight
        }
    }
    // Source-labelled viewer nested within LENSES. The separate GRIMOIRE
    // reference route is still pending and must not be silently replaced.
    StationMagickAgrippaCorrespondencesPane {
        anchors.fill: parent
        visible: lenses.lensView==="agrippa"
        onBackRequested: lenses.lensView="index"
    }
}
