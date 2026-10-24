import QtQuick
import "../components"

// An opt-in OSIRIS globe INSIDE FinanceW. No browser launch or shell Process.
// Lazy QtWebEngine import is isolated in FinanceOsirisWebView.qml so Quickshell
// remains loadable when QtWebEngine is unavailable.
Item {
    id: osiris
    property bool shown: false
    property bool loadRequested: false

    GohuText {
        id: header
        anchors.top: parent.top
        anchors.topMargin: 9
        anchors.left: parent.left
        anchors.right: toggleGlobe.left
        anchors.rightMargin: 8
        text: "OSIRIS // GLOBAL INTEL"
        font.pixelSize: 13
        font.bold: true
        color: Colors.orange
        elide: Text.ElideRight
    }

    ActionButton {
        id: toggleGlobe
        anchors.top: parent.top
        anchors.topMargin: 5
        anchors.right: parent.right
        width: 91
        height: 29
        label: osiris.loadRequested ? "STOP GLOBE" : "LOAD GLOBE"
        labelPixelSize: 9
        accentColor: osiris.loadRequested ? Colors.red : Colors.cyan
        onLeftClicked: osiris.loadRequested = !osiris.loadRequested
    }

    GohuText {
        id: sourceLabel
        anchors.top: header.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.right: parent.right
        text: osiris.loadRequested
              ? "REMOTE OSIRIS // MAPLIBRE WEBGL // VIEWER ONLY"
              : "OSIRIS SOURCE // https://osirisai.live/"
        font.pixelSize: 9
        color: Colors.cyan
        textFormat: Text.PlainText
        elide: Text.ElideRight
    }

    Rectangle {
        id: mapFrame
        anchors.top: sourceLabel.bottom
        anchors.topMargin: 7
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top
        anchors.bottomMargin: 6
        color: Colors.black
        border.color: Colors.cyan
        border.width: 1
        clip: true

        Loader {
            id: globeLoader
            anchors.fill: parent
            anchors.margins: 2
            // Explicit user action only. Unload on tool-switch to avoid
            // retaining an unseen GPU-heavy globe. Resizes never destroy it.
            active: osiris.shown && osiris.loadRequested
            source: Qt.resolvedUrl("FinanceOsirisWebView.qml")
        }

        Column {
            anchors.centerIn: parent
            width: Math.max(0, parent.width - 26)
            spacing: 10
            visible: !globeLoader.active || globeLoader.status === Loader.Error
                     || globeLoader.status === Loader.Loading

            GohuText {
                width: parent.width
                text: globeLoader.status === Loader.Error
                    ? "WEB RENDERER UNAVAILABLE"
                    : globeLoader.status === Loader.Loading
                    ? "INITIALIZING GLOBE..."
                    : "OSIRIS // READY TO LOAD"
                font.pixelSize: 13
                color: globeLoader.status === Loader.Error ? Colors.red : Colors.magenta
                horizontalAlignment: Text.AlignHCenter
            }
            GohuText {
                width: parent.width
                text: globeLoader.status === Loader.Error
                    ? "QtWebEngine could not load. FinanceW remains intact."
                    : "Loads the real OSIRIS globe here, not in Brave."
                font.pixelSize: 10
                color: Colors.white
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    GohuText {
        id: footer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 28
        font.pixelSize: 9
        color: Colors.orange
        textFormat: Text.PlainText
        wrapMode: Text.WordWrap
        text: "PUBLIC REMOTE VIEW // NO ACCOUNT OR AI KEYS // STOP TO FREE GPU"
    }
}
