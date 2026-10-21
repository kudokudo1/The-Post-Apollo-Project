import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"

// FinanceW navigation scaffold only. No services, money data, or input editors.
PanelWindow {
    id: root

    property bool menuOpen: false

    // Independent navigation state; no financial services are attached.
    readonly property var mainModes: [
        { id: "budget", name: "Budget", icon: "⋆$🗓₊˚" },
        { id: "market", name: "Market", icon: "₊˚$🗠๋࣭⭑" },
        { id: "radar", name: "Radar", icon: "࣪ ˖(˓🛰₊˚⊹" },
        { id: "research", name: "Research", icon: "⋆˚🗃₊" },
        { id: "strategies", name: "Strategies", icon: "˙°⚖︎๋࣭⭑" },
        { id: "safety", name: "Safety", icon: "🛡๋࣭⭑" },
        { id: "agentic", name: "Agentic", icon: "⋆˚⚡︎๋࣭⭑" },
        { id: "later-shop", name: "Later", icon: "🛍", future: true },
        { id: "later-print", name: "Later", icon: "🖨", future: true }
    ]
    readonly property var budgetSubModes: [
        { id: "budget", name: "Budget", icon: "˗ˋˏ˖⛁⛀๋࣭⭑ˎˊ˗" },
        { id: "reports", name: "Reports", icon: "₊˚$🗠๋࣭⭑" },
        { id: "schedules", name: "Schedules", icon: "⋆$🗓₊˚" }
    ]
    property string selectedMainMode: "budget"
    property string selectedBudgetSubMode: "budget"

    function mainModeName() {
        for (let i = 0; i < mainModes.length; ++i) {
            if (mainModes[i].id === selectedMainMode)
                return mainModes[i].name;
        }
        return "Budget";
    }

    function selectMainMode(id) {
        for (let i = 0; i < mainModes.length; ++i) {
            if (mainModes[i].id === id && !mainModes[i].future) {
                selectedMainMode = id;
                return;
            }
        }
    }

    function budgetSubColor(id) {
        return id === "budget" ? Colors.omnitrix
             : id === "reports" ? Colors.white : Colors.green;
    }

    function budgetSubGlow(id) {
        return id === "schedules" ? Colors.green : Colors.omnitrix;
    }

    // Display coordinates relative to DP-5, supplied by shell.qml.
    property real dockCenterX: 0
    property real chassisTopY: 0

    // The visible chassis is exactly 9:16; gutter belongs to its glow.
    readonly property int frameWidth: 432
    readonly property int frameHeight: 768
    readonly property int glowGutter: 12

    function toggle() {
        menuOpen = !menuOpen;
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + glowGutter * 2

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    // Clamp the panel to its screen if the dock layout becomes wider.
    margins {
        // Match Hospital/Git's visible frame top, not the Finance dock bottom.
        top: Math.max(0, Math.round(root.chassisTopY - root.glowGutter))
        left: Math.max(0, Math.min(
            Math.max(0, root.screen ? root.screen.width - root.implicitWidth : 0),
            Math.round(root.dockCenterX - root.implicitWidth / 2)
        ))
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay

    // Blank chassis has no text editor or keyboard shortcuts. Never steal
    // focus from Hospital, Git, or the terminal just to display it.
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    focusable: false

    color: "transparent"
    surfaceFormat.opaque: false

    // Map once: repeated show/hide of layer-shell windows previously caused
    // native crashes. A zero-size input mask makes the closed panel inert.
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.glowGutter
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        id: financeFrame
        anchors.fill: parent
        anchors.margins: root.glowGutter
        visible: root.menuOpen

        fillColor: Colors.black
        fillOpacity: 0.95
        borderColor: Colors.omnitrix
        borderWidth: 1
        radius: 0

        glowVisible: root.menuOpen
        glowColor: Colors.omnitrix

        // Header stays independent from the main and budget-mode rails.
        Rectangle {
            id: financeHeader
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 56
            color: Colors.dark

            Rectangle {
                anchors.fill: parent
                color: Colors.magenta
                opacity: 0.20
            }

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: closeButton.left
                anchors.rightMargin: 8
                text: "FINANCEW // " + root.mainModeName().toUpperCase()
                font.pixelSize: 17
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }

            ActionButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 34
                height: 32
                label: "×"
                labelPixelSize: 22
                contentPadding: 4
                accentColor: Colors.red
                destructive: true
                onLeftClicked: root.menuOpen = false
            }
        }

        Rectangle {
            id: headerDivider
            anchors.top: financeHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2
            color: Colors.cyan
        }

        // MAIN MODE: nine slots fit in a permanent vertical rail.
        // The shopping/print icons are reserved and do not activate pages.
        Column {
            id: mainModeRail
            anchors.top: headerDivider.bottom
            anchors.topMargin: 10
            anchors.left: parent.left
            anchors.leftMargin: 6
            width: 102
            spacing: 5

            Repeater {
                model: root.mainModes

                ModeButton {
                    id: mainModeButton
                    required property var modelData
                    width: mainModeRail.width
                    height: 60
                    interactive: !modelData.future
                    selected: root.selectedMainMode === modelData.id
                    opacity: modelData.future ? 0.42 : 1.0
                    customArtwork: true
                    customPrimaryGlowSource: mainIcon
                    labelGlowEnabled: false
                    primaryGlowEnabled: !modelData.future
                    bordered: true

                    NotoText {
                        id: mainIcon
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 5
                        width: parent.width - 6
                        horizontalAlignment: Text.AlignHCenter
                        text: modelData.icon
                        textFormat: Text.PlainText
                        font.pixelSize: 17
                        elide: Text.ElideRight
                        color: mainModeButton.primaryColor
                    }

                    GohuText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 7
                        width: parent.width - 4
                        horizontalAlignment: Text.AlignHCenter
                        text: modelData.future ? "LATER" : modelData.name.toUpperCase()
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        color: mainModeButton.selected ? Colors.magenta : Colors.white
                    }

                    onTriggered: root.selectMainMode(modelData.id)
                }
            }
        }

        Rectangle {
            id: mainRailDivider
            anchors.left: mainModeRail.right
            anchors.leftMargin: 6
            anchors.top: headerDivider.bottom
            anchors.bottom: parent.bottom
            width: 1
            color: Colors.cyan
            opacity: 0.55
        }

        Item {
            id: workArea
            anchors.top: headerDivider.bottom
            anchors.bottom: parent.bottom
            anchors.left: mainRailDivider.right
            anchors.right: parent.right
            anchors.leftMargin: 8
            anchors.rightMargin: 8

            GohuText {
                id: sectionTitle
                anchors.top: parent.top
                anchors.topMargin: 16
                anchors.left: parent.left
                anchors.right: parent.right
                text: root.mainModeName().toUpperCase()
                font.pixelSize: 15
                font.bold: true
                color: Colors.white
                elide: Text.ElideRight
            }

            // BUDGET SUB MODES: symbol and glow colors are independent.
            Row {
                id: budgetSubRail
                visible: root.selectedMainMode === "budget"
                anchors.top: sectionTitle.bottom
                anchors.topMargin: 14
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: 5

                Repeater {
                    model: root.budgetSubModes

                    ActionButton {
                        id: budgetSubButton
                        required property var modelData
                        readonly property color identityColor:
                            root.budgetSubColor(modelData.id)
                        readonly property color identityGlow:
                            root.budgetSubGlow(modelData.id)

                        width: (budgetSubRail.width - budgetSubRail.spacing * 2) / 3
                        height: 72
                        showLabel: false
                        selected: root.selectedBudgetSubMode === modelData.id
                        accentColor: identityColor
                        idleForegroundColor: identityColor
                        hoverForegroundColor: identityColor
                        pressedForegroundColor: identityColor
                        selectedForegroundColor: identityColor
                        idleContentGlowColor: identityGlow
                        hoverContentGlowColor: identityGlow
                        pressedContentGlowColor: identityGlow
                        selectedContentGlowColor: identityGlow
                        contentGlowSource: subIcon
                        idleSoftGlowColor: identityGlow
                        hoverSoftGlowColor: identityGlow
                        pressedSoftGlowColor: identityGlow
                        selectedSoftGlowColor: identityGlow
                        idleBorderColor: identityColor
                        hoverBorderColor: identityColor
                        selectedBorderColor: identityColor

                        NotoText {
                            id: subIcon
                            anchors.top: parent.top
                            anchors.topMargin: 10
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width - 8
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.icon
                            textFormat: Text.PlainText
                            font.pixelSize: 15
                            elide: Text.ElideRight
                            color: budgetSubButton.foregroundColor
                        }

                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 9
                            width: parent.width - 6
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.name.toUpperCase()
                            font.pixelSize: 10
                            color: Colors.white
                            elide: Text.ElideRight
                        }

                        onLeftClicked: root.selectedBudgetSubMode = modelData.id
                    }
                }
            }

            Rectangle {
                id: emptyPage
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: root.selectedMainMode === "budget"
                             ? budgetSubRail.bottom : sectionTitle.bottom
                anchors.topMargin: 14
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 12
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                opacity: 0.78

                GohuText {
                    anchors.top: parent.top
                    anchors.topMargin: 16
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width - 12
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 11
                    color: Colors.white
                    text: root.selectedMainMode === "budget"
                          ? root.selectedBudgetSubMode.toUpperCase()
                          : root.mainModeName().toUpperCase()
                }
            }
        }
    }
}
