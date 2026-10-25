import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"

// Truthful provider access surface. Does NOT render invented personal chats.
// An official desktop client may work even if its native adapter is UNSUPPORTED.
Rectangle {
    id: panel
    property int serviceIndex: -1
    property string backendMode: "UNSUPPORTED"
    property string backendDetail: ""
    signal browserRequested(string serviceId)
    signal desktopDocked(string serviceId)

    readonly property string serviceId:
        serviceIndex === 14 ? "whatsapp" :
        serviceIndex === 15 ? "messenger" :
        serviceIndex === 26 ? "signal" :
        serviceIndex === 27 ? "wechat" :
        serviceIndex === 28 ? "line" :
        serviceIndex === 29 ? "viber" :
        serviceIndex === 30 ? "kakaotalk" :
        serviceIndex === 31 ? "bereal" : ""
    readonly property string serviceTitle: serviceId.toUpperCase()
    readonly property bool desktopSupported:
        serviceId === "signal" || serviceId === "wechat" || serviceId === "viber"
    readonly property bool webSupported:
        serviceId === "whatsapp" || serviceId === "messenger"
    readonly property string clientGuide:
        serviceId === "signal" ? "Signal Desktop: link from the Signal app on your phone. Install the official Linux client first." :
        serviceId === "viber" ? "Viber Desktop: requires an active Viber phone account. Install the Linux client first." :
        serviceId === "wechat" ? "WeChat: install the official Linux client. Device linking takes place in the provider application." :
        serviceId === "line" ? "LINE on Linux uses LINE's official Chrome extension. It must be installed and authorized in Chrome separately." :
        serviceId === "kakaotalk" ? "No official Linux desktop client or supported personal-message adapter verified." :
        serviceId === "bereal" ? "Mobile-only connection; no supported Post-Apollo desktop adapter verified." :
        serviceId === "whatsapp" ? "WhatsApp Web lets you use your personal account through the official website. The native API remains unsupported." :
        serviceId === "messenger" ? "Messenger personal chats are available through Facebook Messages in a browser, not the old standalone app." : ""

    property bool desktopAvailable: false
    property bool windowAvailable: false
    property string launchNotice: ""
    property string dockNotice: ""
    property int windowProbeAttempts: 0

    function probeWindow() {
        if (!visible || !desktopSupported || windowProcess.running)
            return;
        windowProcess.requestService = serviceId;
        windowProcess.command = ["python3", Quickshell.shellPath("services/messaging/DesktopWindowBridge.py"),
                                 "probe", serviceId];
        windowProcess.running = true;
    }

    function dockWindow() {
        if (!visible || !desktopSupported || !windowAvailable || windowProcess.running)
            return;
        windowRetryTimer.stop();
        dockNotice = "Docking identified provider window...";
        windowProcess.requestService = serviceId;
        windowProcess.command = ["python3", Quickshell.shellPath("services/messaging/DesktopWindowBridge.py"),
                                 "dock", serviceId];
        windowProcess.running = true;
    }
    color: Colors.black
    border.color: Colors.cyan
    border.width: 1
    clip: true

    function probeDesktop() {
        if (!visible || !desktopSupported || desktopProcess.running)
            return;
        desktopAvailable = false;
        desktopProcess.requestService = serviceId;
        desktopProcess.command = ["python3", Quickshell.shellPath("services/messaging/DesktopServiceLauncher.py"),
                                  "probe", serviceId];
        desktopProcess.running = true;
    }

    function openDesktop() {
        if (!visible || !desktopSupported || !desktopAvailable || desktopProcess.running)
            return;
        launchNotice = "Requesting provider desktop window...";
        desktopProcess.requestService = serviceId;
        desktopProcess.command = ["python3", Quickshell.shellPath("services/messaging/DesktopServiceLauncher.py"),
                                  "open", serviceId];
        desktopProcess.running = true;
    }

    onVisibleChanged: {
        if (visible) {
            launchNotice = "";
            dockNotice = "";
            probeDesktop();
            probeWindow();
        }
    }
    onServiceIdChanged: {
        launchNotice = "";
        dockNotice = "";
        windowAvailable = false;
        windowRetryTimer.stop();
        desktopAvailable = false;
        probeDesktop();
        probeWindow();
    }

    Process {
        id: desktopProcess
        property string requestService: ""
        stdout: StdioCollector {
            onStreamFinished: {
                if (!panel.visible)
                    return;
                try {
                    const result = JSON.parse(String(text || ""));
                    if (result.serviceId !== panel.serviceId)
                        return;
                    panel.desktopAvailable = result.desktopInstalled === true;
                    if (result.launched === true || result.desktopInstalled === false)
                        panel.launchNotice = String(result.detail || "");
                    if (result.launched === true) {
                        panel.windowProbeAttempts = 0;
                        windowRetryTimer.start();
                    }
                } catch (e) {
                    panel.launchNotice = "Desktop status could not be checked";
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (!panel.visible)
                return;
            if (requestService !== panel.serviceId) {
                // The selection changed during a previous provider's probe.
                Qt.callLater(function() { panel.probeDesktop(); });
                return;
            }
            if (exitCode !== 0)
                panel.launchNotice = "Provider desktop launcher unavailable";
        }
    }

    Process {
        id: windowProcess
        property string requestService: ""
        stdout: StdioCollector {
            onStreamFinished: {
                if (!panel.visible)
                    return;
                try {
                    const result = JSON.parse(String(text || ""));
                    if (result.serviceId !== panel.serviceId)
                        return;
                    panel.windowAvailable = result.windowAvailable === true
                                             && result.ambiguous !== true;
                    panel.dockNotice = String(result.detail || "");
                    if (result.action === "dock" && result.changed === true
                            && result.docked === true) {
                        panel.desktopDocked(panel.serviceId);
                    }
                    if (panel.windowAvailable)
                        windowRetryTimer.stop();
                } catch (e) {
                    panel.windowAvailable = false;
                    panel.dockNotice = "Could not identify a safe provider window";
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (!panel.visible)
                return;
            if (requestService !== panel.serviceId) {
                Qt.callLater(function() { panel.probeWindow(); });
            } else if (exitCode !== 0) {
                panel.dockNotice = "Sway provider window check unavailable";
            }
        }
    }

    Timer {
        id: windowRetryTimer
        interval: 850
        repeat: true
        running: false
        onTriggered: {
            if (!panel.visible || !panel.desktopSupported
                    || panel.windowAvailable || panel.windowProbeAttempts >= 8) {
                stop();
                return;
            }
            panel.windowProbeAttempts += 1;
            panel.probeWindow();
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 20
        contentWidth: width
        contentHeight: body.implicitHeight
        clip: true
        flickableDirection: Flickable.VerticalFlick

        Column {
            id: body
            width: parent.width
            spacing: 16

            Text {
                text: panel.serviceTitle + " // PROVIDER ACCESS"
                color: Colors.orange
                font.family: "GohuFont 11 Nerd Font Mono"
                font.bold: true
                font.pixelSize: 19
                width: parent.width
                wrapMode: Text.WordWrap
            }
            Text {
                text: "NATIVE PERSONAL-MESSAGE BACKEND // " + panel.backendMode
                color: Colors.cyan
                width: parent.width
                font.pixelSize: 13
                wrapMode: Text.WordWrap
            }
            Text {
                text: panel.backendDetail
                color: Colors.white
                width: parent.width
                font.pixelSize: 13
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }
            Text {
                text: panel.clientGuide
                color: Colors.white
                width: parent.width
                font.pixelSize: 14
                wrapMode: Text.WordWrap
            }
            Rectangle {
                id: desktopButton
                width: Math.min(parent.width, 310)
                height: 44
                visible: panel.desktopSupported
                opacity: panel.desktopAvailable ? 1 : 0.6
                color: Colors.dark
                border.color: Colors.orange
                Text {
                    anchors.centerIn: parent
                    text: panel.desktopAvailable ? "OPEN DESKTOP CLIENT" : "DESKTOP CLIENT NOT FOUND"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: panel.desktopAvailable
                    onClicked: panel.openDesktop()
                }
            }
            Rectangle {
                id: webButton
                width: Math.min(parent.width, 310)
                height: 44
                visible: panel.webSupported
                color: Colors.dark
                border.color: Colors.orange
                Text {
                    anchors.centerIn: parent
                    text: "OPEN OFFICIAL WEB MESSAGING"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: panel.browserRequested(panel.serviceId)
                }
            }
            Rectangle {
                width: Math.min(parent.width, 310)
                height: 44
                visible: panel.desktopSupported
                opacity: panel.windowAvailable ? 1 : 0.6
                color: Colors.dark
                border.color: Colors.orange
                Text {
                    anchors.centerIn: parent
                    text: panel.windowAvailable ? "DOCK DESKTOP WINDOW IN SOCIAL"
                                                : "WINDOW NOT YET IDENTIFIED"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: panel.windowAvailable
                    onClicked: panel.dockWindow()
                }
            }
            Rectangle {
                width: Math.min(parent.width, 310)
                height: 36
                visible: panel.desktopSupported
                color: Colors.dark
                border.color: Colors.cyan
                Text {
                    anchors.centerIn: parent
                    text: "CHECK FOR DESKTOP WINDOW"
                    color: Colors.cyan
                    font.pixelSize: 12
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: panel.probeWindow()
                }
            }
            Text {
                text: panel.dockNotice
                visible: panel.dockNotice !== ""
                color: Colors.cyan
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 12
            }
            Text {
                text: panel.launchNotice
                visible: panel.launchNotice !== ""
                color: Colors.cyan
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 12
            }
            Text {
                text: "Desktop/web access stays within the provider's own application. It is not native message data and does not mean your account is authenticated."
                color: Colors.cyan
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 12
            }
        }
    }
}
