import QtQuick
import Quickshell
import QtQuick.Effects
import qs.components

Rectangle {
    id: root

    required property var registryService
    required property var intercomService
    required property var speechInputService

    property string workingDirectory: ""
    property string floorLabel: "NO FLOOR"
    property string roomLabel: "NO ROOM"
    property int channelIndex: 0
    property int selectedSpecialistIndex: 0
    property var channelModes: ["ROOM", "FLOOR", "SPECIALIST", "HOSPITAL"]

    signal typingChanged(bool active)

    readonly property string channelType:
        String(channelModes[Math.max(0, Math.min(channelModes.length - 1, channelIndex))] || "HOSPITAL")
    readonly property var selectedSpecialist:
        registryService.specialistAt(selectedSpecialistIndex)
    readonly property string selectedSpecialistId:
        selectedSpecialist ? String(selectedSpecialist.id || "") : ""
    readonly property string channelLabel: {
        if (focusedChannelLabel
                && focusedChannelType === channelType)
            return focusedChannelLabel;

        if (channelType === "ROOM")
            return String(roomLabel || "NO ROOM");

        if (channelType === "FLOOR")
            return String(floorLabel || "NO FLOOR");

        if (channelType === "SPECIALIST")
            return selectedSpecialist
                ? String(selectedSpecialist.name || selectedSpecialist.id || "SPECIALIST")
                : "NO SPECIALIST";

        return "HOSPITAL WIDE";
    }
    property string focusedChannelType: ""
    property string focusedChannelLabel: ""

    readonly property var currentMessages:
        intercomService.messagesFor(
            channelType,
            (
                focusedChannelLabel
                && focusedChannelType === channelType
                ? focusedChannelLabel
                : channelLabel
            ),
            selectedSpecialistId
        )

    function focusSpecialistId(value) {
        const wanted = String(value || "").trim();
        const rows =
            root.registryService
            && Array.isArray(root.registryService.specialists)
            ? root.registryService.specialists
            : [];

        if (!wanted)
            return false;

        for (let i = 0; i < rows.length; ++i) {
            if (String((rows[i] || {}).id || "") !== wanted)
                continue;

            selectedSpecialistIndex = i;
            return true;
        }

        return false;
    }

    function focusActivityContext(
            specialistIdValue,
            channelTypeValue,
            channelLabelValue) {
        const type =
            String(channelTypeValue || "").trim().toUpperCase();
        const label =
            String(channelLabelValue || "").trim();

        focusSpecialistId(specialistIdValue);

        const modeIndex = channelModes.indexOf(type);

        if (modeIndex >= 0)
            channelIndex = modeIndex;

        focusedChannelType =
            modeIndex >= 0 ? type : "";
        focusedChannelLabel =
            modeIndex >= 0 ? label : "";

        return selectedSpecialist !== null;
    }

    function clearFocusedChannel() {
        focusedChannelType = "";
        focusedChannelLabel = "";
    }

    function sendCurrent() {
        const specialist = selectedSpecialist;
        const body = String(messageInput.text || "").trim();

        if (!specialist || !body)
            return false;

        if (!intercomService.sendMessage(
                specialist,
                channelType,
                channelLabel,
                body,
                workingDirectory))
            return false;

        messageInput.text = "";
        Qt.callLater(function() {
            transcript.contentY = Math.max(
                0,
                transcript.contentHeight - transcript.height
            );
        });
        return true;
    }

    function sendCurrentVoiceAware() {
        if (speechInputService.recording)
            return speechInputService.stopRecording(true);

        if (speechInputService.stopping
                || speechInputService.transcribing)
            return false;

        return sendCurrent();
    }

    function acceptVoiceTranscript(
            textValue,
            submitRequested) {
        const spoken =
            String(textValue || "").trim();

        if (!spoken)
            return false;

        const existing =
            String(messageInput.text || "").trim();

        messageInput.text =
            existing
            ? existing + " " + spoken
            : spoken;
        messageInput.cursorPosition =
            messageInput.text.length;
        messageInput.forceActiveFocus();

        if (submitRequested) {
            Qt.callLater(function() {
                root.sendCurrent();
            });
        }

        return true;
    }

    Connections {
        target: root.speechInputService

        function onTranscriptionReady(
                text,
                submitRequested) {
            root.acceptVoiceTranscript(
                text,
                submitRequested
            );
        }
    }

    onVisibleChanged: {
        if (!visible) {
            if (speechInputService.busy)
                speechInputService.cancel();

            messageInput.focus = false;
            typingChanged(false);
            return;
        }

        if (selectedSpecialistIndex >= registryService.specialistCount)
            selectedSpecialistIndex = 0;
    }

    width: 430
    height: 390
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta

    RectangularShadow {
        anchors.fill: parent
        spread: 5
        z: -1
        opacity: 0.42
        color: Colors.magenta
    }

    GohuText {
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            leftMargin: 11
            rightMargin: 11
            topMargin: 9
        }

        height: 22
        text: "INTERCOM // " + root.channelType
        font.pixelSize: 12
        color: Colors.magenta
        elide: Text.ElideRight
    }

    Row {
        id: channelRow

        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            leftMargin: 8
            rightMargin: 8
            topMargin: 36
        }

        height: 32
        spacing: 5

        Repeater {
            model: root.channelModes

            Rectangle {
                required property string modelData
                required property int index

                width: (channelRow.width - 15) / 4
                height: 30
                color:
                    index === root.channelIndex
                    ? Colors.yellow
                    : channelMouse.pressed
                    ? Colors.black
                    : Colors.dark
                border.width:
                    index === root.channelIndex
                    || channelMouse.containsMouse
                    ? 2 : 1
                border.color:
                    index === root.channelIndex
                    ? Colors.magenta
                    : channelMouse.containsMouse
                    ? Colors.orange
                    : Colors.cyan

                GohuText {
                    anchors.centerIn: parent
                    text: parent.modelData
                    font.pixelSize: 9
                    color:
                        parent.index === root.channelIndex
                        ? Colors.magenta
                        : channelMouse.containsMouse
                        ? Colors.orange
                        : Colors.cyan
                }

                MouseArea {
                    id: channelMouse

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked: {
                        root.clearFocusedChannel();
                        root.channelIndex = parent.index;
                    }
                }
            }
        }
    }

    Column {
        id: recipientColumn

        anchors {
            left: parent.left
            right: parent.right
            top: channelRow.bottom
            leftMargin: 8
            rightMargin: 8
            topMargin: 8
        }

        spacing: 5

        GohuText {
            width: parent.width
            text:
                "CHANNEL // "
                + root.channelLabel
                + "    TO // "
                + (
                    root.selectedSpecialist
                    ? String(
                        root.selectedSpecialist.name
                        || root.selectedSpecialist.id
                        || "SPECIALIST"
                    )
                    : "NO SPECIALIST"
                  )
            font.pixelSize: 10
            color: Colors.white
            elide: Text.ElideRight
        }

        Row {
            id: recipientRow

            width: parent.width
            height: 30
            spacing: 5

            Repeater {
                model: root.registryService.specialists

                Rectangle {
                    required property var modelData
                    required property int index

                    readonly property string presence:
                        String(modelData.presence || "UNKNOWN").toUpperCase()
                    readonly property color stateColor:
                        presence === "READY"
                        ? Colors.green
                        : presence === "OFFLINE"
                        ? Colors.red
                        : Colors.orange

                    width:
                        Math.max(
                            86,
                            (
                                recipientRow.width
                                - Math.max(
                                    0,
                                    root.registryService.specialistCount - 1
                                  ) * recipientRow.spacing
                            )
                            / Math.max(
                                1,
                                root.registryService.specialistCount
                              )
                        )
                    height: 30
                    color:
                        index === root.selectedSpecialistIndex
                        ? Colors.yellow
                        : recipientMouse.pressed
                        ? Colors.black
                        : Colors.dark
                    border.width:
                        index === root.selectedSpecialistIndex
                        || recipientMouse.containsMouse
                        ? 2 : 1
                    border.color:
                        index === root.selectedSpecialistIndex
                        ? Colors.magenta
                        : recipientMouse.containsMouse
                        ? Colors.orange
                        : stateColor

                    GohuText {
                        anchors.centerIn: parent
                        text:
                            String(parent.modelData.name || parent.modelData.id || "STAFF")
                            + " // "
                            + parent.presence
                        font.pixelSize: 9
                        opacity:
                            String(parent.modelData.presence || "") === "READY"
                            ? 1.0 : 0.48
                        color:
                            parent.index === root.selectedSpecialistIndex
                            ? Colors.magenta
                            : parent.stateColor
                    }

                    MouseArea {
                        id: recipientMouse

                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked:
                            root.selectedSpecialistIndex = parent.index
                    }
                }
            }
        }
    }

    Rectangle {
        id: transcriptFrame

        anchors {
            left: parent.left
            right: parent.right
            top: recipientColumn.bottom
            leftMargin: 8
            rightMargin: 8
            topMargin: 8
        }

        height: 160
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan
        clip: true

        Flickable {
            id: transcript

            anchors.fill: parent
            anchors.margins: 7
            contentWidth: width
            contentHeight: transcriptColumn.height
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            Column {
                id: transcriptColumn

                width: transcript.width
                spacing: 7

                Repeater {
                    model: root.currentMessages

                    Column {
                        required property var modelData

                        width: transcriptColumn.width
                        spacing: 2

                        GohuText {
                            width: parent.width
                            text:
                                String(parent.modelData.sender || "OPERATOR")
                                + " // "
                                + String(parent.modelData.launchedAt || "")
                                + " // "
                                + String(parent.modelData.specialistName || "")
                            font.pixelSize: 9
                            color: Colors.green
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text: String(parent.modelData.body || "")
                            font.pixelSize: 10
                            color: Colors.white
                            wrapMode: Text.Wrap
                        }
                    }
                }

                GohuText {
                    width: parent.width
                    visible: root.currentMessages.length === 0
                    text: "NO TRAFFIC ON THIS CHANNEL"
                    font.pixelSize: 10
                    color: Colors.cyan
                    opacity: 0.62
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Rectangle {
        id: composerFrame

        anchors {
            left: parent.left
            right: vadButton.left
            top: transcriptFrame.bottom
            leftMargin: 8
            rightMargin: 6
            topMargin: 8
        }

        height: 42
        color: Colors.dark
        border.width: messageInput.activeFocus ? 2 : 1
        border.color:
            messageInput.activeFocus
            ? Colors.orange
            : Colors.cyan

        TextInput {
            id: messageInput

            anchors {
                fill: parent
                leftMargin: 9
                rightMargin: 9
            }

            verticalAlignment: TextInput.AlignVCenter
            clip: true
            color: Colors.white
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black
            font.pixelSize: 11
            enabled:
                !root.speechInputService.stopping
                && !root.speechInputService.transcribing

            onActiveFocusChanged:
                root.typingChanged(activeFocus)

            Keys.onReturnPressed: function(event) {
                if (root.speechInputService.recording) {
                    root.speechInputService.stopRecording(true);
                    event.accepted = true;
                    return;
                }

                if (root.speechInputService.stopping
                        || root.speechInputService.transcribing) {
                    event.accepted = true;
                    return;
                }

                root.sendCurrent();
                event.accepted = true;
            }

            Keys.onEscapePressed: function(event) {
                if (!root.speechInputService.busy)
                    return;

                root.speechInputService.cancel();
                event.accepted = true;
            }
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 9
            }

            visible: messageInput.text.length === 0
            text:
                root.speechInputService.recording
                ? (
                    "LISTENING "
                    + root.speechInputService.recordingElapsedLabel
                    + (
                        root.speechInputService.vadActive
                        ? " // VAD"
                        : ""
                      )
                  )
                : root.speechInputService.stopping
                  || root.speechInputService.transcribing
                ? "TRANSCRIBING..."
                : "MESSAGE SPECIALIST..."
            font.pixelSize: 10
            color:
                root.speechInputService.recording
                ? Colors.magenta
                : root.speechInputService.transcribing
                ? Colors.orange
                : Colors.white
            opacity:
                root.speechInputService.busy
                ? 0.82 : 0.38
        }
    }

    Rectangle {
        id: vadButton

        readonly property bool enabledAction:
            root.speechInputService.vadAvailable
            && !root.speechInputService.busy

        anchors {
            right: micButton.left
            top: transcriptFrame.bottom
            rightMargin: 6
            topMargin: 8
        }

        width: 42
        height: 42
        color:
            root.speechInputService.vadEnabled
            ? Colors.yellow
            : vadMouse.pressed
            ? Colors.black
            : Colors.dark
        border.width:
            root.speechInputService.vadEnabled
            || vadMouse.containsMouse
            ? 2 : 1
        border.color:
            vadMouse.containsMouse
            && vadButton.enabledAction
            ? Colors.orange
            : root.speechInputService.vadEnabled
            ? Colors.omnitrix
            : Colors.cyan

        RectangularShadow {
            anchors.fill: parent
            spread: 3
            z: -1
            opacity:
                root.speechInputService.vadEnabled
                ? 0.38
                : vadButton.enabledAction
                ? 0.18 : 0.08
            color:
                root.speechInputService.vadEnabled
                ? Colors.omnitrix
                : Colors.cyan
        }

        GohuText {
            anchors.centerIn: parent
            text: "VAD"
            font.pixelSize: 9
            color:
                root.speechInputService.vadEnabled
                ? Colors.magenta
                : vadMouse.containsMouse
                  && vadButton.enabledAction
                ? Colors.orange
                : Colors.cyan
            opacity:
                vadButton.enabledAction
                || root.speechInputService.vadEnabled
                ? 1.0 : 0.34
        }

        MouseArea {
            id: vadMouse

            anchors.fill: parent
            enabled: vadButton.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked:
                root.speechInputService.setVadEnabled(
                    !root.speechInputService.vadEnabled
                )
        }
    }

    Rectangle {
        id: micButton

        anchors {
            right: voiceCancelButton.left
            top: transcriptFrame.bottom
            rightMargin: voiceCancelButton.visible ? 6 : 0
            topMargin: 8
        }

        width: 42
        height: 42
        color:
            micMouse.pressed
            ? Colors.black
            : Colors.dark
        border.width:
            root.speechInputService.recording
            || micMouse.containsMouse
            ? 2 : 1
        border.color:
            root.speechInputService.recording
            ? Colors.omnitrix
            : root.speechInputService.stopping
              || root.speechInputService.transcribing
            ? Colors.orange
            : micMouse.containsMouse
            ? Colors.orange
            : Colors.omnitrix

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity:
                root.speechInputService.stopping
                  || root.speechInputService.transcribing
                ? 0.24
                : micMouse.containsMouse
                ? 0.48 : 0.34
            color:
                root.speechInputService.stopping
                  || root.speechInputService.transcribing
                ? Colors.orange
                : micMouse.containsMouse
                ? Colors.orange
                : Colors.omnitrix
        }

        opacity:
            root.speechInputService.stopping
            || root.speechInputService.transcribing
            ? 0.55
            : root.speechInputService.backendReady
            ? 1.0 : 0.48

        GohuText {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: 1
            text: "🗣︎"
            font.pixelSize: 22
            color:
                root.speechInputService.recording
                ? Colors.omnitrix
                : micMouse.containsMouse
                ? Colors.orange
                : Colors.omnitrix
        }

        MouseArea {
            id: micMouse

            anchors.fill: parent
            enabled:
                !root.speechInputService.stopping
                && !root.speechInputService.transcribing
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked: {
                messageInput.forceActiveFocus();

                if (root.speechInputService.recording)
                    root.speechInputService.stopRecording(false);
                else
                    root.speechInputService.startRecording();
            }
        }
    }

    Rectangle {
        id: voiceCancelButton

        visible: root.speechInputService.busy
        anchors {
            right: sendButton.left
            top: transcriptFrame.bottom
            rightMargin: visible ? 6 : 0
            topMargin: 8
        }

        width: visible ? 66 : 0
        height: 42
        color:
            voiceCancelMouse.pressed
            ? Colors.black
            : Colors.dark
        border.width:
            voiceCancelMouse.containsMouse ? 2 : 1
        border.color: Colors.red

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity:
                voiceCancelMouse.containsMouse
                ? 0.48 : 0.28
            color: Colors.red
        }

        GohuText {
            anchors.centerIn: parent
            text: "CANCEL"
            font.pixelSize: 9
            color:
                voiceCancelMouse.containsMouse
                ? Colors.orange
                : Colors.red
        }

        MouseArea {
            id: voiceCancelMouse

            anchors.fill: parent
            enabled: root.speechInputService.busy
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked: {
                root.speechInputService.cancel();
                messageInput.forceActiveFocus();
            }
        }
    }

    Rectangle {
        id: sendButton

        readonly property bool enabledAction:
            root.selectedSpecialist
            && String(root.selectedSpecialist.presence || "") === "READY"
            && (
                root.speechInputService.recording
                || (
                    !root.speechInputService.stopping
                    && !root.speechInputService.transcribing
                    && messageInput.text.trim().length > 0
                   )
               )

        anchors {
            right: parent.right
            top: transcriptFrame.bottom
            rightMargin: 8
            topMargin: 8
        }

        width: 86
        height: 42
        color:
            sendMouse.pressed
            ? Colors.black
            : Colors.dark
        border.width:
            sendMouse.containsMouse ? 2 : 1
        border.color:
            root.speechInputService.recording
            ? Colors.omnitrix
            : sendMouse.containsMouse
            ? Colors.orange
            : Colors.green

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity:
                sendMouse.containsMouse
                ? 0.48
                : sendButton.enabledAction
                ? 0.28 : 0.12
            color:
                root.speechInputService.recording
                ? Colors.omnitrix
                : sendMouse.containsMouse
                ? Colors.orange
                : Colors.green
        }

        GohuText {
            anchors.centerIn: parent
            text:
                root.speechInputService.stopping
                  || root.speechInputService.transcribing
                ? "..."
                : "SEND"
            font.pixelSize: 11
            opacity: sendButton.enabledAction ? 1.0 : 0.34
            color:
                root.speechInputService.recording
                ? Colors.omnitrix
                : sendMouse.containsMouse
                ? Colors.orange
                : Colors.green
        }

        MouseArea {
            id: sendMouse

            anchors.fill: parent
            enabled: sendButton.enabledAction
            hoverEnabled: true
            cursorShape:
                enabled
                ? Qt.PointingHandCursor
                : Qt.ArrowCursor

            onClicked: root.sendCurrentVoiceAware()
        }
    }

    GohuText {
        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
            leftMargin: 10
            rightMargin: 10
            bottomMargin: 8
        }

        height: 20
        text:
            root.speechInputService.lastError
            || (
                root.speechInputService.recording
                ? (
                    "VOICE // LISTENING // "
                    + root.speechInputService.recordingElapsedLabel
                  )
                : root.speechInputService.stopping
                  || root.speechInputService.transcribing
                ? "VOICE // TRANSCRIBING"
                : ""
              )
            || root.intercomService.lastError
            || root.intercomService.lastStatus
            || (
                "READY // INTERCOM"
                + (
                    root.speechInputService.vadEnabled
                    ? " // VAD"
                    : ""
                  )
               )
        font.pixelSize: 9
        color:
            root.speechInputService.lastError
            || root.intercomService.lastError
            ? Colors.red
            : root.speechInputService.recording
            ? Colors.magenta
            : root.speechInputService.stopping
              || root.speechInputService.transcribing
            ? Colors.orange
            : root.intercomService.lastStatus
            ? Colors.green
            : Colors.cyan
        elide: Text.ElideRight
    }
}
