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

    // A deferred gutter update avoids a binding cycle:
    // column width -> wrapped height -> scrollbar visibility -> column width.
    // Reserve width only for a genuinely overflowing content viewport.
    property bool railSpaceReserved: false
    function updateRailSpace() {
        const needsRail = diagnosticsScroll.contentHeight
                          > diagnosticsScroll.height + diagnosticsRail.scrollThreshold;
        if (railSpaceReserved !== needsRail)
            railSpaceReserved = needsRail;
    }

    signal closeRequested()

    // Fully opaque local backing. The host separately dims/blocks the work
    // area below this in-widget modal; no transparency is inherited here.
    color: "#110319"
    opacity: 1.0
    border.width: 1
    border.color: Colors.magenta
    clip: true

    // Catch unused pointer events before they reach interactive widgets below
    // the popup. The Flickable and its real close/scroll controls paint above
    // this shield and keep their own input handlers.
    MouseArea {
        id: diagnosticsPointerShield
        anchors.fill: parent
        z: 0
        acceptedButtons: Qt.AllButtons
        preventStealing: true
        onPressed: function(mouse) { mouse.accepted = true; }
        onClicked: function(mouse) { mouse.accepted = true; }
        onWheel: function(wheel) { wheel.accepted = true; }
    }

    // Own the *entire* popup's scroll wheel, including header, empty spaces
    // and end-of-scroll. Never chain a wheel delta into the underlying Budget
    // or Weather work area. No second Flickable or polling machinery.
    WheelHandler {
        id: diagnosticsWheelContainment
        target: null
        blocking: true
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        onWheel: function(wheel) {
            const delta = wheel.pixelDelta.y !== 0
                ? -wheel.pixelDelta.y : -wheel.angleDelta.y / 120 * 42;
            const limit = Math.max(0,
                diagnosticsScroll.contentHeight - diagnosticsScroll.height);
            diagnosticsScroll.contentY = Math.max(0,
                Math.min(limit, diagnosticsScroll.contentY + delta));
            wheel.accepted = true;
        }
    }

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

    // Header and canonical close are siblings ABOVE the Flickable. They
    // remain pinned while the service rows and reason text scroll below.
    Item {
        id: diagnosticsPinnedHeader
        z: 4
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 8
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        height: 49

        Row {
            id: diagnosticsHeaderRow
            anchors.top: parent.top
            width: parent.width
            height: 34
            spacing: 8

            GohuText {
                width: Math.max(0, parent.width - diagnosticsCloseButton.width
                                   - parent.spacing)
                anchors.verticalCenter: parent.verticalCenter
                text: diagnosticsPane.heading
                font.pixelSize: 12
                color: Colors.magenta
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
            CloseButton {
                id: diagnosticsCloseButton
                width: 34
                onCloseRequested: diagnosticsPane.closeRequested()
            }
        }

        Rectangle {
            id: diagnosticsPinnedDivider
            anchors.top: diagnosticsHeaderRow.bottom
            anchors.topMargin: 8
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2
            color: Colors.cyan
        }
    }

    Flickable {
        id: diagnosticsScroll
        z: 1
        anchors.top: diagnosticsPinnedHeader.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottomMargin: 4
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, detailBody.y + detailBody.implicitHeight + 16)

        // Schedule after layout settles. No polling, timer, and no direct
        // rail.scrollable -> column width -> contentHeight binding cycle.
        onContentHeightChanged: Qt.callLater(diagnosticsPane.updateRailSpace)
        onHeightChanged: Qt.callLater(diagnosticsPane.updateRailSpace)
        Component.onCompleted: Qt.callLater(diagnosticsPane.updateRailSpace)

        Column {
            id: detailBody
            x: 12
            y: 10
            width: Math.max(0, diagnosticsScroll.width
                - (diagnosticsPane.railSpaceReserved ? 44 : 24))
            spacing: 11

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
        id: diagnosticsRail
        flickable: diagnosticsScroll
        mountingParent: diagnosticsPane
        geometryHost: diagnosticsPane
        geometryMode: "box"
        handleStyle: "star"
        // The fixed sibling header bounds the rail's usable box. Reserve
        // only a modest gap BELOW its divider, never header/× height twice.
        boxTopInset: 7
        boxBottomInset: 12
        rightInset: 8
        z: 3
        visible: scrollable
    }
}
