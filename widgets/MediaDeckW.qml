import QtQuick
import Quickshell
import Quickshell.Wayland
import "../services/audio"
import "../services/media"
import "../components"

// Initial Hi-Fi deck chassis. Adapted from MenuTemplate.qml.template:
// a transparent PanelWindow, explicit open state, screen-edge anchors and
// three structural sections. Hardware artwork/controls come later.
PanelWindow {
    id: deck

    property bool menuOpen: false

    // Keep the first pass easy to resize/reposition during the design phase.
    property int panelWidth: 520
    property int panelHeight: 850
    property int panelTopMargin: 78
    property int panelLeftMargin: 200
    property int contentInset: 14
    property int sectionSpacing: 10
    // MPD remains the default. MPRIS is opt-in and targets one explicitly
    // selected external player; it is not a loaded YouTube playlist.
    property string transportMode: "mpd"

    MprisPlaybackAdapter {
        id: mediaAdapter
    }

    // Read-only use of the existing AppControl-extracted audio physiology.
    // Discovery is application/stream evidence, NOT per-browser-tab ownership.
    ApplicationAudioService {
        id: audioProbe
    }

    function playerAudioDescriptor() {
        const p = mediaAdapter.activePlayer;
        if (!p)
            return null;

        const blocked = [
            "browser", "stable", "beta", "dev", "bin", "app",
            "desktop", "player", "media", "org", "com", "chromium",
            "application", "electron"
        ];
        const tokens = [];
        const names = [String(p.desktopEntry || ""), String(p.identity || "")];
        for (let i = 0; i < names.length; i++) {
            const parts = [names[i]].concat(names[i].split(/[^a-zA-Z0-9]+/));
            for (let j = 0; j < parts.length; j++) {
                const token = String(parts[j]).toLowerCase().replace(/[^a-z0-9]/g, "");
                if (token.length >= 3 && blocked.indexOf(token) === -1
                        && tokens.indexOf(token) === -1)
                    tokens.push(token);
            }
        }
        return { pids: [], tokens: tokens, strictTokens: true };
    }

    readonly property var browserAudioDescriptor: playerAudioDescriptor()
    readonly property var browserAudioEvidence:
        browserAudioDescriptor
        ? audioProbe.resolve(browserAudioDescriptor, audioProbe.sinkInputs)
        : null

    readonly property var audioCandidateInputs:
        browserAudioEvidence ? browserAudioEvidence.inputs : []
    property int audioCandidatePosition: 0
    readonly property var selectedAudioCandidate:
        audioCandidateInputs.length > 0
        ? audioCandidateInputs[audioCandidatePosition % audioCandidateInputs.length]
        : null

    // This is an explicitly armed *stream-level* experiment, not per-tab
    // targeting. A browser stream may contain multiple tabs.
    property bool audioTestArmed: false
    property string audioTestStatus: "NO EXPERIMENT RUN YET"

    function handleAudioExperiment(action) {
        if (action === "arm") {
            audioTestArmed = !audioTestArmed;
            return;
        }

        if (action === "next") {
            audioCandidatePosition += 1;
            audioTestArmed = false;
            return;
        }

        if (!audioTestArmed || !selectedAudioCandidate
                || audioExperimentProcess.running || transportMode !== "mpris")
            return;

        const input = selectedAudioCandidate;
        const props = input.properties || {};
        const pid = String(props["application.process.id"] || "");
        const binary = String(props["application.process.binary"] || "");
        if (!pid && !binary) {
            audioTestStatus = "CANNOT VERIFY STREAM IDENTITY";
            audioTestArmed = false;
            return;
        }

        audioTestArmed = false;
        audioTestStatus = "TESTING STREAM " + input.index + " / 3 SEC";
        audioExperimentProcess.exec([
            "/usr/bin/python3",
            Quickshell.shellPath("scripts/media/temporary_audio_test.py"),
            String(input.index), action, pid, binary
        ]);
    }

    Process {
        id: audioExperimentProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const response = String(text || "").trim();
                if (response)
                    deck.audioTestStatus = response;
                audioProbe.refresh();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();
                if (message)
                    deck.audioTestStatus = "TEST ERROR: " + message;
            }
        }
    }

    Timer {
        interval: 2000
        repeat: true
        running: deck.menuOpen && deck.transportMode === "mpris"
        onTriggered: audioProbe.refresh()
    }

    onMenuOpenChanged: {
        if (menuOpen)
            audioProbe.refresh();
    }

    function runTransport(action) {
        if (transportMode === "mpris") {
            if (!mediaAdapter.run(action))
                console.log("MediaDeck: MPRIS command unavailable", action);
            return;
        }
        runLocalTransport(action);
    }
    // The three functional zones are now stacked, with controls receiving
    // the largest share. These proportions are still design parameters.
    property real displayHeightShare: 0.34
    property real cassetteHeightShare: 0.24

    // Only the local MPD backend is connected in this prototype.
    // A shared source-neutral transport service is a later milestone.
    function runLocalTransport(action) {
        const commands = {
            previous: ["mpc", "prev"],
            play: ["mpc", "play"],
            pause: ["mpc", "pause", "1"],
            next: ["mpc", "next"],
            rewind5: ["mpc", "seek", "-5"],
            forward5: ["mpc", "seek", "+5"],
            stop: ["mpc", "stop"]
        };

        const command = commands[action];
        if (command)
            Quickshell.execDetached(command);
    }

    screen: Quickshell.screens.find(s => s.name === "DP-5")

    visible: menuOpen
    implicitWidth: panelWidth
    implicitHeight: panelHeight
    color: "transparent"
    exclusiveZone: 0

    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

    anchors {
        top: true
        left: true
        right: false
        bottom: false
    }

    margins {
        top: panelTopMargin
        left: panelLeftMargin
        right: 0
        bottom: 0
    }

    SurfaceFrame {
        anchors.fill: parent

        fillColor: Colors.black
        fillOpacity: 0.96
        borderColor: Colors.cyan
        borderWidth: 2

        Column {
            id: deckSections

            anchors.fill: parent
            anchors.margins: deck.contentInset
            spacing: deck.sectionSpacing

            // Top zone: the future text-first browser and playback display.
            SectionFrame {
                id: displaySection
                width: parent.width
                height: Math.round(
                    (deckSections.height - 2 * deckSections.spacing)
                    * deck.displayHeightShare
                )
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "DISPLAY / BROWSER"
                    color: Colors.cyan
                    font.pixelSize: 16
                }

                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 35
                    anchors.left: parent.left
                    anchors.right: parent.right
                    text: mediaAdapter.connected
                          ? ("EXTERNAL: " + String(mediaAdapter.activePlayer.identity || "MPRIS"))
                          : "EXTERNAL: NO PLAYER SELECTED"
                    color: Colors.orange
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }

                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 61
                    anchors.left: parent.left
                    anchors.right: parent.right
                    text: mediaAdapter.connected
                          ? String(mediaAdapter.activePlayer.trackTitle || "NO TRACK METADATA")
                          : "Open a YouTube video in a browser first."
                    color: Colors.white
                    font.pixelSize: 14
                    elide: Text.ElideRight
                }

                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 90
                    anchors.left: parent.left
                    anchors.right: parent.right
                    text: "AUDIO: "
                          + (browserAudioEvidence
                             ? browserAudioEvidence.indexes.length + " APP-MATCHED STREAM(S)"
                             : "NO APP TARGET")
                    color: Colors.cyan
                    font.pixelSize: 12
                }

                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 111
                    anchors.left: parent.left
                    anchors.right: parent.right
                    text: audioProbe.errorText
                          ? ("PROBE ERROR: " + audioProbe.errorText)
                          : "PIPEWIRE MATCH IS NOT PER-TAB PROOF"
                    color: Colors.orange
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                Row {
                    anchors.top: parent.top
                    anchors.topMargin: 152
                    anchors.left: parent.left
                    spacing: 9

                    Rectangle {
                        width: 128
                        height: 36
                        radius: 3
                        color: modeMouse.containsMouse ? "#39333E" : "#29252E"
                        border.width: 1
                        border.color: deck.transportMode === "mpris"
                                      ? Colors.orange : Colors.cyan

                        GohuText {
                            anchors.centerIn: parent
                            text: "USE MPRIS"
                            font.pixelSize: 12
                            color: Colors.white
                        }

                        MouseArea {
                            id: modeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (!mediaAdapter.connected
                                        && !mediaAdapter.selectNextPlayer())
                                    return;
                                deck.transportMode = "mpris";
                                audioProbe.refresh();
                            }
                        }
                    }

                    Rectangle {
                        width: 140
                        height: 36
                        radius: 3
                        color: playerMouse.containsMouse ? "#39333E" : "#29252E"
                        border.width: 1
                        border.color: Colors.cyan

                        GohuText {
                            anchors.centerIn: parent
                            text: "NEXT PLAYER"
                            font.pixelSize: 12
                            color: Colors.white
                        }

                        MouseArea {
                            id: playerMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (mediaAdapter.selectNextPlayer()) {
                                    deck.transportMode = "mpris";
                                    audioProbe.refresh();
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: 125
                        height: 36
                        radius: 3
                        color: localMouse.containsMouse ? "#39333E" : "#29252E"
                        border.width: 1
                        border.color: deck.transportMode === "mpd"
                                      ? Colors.orange : Colors.cyan

                        GohuText {
                            anchors.centerIn: parent
                            text: "LOCAL / MPD"
                            font.pixelSize: 12
                            color: Colors.white
                        }

                        MouseArea {
                            id: localMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: deck.transportMode = "mpd"
                        }
                    }
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    text: "READ-ONLY AUDIO PROBE • NO VOLUME MUTATIONS"
                    color: Colors.cyan
                    opacity: 0.65
                    font.pixelSize: 10
                }
            }

            // Middle zone: the future cassette or alternative loaded medium.
            SectionFrame {
                id: cassetteSection
                width: parent.width
                height: Math.round(
                    (deckSections.height - 2 * deckSections.spacing)
                    * deck.cassetteHeightShare
                )
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "CASSETTE BAY"
                    color: Colors.cyan
                    font.pixelSize: 16
                }
            }

            // Zone C — first tactile transport test, not the final hardware.
            SectionFrame {
                width: parent.width
                height: deckSections.height
                        - displaySection.height
                        - cassetteSection.height
                        - 2 * deckSections.spacing
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                GohuText {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "CONTROLS"
                    color: Colors.cyan
                    font.pixelSize: 16
                }

                GohuText {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    text: deck.transportMode === "mpris" ? "MPRIS / EXTERNAL" : "LOCAL / MPD"
                    color: Colors.orange
                    font.pixelSize: 11
                }

                Grid {
                    id: transportGrid

                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        topMargin: 48
                    }

                    columns: 4
                    spacing: 8

                    Repeater {
                        model: [
                            { label: "PREV", action: "previous" },
                            { label: "PLAY", action: "play" },
                            { label: "PAUSE", action: "pause" },
                            { label: "NEXT", action: "next" },
                            { label: "-5 SEC", action: "rewind5" },
                            { label: "+5 SEC", action: "forward5" },
                            { label: "STOP", action: "stop" }
                        ]

                        Rectangle {
                            id: transportKey

                            required property var modelData

                            width: (transportGrid.width
                                    - 3 * transportGrid.spacing) / 4
                            height: 50
                            radius: 3
                            opacity: deck.transportMode !== "mpris"
                                     || mediaAdapter.supports(modelData.action) ? 1.0 : 0.45

                            color: keyMouse.pressed
                                   ? "#16131B"
                                   : keyMouse.containsMouse
                                   ? "#39333E"
                                   : "#29252E"

                            border.width: 1
                            border.color: keyMouse.pressed
                                          ? Colors.orange
                                          : keyMouse.containsMouse
                                          ? Colors.cyan
                                          : "#69616F"

                            transform: Translate {
                                y: keyMouse.pressed ? 1 : 0
                            }

                            GohuText {
                                anchors.centerIn: parent
                                text: transportKey.modelData.label
                                font.pixelSize: 12
                                color: keyMouse.pressed
                                       ? Colors.orange
                                       : keyMouse.containsMouse
                                       ? Colors.cyan
                                       : Colors.white
                            }

                            MouseArea {
                                id: keyMouse
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked: deck.runTransport(
                                    transportKey.modelData.action
                                )
                            }
                        }
                    }
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.topMargin: 184
                    text: deck.transportMode === "mpris"
                          ? "STREAM TEST / MAY AFFECT OTHER BROWSER TABS"
                          : "SWITCH TO MPRIS TO INSPECT BROWSER AUDIO"
                    color: Colors.orange
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                Row {
                    id: audioTestButtons
                    anchors.top: parent.top
                    anchors.topMargin: 212
                    anchors.left: parent.left
                    anchors.right: parent.right
                    spacing: 8

                    Repeater {
                        model: [
                            { label: deck.audioTestArmed ? "ARMED" : "ARM TEST",
                              action: "arm" },
                            { label: "NEXT STREAM", action: "next" },
                            { label: "MUTE / 3S", action: "mute" },
                            { label: "VOLUME / 3S", action: "volume" }
                        ]

                        Rectangle {
                            id: experimentButton
                            required property var modelData

                            width: (audioTestButtons.width - 3 * audioTestButtons.spacing) / 4
                            height: 37
                            radius: 3
                            opacity: deck.transportMode === "mpris" ? 1.0 : 0.4
                            color: experimentMouse.containsMouse ? "#39333E" : "#29252E"
                            border.width: 1
                            border.color: deck.audioTestArmed
                                          && experimentButton.modelData.action === "arm"
                                          ? Colors.orange : Colors.cyan

                            GohuText {
                                anchors.centerIn: parent
                                text: experimentButton.modelData.label
                                font.pixelSize: 10
                                color: Colors.white
                            }

                            MouseArea {
                                id: experimentMouse
                                anchors.fill: parent
                                enabled: deck.transportMode === "mpris"
                                hoverEnabled: true
                                cursorShape: enabled ? Qt.PointingHandCursor
                                                     : Qt.ArrowCursor
                                onClicked: deck.handleAudioExperiment(
                                    experimentButton.modelData.action
                                )
                            }
                        }
                    }
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.topMargin: 259
                    text: "STREAM "
                          + (deck.selectedAudioCandidate
                             ? deck.selectedAudioCandidate.index : "NONE")
                          + " / " + deck.audioTestStatus
                    color: Colors.cyan
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    text: deck.transportMode === "mpris"
                          ? "3S EXPERIMENT // AUTO-RESTORE REQUESTED"
                          : "TRANSPORT // LOCAL MPD"
                    color: Colors.cyan
                    opacity: 0.6
                    font.pixelSize: 10
                }
            }
        }
    }
}
