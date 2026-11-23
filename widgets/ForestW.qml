import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"
import "ForestChassisPolicy.js" as ForestSizing
import "../services/forest"

// FOREST V0: self-contained visual workspace. No model, PX or Hospital calls.
PanelWindow {
    id: root

    property bool menuOpen: false
    // Forest B0 inventory only proves model discovery. It is not permission
    // to record audio, submit a prompt, or attach a provider session.
    // Until protected Forest host adapters exist both controls fail closed.
    readonly property bool voiceHostTrusted: false
    readonly property bool chatHostTrusted: false
    // No session provider is authorized yet. Do not synthesize active chats
    // from Tree names, model inventory, or the LIVE workspace indicator.
    readonly property var activeChatSessions: []
    property real dockCenterX: 0
    // Read-only reference solely for Git's fullscreen size cap.
    property var gitFullscreenReference: null
    property int chassisLevel: 0
    property int selectedTreeIndex: 0
    // One explicit model choice per Tree. Inventory refreshes never silently
    // switch either Tree to the first returned model.
    property var selectedTreeModels: ["", "", "", "", ""]
    // Per-Tree local visual preference only. No Ollama/Hermes transport
    // consumes this setting while the trusted Forest host is disconnected.
    property var selectedTreeReasoningSteps: [0, 0, 0, 0, 0]
    readonly property int selectedReasoningStep:
        selectedTreeReasoningSteps[selectedTreeIndex] || 0
    function chooseTreeReasoningStep(step) {
        if (!Number.isInteger(step) || step < 0 || step > 3)
            return;
        const steps = selectedTreeReasoningSteps.slice();
        steps[selectedTreeIndex] = step;
        selectedTreeReasoningSteps = steps;
    }
    property bool modelPopupOpen: false
    property string pendingModelScan: ""
    property string lastScannedModel: ""
    property string lastModelScanResult: ""
    readonly property string selectedLocalModel: {
        const desired = String(selectedTreeModels[selectedTreeIndex] || "");
        if (!desired || localInventory.status !== "REACHABLE")
            return "";
        for (let i = 0; i < localInventory.models.length; i++) {
            if (localInventory.models[i].name === desired)
                return desired;
        }
        return "";
    }

    function chooseLocalModel(name) {
        if (localInventory.status !== "REACHABLE" || localInventory.scanning)
            return false;
        for (let i = 0; i < localInventory.models.length; i++) {
            if (localInventory.models[i].name === name) {
                const choices = selectedTreeModels.slice();
                choices[selectedTreeIndex] = name;
                selectedTreeModels = choices;
                return true;
            }
        }
        return false;
    }
    function scanModel(name) {
        if (!menuOpen || !modelPopupOpen || !name || localInventory.scanning)
            return false;
        if (!localInventory.scanModels())
            return false;
        pendingModelScan = name;
        lastScannedModel = "";
        lastModelScanResult = "";
        return true;
    }
    onSelectedTreeIndexChanged: modelPopupOpen = false
    // An actual operator popup-open gesture explicitly authorizes one B0
    // read-only inventory refresh. Reopening refreshes, but merely opening
    // Forest or loading this QML component never scans automatically.
    onModelPopupOpenChanged: {
        if (modelPopupOpen) {
            pendingModelScan = "";
            lastScannedModel = "";
            lastModelScanResult = "";
            if (!localInventory.scanning)
                localInventory.scanModels();
        }
    }
    onMenuOpenChanged: {
        if (!menuOpen) {
            modelPopupOpen = false;
            // Local-only drafts never outlive the displayed Forest session.
            if (forestPromptInput)
                forestPromptInput.clear();
        }
    }
    ForestInventoryAdapter {
        id: localInventory
        // A row SCAN is a B0 inventory refresh, NOT a probe of inference,
        // running status, resource readiness or permissions.
        onScanningChanged: {
            if (scanning || !root.pendingModelScan)
                return;
            const requested = root.pendingModelScan;
            let found = false;
            if (status === "REACHABLE") {
                for (let i = 0; i < models.length; i++) {
                    if (models[i].name === requested) {
                        found = true;
                        break;
                    }
                }
            }
            root.lastScannedModel = requested;
            root.lastModelScanResult = status === "REACHABLE"
                ? (found ? "DISCOVERED" : "NOT FOUND")
                : "NOT CONNECTED";
            root.pendingModelScan = "";
        }
    }
    // Tree names are presentation identities independent of trusted models.
    // Preserve the approved 48px artwork: Cherry/Maple vectors; Cedar and
    // Macintosh vectors; Bristlecone's operator-edited 48px pixel artwork.
    // Tree roles are operator-assigned presentation labels, not new host permissions.
    readonly property var treeSlots: [
        {
            name: "CHERRY", role: "GENERAL // ASSISTANT",
            iconPath: "../assets/forest/cherry-outline.svg",
            hoverIconPath: "../assets/forest/cherry-hover-orange.svg",
            openIconPath: "../assets/forest/cherry-open-magenta.svg",
            identityColor: Colors.white,
            iconIdleGlowColor: Colors.magenta, spiritualIdleGlowColor: Colors.magenta,
            gradientAccentColor: "#EE76B2", gradientTopRight: false
        },
        {
            name: "MAPLE", role: "FILES // ORGANIZATION",
            iconPath: "../assets/forest/maple-outline.svg",
            hoverIconPath: "../assets/forest/maple-hover-orange.svg",
            openIconPath: "../assets/forest/maple-open-magenta.svg",
            identityColor: Colors.orange,
            iconIdleGlowColor: Colors.red, spiritualIdleGlowColor: Colors.red,
            // Red in the upper-left, fading toward orange on the right.
            gradientAccentColor: "#C7482F", gradientTopRight: false
        },
        {
            name: "BRISTLECONE PINE", role: "TREEWRITE // CODER",
            iconPath: "../assets/forest/bristlecone-pine.png",
            hoverIconPath: "../assets/forest/bristlecone-hover-orange.png",
            openIconPath: "../assets/forest/bristlecone-open-magenta.png",
            identityColor: Colors.white,
            iconIdleGlowColor: Colors.orange, spiritualIdleGlowColor: Colors.green,
            gradientAccentColor: Colors.green, gradientTopRight: false
        },
        {
            name: "CEDAR", role: "SECURITY // PROTECTION",
            iconPath: "../assets/forest/cedar-outline.svg",
            hoverIconPath: "../assets/forest/cedar-hover-orange.svg",
            openIconPath: "../assets/forest/cedar-open-magenta.svg",
            identityColor: Colors.green,
            iconIdleGlowColor: Colors.orange, spiritualIdleGlowColor: Colors.orange,
            gradientAccentColor: Colors.orange, gradientTopRight: false
        },
        {
            name: "MACINTOSH", role: "TECH // SUPPORT",
            iconPath: "../assets/forest/macintosh-outline.svg",
            hoverIconPath: "../assets/forest/macintosh-hover-orange.svg",
            openIconPath: "../assets/forest/macintosh-open-magenta.svg",
            identityColor: Colors.green,
            iconIdleGlowColor: Colors.red, spiritualIdleGlowColor: Colors.red,
            gradientAccentColor: Colors.red, gradientTopRight: false
        }
    ]
    readonly property var activeTree: treeSlots[selectedTreeIndex]
    // Resolve the actually selected DockButton once so the chat heading
    // follows the Tree name's real foreground/content-glow state.
    // Repeater.count makes delegate creation reactive at initial startup.
    readonly property var selectedTreeButton:
        treeSelectorRepeater.count > selectedTreeIndex
        ? treeSelectorRepeater.itemAt(selectedTreeIndex) : null
    readonly property int glowGutter: 12
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 8
    // Git fullscreen is bounded to screen width minus its two 14px
    // gutters and its measured notification boundary minus 9px.
    // The reference stays read-only; Forest never changes Git sizing.
    readonly property int gitFullscreenWidthCap: gitFullscreenReference
        ? Math.max(1, (gitFullscreenReference.screen
                        ? gitFullscreenReference.screen.width : 1366)
                      - 2 * gitFullscreenReference.glowGutter)
        : Math.max(1, (root.screen ? root.screen.width : 1366) - 28)
    readonly property int gitFullscreenHeightCap: gitFullscreenReference
        ? Math.max(1, gitFullscreenReference.visualBottomY
                      - gitFullscreenReference.panelTopMargin
                      - gitFullscreenReference.topGlowGutter)
        : Math.max(1, (root.screen ? root.screen.height : 768) - 22)
    readonly property var chassisFrame: ForestSizing.frame(
        chassisLevel, root.screen ? root.screen.width : 1366,
        root.screen ? root.screen.height : 768,
        glowGutter, frameTopInset, bottomScreenGap,
        gitFullscreenWidthCap, gitFullscreenHeightCap)
    readonly property int frameWidth: chassisFrame.width
    readonly property int frameHeight: chassisFrame.height
    readonly property int sideWidth:
        Math.min(204, Math.max(144, Math.round(frameWidth * 0.31)))
    // Social-style chat list rail sits between Trees and live chat. On
    // narrow screens leave the locked chat/composer a usable minimum width.
    readonly property int chatListWidth:
        frameWidth >= 800 ? 184 : frameWidth >= 680 ? 148 : 0

    function toggle() { menuOpen = !menuOpen; }
    function expandChassis() { chassisLevel = ForestSizing.step(chassisLevel, 1); }
    function collapseChassis() { chassisLevel = ForestSizing.step(chassisLevel, -1); }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + frameTopInset + bottomScreenGap
    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }
    margins {
        top: ForestSizing.topMargin(
            root.screen ? root.screen.height : 768, root.implicitHeight)
        left: ForestSizing.leftMargin(
            root.screen ? root.screen.width : 1366,
            root.implicitWidth, root.dockCenterX)
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        root.menuOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: root.menuOpen
    color: "transparent"
    surfaceFormat.opaque: false
    // Remain mapped: a zero-size input mask makes the closed panel inert.
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.frameTopInset
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        id: forestFrame
        anchors.fill: parent
        anchors.leftMargin: root.glowGutter
        anchors.rightMargin: root.glowGutter
        anchors.topMargin: root.frameTopInset
        anchors.bottomMargin: root.bottomScreenGap
        visible: root.menuOpen
        focus: root.menuOpen
        fillColor: Colors.black
        fillOpacity: 0.97
        borderColor: Colors.green
        borderWidth: 1
        radius: 0
        glowColor: Colors.green
        glowVisible: root.menuOpen
        Keys.onEscapePressed: function(event) {
            if (root.modelPopupOpen)
                root.modelPopupOpen = false;
            else
                root.menuOpen = false;
            event.accepted = true;
        }

        Rectangle {
            id: header
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 56
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: collapseButton.left
                anchors.rightMargin: 8
                text: "FOREST // AI WORKSPACE"
                font.pixelSize: 16
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }
            ResizeButton {
                id: collapseButton
                anchors.right: expandButton.left
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                direction: "down"
                available: root.chassisLevel > 0
                onResizeRequested: function(delta) {
                    if (delta === -1) root.collapseChassis();
                }
            }
            ResizeButton {
                id: expandButton
                anchors.right: headerStatusControls.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                direction: "up"
                available: root.chassisLevel < ForestSizing.stages.length - 1
                onResizeRequested: function(delta) {
                    if (delta === 1) root.expandChassis();
                }
            }

            // Keep Rescan and LIVE in one anchored status cluster. Unlike
            // two independent header anchors, this makes their left-to-right
            // order and fixed 7px separation explicit across all sizes.
            Item {
                id: headerStatusControls
                anchors.right: closeButton.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                width: headerRescanButton.width + 7 + liveIndicator.width
                height: 32

                // Shared ordinary reload control. One deliberate click makes
                // a read-only B0 local model inventory refresh. No chat/audio
                // host, session creation or recurring timer is activated.
                ReloadButton {
                    id: headerRescanButton
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    interactive: root.menuOpen && !localInventory.scanning
                    Accessible.name: localInventory.scanning
                        ? "Forest model inventory scan in progress"
                        : "Rescan local Ollama model inventory (read-only)"
                    onReloadRequested: {
                        if (!root.menuOpen || localInventory.scanning)
                            return;
                        root.pendingModelScan = "";
                        root.lastScannedModel = "";
                        root.lastModelScanResult = "";
                        localInventory.scanModels();
                    }
                }

                // LIVE describes only the Quickshell workspace, not Ollama
                // or Hermes connectivity. It is always RIGHT of Rescan.
                Rectangle {
                    id: liveIndicator
                    anchors.left: headerRescanButton.right
                    anchors.leftMargin: 7
                    anchors.verticalCenter: parent.verticalCenter
                    width: 60
                    height: 25
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.green
                    Accessible.name: "Forest workspace live; AI engine not connected"

                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        width: 6
                        height: 6
                        radius: 3
                        color: Colors.green
                    }
                    GohuText {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: "LIVE"
                        font.pixelSize: 11
                        color: Colors.green
                    }
                }
            }

            CloseButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                Accessible.name: "Close Forest workspace"
                onCloseRequested: root.menuOpen = false
            }
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.green
            }
        }

        Rectangle {
            id: treePane
            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: parent.left
            width: root.sideWidth
            color: "transparent"

            GohuText {
                id: treeHeading
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 13
                text: "TREES // " + String(root.treeSlots.length).padStart(2, "0")
                font.pixelSize: 12
                color: Colors.cyan
            }
            Column {
                id: treeColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: treeHeading.bottom
                anchors.topMargin: 14
                anchors.leftMargin: 9
                anchors.rightMargin: 9
                spacing: 7
                Repeater {
                    id: treeSelectorRepeater
                    model: root.treeSlots
                    DockButton {
                        id: treeRow
                        width: treeColumn.width
                        height: 59
                        open: index === root.selectedTreeIndex
                        // Three independent idle channels: identity sets the
                        // outline/name/border ink; icon glow illuminates only
                        // the image; spiritual glow illuminates name and button
                        // border/perimeter. Shared hover/open states still win.
                        readonly property color iconIdentityColor: modelData.identityColor
                        readonly property color iconIdleGlowColor: modelData.iconIdleGlowColor
                        readonly property color spiritualIdleGlowColor: modelData.spiritualIdleGlowColor
                        readonly property color resolvedIconGlowColor:
                            treeRow.open || treeRow.pressed || treeRow.hovered
                                ? treeRow.contentGlowColor : treeRow.iconIdleGlowColor
                        normalForegroundColor: iconIdentityColor
                        hoverForegroundColor: Colors.orange
                        pressedForegroundColor: Colors.magenta
                        normalDockGlowColor: spiritualIdleGlowColor
                        normalContentGlowColor: spiritualIdleGlowColor
                        // DockButton owns the two perimeter halos; separate
                        // text and icon samples avoid duplicate full-row glow.
                        contentGlowEnabled: false
                        // The original DockButton supplies fill, pointer,
                        // sampled glows and semantic state transitions. The
                        // local 1px ring is the only visible border ink.
                        // The corner accent is idle-only; energized states
                        // become solid orange or magenta like DockButton.
                        border.width: 0
                        Accessible.name: modelData.name + " Tree"
                        ForestCornerGradientBorder {
                            id: treeGradientBorder
                            anchors.fill: parent
                            baseColor: treeRow.foregroundColor
                            accentColor: treeRow.energized
                                ? treeRow.foregroundColor : modelData.gradientAccentColor
                            accentTopRight: modelData.gradientTopRight
                            z: 4
                        }
                        onLeftClicked: root.selectedTreeIndex = index

                        Item {
                            id: treeTitleRow
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.topMargin: 6
                            anchors.leftMargin: 9
                            anchors.rightMargin: 9
                            height: 26

                            Image {
                                id: treeGlyph
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                width: 26
                                height: 26
                                // Same vector silhouette in identity, hover,
                                // and open palettes: no overlay tint or font fallback.
                                source: Qt.resolvedUrl(
                                    treeRow.open || treeRow.pressed
                                    ? modelData.openIconPath
                                    : treeRow.hovered
                                      ? modelData.hoverIconPath : modelData.iconPath)
                                sourceSize: Qt.size(64, 64)
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }

                            TextHashGlow {
                                id: treeGlyphGlow
                                safeSource: treeGlyph
                                requestedVisible: root.menuOpen
                                foregroundColor: treeRow.foregroundColor
                                preferredGlowColor: treeRow.resolvedIconGlowColor
                                radius: 8
                                samples: 17
                                opacity: treeRow.contentGlowOpacity
                                z: -1
                            }

                            ForestGradientName {
                                id: treeName
                                anchors.left: treeGlyph.right
                                anchors.leftMargin: 6
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                height: 26
                                text: modelData.name
                                pixelSize: 12
                                bold: true
                                baseColor: treeRow.foregroundColor
                                accentColor: treeRow.energized
                                    ? treeRow.foregroundColor : modelData.gradientAccentColor
                                accentTopRight: modelData.gradientTopRight
                            }
                            TextHashGlow {
                                id: treeNameGlow
                                safeSource: treeName
                                requestedVisible: root.menuOpen
                                foregroundColor: treeRow.foregroundColor
                                preferredGlowColor: treeRow.contentGlowColor
                                radius: 7
                                samples: 13
                                opacity: treeRow.contentGlowOpacity
                                z: -1
                            }
                        }
                        // Role labels use the same measured, tree-specific
                        // idle gradient as the Tree name. Normal DockButton
                        // hover/open foreground replaces both colors, so
                        // selected roles stay solid magenta on yellow.
                        ForestGradientName {
                            id: treeRole
                            anchors.left: parent.left
                            anchors.leftMargin: 9
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 9
                            width: parent.width - 18
                            height: 12
                            text: modelData.role
                            pixelSize: 9
                            bold: false
                            baseColor: treeRow.foregroundColor
                            accentColor: treeRow.energized
                                ? treeRow.foregroundColor : modelData.gradientAccentColor
                            accentTopRight: modelData.gradientTopRight
                        }
                    }
                }
            }
            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 13
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 13
                text: "LEAVES // NOT CONNECTED"
                font.pixelSize: 9
                color: Colors.orange
                width: parent.width - 20
                wrapMode: Text.WordWrap
            }
            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 1
                color: Colors.green
            }
        }

        // Social ContactList's visual recipe, not its account/provider
        // implementation. This Forest-owned rail uses the same ListView +
        // NeonScrollBar family and stays empty until a trusted session host.
        ForestChatList {
            id: activeChatRail
            anchors.left: treePane.right
            anchors.top: header.bottom
            anchors.bottom: footer.top
            width: root.chatListWidth
            visible: width > 0
            hostConnected: root.chatHostTrusted
            sessions: root.activeChatSessions
        }

        Item {
            id: chatPane
            anchors.left: activeChatRail.right
            anchors.right: parent.right
            anchors.top: header.bottom
            anchors.bottom: footer.top

            Item {
                id: chatHeadingRow
                anchors.top: parent.top
                anchors.topMargin: 9
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.right: parent.right
                anchors.rightMargin: 85
                height: 27

                Item {
                    id: chatTreeIconHost
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    width: 25
                    height: 25

                    Image {
                        id: activeChatTreeIcon
                        anchors.fill: parent
                        source: Qt.resolvedUrl(root.activeTree.iconPath)
                        sourceSize: Qt.size(64, 64)
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                    TextHashGlow {
                        safeSource: activeChatTreeIcon
                        requestedVisible: root.menuOpen
                        foregroundColor: root.activeTree.identityColor
                        preferredGlowColor: root.activeTree.iconIdleGlowColor
                        radius: 8
                        samples: 17
                        opacity: 0.82
                        z: -1
                    }
                }

                // The chat title is informational, not a selected button:
                // retain the Tree's idle identity/gradient while its button
                // can be open-magenta. The accent now spans the full
                // NAME // CHAT label, including the suffix, for every Tree.
                ForestGradientName {
                    id: chatHeading
                    anchors.left: chatTreeIconHost.right
                    anchors.leftMargin: 8
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    height: 27
                    text: root.activeTree.name + " // CHAT"
                    gradientText: root.activeTree.name + " // CHAT"
                    pixelSize: 15
                    bold: true
                    baseColor: root.activeTree.identityColor
                    accentColor: root.activeTree.gradientAccentColor
                    accentTopRight: root.activeTree.gradientTopRight
                }
                // The title keeps its independent Tree Spiritual Glow; it
                // does not inherit the active selector's magenta open state.
                TextHashGlow {
                    id: chatHeadingGlow
                    safeSource: chatHeading
                    requestedVisible: root.menuOpen
                    foregroundColor: chatHeading.baseColor
                    preferredGlowColor: root.activeTree.spiritualIdleGlowColor
                    radius: 7
                    samples: 13
                    opacity: 0.82
                    z: -1
                }
            }
            GohuText {
                anchors.right: parent.right
                anchors.rightMargin: 13
                anchors.top: parent.top
                anchors.topMargin: 18
                text: "PREVIEW"
                color: Colors.orange
                font.pixelSize: 10
            }
            Rectangle {
                id: chatDivider
                anchors.top: chatHeadingRow.bottom
                anchors.topMargin: 8
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.green
            }

            // The prompt-adjacent flower button owns this selector. The popup
            // stays inside Forest's input mask and never opens another window.
            MouseArea {
                id: dismissModelPopup
                anchors.fill: parent
                visible: root.modelPopupOpen
                z: 20
                onClicked: root.modelPopupOpen = false
            }

            Rectangle {
                id: modelPopup
                visible: root.modelPopupOpen
                z: 30
                anchors.right: promptRow.right
                anchors.bottom: promptRow.top
                anchors.bottomMargin: 6
                width: Math.min(390, chatPane.width - 24)
                // Compact stages retain a scrollable list without covering
                // the Forest header or escaping the 340px viewport.
                height: Math.max(120, Math.min(360, promptRow.y - 42))
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta
                // The ListView clips its own content. Keep this outer popup
                // unclipped so the shared red CloseButton halos remain intact.
                clip: false

                Item {
                    id: popupHeader
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    height: 33

                    GohuText {
                        anchors.left: parent.left
                        anchors.leftMargin: 9
                        anchors.right: scanAllButton.left
                        anchors.rightMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                        text: "FOREST // MODELS"
                        color: Colors.magenta
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        id: scanAllButton
                        anchors.right: closeModelPopupButton.left
                        anchors.rightMargin: 5
                        anchors.verticalCenter: parent.verticalCenter
                        width: 66
                        height: 23
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                        Accessible.name: "Scan local Ollama models, read-only"
                        GohuText {
                            anchors.centerIn: parent
                            text: localInventory.scanning ? "..." : "SCAN ALL"
                            color: Colors.cyan
                            font.pixelSize: 9
                        }
                        MouseArea {
                            anchors.fill: parent
                            enabled: !localInventory.scanning
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                root.lastScannedModel = "";
                                root.lastModelScanResult = "";
                                localInventory.scanModels();
                            }
                        }
                    }
                    // Reuse the ordinary red CloseButton contract:
                    // U+00D7, red border/foreground/glow, yellow hover,
                    // 17:16 ratio, and guarded ActionButton illumination.
                    CloseButton {
                        id: closeModelPopupButton
                        anchors.right: parent.right
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        width: 24
                        Accessible.name: "Close Forest model selector"
                        onCloseRequested: root.modelPopupOpen = false
                    }
                }

                GohuText {
                    id: popupProviderStatus
                    anchors.top: popupHeader.bottom
                    anchors.left: parent.left
                    anchors.leftMargin: 9
                    anchors.right: parent.right
                    anchors.rightMargin: 9
                    height: 19
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    color: localInventory.status === "REACHABLE" ? Colors.green : Colors.orange
                    text: localInventory.scanning ? "OLLAMA // SCANNING"
                        : localInventory.status === "REACHABLE"
                            ? "OLLAMA // " + localInventory.modelCount + " DISCOVERED"
                        : localInventory.status === "NOT_CHECKED"
                            ? "OLLAMA // NOT CHECKED"
                        : "OLLAMA // NOT CONNECTED"
                }

                ListView {
                    id: modelList
                    anchors.top: popupProviderStatus.bottom
                    anchors.topMargin: 2
                    anchors.bottom: popupFoot.top
                    anchors.bottomMargin: 3
                    anchors.left: parent.left
                    anchors.leftMargin: 7
                    anchors.right: parent.right
                    anchors.rightMargin: 7
                    clip: true
                    spacing: 5
                    boundsBehavior: Flickable.StopAtBounds
                    model: localInventory.status === "REACHABLE" ? localInventory.models : []
                    delegate: Rectangle {
                        id: modelEntry
                        property string modelName: String(modelData.name || "")
                        width: modelList.width
                        height: 82
                        color: root.selectedLocalModel === modelName ? Colors.dark : Colors.black
                        border.width: 1
                        border.color: root.selectedLocalModel === modelName ? Colors.magenta : Colors.cyan

                        GohuText {
                            anchors.left: parent.left
                            anchors.leftMargin: 7
                            anchors.top: parent.top
                            anchors.topMargin: 7
                            anchors.right: selectModelButton.left
                            anchors.rightMargin: 5
                            font.pixelSize: 11
                            font.bold: root.selectedLocalModel === modelEntry.modelName
                            color: root.selectedLocalModel === modelEntry.modelName ? Colors.magenta : Colors.white
                            text: modelEntry.modelName
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            id: selectModelButton
                            anchors.right: scanModelButton.left
                            anchors.rightMargin: 4
                            anchors.top: parent.top
                            anchors.topMargin: 4
                            width: 46
                            height: 23
                            color: root.selectedLocalModel === modelEntry.modelName ? Colors.dark : Colors.black
                            border.width: 1
                            border.color: Colors.magenta
                            Accessible.name: "Select model " + modelEntry.modelName + " for current Tree"
                            GohuText {
                                anchors.centerIn: parent
                                text: root.selectedLocalModel === modelEntry.modelName ? "SET" : "USE"
                                font.pixelSize: 9
                                color: Colors.magenta
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.chooseLocalModel(modelEntry.modelName)
                            }
                        }
                        Rectangle {
                            id: scanModelButton
                            anchors.right: parent.right
                            anchors.rightMargin: 5
                            anchors.top: parent.top
                            anchors.topMargin: 4
                            width: 45
                            height: 23
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.cyan
                            Accessible.name: "Recheck Ollama inventory for " + modelEntry.modelName
                            GohuText {
                                anchors.centerIn: parent
                                text: "SCAN"
                                font.pixelSize: 9
                                color: Colors.cyan
                            }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !localInventory.scanning
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: root.scanModel(modelEntry.modelName)
                            }
                        }

                        // Three distinct evidence classes. B0 only establishes
                        // discovery. Live execution and B4 permission cannot
                        // be inferred from the installed model list.
                        Row {
                            id: modelStatusBar
                            anchors.left: parent.left
                            anchors.leftMargin: 7
                            anchors.right: parent.right
                            anchors.rightMargin: 7
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 8
                            height: 22
                            spacing: 3
                            Rectangle {
                                width: (modelStatusBar.width - 6) / 3
                                height: parent.height
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.green
                                GohuText {
                                    anchors.centerIn: parent
                                    text: "FOUND"
                                    font.pixelSize: 9
                                    color: Colors.green
                                }
                            }
                            Rectangle {
                                width: (modelStatusBar.width - 6) / 3
                                height: parent.height
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.orange
                                GohuText {
                                    anchors.centerIn: parent
                                    text: "LIVE ?"
                                    font.pixelSize: 9
                                    color: Colors.orange
                                }
                            }
                            Rectangle {
                                width: (modelStatusBar.width - 6) / 3
                                height: parent.height
                                color: Colors.dark
                                border.width: 1
                                border.color: Colors.cyan
                                GohuText {
                                    anchors.centerIn: parent
                                    text: "ACCESS ?"
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                }
                            }
                        }
                    }
                }

                GohuText {
                    visible: localInventory.modelCount === 0
                    anchors.centerIn: modelList
                    width: modelList.width - 12
                    text: localInventory.scanning ? "SCANNING INVENTORY"
                        : localInventory.status === "NOT_CHECKED" ? "PRESS SCAN ALL"
                        : localInventory.status === "REACHABLE" ? "NO MODELS FOUND"
                        : "OLLAMA NOT CONNECTED"
                    color: Colors.orange
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                }

                GohuText {
                    id: popupFoot
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 4
                    height: 17
                    color: root.lastScannedModel ? Colors.cyan : Colors.orange
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    text: root.lastScannedModel
                        ? "SCAN // " + root.lastScannedModel + " // " + root.lastModelScanResult
                        : "SCAN = INVENTORY ONLY // LIVE & ACCESS UNVERIFIED"
                }
            }
            // Compact empty-session state remains below the chat heading.
            // The selector lives in its own overlay and cannot cover the prompt.
            Item {
                id: sessionPreview
                anchors.top: chatDivider.bottom
                anchors.topMargin: 12
                anchors.bottom: promptRow.top
                anchors.bottomMargin: 8
                anchors.left: parent.left
                // Keep the session placeholder clear of the reasoning rail;
                // the rail owns a narrow vertical strip on chat's right edge.
                anchors.right: reasoningRailHost.left
                anchors.rightMargin: 8
                clip: true

                Column {
                    anchors.centerIn: parent
                    width: Math.max(120, parent.width - 30)
                    spacing: root.frameHeight >= 540 ? 8 : 4
                    GohuText {
                        width: parent.width
                        text: "NO ACTIVE SESSION"
                        color: Colors.white
                        font.pixelSize: 15
                        horizontalAlignment: Text.AlignHCenter
                    }
                    GohuText {
                        width: parent.width
                        text: localInventory.status === "REACHABLE"
                            ? "MODEL LIST READY // CHAT HOST NOT CONNECTED"
                            : "OLLAMA / HERMES ADAPTER NOT CONNECTED"
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                    GohuText {
                        // Keep explanatory detail in taller stages. This does
                        // not hide any active chat or personal conversation.
                        visible: root.frameHeight >= 540
                        width: parent.width
                        text: "B1 / B2 / B3 READY AS CONTRACTS // TRUSTED HOST NOT CONNECTED"
                        color: Colors.cyan
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
            // The established Post-Apollo IndexRail runs the full usable
            // chat height, below the green header divider and to the same
            // lower baseline as the message field and SEND. HIGH is at top
            // and NONE at bottom. This is only a local Tree preference.
            Item {
                id: reasoningRailHost
                z: 12
                enabled: root.menuOpen
                anchors.top: chatDivider.bottom
                anchors.topMargin: 7
                anchors.bottom: promptRow.bottom
                anchors.right: parent.right
                anchors.rightMargin: 7
                width: 46

                // Track geometry mirrors the shared IndexRail's own
                // 34px top / 10px bottom insets and snap-handle dimensions.
                readonly property real trackHeight:
                    Math.max(0, height - 44)
                readonly property real handleHeight:
                    Math.max(30, Math.min(58, trackHeight / 4 * 2))
                function detentCenterY(index) {
                    const travel = Math.max(0, trackHeight - handleHeight);
                    return 34 + handleHeight / 2
                        + travel * Math.max(0, Math.min(3, index)) / 3;
                }

                IndexRail {
                    id: reasoningIndexRail
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 24
                    count: 4
                    // IndexRail 0 is at top; Forest's step 3 is HIGH.
                    currentIndex: 3 - root.selectedReasoningStep
                    accentColor: Colors.cyan
                    sideLabel: "THINK"
                    enabledRail: root.menuOpen
                    Accessible.name: "Forest reasoning level"
                    Accessible.description:
                        "Local Tree preference only; not connected to inference."
                    onIndexRequested: function(index) {
                        if (root.menuOpen)
                            root.chooseTreeReasoningStep(3 - index);
                    }
                }

                Repeater {
                    model: ["HIGH", "MED", "LOW", "NONE"]
                    delegate: GohuText {
                        required property int index
                        required property string modelData
                        anchors.left: reasoningIndexRail.right
                        anchors.leftMargin: 2
                        width: reasoningRailHost.width
                               - reasoningIndexRail.width - 2
                        height: 15
                        y: reasoningRailHost.detentCenterY(index) - height / 2
                        text: modelData
                        font.pixelSize: 8
                        color: index === reasoningIndexRail.currentIndex
                               ? Colors.magenta : Colors.cyan
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Item {
                id: promptRow
                z: 40
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: reasoningRailHost.left
                anchors.rightMargin: 4
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 13
                height: 40

                // Local-only, unsubmitted draft. No provider/session/transport
                // ownership has been authorized; SEND and voice remain gated.
                Rectangle {
                    id: sendGate
                    anchors.left: parent.left
                    anchors.right: forestAskSendButton.left
                    anchors.rightMargin: 6
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    color: Colors.dark
                    // Restore the established Post-Apollo input state colors:
                    // cyan at rest (the original Forest border), orange on
                    // hover and magenta when the draft has keyboard focus.
                    // The interaction is presentational: no host activation.
                    readonly property color promptBorderColor:
                        forestPromptInput.activeFocus ? Colors.magenta
                        : promptHover.hovered ? Colors.orange : Colors.cyan
                    border.width: forestPromptInput.activeFocus ? 2 : 1
                    border.color: promptBorderColor

                    HoverHandler {
                        id: promptHover
                        enabled: root.menuOpen
                    }

                    TextInput {
                        id: forestPromptInput
                        anchors.left: parent.left
                        anchors.leftMargin: 11
                        anchors.right: voiceToTextButton.left
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        height: parent.height - 8
                        verticalAlignment: TextInput.AlignVCenter
                        enabled: root.menuOpen
                        clip: true
                        selectByMouse: true
                        font.family: "GohuFont 11 Nerd Font Mono"
                        font.pixelSize: 16
                        color: Colors.magenta
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        // Qt automatically aligns custom cursor height and
                        // position to cursorRectangle. Increasing the font
                        // enlarges its height; make its orange stroke 3px.
                        cursorDelegate: Rectangle {
                            width: 3
                            color: Colors.orange
                        }
                        Accessible.name: "Forest local draft text input"
                        Accessible.description:
                            "In-memory draft only. SEND is locked until a trusted Forest chat host is connected."
                        // Intentionally no onAccepted / transport / history.
                    }
                    GohuText {
                        anchors.left: forestPromptInput.left
                        anchors.right: forestPromptInput.right
                        anchors.verticalCenter: forestPromptInput.verticalCenter
                        height: forestPromptInput.height
                        verticalAlignment: Text.AlignVCenter
                        visible: forestPromptInput.text.length === 0
                                 && !forestPromptInput.activeFocus
                        text: root.frameHeight < 540
                            ? "SEND LOCKED // HOST NOT CONNECTED"
                            : "SEND LOCKED // B4 TRUSTED HOST NOT CONNECTED"
                        color: Colors.magenta
                        opacity: 0.74
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }

                    // Shared Hospital-derived presentation component. Reusing a
                    // button does not import or start Hospital's mic service.
                    // Disabled until a separately reviewed Forest voice host
                    // supplies recorder custody, consent and stop behavior.
                    VoiceToTextButton {
                        id: voiceToTextButton
                        anchors.right: modelPickerButton.left
                        anchors.rightMargin: 4
                        anchors.top: parent.top
                        anchors.topMargin: 4
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 4
                        width: Math.max(28, Math.min(34,
                            Math.round(sendGate.width * 0.16)))
                        idleAccent: Colors.omnitrix
                        // The talking-mouth text is centered dynamically as this
                        // button resizes. Sampling the glyph directly can leave
                        // a stale DropShadow origin when that center moves.
                        // Sample ActionButton's anchored contentHost instead:
                        // the same glyph still glows, but both source and glow
                        // keep a resize-stable (0, 0) origin in contentLayer.
                        glyphGlowEnabled: true
                        contentGlowSource: contentItem
                        backendReady: root.voiceHostTrusted
                        busy: false
                        processing: false
                        available: root.voiceHostTrusted && !processing
                        Accessible.name:
                            "VOICE LOCKED // TRUSTED FOREST AUDIO HOST NOT CONNECTED"
                        // No onToggleRequested: protected voice service unavailable.
                    }


                    // Match Forest's ordinary DockButton state grammar: green
                    // fruit identity and perimeter when idle/hovered, magenta
                    // foreground + border + glow on open, yellow selected fill.
                    // The shared control owns the hover/pressed/open transitions
                    // and its teardown-safe source-sampled artwork glow.
                    DockButton {
                        id: modelPickerButton
                        anchors.right: parent.right
                        anchors.rightMargin: 4
                        anchors.top: parent.top
                        anchors.topMargin: 4
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 4
                        width: 39
                        radius: 0
                        acceptedButtons: Qt.LeftButton
                        open: root.modelPopupOpen
                        Accessible.name: "Open Forest model selector"

                        normalForegroundColor: Colors.green
                        hoverForegroundColor: Colors.green
                        pressedForegroundColor: Colors.green
                        openForegroundColor: Colors.magenta

                        normalDockGlowColor: Colors.green
                        hoverDockGlowColor: Colors.green
                        pressedDockGlowColor: Colors.green
                        openGlowColor: Colors.magenta

                        normalContentGlowColor: Colors.green
                        hoverContentGlowColor: Colors.green
                        pressedContentGlowColor: Colors.green
                        contentGlowSource: pickerFlower
                        trackArtworkGlowLocally: true

                        // Border follows the same resolved color as flower/glow.
                        border.width: 1
                        border.color: dockGlowColor

                        // Forest dock precedent: white idle/hover ornaments,
                        // magenta together with the flower when open.
                        readonly property color pickerStarColor:
                            modelPickerButton.open ? Colors.magenta : Colors.white

                        Item {
                            id: modelPickerArt
                            anchors.centerIn: parent
                            width: 34
                            height: 30

                            GohuText {
                                id: pickerLeftStar
                                anchors.left: parent.left
                                anchors.top: parent.top
                                text: "⊹"
                                textFormat: Text.PlainText
                                font.pixelSize: 14
                                color: modelPickerButton.pickerStarColor
                            }
                            GohuText {
                                id: pickerFlower
                                anchors.centerIn: parent
                                text: "❦︎๋࣭"
                                textFormat: Text.PlainText
                                font.pixelSize: 19
                                color: modelPickerButton.foregroundColor
                            }
                            GohuText {
                                id: pickerRightStars
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                text: "⭑"
                                textFormat: Text.PlainText
                                font.pixelSize: 13
                                color: modelPickerButton.pickerStarColor
                            }
                        }
                        onLeftClicked: root.modelPopupOpen = !root.modelPopupOpen
                    }
                }

                // The shared Hospital ASK/SEND component is labeled SEND
                // in Forest. It owns presentation, never provider calls.
                AskSendButton {
                    id: forestAskSendButton
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: Math.max(54, Math.min(86,
                        Math.round(promptRow.width * 0.21)))
                    enabledAction: root.chatHostTrusted
                    recording: false
                    processing: false
                    idleAccent: Colors.green
                    recordingAccent: Colors.magenta
                    askLabel: "SEND"
                    sendLabel: "SEND"
                    allowSecondaryAction: false
                    Accessible.name:
                        "SEND LOCKED // TRUSTED FOREST CHAT HOST NOT CONNECTED"
                    // No onPrimaryRequested/onSecondaryRequested:
                    // a selected B0 model is not an authorized session.
                }

            }
        }

        Rectangle {
            id: footer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 30
            color: Colors.black
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.green
            }
            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "LOCAL FIRST // OPTIONAL LOOPBACK MODEL SCAN"
                color: Colors.cyan
                font.pixelSize: 10
            }
            GohuText {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "TOOLS OFF"
                color: Colors.orange
                font.pixelSize: 10
            }
        }
    }
}
