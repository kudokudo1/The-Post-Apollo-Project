import QtQuick
import "../../components"

// M6c read-only inspection of the EXISTING one WeatherService.
// No timer, process, network request or cache write.
Rectangle {
    id: diagnosticsPane
    property var snapshot: null
    signal closeRequested()
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    clip: true

    readonly property var rows:
        snapshot ? [snapshot.primary, snapshot.fallback, snapshot.aqi] : []

    function statusColor(state) {
        const value = String(state || "");
        if (value === "LIVE") return Colors.cyan;
        if (value === "READING") return Colors.orange;
        if (value === "CACHE" || value === "FALLBACK")
            return Colors.yellow;
        if (value === "CACHE STALE") return Colors.orange;
        if (value === "IDLE" || value === "WAITING"
                || value === "NO SELECTED PLACE") return Colors.white;
        return Colors.red;
    }

    Flickable {
        id: diagnosticsScroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, detailBody.y + detailBody.implicitHeight + 16)

        Column {
            id: detailBody
            x: 12
            y: 12
            width: Math.max(0, diagnosticsScroll.width - 24)
            spacing: 11

        Row {
            width: parent.width
            height: 34
            spacing: 8

            GohuText {
                width: parent.width - 44
                anchors.verticalCenter: parent.verticalCenter
                text: "PROVIDER HEALTH // DIAGNOSTICS"
                font.pixelSize: 12
                color: Colors.magenta
                elide: Text.ElideRight
            }
            ActionButton {
                width: 34
                height: 30
                label: "×"
                labelPixelSize: 19
                accentColor: Colors.red
                onLeftClicked: diagnosticsPane.closeRequested()
            }
        }

        Rectangle {
            width: parent.width
            height: 2
            color: Colors.cyan
        }

        GohuText {
            width: parent.width
            text: diagnosticsPane.snapshot
                  ? "DISPLAYED // " + diagnosticsPane.snapshot.currentState
                  : "DISPLAYED // NO SERVICE"
            color: diagnosticsPane.snapshot
                   ? diagnosticsPane.statusColor(
                         diagnosticsPane.snapshot.currentState)
                   : Colors.white
            font.pixelSize: 12
        }
        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 10
            text: diagnosticsPane.snapshot
                  ? "ORIGIN // " + diagnosticsPane.snapshot.providerLabel
                    + "   LAST READING // "
                    + diagnosticsPane.snapshot.currentAge
                  : "NO WEATHER SERVICE ATTACHED"
        }
        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            font.pixelSize: 10
            text: diagnosticsPane.snapshot
                  ? "LOCATION // " + diagnosticsPane.snapshot.location
                  : "LOCATION // UNAVAILABLE"
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Colors.cyan
            opacity: 0.45
        }

        Repeater {
            model: diagnosticsPane.rows
            delegate: Rectangle {
                id: sourceRow
                required property var modelData
                width: detailBody.width
                height: 56
                color: Colors.dark
                border.width: 1
                border.color:
                    diagnosticsPane.statusColor(sourceRow.modelData.state)

                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6

                    Row {
                        width: parent.width
                        spacing: 6
                        GohuText {
                            width: parent.width * 0.53
                            text: sourceRow.modelData.label
                            color: Colors.white
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width * 0.44
                            text: sourceRow.modelData.state
                            color: diagnosticsPane.statusColor(
                                sourceRow.modelData.state)
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                    }
                    QuietText {
                        width: parent.width
                        font.pixelSize: 9
                        text: "LAST PROVIDER SUCCESS // "
                              + sourceRow.modelData.age
                    }
                }
            }
        }

        GohuText {
            width: parent.width
            text: "REASON // CURRENT ROUTING"
            color: Colors.orange
            font.pixelSize: 10
        }
        QuietText {
            width: parent.width
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            font.pixelSize: 10
            text: diagnosticsPane.snapshot
                  ? diagnosticsPane.snapshot.reason
                  : "NO SERVICE DATA"
        }

        SecondaryText {
            width: parent.width
            wrapMode: Text.WordWrap
            font.pixelSize: 9
            text: "READ ONLY // PROVIDER STATUS IS SESSION-LOCAL. "
                  + "CACHE AGE COMES FROM THE SAVED SAMPLE. "
                  + "NO EXTRA FETCHES FROM THIS PANEL."
        }
        }
    }

    NeonScrollBar {
        flickable: diagnosticsScroll
        handleStyle: "star"
        geometryHost: diagnosticsPane
        visible: scrollable
    }
}
