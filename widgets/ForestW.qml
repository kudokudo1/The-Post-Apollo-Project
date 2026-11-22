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
    property int selectedModelIndex: 0
    readonly property string selectedLocalModel:
        localInventory.modelCount > 0
        ? localInventory.models[Math.min(selectedModelIndex, localInventory.modelCount - 1)].name
        : ""
    function cycleLocalModel() {
        if (localInventory.modelCount > 1)
            selectedModelIndex = (selectedModelIndex + 1) % localInventory.modelCount;
    }
    ForestInventoryAdapter {
        id: localInventory
        onModelsChanged: root.selectedModelIndex = 0
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
                anchors.top: chatHeading.bottom
                anchors.topMargin: 12
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
            }

            // Real B0 read-only local inventory; a scan is never automatic.
            Rectangle {
                id: modelStrip
                anchors.top: chatHeading.bottom
                anchors.topMargin: 20
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: parent.right
                anchors.rightMargin: 12
                height: 58
                color: Colors.dark
                border.color: Colors.cyan
                border.width: 1

                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.top: parent.top
                    anchors.topMargin: 8
                    anchors.right: scanButton.left
                    anchors.rightMargin: 6
                    elide: Text.ElideRight
                    font.pixelSize: 10
                    color: localInventory.status === "REACHABLE" ? Colors.green : Colors.orange
                    text: localInventory.scanning ? "OLLAMA // SCANNING"
                         : localInventory.status === "REACHABLE"
                            ? "OLLAMA // " + localInventory.modelCount + " LOCAL"
                         : localInventory.status === "NOT_CHECKED"
                            ? "OLLAMA // NOT CHECKED" : "OLLAMA // UNAVAILABLE"
                }

                Rectangle {
                    id: scanButton
                    anchors.top: parent.top
                    anchors.topMargin: 4
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    width: 55
                    height: 24
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    GohuText {
                        anchors.centerIn: parent
                        text: localInventory.scanning ? "..." : "SCAN"
                        font.pixelSize: 10
                        color: localInventory.scanning ? Colors.orange : Colors.cyan
                    }
                    Accessible.name: "Scan local Ollama models, read-only"
                    MouseArea {
                        anchors.fill: parent
                        enabled: !localInventory.scanning
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: localInventory.scanModels()
                    }
                }

                GohuText {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    anchors.right: nextModelButton.left
                    anchors.rightMargin: 6
                    font.pixelSize: 10
                    elide: Text.ElideRight
                    color: root.selectedLocalModel ? Colors.white : Colors.cyan
                    text: root.selectedLocalModel
                        ? "MODEL // " + root.selectedLocalModel
                        : "MODEL // NONE SELECTED"
                }
                Rectangle {
                    id: nextModelButton
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 4
                    width: 55
                    height: 23
                    color: Colors.black
                    border.width: 1
                    border.color: localInventory.modelCount > 1 ? Colors.magenta : Colors.cyan
                    opacity: localInventory.modelCount > 1 ? 1.0 : 0.45
                    GohuText {
                        anchors.centerIn: parent
                        text: "NEXT >"
                        font.pixelSize: 9
                        color: Colors.magenta
                    }
                    Accessible.name: "Select next inventoried local model"
                    MouseArea {
                        anchors.fill: parent
                        enabled: localInventory.modelCount > 1
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: root.cycleLocalModel()
                    }
                }
            }
            // Keep this panel strictly between model inventory and send gate.
            // The previous free-positioned Column could overlap the gate on
            // compact 340px chassis stages when wrapped text grew taller.
            Item {
                id: sessionPreview
                anchors.top: modelStrip.bottom
                anchors.topMargin: 8
                anchors.bottom: sendGate.top
                anchors.bottomMargin: 6
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
            Rectangle {
                id: sendGate
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 13
                height: 40
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
