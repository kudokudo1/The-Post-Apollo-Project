import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import "../services/audio"
import "../services/media"
import "../services/media/MediaAudioTargetResolver.js" as AudioTarget
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
    // The SurfaceFrame begins at the PanelWindow origin; no internal top gutter.
    property int panelTopMargin: 9
    property int panelLeftMargin: 200
    property int contentInset: 14
    property int sectionSpacing: 10
    // MPD remains the default. MPRIS is opt-in and targets one explicitly
    // selected external player; it is not a loaded YouTube playlist.
    property string transportMode: "mpd"
    property string catalogSource: "local-mpd"
    property int browseIndex: 0
    property int navigationZone: 1 // SOURCE / RESULTS / NOW
    property string browserStatus: "SEARCH LIBRARY, RADIO OR YOUTUBE"
    readonly property var browseItems:
        catalogSource === "direct-stream"
        ? [{ref: {source: "direct-stream", kind: "stream", id: radioStreamUrl},
            title: "Groove Salad", artist: "SomaFM"}]
        : headless.browse && headless.browse.source === catalogSource
          && Array.isArray(headless.browse.items) ? headless.browse.items : []
    readonly property string nextBrowseCursor:
        headless.browse && headless.browse.source === catalogSource
        ? String(headless.browse.nextCursor || "") : ""
    readonly property var highlightedItem:
        browseIndex >= 0 && browseIndex < browseItems.length
        ? browseItems[browseIndex] : null
    readonly property var tuningGroups: {
        const length = Math.max(1, Math.ceil(browseItems.length / 5));
        const labels = [];
        for (let i = 0; i < length; ++i)
            labels.push(String(1 + i * 5));
        return labels;
    }
    readonly property int tuningGroup: Math.floor(Math.max(0, browseIndex) / 5)
    onBrowseItemsChanged: {
        if (browseIndex >= browseItems.length)
            browseIndex = Math.max(0, browseItems.length - 1);
    }

    function highlightRow(index) {
        if (index < 0 || index >= browseItems.length)
            return false;
        browseIndex = index;
        navigationZone = 1;
        return true;
    }

    function tuneToGroup(index) {
        return highlightRow(Math.min(browseItems.length - 1, Math.max(0, index * 5)));
    }

    function toggleCatalogSource() {
        catalogSource = catalogSource === "local-mpd" ? "radio-browser"
            : catalogSource === "radio-browser" ? "youtube"
            : catalogSource === "youtube" ? "direct-stream" : "local-mpd";
        navigationZone = 0;
        browseIndex = 0;
        browserStatus = catalogSource === "youtube"
            ? "YOUTUBE CATALOG / REQUIRES API KEY / NO PLAYBACK"
            : catalogSource === "radio-browser"
              ? "RADIO DIRECTORY / SELECT THEN LOAD THEN PLAY"
              : catalogSource === "direct-stream"
                ? "RADIO PRESET / SELECT THEN LOAD / NO AUTOPLAY"
                : "LOCAL MPD LIBRARY";
    }

    function searchLibrary() {
        if (catalogSource === "direct-stream") {
            browserStatus = "RADIO / USE SELECT THEN LOAD";
            return;
        }
        const query = browserControls.queryText;
        if (!query.trim() && catalogSource !== "radio-browser") {
            browserStatus = "ENTER A SEARCH QUERY";
            return;
        }
        if (headless.searchMedia(catalogSource, query)) {
            browseIndex = 0;
            navigationZone = 1;
            browserStatus = catalogSource === "radio-browser"
                ? "RADIO DIRECTORY / SELECT THEN LOAD THEN PLAY"
                : "SEARCH REQUESTED / " + catalogSource.toUpperCase();
        } else {
            browserStatus = "SEARCH UNAVAILABLE / CONTROLLER BUSY";
        }
    }

    function nextRadioPage() {
        if (catalogSource !== "radio-browser" || !nextBrowseCursor) {
            browserStatus = "NO NEXT RADIO PAGE";
            return;
        }
        if (headless.searchMedia("radio-browser", browserControls.queryText, nextBrowseCursor)) {
            browseIndex = 0;
            browserStatus = "RADIO / NEXT PAGE REQUESTED";
        } else {
            browserStatus = "RADIO / NEXT PAGE UNAVAILABLE";
        }
    }

    function selectHighlighted() {
        const item = highlightedItem;
        if (!item || !item.ref) {
            browserStatus = "NO RESULT TO SELECT";
            return;
        }
        if (headless.selectMedia(item.ref))
            browserStatus = item.ref.source === "radio-browser"
                ? "STATION SELECTED / PRESS LOAD THEN PLAY"
                : "SELECT REQUESTED / NOT LOADED";
        else
            browserStatus = "SELECT UNAVAILABLE";
    }

    function loadStaged() {
        if (!headless.selection
                || (headless.selection.source !== "local-mpd"
                    && headless.selection.source !== "direct-stream"
                    && headless.selection.source !== "radio-browser")) {
            browserStatus = "STAGED SOURCE CANNOT LOAD INTO MPD";
            return;
        }
        if (headless.loadSelectedMedia())
            browserStatus = "LOAD REQUESTED / PLAY SEPARATELY";
        else
            browserStatus = "LOAD UNAVAILABLE";
    }

    function enterHighlighted() {
        if (navigationZone === 0) {
            toggleCatalogSource();
            return;
        }
        if (navigationZone === 2) {
            navigationZone = 1;
            return;
        }
        const item = highlightedItem;
        if (!item || !item.ref) {
            browserStatus = "NO RESULT TO OPEN";
            return;
        }
        if (item.ref.source === "youtube") {
            browserStatus = "YOUTUBE IS CATALOG-ONLY / NO PLAYBACK";
            return;
        }
        const requested = item.ref.source === "direct-stream"
            ? headless.loadRadio(item.ref.id) : headless.loadMedia(item.ref);
        if (requested)
            browserStatus = "ENTER / LOAD REQUESTED / PRESS PLAY";
        else
            browserStatus = "ENTER / LOAD UNAVAILABLE";
    }

    // Operator-selected initial radio station, not a searchable catalog.
    readonly property string radioStreamUrl:
        "https://ice5.somafm.com/groovesalad-128-mp3"

    HeadlessMediaController {
        id: headless
        polling: deck.menuOpen && deck.transportMode === "mpd"
    }

    MprisPlaybackAdapter {
        id: mediaAdapter
    }

    // B4 owner-mediated observation seam: references to the EXISTING objects.
    // ApolloHubLiveBridge reads snapshots and selected identity only. This
    // does not create a controller, select a player or change polling.
    readonly property var hubMediaController: headless
    readonly property string hubSelectedMprisBusName: mediaAdapter.selectedBusName

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

    // Exact-title evidence can select a stream automatically. Otherwise a
    // stream must be selected manually; disappearance never picks a neighbor.
    // Neither route establishes general browser-tab identity.
    readonly property string playerAudioBusName:
        mediaAdapter.activePlayer
        ? String(mediaAdapter.activePlayer.dbusName || "") : ""
    readonly property string playerAudioTitle:
        mediaAdapter.activePlayer
        ? String(mediaAdapter.activePlayer.trackTitle || "") : ""

    // AUTO FOLLOW stays active across tracks; NEXT STREAM is a manual
    // override for *this* MPRIS media title only.
    property bool autoFollowEnabled: true
    property var manualAudioBinding: null
    readonly property var audioTargetResolution:
        AudioTarget.resolve(playerAudioBusName, playerAudioTitle,
                            audioCandidateInputs,
                            autoFollowEnabled ? null : manualAudioBinding)
    readonly property var selectedAudioCandidate: audioTargetResolution.input
    readonly property int selectedAudioCandidatePosition:
        selectedAudioCandidate
        ? audioCandidateInputs.findIndex(function(input) {
            return Number(input.index) === Number(selectedAudioCandidate.index);
        }) : -1

    readonly property string audioSelectionLabel:
        selectedAudioCandidate
        ? ((audioTargetResolution.mode === "AUTO_TITLE" ? "AUTO" : "MANUAL")
           + " STREAM #" + selectedAudioCandidate.index
           + " (" + (selectedAudioCandidatePosition + 1)
           + "/" + audioCandidateInputs.length + ")")
        : "NO AUDIO TARGET"

    // A manual stream choice applies to one media session, not to every
    // browser tab the player may subsequently represent. On a new track,
    // expire the override and resume evidence-gated automatic following.
    readonly property string playerAudioSessionKey:
        playerAudioBusName + "|" + playerAudioTitle
    onPlayerAudioSessionKeyChanged: {
        audioTestArmed = false;
        armedAudioFingerprint = null;
        manualAudioBinding = null;
        autoFollowEnabled = true;
        audioTestStatus = "MEDIA CHANGED / AUTO FOLLOW";
        if (menuOpen && transportMode === "mpris")
            audioProbe.refresh();
    }

    // This is an explicitly armed *stream-level* experiment, not per-tab
    // targeting. A browser stream may contain multiple tabs.
    property bool audioTestArmed: false
    property var armedAudioFingerprint: null
    property string audioTestStatus: "NO EXPERIMENT RUN YET"

    function handleAudioExperiment(action) {
        if (action === "arm") {
            if (!selectedAudioCandidate) {
                audioTestArmed = false;
                armedAudioFingerprint = null;
                audioTestStatus = "NO TARGET / " + audioTargetResolution.status;
                return;
            }
            audioTestArmed = !audioTestArmed;
            armedAudioFingerprint = audioTestArmed
                ? AudioTarget.fingerprint(selectedAudioCandidate) : null;
            audioTestStatus = audioTestArmed
                ? "ARMED " + audioSelectionLabel : "EXPERIMENT DISARMED";
            return;
        }

        if (action === "auto") {
            audioTestArmed = false;
            armedAudioFingerprint = null;
            manualAudioBinding = null;
            autoFollowEnabled = true;
            audioTestStatus = "AUTO FOLLOW ON / " + audioTargetResolution.status;
            audioProbe.refresh();
            return;
        }

        if (action === "next") {
            audioTestArmed = false;
            armedAudioFingerprint = null;
            const inputs = audioCandidateInputs;
            if (inputs.length === 0) {
                audioTestStatus = "NO AUDIO STREAMS TO SELECT";
                return;
            }

            const nextPosition = selectedAudioCandidatePosition < 0
                ? 0 : (selectedAudioCandidatePosition + 1) % inputs.length;
            const next = inputs[nextPosition];
            const binding = AudioTarget.bindManual(playerAudioBusName,
                                                   playerAudioTitle, next);
            if (!binding) {
                audioTestStatus = "NO PROCESS EVIDENCE / NOT SELECTED";
                return;
            }

            manualAudioBinding = binding;
            autoFollowEnabled = false;
            audioTestStatus = "MANUAL SELECTED " + (nextPosition + 1)
                              + "/" + inputs.length + " • #" + next.index;
            console.log("MediaDeck: manually selected PipeWire stream",
                        next.index, "of", inputs.length, "candidates");
            return;
        }

        if (!audioTestArmed || audioExperimentProcess.running
                || transportMode !== "mpris")
            return;

        // A target can disappear or be replaced after ARM, particularly when
        // temporary TTS streams come and go. Never mutate the replacement.
        if (!selectedAudioCandidate
                || !AudioTarget.sameFingerprint(selectedAudioCandidate,
                                                armedAudioFingerprint)) {
            audioTestArmed = false;
            armedAudioFingerprint = null;
            audioTestStatus = "TARGET CHANGED / RE-ARM REQUIRED";
            return;
        }

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
        armedAudioFingerprint = null;
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
        if (menuOpen && transportMode === "mpris")
            audioProbe.refresh();
        if (menuOpen && transportMode === "mpd")
            headless.refresh();
    }

    function runTransport(action) {
        if (transportMode === "mpris") {
            if (!mediaAdapter.run(action))
                console.log("MediaDeck: MPRIS command unavailable", action);
            return;
        }
        if (!headless.transport(action))
            console.log("MediaDeck: controller command unavailable", action);
    }

    property real displayHeightShare: 0.27
    property real cassetteHeightShare: 0.21

    screen: Quickshell.screens.find(s => s.name === "DP-5")

    visible: menuOpen
    implicitWidth: panelWidth
    implicitHeight: panelHeight
    color: "transparent"
    exclusiveZone: 0

    WlrLayershell.layer: WlrLayer.Overlay
    // OnDemand is local to this Hi-Fi surface; external-owner handoff and
    // standalone Shift remain subject to actual SwayFX acceptance.
    WlrLayershell.keyboardFocus: menuOpen
        ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

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

            // Read-only display: input and clickable controls stay in Zone C.
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
                    anchors { left: parent.left; top: parent.top }
                    text: deck.transportMode === "mpd"
                        ? "HI-FI / MUSIC BROWSER" : "DISPLAY / EXTERNAL PLAYER"
                    color: Colors.cyan
                    font.pixelSize: 16
                }
                GohuText {
                    anchors { top: parent.top; topMargin: 27; left: parent.left; right: parent.right }
                    text: deck.transportMode === "mpd"
                        ? ("NOW: " + (headless.loaded
                            ? String(headless.loaded.item.title || "LOADED")
                            : "NO CASSETTE LOADED"))
                        : (mediaAdapter.connected
                            ? String(mediaAdapter.activePlayer.trackTitle || "NO TRACK")
                            : "NO EXTERNAL PLAYER")
                    color: Colors.white
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
                GohuText {
                    anchors { top: parent.top; topMargin: 49; left: parent.left; right: parent.right }
                    text: deck.transportMode === "mpd"
                        ? ("STATE: " + headless.playbackState.toUpperCase()
                           + " / " + (headless.ownsPlayback ? "OWNED" : "NOT OWNED"))
                        : ("MPRIS / " + deck.audioSelectionLabel)
                    color: Colors.orange
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
                GohuText {
                    anchors { top: parent.top; topMargin: 71; left: parent.left; right: parent.right }
                    text: deck.transportMode === "mpd"
                        ? ("RESULTS / " + deck.catalogSource.toUpperCase()
                           + " / " + deck.browseItems.length)
                        : ("AUDIO STREAM EVIDENCE / "
                           + deck.audioCandidateInputs.length + " CANDIDATES")
                    color: Colors.cyan
                    font.pixelSize: 11
                }

                Flickable {
                    id: resultViewport
                    anchors {
                        top: parent.top; topMargin: 91
                        left: parent.left; right: parent.right
                        bottom: parent.bottom; bottomMargin: 26
                    }
                    visible: deck.transportMode === "mpd"
                    clip: true
                    contentWidth: width
                    contentHeight: resultList.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds

                    Column {
                        id: resultList
                        width: resultViewport.width
                        spacing: 2
                        Repeater {
                            model: deck.browseItems
                            Rectangle {
                                id: resultRow
                                required property int index
                                required property var modelData
                                width: resultList.width
                                height: 22
                                radius: 2
                                color: index === deck.browseIndex
                                    ? "#34233D" : "transparent"
                                GohuText {
                                    anchors { fill: parent; leftMargin: 5; rightMargin: 4 }
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 11
                                    text: (resultRow.index === deck.browseIndex ? "▶ " : "  ")
                                        + String(resultRow.modelData.title || "(UNTITLED)")
                                        + " / " + String(resultRow.modelData.artist || "")
                                    color: resultRow.index === deck.browseIndex
                                        ? Colors.orange : Colors.white
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
                Connections {
                    target: deck
                    function onBrowseIndexChanged() {
                        if (!resultViewport.visible) return;
                        const rowY = deck.browseIndex * 24;
                        resultViewport.contentY = Math.min(
                            Math.max(0, resultViewport.contentHeight - resultViewport.height),
                            Math.max(0, rowY - resultViewport.height / 2)
                        );
                    }
                }
                GohuText {
                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                    text: deck.transportMode === "mpd"
                        ? (headless.errorText
                           ? "ERROR: " + headless.errorText
                           : deck.browserStatus + " / " + headless.message)
                        : (audioProbe.errorText || deck.audioTestStatus)
                    color: headless.errorText ? Colors.orange : Colors.cyan
                    font.pixelSize: 10
                    elide: Text.ElideRight
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

                // Independent radio cassette. A station click queues the URL;
                // it never autoplays, and PLAY is handled by the controller.
                Column {
                    id: radioCassette
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.topMargin: 28
                    spacing: 4
                    visible: deck.transportMode === "mpd"

                    GohuText {
                        text: "INTERNET RADIO / NO LOCAL LIBRARY REQUIRED"
                        font.pixelSize: 11
                        color: Colors.orange
                    }

                    Rectangle {
                        id: grooveCassette
                        width: radioCassette.width
                        height: 38
                        radius: 3
                        color: "#29252E"
                        border.width: 1
                        border.color: Colors.cyan
                        GohuText {
                            anchors.centerIn: parent
                            text: headless.loaded && headless.loaded.ref.source === "radio-browser"
                                ? String(headless.loaded.item.title || "RADIO") + " / INSERTED"
                                : headless.loaded && headless.loaded.ref.source === "direct-stream"
                                  ? "GROOVE SALAD / INSERTED" : "CASSETTE BAY / NOT INSERTED"
                            color: Colors.white
                            font.pixelSize: 12
                        }
                    }

                    GohuText {
                        width: parent.width
                        text: headless.loaded && (headless.loaded.ref.source === "direct-stream"
                                             || headless.loaded.ref.source === "radio-browser")
                              ? "CASSETTE: RADIO / QUEUED"
                              : "CASSETTE: EMPTY / SELECT STATION"
                        font.pixelSize: 11
                        color: Colors.cyan
                        elide: Text.ElideRight
                    }

                    GohuText {
                        text: "LOAD DOES NOT AUTOPLAY / PRESS PLAY BELOW"
                        font.pixelSize: 10
                        color: Colors.white
                    }
                }

                // Temporary read-only evidence bench. PipeWire media.name
                // often differs from an MPRIS track title, which must be
                // inspected before attempting any more automatic matching.
                // Do not infer browser-tab ownership from these observations.
                Column {
                    id: audioEvidenceRows
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.topMargin: 32
                    spacing: 4
                    visible: deck.transportMode === "mpris"
                             && deck.audioTargetResolution.mode !== "AUTO_TITLE"

                    GohuText {
                        text: "STREAM EVIDENCE / READ ONLY"
                              + (deck.audioCandidateInputs.length > 3
                                 ? " / FIRST 3 OF " + deck.audioCandidateInputs.length
                                 : "")
                        color: Colors.orange
                        font.pixelSize: 10
                    }

                    Repeater {
                        model: deck.audioCandidateInputs.slice(0, 3)

                        Column {
                            id: candidateEvidenceRow
                            required property var modelData
                            width: audioEvidenceRows.width
                            spacing: 0

                            GohuText {
                                width: parent.width
                                text: "#" + candidateEvidenceRow.modelData.index
                                      + "  MEDIA: "
                                      + String((candidateEvidenceRow.modelData.properties || {})
                                               ["media.name"] || "(none)")
                                color: Colors.cyan
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width
                                text: "APP: "
                                      + String((candidateEvidenceRow.modelData.properties || {})
                                               ["application.name"] || "(none)")
                                      + "  /  BIN: "
                                      + String((candidateEvidenceRow.modelData.properties || {})
                                               ["application.process.binary"] || "(none)")
                                      + "  /  PID: "
                                      + String((candidateEvidenceRow.modelData.properties || {})
                                               ["application.process.id"] || "(none)")
                                color: Colors.white
                                opacity: 0.75
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            // All UI inputs live in the control bay, separate from the display.
            SectionFrame {
                id: controlSection
                width: parent.width
                height: deckSections.height - displaySection.height
                        - cassetteSection.height - 2 * deckSections.spacing
                inset: 14
                fillColor: Colors.black
                fillOpacity: 0.48
                borderColor: Colors.cyan
                borderOpacity: 0.68

                FocusScope {
                    id: controlKeys
                    anchors.fill: parent
                    focus: true
                    property bool shiftCandidate: false
                    // Fail closed until modifier-only events and cross-widget
                    // ownership have been verified on the compositor.
                    property bool standaloneShiftVerified: false
                    Keys.priority: Keys.BeforeItem
                    Keys.onPressed: function(event) {
                        if (!deck.menuOpen || deck.transportMode !== "mpd")
                            return;
                        if (event.key === Qt.Key_Shift) {
                            shiftCandidate = standaloneShiftVerified
                                && !browserControls.searchEditing
                                && !event.isAutoRepeat
                                && (event.modifiers === Qt.ShiftModifier);
                            return;
                        }
                        shiftCandidate = false;
                        if (browserControls.searchEditing
                                || event.modifiers !== Qt.NoModifier)
                            return;
                        if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
                            deck.highlightRow(deck.browseIndex
                                + (event.key === Qt.Key_Down ? 1 : -1));
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Left || event.key === Qt.Key_Right) {
                            deck.navigationZone = Math.max(0, Math.min(2,
                                deck.navigationZone + (event.key === Qt.Key_Right ? 1 : -1)));
                            event.accepted = true;
                        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                            deck.enterHighlighted();
                            event.accepted = true;
                        }
                    }
                    Keys.onReleased: function(event) {
                        if (event.key !== Qt.Key_Shift) return;
                        const selectNow = shiftCandidate
                            && standaloneShiftVerified
                            && deck.menuOpen && !browserControls.searchEditing;
                        shiftCandidate = false;
                        if (selectNow) {
                            deck.selectHighlighted();
                            event.accepted = true;
                        }
                    }
                    TapHandler {
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        onPressedChanged: if (pressed) controlKeys.shiftCandidate = false
                    }

                    GohuText {
                        anchors { top: parent.top; left: parent.left }
                        text: "CONTROLS"
                        color: Colors.cyan
                        font.pixelSize: 16
                    }
                    Row {
                        id: modeRow
                        anchors {
                            top: parent.top; topMargin: 23
                            left: parent.left; right: parent.right
                        }
                        spacing: 7
                        height: 30

                        ActionButton {
                            width: (modeRow.width - 2 * modeRow.spacing) / 3
                            height: parent.height
                            label: "HI-FI / MPD"
                            labelPixelSize: 11
                            selected: deck.transportMode === "mpd"
                            onClicked: deck.transportMode = "mpd"
                        }
                        ActionButton {
                            width: (modeRow.width - 2 * modeRow.spacing) / 3
                            height: parent.height
                            label: "USE MPRIS"
                            labelPixelSize: 11
                            selected: deck.transportMode === "mpris"
                            onClicked: {
                                if (!mediaAdapter.connected && !mediaAdapter.selectNextPlayer())
                                    return;
                                deck.transportMode = "mpris";
                                audioProbe.refresh();
                            }
                        }
                        ActionButton {
                            width: (modeRow.width - 2 * modeRow.spacing) / 3
                            height: parent.height
                            label: "NEXT PLAYER"
                            labelPixelSize: 11
                            available: mediaAdapter.availablePlayers.length > 0
                            onClicked: {
                                if (mediaAdapter.selectNextPlayer()) {
                                    deck.transportMode = "mpris";
                                    audioProbe.refresh();
                                }
                            }
                        }
                    }

                    MediaDeckBrowserControls {
                        id: browserControls
                        anchors {
                            top: modeRow.bottom; topMargin: 4
                            left: parent.left; right: parent.right
                        }
                        height: 194
                        deckHost: deck
                        controller: headless
                        opacity: deck.transportMode === "mpd" ? 1.0 : 0.30
                        enabled: deck.transportMode === "mpd"
                    }

                    Grid {
                        id: transportGrid
                        anchors {
                            top: browserControls.bottom; topMargin: 5
                            left: parent.left; right: parent.right
                        }
                        height: 82
                        columns: 4
                        spacing: 6

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
                                readonly property bool localCanControl:
                                    !!headless.loaded && !headless.busy
                                    && (modelData.action === "play"
                                        || (headless.ownsPlayback
                                            && (modelData.action === "pause"
                                                || modelData.action === "stop"
                                                || (!headless.loaded.item.live
                                                    && ["previous", "next", "rewind5",
                                                        "forward5"].indexOf(modelData.action) !== -1))))
                                readonly property bool canControl:
                                    deck.transportMode === "mpris"
                                    ? mediaAdapter.supports(modelData.action)
                                    : localCanControl
                                width: (transportGrid.width - 3 * transportGrid.spacing) / 4
                                height: 38
                                radius: 3
                                opacity: transportKey.canControl ? 1.0 : 0.45
                                color: keyMouse.pressed ? "#16131B"
                                    : keyMouse.containsMouse ? "#39333E" : "#29252E"
                                border.width: 1
                                border.color: keyMouse.pressed ? Colors.orange
                                    : keyMouse.containsMouse ? Colors.cyan : "#69616F"
                                transform: Translate { y: keyMouse.pressed ? 1 : 0 }
                                GohuText {
                                    anchors.centerIn: parent
                                    text: transportKey.modelData.label
                                    font.pixelSize: 11
                                    color: keyMouse.pressed ? Colors.orange
                                        : keyMouse.containsMouse ? Colors.cyan : Colors.white
                                }
                                MouseArea {
                                    id: keyMouse
                                    anchors.fill: parent
                                    enabled: transportKey.canControl
                                    acceptedButtons: Qt.LeftButton
                                    hoverEnabled: true
                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: deck.runTransport(transportKey.modelData.action)
                                }
                            }
                        }
                    }

                    Row {
                        id: audioTestButtons
                        anchors {
                            top: transportGrid.bottom; topMargin: 4
                            left: parent.left; right: parent.right
                        }
                        height: 29
                        spacing: 6
                        visible: deck.transportMode === "mpris"
                        Repeater {
                            model: [
                                {label: deck.audioTestArmed ? "ARMED" : "ARM TEST", action: "arm"},
                                {label: "NEXT STREAM", action: "next"},
                                {label: "MUTE / 3S", action: "mute"},
                                {label: "VOLUME / 3S", action: "volume"}
                            ]
                            ActionButton {
                                required property var modelData
                                width: (audioTestButtons.width - 3 * audioTestButtons.spacing) / 4
                                height: 29
                                label: modelData.label
                                labelPixelSize: 10
                                available: deck.transportMode === "mpris"
                                enabled: deck.transportMode === "mpris"
                                onClicked: deck.handleAudioExperiment(modelData.action)
                            }
                        }
                    }
                    GohuText {
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                        font.pixelSize: 10
                        color: Colors.orange
                        text: deck.transportMode === "mpd"
                            ? "SELECT ≠ LOAD ≠ PLAY / SHIFT KEY PENDING FOCUS PROOF"
                            : "3S AUDIO EXPERIMENT / STREAM MAY COVER MANY TABS"
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
