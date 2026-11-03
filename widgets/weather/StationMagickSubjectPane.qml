import QtQuick
import "../../components"
import "StationMagickSubjectPanelPolicy.js" as MagickPolicy

// MAGICK G1 is a labeled interpretive workspace, not a calculation engine.
// Existing SKY sections are mounted at their exact COSMOS source routes.
// Neither this pane nor its policy owns requests, saved readings or journals.
Rectangle {
    id: magickPane
    color: Colors.black

    property string subjectRoute: ""
    property var weatherService: null
    property real runtimeNowMs: Date.now()

    readonly property string kind: MagickPolicy.kindForRoute(subjectRoute)
    readonly property string primaryObservation:
        MagickPolicy.sourceFor(subjectRoute)
    readonly property string secondaryObservation:
        MagickPolicy.secondarySourceFor(subjectRoute)

    Column {
        id: contextHeader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 10
        spacing: 7

        GohuText {
            width: parent.width
            text: MagickPolicy.titleFor(magickPane.subjectRoute)
            color: Colors.magenta
            font.pixelSize: 17
            elide: Text.ElideRight
        }

        QuietText {
            width: parent.width
            font.pixelSize: 10
            wrapMode: Text.WordWrap
            color: Colors.yellow
            text: magickPane.primaryObservation !== ""
                  ? "OBSERVATION // EXISTING COSMOS DATA   |   INTERPRETATION // NOT CONNECTED"
                  : "INTERPRETIVE WORKSPACE // NOT IMPLEMENTED   |   NO DATA OR READING GENERATED"
        }

        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 10
            text: MagickPolicy.noteFor(magickPane.subjectRoute)
        }
    }

    Rectangle {
        id: observationFrame
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: contextHeader.bottom
        anchors.topMargin: 9
        anchors.bottom: parent.bottom
        anchors.leftMargin: 13
        anchors.rightMargin: 13
        anchors.bottomMargin: 8
        color: Colors.black
        border.width: 1
        border.color: Colors.magenta
        clip: true

        Loader {
            anchors.fill: parent
            anchors.margins: 4
            active: magickPane.visible && magickPane.kind === "reference"
            sourceComponent: magickPane.secondaryObservation !== ""
                             ? overviewReference
                             : magickPane.primaryObservation !== ""
                               ? singleReference : unimplemented
        }
    }

    Component {
        id: singleReference
        StationSky {
            subjectRoute: magickPane.primaryObservation
            weatherService: magickPane.weatherService
            runtimeNowMs: magickPane.runtimeNowMs
        }
    }

    // One lunar instrument and one solar/twilight instrument in a single
    // MAGICK overview. No second Moon service is active for the solar bay.
    Component {
        id: overviewReference
        Item {
            id: referenceOverview

            Rectangle {
                id: lunarBay
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: Math.max(0,(referenceOverview.height - 8) / 2)
                color: Colors.black
                clip: true

                StationSky {
                    anchors.fill: parent
                    subjectRoute: magickPane.primaryObservation
                    weatherService: magickPane.weatherService
                    runtimeNowMs: magickPane.runtimeNowMs
                }
            }

            Rectangle {
                anchors.top: lunarBay.bottom
                anchors.topMargin: 8
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                color: Colors.black
                clip: true

                StationSky {
                    anchors.fill: parent
                    subjectRoute: magickPane.secondaryObservation
                    weatherService: magickPane.weatherService
                    runtimeNowMs: magickPane.runtimeNowMs
                }
            }
        }
    }

    Component {
        id: unimplemented
        Item {
            Column {
                anchors.centerIn: parent
                width: Math.max(0,parent.width - 36)
                spacing: 15

                GohuText {
                    width: parent.width
                    font.pixelSize: 17
                    text: "NO CONNECTED INSTRUMENT"
                    color: Colors.orange
                    horizontalAlignment: Text.AlignHCenter
                }

                QuietText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                    text: "THIS DESTINATION IS RESERVED. IT DOES NOT GENERATE ASTROLOGY, TAROT, SYMBOLIC CORRESPONDENCES OR PRIVATE JOURNAL ENTRIES."
                    horizontalAlignment: Text.AlignHCenter
                }

                QuietText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    color: Colors.magenta
                    text: "SCIENTIFIC SKY DATA REMAINS AVAILABLE UNDER COSMOS."
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }
}
