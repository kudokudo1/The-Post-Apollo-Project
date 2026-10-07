import QtQuick
import QtQuick.Effects
import qs.components

Rectangle {
    id: root

    required property var receptionistService
    required property var speechInputService

    property string floorLabel: "NO FLOOR"
    property string roomLabel: "NO ROOM"
    property int readyCount: 0
    property int specialistCount: 0
    property int attentionCount: 0
    property int newCount: 0
    property int recentCount: 0
    property var inbox: []

    signal routeRequested(string route)
    signal attentionActivated(var item)
    signal typingChanged(bool active)

    function attentionColor(item) {
        const source = String((item || {}).source || "").toLowerCase();

        if (source === "phone")
            return Colors.green;
        if (source === "intercom")
            return Colors.omnitrix;
        if (source === "reports")
            return Colors.magenta;
        if (source === "rounds")
            return Colors.yellow;

        return Colors.cyan;
    }

    function scrollTranscriptToBottom() {
        Qt.callLater(function() {
            transcript.contentY = Math.max(
                0,
                transcript.contentHeight - transcript.height
            );
        });
    }

    function submitReceptionInput() {
        const message =
            String(receptionInput.text || "").trim();

        if (!message)
            return false;

        const accepted =
            root.receptionistService.submit(message);

        receptionInput.resetHistory();

        if (accepted)
            receptionInput.text = "";

        root.scrollTranscriptToBottom();
        return accepted;
    }

    function acceptVoiceTranscript(
            textValue,
            submitRequested) {
        const spoken =
            String(textValue || "").trim();

        if (!spoken)
            return false;

        const existing =
            String(receptionInput.text || "").trim();
        const combined =
            existing
            ? existing + " " + spoken
            : spoken;

        receptionInput.resetHistory();
        receptionInput.applyHistoryText(combined);
        receptionInput.forceActiveFocus();

        if (submitRequested)
            root.submitReceptionInput();

        return true;
    }

    color: Colors.black
    border.width: 1
    border.color: Colors.magenta

    Connections {
        target: root.receptionistService

        function onRouteRequested(route) {
            root.routeRequested(route);
        }
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

    Column {
        anchors {
            fill: parent
            margins: 10
        }

        spacing: 9

        Rectangle {
            id: receptionStage

            width: parent.width
            height: Math.max(210, root.height * 0.34)
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.22
                color: Colors.cyan
            }

            GohuText {
                anchors {
                    top: parent.top
                    horizontalCenter: parent.horizontalCenter
                    topMargin: 12
                }

                text: "RECEPTION // FRONT DESK"
                font.pixelSize: 14
                color: Colors.magenta
            }

            Rectangle {
                id: avatarHead

                width: 72
                height: 72
                radius: 36
                anchors {
                    horizontalCenter: parent.horizontalCenter
                    top: parent.top
                    topMargin: 48
                }

                color: Colors.black
                border.width: 2
                border.color: Colors.magenta

                RectangularShadow {
                    anchors.fill: parent
                    spread: 5
                    z: -1
                    opacity: 0.38
                    color: Colors.magenta
                }

                GohuText {
                    anchors.centerIn: parent
                    text: "R"
                    font.pixelSize: 30
                    color: Colors.cyan
                }
            }

            Rectangle {
                width: 150
                height: 68
                radius: 10
                anchors {
                    horizontalCenter: parent.horizontalCenter
                    top: avatarHead.bottom
                    topMargin: 5
                }

                color: Colors.black
                border.width: 2
                border.color: Colors.cyan
            }

            Rectangle {
                id: desk

                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                    leftMargin: 28
                    rightMargin: 28
                    bottomMargin: 18
                }

                height: 58
                color: Colors.black
                border.width: 2
                border.color: Colors.orange

                GohuText {
                    anchors {
                        left: parent.left
                        verticalCenter: parent.verticalCenter
                        leftMargin: 14
                    }

                    text:
                        "FLOOR // "
                        + root.floorLabel
                        + "    ROOM // "
                        + root.roomLabel
                    font.pixelSize: 10
                    color: Colors.white
                    elide: Text.ElideRight
                    width: parent.width - deskControls.width - 34
                }

                Row {
                    id: deskControls

                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                        rightMargin: 10
                    }

                    spacing: 7

                    Repeater {
                        model: [
                            { label: "☎︎", route: "phone", color: Colors.green },
                            { label: "🎙︎", route: "intercom", color: Colors.omnitrix },
                            { label: "🗒︎", route: "reports", color: Colors.magenta },
                            { label: "⚠︎", route: "rounds", color: Colors.yellow }
                        ]

                        Rectangle {
                            required property var modelData

                            width: 42
                            height: 36
                            color:
                                deskControlMouse.pressed
                                ? Colors.black
                                : Colors.dark
                            border.width:
                                deskControlMouse.containsMouse
                                ? 2 : 1
                            border.color:
                                deskControlMouse.containsMouse
                                ? Colors.orange
                                : modelData.color

                            GohuText {
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset:
                                    parent.modelData.route === "intercom"
                                    ? 1 : 0
                                width: parent.width
                                height: parent.height
                                visible:
                                    parent.modelData.route === "intercom"
                                    || parent.modelData.route === "phone"
                                text: parent.modelData.label
                                font.pixelSize:
                                    parent.modelData.route === "phone"
                                    ? 25 : 23
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                color:
                                    deskControlMouse.containsMouse
                                    ? Colors.orange
                                    : parent.modelData.color
                            }

                            NotoText {
                                anchors.centerIn: parent
                                anchors.verticalCenterOffset:
                                    parent.modelData.route === "reports"
                                    ? 4
                                    : parent.modelData.route === "rounds"
                                    ? 2 : 0
                                width: parent.width
                                height: parent.height
                                visible:
                                    parent.modelData.route !== "intercom"
                                    && parent.modelData.route !== "phone"
                                text: parent.modelData.label
                                font.pixelSize:
                                    parent.modelData.route === "reports"
                                    ? 22
                                    : parent.modelData.route === "rounds"
                                    ? 28
                                    : 11
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                color:
                                    deskControlMouse.containsMouse
                                    ? Colors.orange
                                    : parent.modelData.color
                            }

                            MouseArea {
                                id: deskControlMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor

                                onClicked:
                                    root.receptionistService.request(
                                        parent.modelData.route,
                                        ""
                                    )
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: statusStrip

            width: parent.width
            height: 38
            color: Colors.dark
            border.width: 1
            border.color: Colors.green

            GohuText {
                anchors {
                    fill: parent
                    margins: 8
                }

                verticalAlignment: Text.AlignVCenter
                text:
                    "STAFF READY "
                    + String(root.readyCount)
                    + "/"
                    + String(root.specialistCount)
                    + "    //    ATTENTION "
                    + String(root.attentionCount)
                    + "    //    NEW "
                    + String(root.newCount)
                    + "    //    RECENT "
                    + String(root.recentCount)
                    + "    //    AUTHORITY: ROUTE + EXPLAIN + INITIATE"
                font.pixelSize: 10
                color: Colors.green
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: inboxFrame

            width: parent.width
            height: 82
            color: Colors.dark
            border.width: 1
            border.color: Colors.yellow

            Column {
                anchors {
                    fill: parent
                    margins: 7
                }

                spacing: 5

                Row {
                    width: parent.width
                    height: 18

                    GohuText {
                        width: parent.width - inboxCount.width
                        anchors.verticalCenter: parent.verticalCenter
                        text: "FRONT DESK // RECENT + FAVORITES"
                        font.pixelSize: 10
                        color: Colors.yellow
                    }

                    GohuText {
                        id: inboxCount

                        anchors.verticalCenter: parent.verticalCenter
                        text: {
                            const pinned =
                                Number(
                                    root.receptionistService.pinnedCount
                                    || 0
                                );
                            const parts = [];

                            if (pinned > 0)
                                parts.push("✦ " + String(pinned));

                            if (root.newCount > 0)
                                parts.push(
                                    "NEW " + String(root.newCount)
                                );

                            parts.push(String(root.recentCount));
                            return parts.join(" // ");
                        }
                        font.pixelSize: 10
                        color: Colors.yellow
                    }
                }

                Row {
                    id: inboxSlots

                    width: parent.width
                    height: 44
                    spacing: 6

                    Repeater {
                        model: 5

                        Rectangle {
                            id: inboxSlot

                            required property int index

                            readonly property var itemData:
                                index < root.inbox.length
                                ? root.inbox[index]
                                : null
                            readonly property bool occupied:
                                itemData !== null
                            readonly property bool unread:
                                occupied
                                && root.receptionistService.isUnread(itemData)
                            readonly property bool pinned:
                                occupied
                                && root.receptionistService.isPinned(itemData)
                            readonly property color attentionAccent:
                                root.attentionColor(itemData)

                            width: (inboxSlots.width - 24) / 5
                            height: inboxSlots.height
                            color:
                                occupied
                                && inboxMouse.pressed
                                ? Colors.black
                                : Colors.black
                            opacity:
                                !occupied
                                ? 0.18
                                : unread || pinned
                                ? 1.0
                                : 0.62
                            border.width:
                                occupied
                                && (
                                    unread
                                    || pinned
                                    || inboxMouse.containsMouse
                                )
                                ? 2 : 1
                            border.color:
                                !occupied
                                ? Colors.cyan
                                : inboxMouse.containsMouse
                                ? Colors.orange
                                : attentionAccent

                            Column {
                                anchors {
                                    fill: parent
                                    leftMargin: 5
                                    rightMargin: 25
                                    topMargin: 5
                                    bottomMargin: 5
                                }

                                spacing: 2

                                GohuText {
                                    width: parent.width
                                    visible: parent.parent.occupied
                                    text:
                                        String(
                                            (parent.parent.itemData || {}).title
                                            || ""
                                        )
                                    font.pixelSize: 8
                                    color:
                                        parent.parent.attentionAccent
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    visible: parent.parent.occupied
                                    text: {
                                        const item =
                                            parent.parent.itemData || {};
                                        const time =
                                            String(item.timeLabel || "");
                                        const detail =
                                            String(item.detail || "");

                                        const body =
                                            time
                                            ? (
                                                detail
                                                ? time + " // " + detail
                                                : time
                                              )
                                            : detail;

                                        return parent.parent.unread
                                            ? "NEW // " + body
                                            : body;
                                    }
                                    font.pixelSize: 7
                                    color: Colors.white
                                    opacity: 0.72
                                    elide: Text.ElideRight
                                }
                            }

                            Item {
                                id: favoriteControl

                                visible: inboxSlot.occupied
                                z: 3
                                width: 20
                                height: 20
                                anchors {
                                    top: parent.top
                                    right: parent.right
                                    topMargin: 1
                                    rightMargin: 2
                                }

                                NotoText {
                                    anchors.centerIn: parent
                                    text:
                                        inboxSlot.pinned
                                        ? "✦"
                                        : "✧"
                                    font.pixelSize: 15
                                    color:
                                        favoriteMouse.containsMouse
                                        ? Colors.orange
                                        : inboxSlot.attentionAccent
                                }

                                MouseArea {
                                    id: favoriteMouse

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor

                                    onClicked:
                                        root.receptionistService.togglePinned(
                                            inboxSlot.itemData
                                        )
                                }
                            }

                            MouseArea {
                                id: inboxMouse

                                anchors.fill: parent
                                enabled: parent.occupied
                                hoverEnabled: true
                                cursorShape:
                                    enabled
                                    ? Qt.PointingHandCursor
                                    : Qt.ArrowCursor

                                onClicked:
                                    root.attentionActivated(parent.itemData)
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: contextStrip

            width: parent.width
            height:
                root.receptionistService.contextActive
                ? 36 : 0
            visible: root.receptionistService.contextActive
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            GohuText {
                anchors {
                    left: parent.left
                    right: contextActions.left
                    verticalCenter: parent.verticalCenter
                    leftMargin: 8
                    rightMargin: 8
                }

                text:
                    "CONTEXT // "
                    + String(
                        root.receptionistService.contextLabel
                        || "ACTIVITY"
                    )
                font.pixelSize: 9
                color: Colors.cyan
                elide: Text.ElideRight
            }

            Row {
                id: contextActions

                anchors {
                    right: parent.right
                    verticalCenter: parent.verticalCenter
                    rightMargin: 6
                }

                spacing: 5

                Rectangle {
                    id: contextOpen

                    width: 52
                    height: 24
                    color:
                        contextOpenMouse.pressed
                        ? Colors.magenta
                        : Colors.black
                    border.width:
                        contextOpenMouse.containsMouse
                        ? 2 : 1
                    border.color:
                        contextOpenMouse.containsMouse
                        ? Colors.orange
                        : Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        text: "OPEN"
                        font.pixelSize: 8
                        color:
                            contextOpenMouse.pressed
                            ? Colors.black
                            : contextOpenMouse.containsMouse
                            ? Colors.orange
                            : Colors.cyan
                    }

                    MouseArea {
                        id: contextOpenMouse

                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked: {
                            root.receptionistService.contextAction("open");
                            Qt.callLater(function() {
                                transcript.contentY = Math.max(
                                    0,
                                    transcript.contentHeight
                                    - transcript.height
                                );
                            });
                        }
                    }
                }

                Rectangle {
                    id: contextThere

                    width: 52
                    height: 24
                    color:
                        contextThereMouse.pressed
                        && contextThereMouse.enabled
                        ? Colors.magenta
                        : Colors.black
                    opacity:
                        root.receptionistService.contextCanThere
                        ? 1.0 : 0.30
                    border.width:
                        contextThereMouse.containsMouse
                        && contextThereMouse.enabled
                        ? 2 : 1
                    border.color: Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        text: "THERE"
                        font.pixelSize: 7
                        color:
                            contextThereMouse.pressed
                            && contextThereMouse.enabled
                            ? Colors.black
                            : contextThereMouse.containsMouse
                              && contextThereMouse.enabled
                            ? Colors.orange
                            : Colors.cyan
                    }

                    MouseArea {
                        id: contextThereMouse

                        anchors.fill: parent
                        enabled:
                            root.receptionistService.contextCanThere
                        hoverEnabled: true
                        cursorShape:
                            enabled
                            ? Qt.PointingHandCursor
                            : Qt.ArrowCursor

                        onClicked: {
                            root.receptionistService
                                .contextAction("there");
                            Qt.callLater(function() {
                                transcript.contentY = Math.max(
                                    0,
                                    transcript.contentHeight
                                    - transcript.height
                                );
                            });
                        }
                    }
                }

                Item {
                    id: contextFavorite

                    width: 30
                    height: 24
                    opacity:
                        root.receptionistService.contextHasEvent
                        ? 1.0 : 0.28

                    NotoText {
                        anchors.centerIn: parent
                        text:
                            root.receptionistService.contextIsFavorite
                            ? "✦"
                            : "✧"
                        font.pixelSize: 17
                        color:
                            contextFavoriteMouse.containsMouse
                            && contextFavoriteMouse.enabled
                            ? Colors.orange
                            : root.attentionColor(
                                root.receptionistService.contextItem
                              )
                    }

                    MouseArea {
                        id: contextFavoriteMouse

                        anchors.fill: parent
                        enabled:
                            root.receptionistService.contextHasEvent
                        hoverEnabled: true
                        cursorShape:
                            enabled
                            ? Qt.PointingHandCursor
                            : Qt.ArrowCursor

                        onClicked: {
                            root.receptionistService
                                .contextAction("favorite");
                            Qt.callLater(function() {
                                transcript.contentY = Math.max(
                                    0,
                                    transcript.contentHeight
                                    - transcript.height
                                );
                            });
                        }
                    }
                }

                Rectangle {
                    id: contextBefore

                    width: 52
                    height: 24
                    color:
                        contextBeforeMouse.pressed
                        && contextBeforeMouse.enabled
                        ? Colors.magenta
                        : Colors.black
                    opacity:
                        root.receptionistService.contextCanBefore
                        ? 1.0 : 0.30
                    border.width:
                        contextBeforeMouse.containsMouse
                        && contextBeforeMouse.enabled
                        ? 2 : 1
                    border.color: Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        text: "BEFORE"
                        font.pixelSize: 7
                        color:
                            contextBeforeMouse.pressed
                            && contextBeforeMouse.enabled
                            ? Colors.black
                            : contextBeforeMouse.containsMouse
                              && contextBeforeMouse.enabled
                            ? Colors.orange
                            : Colors.cyan
                    }

                    MouseArea {
                        id: contextBeforeMouse

                        anchors.fill: parent
                        enabled:
                            root.receptionistService.contextCanBefore
                        hoverEnabled: true
                        cursorShape:
                            enabled
                            ? Qt.PointingHandCursor
                            : Qt.ArrowCursor

                        onClicked: {
                            root.receptionistService
                                .contextAction("before");
                            Qt.callLater(function() {
                                transcript.contentY = Math.max(
                                    0,
                                    transcript.contentHeight
                                    - transcript.height
                                );
                            });
                        }
                    }
                }

                Rectangle {
                    id: contextNewer

                    width: 52
                    height: 24
                    color:
                        contextNewerMouse.pressed
                        && contextNewerMouse.enabled
                        ? Colors.magenta
                        : Colors.black
                    opacity:
                        root.receptionistService.contextCanNewer
                        ? 1.0 : 0.30
                    border.width:
                        contextNewerMouse.containsMouse
                        && contextNewerMouse.enabled
                        ? 2 : 1
                    border.color: Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        text: "NEWER"
                        font.pixelSize: 7
                        color:
                            contextNewerMouse.pressed
                            && contextNewerMouse.enabled
                            ? Colors.black
                            : contextNewerMouse.containsMouse
                              && contextNewerMouse.enabled
                            ? Colors.orange
                            : Colors.cyan
                    }

                    MouseArea {
                        id: contextNewerMouse

                        anchors.fill: parent
                        enabled:
                            root.receptionistService.contextCanNewer
                        hoverEnabled: true
                        cursorShape:
                            enabled
                            ? Qt.PointingHandCursor
                            : Qt.ArrowCursor

                        onClicked: {
                            root.receptionistService
                                .contextAction("newer");
                            Qt.callLater(function() {
                                transcript.contentY = Math.max(
                                    0,
                                    transcript.contentHeight
                                    - transcript.height
                                );
                            });
                        }
                    }
                }
            }
        }

        Rectangle {
            id: transcriptFrame

            width: parent.width
            height:
                Math.max(
                    90,
                    root.height
                    - receptionStage.height
                    - statusStrip.height
                    - inboxFrame.height
                    - contextStrip.height
                    - composer.height
                    - 61
                    - (
                        contextStrip.visible
                        ? 9 : 0
                      )
                )
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            Flickable {
                id: transcript

                anchors.fill: parent
                anchors.margins: 8
                contentWidth: width
                contentHeight: transcriptColumn.height
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                Column {
                    id: transcriptColumn

                    width: transcript.width
                    spacing: 6

                    Repeater {
                        model: root.receptionistService.transcript

                        Column {
                            required property var modelData

                            width: transcriptColumn.width
                            spacing: 2

                            GohuText {
                                width: parent.width
                                text: String(parent.modelData.sender || "")
                                font.pixelSize: 9
                                color:
                                    String(parent.modelData.sender || "") === "RECEPTION"
                                    ? Colors.magenta
                                    : Colors.green
                            }

                            GohuText {
                                width: parent.width
                                text: String(parent.modelData.body || "")
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
        }

        Row {
            id: composer

            width: parent.width
            height: 42
            spacing: 7

            Rectangle {
                width:
                    composer.width
                    - micButton.width
                    - sendButton.width
                    - (composer.spacing * 2)
                height: composer.height
                color: Colors.dark
                border.width: receptionInput.activeFocus ? 2 : 1
                border.color:
                    receptionInput.activeFocus
                    ? Colors.orange
                    : Colors.cyan

                TextInput {
                    id: receptionInput

                    property int historyIndex: -1
                    property string historyDraft: ""

                    function historyEntries() {
                        const rows =
                            root.receptionistService.transcript || [];
                        const entries = [];

                        for (let i = 0; i < rows.length; ++i) {
                            const row = rows[i] || {};

                            if (String(row.sender || "") !== "OPERATOR")
                                continue;

                            const body =
                                String(row.body || "").trim();

                            if (body)
                                entries.push(body);
                        }

                        return entries;
                    }

                    function resetHistory() {
                        historyIndex = -1;
                        historyDraft = "";
                    }

                    function applyHistoryText(value) {
                        text = String(value || "");
                        cursorPosition = text.length;
                    }

                    function historyPrevious() {
                        const entries = historyEntries();

                        if (entries.length === 0)
                            return;

                        if (historyIndex < 0) {
                            historyDraft = String(text || "");
                            historyIndex = entries.length - 1;
                        } else if (historyIndex > 0) {
                            historyIndex -= 1;
                        }

                        applyHistoryText(entries[historyIndex]);
                    }

                    function historyNext() {
                        const entries = historyEntries();

                        if (historyIndex < 0)
                            return;

                        if (historyIndex < entries.length - 1) {
                            historyIndex += 1;
                            applyHistoryText(entries[historyIndex]);
                            return;
                        }

                        const draft = historyDraft;
                        resetHistory();
                        applyHistoryText(draft);
                    }

                    anchors {
                        fill: parent
                        leftMargin: 10
                        rightMargin: 10
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

                    onTextEdited: {
                        if (historyIndex >= 0) {
                            historyIndex = -1;
                            historyDraft = "";
                        }
                    }

                    Keys.onUpPressed: function(event) {
                        historyPrevious();
                        event.accepted = true;
                    }

                    Keys.onDownPressed: function(event) {
                        historyNext();
                        event.accepted = true;
                    }

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

                        root.submitReceptionInput();
                        event.accepted = true;
                    }
                }

                GohuText {
                    anchors {
                        left: parent.left
                        verticalCenter: parent.verticalCenter
                        leftMargin: 10
                    }

                    visible: receptionInput.text.length === 0
                    text:
                        root.speechInputService.recording
                        ? "LISTENING..."
                        : root.speechInputService.stopping
                          || root.speechInputService.transcribing
                        ? "TRANSCRIBING..."
                        : "ASK RECEPTION..."
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
                id: micButton

                width: 42
                height: composer.height
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
                    ? Colors.magenta
                    : root.speechInputService.stopping
                      || root.speechInputService.transcribing
                    ? Colors.orange
                    : micMouse.containsMouse
                    ? Colors.orange
                    : root.speechInputService.backendReady
                    ? Colors.cyan
                    : Colors.magenta
                opacity:
                    root.speechInputService.stopping
                    || root.speechInputService.transcribing
                    ? 0.55
                    : root.speechInputService.backendReady
                    ? 1.0 : 0.48

                GohuText {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: 1
                    text: "🎙︎"
                    font.pixelSize: 22
                    color:
                        root.speechInputService.recording
                        ? Colors.magenta
                        : micMouse.containsMouse
                        ? Colors.orange
                        : root.speechInputService.backendReady
                        ? Colors.cyan
                        : Colors.magenta
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
                        receptionInput.forceActiveFocus();

                        if (root.speechInputService.recording)
                            root.speechInputService.stopRecording(false);
                        else
                            root.speechInputService.startRecording();
                    }
                }
            }

            Rectangle {
                id: sendButton

                width: 86
                height: composer.height
                color:
                    sendMouse.pressed
                    ? Colors.black
                    : Colors.dark
                border.width:
                    sendMouse.containsMouse
                    ? 2 : 1
                border.color:
                    root.speechInputService.recording
                    ? Colors.magenta
                    : sendMouse.containsMouse
                    ? Colors.orange
                    : Colors.green
                opacity:
                    root.speechInputService.recording
                    || (
                        !root.speechInputService.stopping
                        && !root.speechInputService.transcribing
                        && receptionInput.text.trim().length > 0
                       )
                    ? 1.0 : 0.48

                GohuText {
                    anchors.centerIn: parent
                    text:
                        root.speechInputService.recording
                        ? "SEND"
                        : root.speechInputService.stopping
                          || root.speechInputService.transcribing
                        ? "..."
                        : "ASK"
                    font.pixelSize: 11
                    color:
                        root.speechInputService.recording
                        ? Colors.magenta
                        : sendMouse.containsMouse
                        ? Colors.orange
                        : Colors.green
                }

                MouseArea {
                    id: sendMouse

                    anchors.fill: parent
                    enabled:
                        root.speechInputService.recording
                        || (
                            !root.speechInputService.stopping
                            && !root.speechInputService.transcribing
                            && receptionInput.text.trim().length > 0
                           )
                    hoverEnabled: true
                    cursorShape:
                        enabled
                        ? Qt.PointingHandCursor
                        : Qt.ArrowCursor

                    onClicked: {
                        receptionInput.forceActiveFocus();

                        if (root.speechInputService.recording) {
                            root.speechInputService.stopRecording(true);
                            return;
                        }

                        root.submitReceptionInput();
                    }
                }
            }
        }
    }
}
