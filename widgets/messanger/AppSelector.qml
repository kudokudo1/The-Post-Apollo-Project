import QtQuick
import Quickshell
import "../../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: appSelector

    // ============================================================
    // STATE
    // ============================================================

    property int selectedIndex: 0
    property bool keyboardActive: false
    property string statusText: ""
    // Entry-point shell only. Identity storage, credentials and family layouts
    // are deliberately reserved for subsequent operator-reviewed slices.
    property bool settingsOpen: false

    // Emitted ONLY when a button is actually clicked.
    signal appActivated(int index)

    // ============================================================
    // APPS
    // ============================================================

    property var messagingApps: [
        {
            name: "SESSIONS",
            icon: "../../assets/Sessions.png"
        },
        {
            name: "DISCORD",
            icon: ""
        },
        {
            name: "TELEGRAM",
            icon: ""
        },
        {
            name: "X",
            icon: ""
        },
        {
            name: "INSTAGRAM",
            icon: ""
        },
        {
            name: "FACEBOOK",
            icon: ""
        },
        {
            name: "REDDIT",
            icon: ""
        },
        {
            name: "THREADS",
            icon: ""
        },
        {
            name: "PINTEREST",
            icon: ""
        },
        {
            name: "TRUTH SOCIAL",
            icon: ""
        },
        {
            name: "BLUESKY",
            icon: ""
        },
        {
            name: "TUMBLR",
            icon: ""
        },
        {
            name: "TIKTOK",
            icon: ""
        },
        {
            name: "SNAPCHAT",
            icon: ""
        },
        {
            name: "WHATSAPP",
            icon: ""
        },
        {
            name: "MESSENGER",
            icon: ""
        },
        {
            name: "LINKEDIN",
            icon: ""
        },
        {
            name: "MASTODON",
            icon: ""
        },
        {
            name: "NEXTDOOR",
            icon: ""
        },
        {
            name: "STEAM CHAT",
            icon: ""
        },
        {
            name: "ELEMENT",
            icon: ""
        },
        {
            name: "GROUPME",
            icon: ""
        },
        {
            name: "LEMON8",
            icon: ""
        },
        {
            name: "QUORA",
            icon: ""
        },
        {
            name: "PIXELFED",
            icon: ""
        },
        {
            name: "ZALO",
            icon: ""
        },
        {
            name: "SIGNAL",
            icon: ""
        },
        {
            name: "WECHAT",
            icon: ""
        },
        {
            name: "LINE",
            icon: ""
        },
        {
            name: "VIBER",
            icon: ""
        },
        {
            name: "KAKAOTALK",
            icon: ""
        },
        {
            name: "BEREAL",
            icon: ""
        }
    ]

    // ============================================================
    // SIZE / PANEL
    // ============================================================

    implicitWidth: 110
    implicitHeight: 700

    opacity: 0.90
    color: Colors.black

    border.width: 1
    border.color: Colors.cyan

    radius: 0

    // ============================================================
    // APP BUTTONS
    // ============================================================

    // Scroll within Social's existing fixed-height cyan selector frame.
    // Keyboard/Tab selection stays visible without changing activation rules.
    function ensureSelectedVisible() {
        if (appScroll.height <= 0)
            return;
        var rowTop = 10 + selectedIndex * 60;
        var rowBottom = rowTop + 50;
        var target = appScroll.contentY;
        if (rowTop < target)
            target = rowTop;
        else if (rowBottom > target + appScroll.height)
            target = rowBottom - appScroll.height;
        appScroll.contentY = Math.max(0, Math.min(
            target, Math.max(0, appScroll.contentHeight - appScroll.height)));
    }

    onSelectedIndexChanged: Qt.callLater(function() {
        appSelector.ensureSelectedVisible();
    })

    Flickable {
        id: appScroll
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top
        }
        contentWidth: width
        contentHeight: appColumn.height + 20
        visible: !appSelector.settingsOpen
        clip: true
        flickableDirection: Flickable.VerticalFlick
        boundsBehavior: Flickable.StopAtBounds
        onHeightChanged: appSelector.ensureSelectedVisible()
        onContentHeightChanged: appSelector.ensureSelectedVisible()

        Column {
            id: appColumn
    
            anchors {
                top: parent.top
                horizontalCenter: parent.horizontalCenter
                topMargin: 10
            }
    
            spacing: 10
    
            Repeater {
                model: appSelector.messagingApps
    
                delegate: Item {
                    id: buttonContainer
    
                    required property var modelData
                    required property int index
    
                    width: 90
                    height: 50
    
                    Rectangle {
                        id: appButton
    
                        anchors.fill: parent
    
                        radius: 0
                        clip: false
    
                        property bool isSelected: appSelector.selectedIndex === buttonContainer.index
    
                        property bool isHovered: !appSelector.keyboardActive && appMouse.containsMouse
    
                        property bool isPressed: appMouse.pressed
    
                        // ============================================
                        // POWER-STYLE BUTTON COLOR
                        // ============================================
    
                        color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.yellow : appButton.isSelected ? Colors.yellow : Colors.dark
    
                        // ============================================
                        // CONTENT
                        // ============================================
    
                        Row {
                            id: appContent
    
                            anchors.centerIn: parent
    
                            spacing: buttonContainer.modelData.icon !== "" ? 4 : 0
    
                            // ========================================
                            // APP ICON
                            // ========================================
    
                            Item {
                                id: iconContainer
    
                                width: buttonContainer.modelData.icon !== "" ? 14 : 0
    
                                height: 18
    
                                visible: buttonContainer.modelData.icon !== ""
    
                                Image {
                                    id: appIcon
    
                                    anchors.centerIn: parent
    
                                    width: 14
                                    height: 14
    
                                    source: buttonContainer.modelData.icon !== "" ? Qt.resolvedUrl(buttonContainer.modelData.icon) : ""
    
                                    fillMode: Image.PreserveAspectFit
    
                                    smooth: false
    
                                    opacity: appButton.isPressed ? 1.0 : appButton.isSelected || appButton.isHovered ? 1.0 : 0.80
                                }
    
                                DropShadow {
                                    anchors.fill: appIcon
                                    source: appIcon
    
                                    horizontalOffset: 0
                                    verticalOffset: 0
    
                                    radius: 8
                                    samples: 12
    
                                    color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                                    opacity: appButton.isPressed ? 0.55 : appButton.isHovered ? 0.45 : appButton.isSelected ? 0.45 : 0.18
    
                                    transparentBorder: true
                                }
                            }
    
                            // ========================================
                            // APP NAME
                            // ========================================
    
                            Text {
                                id: appText
    
                                anchors.verticalCenter: parent.verticalCenter
    
                                text: buttonContainer.modelData.name
    
                                font.family: "GohuFont 11 Nerd Font Mono"
    
                                font.pixelSize: buttonContainer.modelData.name === "TRUTH SOCIAL" ? 9 : buttonContainer.modelData.icon !== "" ? 10 : 11
    
                                color: appButton.isPressed ? Colors.black : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                                layer.enabled: appButton.isSelected || appButton.isHovered
    
                                layer.effect: DropShadow {
                                    color: Colors.orange
    
                                    opacity: 1.0
    
                                    horizontalOffset: 0
                                    verticalOffset: 0
    
                                    radius: 30
                                    samples: 60
    
                                    transparentBorder: true
                                }
                            }
                        }
    
                        // ============================================
                        // MOUSE
                        // ============================================
    
                        MouseArea {
                            id: appMouse
    
                            anchors.fill: parent
    
                            hoverEnabled: true
    
                            acceptedButtons: Qt.LeftButton
    
                            // Hover may move the visual selector,
                            // but it does NOT activate/open an app.
                            onEntered: {
                                appSelector.keyboardActive = false;
                                appSelector.selectedIndex = buttonContainer.index;
                            }
    
                            // The button itself owns activation.
                            onClicked: function (mouse) {
                                if (mouse.button !== Qt.LeftButton)
                                    return;
    
                                appSelector.selectedIndex = buttonContainer.index;
    
                                appSelector.appActivated(buttonContainer.index);
    
                                console.log("Selected:", buttonContainer.modelData.name);
                            }
                        }
    
                        // ============================================
                        // CLOCK-STYLE CLOSE GLOW
                        // ============================================
    
                        RectangularShadow {
                            anchors.fill: parent
    
                            spread: 3
    
                            color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                            opacity: appButton.isPressed ? 0.60 : appButton.isHovered ? 0.50 : appButton.isSelected ? 0.50 : 0.0
    
                            z: -1
                        }
    
                        // ============================================
                        // CLOCK-STYLE WIDE GLOW
                        // ============================================
    
                        RectangularShadow {
                            anchors.fill: parent
    
                            spread: 10
    
                            color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan
    
                            opacity: appButton.isPressed ? 0.12 : appButton.isHovered ? 0.09 : appButton.isSelected ? 0.09 : 0.0
    
                            z: -2
                        }
                    }
                }
            }
        }
    }

    // Settings stays inside the selector's existing 110 px input region.
    // A wider pop-out must be handled separately: external browser/Discord
    // modes deliberately mask off the content region for pointer pass-through.
    Rectangle {
        id: settingsPage
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            bottom: statusMessage.visible ? statusMessage.top : settingsFooter.top
        }
        color: Colors.black
        visible: appSelector.settingsOpen
        clip: true

        Flickable {
            anchors.fill: parent
            contentWidth: width
            contentHeight: settingsColumn.height + 24
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds
            clip: true

            Column {
                id: settingsColumn
                anchors.top: parent.top
                anchors.topMargin: 12
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.max(1, parent.width - 14)
                spacing: 12

                Text {
                    width: parent.width
                    text: "USER //\nSETTINGS"
                    color: Colors.orange
                    horizontalAlignment: Text.AlignHCenter
                    font.family: "GohuFont 11 Nerd Font Mono"
                    font.pixelSize: 11
                    font.bold: true
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Colors.cyan
                }
                Text {
                    width: parent.width
                    text: "IDENTITIES"
                    color: Colors.cyan
                    font.pixelSize: 10
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Not configured yet"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "BUTTON FAMILIES"
                    color: Colors.cyan
                    font.pixelSize: 9
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Layout manager is next"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "LINKED ACCOUNTS"
                    color: Colors.cyan
                    font.pixelSize: 9
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Not connected to this menu"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "API CREDENTIALS"
                    color: Colors.cyan
                    font.pixelSize: 9
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Existing service setup unchanged"
                    color: Colors.white
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    // This entry point is always visible, independently of app scrolling and
    // status/error text. Its click must never activate a provider app index.
    ActionButton {
        id: settingsFooter
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        width: parent.width - 12
        height: 44
        label: "USER // SETTINGS"
        labelPixelSize: 8
        labelMinimumPixelSize: 8
        contentPadding: 2
        accentColor: Colors.cyan
        selected: appSelector.settingsOpen
        onTriggered: appSelector.settingsOpen = !appSelector.settingsOpen
    }

    // Keep launch errors visible in the selector even when the external
    // browser owns the rest of Social's click-through window.
    Text {
        id: statusMessage
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: settingsFooter.top
        anchors.margins: 6
        visible: appSelector.statusText !== ""
        text: appSelector.statusText
        wrapMode: Text.WrapAnywhere
        font.pixelSize: 9
        color: Colors.orange
        maximumLineCount: 7
        elide: Text.ElideRight
    }

}
