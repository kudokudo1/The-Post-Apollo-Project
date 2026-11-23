import QtQuick

// Shared in-widget provider/service diagnostics, extracted from Weather M6c.
// The host supplies its EXISTING service snapshots. This component never
// polls, launches, fetches, writes, or creates an external window.
Rectangle {
    id: diagnosticsPane

    property string heading: "PROVIDER HEALTH // DIAGNOSTICS"
    property string displayedState: "WAITING"
    property string providerLabel: "NONE"
    property string currentAge: "--"
    property string locationLabel: ""
    property bool showLocation: true
    property var serviceRows: []
    property string reason: "NO SERVICE DATA"
    property string reasonHeading: "REASON // CURRENT ROUTING"
    property string footnote: "READ ONLY // NO EXTRA FETCHES FROM THIS PANEL."
    property string ageHeading: "LAST PROVIDER SUCCESS // "

    signal closeRequested()

    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    clip: true

    function statusColor(state) {
        const value = String(state || "").toUpperCase();
        if (value === "LIVE" || value === "READY") return Colors.cyan;
        if (value === "READING") return Colors.orange;
        if (value === "CACHE" || value === "FALLBACK") return Colors.yellow;
        if (value === "CACHE STALE" || value === "FALLBACK STALE") return Colors.orange;
        if (value === "SNAPSHOT" || value === "MANUAL" || value === "LOCAL")
            return Colors.cyan;
        if (value === "IDLE" || value === "WAITING"
                || value === "NO SELECTED PLACE" || value === "NO FEED")
            return Colors.white;
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
                    width: Math.max(0, parent.width - 44)
                    anchors.verticalCenter: parent.verticalCenter
                    text: diagnosticsPane.heading
                    font.pixelSize: 12
                    color: Colors.magenta
                    textFormat: Text.PlainText
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
                text: "DISPLAYED // " + diagnosticsPane.displayedState
                color: diagnosticsPane.statusColor(diagnosticsPane.displayedState)
                font.pixelSize: 12
                textFormat: Text.PlainText
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                textFormat: Text.PlainText
                text: "ORIGIN // " + diagnosticsPane.providerLabel
                      + "   LAST READING // " + diagnosticsPane.currentAge
            }
            QuietText {
                width: parent.width
                visible: diagnosticsPane.showLocation
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                font.pixelSize: 10
                text: "LOCATION // " + (diagnosticsPane.locationLabel || "UNAVAILABLE")
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
                opacity: 0.45
            }

            Repeater {
                model: Array.isArray(diagnosticsPane.serviceRows)
                       ? diagnosticsPane.serviceRows : []
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
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: parent.width * 0.44
                                text: sourceRow.modelData.state
                                color: diagnosticsPane.statusColor(
                                           sourceRow.modelData.state)
                                font.pixelSize: 10
                                textFormat: Text.PlainText
                                elide: Text.ElideRight
                            }
                        }
                        QuietText {
                            width: parent.width
                            font.pixelSize: 9
                            textFormat: Text.PlainText
                            text: diagnosticsPane.ageHeading
                                  + sourceRow.modelData.age
                        }
                    }
                }
            }

            GohuText {
                width: parent.width
                text: diagnosticsPane.reasonHeading
                color: Colors.orange
                font.pixelSize: 10
                textFormat: Text.PlainText
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                font.pixelSize: 10
                text: diagnosticsPane.reason
            }
            SecondaryText {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                font.pixelSize: 9
                text: diagnosticsPane.footnote
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
