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
    // One source owned by the persistent SUBJECTS navigator, not this pane.
    property var celestialSource: null
    readonly property bool showCelestial:
        MagickPolicy.visualForRoute(subjectRoute)
    // Supplied by the existing Station root; no independent clock.
    property real runtimeNowMs: 0

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
            text: magickPane.showCelestial
                  ? "ASTRONOMY // M4 JPL POSITION SERIES   |   INTERPRETATION // NOT CONNECTED"
                  : magickPane.primaryObservation !== ""
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
            sourceComponent: magickPane.showCelestial
                             ? celestialReference
                             : magickPane.secondaryObservation !== ""
                             ? overviewReference
                             : magickPane.primaryObservation !== ""
                               ? singleReference : unimplemented
        }
    }

    // M5b // The visual host is an on-demand consumer of the SAME
    // source verified M4 result in the owning StationSubjectNavigator.
    // No timer, second Process or fallback invented orbital coordinates.
    Component {
        id: celestialReference
        Item {
            Flickable {
                anchors.fill: parent
                clip: true
                contentWidth: width
                contentHeight: Math.max(height, 582)
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    width: parent.width
                    spacing: 6

                    Row {
                        width: parent.width
                        height: 30
                        spacing: 8
                        QuietText {
                            width: Math.max(0,parent.width-140)
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                            color: magickPane.celestialSource
                                   && magickPane.celestialSource.ready
                                   ? Colors.cyan : Colors.orange
                            text: magickPane.celestialSource
                                  ? magickPane.celestialSource.statusText
                                  : "JPL CALCULATION OWNER UNAVAILABLE"
                        }
                        ActionButton {
                            width: 132
                            height: 28
                            label: magickPane.celestialSource
                                   && magickPane.celestialSource.loading
                                   ? "CALCULATING" : "CALCULATE"
                            labelPixelSize: 10
                            accentColor: Colors.magenta
                            available: !!magickPane.celestialSource
                                       && magickPane.celestialSource.active
                                       && magickPane.celestialSource.configured
                                       && !magickPane.celestialSource.loading
                            onClicked: magickPane.celestialSource.refresh()
                        }
                    }
                    // M5c // Date and body controls work on the root-owned
                    // service only; changing options invalidates data until
                    // the user explicitly presses CALCULATE again.
                    Row {
                        width: parent.width
                        height: 27
                        spacing: 6
                        ActionButton {
                            width: 83
                            height: 26
                            label: "◀ 30D"
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            available: !!magickPane.celestialSource
                                       && !magickPane.celestialSource.loading
                            onClicked: magickPane.celestialSource.shiftDate(-30)
                        }
                        QuietText {
                            width: Math.max(20,parent.width-83-83-82-18)
                            height: 27
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                            color: Colors.white
                            font.pixelSize: 10
                            text: magickPane.celestialSource
                                  ? "UTC " + magickPane.celestialSource.targetDayUtc
                                  : "UTC // SOURCE OFFLINE"
                        }
                        ActionButton {
                            width: 82
                            height: 26
                            label: "TODAY"
                            labelPixelSize: 10
                            accentColor: Colors.orange
                            available: !!magickPane.celestialSource
                                       && !magickPane.celestialSource.loading
                            onClicked: magickPane.celestialSource.returnToToday()
                        }
                        ActionButton {
                            width: 83
                            height: 26
                            label: "30D ▶"
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            available: !!magickPane.celestialSource
                                       && !magickPane.celestialSource.loading
                            onClicked: magickPane.celestialSource.shiftDate(30)
                        }
                    }
                    Row {
                        width: parent.width
                        height: 27
                        spacing: 6
                        ActionButton {
                            width: 81
                            height: 26
                            label: "◀ PAIR"
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            available: !!magickPane.celestialSource
                                       && !magickPane.celestialSource.loading
                            onClicked: magickPane.celestialSource.cyclePair(-1)
                        }
                        QuietText {
                            width: Math.max(20,parent.width-81-81-87-18)
                            height: 27
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                            color: Colors.magenta
                            font.pixelSize: 10
                            text: magickPane.celestialSource
                                  ? magickPane.celestialSource.pairLabel
                                  : "NO PAIR"
                        }
                        ActionButton {
                            width: 81
                            height: 26
                            label: "PAIR ▶"
                            labelPixelSize: 10
                            accentColor: Colors.cyan
                            available: !!magickPane.celestialSource
                                       && !magickPane.celestialSource.loading
                            onClicked: magickPane.celestialSource.cyclePair(1)
                        }
                        ActionButton {
                            width: 87
                            height: 26
                            label: magickPane.celestialSource
                                   ? "SPAN " + magickPane.celestialSource.spanDays + "D"
                                   : "SPAN --"
                            labelPixelSize: 9
                            accentColor: Colors.yellow
                            available: !!magickPane.celestialSource
                                       && !magickPane.celestialSource.loading
                            onClicked: magickPane.celestialSource.cycleSpan()
                        }
                    }
                    StationMagickCelestialInstrument {
                        width: parent.width
                        height: 466
                        visualData: magickPane.celestialSource
                                    && magickPane.celestialSource.ready
                                    ? magickPane.celestialSource.visualData
                                    : null
                        mode: magickPane.subjectRoute === "magick/astrology/aspects"
                              ? "aspects"
                              : magickPane.subjectRoute === "magick/astrology/retrogrades"
                              ? "motion" : "wheel"
                    }
                }
            }
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
