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
    // Browser identity sessions are explicitly opt-in and live in MessagingW.
    // The launcher rail, family metadata, and credential notes stay separate.
    property bool isolatedBrowserModeActive: false
    property bool isolatedBrowserToggleAllowed: false
    signal isolatedBrowserModeToggleRequested()
    // Set by MessagingW to the shared content surface, not a new window.
    property Item settingsWorkspaceParent: null
    property int settingsContactWidth: 200
    property bool creatingIdentity: false
    property bool identityCreatePending: false
    property string identityCreateMode: "default"
    property string copyIdentityId: "identity-1"
    readonly property var identitySnapshot: SocialIdentityStore.snapshot
    readonly property var railRows: identitySnapshot.railRows || []
    readonly property var visibleAppIndices: identitySnapshot.visibleAppIndices || []
    // Non-authenticated profile hints and account labels, held in a private
    // local file distinct from the existing organization layout document.
    property string accountEditorIdentityId: ""
    property string accountSelectedServiceId: ""
    readonly property var accountDetails:
        SocialAccountDetailsStore.recordFor(identitySnapshot.activeId)

    function matchingAccountServices(query) {
        var term = String(query || "").trim().toLowerCase();
        return (identitySnapshot.appChoices || []).filter(function(c) {
            var a = messagingApps[c.serviceIndex];
            return a && (!term || a.name.toLowerCase().indexOf(term) !== -1
                         || c.id.indexOf(term) !== -1);
        }).slice(0, 8);
    }

    function refreshAccountForm() {
        var id = identitySnapshot.activeId;
        accountEditorIdentityId = id;
        var entry = SocialAccountDetailsStore.recordFor(id);
        accountEmailInput.text = entry.email || "";
        accountPhoneInput.text = entry.phone || "";
        if (accountSelectedServiceId)
            accountLabelInput.text =
                entry.accounts[accountSelectedServiceId] || "";
    }

    // Family editing only touches metadata for the identity active when its
    // controls were selected. Switches clear stale selections, even if two
    // identities happen to use the same stable family ID.
    property bool editingFamilies: false
    property string familyEditorIdentityId: ""
    property string editedFamilyId: ""
    property string editedAppId: ""
    property bool familyCreatePending: false
    property string pendingNewFamilyId: ""
    property string removalTargetFamilyId: ""
    property string removalConfirmIdentityId: ""
    property string removalConfirmFamilyId: ""
    property string removalConfirmTargetId: ""

    // A confirmation is scoped to a particular identity, family and target.
    function resetFamilyRemovalConfirmation() {
        removalConfirmIdentityId = "";
        removalConfirmFamilyId = "";
        removalConfirmTargetId = "";
    }

    function rehomeFamilyOptions() {
        if (!familyIsSelected()) return [];
        return (identitySnapshot.familyOptions || []).filter(function(f) {
            return f.id !== editedFamilyId;
        });
    }

    function removalTargetValid() {
        return rehomeFamilyOptions().some(function(f) {
            return f.id === removalTargetFamilyId;
        });
    }

    function familyCanBeRemoved() {
        var selected = selectedFamilyOption();
        return !!selected && (selected.count === 0 || removalTargetValid());
    }

    function familyRemovalConfirmationMatches() {
        var family = selectedFamilyOption();
        if (!family || !familyCanBeRemoved()) return false;
        return removalConfirmIdentityId === identitySnapshot.activeId
            && removalConfirmFamilyId === editedFamilyId
            && removalConfirmTargetId ===
               (family.count > 0 ? removalTargetFamilyId : "");
    }

    function familyIsSelected() {
        if (familyEditorIdentityId !== identitySnapshot.activeId)
            return false;
        return (identitySnapshot.familyOptions || []).some(function(f) {
            return f.id === editedFamilyId;
        });
    }

    function selectedAppNeedsMove() {
        if (!familyIsSelected() || !editedAppId) return false;
        var app = (identitySnapshot.appChoices || []).find(function(c) {
            return c.id === editedAppId;
        });
        return !!app && app.familyId !== editedFamilyId;
    }

    function selectedFamilyOption() {
        if (!familyIsSelected()) return null;
        return (identitySnapshot.familyOptions || []).find(function(f) {
            return f.id === editedFamilyId;
        }) || null;
    }

    function selectedAppOption() {
        if (familyEditorIdentityId !== identitySnapshot.activeId
                || !editedAppId) return null;
        return (identitySnapshot.appChoices || []).find(function(c) {
            return c.id === editedAppId;
        }) || null;
    }

    function familyCanStep(direction) {
        var family = selectedFamilyOption();
        return !!family && (direction === -1 || direction === 1)
               && family.orderIndex + direction >= 0
               && family.orderIndex + direction < family.familyCount;
    }

    function appCanStep(direction) {
        var app = selectedAppOption();
        return familyIsSelected() && !!app
               && app.familyId === editedFamilyId
               && (direction === -1 || direction === 1)
               && app.orderIndex + direction >= 0
               && app.orderIndex + direction < app.siblingCount;
    }

    // Search by existing displayed app names, with a short initial list.
    // No second service catalog or invented provider indices.
    function matchingFamilyApps(query) {
        var term = String(query || "").trim().toLowerCase();
        return (identitySnapshot.appChoices || []).filter(function(c) {
            var a = messagingApps[c.serviceIndex];
            return !!a && (!term || a.name.toLowerCase().indexOf(term) >= 0
                          || c.id.indexOf(term) >= 0);
        }).slice(0, 8);
    }

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
        appSelector.resetFamilyRemovalConfirmation();
        if (appSelector.accountEditorIdentityId !== appSelector.identitySnapshot.activeId) {
            appSelector.accountSelectedServiceId = "";
            accountServiceSearchInput.text = "";
            accountLabelInput.text = "";
            appSelector.refreshAccountForm();
        }
        if (appSelector.familyEditorIdentityId !== appSelector.identitySnapshot.activeId) {
            appSelector.familyEditorIdentityId = appSelector.identitySnapshot.activeId;
            appSelector.editedFamilyId = "";
            appSelector.editedAppId = "";
            appSelector.removalTargetFamilyId = "";
            familyNameInput.text = "";
            familySearchInput.text = "";
        } else if (appSelector.editedFamilyId !== ""
                   && !appSelector.familyIsSelected()
                   && !appSelector.familyCreatePending) {
            // A confirmed save removed the selected family.
            appSelector.editedFamilyId = "";
            appSelector.editedAppId = "";
            appSelector.removalTargetFamilyId = "";
            familyNameInput.text = "";
        }
    })

    // Inputs belong to one identity; the QML fields are never copied when
    // CREATE uses another identity's organization layout.
    onAccountDetailsChanged: Qt.callLater(function() {
        if (SocialAccountDetailsStore.state === "ready"
                && accountEditorIdentityId === identitySnapshot.activeId)
            appSelector.refreshAccountForm();
    })

    Connections {
        target: SocialAccountDetailsStore
        function onStateChanged() {
            if (SocialAccountDetailsStore.state === "ready")
                Qt.callLater(function() { appSelector.refreshAccountForm(); });
        }
    }

    onSettingsOpenChanged: {
        if (settingsOpen) {
            appSelector.refreshAccountForm();
            // The broader editor opens ready to organize, without requiring
            // a second click through the old narrow "EDIT FAMILIES" control.
            editingFamilies = true;
            familyEditorIdentityId = identitySnapshot.activeId;
        } else {
            appSelector.resetFamilyRemovalConfirmation();
        }
    }

    // Only clear the form after the actual atomic FileView save succeeds.
    Connections {
        target: SocialIdentityStore
        function onStorageStateChanged() {
            if (appSelector.identityCreatePending) {
                if (SocialIdentityStore.storageState === "ready") {
                    newIdentityName.text = "";
                    appSelector.creatingIdentity = false;
                    appSelector.identityCreatePending = false;
                } else if (SocialIdentityStore.storageState === "error"
                           || SocialIdentityStore.storageState === "unsupported") {
                    appSelector.identityCreatePending = false;
                }
            }
            if (appSelector.familyCreatePending) {
                if (SocialIdentityStore.storageState === "ready") {
                    appSelector.editedFamilyId = appSelector.pendingNewFamilyId;
                    appSelector.familyCreatePending = false;
                    appSelector.pendingNewFamilyId = "";
                } else if (SocialIdentityStore.storageState === "error"
                           || SocialIdentityStore.storageState === "unsupported") {
                    appSelector.familyCreatePending = false;
                    appSelector.pendingNewFamilyId = "";
                }
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
        // Live preview: family and app positions update after each saved edit.
        visible: true
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
                        : appSelector.messagingApps[0]

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
                            // Preview remains visible but cannot switch live accounts.
                            enabled: !appSelector.settingsOpen
    
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

    // The app rail remains an active, non-launching preview while settings
    // occupies the EXISTING contact-list and chat-feed areas of Social.
    // No second FloatingWindow or Sway geometry owner is introduced here.
    Rectangle {
        id: settingsPage
        parent: appSelector.settingsWorkspaceParent
                ? appSelector.settingsWorkspaceParent : appSelector
        anchors {
            top: parent.top
            bottom: parent.bottom
            left: appSelector.settingsWorkspaceParent
                  ? appSelector.right : parent.left
            right: parent.right
        }
        z: 10
        color: Colors.black
        visible: appSelector.settingsOpen
        clip: true
        border.width: 1
        border.color: Colors.cyan

        Row {
            anchors.fill: parent
            spacing: 0

            // Contact-list-sized identity and account setup column.
            Rectangle {
                id: settingsIdentityPane
                width: Math.min(parent.width, appSelector.settingsContactWidth)
                height: parent.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Flickable {
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: settingsIdentityColumn.height + 24
                    flickableDirection: Flickable.VerticalFlick
                    boundsBehavior: Flickable.StopAtBounds
                    clip: true

                    Column {
                        id: settingsIdentityColumn
                        anchors.top: parent.top
                        anchors.topMargin: 12
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.max(1, parent.width - 16)
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
                    text: appSelector.isolatedBrowserModeActive
                          ? "BROWSER SESSIONS // ISOLATED" : "LAYOUT ONLY"
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
                        width: settingsIdentityColumn.width
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
                            width: settingsIdentityColumn.width
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
                            width: settingsIdentityColumn.width
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
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                Text {
                    width: parent.width
                    text: "IDENTITY DETAILS"
                    color: Colors.orange
                    font.bold: true
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Contact defaults are saved locally, not sent to any service."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "DEFAULT EMAIL"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                Rectangle {
                    width: parent.width
                    height: 36
                    color: Colors.dark
                    border.color: Colors.orange
                    TextInput {
                        id: accountEmailInput
                        anchors.fill: parent
                        anchors.margins: 5
                        clip: true
                        selectByMouse: true
                        color: Colors.white
                        font.pixelSize: 11
                        maximumLength: 254
                        inputMethodHints: Qt.ImhEmailCharactersOnly
                    }
                }
                Text {
                    width: parent.width
                    text: "DEFAULT PHONE"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                Rectangle {
                    width: parent.width
                    height: 36
                    color: Colors.dark
                    border.color: Colors.orange
                    TextInput {
                        id: accountPhoneInput
                        anchors.fill: parent
                        anchors.margins: 5
                        clip: true
                        selectByMouse: true
                        color: Colors.white
                        font.pixelSize: 11
                        maximumLength: 24
                        inputMethodHints: Qt.ImhDialableCharactersOnly
                    }
                }
                ActionButton {
                    width: parent.width
                    height: 36
                    label: "SAVE CONTACT"
                    labelPixelSize: 9
                    interactive: appSelector.identitySnapshot.writable
                                 && SocialAccountDetailsStore.state === "ready"
                                 && appSelector.accountEditorIdentityId ===
                                    appSelector.identitySnapshot.activeId
                    onTriggered: SocialAccountDetailsStore.saveContact(
                        appSelector.identitySnapshot.activeId,
                        accountEmailInput.text, accountPhoneInput.text)
                }
                Text {
                    width: parent.width
                    visible: SocialAccountDetailsStore.state !== "ready"
                             || SocialAccountDetailsStore.errorCode !== ""
                    text: SocialAccountDetailsStore.state === "saving"
                          ? "Saving details..."
                          : (SocialAccountDetailsStore.errorCode || "Loading details...")
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WrapAnywhere
                }
                ActionButton {
                    width: parent.width
                    height: 33
                    label: "RELOAD DETAILS"
                    labelPixelSize: 9
                    contentPadding: 3
                    interactive: SocialAccountDetailsStore.state === "error"
                                 || SocialAccountDetailsStore.errorCode !== ""
                    onTriggered: SocialAccountDetailsStore.refresh()
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                Text {
                    width: parent.width
                    text: "LINKED ACCOUNTS"
                    color: Colors.orange
                    font.bold: true
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "BROWSER SESSIONS"
                    color: Colors.cyan
                    font.bold: true
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: appSelector.isolatedBrowserModeActive
                          ? "ISOLATED // EACH IDENTITY HAS NEW, SEPARATE BROWSER SIGN-IN"
                          : "LEGACY // CURRENT BROWSER ACCOUNTS ARE SHARED"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "This session only. Existing profiles stay untouched. New profiles start signed out."
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                ActionButton {
                    width: parent.width
                    height: 36
                    label: appSelector.isolatedBrowserModeActive
                           ? "USE LEGACY BROWSERS" : "USE ISOLATED BROWSERS"
                    labelPixelSize: 9
                    labelMinimumPixelSize: 8
                    contentPadding: 3
                    interactive: appSelector.isolatedBrowserToggleAllowed
                                 && appSelector.identitySnapshot.writable
                    onTriggered: appSelector.isolatedBrowserModeToggleRequested()
                }
                Text {
                    width: parent.width
                    text: "SETUP NOTES ONLY. A label does not connect or sign in."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 36
                    color: Colors.dark
                    border.color: Colors.orange
                    TextInput {
                        id: accountServiceSearchInput
                        anchors.fill: parent
                        anchors.margins: 5
                        color: Colors.white
                        clip: true
                        selectByMouse: true
                        font.pixelSize: 11
                        maximumLength: 40
                    }
                }
                Repeater {
                    model: appSelector.matchingAccountServices(
                               accountServiceSearchInput.text)
                    delegate: ActionButton {
                        required property var modelData
                        width: settingsIdentityColumn.width
                        height: 31
                        label: appSelector.messagingApps[modelData.serviceIndex].name
                        labelPixelSize: 9
                        labelMinimumPixelSize: 8
                        contentPadding: 3
                        selected: appSelector.accountSelectedServiceId === modelData.id
                        interactive: appSelector.identitySnapshot.writable
                                     && SocialAccountDetailsStore.state === "ready"
                        onTriggered: {
                            appSelector.accountSelectedServiceId = modelData.id;
                            accountLabelInput.text = appSelector.accountDetails.accounts[modelData.id]
                                                     || "";
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: appSelector.accountSelectedServiceId !== ""
                    text: "ACCOUNT NICKNAME // NO SECRETS"
                    color: Colors.cyan
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    width: parent.width
                    height: 36
                    visible: appSelector.accountSelectedServiceId !== ""
                    color: Colors.dark
                    border.color: Colors.orange
                    TextInput {
                        id: accountLabelInput
                        anchors.fill: parent
                        anchors.margins: 5
                        color: Colors.white
                        clip: true
                        selectByMouse: true
                        font.pixelSize: 11
                        maximumLength: 48
                    }
                }
                ActionButton {
                    width: parent.width
                    height: 36
                    label: "SAVE ACCOUNT NOTE"
                    labelPixelSize: 9
                    labelMinimumPixelSize: 8
                    contentPadding: 3
                    interactive: appSelector.identitySnapshot.writable
                                 && SocialAccountDetailsStore.state === "ready"
                                 && appSelector.accountSelectedServiceId !== ""
                                 && accountLabelInput.text.trim() !== ""
                                 && appSelector.accountEditorIdentityId ===
                                    appSelector.identitySnapshot.activeId
                    onTriggered: SocialAccountDetailsStore.setAccountLabel(
                        appSelector.identitySnapshot.activeId,
                        appSelector.accountSelectedServiceId,
                        accountLabelInput.text)
                }
                ActionButton {
                    width: parent.width
                    height: 33
                    label: "CLEAR NOTE"
                    labelPixelSize: 9
                    contentPadding: 3
                    interactive: appSelector.identitySnapshot.writable
                                 && SocialAccountDetailsStore.state === "ready"
                                 && appSelector.accountSelectedServiceId !== ""
                                 && appSelector.accountDetails.accounts[
                                       appSelector.accountSelectedServiceId] !== undefined
                    onTriggered: SocialAccountDetailsStore.setAccountLabel(
                        appSelector.identitySnapshot.activeId,
                        appSelector.accountSelectedServiceId, "")
                }
                Text {
                    width: parent.width
                    text: "AUTHENTICATION // NOT CONNECTED BY THESE CONTROLS"
                    color: Colors.orange
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Existing Telegram and browser sign-in paths stay unchanged."
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                    }
                }
            }

            // Chat-feed-sized organization workspace. Independent scrolling
            // means app edits do not lose the chosen family or identity.
            Rectangle {
                id: settingsEditorPane
                width: Math.max(1, parent.width - settingsIdentityPane.width)
                height: parent.height
                color: Colors.black

                Row {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        id: settingsFamilyPane
                        width: Math.min(parent.width,
                                        Math.max(170, Math.round(parent.width * 0.36)))
                        height: parent.height
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.cyan

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
                                width: Math.max(1, parent.width - 16)
                                spacing: 12
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
                    text: "Active: " + appSelector.identitySnapshot.activeName
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WrapAnywhere
                }
                ActionButton {
                    width: parent.width
                    height: 36
                    label: appSelector.editingFamilies ? "CLOSE EDIT" : "EDIT FAMILIES"
                    labelPixelSize: 9
                    contentPadding: 3
                    interactive: appSelector.identitySnapshot.writable
                    onTriggered: {
                        appSelector.editingFamilies = !appSelector.editingFamilies;
                        appSelector.familyEditorIdentityId =
                            appSelector.identitySnapshot.activeId;
                        appSelector.editedFamilyId = "";
                        appSelector.editedAppId = "";
                        appSelector.removalTargetFamilyId = "";
                        appSelector.resetFamilyRemovalConfirmation();
                        familyNameInput.text = "";
                        familySearchInput.text = "";
                    }
                }
                                Column {
                                    width: parent.width
                                    spacing: 8
                                    visible: appSelector.editingFamilies
                    Text {
                        width: parent.width
                        text: "SELECT FAMILY"
                        color: Colors.cyan
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: appSelector.identitySnapshot.familyOptions || []
                        delegate: ActionButton {
                            required property var modelData
                            width: settingsColumn.width
                            height: 33
                            label: modelData.title
                            labelPixelSize: 9
                            labelMinimumPixelSize: 8
                            contentPadding: 3
                            selected: appSelector.editedFamilyId === modelData.id
                            interactive: appSelector.identitySnapshot.writable
                                         && appSelector.familyEditorIdentityId ===
                                            appSelector.identitySnapshot.activeId
                            onTriggered: {
                                appSelector.editedFamilyId = modelData.id;
                                appSelector.removalTargetFamilyId = "";
                                appSelector.resetFamilyRemovalConfirmation();
                                familyNameInput.text = modelData.title;
                            }
                        }
                    }
                    ActionButton {
                        width: parent.width
                        height: 32
                        label: "FAMILY UP"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.familyCanStep(-1)
                        onTriggered: SocialIdentityStore.reorderFamily(
                            appSelector.editedFamilyId, -1)
                    }
                    ActionButton {
                        width: parent.width
                        height: 32
                        label: "FAMILY DOWN"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.familyCanStep(1)
                        onTriggered: SocialIdentityStore.reorderFamily(
                            appSelector.editedFamilyId, 1)
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.identitySnapshot.familyOptions.length === 0
                        text: "NO FAMILIES"
                        color: Colors.orange
                        font.pixelSize: 9
                    }
                    Text {
                        width: parent.width
                        text: "FAMILY NAME"
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
                            id: familyNameInput
                            anchors.fill: parent
                            anchors.margins: 5
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 11
                            color: Colors.white
                            clip: true
                            selectByMouse: true
                            maximumLength: 32
                        }
                    }
                    ActionButton {
                        width: parent.width
                        height: 34
                        label: "+ FAMILY"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && familyNameInput.text.trim().length > 0
                                     && appSelector.identitySnapshot.familyOptions.length < 20
                                     && appSelector.familyEditorIdentityId ===
                                        appSelector.identitySnapshot.activeId
                                     && !appSelector.familyCreatePending
                        onTriggered: {
                            // The ID is derived from the validated store snapshot.
                            // Show the new selection only after storage confirms the save.
                            var newId = "family-" + appSelector.identitySnapshot.nextFamilyId;
                            if (SocialIdentityStore.createFamily(familyNameInput.text)) {
                                appSelector.pendingNewFamilyId = newId;
                                appSelector.familyCreatePending = true;
                            }
                        }
                    }
                    ActionButton {
                        width: parent.width
                        height: 34
                        label: "RENAME"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.familyIsSelected()
                                     && familyNameInput.text.trim().length > 0
                        onTriggered: SocialIdentityStore.renameFamily(
                            appSelector.editedFamilyId, familyNameInput.text)
                    }
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                    }
                    Text {
                        width: parent.width
                        text: "REMOVE FAMILY"
                        color: Colors.orange
                        font.pixelSize: 9
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.familyIsSelected()
                        text: appSelector.selectedFamilyOption()
                              ? (appSelector.selectedFamilyOption().count
                                 + " assigned apps") : ""
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WrapAnywhere
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.selectedFamilyOption() !== null
                                 && appSelector.selectedFamilyOption().count > 0
                        text: "REHOME TO"
                        color: Colors.cyan
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: appSelector.selectedFamilyOption()
                               && appSelector.selectedFamilyOption().count > 0
                               ? appSelector.rehomeFamilyOptions() : []
                        delegate: ActionButton {
                            required property var modelData
                            width: settingsColumn.width
                            height: 32
                            label: modelData.title
                            labelPixelSize: 9
                            labelMinimumPixelSize: 8
                            contentPadding: 3
                            selected: appSelector.removalTargetFamilyId === modelData.id
                            interactive: appSelector.identitySnapshot.writable
                                         && appSelector.familyIsSelected()
                            onTriggered: {
                                appSelector.removalTargetFamilyId = modelData.id;
                                appSelector.resetFamilyRemovalConfirmation();
                            }
                        }
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.selectedFamilyOption() !== null
                                 && appSelector.selectedFamilyOption().count > 0
                                 && appSelector.rehomeFamilyOptions().length === 0
                        text: "CREATE ANOTHER FAMILY FIRST"
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.familyIsSelected()
                        text: appSelector.selectedFamilyOption()
                              && appSelector.selectedFamilyOption().count > 0
                              ? "Apps append to destination. Hidden stays hidden."
                              : "Empty family: no apps to move."
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: parent.width
                        height: 36
                        label: appSelector.familyRemovalConfirmationMatches()
                               ? "CONFIRM REMOVE" : "REMOVE FAMILY"
                        labelPixelSize: 9
                        labelMinimumPixelSize: 8
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.familyCanBeRemoved()
                                     && !appSelector.familyCreatePending
                        onTriggered: {
                            if (!appSelector.familyCanBeRemoved()) return;
                            var family = appSelector.selectedFamilyOption();
                            if (!family) return;
                            var destination = family.count > 0
                                ? appSelector.removalTargetFamilyId : "";
                            if (!appSelector.familyRemovalConfirmationMatches()) {
                                appSelector.removalConfirmIdentityId =
                                    appSelector.identitySnapshot.activeId;
                                appSelector.removalConfirmFamilyId =
                                    appSelector.editedFamilyId;
                                appSelector.removalConfirmTargetId = destination;
                            } else {
                                // Store validation independently enforces rehome.
                                if (SocialIdentityStore.removeFamily(
                                        appSelector.editedFamilyId, destination))
                                    appSelector.resetFamilyRemovalConfirmation();
                            }
                        }
                    }
                    Text {
                        width: parent.width
                        visible: SocialIdentityStore.familyActionError !== ""
                        text: "FAMILY: " + SocialIdentityStore.familyActionError
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WrapAnywhere
                    }
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        id: settingsAppPane
                        width: Math.max(1, parent.width - settingsFamilyPane.width)
                        height: parent.height
                        color: Colors.black
                        border.width: 1
                        border.color: Colors.cyan

                        Flickable {
                            anchors.fill: parent
                            contentWidth: width
                            contentHeight: settingsAppsColumn.height + 24
                            flickableDirection: Flickable.VerticalFlick
                            boundsBehavior: Flickable.StopAtBounds
                            clip: true

                            Column {
                                id: settingsAppsColumn
                                anchors.top: parent.top
                                anchors.topMargin: 12
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: Math.max(1, parent.width - 20)
                                spacing: 12

                                Text {
                                    width: parent.width
                                    text: "APP ORGANIZATION"
                                    color: Colors.orange
                                    font.pixelSize: 13
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                }
                                Text {
                                    width: parent.width
                                    text: "Saved edits update the live rail on the left."
                                    color: Colors.white
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                }
                                Column {
                                    width: parent.width
                                    spacing: 8
                                    visible: appSelector.editingFamilies
                    Text {
                        width: parent.width
                        text: "MOVE APP"
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Text {
                        width: parent.width
                        text: "Select a family above, then search for an app."
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Rectangle {
                        width: parent.width
                        height: 36
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.orange
                        TextInput {
                            id: familySearchInput
                            anchors.fill: parent
                            anchors.margins: 5
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 11
                            color: Colors.white
                            clip: true
                            selectByMouse: true
                            maximumLength: 40
                        }
                    }
                    Text {
                        width: parent.width
                        text: "First 8 matches"
                        color: Colors.white
                        font.pixelSize: 9
                    }
                    Repeater {
                        model: appSelector.matchingFamilyApps(familySearchInput.text)
                        delegate: ActionButton {
                            required property var modelData
                            width: settingsAppsColumn.width
                            height: 32
                            label: appSelector.messagingApps[modelData.serviceIndex].name
                            labelPixelSize: 9
                            labelMinimumPixelSize: 8
                            contentPadding: 3
                            selected: appSelector.editedAppId === modelData.id
                            interactive: appSelector.identitySnapshot.writable
                                         && appSelector.familyEditorIdentityId ===
                                            appSelector.identitySnapshot.activeId
                            onTriggered: appSelector.editedAppId = modelData.id
                        }
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.matchingFamilyApps(familySearchInput.text).length === 0
                        text: "NO MATCH"
                        color: Colors.orange
                        font.pixelSize: 9
                    }
                    ActionButton {
                        width: parent.width
                        height: 36
                        label: "MOVE HERE"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.selectedAppNeedsMove()
                        onTriggered: SocialIdentityStore.moveAppToFamily(
                            appSelector.editedAppId, appSelector.editedFamilyId)
                    }
                    Text {
                        width: parent.width
                        visible: appSelector.selectedAppOption() !== null
                        text: appSelector.selectedAppOption()
                              ? ("IN: " + appSelector.selectedAppOption().familyTitle
                                 + (appSelector.selectedAppOption().hidden
                                    ? " / HIDDEN" : " / SHOWN")) : ""
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WrapAnywhere
                    }
                    ActionButton {
                        width: parent.width
                        height: 32
                        label: "APP UP"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.appCanStep(-1)
                        onTriggered: SocialIdentityStore.reorderApp(
                            appSelector.editedFamilyId, appSelector.editedAppId, -1)
                    }
                    ActionButton {
                        width: parent.width
                        height: 32
                        label: "APP DOWN"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.appCanStep(1)
                        onTriggered: SocialIdentityStore.reorderApp(
                            appSelector.editedFamilyId, appSelector.editedAppId, 1)
                    }
                    ActionButton {
                        width: parent.width
                        height: 34
                        label: appSelector.selectedAppOption()
                               && appSelector.selectedAppOption().hidden
                               ? "SHOW APP" : "HIDE APP"
                        labelPixelSize: 9
                        contentPadding: 3
                        interactive: appSelector.identitySnapshot.writable
                                     && appSelector.selectedAppOption() !== null
                                     && appSelector.selectedAppOption().familyId !== ""
                        onTriggered: {
                            var app = appSelector.selectedAppOption();
                            if (app)
                                SocialIdentityStore.setAppHidden(
                                    app.id, !app.hidden);
                        }
                    }
                    Text {
                        width: parent.width
                        text: "Hidden apps keep their family and account."
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        width: parent.width
                        text: "Only button placement changes. Logins stay unchanged."
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                                }
                            }
                        }
                    }
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
