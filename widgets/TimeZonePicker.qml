import QtQuick
import QtQuick.Controls
import "../components"
import "../services/time/WorldZoneSearch.js" as ZoneSearch

// Reusable TimeW CALC selector. Each instance owns its own query and popup;
// the parent arbitrates which selector may remain open.
Item {
    id: picker

    property var catalog: []
    property var countryIndex: ({})
    property string selectedZone: "UTC"
    property bool expanded: false
    property bool catalogLoading: false
    property bool catalogFailed: false
    property string query: ""
    readonly property bool searchFocused: searchInput.activeFocus
    readonly property var matches:
        ZoneSearch.search(catalog, query, ZoneSearch.MAX_ZONES, countryIndex)
    signal openRequested()
    signal toggleRequested()
    signal zoneChosen(string zoneId)

    height: 34
    width: 200

    // The caller's passive frame TapHandler uses this to release focus on
    // clicks outside the selector or its overflowing suggestions panel.
    function containsFramePoint(frame, px, py) {
        const point = frame.mapToItem(picker, px, py);
        if (point.x >= 0 && point.x <= picker.width
                && point.y >= 0 && point.y <= picker.height)
            return true;
        return expanded && point.x >= 0 && point.x <= popup.width
               && point.y >= popup.y && point.y <= popup.y + popup.height;
    }

    function dropFocus() {
        searchInput.focus = false;
    }

    onExpandedChanged: {
        if (expanded) {
            query = "";
            searchInput.text = "";
            Qt.callLater(function() {
                if (picker.expanded && picker.visible)
                    searchInput.forceActiveFocus();
            });
        } else {
            searchInput.focus = false;
            searchInput.text = ZoneSearch.label(selectedZone);
        }
    }

    onSelectedZoneChanged: {
        if (!expanded)
            searchInput.text = ZoneSearch.label(selectedZone);
    }
    Component.onCompleted: searchInput.text = ZoneSearch.label(selectedZone)

    Row {
        id: searchRow
        anchors.fill: parent
        spacing: 6

        ActionButton {
            id: menuArrow
            width: 32
            height: 34
            label: "▾"
            labelPixelSize: 18
            trackLabelGlowLocally: true
            accentColor: Colors.white
            selected: picker.expanded
            onLeftClicked: picker.toggleRequested()
        }

        TextField {
            id: searchInput
            width: Math.max(0, searchRow.width - menuArrow.width
                            - searchRow.spacing)
            height: searchRow.height
            placeholderText: "SEARCH COUNTRY / ZONE"
            placeholderTextColor: Colors.cyan
            color: Colors.magenta
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            cursorDelegate: Rectangle { width: 2; color: Colors.orange }
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 11
            leftPadding: 8
            rightPadding: 8
            selectByMouse: true
            background: Rectangle {
                color: Colors.black
                border.width: 1
                border.color: searchInput.activeFocus
                              ? Colors.magenta : Colors.cyan
            }
            onPressed: picker.openRequested()
            onTextEdited: {
                picker.query = text;
                if (!picker.expanded)
                    picker.openRequested();
            }
            onAccepted: {
                if (picker.expanded && picker.matches.length > 0)
                    picker.zoneChosen(picker.matches[0].id);
            }
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Escape) {
                    picker.toggleRequested();
                    event.accepted = true;
                }
            }
        }
    }

    Rectangle {
        id: popup
        y: picker.height + 3
        width: parent.width
        height: picker.matches.length > 0
                ? Math.min(212, 34 + picker.matches.length * 30) : 54
        z: 50
        visible: picker.expanded
        color: Colors.black
        border.width: 1
        border.color: Colors.white

        GohuText {
            id: countHeader
            x: 8
            y: 4
            width: parent.width - 16
            height: 18
            verticalAlignment: Text.AlignVCenter
            color: Colors.cyan
            font.pixelSize: 11
            text: (picker.query.trim() === "" ? "ITEMS // " : "MATCHES // ")
                  + picker.matches.length
        }

        ListView {
            id: zoneResults
            anchors {
                top: countHeader.bottom
                bottom: parent.bottom
                left: parent.left
                right: parent.right
                margins: 4
                topMargin: 4
                rightMargin: pickerRail.crossExtent + 5
            }
            clip: true
            spacing: 2
            model: picker.matches
            boundsBehavior: Flickable.StopAtBounds
            interactive: contentHeight > height

            delegate: ActionButton {
                width: zoneResults.width
                height: 28
                label: modelData.country
                       ? modelData.country + " // " + modelData.label
                       : modelData.label
                labelPixelSize: 11
                labelHorizontalAlignment: Text.AlignLeft
                trackLabelGlowLocally: true
                accentColor: Colors.white
                softGlowEnabled: false
                onLeftClicked: picker.zoneChosen(modelData.id)
            }
        }

        NeonScrollBar {
            id: pickerRail
            flickable: zoneResults
            accountForContentOrigin: true
            geometryMode: "viewport"
            x: popup.width - width - 3
            y: zoneResults.y
            height: zoneResults.height
            handleStyle: "star"
            railColor: Colors.cyan
            handleColor: Colors.magenta
            handleBorderColor: Colors.magenta
            railGlowColor: Colors.white
            containGlow: true
            visible: picker.expanded && scrollable
        }

        GohuText {
            visible: picker.matches.length === 0
            anchors.centerIn: parent
            width: parent.width - 12
            height: 24
            verticalAlignment: Text.AlignVCenter
            color: Colors.orange
            font.pixelSize: 11
            text: picker.catalogLoading
                  ? "LOADING ZONES..."
                  : picker.catalogFailed ? "DIRECTORY UNAVAILABLE"
                  : "NO MATCHES"
        }
    }
}
