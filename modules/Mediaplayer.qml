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

    // Media-only rear halo. The standard DockButton gives the rear and front
    // the SAME color; disable only its rear layer below, then draw that layer
    // here behind the dock. Keep its canonical opacity/spread and open-magenta
    // priority, while cyan/orange tracks the CAVA accent in ordinary states.
    RectangularShadow {
        id: mediaRearHalo
        anchors.fill: mediaDock
        spread: mediaDock.softGlowSpread
        opacity: mediaDock.softGlowOpacity
        color: mediaDock.open ? mediaDock.openGlowColor : mediaDock.accentColor
        visible: mediaDock.visible
        z: -1
    }

    DockButton {
    id: mediaDock
    anchors.fill: parent
    open: mediaRoot.deckOpen

    // Follow the canonical yellow open fill when the Hi-Fi deck is open.
    // Keep the Media-specific magenta open artwork/glows and the separate
    // CAVA-colored closed-state lighting unchanged.
    openFillColor: Colors.yellow

    readonly property int barCount: 20
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

    // Both the note image and the shared Media glow accent follow the CAVA
    // playback palette: MPD playing = cool cyan; idle = warm orange.
    // The canonical open-state highlight remains magenta.
    readonly property color accentColor: mpdPlaying ? Colors.cyan : Colors.orange
    // Appearance-only open priority: opening the deck magenta-energizes all
    // stars, clef, CAVA cores, individual halos and CAVA ambient light.
    // Keep accentColor tied to playback for normal/closed presentation.
    readonly property color artworkAccentColor: open ? Colors.magenta : accentColor

    // Share one vertical palette among all 20 bars and both existing halos.
    // Qt Quick GradientStop positions run top (0) to bottom (1).
    // MPD playing reveals cyan→blue→magenta from bottom to top; when not
    // playing, yellow→orange→red rises instead. Opening the Hi-Fi deck still
    // forces uniform magenta at every stop.
    readonly property Gradient cavaVerticalGradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop {
            position: 0.0
            color: mediaDock.open ? Colors.magenta
                : (mediaDock.mpdPlaying ? Colors.magenta : Colors.red)
        }
        GradientStop {
            position: 0.5
            color: mediaDock.open ? Colors.magenta
                : (mediaDock.mpdPlaying ? Colors.blue : Colors.orange)
        }
        GradientStop {
            position: 1.0
            color: mediaDock.open ? Colors.magenta
                : (mediaDock.mpdPlaying ? Colors.cyan : Colors.yellow)
        }
    }

    // Follow the general height of CAVA without following individual spikes.
    // The four tallest of 20 bars set a padded, bounded ambient envelope.
    // This recalculates only when the deduplicated levels array changes.
    readonly property real cavaAmbientTargetHeight: {
        const peaks = levels.slice().sort(function(a, b) { return b - a; });
        const upperAverage = (Number(peaks[0] || 0)
                            + Number(peaks[1] || 0)
                            + Number(peaks[2] || 0)
                            + Number(peaks[3] || 0)) / 4;
        return Math.max(14, Math.min(34, Math.round(12 + upperAverage * 27 / 7)));
    }

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

    // Media-specific two-plane glow: the root-level rear halo follows CAVA
    // cyan/orange (magenta on open); the built-in front wash remains magenta.
    // Disable only the original rear halo to prevent double stacking.
    softGlowEnabled: false
    normalDockGlowColor: Colors.magenta
    hoverDockGlowColor: Colors.magenta
    pressedDockGlowColor: Colors.magenta

    // Do not texture-sample the entire mark or the animated CAVA spectrum.
    // Each static glyph has its own source-attached glow below the artwork.
    // The spectrum already owns cheap per-bar accent-colored geometry halos.
    contentGlowEnabled: false
    contentGlowSource: null

    // The tiny ornament glyphs carry far less opaque alpha than the clef.
    // Keep their independent source-attached shadows, and add a small, soft
    // accent aura behind EACH star group. These are not a combined strip,
    // and neither aura samples or follows animated CAVA frames.
    RectangularShadow {
        id: leadingStarsAura
        x: mediaArtwork.x + musicMark.x + leadingStars.x
           + (leadingStars.width - width) / 2
        y: mediaArtwork.y + musicMark.y + leadingStars.y
           + (leadingStars.height - height) / 2
        width: Math.max(1, leadingStars.width - 2 * mediaDock.softGlowSpread)
        height: Math.max(1, leadingStars.height - 2 * mediaDock.softGlowSpread)
        radius: height / 2
        blur: mediaDock.contentGlowRadius + 4
        spread: 0
        color: mediaDock.artworkAccentColor
        opacity: mediaDock.softGlowOpacity
        z: 0
    }

    // Match the stars' extra local aura on the otherwise thinner clef PNG.
    // It stays behind this single static icon, never the animated CAVA bars.
    RectangularShadow {
        id: trebleClefAura
        x: mediaArtwork.x + musicMark.x + trebleClef.x
           + (trebleClef.width - width) / 2
        y: mediaArtwork.y + musicMark.y + trebleClef.y
           + (trebleClef.height - height) / 2
        width: Math.max(1, trebleClef.width - 2 * mediaDock.softGlowSpread)
        height: Math.max(1, trebleClef.height - 2 * mediaDock.softGlowSpread)
        radius: height / 2
        blur: mediaDock.contentGlowRadius + 4
        spread: 0
        color: mediaDock.artworkAccentColor
        opacity: mediaDock.softGlowOpacity
        z: 0
    }

    RectangularShadow {
        id: trailingStarAura
        x: mediaArtwork.x + musicMark.x + trailingStar.x
           + (trailingStar.width - width) / 2
        y: mediaArtwork.y + musicMark.y + trailingStar.y
           + (trailingStar.height - height) / 2
        width: Math.max(1, trailingStar.width - 2 * mediaDock.softGlowSpread)
        height: Math.max(1, trailingStar.height - 2 * mediaDock.softGlowSpread)
        radius: height / 2
        blur: mediaDock.contentGlowRadius + 4
        spread: 0
        color: mediaDock.artworkAccentColor
        opacity: mediaDock.softGlowOpacity
        z: 0
    }

    // Strengthen the three *static* symbol shadows without sampling any
    // moving CAVA bars. Leave the magenta full-width dock wash untouched.
    SafeDropShadow {
        id: leadingStarsGlow
        safeSource: leadingStars
        x: mediaArtwork.x + musicMark.x + leadingStars.x
        y: mediaArtwork.y + musicMark.y + leadingStars.y
        width: leadingStars.width
        height: leadingStars.height
        horizontalOffset: 0
        verticalOffset: 0
        radius: mediaDock.contentGlowRadius + 4
        samples: mediaDock.contentGlowSamples + 6
        requestedVisible: true
        opacity: Math.min(1.0, mediaDock.contentGlowOpacity + 0.18)
        color: mediaDock.artworkAccentColor
        transparentBorder: true
        z: 0
    }

    SafeDropShadow {
        id: trebleClefGlow
        safeSource: trebleClef
        x: mediaArtwork.x + musicMark.x + trebleClef.x
        y: mediaArtwork.y + musicMark.y + trebleClef.y
        width: trebleClef.width
        height: trebleClef.height
        horizontalOffset: 0
        verticalOffset: 0
        radius: mediaDock.contentGlowRadius + 4
        samples: mediaDock.contentGlowSamples + 6
        requestedVisible: true
        opacity: Math.min(1.0, mediaDock.contentGlowOpacity + 0.18)
        color: mediaDock.artworkAccentColor
        transparentBorder: true
        z: 0
    }

    SafeDropShadow {
        id: trailingStarGlow
        safeSource: trailingStar
        x: mediaArtwork.x + musicMark.x + trailingStar.x
        y: mediaArtwork.y + musicMark.y + trailingStar.y
        width: trailingStar.width
        height: trailingStar.height
        horizontalOffset: 0
        verticalOffset: 0
        radius: mediaDock.contentGlowRadius + 4
        samples: mediaDock.contentGlowSamples + 6
        requestedVisible: true
        opacity: Math.min(1.0, mediaDock.contentGlowOpacity + 0.18)
        color: mediaDock.artworkAccentColor
        transparentBorder: true
        z: 0
    }

    // Requested Media icon: ‧₊˚ 𝄞 ׅ˖ㅤ
    // The treble clef stays as the matching bundled U+1D11E PNG because
    // the operator's Qt font stack previously failed to render it as text.
    // Existing per-glyph sampled shadows and local auras remain unchanged.
    Row {
        id: mediaArtwork
        anchors.centerIn: parent
        // With 20 bars the centered artwork grows by 32px: the music mark
        // shifts 16px left while the spectrum extends to the right. Keep a
        // little more room between the clef and the added frequency bands.
        spacing: 13
        z: 1

        // Musical-symbol font fallback is not reliable on the operator's Qt
        // runtime (including the previous plain-text attempt). Bundle a
        // two static PNG color variants from our SVG source. Follow the same
        // MPD playing state as CAVA's accent, without a runtime tint shader.
        // Keep the whole mark's magenta glow separate from the animated bars.
        Row {
            id: musicMark
            anchors.verticalCenter: parent.verticalCenter
            // Small overlap closes remaining monospace side bearings.
            // Each glow already tracks its own glyph's actual bounds.
            spacing: -2

            GohuText {
                id: leadingStars
                anchors.verticalCenter: trebleClef.verticalCenter
                textFormat: Text.PlainText
                // Do not reserve an extra monospaced cell after the stars.
                text: "‧₊˚"
                font.pixelSize: 21
                // Bring the outer left ornaments toward the one by the note.
                // Keep all three glyphs in the same source for their glow.
                font.letterSpacing: -6
                color: mediaDock.foregroundColor
            }

            Image {
                id: trebleClef
                width: 15
                height: 34
                // Switch only when opening/closing the deck or when MPD
                // changes state, never on a CAVA frame. Keep the transparent
                // original magenta PNG for the open state.
                source: mediaDock.open
                    ? Qt.resolvedUrl("../assets/media/treble-clef.png")
                    : mediaDock.mpdPlaying
                      ? Qt.resolvedUrl("../assets/media/treble-clef-cyan.png")
                      : Qt.resolvedUrl("../assets/media/treble-clef-orange.png")
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
                id: trailingStar
                anchors.verticalCenter: trebleClef.verticalCenter
                textFormat: Text.PlainText
                // The old leading space and Hangul filler widened the Row.
                // Preserve the visible combining accent and star without
                // reserving invisible spacing on either side.
                text: "ׅ˖"
                font.pixelSize: 21
                color: mediaDock.foregroundColor
            }
        }

        Item {
            id: spectrum
            width: mediaDock.barCount * 5 + (mediaDock.barCount - 1) * 2
            height: 28
            anchors.verticalCenter: parent.verticalCenter

            // Faint wash follows the broad spectrum envelope, not each bar.
            // Extra height padding and a slower transition keep it loose.
            // Only this one rounded geometry animates; no CAVA texture sample.
            RectangularShadow {
                id: cavaAmbientWash
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: -2
                // Keep the full bar range within the flatter center of
                // this blurred wash. Its feathered edges extend outside
                // BOTH spectrum ends by the blur radius + a small shoulder,
                // so neither edge loses ambient light. Width still follows
                // barCount via spectrum.width, without sampling moving bars.
                width: Math.max(0, spectrum.width
                    + 2 * (mediaDock.contentGlowRadius + 4 + mediaDock.softGlowSpread))
                height: mediaDock.cavaAmbientTargetHeight
                radius: height / 2
                blur: mediaDock.contentGlowRadius + 4
                spread: 0
                color: mediaDock.artworkAccentColor
                opacity: 0.30
                z: -1

                Behavior on height {
                    NumberAnimation {
                        duration: 180
                        easing.type: Easing.OutQuad
                    }
                }
            }

            Row {
                anchors.fill: parent
                spacing: 2

                Repeater {
                    model: mediaDock.barCount

                    Item {
                        width: 5
                        height: spectrum.height

                        // One scalar per bar, updated from CAVA's already
                        // deduplicated 0–7 levels (15 FPS maximum). No new
                        // animation, shader, texture sampling or CAVA process.
                        readonly property real glowActivity: Math.max(0, Math.min(1,
                            Number(mediaDock.levels[index] || 0) / 7))

                        // Reveal a full-spectrum-height gradient from the
                        // bottom: low activity stays near cyan/yellow, and
                        // only taller bars reach blue/orange then magenta/red.
                        // Avoid stretching the entire palette into each
                        // short bar. Preserve both existing geometry halos.
                        Item {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: -3
                            width: parent.width + 8
                            height: cavaBar.height + 6
                            clip: true

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: spectrum.height + 6
                                radius: 0
                                gradient: mediaDock.cavaVerticalGradient
                                opacity: 0.30 + 0.24 * parent.parent.glowActivity
                            }
                        }

                        Item {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: -1
                            width: parent.width + 4
                            height: cavaBar.height + 2
                            clip: true

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: spectrum.height + 2
                                radius: 0
                                gradient: mediaDock.cavaVerticalGradient
                                opacity: 0.50 + 0.30 * parent.parent.glowActivity
                            }
                        }

                        Item {
                            id: cavaBar
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: Math.max(2, Math.round(
                                (Number(mediaDock.levels[index] || 0) / 7) * 27
                            ))
                            clip: true

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: spectrum.height
                                radius: 0
                                gradient: mediaDock.cavaVerticalGradient
                            }

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
        // Do not trigger 20 QML bindings and animations for identical frames,
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
