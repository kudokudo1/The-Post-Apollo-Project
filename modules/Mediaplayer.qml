import QtQuick
import QtQuick.Effects
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

    // Dormant unless the existing diagnostic launch flag is enabled.
    readonly property bool bgLagProbeEnabled:
        String(Quickshell.env("POST_APOLLO_UI_LAG_PROBE") || "").trim() === "1"
    property int bgFrameCount: 0
    property int bgChangedFrameCount: 0
    property int bgMaxFrameMs: 0
    property double bgLastFrameSummaryMs: 0

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

    // The static stars/clef cluster follows the same accent as CAVA.
    // The DockButton's canonical open-magenta priority still applies.
    normalContentGlowColor: accentColor
    hoverContentGlowColor: accentColor
    pressedContentGlowColor: accentColor

    // Magenta idle chassis; leave hover and opened dock semantics unchanged.
    normalDockGlowColor: Colors.magenta
    hoverDockGlowColor: accentColor
    pressedDockGlowColor: Colors.magenta

    // Never texture-sample the 16 animated VU bars for a blur glow.
    // Sampling them forced a new shadow texture every CAVA frame. Keep the
    // sampled glow attached to the static music glyph instead.
    contentGlowSource: musicMark

    // One non-sampled cyan/orange wash below the entire music mark + CAVA.
    // It sits inside the module, above the independent magenta chassis glow
    // but below the artwork. This only changes on MPD state/hover, not on
    // each CAVA frame (which previously caused Quickshell render stalls).
    RectangularShadow {
        id: mediaArtworkUnderlay
        anchors.centerIn: mediaArtwork
        width: mediaArtwork.width + 10
        height: mediaArtwork.height + 4
        spread: mediaDock.softGlowSpread
        blur: mediaDock.contentGlowRadius
        color: mediaDock.accentColor
        opacity: mediaDock.softGlowOpacity * 0.80
        z: 0
    }

    // Preserve the requested glyph exactly, before the live spectrum.
    Row {
        id: mediaArtwork
        anchors.centerIn: parent
        spacing: 9
        z: 1

        // Musical-symbol font fallback is not reliable on the operator's Qt
        // runtime (including the previous plain-text attempt). Bundle a
        // two static PNG color variants from our SVG source. Follow the same
        // MPD playing state as CAVA's accent, without a runtime tint shader.
        // Keep the whole mark's magenta glow separate from the animated bars.
        Row {
            id: musicMark
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0

            GohuText {
                anchors.verticalCenter: trebleClef.verticalCenter
                textFormat: Text.PlainText
                text: "‧₊˚ "
                font.pixelSize: 21
                color: mediaDock.foregroundColor
            }

            Image {
                id: trebleClef
                width: 15
                height: 34
                // One source change per playback-state change, not per CAVA
                // frame: cyan when idle/paused/stopped, orange when playing.
                source: mediaDock.mpdPlaying
                    ? Qt.resolvedUrl("../assets/media/treble-clef-orange.png")
                    : Qt.resolvedUrl("../assets/media/treble-clef-cyan.png")
                sourceSize: Qt.size(45, 102)
                fillMode: Image.PreserveAspectFit
                smooth: true
                asynchronous: false
                onStatusChanged: {
                    if (status === Image.Error)
                        console.warn("MediaDock: treble clef PNG failed to load", source);
                }
            }

            GohuText {
                anchors.verticalCenter: trebleClef.verticalCenter
                textFormat: Text.PlainText
                text: "˖"
                font.pixelSize: 21
                color: mediaDock.foregroundColor
            }
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

                        // Two geometry-only halos follow the animated core.
                        // Never create a per-frame shader texture or a second
                        // animation for CAVA: that previously stalled Quickshell.
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: -3
                            width: parent.width + 8
                            height: cavaBar.height + 6
                            radius: 0
                            color: mediaDock.accentColor
                            opacity: 0.13
                        }

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: -1
                            width: parent.width + 4
                            height: cavaBar.height + 2
                            radius: 0
                            color: mediaDock.accentColor
                            opacity: 0.28
                        }

                        Rectangle {
                            id: cavaBar
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
        const traceStartMs = bgLagProbeEnabled ? Date.now() : 0;
        var raw = String(frame).trim();
        if (raw.endsWith(";"))
            raw = raw.slice(0, -1);
        var columns = raw.split(";");
        if (columns.length !== barCount)
            return;

        var newLevels = [];
        var changed = false;
        for (var i = 0; i < barCount; ++i) {
            var value = Number(columns[i]);
            if (!isFinite(value))
                return;
            var level = Math.max(0, Math.min(7, value));
            newLevels.push(level);
            if (level !== Number(levels[i] || 0))
                changed = true;
        }
        // Do not trigger 16 QML bindings and animations for identical frames,
        // especially when the monitor stream is silent but CAVA stays alive.
        if (changed)
            levels = newLevels;

        if (traceStartMs) {
            const now = Date.now();
            const elapsed = now - traceStartMs;
            bgFrameCount += 1;
            if (changed)
                bgChangedFrameCount += 1;
            bgMaxFrameMs = Math.max(bgMaxFrameMs, elapsed);
            if (elapsed >= 25)
                console.warn("SYNTAGMA_BG_PROBE // media cava-frame synchronous="
                             + elapsed + "ms tsMs=" + now);
            if (!bgLastFrameSummaryMs)
                bgLastFrameSummaryMs = now;
            if (now - bgLastFrameSummaryMs >= 5000) {
                console.warn("SYNTAGMA_BG_PROBE // media cava-frames 5s count="
                             + bgFrameCount + " changed=" + bgChangedFrameCount
                             + " maxHandlerMs=" + bgMaxFrameMs + " tsMs=" + now);
                bgLastFrameSummaryMs = now;
                bgFrameCount = 0;
                bgChangedFrameCount = 0;
                bgMaxFrameMs = 0;
            }
        }
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
