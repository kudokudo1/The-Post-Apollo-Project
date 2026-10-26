import QtQuick
import QtQuick.Controls
import "../../components"

// P3-A: one passive view of the EXISTING Volumebar PipeWire sink.
// No second PwObjectTracker, Process, PipeWire mutation, timer or stream
// identity provider. Mutations are explicit requests to the shell owner.
Item {
    id: audioMini

    property var audioSnapshot: null
    property int volumeDraft: 0
    property bool volumeDirty: false
    signal muteRequested(bool muted)
    signal volumeRequested(int percent)
    signal inputFocusChanged(bool focused)

    readonly property int densityLevel: height >= 300 ? 3 : height >= 170 ? 2 : 1
    readonly property bool outputReady:
        audioSnapshot !== null && audioSnapshot.state === "ready"
    readonly property int observedPercent:
        outputReady && typeof audioSnapshot.volumePercent === "number"
        && isFinite(audioSnapshot.volumePercent)
        ? Math.max(0, Math.min(300, Math.round(audioSnapshot.volumePercent))) : -1
    readonly property bool observedMuted:
        outputReady && audioSnapshot.muted === true
    readonly property string outputName:
        outputReady && typeof audioSnapshot.outputName === "string"
        ? audioSnapshot.outputName : "NO DEFAULT OUTPUT"
    readonly property string actionFeedback:
        audioSnapshot && typeof audioSnapshot.requestStatus === "string"
        ? audioSnapshot.requestStatus : "NO ACTION REQUESTED"
    readonly property string statusLine:
        outputReady ? ("AUDIO // " + (observedMuted ? "MUTED" : "LIVE")
                       + " // " + observedPercent + "% // OBSERVED")
        : "AUDIO // OWNER UNAVAILABLE"

    onAudioSnapshotChanged: {
        if (outputReady && !volumeDirty)
            volumeDraft = observedPercent;
    }
    onOutputReadyChanged: {
        if (!outputReady) {
            volumeDirty = false;
            inputFocusChanged(false);
        }
    }
    onVisibleChanged: {
        if (!visible)
            inputFocusChanged(false);
    }

    function requestIncrement(delta) {
        if (!outputReady || !Number.isInteger(delta))
            return;
        // Use the observed value for this one-shot action. No optimistic
        // claim of success; the live owner's next observation is authoritative.
        const target = Math.max(0, Math.min(300, observedPercent + delta));
        volumeRequested(target);
    }

    function applyVolume() {
        if (!outputReady || !volumeDirty || !Number.isInteger(volumeDraft))
            return;
        volumeRequested(volumeDraft);
        volumeDirty = false;
    }

    GohuText {
        id: outputStatus
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 20
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        color: audioMini.outputReady ? Colors.cyan : Colors.orange
        font.pixelSize: 12
        text: audioMini.outputReady
              ? (audioMini.observedMuted ? "OUTPUT MUTED" : "OUTPUT ACTIVE")
                + " // " + String(audioMini.observedPercent) + "%"
              : "DEFAULT OUTPUT UNAVAILABLE"
    }

    Row {
        id: quickActions
        anchors.top: outputStatus.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        height: 28
        spacing: 5

        ActionButton {
            width: Math.max(1, (parent.width - parent.spacing * 2) / 3)
            height: parent.height
            label: "-5%"
            labelPixelSize: 11
            available: audioMini.outputReady && audioMini.observedPercent > 0
            softGlowEnabled: false
            onLeftClicked: audioMini.requestIncrement(-5)
        }
        ActionButton {
            width: Math.max(1, (parent.width - parent.spacing * 2) / 3)
            height: parent.height
            label: audioMini.observedMuted ? "UNMUTE" : "MUTE"
            labelPixelSize: 11
            available: audioMini.outputReady
            softGlowEnabled: false
            onLeftClicked: audioMini.muteRequested(!audioMini.observedMuted)
        }
        ActionButton {
            width: Math.max(1, (parent.width - parent.spacing * 2) / 3)
            height: parent.height
            label: "+5%"
            labelPixelSize: 11
            available: audioMini.outputReady && audioMini.observedPercent < 300
            softGlowEnabled: false
            onLeftClicked: audioMini.requestIncrement(5)
        }
    }

    GohuText {
        visible: audioMini.densityLevel === 1
        anchors.top: quickActions.bottom
        anchors.topMargin: 5
        anchors.left: parent.left
        anchors.right: parent.right
        height: 16
        font.pixelSize: 10
        color: audioMini.observedPercent > 100 ? Colors.orange : Colors.cyan
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        text: audioMini.observedPercent > 100
              ? "BOOSTED OUTPUT // ABOVE 100%"
              : "DEFAULT SINK // DIRECT CONTROL"
    }

    Column {
        id: expanded
        visible: audioMini.densityLevel > 1
        anchors.top: quickActions.bottom
        anchors.topMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 6

        GohuText {
            width: parent.width
            height: 18
            text: "VOLUME // " + String(audioMini.volumeDraft)
                  + "% // RANGE 0–300%"
            color: audioMini.volumeDraft > 100 ? Colors.orange : Colors.cyan
            font.pixelSize: 11
        }

        Slider {
            id: outputVolumeSlider
            width: parent.width
            height: 27
            from: 0
            to: 300
            stepSize: 5
            value: audioMini.volumeDraft
            enabled: audioMini.outputReady
            onMoved: {
                audioMini.volumeDraft = Math.round(value);
                audioMini.volumeDirty = true;
            }
            onActiveFocusChanged: audioMini.inputFocusChanged(activeFocus)
        }

        Row {
            width: parent.width
            height: 28
            spacing: 5
            ActionButton {
                width: Math.max(1, (parent.width - parent.spacing) / 2)
                height: parent.height
                label: "APPLY VOLUME"
                labelPixelSize: 10
                available: audioMini.outputReady && audioMini.volumeDirty
                softGlowEnabled: false
                onLeftClicked: audioMini.applyVolume()
            }
            ActionButton {
                width: Math.max(1, (parent.width - parent.spacing) / 2)
                height: parent.height
                label: "RESET DRAFT"
                labelPixelSize: 10
                available: audioMini.outputReady && audioMini.volumeDirty
                softGlowEnabled: false
                onLeftClicked: {
                    audioMini.volumeDirty = false;
                    audioMini.volumeDraft = audioMini.observedPercent;
                }
            }
        }

        GohuText {
            width: parent.width
            height: audioMini.densityLevel === 3 ? 32 : 17
            text: audioMini.densityLevel === 3
                  ? "DEFAULT SINK // " + audioMini.outputName
                  : audioMini.actionFeedback
            font.pixelSize: 10
            color: Colors.cyan
            elide: Text.ElideRight
            wrapMode: audioMini.densityLevel === 3 ? Text.WordWrap : Text.NoWrap
        }

        GohuText {
            visible: audioMini.densityLevel === 3
            width: parent.width
            height: 34
            font.pixelSize: 10
            color: Colors.orange
            wrapMode: Text.WordWrap
            text: audioMini.actionFeedback
                  + " // ACTION REQUESTS ARE NOT VERIFIED OUTCOMES"
        }
    }
}
