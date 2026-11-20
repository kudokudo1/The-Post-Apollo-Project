import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"
import "CompanyChassisPolicy.js" as CompanyChassisPolicy
import "CompanyVectorViewportPolicy.js" as VectorViewportPolicy

// Company Network v0: navigation-only geographic operations chassis.
// No organization membership, employee directory or client data is loaded.
// A mapped, masked PanelWindow avoids repeated Wayland remap cycles.
PanelWindow {
    id: root

    property bool menuOpen: false
    property real dockCenterX: 0
    property real chassisTopY: 0

    // Finance-style controls; default outer panel matches Weather Station
    // exactly (1000 × 700) on a sufficiently large display.
    property string chassisLevel: "standard"
    property bool coverageLoaded: false
    // M26 opt-in must be enabled explicitly by a future approved integration.
    // The M25 QML plugin is optional; normal Company requires no new modules.
    property bool vectorBridgeOptIn: false
    readonly property int glowGutter: 12
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 12
    readonly property var chassisFrame: CompanyChassisPolicy.frame(
        chassisLevel,
        root.screen ? root.screen.width : 2560,
        root.screen ? root.screen.height : 1440,
        glowGutter, frameTopInset, bottomScreenGap)
    readonly property int frameWidth: chassisFrame.width
    readonly property int frameHeight: chassisFrame.height

    readonly property var mainModes: [
        { id: "coverage", label: "COVERAGE", title: "TERRITORY COVERAGE",
          detail: "No verified state, county, city, or service-area records are connected." },
        { id: "network", label: "NETWORK", title: "HUBS & PARTNERS",
          detail: "Organization locations, service providers, and referral links are not connected." },
        { id: "workforce", label: "WORKFORCE", title: "TEAMS & ONBOARDING",
          detail: "Worker assignments and employee/client onboarding records are not connected." },
        { id: "expansion", label: "EXPANSION", title: "EXPANSION PLANNING",
          detail: "No proposed territories, staffing scenarios, or coverage forecasts are loaded." }
    ]
    property int selectedMainModeIndex: 0
    readonly property var activeMode: mainModes[selectedMainModeIndex]

    // Local navigation only. The embedded map and its own/native input
    // remain authoritative whenever they (rather than the frame) have focus.
    property int keyboardModeCursor: 0
    readonly property bool standardModeKeysAvailable:
        root.menuOpen && root.activeFocusItem === companyFrame
    readonly property alias contentKeyboardSelectorItem: companyContentKeys
    onSelectedMainModeIndexChanged: {
        keyboardModeCursor=selectedMainModeIndex;
        companyContentKeys.reset();
        Qt.callLater(function() {
            if(companyContentKeys.navigationActive)
                companyContentKeys.selectInitial();
        });
    }

    function selectMainMode(index) {
        if(index >= 0 && index < mainModes.length) {
            selectedMainModeIndex = index;
            keyboardModeCursor = index;
        }
    }

    function cycleMainMode(direction) {
        if(!standardModeKeysAvailable || mainModes.length < 1) return;
        const count=mainModes.length;
        const step=Number(direction) < 0 ? -1 : 1;
        selectMainMode((selectedMainModeIndex+step+count)%count);
    }

    // Arrows and HJKL navigate the current Company CONTENT pane.
    // Only Tab/Shift+Tab may move the main-mode rail.
    function moveContentKey(key,modifiers) {
        if(!standardModeKeysAvailable) return false;
        return companyContentKeys.handleDirectionKey(key,modifiers);
    }
    function moveNavigationCursor(direction) {
        if(!standardModeKeysAvailable) return false;
        return companyContentKeys.move(0,Number(direction)<0?-1:1);
    }
    function activateNavigationCursor() {
        if(!standardModeKeysAvailable) return false;
        return companyContentKeys.activate();
    }
    // M18 // One candidate viewport in Company FRAME-local coordinates,
    // deliberately NOT native/output-global. Stage Director must separately
    // authenticate the paired Company layer and validate its output epoch.
    // Do not import the Weather-only WATCH QML module into this app.
    readonly property rect activeVectorViewportRect: {
        if (!root.menuOpen || root.selectedMainModeIndex !== 0
                || !coverageLoader.active || !coverageLoader.visible
                || !coverageLoader.item || !coverageLoader.item.visible)
            return Qt.rect(0, 0, 0, 0);
        const coverage = coverageLoader.item;
        const local = coverage.activeVectorViewportRect;
        if (!VectorViewportPolicy.within(local, coverage.width, coverage.height))
            return Qt.rect(0, 0, 0, 0);
        // Make repositioning dependencies explicit; mapToItem supplies the
        // actual QQuickItem translation, not guessed panel screen offsets.
        const layout = coverageLoader.x + coverageLoader.y
                     + contentPane.x + contentPane.y
                     + companyFrame.x + companyFrame.y;
        if (!isFinite(layout))
            return Qt.rect(0, 0, 0, 0);
        const origin = coverage.mapToItem(companyFrame, local.x, local.y);
        const candidate = Qt.rect(
            origin.x, origin.y, local.width, local.height);
        return VectorViewportPolicy.within(
                    candidate, companyFrame.width, companyFrame.height)
            ? candidate : Qt.rect(0, 0, 0, 0);
    }
    readonly property bool activeVectorViewportValid:
        activeVectorViewportRect.width > 0 && activeVectorViewportRect.height > 0
    // M23's frame_in_host is relative to the actual Quickshell PanelWindow,
    // NOT the screen or the M18 companyFrame-local map rectangle. We compute
    // from QQuickItem coordinates on every chassis resize/reposition.
    readonly property rect activeVectorFrameInHostRect: {
        if (!root.menuOpen || !companyFrame.visible)
            return Qt.rect(0, 0, 0, 0);
        // PanelWindow is not a QQuickItem. Qt6 cannot use it as
        // mapToItem(Item) target; null explicitly requests scene-local
        // coordinates, which are PanelWindow-local for this frame.
        // This is candidate geometry, never native actor authority.
        const origin = companyFrame.mapToItem(null, 0, 0);
        const candidate = Qt.rect(origin.x, origin.y,
                                  companyFrame.width, companyFrame.height);
        return VectorViewportPolicy.within(candidate, root.width, root.height)
            ? candidate : Qt.rect(0, 0, 0, 0);
    }
    readonly property string vectorBridgeStatus: vectorBridgeLink.status
    readonly property bool vectorBridgeWireBound: vectorBridgeLink.wireBound

    function toggle() {
        menuOpen = !menuOpen;
    }

    function expandChassis() {
        chassisLevel = CompanyChassisPolicy.step(chassisLevel, 1);
    }

    function collapseChassis() {
        chassisLevel = CompanyChassisPolicy.step(chassisLevel, -1);
    }

    onMenuOpenChanged: {
        if (menuOpen) {
            keyboardModeCursor = selectedMainModeIndex;
            // Load the geographic map only after first explicit opening.
            // Keep it alive thereafter to preserve view while switching modes.
            coverageLoaded = true;
            Qt.callLater(function() {
                if (root.menuOpen) {
                    companyFrame.forceActiveFocus();
                    Qt.callLater(function() {
                        if(companyContentKeys.navigationActive)
                            companyContentKeys.selectInitial();
                    });
                }
            });
        }
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + frameTopInset + bottomScreenGap

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }
    margins {
        top: CompanyChassisPolicy.topMargin(chassisLevel, chassisTopY,
            root.screen ? root.screen.height : root.implicitHeight,
            root.implicitHeight, glowGutter)
        left: CompanyChassisPolicy.leftMargin(chassisLevel, dockCenterX,
            root.screen ? root.screen.width : root.implicitWidth,
            root.implicitWidth)
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    // M19b: stable Company layer-shell discovery label for Stage Director.
    // This string is NOT authentication. SwayPX must pair the real native
    // wl_client/layer and attested map process before accepting geometry.
    WlrLayershell.namespace: "post-apollo-company-network"
    WlrLayershell.keyboardFocus:
        menuOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: menuOpen
    color: "transparent"
    surfaceFormat.opaque: false
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.frameTopInset
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    // No static import of PostApollo.CompanyVector: the M25 module is
    // separately installed, disabled by default and optional at runtime.
    CompanyVectorBridgeLink {
        id: vectorBridgeLink
        bridgeEnabled: root.vectorBridgeOptIn
        frameRect: root.activeVectorFrameInHostRect
        mapRect: root.activeVectorViewportRect
    }

    // Frame-local keys only. The embedded MapLibre/native viewport and
    // its controls retain keyboard focus whenever Company frame is not active.

    WindowPanelFrame {
        id: companyFrame
        anchors.fill: parent
        anchors.leftMargin: root.glowGutter
        anchors.rightMargin: root.glowGutter
        anchors.topMargin: root.frameTopInset
        anchors.bottomMargin: root.bottomScreenGap
        visible: root.menuOpen
        focus: root.menuOpen
        Keys.priority: Keys.BeforeItem
        Keys.onShortcutOverride: function(event) {
            if(!root.standardModeKeysAvailable) return;
            if(event.key===Qt.Key_Tab || event.key===Qt.Key_Backtab
                    || (event.modifiers===Qt.NoModifier
                        && (event.key===Qt.Key_Left
                            || event.key===Qt.Key_Right
                            || event.key===Qt.Key_Up
                            || event.key===Qt.Key_Down
                            || event.key===Qt.Key_H
                            || event.key===Qt.Key_J
                            || event.key===Qt.Key_K
                            || event.key===Qt.Key_L)))
                event.accepted=true;
        }
        Keys.onPressed: function(event) {
            if(!root.standardModeKeysAvailable) return;
            if(event.key===Qt.Key_Tab || event.key===Qt.Key_Backtab) {
                const reverse=event.key===Qt.Key_Backtab
                    || (event.modifiers & Qt.ShiftModifier)!==0;
                root.cycleMainMode(reverse ? -1 : 1);
            } else if(event.modifiers===Qt.NoModifier
                    && (event.key===Qt.Key_Left
                        || event.key===Qt.Key_Right
                        || event.key===Qt.Key_Up
                        || event.key===Qt.Key_Down
                        || event.key===Qt.Key_H
                        || event.key===Qt.Key_J
                        || event.key===Qt.Key_K
                        || event.key===Qt.Key_L)) {
                if(!root.moveContentKey(event.key,event.modifiers)) return;
            } else if(event.modifiers===Qt.NoModifier
                    && (event.key===Qt.Key_Enter ||
                        event.key===Qt.Key_Return)) {
                if(!root.activateNavigationCursor()) return;
            } else return;
            event.accepted=true;
        }
        Keys.onEscapePressed: function(event) {
            if (!root.menuOpen)
                return;
            root.menuOpen = false;
            event.accepted = true;
        }

        fillColor: Colors.black
        fillOpacity: 0.96
        borderColor: Colors.blue
        borderWidth: 1
        radius: 0
        glowVisible: root.menuOpen
        glowColor: Colors.blue

        Rectangle {
            id: header
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 56
            color: "transparent"

            // Decorated identity: white star ornaments, yellow city.
            Row {
                id: headerCity
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                height: 24
                spacing: 1

                // Same fixed-height centered glyph cells as the dock mark.
                // Never align mixed-size symbols by separate implicit top edges.
                // Offset the left stars' artwork without shifting their
                // Row cell or the right-hand stars.
                Item {
                    id: headerLeftStarCell
                    width: headerLeftStarGlyph.implicitWidth
                    height: headerCity.height

                    NotoText {
                        id: headerLeftStarGlyph
                        x: -2
                        height: headerCity.height
                        verticalAlignment: Text.AlignVCenter
                        textFormat: Text.PlainText
                        text: ". ݁₊⊹"
                        font.pixelSize: 15
                        color: Colors.white
                    }
                }
                // Match the dock: six-pixel total city-only optical offset.
                Item {
                    id: headerCityGlyphCell
                    width: headerCityGlyph.implicitWidth
                    height: headerCity.height

                    NotoText {
                        id: headerCityGlyph
                        x: -2
                        y: 6
                        height: headerCity.height
                        verticalAlignment: Text.AlignVCenter
                        textFormat: Text.PlainText
                        text: "🏙︎"
                        font.pixelSize: 18
                        color: Colors.yellow
                    }
                }
                NotoText {
                    height: headerCity.height
                    verticalAlignment: Text.AlignVCenter
                    textFormat: Text.PlainText
                    text: "๋࣭⭑"
                    font.pixelSize: 15
                    color: Colors.white
                }
            }

            GohuText {
                anchors.left: headerCity.right
                anchors.leftMargin: 10
                anchors.right: collapseChassisButton.left
                anchors.rightMargin: 9
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 17
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
                text: "COMPANY // " + root.activeMode.label
            }

            // Same ↓/↑ interaction as Finance; geometry only.
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
                onLeftClicked: root.collapseChassis()
            }

            ActionButton {
                id: expandChassisButton
                anchors.right: feedStatus.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                width: 30
                height: 30
                label: "↑"
                labelPixelSize: 17
                accentColor: Colors.magenta
                available: root.chassisLevel !== "fullscreen"
                onLeftClicked: root.expandChassis()
            }

            Rectangle {
                id: feedStatus
                anchors.right: closeButton.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                width: 76
                height: 26
                color: Colors.dark
                border.color: Colors.blue
                border.width: 1

                GohuText {
                    anchors.centerIn: parent
                    font.pixelSize: 10
                    color: Colors.yellow
                    text: "NO DATA"
                }
            }

            CloseButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                Accessible.name: "Close Company menu"
                onCloseRequested: root.menuOpen = false
            }
        }

        Rectangle {
            id: headerDivider
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: parent.right
            anchors.rightMargin: 12
            height: 2
            color: Colors.cyan
        }

        Column {
            id: mainModeRail
            anchors.top: headerDivider.bottom
            anchors.topMargin: 15
            anchors.left: parent.left
            anchors.leftMargin: 10
            width: 118
            spacing: 7

            Repeater {
                model: root.mainModes
                ModeButton {
                    required property var modelData
                    required property int index
                    width: mainModeRail.width
                    height: 54
                    textOnly: true
                    labelText: modelData.label
                    labelFontSize: 11
                    bordered: false
                    selected: root.selectedMainModeIndex === index
                    keyboardActive: root.standardModeKeysAvailable
                    keyboardSelected: root.keyboardModeCursor === index
                    idlePrimaryColor: Colors.yellow
                    hoverPrimaryColor: Colors.blue
                    selectedPrimaryColor: Colors.blue
                    perimeterGlowColor: Colors.blue
                    onTriggered: {
                        root.selectMainMode(index);
                        if(root.menuOpen)
                            companyFrame.forceActiveFocus();
                    }
                }
            }
        }

        Rectangle {
            anchors.top: mainModeRail.top
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 15
            anchors.left: mainModeRail.right
            anchors.leftMargin: 8
            width: 2
            color: Colors.cyan
            opacity: 0.8
        }

        Item {
            id: contentPane
            anchors.top: headerDivider.bottom
            anchors.topMargin: 20
            anchors.left: mainModeRail.right
            anchors.leftMargin: 25
            anchors.right: parent.right
            anchors.rightMargin: 20
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 18

            WidgetContentKeyboardNavigator {
                id: companyContentKeys
                anchors.fill: parent
                contentRoot: contentPane
                navigationActive: root.standardModeKeysAvailable
            }

            Loader {
                id: coverageLoader
                anchors.fill: parent
                active: root.coverageLoaded
                visible: root.selectedMainModeIndex === 0
                sourceComponent: Component {
                    CompanyCoveragePane { }
                }
            }

            // Reuse the existing explicit user buttons. Sending a candidate
            // intent must never block or replace the attached M15 launcher.
            Connections {
                target: coverageLoader.item
                ignoreUnknownSignals: true
                function onNativeVectorLaunchRequested(online) {
                    vectorBridgeLink.requestIntent(online);
                }
                function onNativeVectorChildStarted(pid) {
                    // The Process itself supplied this PID. The optional
                    // M28b QPA bridge converts it to a real kernel pidfd.
                    vectorBridgeLink.reportChildPid(pid);
                }
                function onNativeVectorClosed() {
                    vectorBridgeLink.closeIntent();
                }
            }

            Column {
                anchors.fill: parent
                spacing: 16
                visible: root.selectedMainModeIndex !== 0

                GohuText {
                    width: parent.width
                    font.pixelSize: 19
                    font.bold: true
                    color: Colors.yellow
                    text: root.activeMode.title
                    wrapMode: Text.WordWrap
                }

                GohuText {
                    width: parent.width
                    font.pixelSize: 12
                    color: Colors.white
                    wrapMode: Text.WordWrap
                    text: root.activeMode.detail
                }

                Rectangle {
                    width: parent.width
                    height: 90
                    color: Colors.dark
                    border.color: Colors.blue
                    border.width: 1

                    Column {
                        anchors.centerIn: parent
                        spacing: 8
                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter
                            font.pixelSize: 15
                            color: Colors.yellow
                            text: "GEOGRAPHIC NETWORK // V0"
                        }
                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter
                            font.pixelSize: 11
                            color: Colors.white
                            text: "UI SCAFFOLD ONLY"
                        }
                    }
                }
            }
        }
    }
}
