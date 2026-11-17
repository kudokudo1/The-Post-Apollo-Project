import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "PhoneFaceTimeLinks.js" as FaceTimeLinks

// Shared, user-initiated FaceTime Audio/Video handoff in existing PHONE views.
// This never opens facetime: schemes on Linux and never claims a native call.
// Apple-device URI is selectable text only. The only external action is an
// explicitly reviewed, exact-origin FaceTime HTTPS invitation.
Rectangle {
    id: handoff
    property string mode: "video"
    property var contact: null
    property string reviewedInvite: ""
    property string result: "IDLE"
    // Explicit local HFP observation is independent from FaceTime call state.
    property string audioRouteState: "NOT_CHECKED"
    property var audioRouteObservation: ({})
    property int audioRouteGeneration: 0
    signal closeRequested()

    width: parent ? parent.width : 320
    height: handoffColumn.implicitHeight + 24
    color: Colors.dark
    border.width: 1
    border.color: mode === "audio" ? Colors.cyan : Colors.orange
    clip: true

    function clear() {
        reviewedInvite = "";
        result = "IDLE";
        audioRouteGeneration += 1;
        audioRouteState = "NOT_CHECKED";
        audioRouteObservation = ({});
        // No stale device status should survive contact, mode or view loss.
        if (audioRouteProcess && audioRouteProcess.running)
            audioRouteProcess.running = false;
        // Mode/contact initialization may precede child creation in QML.
        if (inviteInput)
            inviteInput.text = "";
    }

    function inspectAudioRoute() {
        if (!visible || mode !== "audio" || audioRouteProcess.running)
            return;
        audioRouteGeneration += 1;
        audioRouteState = "CHECKING";
        audioRouteObservation = ({});
        audioRouteProcess.generation = audioRouteGeneration;
        audioRouteProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneFaceTimeAudioRouteProbe.py"),
            "--status"
        ];
        audioRouteProcess.running = true;
    }

    function audioRouteMessage() {
        switch (audioRouteState) {
        case "CHECKING":
            return "CHECKING LOCAL HANDS-FREE AUDIO // No call or device setting will change.";
        case "HFP_SYSTEM_PROFILE_ACTIVE":
            return "SYSTEM HFP PROFILE ACTIVE // A Bluetooth hands-free profile is selected on this PC, but it may belong to another device. FaceTime, microphone and speaker are NOT verified.";
        case "HFP_PROFILE_AVAILABLE_ONLY":
            return "HFP PROFILE AVAILABLE // Not selected in the observed audio card. Use the iPhone audio picker during a real FaceTime Audio call; routing remains unverified.";
        case "HFP_PROFILE_NOT_OBSERVED":
            return "HFP NOT OBSERVED IN PACTL CARDS // This is not proof FaceTime Audio is impossible. oFono may use a separate audio route.";
        case "PHONE_CALLS_NOT_READY":
            return "CELLULAR HFP NOT READY // BlueFerry does not report its hands-free call path ready. This does not diagnose an active FaceTime session.";
        case "PHONE_BRIDGE_UNAVAILABLE":
            return "BLUEFERRY STATUS UNAVAILABLE // Local audio profiles alone cannot prove iPhone or FaceTime connectivity.";
        case "AUDIO_INSPECTION_UNAVAILABLE":
        case "UNAVAILABLE":
            return "AUDIO ROUTE CHECK UNAVAILABLE // Local status could not be read. No device settings changed.";
        default:
            return "FACETIME AUDIO NOT VERIFIED // Select CHECK AUDIO ROUTE to inspect existing BlueFerry and PipeWire observations without changing anything.";
        }
    }

    Process {
        id: audioRouteProcess
        property int generation: 0
        stdout: StdioCollector {
            onStreamFinished: {
                if (!handoff.visible || handoff.mode !== "audio"
                        || audioRouteProcess.generation !== handoff.audioRouteGeneration)
                    return;
                try {
                    var observed = JSON.parse(String(text || ""));
                    var allowed = ["AUDIO_INSPECTION_UNAVAILABLE", "PHONE_BRIDGE_UNAVAILABLE",
                                   "PHONE_CALLS_NOT_READY", "HFP_PROFILE_NOT_OBSERVED",
                                   "HFP_PROFILE_AVAILABLE_ONLY", "HFP_SYSTEM_PROFILE_ACTIVE"];
                    var flags = ["phoneBackendObserved", "cellularHfpReadyReported",
                                 "systemAudioObserved", "systemHfpProfileOffered",
                                 "systemHfpProfileActive"];
                    if (!observed
                            || observed.schema !== "post-apollo.phone.facetime-audio-route.v1"
                            || observed.execution !== "READ_ONLY_USER_INITIATED"
                            || allowed.indexOf(observed.state) < 0
                            || observed.faceTimeAudioVerified !== false
                            || observed.faceTimeConnected !== false
                            || observed.faceTimeCallControl !== false
                            || observed.microphoneVerified !== false
                            || observed.speakerVerified !== false
                            || observed.canChangeRoute !== false
                            || observed.providerAuthenticated !== false
                            || observed.personalDataAccess !== false)
                        throw new Error("invalid route response");
                    for (var i = 0; i < flags.length; ++i) {
                        if (typeof observed[flags[i]] !== "boolean")
                            throw new Error("invalid route flag");
                    }
                    if (observed.systemHfpProfileActive
                            && (!observed.systemHfpProfileOffered
                                || !observed.systemAudioObserved))
                        throw new Error("invalid HFP profile evidence");
                    handoff.audioRouteObservation = ({
                        state: observed.state,
                        cellularHfpReadyReported: observed.cellularHfpReadyReported,
                        systemHfpProfileActive: observed.systemHfpProfileActive
                    });
                    handoff.audioRouteState = observed.state;
                } catch (error) {
                    handoff.audioRouteObservation = ({});
                    handoff.audioRouteState = "UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (handoff.visible && handoff.mode === "audio"
                    && generation === handoff.audioRouteGeneration
                    && code !== 0) {
                handoff.audioRouteObservation = ({});
                handoff.audioRouteState = "UNAVAILABLE";
            }
        }
    }

    function reviewInvite() {
        if (!visible)
            return;
        reviewedInvite = FaceTimeLinks.normalizeInvite(inviteInput.text);
        result = reviewedInvite !== "" ? "REVIEW" : "INVALID";
    }

    function openReviewedInvite() {
        if (!visible || result !== "REVIEW"
                || reviewedInvite === ""
                || reviewedInvite !== FaceTimeLinks.normalizeInvite(inviteInput.text)) {
            reviewedInvite = "";
            result = "INVALID";
            return;
        }
        // Only this second explicit click may hand off the validated HTTPS
        // link to the default browser. No WebRTC join is implied by success.
        var selected = reviewedInvite;
        reviewedInvite = "";
        result = Qt.openUrlExternally(selected) ? "BROWSER_REQUESTED" : "OPEN_FAILED";
    }

    onModeChanged: clear()
    onContactChanged: clear()
    onVisibleChanged: {
        if (!visible)
            clear();
    }

    Column {
        id: handoffColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 9

        Text {
            width: parent.width
            text: handoff.mode === "audio" ? "FACETIME AUDIO // HANDOFF" : "FACETIME VIDEO // HANDOFF"
            color: handoff.mode === "audio" ? Colors.cyan : Colors.orange
            font.bold: true
            font.pixelSize: 12
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "NATIVE LINUX FACETIME // NOT CONNECTED"
            color: Colors.orange
            font.pixelSize: 11
            font.bold: true
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: FaceTimeLinks.supportMessage(handoff.mode)
            color: Colors.white
            font.pixelSize: 11
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            visible: handoff.mode === "audio"
            text: "IPHONE → BLUETOOTH → PC // READ-ONLY ROUTE CHECK"
            color: Colors.cyan
            font.bold: true
            font.pixelSize: 11
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: Math.min(230, handoffColumn.width)
            height: 33
            visible: handoff.mode === "audio"
            label: audioRouteProcess.running ? "CHECKING AUDIO..." : "CHECK AUDIO ROUTE"
            labelPixelSize: 10
            accentColor: Colors.magenta
            interactive: !audioRouteProcess.running
            onTriggered: handoff.inspectAudioRoute()
        }
        Text {
            width: parent.width
            visible: handoff.mode === "audio"
            text: handoff.audioRouteMessage()
            color: Colors.orange
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            visible: handoff.mode === "audio"
            text: "REAL TEST // Start FaceTime Audio on the iPhone, select the available PC/Bluetooth audio endpoint on the iPhone itself, and verify sound and microphone with a consenting caller. PHONE cannot observe which iPhone app owns the HFP stream."
            color: Colors.white
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "JOIN AN INVITED FACETIME CALL // WEB"
            color: Colors.cyan
            font.pixelSize: 11
            font.bold: true
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 37
            border.width: 1
            border.color: Colors.magenta
            color: Colors.black
            TextInput {
                id: inviteInput
                anchors.fill: parent
                anchors.margins: 7
                color: Colors.magenta
                font.pixelSize: 11
                maximumLength: 2048
                selectByMouse: true
                clip: true
                cursorDelegate: Rectangle {
                    width: 2
                    height: inviteInput.font.pixelSize + 2
                    color: Colors.orange
                }
                onTextChanged: {
                    handoff.reviewedInvite = "";
                    handoff.result = "IDLE";
                }
            }
            Text {
                anchors.fill: parent
                anchors.margins: 7
                visible: inviteInput.text.length === 0
                text: "Paste https://facetime.apple.com/join#..."
                color: Colors.white
                opacity: 0.55
                font.pixelSize: 10
                verticalAlignment: Text.AlignVCenter
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
        }
        Row {
            width: parent.width
            spacing: 8
            ActionButton {
                width: Math.max(0, (handoffColumn.width - 8) / 2)
                height: 34
                label: "REVIEW INVITE"
                labelPixelSize: 10
                accentColor: Colors.magenta
                interactive: inviteInput.text.length > 0
                onTriggered: handoff.reviewInvite()
            }
            ActionButton {
                width: Math.max(0, (handoffColumn.width - 8) / 2)
                height: 34
                label: "OPEN INVITE"
                labelPixelSize: 10
                accentColor: Colors.green
                interactive: handoff.result === "REVIEW"
                             && handoff.reviewedInvite !== ""
                             && handoff.reviewedInvite === FaceTimeLinks.normalizeInvite(inviteInput.text)
                onTriggered: handoff.openReviewedInvite()
            }
        }
        Text {
            width: parent.width
            text: handoff.result === "REVIEW"
                  ? "APPLE INVITE REVIEWED // Opening sends the invitation token to the browser. Join only if you trust its sender."
                  : handoff.result === "INVALID"
                    ? "INVALID INVITE // Paste a complete HTTPS FaceTime invitation from facetime.apple.com. No browser opened."
                    : handoff.result === "BROWSER_REQUESTED"
                      ? "BROWSER OPEN REQUESTED // Join in Chrome or Edge; browser access, microphone, camera and host approval are separate."
                      : handoff.result === "OPEN_FAILED"
                        ? "NO BROWSER HANDOFF // No external application accepted the request."
                        : "FaceTime invite required. Chrome or Edge recommended; FaceTime Audio cannot be started directly from Linux."
            color: handoff.result === "INVALID" || handoff.result === "OPEN_FAILED"
                   ? Colors.orange : Colors.white
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: "APPLE-DEVICE CONTACT HANDOFF // NO LINUX DIAL"
            color: Colors.cyan
            font.bold: true
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        Rectangle {
            width: parent.width
            height: 32
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan
            TextInput {
                id: appleDeviceLink
                anchors.fill: parent
                anchors.margins: 6
                text: FaceTimeLinks.appleDeviceLink(handoff.mode, handoff.contact)
                color: Colors.cyan
                font.pixelSize: 11
                readOnly: true
                selectByMouse: true
                clip: true
            }
        }
        Text {
            width: parent.width
            text: appleDeviceLink.text !== ""
                  ? "Optional: select and copy the link above for use on an Apple device. It does not place a call from this Linux desktop. Verify the person on your iPhone."
                  : "Select an authorized contact with a phone number or email to prepare an Apple-device link; otherwise start the call on your iPhone."
            color: Colors.white
            opacity: 0.86
            font.pixelSize: 10
            textFormat: Text.PlainText
            wrapMode: Text.WordWrap
        }
        ActionButton {
            width: Math.min(130, handoffColumn.width)
            height: 31
            label: "CLOSE FACETIME"
            labelPixelSize: 10
            accentColor: Colors.orange
            onTriggered: handoff.closeRequested()
        }
    }
}
