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
    property real dockCenterX: 0
    // Read-only reference solely for Git's fullscreen size cap.
    property var gitFullscreenReference: null
    property int chassisLevel: 0
    property int selectedTreeIndex: 0
    // One explicit model choice per Tree. Inventory refreshes never silently
    // switch either Tree to the first returned model.
    property var selectedTreeModels: ["", ""]
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
        if (!menuOpen)
            modelPopupOpen = false;
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
    // Tree identities remain model-independent; outline icons are local SVG
    // assets in Post-Apollo's fixed palette, not emoji font fallbacks.
    readonly property var treeSlots: [
        {
            name: "CHERRY", role: "GENERAL COORDINATOR",
            iconPath: "../assets/forest/cherry-outline.svg",
            hoverIconPath: "../assets/forest/cherry-hover-orange.svg",
            openIconPath: "../assets/forest/cherry-open-magenta.svg"
        },
        {
            name: "MAPLE", role: "FILES & ORGANIZATION",
            iconPath: "../assets/forest/maple-outline.svg",
            hoverIconPath: "../assets/forest/maple-outline.svg",
            openIconPath: "../assets/forest/maple-open-magenta.svg"
        }
    ]
    readonly property var activeTree: treeSlots[selectedTreeIndex]
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
                anchors.right: liveIndicator.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                direction: "up"
                available: root.chassisLevel < ForestSizing.stages.length - 1
                onResizeRequested: function(delta) {
                    if (delta === 1) root.expandChassis();
                }
            }

            // LIVE is the Quickshell workspace state, not AI connectivity.
            // Ollama/Hermes still say NOT CONNECTED in the chat body.
            Rectangle {
                id: liveIndicator
                anchors.right: closeButton.left
                anchors.rightMargin: 7
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
                color: Colors.cyan
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
                text: "TREES // 02"
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
                    model: root.treeSlots
                    Rectangle {
                        id: treeRow
                        width: treeColumn.width
                        height: 59
                        color: index === root.selectedTreeIndex ? Colors.dark : Colors.black
                        border.width: 1
                        border.color: index === root.selectedTreeIndex ? Colors.magenta : Colors.cyan
                        // Hollow line artwork uses the same independent QML
                        // layout as CameraGlyph, with an SVG Image as source.
                        // Keep selected-state emphasis on text/border, not
                        // recoloring Maple into Cherry's magenta.
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
                                source: Qt.resolvedUrl(modelData.iconPath)
                                sourceSize: Qt.size(64, 64)
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                            }

                            // The actual Image remains the foreground source. Sample it
                            // from a sibling so the glow tracks its exact coordinates
                            // and disconnects safely when the QML window goes away.
                            TextHashGlow {
                                id: treeGlyphGlow
                                safeSource: treeGlyph
                                requestedVisible: root.menuOpen
                                foregroundColor: modelData.name === "CHERRY" ? Colors.white : Colors.orange
                                preferredGlowColor: modelData.name === "CHERRY" ? Colors.magenta : Colors.red
                                radius: 8
                                samples: 17
                                opacity: 0.82
                                z: -1
                            }

                            GohuText {
                                anchors.left: treeGlyph.right
                                anchors.leftMargin: 6
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.name
                                font.pixelSize: 12
                                font.bold: true
                                elide: Text.ElideRight
                                color: index === root.selectedTreeIndex ? Colors.magenta : Colors.white
                            }
                        }
                        GohuText {
                            anchors.left: parent.left
                            anchors.leftMargin: 9
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 9
                            width: parent.width - 18
                            elide: Text.ElideRight
                            text: modelData.role
                            font.pixelSize: 9
                            color: Colors.cyan
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedTreeIndex = index
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
                color: Colors.cyan
            }
        }

        Item {
            id: chatPane
            anchors.left: treePane.right
            anchors.right: parent.right
            anchors.top: header.bottom
            anchors.bottom: footer.top

            GohuText {
                id: chatHeading
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.topMargin: 14
                text: root.activeTree.name + " // CHAT"
                color: Colors.magenta
                font.pixelSize: 15
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
                anchors.top: chatHeading.bottom
                anchors.topMargin: 12
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
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
                anchors.right: parent.right
                clip: true

                Column {
                    anchors.centerIn: parent
                    width: Math.max(120, parent.width - 30)
                    spacing: root.chassisLevel >= 2 ? 8 : 4
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
                        visible: root.chassisLevel >= 2
                        width: parent.width
                        text: "B1 / B2 / B3 READY AS CONTRACTS // TRUSTED HOST NOT CONNECTED"
                        color: Colors.cyan
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
            Item {
                id: promptRow
                z: 40
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 13
                height: 40

                // A disabled prompt placeholder; the B1-B4 trusted session
                // host has not been connected, so no editable draft or SEND.
                Rectangle {
                    id: sendGate
                    anchors.left: parent.left
                    anchors.right: voiceToTextButton.left
                    anchors.rightMargin: 6
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    opacity: 0.65
                    GohuText {
                        anchors.centerIn: parent
                        width: Math.max(0, parent.width - 12)
                        text: root.chassisLevel < 2
                            ? "SEND LOCKED // HOST NOT CONNECTED"
                            : "SEND LOCKED // B4 TRUSTED HOST NOT CONNECTED"
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                // Shared Hospital-derived presentation component. Reusing a
                // button does not import or start Hospital's mic service.
                // Disabled until a separately reviewed Forest voice host
                // supplies recorder custody, consent and stop behavior.
                VoiceToTextButton {
                    id: voiceToTextButton
                    anchors.right: forestAskSendButton.left
                    anchors.rightMargin: 6
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: Math.max(32, Math.min(42,
                        Math.round(promptRow.width * 0.12)))
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

                // The same ASK/SEND component used by Hospital Reception and
                // Intercom. It owns visual states only, never provider calls.
                AskSendButton {
                    id: forestAskSendButton
                    anchors.right: modelPickerButton.left
                    anchors.rightMargin: 6
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: Math.max(54, Math.min(86,
                        Math.round(promptRow.width * 0.21)))
                    enabledAction: root.chatHostTrusted
                    recording: false
                    processing: false
                    idleAccent: Colors.green
                    recordingAccent: Colors.magenta
                    askLabel: "ASK"
                    sendLabel: "SEND"
                    allowSecondaryAction: false
                    Accessible.name:
                        "ASK LOCKED // TRUSTED FOREST CHAT HOST NOT CONNECTED"
                    // No onPrimaryRequested/onSecondaryRequested:
                    // a selected B0 model is not an authorized session.
                }

                // Match Forest's ordinary DockButton state grammar: green
                // fruit identity and perimeter when idle/hovered, magenta
                // foreground + border + glow on open, yellow selected fill.
                // The shared control owns the hover/pressed/open transitions
                // and its teardown-safe source-sampled artwork glow.
                DockButton {
                    id: modelPickerButton
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 51
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
                        width: 46
                        height: 36

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
                            font.pixelSize: 21
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
                color: Colors.cyan
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
