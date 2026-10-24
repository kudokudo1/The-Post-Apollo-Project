import QtQuick
import QtWebEngine
import "StationViewerPolicy.js" as ViewerPolicy

// OPTIONAL WEB RENDERER. Loaded dynamically only after the operator clicks
// READ ARTICLE. No QtWebEngine import is added to the Weather Station startup
// path, since actual Quickshell/WebEngine compatibility remains unverified.
WebEngineView {
    id: newsWeb

    property string articleUrl: ""
    // Audio stays muted until the operator explicitly enables it for the
    // selected source. The viewer host only permits one active web instance.
    property bool audioAllowed: false
    property string loadState: "WAITING"
    property bool blockedNavigation: false

    anchors.fill: parent
    backgroundColor: "#1B0623"
    audioMuted: !newsWeb.audioAllowed
    url: articleUrl

    settings.javascriptEnabled: true
    settings.localContentCanAccessRemoteUrls: false
    settings.unknownUrlSchemePolicy: WebEngineSettings.DisallowUnknownUrlSchemes

    // Allow main-frame navigation only within the selected publisher host.
    // Relative links and ordinary in-page assets remain handled by WebEngine;
    // redirects to other websites, protocols and popups are refused.
    onNavigationRequested: function(request) {
        if (!request.isMainFrame) return;
        const target = ViewerPolicy.safeArticleUrl(String(request.url));
        if (!target
                || ViewerPolicy.articleHost(target)
                   !== ViewerPolicy.articleHost(newsWeb.articleUrl)) {
            newsWeb.blockedNavigation = true;
            request.reject();
        }
    }

    onLoadingChanged: function(loadRequest) {
        if (loadRequest.status === WebEngineLoadRequest.LoadSucceededStatus)
            loadState = "READY";
        else if (loadRequest.status === WebEngineLoadRequest.LoadFailedStatus)
            loadState = "FAILED";
        else
            loadState = "LOADING";
    }

    // No site can create surprise external windows or acquire capabilities.
    onNewWindowRequested: function(request) {}
    onPermissionRequested: function(permission) { permission.deny(); }
}
