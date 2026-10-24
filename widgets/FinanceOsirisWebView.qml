import QtQuick
import QtWebEngine

// Optional, dynamically loaded WebEngine pilot. This file is NOT imported by
// FinanceW or the normal Market pane during Quickshell startup.
// QtWebEngineQuick initialization and WebGL must be checked on the user's
// actual Quickshell build before declaring the globe runtime supported.
WebEngineView {
    id: osirisWeb
    anchors.fill: parent
    backgroundColor: "#090916"
    audioMuted: true
    url: "https://osirisai.live/"

    settings.webGLEnabled: true
    settings.javascriptEnabled: true
    settings.localContentCanAccessRemoteUrls: false
    settings.unknownUrlSchemePolicy: WebEngineSettings.DisallowUnknownUrlSchemes

    // This viewer is confined to OSIRIS. It cannot silently navigate to
    // unrelated websites when the user is investigating inside FinanceW.
    onNavigationRequested: function(request) {
        if (!request.isMainFrame)
            return;
        const target = String(request.url);
        if (target === "https://osirisai.live/"
                || target.startsWith("https://osirisai.live/")
                || target === "https://www.osirisai.live/"
                || target.startsWith("https://www.osirisai.live/"))
            return;
        request.reject();
    }

    // No openIn() call: popups are not granted a separate view/window.
    onNewWindowRequested: function(request) {}

    // OSIRIS can request microphone, camera, or geolocation. These
    // permissions are not automatically granted to FinanceW's viewer.
    onPermissionRequested: function(permission) {
        permission.deny();
    }
}
