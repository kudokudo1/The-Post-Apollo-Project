import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../widgets"

// Compact music transport placeholder. The full Hi-Fi deck will be a separate
// surface; this module only owns its taskbar artwork and initial MPD controls.
Item {
    id: mediaRoot

    // The taskbar only measures this compact surface; the deck is a separate
    // PanelWindow so it can expand without occupying taskbar layout space.
    implicitWidth: mediaDock.implicitWidth
    implicitHeight: mediaDock.implicitHeight

    property bool deckOpen: false

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

    contentGlowIdleOpacity: 0.60
    contentGlowHoverOpacity: 0.80
    contentGlowPressedOpacity: 1.0
    contentGlowHoverRadius: 14
    contentGlowPressedRadius: 14
    contentGlowHoverSamples: 15
    contentGlowPressedSamples: 15

    softGlowIdleOpacity: 0.40
    softGlowHoverOpacity: 0.50
    softGlowPressedOpacity: 0.60

    wideGlowIdleOpacity: 0.07
    wideGlowHoverOpacity: 0.09
    wideGlowPressedOpacity: 0.12

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
        var status = String(output || "").trim();
        var state = status.match(/\[(playing|paused|stopped)\]/);

        if (state) {
            playbackState = state[1];
            currentTrack = status.split(/\r?\n/)[0];
        } else if (/volume:|repeat:|random:/.test(status)) {
            playbackState = "stopped";
            currentTrack = "";
        } else {
            playbackState = "offline";
            currentTrack = "";
        }
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
