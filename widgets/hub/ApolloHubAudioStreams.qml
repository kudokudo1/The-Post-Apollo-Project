import QtQuick
import QtQuick.Controls
import "../../components"

// P3-B stream observation is explicitly NOT canonical application identity.
// Actions remain inside the Hub. Team 6 owns the pactl operation.
Item {
    id: streamsView
    property var streamGate: null
    property int selectedIndex: -1
    property string selectedIdentity: ""
    property bool detailsOpen: false
    property int draftVolume: 100
    property bool draftDirty: false
    signal inputFocusChanged(bool focused)

    readonly property var data: streamGate && streamGate.snapshot
                                ? streamGate.snapshot : null
    readonly property string state: data ? data.state : "unavailable"
    readonly property var entries: data && Array.isArray(data.items)
                                    ? data.items : []
    readonly property var selected: {
        for (let i = 0; i < entries.length; i++) {
            const e = entries[i];
            if (e.index === selectedIndex && e.identity === selectedIdentity)
                return e;
        }
        return null;
    }
    readonly property bool actionReady:
        streamGate !== null && data !== null && state === "ready"
        && selected !== null && !streamGate.busy
    readonly property string statusLine:
        state === "ready" ? "STREAMS // " + data.shown + " OF " + data.total
        : "STREAMS // " + state.toUpperCase()

    function inspect(entry) {
        if (!entry || !data || state !== "ready") return;
        selectedIndex = entry.index;
        selectedIdentity = entry.identity;
        draftVolume = entry.volumePercent >= 0
                      ? Math.max(0,Math.min(100,entry.volumePercent)) : 100;
        draftDirty = false;
        detailsOpen = true;
    }
    function requestMute() {
        if (!actionReady) return;
        streamGate.request(selectedIndex,selectedIdentity,
                           data.generation,"mute",!selected.muted);
    }
    function applyVolume() {
        if (!actionReady || !draftDirty) return;
        if (streamGate.request(selectedIndex,selectedIdentity,
                data.generation,"volume",draftVolume))
            draftDirty = false;
    }

    onVisibleChanged: {
        if (!visible) inputFocusChanged(false);
    }
    onSelectedChanged: {
        if (!selected) {
            draftDirty = false;
            inputFocusChanged(false);
        }
    }

    Row {
        id: streamsHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 28
        spacing: 5
        ActionButton {
            width: Math.max(1, (parent.width - parent.spacing) * 0.46)
            height: parent.height
            label: "REFRESH STREAMS"
            labelPixelSize: 10
            available: streamsView.streamGate !== null
                       && !streamsView.streamGate.busy
            softGlowEnabled: false
            onLeftClicked: streamsView.streamGate.refresh()
        }
        GohuText {
            width: Math.max(1, parent.width - parent.spacing
                                 - (parent.width - parent.spacing) * 0.46)
            height: parent.height
            font.pixelSize: 10
            color: streamsView.state === "ready" ? Colors.cyan : Colors.orange
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            text: streamsView.statusLine
        }
    }

    Item {
        id: listArea
        visible: !streamsView.detailsOpen
        anchors.top: streamsHeader.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        ListView {
            id: list
            anchors.fill: parent
            clip: true
            model: streamsView.entries
            spacing: 4
            boundsBehavior: Flickable.StopAtBounds
            delegate: ActionButton {
                required property var modelData
                width: list.width
                height: 36
                label: "#" + String(modelData.index) + " // "
                       + modelData.label + " // "
                       + (modelData.muted ? "MUTED" : "LIVE")
                labelPixelSize: 10
                softGlowEnabled: false
                onLeftClicked: streamsView.inspect(modelData)
            }
        }
        GohuText {
            anchors.centerIn: parent
            visible: streamsView.entries.length === 0
            width: parent.width
            height: 48
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            color: Colors.orange
            font.pixelSize: 10
            text: streamsView.state === "unavailable"
                  ? "NO STREAM OBSERVATION // PRESS REFRESH"
                  : streamsView.state === "empty" ? "NO LIVE PLAYBACK STREAMS"
                  : "STREAM DATA // " + streamsView.state.toUpperCase()
        }
    }

    Flickable {
        id: detailsArea
        visible: streamsView.detailsOpen
        anchors.top: streamsHeader.bottom
        anchors.topMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        contentWidth: width
        contentHeight: detailsColumn.height
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: detailsColumn
            width: detailsArea.width
            height: childrenRect.height
            spacing: 6

            GohuText {
                width: parent.width
                height: 21
                color: streamsView.selected ? Colors.white : Colors.orange
                font.pixelSize: 12
                elide: Text.ElideRight
                text: streamsView.selected
                      ? "STREAM #" + streamsView.selected.index
                        + " // " + streamsView.selected.label
                      : "STREAM ENDED OR CHANGED"
            }
            GohuText {
                width: parent.width
                height: 22
                color: Colors.cyan
                font.pixelSize: 10
                elide: Text.ElideRight
                text: streamsView.selected
                      ? ("REPORTED MEDIA // " + streamsView.selected.media)
                      : "NO VERIFIED STREAM IDENTITY"
            }
            ActionButton {
                width: parent.width
                height: 27
                label: streamsView.selected && streamsView.selected.muted
                       ? "UNMUTE STREAM" : "MUTE STREAM"
                labelPixelSize: 10
                available: streamsView.actionReady
                softGlowEnabled: false
                onLeftClicked: streamsView.requestMute()
            }
            GohuText {
                width: parent.width
                height: 18
                font.pixelSize: 10
                color: Colors.cyan
                text: "STREAM VOLUME // " + streamsView.draftVolume
                      + "% // OWNER RANGE 0–100%"
            }
            Slider {
                width: parent.width
                height: 26
                from: 0
                to: 100
                stepSize: 1
                enabled: streamsView.actionReady
                value: streamsView.draftVolume
                onMoved: {
                    streamsView.draftVolume = Math.round(value);
                    streamsView.draftDirty = true;
                }
                onActiveFocusChanged: streamsView.inputFocusChanged(activeFocus)
            }
            Row {
                width: parent.width
                height: 27
                spacing: 5
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "APPLY VOLUME"
                    labelPixelSize: 10
                    available: streamsView.actionReady && streamsView.draftDirty
                    softGlowEnabled: false
                    onLeftClicked: streamsView.applyVolume()
                }
                ActionButton {
                    width: Math.max(1,(parent.width-parent.spacing)/2)
                    height: parent.height
                    label: "RESET DRAFT"
                    labelPixelSize: 10
                    available: streamsView.actionReady && streamsView.draftDirty
                    softGlowEnabled: false
                    onLeftClicked: {
                        streamsView.draftDirty = false;
                        streamsView.draftVolume =
                            Math.max(0,Math.min(100,streamsView.selected.volumePercent));
                    }
                }
            }
            GohuText {
                width: parent.width
                height: 36
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: Colors.orange
                text: streamsView.streamGate ? streamsView.streamGate.feedback
                      : "TEAM 6 AUDIO OWNER NOT CONNECTED"
            }
            ActionButton {
                width: parent.width
                height: 27
                label: "BACK TO STREAMS"
                labelPixelSize: 10
                softGlowEnabled: false
                onLeftClicked: streamsView.detailsOpen = false
            }
            GohuText {
                width: parent.width
                height: 38
                wrapMode: Text.WordWrap
                color: Colors.orange
                font.pixelSize: 10
                text: "PIPEWIRE-REPORTED STREAM // NOT VERIFIED APP IDENTITY. "
                    + "DISPATCH IS NOT CONFIRMED APPLICATION."
            }
        }
    }
}
