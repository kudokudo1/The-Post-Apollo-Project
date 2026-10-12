import QtQuick
import Quickshell
import Quickshell.Wayland
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

PanelWindow {
    id: weatherStation

    property var weatherService: null
    property var spaceService: null

    property bool menuOpen: false
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false

    property string activeDomain: "sky"
    property string currentView: "home"

    readonly property var domains: [
        {
            "id": "ground",
            "name": "GROUND",
            "symbol": "⌁"
        },
        {
            "id": "sky",
            "name": "SKY",
            "symbol": "☁"
        },
        {
            "id": "space",
            "name": "SPACE",
            "symbol": "✦"
        }
    ]

    readonly property var views: [
        {
            "id": "map",
            "name": "MAP",
            "symbol": "⌖"
        },
        {
            "id": "news",
            "name": "NEWS",
            "symbol": "▤"
        },
        {
            "id": "radio",
            "name": "RADIO",
            "symbol": "◉"
        },
        {
            "id": "terminal",
            "name": "TERMINAL",
            "symbol": ">_"
        }
    ]

    readonly property string activeDomainName: {
        for (let i = 0; i < domains.length; i++) {
            if (domains[i].id === activeDomain)
                return domains[i].name;
        }

        return "UNKNOWN";
    }

    readonly property string currentViewName: {
        if (currentView === "home")
            return "HOME";

        for (let i = 0; i < views.length; i++) {
            if (views[i].id === currentView)
                return views[i].name;
        }

        return "UNKNOWN";
    }

    readonly property string currentContext: {
        if (currentView === "home")
            return "HOME";

        return activeDomainName + " // " + currentViewName;
    }

    implicitWidth: menuOpen ? 1000 : 0

    implicitHeight: menuOpen ? 700 : 0

    visible: true
    color: "transparent"

    WlrLayershell.layer: WlrLayer.Overlay

    // Outside Relationship Focus Mode preserve Weather's original policy.
    // During it only the selected menu can hold exclusive layer input.
    WlrLayershell.keyboardFocus:
        !weatherStation.menuOpen ? WlrKeyboardFocus.None
        : weatherStation.relationshipFocusModeActive
        ? (weatherStation.relationshipFocused
           ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None)
        : WlrKeyboardFocus.Exclusive

    anchors {
        top: true
        bottom: false
        right: true
        left: false
    }

    margins {
        top: 0
        bottom: 0
        right: 20
        left: 0
    }

    // Mouse can still pass through the Star Map
    // display area while Kitty is visible.
    mask: Region {
        width: weatherStation.menuOpen ? 1000 : 0

        height: weatherStation.menuOpen ? 700 : 0

        Region {
            x: modeRail.width + terminalView.bayX

            y: header.height + terminalView.bayY

            width: weatherStation.menuOpen && weatherStation.currentView === "terminal" && terminalView.terminalState === "VISIBLE" ? terminalView.bayWidth : 0

            height: weatherStation.menuOpen && weatherStation.currentView === "terminal" && terminalView.terminalState === "VISIBLE" ? terminalView.bayHeight : 0

            intersection: Intersection.Subtract
        }
    }

    function open() {
        menuOpen = true;
    }

    function close() {
        terminalView.closeTerminal();
        menuOpen = false;
    }

    function toggle() {
        if (menuOpen)
            close();
        else
            open();
    }

    WindowPanelFrame {
        id: stationBackground

        width: 1000
        height: 700

        anchors.right: parent.right
        anchors.bottom: parent.bottom

        visible: weatherStation.menuOpen

        fillVisible: false
        borderVisible: false

        glowColor: Colors.cyan
        closeGlowSpread: 4
        closeGlowOpacity: relationshipFocusModeActive
                          ? (relationshipFocused ? 0.58 : 0.09) : 0.30
        wideGlowSpread: 14
        wideGlowOpacity: relationshipFocusModeActive
                         ? (relationshipFocused ? 0.20 : 0.02) : 0.10

        // ─────────────────────────────────────────
        // HEADER
        // ─────────────────────────────────────────

        Rectangle {
            id: header

            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right

            height: 62

            color: Colors.black

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                anchors.leftMargin: 22

                text: "✦ WEATHER STATION ✦"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: Colors.cyan
            }

            Text {
                anchors.centerIn: parent

                text: weatherStation.currentContext

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 18

                color: Colors.orange
            }

            Text {
                id: observatoryButton

                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter

                anchors.rightMargin: 22

                text: "[ □ ]"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 20

                color: observatoryMouse.pressed ? Colors.magenta : observatoryMouse.containsMouse ? Colors.orange : Colors.cyan

                MouseArea {
                    id: observatoryMouse

                    anchors.fill: parent
                    hoverEnabled: true
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                anchors.leftMargin: 15
                anchors.rightMargin: 15

                height: 2

                color: Colors.cyan
            }
        }

        // ─────────────────────────────────────────
        // NAVIGATION
        // ─────────────────────────────────────────

        Rectangle {
            id: modeRail

            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: parent.left

            width: 160

            color: Colors.black

            Rectangle {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right

                width: 2

                color: Colors.cyan
            }

            Column {
                id: railColumn

                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right

                anchors.topMargin: 14

                spacing: 6

                ModeButton {
                    id: homeButton

                    width: railColumn.width
                    height: 48
                    selected: weatherStation.currentView === "home"
                    bordered: false
                    horizontalContent: true
                    contentSpacing: 10
                    iconFontSize: 18
                    labelFontSize: 18
                    iconText: "⌂"
                    labelText: "HOME"
                    onTriggered: { weatherStation.currentView = "home"; }
                }

                Item {
                    width: 1
                    height: 7
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter

                    text: "DOMAIN"

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 12

                    color: Colors.white
                }

                Repeater {
                    model: weatherStation.domains

                    delegate: ModeButton {
                        id: domainButton
                        required property int index
                                                required property var modelData

                        width: railColumn.width
                        height: 48
                        selected: weatherStation.activeDomain === modelData.id
                        bordered: false
                        horizontalContent: true
                        contentSpacing: 10
                        iconFontSize: 18
                        labelFontSize: 18
                        iconText: modelData.symbol
                        labelText: modelData.name
                        onTriggered: { weatherStation.activeDomain = modelData.id; }
                    }
                }

                Item {
                    width: railColumn.width
                    height: 17

                    Rectangle {
                        anchors.centerIn: parent

                        width: parent.width - 28
                        height: 2

                        color: Colors.cyan
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter

                    text: "VIEW"

                    font.family: "GohuFont 11 Nerd Font Mono"

                    font.pixelSize: 12

                    color: Colors.white
                }

                Repeater {
                    model: weatherStation.views

                    delegate: ModeButton {
                        id: viewButton
                        required property int index
                                                required property var modelData

                        width: railColumn.width
                        height: 48
                        selected: weatherStation.currentView === modelData.id
                        bordered: false
                        horizontalContent: true
                        contentSpacing: 10
                        iconFontSize: 18
                        labelFontSize: 18
                        iconText: modelData.symbol
                        labelText: modelData.name
                        onTriggered: { weatherStation.currentView = modelData.id; }
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        // MAIN VIEW
        // ─────────────────────────────────────────

        Rectangle {
            id: mainView

            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: modeRail.right
            anchors.right: parent.right

            color: weatherStation.currentView === "terminal" ? "transparent" : Colors.black

            clip: true

            Loader {
                anchors.fill: parent

                visible: weatherStation.currentView !== "terminal"

                sourceComponent: weatherStation.currentView === "home" ? homeViewComponent : placeholderViewComponent
            }

            StationTerminal {
                id: terminalView

                anchors.fill: parent

                visible: weatherStation.currentView === "terminal"

                stationOpen: weatherStation.menuOpen

                targetScreen: weatherStation.screen

                stationWidth: stationBackground.width

                stationHeight: stationBackground.height

                stationRightMargin: 20
                stationBottomMargin: 90

                stationHeaderHeight: header.height

                stationRailWidth: modeRail.width
            }
        }

        Component {
            id: homeViewComponent

            StationHome {
                activeDomain: weatherStation.activeDomain

                weatherService: weatherStation.weatherService

                spaceService: weatherStation.spaceService

                onDomainRequested: function (domain) {
                    weatherStation.activeDomain = domain;
                }
            }
        }

        Component {
            id: placeholderViewComponent

            Rectangle {
                color: Colors.black

                Column {
                    anchors.centerIn: parent

                    spacing: 12

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: weatherStation.activeDomainName

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 20

                        color: Colors.cyan
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: weatherStation.currentViewName

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 28

                        color: Colors.orange
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter

                        text: {
                            if (weatherStation.currentView === "map")
                                return "map display offline...";

                            if (weatherStation.currentView === "news")
                                return "news receiver offline...";

                            if (weatherStation.currentView === "radio")
                                return "radio receiver offline...";

                            return "";
                        }

                        font.family: "GohuFont 11 Nerd Font Mono"

                        font.pixelSize: 16

                        color: Colors.white
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        // FOOTER
        // ─────────────────────────────────────────

        Rectangle {
            id: footer

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            height: 62

            color: Colors.black

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top

                anchors.leftMargin: 15
                anchors.rightMargin: 15

                height: 2

                color: Colors.cyan
            }

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter

                anchors.leftMargin: 20

                text: weatherStation.weatherService && weatherStation.weatherService.ready ? "◉ WEATHER LINK ONLINE" : "◉ SYSTEM ONLINE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.cyan
            }

            Text {
                anchors.centerIn: parent

                text: "MEDIA BAY // IDLE"

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.white
            }

            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter

                anchors.rightMargin: 20

                text: weatherStation.activeDomainName

                font.family: "GohuFont 11 Nerd Font Mono"

                font.pixelSize: 16

                color: Colors.cyan
            }
        }
    }

    Shortcut {
        sequence: "Escape"

        enabled: weatherStation.menuOpen

        onActivated: {
            weatherStation.close();
        }
    }

    Shortcut {
        sequence: "Meta+Shift+Q"

        enabled: weatherStation.menuOpen

        onActivated: {
            weatherStation.close();
        }
    }
}
