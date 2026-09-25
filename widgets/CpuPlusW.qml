import Quickshell
import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../components"
import "appcontrol"
import "cpuplus"

PanelWindow {
    id: cpuPlusWindow

    property var appControlWindow

    property bool menuOpen: false
    property int selectedModeIndex: 0
    property int thermalSelectedIndex: 0
    property int systemSelectedIndex: 0

    readonly property var thermalRows:
        appControlWindow && appControlWindow.thermalRows
        ? appControlWindow.thermalRows
        : []

    readonly property var systemRows:
        appControlWindow && appControlWindow.systemRows
        ? appControlWindow.systemRows
        : []

    readonly property var modes: [
        {
            name: "FAVORITES",
            symbol: "(˵✧ᴗ✧˵)",
            kind: "text"
        },
        {
            name: "PROCESS",
            symbol: "(-_•)︻デ═一",
            kind: "text"
        },
        {
            name: "THERMAL",
            symbol: "",
            kind: "thermal"
        },
        {
            name: "SYSTEM",
            symbol: "🖳",
            kind: "text"
        }
    ]

    function open() {
        menuOpen = true;

        if (selectedModeIndex === 2 || selectedModeIndex === 3)
            refreshSharedMonitors();
    }

    function close() {
        menuOpen = false;
    }

    function toggle() {
        menuOpen = !menuOpen;

        if (menuOpen
                && (selectedModeIndex === 2
                    || selectedModeIndex === 3))
            refreshSharedMonitors();
    }

    function selectMode(index) {
        selectedModeIndex = Math.max(
            0,
            Math.min(modes.length - 1, Number(index || 0))
        );

        if (selectedModeIndex === 2 || selectedModeIndex === 3)
            refreshSharedMonitors();
    }

    function refreshSharedMonitors() {
        if (appControlWindow)
            appControlWindow.refreshKillMonitor();
    }

    function selectedMonitorRows() {
        if (selectedModeIndex === 2)
            return thermalRows;

        if (selectedModeIndex === 3)
            return systemRows;

        return [];
    }

    function selectedMonitorIndex() {
        return selectedModeIndex === 2
               ? thermalSelectedIndex
               : systemSelectedIndex;
    }

    function selectMonitorRow(index) {
        const rows = selectedMonitorRows();
        if (!rows || rows.length <= 0)
            return;

        const next = Math.max(
            0,
            Math.min(rows.length - 1, Number(index || 0))
        );

        if (selectedModeIndex === 2)
            thermalSelectedIndex = next;
        else if (selectedModeIndex === 3)
            systemSelectedIndex = next;
    }

    function selectedMonitorEntry() {
        const rows = selectedMonitorRows();

        if (!rows || rows.length <= 0)
            return null;

        const index = Math.max(
            0,
            Math.min(rows.length - 1, selectedMonitorIndex())
        );

        return rows[index] || null;
    }

    function monitorEntryTitle(entry) {
        return String(
            entry && (entry.label || entry.name) || "UNKNOWN"
        ).toUpperCase();
    }

    function monitorEntryMetric(entry) {
        if (!entry)
            return "";

        if (entry._thermalRecord) {
            if (entry.sensorKind === "fan") {
                if (entry.rpmAvailable === false)
                    return "RPM N/A";

                return Number(entry.rpm || 0).toFixed(0) + " RPM";
            }

            return Number(entry.tempC || 0).toFixed(1) + "°C";
        }

        return String(entry.metric || entry.secondary || "");
    }

    // ============================================================
    // SHARED THERMAL ICON
    // Copied from AppControl's canonical THERMAL composition so the
    // two surfaces speak the same visual language.
    // ============================================================

    Component {
        id: thermalIconComponent

        Item {
            id: thermalIconRoot

            property color iconColor: Colors.orange
            property color glowColor: Colors.orange
            property real iconScale: 1.0
            property real glowOpacity: 0.46
            property bool pressed: false

            opacity: 1.0
            implicitWidth: 59 * iconScale
            implicitHeight: 24 * iconScale
            width: implicitWidth
            height: implicitHeight

            Item {
                id: thermalIconScaledContent

                width: 59
                height: 24

                anchors.centerIn: parent

                scale: thermalIconRoot.iconScale
                transformOrigin: Item.Center
                opacity: 1.0

                GohuText {
                    id: thermalIconTopLeftStar

                    x: 15
                    y: -3

                    text: "⋆"

                    font.pixelSize: 7

                    opacity: 1.0

                    color:
                        thermalIconRoot.pressed
                        ? Colors.black
                        : thermalIconRoot.iconColor
                }

                DropShadow {
                    anchors.fill: thermalIconTopLeftStar
                    source: thermalIconTopLeftStar

                    visible: !thermalIconRoot.pressed

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 4
                    samples: 5

                    opacity: thermalIconRoot.glowOpacity
                    color: thermalIconRoot.glowColor

                    transparentBorder: true
                }

                Row {
                    id: thermalIconOuterRow

                    anchors.centerIn: parent

                    spacing: 1

                    Row {
                        id: thermalIconLeftCoreRow

                        anchors.verticalCenter: parent.verticalCenter

                        spacing: -9

                        Item {
                            width: thermalIconLeft.implicitWidth
                            height: 24

                            GohuText {
                                id: thermalIconLeft

                                anchors.verticalCenter: parent.verticalCenter

                                text: "₊˚⊹"

                                font.pixelSize: 13
                                font.letterSpacing: -1.6

                                opacity: 1.0

                                color:
                                    thermalIconRoot.pressed
                                    ? Colors.black
                                    : thermalIconRoot.iconColor
                            }

                            DropShadow {
                                anchors.fill: thermalIconLeft
                                source: thermalIconLeft

                                visible: !thermalIconRoot.pressed

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 5
                                samples: 5

                                opacity: thermalIconRoot.glowOpacity
                                color: thermalIconRoot.glowColor

                                transparentBorder: true
                            }
                        }

                        Item {
                            width: thermalIconCore.implicitWidth
                            height: 24

                            Text {
                                id: thermalIconCore

                                anchors.verticalCenter: parent.verticalCenter

                                text: "🌡"

                                font.family: "Noto Sans Symbols2"
                                font.pixelSize: 20
                                font.weight: Font.Bold

                                opacity: 1.0

                                color:
                                    thermalIconRoot.pressed
                                    ? Colors.black
                                    : thermalIconRoot.iconColor
                            }

                            DropShadow {
                                anchors.fill: thermalIconCore
                                source: thermalIconCore

                                visible: !thermalIconRoot.pressed

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 5
                                samples: 5

                                opacity: thermalIconRoot.glowOpacity * 0.76
                                color: thermalIconRoot.glowColor

                                transparentBorder: true
                            }
                        }
                    }

                    Item {
                        width: thermalIconRight.implicitWidth
                        height: 24

                        GohuText {
                            id: thermalIconRight

                            anchors.verticalCenter: parent.verticalCenter

                            text: "๋࣭⭑"

                            font.pixelSize: 13

                            opacity: 1.0

                            color:
                                thermalIconRoot.pressed
                                ? Colors.black
                                : thermalIconRoot.iconColor
                        }

                        DropShadow {
                            anchors.fill: thermalIconRight
                            source: thermalIconRight

                            visible: !thermalIconRoot.pressed

                            horizontalOffset: 0
                            verticalOffset: 0

                            radius: 5
                            samples: 5

                            opacity: thermalIconRoot.glowOpacity
                            color: thermalIconRoot.glowColor

                            transparentBorder: true
                        }
                    }
                }
            }
        }
    }

    // ============================================================
    // WINDOW
    // AppControlW: 834 wide x 674 tall
    // CPU++:       674 wide x 834 tall
    // ============================================================

    implicitWidth: 674
    implicitHeight: 834

    anchors {
        top: true
        right: true
    }

    // Original right margin was 2. Increase by 80px to move the
    // entire CPU++ chassis left without changing its dimensions.
    margins {
        top: -3
        right: 200
    }

    color: "transparent"
    surfaceFormat.opaque: false
    focusable: true
    visible: menuOpen

    // ============================================================
    // OUTER CHASSIS GLOW
    // Structural glow remains orange at every interaction state.
    // ============================================================

    RectangularShadow {
        anchors.fill: background

        spread: 6
        z: -20

        opacity: 0.38
        color: Colors.orange
    }

    RectangularShadow {
        anchors.fill: background

        spread: 12
        z: -21

        opacity: 0.12
        color: Colors.orange
    }

    Rectangle {
        id: background

        anchors.fill: parent
        anchors.margins: 12

        color: "transparent"
    }

    // ============================================================
    // TOP MODE SELECTOR
    // ============================================================

    Rectangle {
        id: modeRail

        height: 110

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top

        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.topMargin: 12

        // Swapped with the CPU++ native control panel.
        color: Colors.dark

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.22
            color: Colors.orange
        }

        GohuText {
            id: modeRailHeader

            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 14
            anchors.topMargin: 8

            text: "CPU++"

            font.pixelSize: 15
            color: Colors.magenta
        }

        Rectangle {
            id: modeRailHeaderLine

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: modeRailHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 5

            height: 2

            color: Colors.cyan
        }

        Row {
            id: modeButtonRow

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.bottomMargin: 8

            height: 58
            spacing: 8

            Repeater {
                model: cpuPlusWindow.modes

                Rectangle {
                    id: modeButton

                    required property int index
                    required property var modelData

                    readonly property bool isSelected:
                        index === cpuPlusWindow.selectedModeIndex

                    readonly property bool isHovered:
                        modeMouse.containsMouse

                    readonly property bool isPressed:
                        modeMouse.pressed

                    readonly property color contentColor:
                        isPressed
                        ? Colors.black
                        : isSelected
                        ? Colors.magenta
                        : isHovered
                        ? Colors.orange
                        : Colors.cyan

                    width:
                        (
                            modeButtonRow.width
                            - modeButtonRow.spacing
                              * (cpuPlusWindow.modes.length - 1)
                        )
                        / cpuPlusWindow.modes.length

                    height: parent.height

                    scale:
                        isPressed
                        ? 0.99
                        : isHovered
                        ? 1.025
                        : isSelected
                        ? 1.01
                        : 1.0

                    color:
                        isPressed
                        ? Colors.magenta
                        : isHovered || isSelected
                        ? Colors.yellow
                        : Colors.black

                    border.width: 1
                    border.color: Colors.cyan

                    Behavior on scale {
                        NumberAnimation {
                            duration: 90
                            easing.type: Easing.OutQuad
                        }
                    }

                    Column {
                        width: parent.width
                        anchors.centerIn: parent

                        spacing: 1

                        Item {
                            width: parent.width
                            height: 29

                            Loader {
                                id: thermalModeIcon

                                anchors.centerIn: parent

                                visible: modelData.kind === "thermal"
                                sourceComponent:
                                    visible
                                    ? thermalIconComponent
                                    : undefined

                                onLoaded: {
                                    item.iconScale = 0.82;
                                    item.iconColor = Qt.binding(function() {
                                        return modeButton.contentColor;
                                    });
                                    item.pressed = Qt.binding(function() {
                                        return modeButton.isPressed;
                                    });
                                    item.glowOpacity = 0.34;
                                }
                            }

                            GohuText {
                                id: textModeIcon

                                anchors.centerIn: parent

                                visible: modelData.kind !== "thermal"

                                text: modelData.symbol

                                font.pixelSize:
                                    modelData.name === "PROCESS"
                                    ? 12
                                    : modelData.name === "FAVORITES"
                                    ? 14
                                    : 18

                                color: modeButton.contentColor

                                layer.enabled: !modeButton.isPressed
                                layer.effect: DropShadow {
                                    horizontalOffset: 0
                                    verticalOffset: 0

                                    radius: 7
                                    samples: 9

                                    opacity:
                                        modeButton.isHovered
                                        || modeButton.isSelected
                                        ? 0.60
                                        : 0.30

                                    color: Colors.orange

                                    transparentBorder: true
                                }
                            }
                        }

                        GohuText {
                            anchors.horizontalCenter: parent.horizontalCenter

                            text: modelData.name

                            font.pixelSize: 10
                            color: modeButton.contentColor
                        }
                    }

                    MouseArea {
                        id: modeMouse

                        anchors.fill: parent

                        hoverEnabled: true

                        onClicked: {
                            cpuPlusWindow.selectMode(index);
                        }
                    }

                    // Orange glow is invariant; only its reach/intensity changes.
                    RectangularShadow {
                        anchors.fill: parent

                        spread:
                            modeButton.isHovered
                            ? 6
                            : modeButton.isSelected
                            ? 4
                            : 2

                        z: -1

                        opacity:
                            modeButton.isPressed
                            ? 0.62
                            : modeButton.isHovered
                            ? 0.56
                            : modeButton.isSelected
                            ? 0.46
                            : 0.10

                        color: Colors.orange
                    }

                    RectangularShadow {
                        anchors.fill: parent

                        spread:
                            modeButton.isHovered
                            ? 16
                            : modeButton.isSelected
                            ? 11
                            : 7

                        z: -2

                        opacity:
                            modeButton.isPressed
                            ? 0.16
                            : modeButton.isHovered
                            ? 0.14
                            : modeButton.isSelected
                            ? 0.11
                            : 0.035

                        color: Colors.orange
                    }
                }
            }
        }
    }

    // ============================================================
    // TWO-BODY MONITOR ADAPTER + SHARED REFRESH PACEMAKER
    // ============================================================

    CpuPlusMonitorHost {
        id: monitorHost

        appControlWindow: cpuPlusWindow.appControlWindow
        cpuPlusWindow: cpuPlusWindow
    }

    Timer {
        id: sharedMonitorRefreshTimer

        interval: 1900
        repeat: true

        running:
            cpuPlusWindow.menuOpen
            && (cpuPlusWindow.selectedModeIndex === 2
                || cpuPlusWindow.selectedModeIndex === 3)

        onTriggered: cpuPlusWindow.refreshSharedMonitors()
    }

    // ============================================================
    // SHARED APPCONTROL INSTRUMENT BAY
    // ============================================================

    Rectangle {
        id: sharedInstrumentPane

        width: 390

        anchors.left: parent.left
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.leftMargin: 12
        anchors.bottomMargin: 12

        color: Qt.rgba(
            Colors.black.r,
            Colors.black.g,
            Colors.black.b,
            0.95
        )

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            id: sharedInstrumentHeader

            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 16
            anchors.topMargin: 16

            text:
                cpuPlusWindow.selectedModeIndex === 2
                ? "THERMAL MONITOR"
                : cpuPlusWindow.selectedModeIndex === 3
                ? "SYSTEM MONITOR"
                : "SHARED INSTRUMENT"

            font.pixelSize: 13
            color: Colors.magenta
        }

        Rectangle {
            id: sharedHeaderLine

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sharedInstrumentHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6

            height: 2

            color: Colors.cyan
        }

        Flickable {
            id: sharedInstrumentScroll

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sharedHeaderLine.bottom
            anchors.bottom: parent.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 10
            anchors.bottomMargin: 8

            clip: true
            contentWidth: width
            contentHeight:
                cpuPlusWindow.selectedModeIndex === 2
                ? Math.max(
                      height,
                      thermalMonitorBody.implicitHeight
                  )
                : cpuPlusWindow.selectedModeIndex === 3
                ? Math.max(
                      height,
                      systemMonitorBody.implicitHeight
                  )
                : height

            Item {
                width: sharedInstrumentScroll.width
                height: sharedInstrumentScroll.contentHeight

                ThermalMonitorView {
                    id: thermalMonitorBody

                    width: parent.width
                    controller: monitorHost
                }

                SystemMonitorView {
                    id: systemMonitorBody

                    width: parent.width
                    controller: monitorHost
                }

                GohuText {
                    anchors.centerIn: parent

                    visible:
                        cpuPlusWindow.selectedModeIndex !== 2
                        && cpuPlusWindow.selectedModeIndex !== 3

                    text:
                        cpuPlusWindow.selectedModeIndex === 0
                        ? "FAVORITES BAY"
                        : "PROCESS BAY"

                    font.pixelSize: 14
                    color: Colors.magenta
                    opacity: 0.62
                }
            }
        }
    }

    // ============================================================
    // CPU++ NATIVE EXPANSION / MONITOR SELECTOR BAY
    // ============================================================

    Rectangle {
        id: nativeControlPane

        anchors.left: sharedInstrumentPane.right
        anchors.right: parent.right
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.rightMargin: 12
        anchors.bottomMargin: 12

        color: Colors.black

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent

            spread: 4
            z: -1

            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            id: nativeControlHeader

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top

            anchors.topMargin: 16

            text:
                cpuPlusWindow.selectedModeIndex === 2
                ? "THERMAL SENSORS"
                : cpuPlusWindow.selectedModeIndex === 3
                ? "SYSTEM COMPONENTS"
                : "CPU++ CONTROL"

            font.pixelSize: 13
            color: Colors.magenta
        }

        Rectangle {
            id: nativeHeaderLine

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: nativeControlHeader.bottom

            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 6

            height: 2

            color: Colors.cyan
        }

        Flickable {
            id: monitorSelectorScroll

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: nativeHeaderLine.bottom
            anchors.bottom: parent.bottom

            anchors.margins: 8
            anchors.topMargin: 10

            visible:
                cpuPlusWindow.selectedModeIndex === 2
                || cpuPlusWindow.selectedModeIndex === 3

            clip: true
            contentWidth: width
            contentHeight: monitorSelectorColumn.implicitHeight

            Column {
                id: monitorSelectorColumn

                width: monitorSelectorScroll.width
                spacing: 7

                Repeater {
                    model:
                        cpuPlusWindow.selectedModeIndex === 2
                        ? cpuPlusWindow.thermalRows
                        : cpuPlusWindow.selectedModeIndex === 3
                        ? cpuPlusWindow.systemRows
                        : []

                    Rectangle {
                        id: monitorRowButton

                        required property int index
                        required property var modelData

                        readonly property bool isSelected:
                            index === cpuPlusWindow.selectedMonitorIndex()

                        readonly property bool isHovered:
                            monitorRowMouse.containsMouse

                        readonly property bool isPressed:
                            monitorRowMouse.pressed

                        readonly property color foreground:
                            isPressed
                            ? Colors.black
                            : isSelected
                            ? Colors.magenta
                            : isHovered
                            ? Colors.orange
                            : Colors.cyan

                        width: monitorSelectorColumn.width
                        height: 56

                        color:
                            isPressed
                            ? Colors.magenta
                            : isSelected || isHovered
                            ? Colors.yellow
                            : Colors.black

                        border.width: 1
                        border.color: Colors.cyan

                        scale:
                            isPressed
                            ? 0.99
                            : isHovered
                            ? 1.015
                            : 1.0

                        Behavior on scale {
                            NumberAnimation {
                                duration: 90
                                easing.type: Easing.OutQuad
                            }
                        }

                        Column {
                            anchors.fill: parent
                            anchors.margins: 7

                            spacing: 3

                            GohuText {
                                width: parent.width

                                text:
                                    cpuPlusWindow.monitorEntryTitle(
                                        monitorRowButton.modelData
                                    )

                                font.pixelSize: 11
                                color: monitorRowButton.foreground
                                elide: Text.ElideRight
                            }

                            GohuText {
                                width: parent.width

                                text:
                                    cpuPlusWindow.monitorEntryMetric(
                                        monitorRowButton.modelData
                                    )

                                font.pixelSize: 9
                                color: monitorRowButton.foreground
                                opacity: 0.78
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            id: monitorRowMouse

                            anchors.fill: parent
                            hoverEnabled: true

                            onClicked: {
                                cpuPlusWindow.selectMonitorRow(index);
                            }
                        }

                        RectangularShadow {
                            anchors.fill: parent

                            spread:
                                monitorRowButton.isHovered
                                ? 6
                                : monitorRowButton.isSelected
                                ? 4
                                : 2

                            z: -1

                            opacity:
                                monitorRowButton.isPressed
                                ? 0.58
                                : monitorRowButton.isHovered
                                ? 0.48
                                : monitorRowButton.isSelected
                                ? 0.38
                                : 0.08

                            color: Colors.orange
                        }
                    }
                }
            }
        }

        GohuText {
            anchors.centerIn: parent

            visible:
                cpuPlusWindow.selectedModeIndex !== 2
                && cpuPlusWindow.selectedModeIndex !== 3

            text:
                cpuPlusWindow.selectedModeIndex === 0
                ? "FAVORITES"
                : "PROCESS"

            font.pixelSize: 13
            color: Colors.magenta
            opacity: 0.58
        }
    }
}
