import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../widgets"
import "../services/media/MediaDockMpdStatus.js" as MpdStatus

// Compact music transport placeholder. The full Hi-Fi deck will be a separate
// surface; this module only owns its taskbar artwork and initial MPD controls.
Item {
    id: mediaRoot

    // The taskbar only measures this compact surface; the deck is a separate
    // PanelWindow so it can expand without occupying taskbar layout space.
    implicitWidth: mediaDock.implicitWidth
    implicitHeight: mediaDock.implicitHeight

    property bool deckOpen: false

    // Forward the same Hi-Fi controller and explicit MPRIS selection.
    // These are observations for the Hub, not second media instances.
    readonly property var hubMediaController: deckPanel.hubMediaController
    readonly property string hubSelectedMprisBusName:
        deckPanel.hubSelectedMprisBusName
    // The already-running Media dock polls MPD every two seconds independently
    // of Hi-Fi visibility. Forward only scalars, never the Process or controls.
    readonly property string hubMpdPlaybackState: mediaDock.playbackState
    readonly property string hubMpdCurrentTrack: mediaDock.currentTrack
    readonly property double hubMpdObservedAtMs: mediaDock.lastMpdObservedAtMs
    // Atomic, validated MPD reading for the Hub. Never expose subprocess data.
    readonly property var hubMpdObservation: mediaDock.lastValidMpdObservation

    DockButton {
    id: mediaDock
    anchors.fill: parent
    open: mediaRoot.deckOpen

    readonly property int barCount: 16
    property var levels: Array(barCount).fill(0)

    // CAVA visualizes the system's default audio output, not just MPD.
    // MPD state is independent and will later be shared with the full deck.
    property string playbackState: "offline"
    property string currentTrack: ""
    property double lastMpdObservedAtMs: 0
    property var lastValidMpdObservation: null
    readonly property bool mpdOnline: playbackState !== "offline"
    readonly property bool mpdPlaying: playbackState === "playing"

    readonly property color accentColor: mpdPlaying ? Colors.orange : Colors.cyan

    implicitHeight: 50
    implicitWidth: Math.max(200, Math.ceil(mediaArtwork.implicitWidth) + 24)

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white

    normalContentGlowColor: accentColor
    hoverContentGlowColor: accentColor
    pressedContentGlowColor: Colors.magenta

    normalDockGlowColor: accentColor
    hoverDockGlowColor: accentColor
    pressedDockGlowColor: Colors.magenta

    contentGlowSource: mediaArtwork

    // Preserve the requested glyph exactly, before the live spectrum.
    Row {
        id: mediaArtwork
        anchors.centerIn: parent
        spacing: 9

        GohuText {
            id: musicMark
            anchors.verticalCenter: parent.verticalCenter
            text: "‧₊˚ 𝄞˖"
            font.pixelSize: 21
            color: mediaDock.foregroundColor
        }

        Item {
            id: spectrum
            width: mediaDock.barCount * 5 + (mediaDock.barCount - 1) * 2
            height: 28
            anchors.verticalCenter: parent.verticalCenter

            Row {
                anchors.fill: parent
                spacing: 2

                Repeater {
                    model: mediaDock.barCount

                    Item {
                        width: 5
                        height: spectrum.height

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: Math.max(2, Math.round(
                                (Number(mediaDock.levels[index] || 0) / 7) * 27
                            ))
                            radius: 0
                            color: mediaDock.accentColor

                            Behavior on height {
                                NumberAnimation {
                                    duration: 45
                                    easing.type: Easing.OutQuad
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function receiveCavaFrame(frame) {
        var raw = String(frame).trim();
        if (raw.endsWith(";"))
            raw = raw.slice(0, -1);
        var columns = raw.split(";");
        if (columns.length !== barCount)
            return;

        var newLevels = [];
        for (var i = 0; i < barCount; ++i) {
            var value = Number(columns[i]);
            if (!isFinite(value))
                return;
            newLevels.push(Math.max(0, Math.min(7, value)));
        }
        levels = newLevels;
    }

    Process {
        id: cavaProcess
        command: ["cava", "-p", Quickshell.shellPath("modules/mediaplayer-cava.conf")]
        running: true

        stdout: SplitParser {
            onRead: function(frame) {
                mediaDock.receiveCavaFrame(frame);
            }
        }

        onRunningChanged: {
            if (!running)
                mediaDock.levels = Array(mediaDock.barCount).fill(0);
        }
    }

    function receiveMpdStatus(output) {
        const parsed = MpdStatus.parseStatus(output);
        // A failed/empty subprocess response is not an observed MPD state.
        // Keep the last valid reading until the Hub's 15s freshness expiry.
        if (!parsed)
            return;

        playbackState = parsed.state;
        currentTrack = parsed.title;
        lastMpdObservedAtMs = Date.now();
        // Publish state, track and timestamp together, after they agree.
        lastValidMpdObservation = ({
            state: parsed.state,
            title: parsed.title,
            observedAtMs: lastMpdObservedAtMs
        });
    }

    Process {
        id: mpdStatusProcess
        command: ["mpc", "-f", "%artist% - %title%", "status"]
        running: true

        stdout: StdioCollector {
            onStreamFinished: mediaDock.receiveMpdStatus(this.text)
        }
    }

    Timer {
        interval: 2000
        running: true
        repeat: true

        onTriggered: {
            if (!mpdStatusProcess.running)
                mpdStatusProcess.running = true;
        }
    }

    // Left-click now opens/closes the deck. Playback controls will live in
    // the future control section. Right-click remains free for the planned
    // Desktop / Player CAVA source switch.
    onLeftClicked: {
        if (!mediaRoot.deckOpen) {
            // shell.qml currently starts 50px from the DP-5 screen edge.
            // Follow the dock's current temporary placement without editing
            // shared shell.qml or inventing its final taskbar position.
            var dockSceneX = mediaDock.mapToItem(null, 0, 0).x;
            var screenWidth = deckPanel.screen
                              ? deckPanel.screen.width : 2560;
            var maxLeft = Math.max(
                8, screenWidth - deckPanel.panelWidth - 8
            );
            deckPanel.panelLeftMargin = Math.max(
                8, Math.min(maxLeft, Math.round(50 + dockSceneX))
            );
        }
        mediaRoot.deckOpen = !mediaRoot.deckOpen;
    }
    }

    MediaDeckW {
        id: deckPanel
        menuOpen: mediaRoot.deckOpen
    }
}
