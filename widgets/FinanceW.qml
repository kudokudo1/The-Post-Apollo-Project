import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Wayland
import "FinanceChassisPolicy.js" as FinanceChassisPolicy
import "../components"
import "../services/finance" as FinanceServices

// FinanceW navigation scaffold only. No services, money data, or input editors.
PanelWindow {
    id: root

    property bool menuOpen: false
    property bool fundingReviewOpen: false
    property bool advancedOpen: false
    property string budgetSection: "budget"
    property bool keyboardActive: false
    property bool keyboardLock: false
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false
    signal keyboardOwnershipRequested()

    FinanceServices.FinanceOpeningHistoryService {
        id: openingHistory
        sourceKey: financeBudget.snapshot ? financeBudget.snapshot.sourceKey : ""
        month: financeBudget.selectedMonth
    }

    // Public Market source is isolated from the protected Budget services.
    FinanceServices.FinanceMarketReadService {
        id: marketService
        monitoring: root.menuOpen && root.selectedMainMode === "market"
    }

    // Separate saved-crawl reader; it never executes a spider inside Quickshell.
    FinanceServices.FinanceCrawlReadService {
        id: crawlService
        monitoring: root.menuOpen && root.selectedMainMode === "research"
                    && root.researchTool === "crawl"
    }

    FinanceServices.FinanceSecReadService {
        id: secService
        monitoring: root.menuOpen && root.selectedMainMode === "research"
                    && root.researchTool === "sec"
    }

    Component {
        id: marketPaneComponent
        FinanceMarketPane {
            marketFeed: marketService
            displayLevel: root.chassisLevel
        }
    }

    FinanceServices.FinanceBudgetReadService {
        id: financeBudget
        monitoring: root.menuOpen
        onSnapshotChanged: root.fundingReviewOpen = false
    }

    FinanceServices.FinanceLocalDraftStore {
        id: financeDrafts
        sourceKey: financeBudget.snapshot ? financeBudget.snapshot.sourceKey : ""
        month: financeBudget.selectedMonth
        onDraftSaved: transactionDraftPane.clear()
    }

    FinanceServices.FinanceAllocationGateCheck {
        id: allocationGateCheck
    }

    FinanceServices.FinanceFundingWriteService {
        id: financeFundingWrite
        onSaved: {
            quickAddPane.clear();
            guidedFundingPane.clear();
            if(root.menuOpen)
                financeBudget.refresh();
        }
    }

    FinanceServices.FinanceAllocationWriteService {
        id: financeAllocationWrite
        onSaved: {
            financeBudgetGrid.reset();
            allocationPreviewPane.clear();
            if (root.menuOpen)
                financeBudget.refresh();
        }
    }

    FinanceServices.FinanceTransactionWriteService {
        id: financeWrite
        onSaved: {
            transactionDraftPane.clear();
            if (root.menuOpen)
                financeBudget.refresh();
        }
    }

    FinanceServices.FinanceCategoryWriteService {
        id: financeCategoryWrite
        onSaved: {
            financeCategoriesPane.clearDraft();
            if(root.menuOpen)
                financeBudget.refresh();
        }
    }

    readonly property bool hasBudgetFeed:
        selectedMainMode === "budget" && selectedBudgetSubMode === "budget"
    // NO FEED for reserved/unimplemented pages. LIVE means an authenticated
    // read succeeded AND the local source remains reachable.
    readonly property string feedStatus:
        selectedMainMode === "research" && researchTool === "sec"
          ? (!menuOpen ? "IDLE"
             : secService.loading ? "READING"
             : secService.state === "failed" ? "ERROR"
             : secService.state === "ready" ? "SNAPSHOT" : "NO FEED")
        : selectedMainMode === "research"
          ? (!menuOpen ? "IDLE"
             : crawlService.loading ? "READING"
             : crawlService.state === "failed" ? "ERROR"
             : crawlService.state === "ready" ? "SNAPSHOT" : "NO FEED")
        : selectedMainMode === "market"
          ? (!menuOpen ? "IDLE"
             : marketService.loading ? "READING"
             : marketService.state === "failed" ? "ERROR"
             : marketService.live ? "SNAPSHOT" : "NO FEED")
        : !hasBudgetFeed ? "NO FEED"
        : !menuOpen ? "IDLE"
        : financeBudget.healthStatus === "offline" ? "OFFLINE"
        : financeBudget.state === "failed" ? "ERROR"
        : financeBudget.loading ? "READING"
        : financeBudget.state === "ready"
          && financeBudget.snapshot
          && financeBudget.healthStatus === "online" ? "LIVE"
        : "CHECK"
    readonly property color feedStatusColor:
        feedStatus === "LIVE" ? Colors.green
        : feedStatus === "OFFLINE" || feedStatus === "ERROR" ? Colors.red
        : feedStatus === "NO FEED" ? Colors.orange
        : Colors.cyan
    // Border normally stays Omnitrix. Only genuinely unavailable source/
    // unimplemented page states inherit the interior text state.
    readonly property color feedBorderColor:
        feedStatus === "OFFLINE" || feedStatus === "ERROR"
        || feedStatus === "NO FEED" ? feedStatusColor : Colors.omnitrix

    function selectBudgetSection(section) {
        if(["budget","transactions","accounts","categories"].indexOf(section)<0)
            return false;
        // Never hide an unfinished transaction editor or an active write.
        if((transactionDraftPane.open && section!=="transactions")
                || financeWrite.state==="pending"
                || financeWrite.state==="uncertain"
                || financeCategoryWrite.state==="pending"
                || financeCategoryWrite.state==="uncertain")
            return false;
        budgetSection=section;
        budgetScroll.contentY=0;
        return true;
    }

    function accountTotalCents() {
        const data = financeBudget.snapshot;
        if (!data || !Array.isArray(data.accounts))
            return null;
        let sum = 0;
        for (let i = 0; i < data.accounts.length; ++i) {
            if (!Number.isSafeInteger(data.accounts[i].balanceCents))
                return null;
            sum += data.accounts[i].balanceCents;
            if (!Number.isSafeInteger(sum))
                return null;
        }
        return sum;
    }

    function moneyText(cents) {
        if (!Number.isSafeInteger(cents))
            return "—";
        return (cents < 0 ? "-$" : "$")
            + (Math.abs(cents) / 100).toFixed(2);
    }

    // Independent navigation state; no financial services are attached.
    readonly property var mainModes: [
        { id: "budget", name: "Budget", icon: "⋆$🗓₊˚" },
        { id: "market", name: "Market", icon: "₊˚$🗠๋࣭⭑", prefix: "₊˚", dollar: "$", core: "🗠๋࣭", suffix: "⭑" },
        { id: "radar", name: "Radar", icon: "࣪ ˖(˓🛰₊˚⊹", prefix: "࣪ ˖(˓", core: "🛰", suffix: "₊˚⊹", coreSize: 30 },
        { id: "research", name: "Research", icon: "⋆˚🗃₊" },
        { id: "strategies", name: "Strategies", icon: "˙°⚖︎๋࣭⭑", prefix: "˙°", core: "⚖︎๋࣭", suffix: "⭑", coreSize: 28 },
        { id: "safety", name: "Safety", icon: "🛡๋࣭⭑", prefix: "", core: "🛡๋࣭", suffix: "⭑", coreSize: 28 },
        { id: "agentic", name: "Agentic", icon: "⋆˚⚡︎๋࣭⭑", prefix: "⋆˚", core: "⚡︎๋࣭", suffix: "⭑" },
        { id: "later-shop", name: "Later", icon: "🛍", future: true },
        { id: "later-print", name: "Later", icon: "🖨", future: true }
    ]
    readonly property var budgetSubModes: [
        { id: "budget", name: "Budget", icon: "˗ˋˏ˖⛁⛀๋࣭⭑ˎˊ˗", prefix: "˗ˋˏ˖", core: "⛁⛀๋࣭", suffix: "⭑ˎˊ˗" },
        { id: "reports", name: "Reports", icon: "₊˚$🗠๋࣭⭑", prefix: "₊˚", dollar: "$", core: "🗠๋࣭", suffix: "⭑" },
        { id: "schedules", name: "Schedules", icon: "⋆$🗓₊˚" }
    ]
    property string selectedMainMode: "budget"
    property string researchTool: "crawl"
    property string selectedBudgetSubMode: "budget"


    // Keyboard follows the shared Post-Apollo control grammar. The two
    // future slots never enter the keyboard selection cycle.
    property string navigationZone: "main"
    property int navigationIndex: 0
    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive && !transactionDraftPane.open

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

    // The one mapped layer-shell surface resizes; editors, services and
    // navigation are not recreated on Compact / Expanded / Fullscreen changes.
    property string chassisLevel: "compact"
    readonly property int glowGutter: 12
    // All three levels share the same visible top edge (9px). Reserve
    // 8px beneath the visible frame for the operator's Sway bottom gap.
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 8
    readonly property var chassisFrame: FinanceChassisPolicy.frame(
        chassisLevel,
        root.screen ? root.screen.width : 456,
        root.screen ? root.screen.height : 768,
        glowGutter, frameTopInset, bottomScreenGap
    )
    readonly property int frameWidth: chassisFrame.width
    readonly property int frameHeight: chassisFrame.height

    function expandChassis() {
        chassisLevel = FinanceChassisPolicy.step(chassisLevel, 1);
    }
    function collapseChassis() {
        chassisLevel = FinanceChassisPolicy.step(chassisLevel, -1);
    }
    function toggle() {
        menuOpen = !menuOpen;
    }

    onMenuOpenChanged: {
        if (menuOpen) {
            // Refresh on each real closed → open transition, not shell boot.
            financeBudget.refresh();
            if (keyboardActive)
                Qt.callLater(function() { financeKeyboardAnchor.forceActiveFocus(); });
        } else {
            transactionDraftPane.clear();
        }
    }
    onKeyboardActiveChanged: {
        if (menuOpen && keyboardActive)
            Qt.callLater(function() { financeKeyboardAnchor.forceActiveFocus(); });
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + frameTopInset + bottomScreenGap

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    // Compact remains dock-centered; Expanded is screen-clamped; Fullscreen
    // fills the space between the common 9px top and 8px bottom border gaps.
    margins {
        top: FinanceChassisPolicy.topMargin(
            root.chassisLevel, root.chassisTopY,
            root.screen ? root.screen.height : root.implicitHeight,
            root.implicitHeight, root.frameTopInset)
        left: FinanceChassisPolicy.leftMargin(
            root.chassisLevel, root.dockCenterX,
            root.screen ? root.screen.width : root.implicitWidth,
            root.implicitWidth)
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
        y: root.frameTopInset
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
        anchors.topMargin: root.frameTopInset
        anchors.bottomMargin: root.bottomScreenGap
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
                anchors.right: collapseChassisButton.left
                anchors.rightMargin: 8
                text: "FINANCE // " + root.mainModeName().toUpperCase()
                font.pixelSize: 17
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }

            // Size controls stay inside FinanceW; they never open another app.
            // They only update the window geometry, not financial or edit state.
            ActionButton {
                id: collapseChassisButton
                anchors.right: expandChassisButton.left
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                width: 30
                height: 30
                label: "↓"
                labelPixelSize: 17
                accentColor: Colors.cyan
                available: root.chassisLevel !== "compact"
                onLeftClicked: {
                    root.collapseChassis();
                    root.keyboardOwnershipRequested();
                }
            }
            ActionButton {
                id: expandChassisButton
                anchors.right: financeFeedIndicator.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                width: 30
                height: 30
                label: "↑"
                labelPixelSize: 17
                accentColor: Colors.magenta
                available: root.chassisLevel !== "fullscreen"
                onLeftClicked: {
                    root.expandChassis();
                    root.keyboardOwnershipRequested();
                }
            }

            // Git/Hospital-style source badge, constrained to the header.
            // Always tells the truth for the currently selected view.
            Rectangle {
                id: financeFeedIndicator
                width: 68
                height: 26
                anchors.right: closeButton.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.dark
                border.width: 1
                border.color: root.feedBorderColor

                RectangularShadow {
                    anchors.fill: parent
                    z: -1
                    spread: 4
                    opacity: root.menuOpen ? 0.54 : 0
                    color: root.feedBorderColor
                }

                GohuText {
                    id: financeFeedText
                    anchors.centerIn: parent
                    text: root.feedStatus
                    font.pixelSize: 9
                    color: root.feedStatusColor
                    textFormat: Text.PlainText
                }
                SafeDropShadow {
                    anchors.fill: financeFeedText
                    safeSource: financeFeedText
                    requestedVisible: root.menuOpen
                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 6
                    samples: 9
                    opacity: 0.82
                    color: root.feedStatusColor
                    transparentBorder: true
                }
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
                // The shared ActionButton provides a glow without cloning
                // the × glyph through an extra DropShadow source.
                softGlowEnabled: true
                idleSoftGlowColor: Colors.red
                hoverSoftGlowColor: Colors.red
                pressedSoftGlowColor: Colors.red
                softGlowIdleOpacity: 0.48
                softGlowHoverOpacity: 0.70
                wideGlowEnabled: true
                idleWideGlowColor: Colors.red
                hoverWideGlowColor: Colors.red
                pressedWideGlowColor: Colors.red
                wideGlowIdleOpacity: 0.22
                wideGlowHoverOpacity: 0.32
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
                                // Keep small ornaments centered on the larger core glyph.
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.prefix || ""
                                font.pixelSize: 15
                                color: mainModeButton.primaryColor
                            }
                            // Match the dollar in Main Budget instead of
                            // enlarging it with the adjoining chart glyph.
                            GohuText {
                                visible: !!modelData.dollar
                                // Row aligns children at the top by default;
                                // center $ vertically against the taller chart.
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.dollar || ""
                                font.pixelSize: 24
                                color: mainModeButton.primaryColor
                            }
                            GohuText {
                                text: modelData.core || ""
                                font.pixelSize: modelData.coreSize || 34
                                color: mainModeButton.primaryColor
                            }
                            GohuText {
                                // Keep small ornaments centered on the larger core glyph.
                                anchors.verticalCenter: parent.verticalCenter
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
                                    // Keep small ornaments centered on the larger core glyph.
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.prefix || ""
                                    font.pixelSize: 12
                                    color: budgetSubButton.foregroundColor
                                }
                                // Same Gohu dollar size used by Main Budget.
                                GohuText {
                                    visible: !!modelData.dollar
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.dollar || ""
                                    font.pixelSize: 24
                                    color: budgetSubButton.foregroundColor
                                }
                                GohuText {
                                    text: modelData.core || ""
                                    font.pixelSize: 31
                                    color: budgetSubButton.foregroundColor
                                }
                                GohuText {
                                    // Keep small ornaments centered on the larger core glyph.
                                    anchors.verticalCenter: parent.verticalCenter
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

                // Read-only on open/month change or manual REFRESH.
                // Snapshots stay in process memory, never tracked on disk.
                Column {
                    id: actualBudgetPage
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 9
                    visible: root.selectedMainMode === "budget"
                             && root.selectedBudgetSubMode === "budget"

                    Row {
                        width: parent.width
                        spacing: 7

                        GohuText {
                            width: parent.width - refreshBudget.width - 7
                            height: 30
                            verticalAlignment: Text.AlignVCenter
                            text: financeBudget.state === "ready"
                                  ? (financeBudget.healthStatus === "offline"
                                     ? "ACTUAL // CACHED" : "ACTUAL // READ ONLY")
                                  : financeBudget.state === "loading"
                                  ? "ACTUAL // READING"
                                  : "ACTUAL // NOT LOADED"
                            font.pixelSize: 10
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                        ActionButton {
                            id: refreshBudget
                            width: 78
                            height: 30
                            label: financeBudget.loading ? "LOADING" : "REFRESH"
                            labelPixelSize: 10
                            accentColor: Colors.omnitrix
                            available: !financeBudget.loading
                            interactive: available && financeWrite.state !== "pending"
                            onLeftClicked: financeBudget.refresh()
                        }
                    }

                    // Month changes automatically queue a read; the previous
                    // month is hidden immediately, even during slow downloads.
                    Row {
                        id: financeMonthRail
                        width: parent.width
                        spacing: 7

                        ActionButton {
                            id: previousBudgetMonth
                            width: 40
                            height: 28
                            label: "‹"
                            labelPixelSize: 16
                            accentColor: Colors.cyan
                            interactive: financeWrite.state !== "pending"
                            onLeftClicked: financeBudget.shiftMonth(-1)
                        }
                        GohuText {
                            width: parent.width - previousBudgetMonth.width
                                   - nextBudgetMonth.width - financeMonthRail.spacing * 2
                            height: 28
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            text: financeBudget.selectedMonth
                            textFormat: Text.PlainText
                            font.pixelSize: 13
                            color: Colors.white
                        }
                        ActionButton {
                            id: nextBudgetMonth
                            width: 40
                            height: 28
                            label: "›"
                            labelPixelSize: 16
                            accentColor: Colors.cyan
                            interactive: financeWrite.state !== "pending"
                            onLeftClicked: financeBudget.shiftMonth(1)
                        }
                    }

                    GohuText {
                        visible: financeBudget.state === "ready"
                        text: "TO BUDGET "
                              + root.moneyText(financeBudget.snapshot
                                  ? financeBudget.snapshot.toBudgetCents : null)
                        font.pixelSize: 13
                        color: Colors.white
                        width: parent.width
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width
                        visible: financeBudget.state === "ready"
                                 && !!financeBudget.snapshot
                        text: financeBudget.snapshot && financeBudget.snapshot.toBudgetCents < 0
                            ? "FUNDING // TO BUDGET BELOW ZERO; REVIEW EXISTING ALLOCATIONS"
                            : financeBudget.snapshot && financeBudget.snapshot.toBudgetCents === 0
                            ? "FUNDING // NO UNALLOCATED FUNDS; REVIEW INCOME AND OPENING BALANCES IN ACTUAL"
                            : "FUNDING // UNALLOCATED FUNDS AVAILABLE FOR CATEGORY PLANNING"
                        textFormat: Text.PlainText
                        font.pixelSize: 9
                        color: financeBudget.snapshot && financeBudget.snapshot.toBudgetCents > 0
                               ? Colors.cyan : Colors.orange
                        wrapMode: Text.WordWrap
                    }

                    // Account summary comes from the same verified read-only
                    // response as the list, never an independent bank guess.
                    GohuText {
                        visible: financeBudget.state === "ready"
                        text: "ACCOUNTS "
                              + (financeBudget.snapshot
                                 ? financeBudget.snapshot.accounts.length : 0)
                              + "  /  TOTAL " + root.moneyText(root.accountTotalCents())
                        width: parent.width
                        font.pixelSize: 11
                        color: Colors.omnitrix
                        elide: Text.ElideRight
                    }

                    GohuText {
                        visible: financeBudget.state === "ready"
                                 && financeBudget.healthStatus === "offline"
                        text: "SOURCE OFFLINE // LAST READ " + financeBudget.lastReadAt
                        width: parent.width
                        font.pixelSize: 9
                        color: Colors.red
                        elide: Text.ElideRight
                    }

                    GohuText {
                        visible: financeBudget.state !== "ready"
                        text: financeBudget.message
                        textFormat: Text.PlainText
                        font.pixelSize: 11
                        color: Colors.white
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }

                    Flickable {
                        id: budgetScroll
                        width: parent.width
                        height: Math.max(0, actualBudgetPage.height - y - 4)
                        visible: financeBudget.state === "ready"
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        contentHeight: budgetList.implicitHeight

                        Column {
                            id: budgetList
                            width: budgetScroll.width
                            spacing: 7

                            Grid {
    id: budgetSectionTabs
    width: parent.width
    columns: 2
    spacing: 5
    Repeater {
        model: [
            {key:"budget",label:"BUDGET"},
            {key:"transactions",label:"TRANSACTIONS"},
            {key:"accounts",label:"ACCOUNTS"},
            {key:"categories",label:"CATEGORIES"}
        ]
        delegate: ActionButton {
            required property var modelData
            width: (budgetSectionTabs.width-5)/2
            height: 28
            label: modelData.label
            labelPixelSize: 9
            accentColor: root.budgetSection===modelData.key
                ? Colors.magenta : Colors.cyan
            trackLabelGlowLocally: true
            available: !transactionDraftPane.open
                || root.budgetSection!=="transactions"
                || modelData.key==="transactions"
            onLeftClicked: root.selectBudgetSection(modelData.key)
        }
    }
}
Column {
    id: budgetSectionContent
    width: parent.width
    spacing: 7
    visible: root.budgetSection==="budget"
ActionButton {
    id: quickAddMoney
    width: parent.width
    height: 30
    label: quickAddPane.open ? "HIDE ADD MONEY" : "+ ADD MONEY"
    labelPixelSize: 11
    accentColor: Colors.orange
    trackLabelGlowLocally: true
    available: financeBudget.state==="ready" && !!financeBudget.snapshot
        && financeFundingWrite.state!=="pending"
        && financeFundingWrite.state!=="uncertain"
    onLeftClicked: {
        if(quickAddPane.open)quickAddPane.clear();
        else quickAddPane.begin();
    }
}
FinanceQuickAddPane {
    id: quickAddPane
    width: parent.width
    snapshot: financeBudget.snapshot
    writeState: financeFundingWrite.state
    writeMessage: financeFundingWrite.message
    onSaveRequested: function(payload) {
        if(financeBudget.state==="ready" && financeBudget.snapshot
                && payload && payload.mode==="income"
                && payload.sourceKey===financeBudget.snapshot.sourceKey
                && payload.month===financeBudget.snapshot.month
                && financeFundingWrite.state!=="pending"
                && financeFundingWrite.state!=="uncertain")
            financeFundingWrite.submit(payload);
    }
}
FinanceBudgetGrid {
    id: financeBudgetGrid
    width: parent.width
    snapshot: financeBudget.snapshot
    writeState: financeAllocationWrite.state
    writeMessage: financeAllocationWrite.message
    onSaveRequested: function(payload) {
        if(financeBudget.state==="ready" && financeBudget.snapshot
                && payload
                && payload.sourceKey===financeBudget.snapshot.sourceKey
                && payload.month===financeBudget.snapshot.month
                && financeAllocationWrite.state!=="pending"
                && financeAllocationWrite.state!=="uncertain")
            financeAllocationWrite.submit(payload);
    }
}
ActionButton {
    id: advancedToggle
    width: parent.width
    height: 26
    label: root.advancedOpen ? "HIDE ADVANCED" : "ADVANCED"
    labelPixelSize: 9
    accentColor: Colors.cyan
    trackLabelGlowLocally: true
    onLeftClicked: root.advancedOpen=!root.advancedOpen
}
Column {
    width: parent.width
    spacing: 7
    visible: root.advancedOpen
ActionButton {
                                id: reviewFunding
                                width: parent.width
                                height: 28
                                trackLabelGlowLocally: true
                                label: root.fundingReviewOpen ? "HIDE FUNDING REVIEW" : "REVIEW FUNDING"
                                labelPixelSize: 10
                                accentColor: Colors.cyan
                                available: financeBudget.state === "ready"
                                           && !!financeBudget.snapshot
                                           && !!financeBudget.snapshot.funding
                                onLeftClicked: root.fundingReviewOpen = !root.fundingReviewOpen
                            }
                            Column {
                                width: parent.width
                                spacing: 5
                                visible: root.fundingReviewOpen && financeBudget.state === "ready"
                                         && !!financeBudget.snapshot
                                         && !!financeBudget.snapshot.funding
                                GohuText {
                                    width: parent.width
                                    text: "FUNDING REVIEW // " + financeBudget.selectedMonth
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                    textFormat: Text.PlainText
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: "INCOME CATEGORY ACTIVITY // "
                                          + (financeBudget.snapshot
                                             && financeBudget.snapshot.funding.incomeCategoryActivityCents !== null
                                             ? root.moneyText(financeBudget.snapshot.funding.incomeCategoryActivityCents)
                                             : "NOT REPORTED BY ACTUAL")
                                    color: Colors.white
                                    font.pixelSize: 9
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                }
                                GohuText {
                                    width: parent.width
                                    text: "MONTHLY INCOME (ACTUAL) // "
                                          + (financeBudget.snapshot
                                             && financeBudget.snapshot.funding.reportedIncomeCents !== null
                                             ? root.moneyText(financeBudget.snapshot.funding.reportedIncomeCents)
                                             : "NOT REPORTED")
                                    color: Colors.white
                                    font.pixelSize: 9
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                }
                                GohuText {
                                    width: parent.width
                                    text: "INCOME CATEGORIES // "
                                          + (financeBudget.snapshot
                                             ? financeBudget.snapshot.funding.incomeCategoryCount : 0)
                                    color: Colors.cyan
                                    font.pixelSize: 9
                                    textFormat: Text.PlainText
                                }
                                GohuText {
                                    width: parent.width
                                    text: "POSITIVE UNCATEGORIZED // "
                                          + (financeBudget.snapshot
                                             ? financeBudget.snapshot.funding.positiveUncategorizedCount : 0)
                                          + " ITEMS / "
                                          + root.moneyText(financeBudget.snapshot
                                              ? financeBudget.snapshot.funding.positiveUncategorizedCents : null)
                                    color: Colors.orange
                                    font.pixelSize: 9
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                }
                                GohuText {
                                    width: parent.width
                                    text: "REVIEW POSITIVE UNCATEGORIZED ITEMS IN ACTUAL. "
                                          + "THEY MAY BE REFUNDS OR TRANSFERS, NOT INCOME."
                                    color: Colors.orange
                                    font.pixelSize: 9
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                }
                                GohuText {
                                    width: parent.width
                                    text: "OPENING BALANCES // NOT VERIFIED FROM THIS MONTH"
                                    color: Colors.orange
                                    font.pixelSize: 9
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                }
                                ActionButton {
                                    id: guidedFundingSetup
                                    width: parent.width
                                    height: 28
                                    label: guidedFundingPane.expanded
                                           ? "HIDE FUNDING SETUP" : "GUIDED FUNDING SETUP"
                                    labelPixelSize: 9
                                    accentColor: Colors.cyan
                                    trackLabelGlowLocally: true
                                    available: financeBudget.state === "ready"
                                               && !!financeBudget.snapshot
                                    onLeftClicked: {
                                        if(guidedFundingPane.expanded)
                                            guidedFundingPane.clear();
                                        else
                                            guidedFundingPane.begin();
                                    }
                                }
                                FinanceFundingSetupPane {
                                    id: guidedFundingPane
                                    width: parent.width
                                    snapshot: financeBudget.snapshot
                                    writeState: financeFundingWrite.state
                                    writeMessage: financeFundingWrite.message
                                    onSaveRequested: function(payload) {
                                        if(financeBudget.state === "ready"
                                                && financeBudget.snapshot
                                                && payload && payload.mode === "income"
                                                && payload.sourceKey === financeBudget.snapshot.sourceKey
                                                && payload.month === financeBudget.snapshot.month
                                                && financeFundingWrite.state !== "pending"
                                                && financeFundingWrite.state !== "uncertain")
                                            financeFundingWrite.submit(payload);
                                    }
                                }
                                ActionButton {
                                    id: reviewIncoming
                                    width: parent.width
                                    height: 28
                                    label: incomeCategoryPane.expanded
                                          ? "HIDE INCOME PREVIEW" : "REVIEW INCOMING"
                                    labelPixelSize: 9
                                    accentColor: Colors.cyan
                                    trackLabelGlowLocally: true
                                    available: financeBudget.state === "ready"
                                               && !!financeBudget.snapshot
                                               && !!financeBudget.snapshot.incomeReview
                                    onLeftClicked: {
                                        if (incomeCategoryPane.expanded)
                                            incomeCategoryPane.clear();
                                        else
                                            incomeCategoryPane.openReview();
                                    }
                                }
                                FinanceIncomeCategorizationPane {
                                    id: incomeCategoryPane
                                    width: parent.width
                                    snapshot: financeBudget.snapshot
                                }
                                ActionButton {
                                    id: inspectOpeningBalances
                                    width: parent.width
                                    height: 28
                                    trackLabelGlowLocally: true
                                    label: "INSPECT OPENING BALANCES"
                                    labelPixelSize: 9
                                    accentColor: Colors.cyan
                                    available: financeBudget.state === "ready"
                                        && !!financeBudget.snapshot
                                        && openingHistory.state !== "reading"
                                    onLeftClicked: openingHistory.scan()
                                }
                                GohuText {
                                    width: parent.width
                                    text: openingHistory.message
                                    textFormat: Text.PlainText
                                    font.pixelSize: 9
                                    color: openingHistory.state === "ready"
                                        ? Colors.cyan : Colors.orange
                                    wrapMode: Text.WordWrap
                                }
                                GohuText {
                                    width: parent.width
                                    visible: openingHistory.state === "ready"
                                    text: "RECORDS INSPECTED // " + openingHistory.recordsInspected
                                    textFormat: Text.PlainText
                                    font.pixelSize: 9
                                    color: Colors.cyan
                                }
                                Repeater {
                                    model: openingHistory.state === "ready"
                                        ? openingHistory.accounts : []
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: budgetList.width
                                        height: historyColumn.implicitHeight + 12
                                        color: Colors.black
                                        border.color: Colors.cyan
                                        Column {
                                            id: historyColumn
                                            x: 6
                                            y: 6
                                            width: parent.width - 12
                                            spacing: 4
                                            GohuText {
                                                width: parent.width
                                                text: modelData.accountName
                                                textFormat: Text.PlainText
                                                font.pixelSize: 10
                                                color: Colors.white
                                                elide: Text.ElideRight
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: "FIRST RECORDED // "
                                                      + (modelData.firstRecordedDate || "NO TRANSACTIONS")
                                                textFormat: Text.PlainText
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                                wrapMode: Text.WordWrap
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: "FIRST AMOUNT // "
                                                      + root.moneyText(modelData.firstRecordedAmountCents)
                                                textFormat: Text.PlainText
                                                font.pixelSize: 9
                                                color: Colors.cyan
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: "STARTING BALANCE CANDIDATES // "
                                                      + modelData.startingBalanceCandidateCount
                                                      + " / " + root.moneyText(modelData.startingBalanceCandidateCents)
                                                textFormat: Text.PlainText
                                                font.pixelSize: 9
                                                color: Colors.orange
                                                wrapMode: Text.WordWrap
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: "NOT VERIFIED // CHECK BANK OPENING RECORD"
                                                textFormat: Text.PlainText
                                                font.pixelSize: 9
                                                color: Colors.orange
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }
                                }
                                GohuText {
                                    width: parent.width
                                    text: "ACCOUNT BALANCE IS NOT THE SAME AS TO BUDGET. "
                                          + "REVIEW STARTING BALANCES AND INCOME IN ACTUAL."
                                    color: Colors.cyan
                                    font.pixelSize: 9
                                    textFormat: Text.PlainText
                                    wrapMode: Text.WordWrap
                                }
                            }
                            GohuText {
                                text: "ACCOUNTS"
                                font.pixelSize: 12
                                color: Colors.omnitrix
                            }
                            Repeater {
                                model: financeBudget.snapshot
                                       ? financeBudget.snapshot.accounts : []
                                delegate: Rectangle {
                                    required property var modelData
                                    width: budgetList.width
                                    height: 42
                                    color: Colors.black
                                    border.color: Colors.omnitrix
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.right: parent.right
                                        anchors.margins: 5
                                        text: modelData.name
                                        textFormat: Text.PlainText
                                        font.pixelSize: 10
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.bottom: parent.bottom
                                        anchors.margins: 5
                                        text: root.moneyText(modelData.balanceCents)
                                        font.pixelSize: 11
                                        color: Colors.omnitrix
                                    }
                                }
                            }

                            GohuText {
                                text: "CATEGORIES"
                                font.pixelSize: 12
                                color: Colors.cyan
                            }
                            ActionButton {
                                id: checkAllocationLock
                                width: parent.width
                                height: 28
                                trackLabelGlowLocally: true
                                label: "CHECK WRITE LOCK"
                                labelPixelSize: 10
                                accentColor: Colors.cyan
                                available: allocationGateCheck.state !== "checking"
                                onLeftClicked: allocationGateCheck.check()
                            }
                            GohuText {
                                width: parent.width
                                text: allocationGateCheck.message
                                textFormat: Text.PlainText
                                font.pixelSize: 9
                                color: allocationGateCheck.state === "locked"
                                       ? Colors.cyan : Colors.orange
                                wrapMode: Text.WordWrap
                            }
                            FinanceCategoryAllocationPane {
                                id: allocationPreviewPane
                                width: parent.width
                                snapshot: financeBudget.snapshot
                                writeState: financeAllocationWrite.state
                                writeMessage: financeAllocationWrite.message
                                onSaveRequested: function(payload) {
                                    financeAllocationWrite.submit(payload);
                                }
                            }
                            GohuText {
                                width: parent.width
                                text: financeAllocationWrite.message
                                textFormat: Text.PlainText
                                font.pixelSize: 9
                                color: financeAllocationWrite.state === "committed"
                                       ? Colors.omnitrix : Colors.orange
                                wrapMode: Text.WordWrap
                            }
                            Repeater {
                                model: financeBudget.snapshot
                                       ? financeBudget.snapshot.categories : []
                                delegate: Rectangle {
                                    required property var modelData
                                    width: budgetList.width
                                    height: 76
                                    color: Colors.black
                                    border.color: modelData.availableCents < 0
                                                  ? Colors.magenta : Colors.cyan
                                    readonly property real usageRatio:
                                        modelData.budgetedCents > 0
                                        ? Math.max(0, Math.min(1,
                                            Math.max(0, -modelData.spentCents)
                                            / modelData.budgetedCents))
                                        : 0

                                    ActionButton {
                                        id: allocationButton
                                        anchors.top: parent.top
                                        anchors.topMargin: 4
                                        anchors.right: parent.right
                                        anchors.rightMargin: 5
                                        width: 78
                                        height: 24
                                        trackLabelGlowLocally: true
                                        label: "ALLOCATE"
                                        labelPixelSize: 9
                                        accentColor: Colors.cyan
                                        available: financeBudget.state === "ready"
                                                   && !!financeBudget.snapshot
                                                   && financeAllocationWrite.state !== "pending"
                                                   && financeAllocationWrite.state !== "uncertain"
                                        onLeftClicked: allocationPreviewPane.begin(modelData)
                                    }
                                    GohuText {
                                        anchors.top: parent.top
                                        anchors.left: parent.left
                                        anchors.right: allocationButton.left
                                        anchors.margins: 5
                                        text: modelData.name
                                        textFormat: Text.PlainText
                                        font.pixelSize: 10
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.topMargin: 24
                                        anchors.leftMargin: 5
                                        text: "SET " + root.moneyText(modelData.budgetedCents)
                                              + "  NET SPENT " + root.moneyText(modelData.spentCents)
                                        textFormat: Text.PlainText
                                        font.pixelSize: 9
                                        color: Colors.cyan
                                    }
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.topMargin: 42
                                        anchors.leftMargin: 5
                                        text: "LEFT " + root.moneyText(modelData.availableCents)
                                              + (modelData.availableCents < 0
                                                 ? "  // OVERSPENT" : "")
                                        textFormat: Text.PlainText
                                        font.pixelSize: 9
                                        color: modelData.availableCents < 0
                                               ? Colors.magenta : Colors.omnitrix
                                    }
                                    Rectangle {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        anchors.margins: 5
                                        height: 3
                                        color: Colors.dark
                                        Rectangle {
                                            width: parent.width * usageRatio
                                            height: parent.height
                                            color: modelData.availableCents < 0
                                                   ? Colors.magenta : Colors.cyan
                                        }
                                    }
                                }
                            }

                            }
}
FinanceAccountsPane {
    id: financeAccountsPane
    width: parent.width
    visible: root.budgetSection==="accounts"
    snapshot: financeBudget.snapshot
    onNewTransactionRequested: {
        root.selectBudgetSection("transactions");
        if(financeAccountsPane.selectedAccountId)
            transactionDraftPane.beginForAccount(financeAccountsPane.selectedAccountId);
        else
            transactionDraftPane.begin();
    }
}
FinanceCategoriesPane {
    id: financeCategoriesPane
    width: parent.width
    visible: root.budgetSection==="categories"
    snapshot: financeBudget.snapshot
    writeState: financeCategoryWrite.state
    writeMessage: financeCategoryWrite.message
    onSaveRequested: function(payload) {
        if(financeBudget.state==="ready" && financeBudget.snapshot
                && payload
                && payload.sourceKey===financeBudget.snapshot.sourceKey
                && payload.month===financeBudget.snapshot.month
                && financeCategoryWrite.state!=="pending"
                && financeCategoryWrite.state!=="uncertain"
                && financeWrite.state!=="pending"
                && financeWrite.state!=="uncertain"
                && financeAllocationWrite.state!=="pending"
                && financeAllocationWrite.state!=="uncertain"
                && financeFundingWrite.state!=="pending"
                && financeFundingWrite.state!=="uncertain")
            financeCategoryWrite.submit(payload);
    }
    onEditBudgetRequested: function(category) {
        root.selectBudgetSection("budget");
        financeBudgetGrid.choose(category);
    }
}
Column {
    id: transactionsSectionContent
    width: parent.width
    spacing: 7
    visible: root.budgetSection==="transactions"
Row {
                                width: parent.width
                                spacing: 7
                                GohuText {
                                    width: parent.width - newTransactionDraft.width - 7
                                    height: 30
                                    verticalAlignment: Text.AlignVCenter
                                    text: "TRANSACTIONS // "
                                          + (financeBudget.snapshot
                                             ? financeBudget.snapshot.transactionsCount : 0)
                                    textFormat: Text.PlainText
                                    font.pixelSize: 11
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }
                                ActionButton {
                                    id: newTransactionDraft
                                    // Same reactive label/glow tracking as the
                                    // four actions within the staged draft.
                                    trackLabelGlowLocally: true
                                    width: 84
                                    height: 30
                                    label: "NEW DRAFT"
                                    labelPixelSize: 9
                                    accentColor: Colors.omnitrix
                                    available: financeBudget.state === "ready"
                                               && financeBudget.snapshot
                                               && financeBudget.snapshot.accounts.length > 0
                                               && financeWrite.state !== "pending"
                                    onLeftClicked: transactionDraftPane.begin()
                                }
                            }

                            FinanceTransactionDraftPane {
                                id: transactionDraftPane
                                width: parent.width
                                accounts: financeBudget.snapshot
                                          ? financeBudget.snapshot.accounts : []
                                selectedMonth: financeBudget.selectedMonth
                                sourceKey: financeBudget.snapshot
                                           ? financeBudget.snapshot.sourceKey : ""
                                saveState: financeWrite.state
                                saveMessage: financeWrite.message
                                draftStoreState: financeDrafts.state
                                draftStoreMessage: financeDrafts.message
                                onDraftSaveRequested: function(payload) {
                                    financeDrafts.upsert(payload);
                                }
                                onSaveRequested: function(payload) {
                                    financeWrite.submit(payload);
                                }
                            }

                            Row {
                                width: parent.width
                                spacing: 7
                                GohuText {
                                    width: parent.width - reloadDrafts.width - 7
                                    height: 28
                                    verticalAlignment: Text.AlignVCenter
                                    text: "SAVED DRAFTS // " + financeDrafts.drafts.length
                                    font.pixelSize: 10
                                    textFormat: Text.PlainText
                                    color: Colors.cyan
                                    elide: Text.ElideRight
                                }
                                ActionButton {
                                    id: reloadDrafts
                                    trackLabelGlowLocally: true
                                    width: 66
                                    height: 28
                                    label: "RELOAD"
                                    labelPixelSize: 9
                                    accentColor: Colors.cyan
                                    available: financeDrafts.state !== "pending"
                                    onLeftClicked: financeDrafts.refresh()
                                }
                            }
                            GohuText {
                                width: parent.width
                                visible: financeDrafts.state === "failed"
                                text: financeDrafts.message
                                textFormat: Text.PlainText
                                font.pixelSize: 9
                                color: Colors.orange
                                wrapMode: Text.WordWrap
                            }
                            Repeater {
                                model: financeDrafts.drafts
                                delegate: Rectangle {
                                    required property var modelData
                                    property bool deleteArmed: false
                                    width: budgetList.width
                                    height: 62
                                    color: Colors.black
                                    border.width: 1
                                    border.color: Colors.cyan
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.leftMargin: 5
                                        anchors.topMargin: 5
                                        width: parent.width - 10
                                        text: (modelData.payeeText || "UNTITLED")
                                              + " // " + (modelData.dateText || "NO DATE")
                                        textFormat: Text.PlainText
                                        font.pixelSize: 9
                                        color: Colors.white
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.bottom: parent.bottom
                                        anchors.leftMargin: 5
                                        anchors.bottomMargin: 8
                                        text: "LOCAL ONLY"
                                        font.pixelSize: 9
                                        color: Colors.cyan
                                    }
                                    ActionButton {
                                        anchors.bottom: parent.bottom
                                        anchors.right: deleteLocalDraft.left
                                        anchors.rightMargin: 7
                                        anchors.bottomMargin: 4
                                        width: 50
                                        height: 25
                                        trackLabelGlowLocally: true
                                        label: "OPEN"
                                        labelPixelSize: 9
                                        accentColor: Colors.omnitrix
                                        available: !transactionDraftPane.open
                                            && financeDrafts.state === "ready"
                                            && financeBudget.snapshot
                                            && financeBudget.snapshot.accounts.some(
                                                function(a) {return a.id === modelData.accountId;})
                                        onLeftClicked: transactionDraftPane.beginStored(modelData)
                                    }
                                    ActionButton {
                                        id: deleteLocalDraft
                                        anchors.right: parent.right
                                        anchors.rightMargin: 4
                                        anchors.bottom: parent.bottom
                                        anchors.bottomMargin: 4
                                        width: 65
                                        height: 25
                                        trackLabelGlowLocally: true
                                        label: deleteArmed ? "CONFIRM" : "DELETE"
                                        labelPixelSize: 9
                                        accentColor: deleteArmed ? Colors.red : Colors.orange
                                        available: financeDrafts.state === "ready"
                                            && !transactionDraftPane.open
                                        onLeftClicked: {
                                            if (!deleteArmed) {
                                                deleteArmed = true;
                                            } else {
                                                financeDrafts.remove(modelData.id);
                                            }
                                        }
                                    }
                                }
                            }

                            GohuText {
                                width: parent.width
                                visible: financeBudget.snapshot
                                         && financeBudget.snapshot.transactionsCount === 0
                                text: "NO TRANSACTIONS IN SELECTED MONTH"
                                textFormat: Text.PlainText
                                font.pixelSize: 9
                                color: Colors.white
                            }

                            Repeater {
                                model: financeBudget.snapshot
                                       ? financeBudget.snapshot.transactions : []
                                delegate: Rectangle {
                                    required property var modelData
                                    width: budgetList.width
                                    height: 54
                                    color: Colors.black
                                    border.width: 1
                                    border.color: Colors.cyan
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.right: editTransaction.left
                                        anchors.top: parent.top
                                        anchors.margins: 5
                                        text: modelData.date + "  " + modelData.description
                                        textFormat: Text.PlainText
                                        color: Colors.white
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        anchors.left: parent.left
                                        anchors.bottom: parent.bottom
                                        anchors.margins: 5
                                        text: modelData.account
                                        textFormat: Text.PlainText
                                        color: Colors.cyan
                                        font.pixelSize: 9
                                        elide: Text.ElideRight
                                    }
                                    GohuText {
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        anchors.margins: 5
                                        text: root.moneyText(modelData.amountCents)
                                        textFormat: Text.PlainText
                                        color: modelData.amountCents < 0
                                               ? Colors.orange : Colors.omnitrix
                                        font.pixelSize: 11
                                    }
                                    ActionButton {
                                        id: editTransaction
                                        anchors.top: parent.top
                                        anchors.topMargin: 4
                                        anchors.right: parent.right
                                        anchors.rightMargin: 5
                                        width: 46
                                        height: 24
                                        trackLabelGlowLocally: true
                                        label: "EDIT"
                                        labelPixelSize: 9
                                        accentColor: Colors.cyan
                                        available: modelData.editable === true
                                                   && financeWrite.state !== "pending"
                                                   && financeWrite.state !== "uncertain"
                                        onLeftClicked: transactionDraftPane.beginEdit(modelData)
                                    }

                                }
                            }

                            GohuText {
                                width: parent.width
                                visible: financeBudget.snapshot
                                         && financeBudget.snapshot.transactionsCount > 24
                                text: "LATEST 24 SHOWN // READ ONLY"
                                textFormat: Text.PlainText
                                font.pixelSize: 9
                                color: Colors.orange
                            }
                            }
                        }
                    }
                }

                // Non-Budget pages reserve a stable local host. Future
                // adapters stay mounted across chassis size transitions.
                FinanceToolHost {
                    id: financeToolHost
                    anchors.fill: parent
                    visible: !actualBudgetPage.visible
                             && root.selectedMainMode !== "research"
                    // Component persists while navigating/resizing, not just while Market is selected.
                    embeddedComponent: marketPaneComponent
                    showEmbedded: root.selectedMainMode === "market"
                    domainTitle: root.selectedMainMode === "budget"
                                 ? root.selectedBudgetSubMode.toUpperCase()
                                 : root.mainModeName().toUpperCase()
                }

                // Research tools share an in-place surface; the crawl and SEC
                // readers remain independent and no new PanelWindow is added.
                Item {
                    id: researchTools
                    anchors.fill: parent
                    visible: root.selectedMainMode === "research"

                    Row {
                        id: researchToolStrip
                        anchors.top: parent.top
                        anchors.topMargin: 4
                        anchors.left: parent.left
                        height: 32
                        spacing: 6
                        ActionButton {
                            width: 120
                            height: 28
                            label: "SOURCE CRAWL"
                            labelPixelSize: 9
                            accentColor: Colors.cyan
                            selected: root.researchTool === "crawl"
                            onLeftClicked: root.researchTool = "crawl"
                        }
                        ActionButton {
                            width: 92
                            height: 28
                            label: "SEC EDGAR"
                            labelPixelSize: 9
                            accentColor: Colors.orange
                            selected: root.researchTool === "sec"
                            onLeftClicked: root.researchTool = "sec"
                        }
                    }
                    FinanceResearchCrawlPane {
                        id: crawlPane
                        anchors.top: researchToolStrip.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        visible: root.researchTool === "crawl"
                        crawlFeed: crawlService
                    }
                    FinanceSecFilingsPane {
                        id: secPane
                        anchors.top: researchToolStrip.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        visible: root.researchTool === "sec"
                        secFeed: secService
                    }
                }
            }
        }
    }
}
