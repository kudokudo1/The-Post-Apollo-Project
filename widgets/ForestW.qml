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
    property real dockCenterX: 0
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
        { name: "CHERRY", role: "GENERAL COORDINATOR", iconPath: "../assets/forest/cherry-outline.svg" },
        { name: "MAPLE", role: "FILES & ORGANIZATION", iconPath: "../assets/forest/maple-outline.svg" }
    ]
    readonly property var activeTree: treeSlots[selectedTreeIndex]
    readonly property int glowGutter: 12
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 8
    readonly property var chassisFrame: ForestSizing.frame(
        chassisLevel, root.screen ? root.screen.width : 1366,
        root.screen ? root.screen.height : 768,
        glowGutter, frameTopInset, bottomScreenGap)
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
        borderColor: Colors.cyan
        borderWidth: 1
        radius: 0
        glowColor: Colors.magenta
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
                available: root.chassisLevel < 3
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
                clip: true

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
                    Rectangle {
                        id: closeModelPopupButton
                        anchors.right: parent.right
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        width: 22
                        height: 23
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta
                        Accessible.name: "Close Forest model selector"
                        GohuText {
                            anchors.centerIn: parent
                            text: "×"
                            color: Colors.magenta
                            font.pixelSize: 14
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.modelPopupOpen = false
                        }
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

                // Remains a non-editable preview until a trusted host exists.
                Rectangle {
                    id: sendGate
                    anchors.left: parent.left
                    anchors.right: modelPickerButton.left
                    anchors.rightMargin: 6
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    opacity: 0.65
                    GohuText {
                        anchors.centerIn: parent
                        width: parent.width - 12
                        text: root.chassisLevel < 2
                            ? "SEND LOCKED // HOST NOT CONNECTED"
                            : "SEND LOCKED // B4 TRUSTED HOST NOT CONNECTED"
                        color: Colors.white
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                Rectangle {
                    id: modelPickerButton
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 51
                    color: root.modelPopupOpen ? Colors.yellow : Colors.black
                    border.width: 1
                    border.color: Colors.magenta
                    Accessible.name: "Open Forest model selector"

                    GohuText {
                        id: modelPickerGlyph
                        anchors.centerIn: parent
                        width: parent.width - 4
                        text: "⊹❦︎๋࣭⭑"
                        textFormat: Text.PlainText
                        font.pixelSize: 16
                        color: Colors.magenta
                        horizontalAlignment: Text.AlignHCenter
                    }
                    TextHashGlow {
                        safeSource: modelPickerGlyph
                        requestedVisible: root.menuOpen
                        foregroundColor: Colors.magenta
                        preferredGlowColor: Colors.magenta
                        radius: 8
                        samples: 17
                        opacity: 0.75
                        z: -1
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.modelPopupOpen = !root.modelPopupOpen
                    }
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
