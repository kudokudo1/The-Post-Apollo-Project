import QtQuick
import Quickshell
import qs.components

Item {
    id: root

    required property var gitService
    required property var profileService
    required property var profileStore
    required property var accountService
    required property var keyboardHost

    property string profileMode: "repositories"
    property bool accountDirty: false
    property string accountIdentityMode: "login"
    property string accountEmailMode: "primary"
    property string visibilityMode: "keep"
    property string topicMode: "add"
    property string descriptionMode: "keep"
    property string setNameDraft: ""

    function currentDraft() {
        return {
            visibility: visibilityMode,
            topicMode: topicMode,
            topics: root.profileService.normalizeTopics(topicsInput.text),
            descriptionMode: descriptionMode,
            description: descriptionInput.text,
            repositoryName: repositoryNameInput.text
        };
    }

    function markDirty() {
        root.profileService.invalidateReview();
    }

    function loadAccountDraft() {
        accountNameInput.text = root.accountService.displayName;
        accountBioInput.text = root.accountService.bio;
        accountEmailInput.text = root.accountService.email;
        root.accountDirty = false;
    }

    function showAccountProfile() {
        root.profileMode = "account";

        if (!root.accountService.busy)
            root.accountService.refreshProfile();
    }

    function showRepositoryProfiles() {
        root.profileMode = "repositories";
    }

    component ManagerButton: Rectangle {
        id: button

        property string label: ""
        property bool enabledAction: true
        property bool selectedAction: false
        property bool primaryBlue: false
        property bool dangerAccent: false

        readonly property bool keyboardSelected:
            root.keyboardHost
            && root.keyboardHost.gitKeyboardControl === button
        readonly property bool keyboardSelector:
            keyboardSelected
            && root.keyboardHost.gitSelectorSource === "keyboard"
        readonly property bool mouseSelector:
            keyboardSelected
            && root.keyboardHost.gitSelectorSource === "mouse"

        signal triggered()

        Component.onCompleted: {
            if (root.keyboardHost)
                root.keyboardHost.registerGitKeyboardControl(button);
        }

        Component.onDestruction: {
            if (root.keyboardHost)
                root.keyboardHost.unregisterGitKeyboardControl(button);
        }

        height: 28

        color:
            !enabledAction
            ? Colors.black
            : keyboardSelector || selectedAction
            ? Colors.yellow
            : primaryBlue
            ? Colors.black
            : Colors.black

        border.width:
            keyboardSelector || mouseSelector
            ? 2
            : 1

        border.color:
            keyboardSelector || mouseSelector
            ? Colors.orange
            : dangerAccent
            ? Colors.red
            : primaryBlue
            ? Colors.blue
            : selectedAction
            ? Colors.orange
            : mouse.containsMouse
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: button.label
            font.pixelSize: 8
            color:
                !button.enabledAction
                ? Colors.cyan
                : button.keyboardSelector || button.selectedAction
                ? Colors.magenta
                : button.dangerAccent
                ? Colors.red
                : button.primaryBlue
                ? Colors.blue
                : Colors.cyan
            opacity: button.enabledAction ? 1.0 : 0.34
        }

        MouseArea {
            id: mouse

            anchors.fill: parent
            enabled: button.enabledAction
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

            onEntered: {
                if (root.keyboardHost)
                    root.keyboardHost.selectGitControlFromMouse(button);
            }

            onPositionChanged: {
                if (root.keyboardHost)
                    root.keyboardHost.selectGitControlFromMouse(button);
            }

            onClicked: {
                if (root.keyboardHost)
                    root.keyboardHost.selectGitControlFromMouse(button);

                button.triggered();
            }
        }
    }

    component ManagerInput: Rectangle {
        id: field

        property string placeholderText: ""
        property bool enabledInput: true
        property alias text: editor.text

        signal edited()

        height: 30
        color: Colors.black
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.magenta
            : field.enabledInput
            ? Colors.cyan
            : Colors.dark

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 7
            }

            visible: editor.text.length === 0 && !editor.activeFocus
            text: field.placeholderText
            font.pixelSize: 8
            color: Colors.white
            opacity: field.enabledInput ? 0.42 : 0.22
        }

        TextInput {
            id: editor

            anchors {
                fill: parent
                margins: 6
            }

            enabled: field.enabledInput
            activeFocusOnPress: true
            selectByMouse: true
            verticalAlignment: TextInput.AlignVCenter
            clip: true
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 9
            color: field.enabledInput ? Colors.white : Colors.cyan
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black

            onTextChanged: field.edited()

            onAccepted: {
                focus = false;

                if (root.keyboardHost) {
                    root.keyboardHost.activeTextEditor = null;
                    root.keyboardHost.restoreGitKeyboardFocus(false);
                }
            }

            Keys.onEscapePressed: function(event) {
                focus = false;

                if (root.keyboardHost) {
                    root.keyboardHost.activeTextEditor = null;
                    root.keyboardHost.restoreGitKeyboardFocus(false);
                }

                event.accepted = true;
            }

            onActiveFocusChanged: {
                if (!root.keyboardHost)
                    return;

                if (activeFocus)
                    root.keyboardHost.activeTextEditor = editor;
                else if (root.keyboardHost.activeTextEditor === editor)
                    root.keyboardHost.activeTextEditor = null;
            }
        }
    }

    component ManagerTextArea: Rectangle {
        id: field

        property string placeholderText: ""
        property bool enabledInput: true
        property alias text: editor.text

        signal edited()

        height: 96
        color: Colors.black
        border.width: 1
        border.color:
            editor.activeFocus
            ? Colors.magenta
            : field.enabledInput
            ? Colors.cyan
            : Colors.dark

        GohuText {
            anchors {
                left: parent.left
                top: parent.top
                leftMargin: 7
                topMargin: 7
            }

            visible: editor.text.length === 0 && !editor.activeFocus
            text: field.placeholderText
            font.pixelSize: 8
            color: Colors.white
            opacity: field.enabledInput ? 0.42 : 0.22
        }

        TextEdit {
            id: editor

            anchors {
                fill: parent
                margins: 7
            }

            enabled: field.enabledInput
            activeFocusOnPress: true
            selectByMouse: true
            wrapMode: TextEdit.Wrap
            clip: true
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 9
            color: field.enabledInput ? Colors.white : Colors.cyan
            selectionColor: Colors.magenta
            selectedTextColor: Colors.black

            onTextChanged: field.edited()

            Keys.onEscapePressed: function(event) {
                focus = false;

                if (root.keyboardHost) {
                    root.keyboardHost.activeTextEditor = null;
                    root.keyboardHost.restoreGitKeyboardFocus(false);
                }

                event.accepted = true;
            }

            onActiveFocusChanged: {
                if (!root.keyboardHost)
                    return;

                if (activeFocus)
                    root.keyboardHost.activeTextEditor = editor;
                else if (root.keyboardHost.activeTextEditor === editor)
                    root.keyboardHost.activeTextEditor = null;
            }
        }
    }

    Connections {
        target: root.accountService

        function onProfileLoaded() {
            root.loadAccountDraft();
        }

        function onProfileSaved(success) {
            if (success)
                root.loadAccountDraft();
        }
    }

    Connections {
        target: root.profileStore

        function onSetLoaded(record) {
            root.visibilityMode = String(record.visibility || "keep");
            root.topicMode = String(record.topicMode || "add");
            root.descriptionMode = String(record.descriptionMode || "keep");
            topicsInput.text = Array.isArray(record.topics)
                ? record.topics.join(", ")
                : "";
            descriptionInput.text = String(record.description || "");
            repositoryNameInput.text = String(record.repositoryName || "");
            root.profileService.invalidateReview();
        }
    }

    Connections {
        target: root.profileService

        function onBatchFinished(success) {
            if (success)
                root.gitService.discoverRepos();
        }
    }

    Column {
        id: repositoryManager

        anchors.fill: parent
        visible: root.profileMode === "repositories"
        spacing: 10

        Item {
            width: parent.width
            height: 42

            Row {
                anchors {
                    fill: parent
                    margins: 8
                }

                spacing: 8

                GohuText {
                    width: parent.width - 278
                    anchors.verticalCenter: parent.verticalCenter
                    text: "REPOSITORY PROFILE MANAGER // BATCH CONTROL"
                    font.pixelSize: 11
                    color: Colors.blue
                }

                GohuText {
                    width: 172
                    anchors.verticalCenter: parent.verticalCenter
                    horizontalAlignment: Text.AlignRight
                    text:
                        String(root.profileStore.queueCount)
                        + " TARGET"
                        + (root.profileStore.queueCount === 1 ? "" : "S")
                    font.pixelSize: 9
                    color: Colors.cyan
                }

                ManagerButton {
                    width: 90
                    height: 26
                    anchors.verticalCenter: parent.verticalCenter
                    label: "ACCOUNT"
                    primaryBlue: true
                    onTriggered: root.showAccountProfile()
                }
            }
        }

        Row {
            width: parent.width
            height: parent.height - 52
            spacing: 10

            Column {
                width: (parent.width - 10) * 0.43
                height: parent.height
                spacing: 8

                Rectangle {
                    width: parent.width
                    height: 205
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }

                        spacing: 5

                        Row {
                            width: parent.width
                            height: 24

                            GohuText {
                                width: parent.width - 84
                                text: "REPOSITORY CATALOG"
                                font.pixelSize: 9
                                color: Colors.magenta
                            }

                            ManagerButton {
                                width: 84
                                height: 24
                                label: "REFRESH"
                                enabledAction: !root.gitService.discoveringRepos
                                onTriggered: root.gitService.discoverRepos()
                            }
                        }

                        Item {
                            id: catalogViewport

                            width: parent.width
                            height: parent.height - 34

                            Flickable {
                                id: catalogScroll

                                anchors {
                                    left: parent.left
                                    top: parent.top
                                    bottom: parent.bottom
                                    right: catalogScrollTrack.left
                                    rightMargin: 5
                                }

                                clip: true
                                contentWidth: width
                                contentHeight: catalogColumn.height
                                flickableDirection: Flickable.VerticalFlick
                                boundsBehavior: Flickable.StopAtBounds

                                Column {
                                    id: catalogColumn

                                    width: catalogScroll.width
                                    spacing: 4

                                    Repeater {
                                        model: root.gitService.repoCount

                                        Rectangle {
                                            required property int index

                                            readonly property var repoRow:
                                                root.gitService.repoAt(index)
                                            readonly property string slug:
                                                repoRow
                                                ? String(repoRow.remoteSlug || "")
                                                : ""

                                            width: catalogColumn.width
                                            height: slug ? 32 : 0
                                            visible: !!slug
                                            color: Colors.black
                                            border.width: 1
                                            border.color:
                                                root.profileStore.queueContains(slug)
                                                ? Colors.blue
                                                : Colors.dark

                                            Row {
                                                anchors {
                                                    fill: parent
                                                    margins: 4
                                                }

                                                spacing: 5

                                                GohuText {
                                                    width: parent.width - 68
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: slug
                                                    font.pixelSize: 10
                                                    color:
                                                        root.profileStore.queueContains(slug)
                                                        ? Colors.blue
                                                        : Colors.white
                                                    elide: Text.ElideRight
                                                }

                                                ManagerButton {
                                                    width: 58
                                                    height: 24
                                                    label:
                                                        root.profileStore.queueContains(slug)
                                                        ? "ADDED"
                                                        : "ADD"
                                                    primaryBlue:
                                                        !root.profileStore.queueContains(slug)
                                                    enabledAction:
                                                        !root.profileStore.queueContains(slug)

                                                    onTriggered: {
                                                        root.profileStore.addTarget(slug);
                                                        root.markDirty();
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                id: catalogScrollTrack

                                width: 5
                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    right: parent.right
                                }

                                color: Colors.black
                                border.width: 1
                                border.color: Colors.dark

                                Rectangle {
                                    width: parent.width
                                    height:
                                        catalogScroll.contentHeight <= 0
                                        ? parent.height
                                        : Math.max(
                                            18,
                                            parent.height
                                            * Math.min(
                                                1,
                                                catalogScroll.height
                                                / catalogScroll.contentHeight
                                            )
                                          )
                                    y:
                                        catalogScroll.contentHeight
                                        <= catalogScroll.height
                                        ? 0
                                        : (
                                            parent.height - height
                                          )
                                          * (
                                              catalogScroll.contentY
                                              / Math.max(
                                                  1,
                                                  catalogScroll.contentHeight
                                                  - catalogScroll.height
                                              )
                                            )
                                    color: Colors.cyan
                                    opacity:
                                        catalogScroll.contentHeight
                                        > catalogScroll.height
                                        ? 0.82
                                        : 0.30
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 145
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }

                        spacing: 5

                        Row {
                            width: parent.width
                            height: 24

                            GohuText {
                                width: parent.width - 70
                                text: "TARGET BATCH"
                                font.pixelSize: 9
                                color: Colors.magenta
                            }

                            ManagerButton {
                                width: 70
                                height: 24
                                label: "CLEAR"
                                enabledAction: root.profileStore.queueCount > 0

                                onTriggered: {
                                    root.profileStore.clearTargets();
                                    root.markDirty();
                                }
                            }
                        }

                        Flickable {
                            width: parent.width
                            height: parent.height - 34
                            clip: true
                            contentWidth: width
                            contentHeight: queueColumn.height
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: queueColumn

                                width: parent.width
                                spacing: 3

                                Repeater {
                                    model: root.profileStore.queue

                                    Rectangle {
                                        required property int index
                                        required property var modelData

                                        width: queueColumn.width
                                        height: 28
                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.blue

                                        Row {
                                            anchors {
                                                fill: parent
                                                margins: 3
                                            }

                                            spacing: 4

                                            GohuText {
                                                width: parent.width - 42
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: String(modelData || "")
                                                font.pixelSize: 7
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            ManagerButton {
                                                width: 34
                                                height: 22
                                                label: "×"
                                                dangerAccent: true
                                                onTriggered: {
                                                    root.profileStore.removeTarget(index);
                                                    root.markDirty();
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: parent.height - 366
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    Column {
                        anchors {
                            fill: parent
                            margins: 7
                        }

                        spacing: 5

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 5

                            ManagerInput {
                                id: setNameInput

                                width: parent.width - 88
                                height: 28
                                placeholderText: "PROFILE SET NAME"
                                text: root.setNameDraft

                                onEdited: root.setNameDraft = text
                            }

                            ManagerButton {
                                width: 83
                                height: 28
                                label: "SAVE SET"
                                primaryBlue: true
                                enabledAction:
                                    root.profileStore.queueCount > 0
                                    && setNameInput.text.trim().length > 0

                                onTriggered:
                                    root.profileStore.saveSet(
                                        setNameInput.text.trim(),
                                        root.currentDraft()
                                    )
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: "SAVED SETS // TARGETS + VISIBILITY + TOPICS + DESCRIPTION"
                            font.pixelSize: 7
                            color: Colors.cyan
                        }

                        Flickable {
                            width: parent.width
                            height: parent.height - 67
                            clip: true
                            contentWidth: width
                            contentHeight: savedColumn.height
                            boundsBehavior: Flickable.StopAtBounds

                            Column {
                                id: savedColumn

                                width: parent.width
                                spacing: 3

                                Repeater {
                                    model: root.profileStore.savedSets

                                    Rectangle {
                                        required property int index
                                        required property var modelData

                                        width: savedColumn.width
                                        height: 30
                                        color: Colors.black
                                        border.width: 1
                                        border.color: Colors.cyan

                                        Row {
                                            anchors {
                                                fill: parent
                                                margins: 3
                                            }

                                            spacing: 4

                                            GohuText {
                                                width: parent.width - 112
                                                anchors.verticalCenter: parent.verticalCenter
                                                text:
                                                    String(modelData.name || "SET")
                                                    + " // "
                                                    + String(
                                                        Array.isArray(modelData.targets)
                                                        ? modelData.targets.length
                                                        : 0
                                                    )
                                                font.pixelSize: 7
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }

                                            ManagerButton {
                                                width: 64
                                                height: 24
                                                label: "LOAD"
                                                onTriggered:
                                                    root.profileStore.loadSet(modelData)
                                            }

                                            ManagerButton {
                                                width: 40
                                                height: 24
                                                label: "×"
                                                dangerAccent: true
                                                onTriggered:
                                                    root.profileStore.deleteSet(modelData)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Column {
                width: (parent.width - 10) * 0.57
                height: parent.height
                spacing: 8

                Rectangle {
                    width: parent.width
                    height: 292
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.blue

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }

                        spacing: 7

                        GohuText {
                            text: "PROFILE PATCH"
                            font.pixelSize: 10
                            color: Colors.blue
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            GohuText {
                                width: 82
                                anchors.verticalCenter: parent.verticalCenter
                                text: "VISIBILITY"
                                font.pixelSize: 8
                                color: Colors.white
                            }

                            Repeater {
                                model: ["KEEP", "PRIVATE", "PUBLIC"]

                                ManagerButton {
                                    required property string modelData

                                    width: (parent.width - 97) / 3
                                    height: 28
                                    label: modelData
                                    selectedAction:
                                        root.visibilityMode
                                        === modelData.toLowerCase()

                                    onTriggered: {
                                        root.visibilityMode =
                                            modelData.toLowerCase();
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            GohuText {
                                width: 82
                                anchors.verticalCenter: parent.verticalCenter
                                text: "TOPICS"
                                font.pixelSize: 8
                                color: Colors.white
                            }

                            Repeater {
                                model: ["ADD", "REMOVE", "REPLACE"]

                                ManagerButton {
                                    required property string modelData

                                    width: (parent.width - 97) / 3
                                    height: 28
                                    label: modelData
                                    selectedAction:
                                        root.topicMode
                                        === modelData.toLowerCase()

                                    onTriggered: {
                                        root.topicMode =
                                            modelData.toLowerCase();
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        ManagerInput {
                            id: topicsInput

                            width: parent.width
                            placeholderText: "TOPICS // comma separated // post-apollo, quickshell, sway"
                            onEdited: root.markDirty()
                        }

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 5

                            GohuText {
                                width: 82
                                anchors.verticalCenter: parent.verticalCenter
                                text: "DESCRIPTION"
                                font.pixelSize: 8
                                color: Colors.white
                            }

                            Repeater {
                                model: ["KEEP", "SET", "CLEAR"]

                                ManagerButton {
                                    required property string modelData

                                    width: (parent.width - 97) / 3
                                    height: 28
                                    label: modelData
                                    selectedAction:
                                        root.descriptionMode
                                        === modelData.toLowerCase()

                                    onTriggered: {
                                        root.descriptionMode =
                                            modelData.toLowerCase();
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        ManagerInput {
                            id: descriptionInput

                            width: parent.width
                            placeholderText: "DESCRIPTION"
                            enabledInput: root.descriptionMode === "set"
                            onEdited: root.markDirty()
                        }

                        ManagerInput {
                            id: repositoryNameInput

                            width: parent.width
                            placeholderText:
                                root.profileStore.queueCount === 1
                                ? "REPOSITORY NAME / TITLE // optional rename"
                                : "REPOSITORY NAME / TITLE // single target only"
                            enabledInput: root.profileStore.queueCount === 1
                            onEdited: root.markDirty()
                        }

                        GohuText {
                            width: parent.width
                            text:
                                "NAME/TITLE MAPS TO THE GITHUB REPOSITORY NAME. "
                                + "RENAMING CHANGES ITS URL."
                            wrapMode: Text.Wrap
                            font.pixelSize: 7
                            color: Colors.orange
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: parent.height - 300
                    color: Colors.dark
                    border.width: 1
                    border.color:
                        root.profileService.lastError
                        ? Colors.red
                        : root.profileService.reviewReady
                        ? Colors.orange
                        : Colors.cyan

                    Column {
                        anchors {
                            fill: parent
                            margins: 8
                        }

                        spacing: 7

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6

                            ManagerButton {
                                width: 116
                                height: 30
                                label: "REVIEW"
                                enabledAction:
                                    !root.profileService.busy
                                    && root.profileStore.queueCount > 0

                                onTriggered:
                                    root.profileService.previewBatch(
                                        root.profileStore.queue,
                                        root.currentDraft()
                                    )
                            }

                            ManagerButton {
                                width: 126
                                height: 30
                                label:
                                    root.profileService.busy
                                    ? "APPLYING"
                                    : "APPLY BATCH"
                                primaryBlue: true
                                enabledAction:
                                    !root.profileService.busy
                                    && root.profileService.reviewReady

                                onTriggered:
                                    root.profileService.applyBatch(
                                        root.profileStore.queue,
                                        root.currentDraft()
                                    )
                            }

                            GohuText {
                                width: parent.width - 254
                                anchors.verticalCenter: parent.verticalCenter
                                horizontalAlignment: Text.AlignRight
                                text:
                                    root.profileService.reviewReady
                                    ? "REVIEWED // ARMED"
                                    : "REVIEW REQUIRED"
                                font.pixelSize: 8
                                color:
                                    root.profileService.reviewReady
                                    ? Colors.orange
                                    : Colors.cyan
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: parent.height - 45
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            clip: true

                            Flickable {
                                anchors.fill: parent
                                anchors.margins: 6
                                clip: true
                                contentWidth: width
                                contentHeight: reportText.paintedHeight
                                boundsBehavior: Flickable.StopAtBounds

                                GohuText {
                                    id: reportText

                                    width: parent.width
                                    text:
                                        root.profileService.reviewReady
                                        ? root.profileService.reviewText
                                        : root.profileService.resultText
                                          + (
                                              root.profileService.reviewText
                                              && root.profileService.reviewText
                                                 !== root.profileService.resultText
                                              ? "\n\n" + root.profileService.reviewText
                                              : ""
                                            )
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WrapAnywhere
                                    font.pixelSize: 8
                                    color:
                                        root.profileService.lastError
                                        ? Colors.red
                                        : Colors.white
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Column {
        id: accountManager

        anchors.fill: parent
        visible: root.profileMode === "account"
        spacing: 10

        Rectangle {
            width: parent.width
            height: 42
            color: Colors.dark
            border.width: 1
            border.color: Colors.blue

            Row {
                anchors {
                    fill: parent
                    margins: 8
                }

                spacing: 8

                GohuText {
                    width: parent.width - 206
                    anchors.verticalCenter: parent.verticalCenter
                    text: "GITHUB ACCOUNT PROFILE"
                    font.pixelSize: 11
                    color: Colors.blue
                }

                ManagerButton {
                    width: 106
                    height: 26
                    anchors.verticalCenter: parent.verticalCenter
                    label: "REPOSITORIES"
                    onTriggered: root.showRepositoryProfiles()
                }

                ManagerButton {
                    width: 84
                    height: 26
                    anchors.verticalCenter: parent.verticalCenter
                    label:
                        root.accountService.loading
                        ? "READING"
                        : "REFRESH"
                    enabledAction: !root.accountService.busy
                    onTriggered: root.accountService.refreshProfile()
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - 46

            Column {
                anchors {
                    fill: parent
                    topMargin: 2
                }

                spacing: 6

                Rectangle {
                    width: parent.width
                    height: 38
                    color: Colors.black
                    border.width: 1
                    border.color:
                        root.accountIdentityMode === "display"
                        && root.accountDirty
                        ? Colors.orange
                        : Colors.blue

                    Row {
                        anchors {
                            fill: parent
                            margins: 6
                        }

                        spacing: 7

                        GohuText {
                            width: 114
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                root.accountIdentityMode === "login"
                                ? "GITHUB LOGIN"
                                : "DISPLAY NAME"
                            font.pixelSize: 8
                            color: Colors.cyan
                        }

                        Item {
                            width: parent.width - 196
                            height: parent.height

                            GohuText {
                                anchors.fill: parent
                                visible: root.accountIdentityMode === "login"
                                verticalAlignment: Text.AlignVCenter
                                text:
                                    root.accountService.login
                                    ? "@" + root.accountService.login
                                    : "NOT LOADED"
                                font.pixelSize: 10
                                color: Colors.white
                                elide: Text.ElideRight
                            }

                            TextInput {
                                id: accountNameInput

                                anchors.fill: parent
                                visible: root.accountIdentityMode === "display"
                                enabled:
                                    visible
                                    && !root.accountService.busy
                                verticalAlignment: TextInput.AlignVCenter
                                selectByMouse: true
                                clip: true
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 9
                                color: Colors.white
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black

                                onTextChanged: {
                                    if (visible)
                                        root.accountDirty = true;
                                }

                                Keys.onEscapePressed: function(event) {
                                    focus = false;

                                    if (root.keyboardHost) {
                                        root.keyboardHost.activeTextEditor = null;
                                        root.keyboardHost.restoreGitKeyboardFocus(false);
                                    }

                                    event.accepted = true;
                                }

                                onActiveFocusChanged: {
                                    if (!root.keyboardHost)
                                        return;

                                    if (activeFocus)
                                        root.keyboardHost.activeTextEditor = accountNameInput;
                                    else if (root.keyboardHost.activeTextEditor === accountNameInput)
                                        root.keyboardHost.activeTextEditor = null;
                                }
                            }
                        }

                        ManagerButton {
                            width: 68
                            height: 26
                            anchors.verticalCenter: parent.verticalCenter
                            label:
                                root.accountIdentityMode === "login"
                                ? "DISPLAY"
                                : "LOGIN"
                            onTriggered:
                                root.accountIdentityMode =
                                    root.accountIdentityMode === "login"
                                    ? "display"
                                    : "login"
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 38
                    color: Colors.black
                    border.width: 1
                    border.color:
                        root.accountEmailMode === "primary"
                        ? (
                            root.accountService.primaryEmailAvailable
                            ? Colors.blue
                            : Colors.orange
                          )
                        : root.accountDirty
                        ? Colors.orange
                        : Colors.blue

                    Row {
                        anchors {
                            fill: parent
                            margins: 6
                        }

                        spacing: 7

                        GohuText {
                            width: 114
                            anchors.verticalCenter: parent.verticalCenter
                            text:
                                root.accountEmailMode === "primary"
                                ? "PRIMARY EMAIL"
                                : "PUBLIC EMAIL"
                            font.pixelSize: 8
                            color: Colors.cyan
                        }

                        Item {
                            width:
                                parent.width
                                - 196
                                - (
                                    root.accountEmailMode === "primary"
                                    ? 72
                                    : 0
                                  )
                            height: parent.height

                            GohuText {
                                anchors.fill: parent
                                visible: root.accountEmailMode === "primary"
                                verticalAlignment: Text.AlignVCenter
                                text:
                                    root.accountService.primaryEmailAvailable
                                    ? root.accountService.primaryEmail
                                    : root.accountService.primaryEmailMessage
                                font.pixelSize: 9
                                color:
                                    root.accountService.primaryEmailAvailable
                                    ? Colors.white
                                    : Colors.orange
                                elide: Text.ElideRight
                            }

                            TextInput {
                                id: accountEmailInput

                                anchors.fill: parent
                                visible: root.accountEmailMode === "public"
                                enabled:
                                    visible
                                    && !root.accountService.busy
                                verticalAlignment: TextInput.AlignVCenter
                                selectByMouse: true
                                clip: true
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 9
                                color: Colors.white
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black

                                onTextChanged: {
                                    if (visible)
                                        root.accountDirty = true;
                                }

                                Keys.onEscapePressed: function(event) {
                                    focus = false;

                                    if (root.keyboardHost) {
                                        root.keyboardHost.activeTextEditor = null;
                                        root.keyboardHost.restoreGitKeyboardFocus(false);
                                    }

                                    event.accepted = true;
                                }

                                onActiveFocusChanged: {
                                    if (!root.keyboardHost)
                                        return;

                                    if (activeFocus)
                                        root.keyboardHost.activeTextEditor = accountEmailInput;
                                    else if (root.keyboardHost.activeTextEditor === accountEmailInput)
                                        root.keyboardHost.activeTextEditor = null;
                                }
                            }
                        }

                        ManagerButton {
                            visible: root.accountEmailMode === "primary"
                            width: visible ? 72 : 0
                            height: 26
                            anchors.verticalCenter: parent.verticalCenter
                            label: "SETTINGS"
                            onTriggered:
                                Qt.openUrlExternally(
                                    "https://github.com/settings/emails"
                                )
                        }

                        ManagerButton {
                            width: 68
                            height: 26
                            anchors.verticalCenter: parent.verticalCenter
                            label:
                                root.accountEmailMode === "primary"
                                ? "PUBLIC"
                                : "PRIMARY"
                            onTriggered:
                                root.accountEmailMode =
                                    root.accountEmailMode === "primary"
                                    ? "public"
                                    : "primary"
                        }
                    }
                }

                GohuText {
                    width: parent.width
                    text:
                        "LOGIN + PRIMARY EMAIL ARE ACCOUNT IDENTITY. "
                        + "DISPLAY NAME + PUBLIC EMAIL ARE EDITABLE."
                    font.pixelSize: 7
                    color: Colors.orange
                    elide: Text.ElideRight
                }

                ManagerTextArea {
                    id: accountBioInput

                    width: parent.width
                    height: 72
                    placeholderText: "BIO"
                    enabledInput: !root.accountService.busy
                    onEdited: root.accountDirty = true
                }

                Row {
                    width: parent.width
                    height: 30
                    spacing: 8

                    ManagerButton {
                        width: 108
                        height: 30
                        label: "RESET"
                        enabledAction:
                            !root.accountService.busy
                            && root.accountDirty
                        onTriggered: root.loadAccountDraft()
                    }

                    ManagerButton {
                        width: 132
                        height: 30
                        label:
                            root.accountService.saving
                            ? "SAVING"
                            : "SAVE PROFILE"
                        primaryBlue: true
                        enabledAction:
                            !root.accountService.busy
                            && root.accountDirty

                        onTriggered:
                            root.accountService.saveProfile(
                                accountNameInput.text,
                                accountBioInput.text,
                                accountEmailInput.text
                            )
                    }

                    GohuText {
                        width: parent.width - 256
                        anchors.verticalCenter: parent.verticalCenter
                        horizontalAlignment: Text.AlignRight
                        text:
                            root.accountDirty
                            ? "UNSAVED CHANGES"
                            : "SYNCED"
                        font.pixelSize: 8
                        color:
                            root.accountDirty
                            ? Colors.orange
                            : Colors.cyan
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 42
                    color: Colors.black
                    border.width: 1
                    border.color:
                        root.accountService.lastError
                        ? Colors.red
                        : Colors.cyan

                    GohuText {
                        anchors {
                            fill: parent
                            margins: 7
                        }

                        text:
                            root.accountService.lastError
                            ? "ERROR // " + root.accountService.lastError
                            : root.accountService.stateText
                        wrapMode: Text.WrapAnywhere
                        font.pixelSize: 8
                        color:
                            root.accountService.lastError
                            ? Colors.red
                            : Colors.white
                    }
                }
            }
        }
    }

}
