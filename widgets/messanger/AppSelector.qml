import QtQuick
import Quickshell
import "../../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import qs.services.social

Rectangle {
    id: appSelector

    // ============================================================
    // STATE
    // ============================================================

    property int selectedIndex: 0
    property bool keyboardActive: false
    property string statusText: ""
    // Entry-point shell only. Identity storage, credentials and family layouts
    // are deliberately reserved for subsequent operator-reviewed slices.
    property bool settingsOpen: false
    property bool creatingIdentity: false
    property bool identityCreatePending: false
    property string identityCreateMode: "default"
    property string copyIdentityId: "identity-1"
    readonly property var identitySnapshot: SocialIdentityStore.snapshot
    readonly property var railRows: identitySnapshot.railRows || []
    readonly property var visibleAppIndices: identitySnapshot.visibleAppIndices || []

    // Cursor tracks the legacy provider index, not a re-ordered visual row.
    function isAppVisible(index) {
        return visibleAppIndices.indexOf(index) !== -1;
    }
    function ensureValidSelection() {
        if (!visibleAppIndices.length) selectedIndex = -1;
        else if (!isAppVisible(selectedIndex)) selectedIndex = visibleAppIndices[0];
    }
    function moveSelection(direction) {
        var list = visibleAppIndices;
        if (!list.length) { selectedIndex = -1; return; }
        var pos = list.indexOf(selectedIndex);
        selectedIndex = pos < 0
            ? (direction < 0 ? list[list.length - 1] : list[0])
            : list[(pos + direction + list.length) % list.length];
    }
    function nextActiveAppIndex(activeIndex, reverse) {
        var list = visibleAppIndices;
        if (!list.length) return -1;
        var pos = list.indexOf(activeIndex);
        return pos < 0 ? (reverse ? list[list.length - 1] : list[0])
            : list[(pos + (reverse ? -1 : 1) + list.length) % list.length];
    }
    onIdentitySnapshotChanged: Qt.callLater(function() {
        appSelector.ensureValidSelection();
        appSelector.ensureSelectedVisible();
    })

    // Only clear the form after the actual atomic FileView save succeeds.
    Connections {
        target: SocialIdentityStore
        function onStorageStateChanged() {
            if (!appSelector.identityCreatePending)
                return;
            if (SocialIdentityStore.storageState === "ready") {
                newIdentityName.text = "";
                appSelector.creatingIdentity = false;
                appSelector.identityCreatePending = false;
            } else if (SocialIdentityStore.storageState === "error"
                       || SocialIdentityStore.storageState === "unsupported") {
                appSelector.identityCreatePending = false;
            }
        }
    }

    // Emitted ONLY when a button is actually clicked.
    signal appActivated(int index)

    // ============================================================
    // APPS
    // ============================================================

    property var messagingApps: [
        {
            name: "SESSIONS",
            icon: "../../assets/Sessions.png"
        },
        {
            name: "DISCORD",
            icon: ""
        },
        {
            name: "TELEGRAM",
            icon: ""
        },
        {
            name: "X",
            icon: ""
        },
        {
            name: "INSTAGRAM",
            icon: ""
        },
        {
            name: "FACEBOOK",
            icon: ""
        },
        {
            name: "REDDIT",
            icon: ""
        },
        {
            name: "THREADS",
            icon: ""
        },
        {
            name: "PINTEREST",
            icon: ""
        },
        {
            name: "TRUTH SOCIAL",
            icon: ""
        },
        {
            name: "BLUESKY",
            icon: ""
        },
        {
            name: "TUMBLR",
            icon: ""
        },
        {
            name: "TIKTOK",
            icon: ""
        },
        {
            name: "SNAPCHAT",
            icon: ""
        },
        {
            name: "WHATSAPP",
            icon: ""
        },
        {
            name: "MESSENGER",
            icon: ""
        },
        {
            name: "LINKEDIN",
            icon: ""
        },
        {
            name: "MASTODON",
            icon: ""
        },
        {
            name: "NEXTDOOR",
            icon: ""
        },
        {
            name: "STEAM CHAT",
            icon: ""
        },
        {
            name: "ELEMENT",
            icon: ""
        },
        {
            name: "GROUPME",
            icon: ""
        },
        {
            name: "LEMON8",
            icon: ""
        },
        {
            name: "QUORA",
            icon: ""
        },
        {
            name: "PIXELFED",
            icon: ""
        },
        {
            name: "ZALO",
            icon: ""
        },
        {
            name: "SIGNAL",
            icon: ""
        },
        {
            name: "WECHAT",
            icon: ""
        },
        {
            name: "LINE",
            icon: ""
        },
        {
            name: "VIBER",
            icon: ""
        },
        {
            name: "KAKAOTALK",
            icon: ""
        },
        {
            name: "BEREAL",
            icon: ""
        }
    ]

    // ============================================================
    // SIZE / PANEL
    // ============================================================

    implicitWidth: 110
    implicitHeight: 700

    opacity: 0.90
    color: Colors.black

    border.width: 1
    border.color: Colors.cyan

    radius: 0

    // ============================================================
    // APP BUTTONS
    // ============================================================

    // Scroll within Social's existing fixed-height cyan selector frame.
    // Keyboard/Tab selection stays visible without changing activation rules.
    function ensureSelectedVisible() {
        if (appScroll.height <= 0 || selectedIndex < 0) return;
        var rowTop = 10;
        var rowBottom = -1;
        for (var i = 0; i < railRows.length; i++) {
            var row = railRows[i];
            var height = row.kind === "family" ? 42
                       : row.kind === "empty" ? 56 : 50;
            if (row.kind === "app" && row.serviceIndex === selectedIndex) {
                rowBottom = rowTop + height;
                break;
            }
            rowTop += height + appColumn.spacing;
        }
        if (rowBottom < 0) return; // A collapsed app has no scroll target.
        var target = appScroll.contentY;
        if (rowTop < target) target = rowTop;
        else if (rowBottom > target + appScroll.height)
            target = rowBottom - appScroll.height;
        appScroll.contentY = Math.max(0, Math.min(
            target, Math.max(0, appScroll.contentHeight - appScroll.height)));
    }

    onSelectedIndexChanged: Qt.callLater(function() {
        appSelector.ensureSelectedVisible();
    })

    Flickable {
        id: appScroll
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top
        }
        contentWidth: width
        contentHeight: appColumn.height + 20
        visible: !appSelector.settingsOpen
        clip: true
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds
        onHeightChanged: appSelector.ensureSelectedVisible()
        onContentHeightChanged: appSelector.ensureSelectedVisible()

        Column {
            id: appColumn
    
            anchors {
                top: parent.top
                horizontalCenter: parent.horizontalCenter
                topMargin: 10
            }
    
            spacing: 10
    
            Repeater {
                model: appSelector.railRows
    
                delegate: Item {
                    id: buttonContainer
    
                    required property var modelData
                    required property int index
                    readonly property bool isAppRow: modelData.kind === "app"
                    readonly property bool isFamilyRow: modelData.kind === "family"
                    readonly property var appData: isAppRow
                        ? appSelector.messagingApps[modelData.serviceIndex]
                        : ({name:"", icon:""})

                    width: 90
                    height: isFamilyRow ? 42 : modelData.kind === "empty" ? 56 : 50

                    ActionButton {
                        anchors.fill: parent
                        visible: buttonContainer.isFamilyRow
                        interactive: visible && appSelector.identitySnapshot.writable
                        label: (buttonContainer.modelData.expanded ? "▾ " : "▸ ")
                               + buttonContainer.modelData.title
                        labelPixelSize: 9
                        labelMinimumPixelSize: 8
                        contentPadding: 3
                        accentColor: Colors.cyan
                        onTriggered: SocialIdentityStore.toggleFamily(
                            buttonContainer.modelData.familyId)
                    }

                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 4
                        visible: buttonContainer.modelData.kind === "empty"
                        text: "NO FAMILIES\nUSE SETTINGS"
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Rectangle {
                        id: appButton
                        visible: buttonContainer.isAppRow
    
                        anchors.fill: parent
    
                        radius: 0
                        clip: false
    
                        property bool isSelected: appSelector.selectedIndex === buttonContainer.modelData.serviceIndex
    
                        property bool isHovered: !appSelector.keyboardActive && appMouse.containsMouse
    
                        property bool isPressed: appMouse.pressed
    
                        // ============================================
                        // POWER-STYLE BUTTON COLOR
                        // ============================================
    
                        color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.yellow : appButton.isSelected ? Colors.yellow : Colors.dark
    
                        // ============================================
                        // CONTENT
                        // ============================================
    
                        Row {
                            id: appContent
    
                            anchors.centerIn: parent
    
                            spacing: buttonContainer.appData.icon !== "" ? 4 : 0
    
                            // ========================================
                            // APP ICON
                            // ========================================
    
                            Item {
                                id: iconContainer
    
                                width: buttonContainer.appData.icon !== "" ? 14 : 0
    
                                height: 18
    
                                visible: buttonContainer.appData.icon !== ""
    
                                Image {
                                    id: appIcon
    
                                    anchors.centerIn: parent
    
                                    width: 14
                                    height: 14
    
                                    source: buttonContainer.appData.icon !== "" ? Qt.resolvedUrl(buttonContainer.appData.icon) : ""
    
                                    fillMode: Image.PreserveAspectFit
    
                                    smooth: false
    
                                    opacity: appButton.isPressed ? 1.0 : appButton.isSelected || appButton.isHovered ? 1.0 : 0.80
                                }
    
                                DropShadow {
                                    anchors.fill: appIcon
                                    source: appIcon
    
                                    horizontalOffset: 0
                                    verticalOffset: 0
    
                                    radius: 8
                                    samples: 12
    
                                    color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                                    opacity: appButton.isPressed ? 0.55 : appButton.isHovered ? 0.45 : appButton.isSelected ? 0.45 : 0.18
    
                                    transparentBorder: true
                                }
                            }
    
                            // ========================================
                            // APP NAME
                            // ========================================
    
                            Text {
                                id: appText
    
                                anchors.verticalCenter: parent.verticalCenter
    
                                text: buttonContainer.appData.name
    
                                font.family: "GohuFont 11 Nerd Font Mono"
    
                                font.pixelSize: buttonContainer.appData.name === "TRUTH SOCIAL" ? 9 : buttonContainer.appData.icon !== "" ? 10 : 11
    
                                color: appButton.isPressed ? Colors.black : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                                layer.enabled: appButton.isSelected || appButton.isHovered
    
                                layer.effect: DropShadow {
                                    color: Colors.orange
    
                                    opacity: 1.0
    
                                    horizontalOffset: 0
                                    verticalOffset: 0
    
                                    radius: 30
                                    samples: 60
    
                                    transparentBorder: true
                                }
                            }
                        }
    
                        // ============================================
                        // MOUSE
                        // ============================================
    
                        MouseArea {
                            id: appMouse
    
                            anchors.fill: parent
    
                            hoverEnabled: true
    
                            acceptedButtons: Qt.LeftButton
    
                            // Hover may move the visual selector,
                            // but it does NOT activate/open an app.
                            onEntered: {
                                appSelector.keyboardActive = false;
                                appSelector.selectedIndex = buttonContainer.modelData.serviceIndex;
                            }
    
                            // The button itself owns activation.
                            onClicked: function (mouse) {
                                if (mouse.button !== Qt.LeftButton
                                        || !appSelector.isAppVisible(buttonContainer.modelData.serviceIndex))
                                    return;
    
                                appSelector.selectedIndex = buttonContainer.modelData.serviceIndex;
    
                                appSelector.appActivated(buttonContainer.modelData.serviceIndex);
    
                                console.log("Selected:", buttonContainer.appData.name);
                            }
                        }
    
                        // ============================================
                        // CLOCK-STYLE CLOSE GLOW
                        // ============================================
    
                        RectangularShadow {
                            anchors.fill: parent
    
                            spread: 3
    
                            color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                            opacity: appButton.isPressed ? 0.60 : appButton.isHovered ? 0.50 : appButton.isSelected ? 0.50 : 0.0
    
                            z: -1
                        }
    
                        // ============================================
                        // CLOCK-STYLE WIDE GLOW
                        // ============================================
    
                        RectangularShadow {
                            anchors.fill: parent
    
                            spread: 10
    
                            color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                            opacity: appButton.isPressed ? 0.12 : appButton.isHovered ? 0.09 : appButton.isSelected ? 0.09 : 0.0
    
                            z: -2
                        }
                    }
                }
            }
        }
    }

    // Settings stays inside the selector's existing 110 px input region.
    // A wider pop-out must be handled separately: external browser/Discord
    // modes deliberately mask off the content region for pointer pass-through.
    Rectangle {
        id: settingsPage
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top
        }
        color: Colors.black
        visible: appSelector.settingsOpen
        clip: true

        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: settingsColumn.height + 24
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            Column {
                id: settingsColumn
                anchors.top: parent.top
                anchors.topMargin: 12
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.max(1, parent.width - 14)
                spacing: 12

                Text {
                    width: parent.width
                    text: "USER //\nSETTINGS"
                    color: Colors.orange
                    horizontalAlignment: Text.AlignHCenter
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 11
                    font.bold: true
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                Text {
                    width: parent.width
                    text: "IDENTITIES"
                    color: Colors.cyan
                    font.pixelSize: 10
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "LAYOUT ONLY"
                    color: Colors.orange
                    font.pixelSize: 9
                }
                Text {
                    width: parent.width
                    visible: !appSelector.identitySnapshot.writable
                    text: appSelector.identitySnapshot.state === "saving"
                          ? "Saving..." :
                          appSelector.identitySnapshot.error
                          ? "Storage blocked: " + appSelector.identitySnapshot.error
                          : "Loading..."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: appSelector.identitySnapshot.identities
                    delegate: ActionButton {
                        required property var modelData
                        width: settingsColumn.width
                        height: 34
                        label: modelData.name
                        labelPixelSize: 9
                        contentPadding: 4
                        selected: appSelector.identitySnapshot.activeId === modelData.id
                        interactive: appSelector.identitySnapshot.writable
                        onTriggered: SocialIdentityStore.selectIdentity(modelData.id)
                    }
                }
                ActionButton {
                    width: parent.width
                    height: 36
                    label: appSelector.creatingIdentity ? "CANCEL NEW" : "+ NEW ID"
                    labelPixelSize: 9
                    contentPadding: 3
                    interactive: appSelector.identitySnapshot.writable
                    onTriggered: {
                        appSelector.creatingIdentity = !appSelector.creatingIdentity;
                        appSelector.identityCreateMode = "default";
                        appSelector.copyIdentityId = appSelector.identitySnapshot.activeId;
                        newIdentityName.text = "";
                    }
                }
                Column {
                    width: parent.width
                    spacing: 8
                    visible: appSelector.creatingIdentity

                    Text {
                        width: parent.width
                        text: "NAME"
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Rectangle {
                        width: parent.width
                        height: 36
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange
                        TextInput {
                            id: newIdentityName
                            anchors.fill: parent
                            anchors.margins: 5
                            color: Colors.white
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 11
                            clip: true
                            selectByMouse: true
                            maximumLength: 32
                        }
                    }
                    Text {
                        width: parent.width
                        text: "START FROM"
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Repeater {
                        model: [
                            {mode:"default", title:"DEFAULT"},
                            {mode:"copy", title:"COPY"},
                            {mode:"empty", title:"EMPTY"}
                        ]
                        delegate: ActionButton {
                            required property var modelData
                            width: settingsColumn.width
                            height: 32
                            label: modelData.title
                            labelPixelSize: 9
                            selected: appSelector.identityCreateMode === modelData.mode
                            interactive: appSelector.identitySnapshot.writable
                            onTriggered: appSelector.identityCreateMode = modelData.mode
                        }
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.identityCreateMode === "default"
                        text: "ALL APPS (TEMP)"
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.identityCreateMode === "copy"
                        text: "COPY FROM"
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Repeater {
                        model: appSelector.identityCreateMode === "copy"
                               ? appSelector.identitySnapshot.identities : []
                        delegate: ActionButton {
                            required property var modelData
                            width: settingsColumn.width
                            height: 31
                            label: modelData.name
                            labelPixelSize: 9
                            selected: appSelector.copyIdentityId === modelData.id
                            interactive: appSelector.identitySnapshot.writable
                            onTriggered: appSelector.copyIdentityId = modelData.id
                        }
                    }
                    ActionButton {
                        width: parent.width
                        height: 36
                        label: appSelector.identityCreatePending ? "SAVING" : "CREATE"
                        labelPixelSize: 9
                        interactive: appSelector.identitySnapshot.writable
                                     && newIdentityName.text.trim().length > 0
                                     && !appSelector.identityCreatePending
                        onTriggered: {
                            appSelector.identityCreatePending =
                                SocialIdentityStore.createIdentity(
                                    newIdentityName.text,
                                    appSelector.identityCreateMode,
                                    appSelector.copyIdentityId);
                        }
                    }
                }
                Text {
                    width: parent.width
                    text: "Identity layout selection does not switch live accounts yet."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "BUTTON FAMILIES"
                    color: Colors.cyan
                    font.pixelSize: 9
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Layout manager is next"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "LINKED ACCOUNTS"
                    color: Colors.cyan
                    font.pixelSize: 9
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Not connected to this menu"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "API CREDENTIALS"
                    color: Colors.cyan
                    font.pixelSize: 9
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Existing service setup unchanged"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    // This entry point is always visible, independently of app scrolling and
    // status/error text. Its click must never activate a provider app index.
    ActionButton {
        id: settingsFooter
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        width: parent.width - 12
        height: 44
        label: "USER // SETTINGS"
        labelPixelSize: 8
        labelMinimumPixelSize: 8
        contentPadding: 2
        accentColor: Colors.cyan
        selected: appSelector.settingsOpen
        onTriggered: appSelector.settingsOpen = !appSelector.settingsOpen
    }

    // Keep launch errors visible in the selector even when the external
    // browser owns the rest of Social's click-through window.
    Text {
        id: statusMessage
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: settingsFooter.top
        anchors.margins: 6
        visible: appSelector.statusText !== ""
        text: appSelector.statusText
        wrapMode: Text.WrapAnywhere
        font.pixelSize: 9
        color: Colors.orange
        maximumLineCount: 7
        elide: Text.ElideRight
    }

}
