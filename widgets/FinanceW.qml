import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"

// FinanceW navigation scaffold only. No services, money data, or input editors.
PanelWindow {
    id: root

    property bool menuOpen: false
    property bool keyboardActive: false
    property bool keyboardLock: false
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false
    signal keyboardOwnershipRequested()

    // Independent navigation state; no financial services are attached.
    readonly property var mainModes: [
        { id: "budget", name: "Budget", icon: "⋆$🗓₊˚" },
        { id: "market", name: "Market", icon: "₊˚$🗠๋࣭⭑", prefix: "₊˚", core: "$🗠๋࣭", suffix: "⭑" },
        { id: "radar", name: "Radar", icon: "࣪ ˖(˓🛰₊˚⊹", prefix: "࣪ ˖(˓", core: "🛰", suffix: "₊˚⊹" },
        { id: "research", name: "Research", icon: "⋆˚🗃₊" },
        { id: "strategies", name: "Strategies", icon: "˙°⚖︎๋࣭⭑", prefix: "˙°", core: "⚖︎๋࣭", suffix: "⭑" },
        { id: "safety", name: "Safety", icon: "🛡๋࣭⭑", prefix: "", core: "🛡๋࣭", suffix: "⭑" },
        { id: "agentic", name: "Agentic", icon: "⋆˚⚡︎๋࣭⭑", prefix: "⋆˚", core: "⚡︎๋࣭", suffix: "⭑" },
        { id: "later-shop", name: "Later", icon: "🛍", future: true },
        { id: "later-print", name: "Later", icon: "🖨", future: true }
    ]
    readonly property var budgetSubModes: [
        { id: "budget", name: "Budget", icon: "˗ˋˏ˖⛁⛀๋࣭⭑ˎˊ˗", prefix: "˗ˋˏ˖", core: "⛁⛀๋࣭", suffix: "⭑ˎˊ˗" },
        { id: "reports", name: "Reports", icon: "₊˚$🗠๋࣭⭑", prefix: "₊˚", core: "$🗠๋࣭", suffix: "⭑" },
        { id: "schedules", name: "Schedules", icon: "⋆$🗓₊˚" }
    ]
    property string selectedMainMode: "budget"
    property string selectedBudgetSubMode: "budget"


    // Keyboard follows the shared Post-Apollo control grammar. The two
    // future slots never enter the keyboard selection cycle.
    property string navigationZone: "main"
    property int navigationIndex: 0
    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive

    function activeMainModes() {
        return mainModes.filter(function(mode) { return !mode.future; });
    }

    function cycleMainMode(direction) {
        const modes = activeMainModes();
        const at = Math.max(0, modes.findIndex(function(mode) {
            return mode.id === selectedMainMode;
        }));
        const step = Number(direction) < 0 ? -1 : 1;
        const next = (at + step + modes.length) % modes.length;
        selectMainMode(modes[next].id);
        navigationZone = "main";
        navigationIndex = next;
    }

    function cycleBudgetSubMode(direction) {
        if (selectedMainMode !== "budget")
            return;
        const at = Math.max(0, budgetSubModes.findIndex(function(mode) {
            return mode.id === selectedBudgetSubMode;
        }));
        const step = Number(direction) < 0 ? -1 : 1;
        navigationIndex = (at + step + budgetSubModes.length)
                          % budgetSubModes.length;
        navigationZone = "sub";
        selectedBudgetSubMode = budgetSubModes[navigationIndex].id;
    }

    function moveNavigationCursor(direction) {
        const count = navigationZone === "sub" && selectedMainMode === "budget"
                      ? budgetSubModes.length : activeMainModes().length;
        const step = Number(direction) < 0 ? -1 : 1;
        navigationIndex = (navigationIndex + step + count) % count;
    }

    function moveNavigationZone(direction) {
        if (selectedMainMode !== "budget")
            return;
        if (Number(direction) > 0) {
            if (navigationZone === "sub")
                return;
            navigationZone = "sub";
            navigationIndex = Math.max(0, budgetSubModes.findIndex(
                function(mode) { return mode.id === selectedBudgetSubMode; }
            ));
        } else {
            if (navigationZone === "main")
                return;
            navigationZone = "main";
            navigationIndex = Math.max(0, activeMainModes().findIndex(
                function(mode) { return mode.id === selectedMainMode; }
            ));
        }
    }

    function activateNavigationCursor() {
        if (navigationZone === "sub" && selectedMainMode === "budget")
            selectedBudgetSubMode = budgetSubModes[navigationIndex].id;
        else {
            const modes = activeMainModes();
            selectMainMode(modes[navigationIndex].id);
        }
    }

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

    onMenuOpenChanged: {
        if (menuOpen && keyboardActive)
            Qt.callLater(function() { financeKeyboardAnchor.forceActiveFocus(); });
    }
    onKeyboardActiveChanged: {
        if (menuOpen && keyboardActive)
            Qt.callLater(function() { financeKeyboardAnchor.forceActiveFocus(); });
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

    // Only the current shared owner can receive keys. A bounded acquisition
    // pulse is used at open/pointer entry; never hold Exclusive indefinitely.
    WlrLayershell.keyboardFocus:
        !root.menuOpen || !root.keyboardActive
        ? WlrKeyboardFocus.None
        : root.keyboardLock
        ? WlrKeyboardFocus.Exclusive
        : WlrKeyboardFocus.OnDemand
    focusable: root.menuOpen && root.keyboardActive

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


    Item {
        id: financeKeyboardAnchor
        anchors.fill: parent
        enabled: root.standardKeysAvailable
        focus: root.standardKeysAvailable
        z: -1000

        // Qt can consume Tab as focus-chain navigation before Shortcut.
        Keys.priority: Keys.BeforeItem
        Keys.onShortcutOverride: function(event) {
            if (!root.standardKeysAvailable)
                return;
            if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab
                    || event.key === Qt.Key_Escape)
                event.accepted = true;
        }
        Keys.onPressed: function(event) {
            if (!root.standardKeysAvailable)
                return;
            if (event.key === Qt.Key_Escape) {
                root.menuOpen = false;
                event.accepted = true;
            } else if (event.key === Qt.Key_Tab
                       || event.key === Qt.Key_Backtab) {
                const reverse = event.key === Qt.Key_Backtab
                    || (event.modifiers & Qt.ShiftModifier) !== 0;
                root.cycleMainMode(reverse ? -1 : 1);
                event.accepted = true;
            }
        }
    }

    Shortcut {
        sequence: "Tab"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.cycleMainMode(1)
    }
    Shortcut {
        sequence: "Shift+Tab"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.cycleMainMode(-1)
    }
    Shortcut {
        sequence: "Shift+Left"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.cycleBudgetSubMode(-1)
    }
    Shortcut {
        sequence: "Shift+Right"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.cycleBudgetSubMode(1)
    }
    Shortcut {
        sequence: "Up"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.moveNavigationCursor(-1)
    }
    Shortcut {
        sequence: "Down"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.moveNavigationCursor(1)
    }
    Shortcut {
        sequence: "Left"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.moveNavigationZone(-1)
    }
    Shortcut {
        sequence: "Right"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.moveNavigationZone(1)
    }
    Shortcut {
        sequence: "Return"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.activateNavigationCursor()
    }
    Shortcut {
        sequence: "Enter"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.activateNavigationCursor()
    }
    Shortcut {
        sequence: "Esc"
        context: Qt.WindowShortcut
        enabled: root.standardKeysAvailable
        onActivated: root.menuOpen = false
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

        HoverHandler {
            enabled: root.menuOpen
            onHoveredChanged: {
                if (hovered)
                    root.keyboardOwnershipRequested();
            }
        }

        // Header stays independent from the main and budget-mode rails.
        Rectangle {
            id: financeHeader
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 56
            // Same actual surface as FinanceW, without an extra tint.
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: closeButton.left
                anchors.rightMargin: 8
                text: "FINANCE // " + root.mainModeName().toUpperCase()
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
            anchors.leftMargin: 12
            anchors.right: parent.right
            anchors.rightMargin: 12
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
                    required property int index
                    width: mainModeRail.width
                    height: 60
                    interactive: !modelData.future
                    selected: root.selectedMainMode === modelData.id
                    keyboardActive: root.standardKeysAvailable
                    keyboardSelected: root.navigationZone === "main"
                                      && root.navigationIndex === index
                    opacity: modelData.future ? 0.42 : 1.0
                    customArtwork: true
                    customPrimaryGlowSource: mainIcon
                    labelGlowEnabled: false
                    primaryGlowEnabled: !modelData.future
                    bordered: true

                    Item {
                        id: mainIcon
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 5
                        width: parent.width - 6
                        height: 31

                        GohuText {
                            anchors.centerIn: parent
                            visible: !modelData.core
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData.icon
                            textFormat: Text.PlainText
                            font.pixelSize: 24
                            fontSizeMode: Text.Fit
                            minimumPixelSize: 15
                            color: mainModeButton.primaryColor
                        }

                        // The ornaments stay small while the meaningful
                        // central glyph grows; marks stay attached to core.
                        Row {
                            id: mainGlyphParts
                            anchors.centerIn: parent
                            visible: !!modelData.core
                            spacing: 0
                            scale: Math.min(1, mainIcon.width
                                            / Math.max(1, implicitWidth))

                            GohuText {
                                text: modelData.prefix || ""
                                font.pixelSize: 15
                                color: mainModeButton.primaryColor
                            }
                            GohuText {
                                text: modelData.core || ""
                                font.pixelSize: 34
                                color: mainModeButton.primaryColor
                            }
                            GohuText {
                                text: modelData.suffix || ""
                                font.pixelSize: 15
                                color: mainModeButton.primaryColor
                            }
                        }
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
                        opacity: mainModeButton.selected ? 0.60 : 0.36
                    }

                    onTriggered: {
                        root.selectMainMode(modelData.id);
                        root.navigationZone = "main";
                        root.navigationIndex = index;
                        root.keyboardOwnershipRequested();
                    }
                }
            }
        }

        Rectangle {
            id: mainRailDivider
            anchors.left: mainModeRail.right
            anchors.leftMargin: 6
            anchors.top: headerDivider.bottom
            anchors.bottom: parent.bottom
            width: 2
            color: Colors.omnitrix
            opacity: 1.0
        }

        // Separate sampled glow preserves the line's color and geometry.
        SafeDropShadow {
            id: mainRailDividerGlow
            anchors.fill: mainRailDivider
            safeSource: mainRailDivider
            requestedVisible: root.menuOpen
            horizontalOffset: 0
            verticalOffset: 0
            radius: 10
            samples: 21
            color: Colors.omnitrix
            opacity: 0.70
            transparentBorder: true
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
                        required property int index
                        readonly property color identityColor:
                            root.budgetSubColor(modelData.id)
                        readonly property color identityGlow:
                            root.budgetSubGlow(modelData.id)

                        width: (budgetSubRail.width - budgetSubRail.spacing * 2) / 3
                        height: 72
                        showLabel: false
                        selected: root.selectedBudgetSubMode === modelData.id
                        keyboardSelected: root.standardKeysAvailable
                                          && root.navigationZone === "sub"
                                          && root.navigationIndex === index
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

                        Item {
                            id: subIcon
                            anchors.top: parent.top
                            anchors.topMargin: 10
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width - 8
                            height: 35

                            GohuText {
                                anchors.centerIn: parent
                                visible: !modelData.core
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: modelData.icon
                                textFormat: Text.PlainText
                                font.pixelSize: 22
                                fontSizeMode: Text.Fit
                                minimumPixelSize: 12
                                color: budgetSubButton.foregroundColor
                            }

                            Row {
                                id: subGlyphParts
                                anchors.centerIn: parent
                                visible: !!modelData.core
                                spacing: 0
                                scale: Math.min(1, subIcon.width
                                                / Math.max(1, implicitWidth))

                                GohuText {
                                    text: modelData.prefix || ""
                                    font.pixelSize: 12
                                    color: budgetSubButton.foregroundColor
                                }
                                GohuText {
                                    text: modelData.core || ""
                                    font.pixelSize: 31
                                    color: budgetSubButton.foregroundColor
                                }
                                GohuText {
                                    text: modelData.suffix || ""
                                    font.pixelSize: 12
                                    color: budgetSubButton.foregroundColor
                                }
                            }
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

                        onLeftClicked: {
                            root.selectedBudgetSubMode = modelData.id;
                            root.navigationZone = "sub";
                            root.navigationIndex = index;
                            root.keyboardOwnershipRequested();
                        }
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
