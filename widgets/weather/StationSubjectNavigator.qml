import QtQuick
import "../../components"
import "StationSubjectNavigationPolicy.js" as SubjectRoutes
import "StationSubjectNavigationPreviewPolicy.js" as PreviewRoutes
import "StationWeatherSubjectPanelPolicy.js" as WeatherPanelPolicy
import "StationCosmosSubjectPanelPolicy.js" as CosmosPanelPolicy
import "StationEarthSubjectPanelPolicy.js" as EarthPanelPolicy
import "StationMediaSubjectPanelPolicy.js" as MediaPanelPolicy
import "StationMagickSubjectPanelPolicy.js" as MagickPanelPolicy

// M1 bounded visual browser. Source panels remain in their original classic
// QML pages; no new fetches, persistence, or fake submode content.
Rectangle {
    id: browser
    color: Colors.black

    property string currentPath: "weather"
    property var lastSubjectPaths: ({})
    property int navigationCursor: 0
    // Existing Weather Station sources supplied from the single owning root.
    property var weatherService: null
    property var spaceService: null
    property var nwsAlertSource: null
    property var historyService: null
    property var seismicSource: null
    property var lightningSource: null
    property var riverSource: null
    property var persistentCacheStore: null
    property var liveHistoryStore: null
    property var eventArchiveStore: null
    property var dossierArchiveStore: null
    property real runtimeNowMs: Date.now()
    readonly property string liveWeatherKind:
        WeatherPanelPolicy.kindForRoute(currentPath)
    readonly property string liveCosmosKind:
        CosmosPanelPolicy.kindForRoute(currentPath)
    readonly property string liveEarthKind:
        EarthPanelPolicy.kindForRoute(currentPath)
    readonly property string liveMediaKind:
        MediaPanelPolicy.kindForRoute(currentPath)
    readonly property string liveMagickKind:
        MagickPanelPolicy.kindForRoute(currentPath)

    readonly property var currentRoute: SubjectRoutes.findRoute(currentPath)
    readonly property var childrenRoutes: SubjectRoutes.childrenOf(currentPath)
    readonly property var pathCrumbs: SubjectRoutes.breadcrumbs(currentPath)
    readonly property var classicSources:
        PreviewRoutes.sourcePagesForPath(currentPath, SubjectRoutes.PANELS)

    signal legacyPageRequested(string pageId)
    signal newsMapRequested(var payload)

    function chooseRoute(path) {
        const candidate = SubjectRoutes.findRoute(path);
        if (!candidate)
            return false;
        currentPath = candidate.path;
        const updated = Object.assign({}, lastSubjectPaths);
        updated[candidate.subject] = candidate.path;
        lastSubjectPaths = updated;
        navigationCursor = 0;
        routeScroll.contentY = 0;
        return true;
    }

    function selectSubject(subjectId) {
        const subject = SubjectRoutes.findRoute(subjectId);
        if (!subject || subject.depth !== 0)
            return false;
        const remembered = lastSubjectPaths[subjectId];
        const valid = SubjectRoutes.findRoute(remembered);
        return chooseRoute(valid && valid.subject === subjectId
                           ? remembered : subjectId);
    }

    function cycleSubjects(direction) {
        const now = currentRoute ? currentRoute.subject : "weather";
        const subjects = SubjectRoutes.SUBJECTS;
        const index = subjects.findIndex(function(x) {return x.id === now;});
        const step = Number(direction) < 0 ? -1 : 1;
        const next = (Math.max(0, index) + step + subjects.length) % subjects.length;
        selectSubject(subjects[next].id);
    }

    function moveCursor(direction) {
        const count = childrenRoutes.length;
        if (count === 0)
            return;
        const step = Number(direction) < 0 ? -1 : 1;
        navigationCursor = (navigationCursor + step + count) % count;
    }

    function activateCursor() {
        if (childrenRoutes.length > 0)
            chooseRoute(childrenRoutes[navigationCursor].path);
    }

    function goUp() {
        if (pathCrumbs.length > 1)
            chooseRoute(pathCrumbs[pathCrumbs.length - 2].path);
    }

    Item {
        id: navigationHeading
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        height: 39

        GohuText {
            id: headingText
            anchors.top: parent.top
            anchors.left: parent.left
            text: browser.liveWeatherKind !== ""
                  ? "WEATHER // SUBJECT VIEW"
                  : browser.liveCosmosKind !== ""
                    ? "COSMOS // SUBJECT VIEW"
                    : browser.liveEarthKind !== ""
                      ? "EARTH // SUBJECT VIEW"
                    : browser.liveMediaKind !== ""
                      ? "MEDIA // SUBJECT VIEW"
                    : browser.liveMagickKind !== ""
                      ? "MAGICK // INTERPRETIVE REFERENCE"
                    : "SUBJECTS // NAVIGATION PREVIEW"
            color: Colors.magenta
            font.pixelSize: 17
        }

    }

    Row {
        id: breadcrumbRow
        anchors.top: navigationHeading.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 6
        height: 32

        ActionButton {
            width: 56
            height: 30
            label: "UP"
            labelPixelSize: 11
            available: browser.pathCrumbs.length > 1
            onClicked: browser.goUp()
        }

        Repeater {
            model: browser.pathCrumbs
            delegate: ModeButton {
                required property var modelData
                width: Math.min(145, Math.max(74, modelData.label.length * 9))
                height: 30
                textOnly: true
                labelFontSize: 10
                selected: modelData.path === browser.currentPath
                onTriggered: browser.chooseRoute(modelData.path)
            }
        }
    }

    Rectangle {
        anchors.top: breadcrumbRow.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        height: 2
        color: Colors.cyan
    }

    Flickable {
        id: routeScroll
        anchors.top: breadcrumbRow.bottom
        anchors.topMargin: 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        clip: true
        visible: browser.liveWeatherKind === ""
                 && browser.liveCosmosKind === ""
                 && browser.liveEarthKind === ""
                 && browser.liveMediaKind === ""
                 && browser.liveMagickKind === ""
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, contentColumn.implicitHeight + 12)

        Column {
            id: contentColumn
            width: routeScroll.width
            spacing: 9

            GohuText {
                text: browser.currentRoute
                      ? browser.currentRoute.label : "UNKNOWN ROUTE"
                font.pixelSize: 22
                color: Colors.orange
            }

            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                text: browser.childrenRoutes.length > 0
                      ? "SUBMODES // SELECT A SUBJECT AREA TO OPEN ITS DEEPER BUCKETS"
                      : "ROUTE RESERVED // ITS CONTENT HAS NOT BEEN MOVED FROM THE CLASSIC PAGES"
            }

            Repeater {
                model: browser.childrenRoutes
                delegate: ModeButton {
                    required property int index
                    required property var modelData
                    width: contentColumn.width
                    height: 39
                    horizontalContent: true
                    bordered: false
                    iconText: modelData.group ? "▸" : "·"
                    labelText: modelData.label
                    labelFontSize: 13
                    iconFontSize: 14
                    keyboardActive: browser.visible
                    keyboardSelected: index === browser.navigationCursor
                    onPointerMoved: browser.navigationCursor = index
                    onTriggered: browser.chooseRoute(modelData.path)
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }

            GohuText {
                text: "CURRENT SOURCE PAGES // CLASSIC"
                font.pixelSize: 13
                color: Colors.cyan
            }

            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "OPEN A CLASSIC PAGE TO USE ITS EXISTING CONTROLS. THE NEW ROUTE TREE DOES NOT YET RELOCATE OR FILTER THAT PAGE."
                font.pixelSize: 10
            }

            Repeater {
                model: browser.classicSources
                delegate: ActionButton {
                    required property var modelData
                    width: contentColumn.width
                    height: 32
                    label: "OPEN " + modelData.label
                           + " // " + modelData.panels + " MAPPED"
                    labelPixelSize: 11
                    onClicked: browser.legacyPageRequested(modelData.id)
                }
            }

            QuietText {
                width: parent.width
                visible: browser.classicSources.length === 0
                wrapMode: Text.WordWrap
                text: browser.currentRoute
                      && browser.currentRoute.subject === "magick"
                      ? "MAGICK IS A PLANNED INTERPRETIVE SUBJECT. NO ASTROLOGY OR MAGICK CONTENT IS BEING CLAIMED AS OPERATIONAL."
                      : "NO CLASSIC PAGE IS DIRECTLY MAPPED TO THIS ROUTE YET."
            }
        }
    }

    // Selectors for deeper reserved river subroutes remain available even
    // while the parent river instrument is displayed.
    Flickable {
        id: liveChildren
        visible: (browser.liveWeatherKind !== ""
                  || browser.liveCosmosKind !== ""
                  || browser.liveEarthKind !== ""
                  || browser.liveMediaKind !== ""
                  || browser.liveMagickKind !== "")
                 && browser.childrenRoutes.length > 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: breadcrumbRow.bottom
        anchors.topMargin: 6
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        height: visible ? 34 : 0
        contentHeight: height
        contentWidth: Math.max(width, liveChildRow.implicitWidth)
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Row {
            id: liveChildRow
            spacing: 7
            Repeater {
                model: browser.childrenRoutes
                delegate: ModeButton {
                    required property var modelData
                    height: 31
                    width: Math.max(100, modelData.label.length * 9 + 14)
                    labelFontSize: 11
                    textOnly: true
                    onTriggered: browser.chooseRoute(modelData.path)
                }
            }
        }
    }

    StationWeatherSubjectPane {
        id: weatherLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveWeatherKind !== ""
        subjectRoute: browser.currentPath
        weatherService: browser.weatherService
        nwsAlertSource: browser.nwsAlertSource
        historyService: browser.historyService
        seismicSource: browser.seismicSource
        lightningSource: browser.lightningSource
        riverSource: browser.riverSource
        persistentCacheStore: browser.persistentCacheStore
        liveHistoryStore: browser.liveHistoryStore
        runtimeNowMs: browser.runtimeNowMs
    }

    StationCosmosSubjectPane {
        id: cosmosLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveCosmosKind !== ""
        subjectRoute: browser.currentPath
        weatherService: browser.weatherService
        spaceService: browser.spaceService
        liveHistoryStore: browser.liveHistoryStore
        runtimeNowMs: browser.runtimeNowMs
    }

    StationEarthSubjectPane {
        id: earthLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveEarthKind !== ""
        subjectRoute: browser.currentPath
        seismicSource: browser.seismicSource
        lightningSource: browser.lightningSource
        riverSource: browser.riverSource
        weatherService: browser.weatherService
        persistentCacheStore: browser.persistentCacheStore
        eventArchiveStore: browser.eventArchiveStore
        dossierArchiveStore: browser.dossierArchiveStore
        runtimeNowMs: browser.runtimeNowMs
    }

    StationMediaSubjectPane {
        id: mediaLivePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveMediaKind !== ""
        subjectRoute: browser.currentPath
        runtimeNowMs: browser.runtimeNowMs
        onNewsMapRequested: function(payload) {
            browser.newsMapRequested(payload);
        }
    }

    StationMagickSubjectPane {
        id: magickReferencePane
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: liveChildren.visible
                     ? liveChildren.bottom : breadcrumbRow.bottom
        anchors.topMargin: liveChildren.visible ? 6 : 14
        anchors.bottom: previewNote.top
        anchors.bottomMargin: 6
        visible: browser.visible && browser.liveMagickKind !== ""
        subjectRoute: browser.currentPath
        weatherService: browser.weatherService
        runtimeNowMs: browser.runtimeNowMs
    }

    // Post-Apollo shared star indicator; no new scroll behavior is invented.
    NeonScrollBar {
        flickable: routeScroll
        geometryMode: "viewport"
        handleStyle: "star"
        visible: browser.visible && browser.liveWeatherKind === ""
                 && browser.liveCosmosKind === ""
                 && browser.liveEarthKind === ""
                 && browser.liveMediaKind === ""
                 && browser.liveMagickKind === ""
                 && routeScroll.contentHeight > routeScroll.height + 1
    }

    QuietText {
        id: previewNote
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.bottomMargin: 10
        height: 23
        font.pixelSize: 10
        color: Colors.yellow
        text: browser.liveWeatherKind !== ""
              ? "WEATHER // EXISTING SOURCE PANELS // SAME COLLECTORS"
              : browser.liveCosmosKind !== ""
                ? "COSMOS // EXISTING SKY + SPACE PANELS // SAME COLLECTORS"
                : browser.liveEarthKind !== ""
                  ? "EARTH // SHARED MAP + EVENT DOSSIERS // ORIGINAL STORES"
                : browser.liveMediaKind !== ""
                  ? "MEDIA // GDELT + PUBLISHER CATALOG + HI-FI RADIO // ORIGINAL SOURCES"
                : browser.liveMagickKind !== ""
                  ? "MAGICK // ASTRONOMICAL REFERENCE ONLY // NO CALCULATED READINGS"
                : "SPEC-ONLY SUBJECTS // CLASSIC PAGES REMAIN CANONICAL UNTIL PANEL MIGRATION"
    }
}
