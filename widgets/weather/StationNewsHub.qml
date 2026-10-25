import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import "../../components"
import "StationNewsCatalogPolicy.js" as Catalog

// NEWS domain channel rack. Sources are explicit catalog destinations, NOT
// claims of streaming health. One in-pane viewer; GDELT headlines remain a
// separate REPORTS view and keep their own provider cooldown.
Rectangle {
    id: stationNewsHub
    property bool stationOpen: true
    property string section: "LIVE"
    property bool viewerOpen: false
    property var chosenRecord: null
    // Preserve an explicit muted presentation preference for a future
    // independent player. Audio controls are disabled while playback is off.
    property bool channelMuted: true
    property string notice: ""
    property string creatorFeedStatus: "CHOOSE A SAVED CREATOR"
    property var creatorFeedRows: []
    property string selectedCreatorId: ""
    property string inflightCreatorId: ""
    readonly property bool isReports: section === "REPORTS"
    readonly property string feedBadge: isReports
        ? (reportsLoader.item ? reportsLoader.item.feedBadge : "NEWS // CONNECTING")
        : "NEWS // " + section + " CATALOG"
    readonly property color feedBadgeColor: isReports && reportsLoader.item
        ? reportsLoader.item.feedBadgeColor : Colors.cyan

    readonly property var creatorEntries: creatorAdapter.creatorEntries
    readonly property var visibleItems: {
        const base = Catalog.itemsFor(section);
        if (section !== "CREATORS") return base;
        const saved = creatorEntries;
        const result = base.slice();
        for (let i = 0; i < saved.length && i < 40; ++i) {
            const str = String(saved[i] || "");
            const pipe = str.indexOf("|");
            if (pipe < 0) continue;
            const entry = Catalog.creatorRecord(str.slice(pipe + 1), str.slice(0, pipe));
            if (entry) result.push(entry);
        }
        return result;
    }
    color: Colors.black

    FileView {
        id: savedCreatorFile
        // Storage follows the established FavoritesStore FileView + JsonAdapter
        // pattern. Only the user selecting ADD/REMOVE changes their list.
        path: Quickshell.dataDir + "/weather-news-creators.json"
        watchChanges: true
        onFileChanged: reload()
        onAdapterUpdated: writeAdapter()
        JsonAdapter {
            id: creatorAdapter
            property list<string> creatorEntries: []
        }
    }

    function saveCreator() {
        const result = Catalog.normalizeCreator(creatorLabel.text, creatorId.text);
        if (!result) {
            notice = "USE A NAME AND YOUTUBE CHANNEL ID (UC...) OR /channel/UC... URL";
            return;
        }
        const current = creatorAdapter.creatorEntries.slice();
        for (let i = 0; i < current.length; ++i) {
            if (current[i].indexOf(result.id + "|") === 0) {
                notice = "CREATOR ALREADY SAVED";
                return;
            }
        }
        if (current.length >= 40) {
            notice = "CREATOR LIMIT // 40";
            return;
        }
        current.push(result.id + "|" + result.title);
        creatorAdapter.creatorEntries = current;
        creatorLabel.text = "";
        creatorId.text = "";
        notice = "CREATOR SAVED // SELECT TO VIEW OR CHECK UPLOADS";
    }
    function removeCreator(channelId) {
        const current = creatorAdapter.creatorEntries.slice();
        creatorAdapter.creatorEntries = current.filter(function(v) {
            return String(v).indexOf(channelId + "|") !== 0;
        });
        if (selectedCreatorId === channelId) {
            selectedCreatorId = "";
            creatorFeedRows = [];
            creatorFeedStatus = "CHOOSE A SAVED CREATOR";
        }
        notice = "CREATOR REMOVED";
    }
    function chooseItem(item) {
        if (!item) return;
        chosenRecord = Catalog.toViewerRecord(item);
        if (!chosenRecord) {
            notice = "SOURCE URL UNAVAILABLE";
            return;
        }
        viewerOpen = true;
    }
    function closeViewer() {
        viewerOpen = false;
        chosenRecord = null;
        channelMuted = true;
    }
    function checkUploads(item) {
        if (!item || !item.channelId) return;
        selectedCreatorId = item.channelId;
        if (creatorFeedProcess.running) {
            creatorFeedStatus = "ANOTHER FEED REQUEST IS ALREADY RUNNING";
            return;
        }
        inflightCreatorId = item.channelId;
        creatorFeedRows = [];
        creatorFeedStatus = "REQUESTING UPLOADS // NO AUTOPLAY";
        creatorFeedProcess.running = true;
    }

    Process {
        id: creatorFeedProcess
        // The python helper accepts exactly a YouTube UC... ID. No URL or
        // publisher title is interpolated into shell commands.
        command: ["python3", "-B",
                  Quickshell.configDir + "/scripts/weather/station_youtube_feed.py",
                  stationNewsHub.inflightCreatorId]
        stdout: StdioCollector {
            onStreamFinished: {
                if (stationNewsHub.selectedCreatorId !== stationNewsHub.inflightCreatorId)
                    return;
                try {
                    const result = JSON.parse(String(text || ""));
                    if (!Array.isArray(result.rows))
                        throw new Error("Missing YouTube rows");
                    stationNewsHub.creatorFeedRows = result.rows.slice(0, 15);
                    stationNewsHub.creatorFeedStatus =
                        "UPLOADS RECEIVED // " + stationNewsHub.creatorFeedRows.length;
                } catch (error) {
                    stationNewsHub.creatorFeedStatus = "CREATOR FEED UNAVAILABLE";
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && stationNewsHub.selectedCreatorId === stationNewsHub.inflightCreatorId) {
                stationNewsHub.creatorFeedStatus = "CREATOR FEED UNAVAILABLE";
                stationNewsHub.creatorFeedRows = [];
            }
        }
    }

    Row {
        id: tabBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        height: 33
        spacing: 7
        visible: !stationNewsHub.viewerOpen

        Repeater {
            model: Catalog.sections
            delegate: ActionButton {
                required property string modelData
                width: Math.max(93, Math.floor((tabBar.width - tabBar.spacing * 5) / 6))
                height: 32
                label: modelData
                labelPixelSize: 11
                selected: stationNewsHub.section === modelData
                onClicked: {
                    stationNewsHub.closeViewer();
                    stationNewsHub.section = modelData;
                }
            }
        }
    }

    // Preserve GDELT's independent source request state and internal report
    // viewer without moving its owner into the new channel directory.
    Loader {
        id: reportsLoader
        anchors.top: tabBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        active: stationNewsHub.isReports && stationNewsHub.stationOpen
        visible: active && !stationNewsHub.viewerOpen
        sourceComponent: Component {
            StationDiscovery {
                domain: "news"
                stationOpen: stationNewsHub.stationOpen
            }
        }
    }

    Flickable {
        id: catalogScroll
        anchors.top: tabBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: !stationNewsHub.isReports && !stationNewsHub.viewerOpen
        clip: true
        contentWidth: width
        contentHeight: hubContent.height + 16
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: hubContent
            x: 17
            y: 9
            width: Math.max(0, catalogScroll.width - 34)
            spacing: 10

            Row {
                width: parent.width
                height: 25
                spacing: 12
                GohuText {
                    text: "NEWS // " + stationNewsHub.section
                    color: Colors.cyan
                    font.pixelSize: 20
                }
                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    font.pixelSize: 11
                    text: "CATALOG DESTINATIONS // VIDEO SAFE MODE"
                }
            }
            QuietText {
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 11
                text: stationNewsHub.section === "CONGRESS"
                      ? "OFFICIAL FLOOR AND HEARING WEBCASTS // LIVE ONLY WHEN IN SESSION"
                      : stationNewsHub.section === "COMPARE"
                      ? "COMPARE OUTLETS, NOT A CLAIM OF PERFECT NEUTRALITY // RATINGS OWNED BY PROVIDER"
                      : stationNewsHub.section === "CREATORS"
                      ? "DISCUSSION & USER-SAVED CHANNELS // NOT EDITORIAL NEWS CERTIFICATION"
                      : stationNewsHub.section === "SATIRE"
                      ? "PARODY AND FICTIONAL NEWS // NOT VERIFIED CURRENT EVENTS"
                      : "SOURCE PAGES REGISTERED // VIDEO ENGINE TEMPORARILY DISABLED"
            }

            Repeater {
                model: stationNewsHub.visibleItems
                delegate: Rectangle {
                    required property var modelData
                    width: hubContent.width
                    height: 76
                    color: Colors.dark
                    border.width: 1
                    border.color: sourceMouse.containsMouse ? Colors.yellow : Colors.cyan

                    Column {
                        anchors.left: parent.left
                        anchors.right: controls.left
                        anchors.top: parent.top
                        anchors.margins: 9
                        spacing: 5
                        GohuText {
                            width: parent.width
                            text: modelData.title
                            color: Colors.white
                            elide: Text.ElideRight
                            font.pixelSize: 14
                        }
                        SecondaryText {
                            width: parent.width
                            text: modelData.detail
                            elide: Text.ElideRight
                            font.pixelSize: 10
                        }
                        QuietText {
                            width: parent.width
                            text: modelData.access
                            elide: Text.ElideRight
                            font.pixelSize: 10
                        }
                    }
                    MouseArea {
                        id: sourceMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: stationNewsHub.chooseItem(modelData)
                    }
                    Row {
                        id: controls
                        anchors.right: parent.right
                        anchors.rightMargin: 9
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        z: 2
                        ActionButton {
                            width: 139
                            height: 28
                            label: "WATCH IN STATION"
                            labelPixelSize: 10
                            onClicked: stationNewsHub.chooseItem(modelData)
                        }
                        ActionButton {
                            width: 90
                            height: 28
                            label: "MUTE: ON"
                            labelPixelSize: 10
                            available: false
                        }
                        ActionButton {
                            width: 82
                            height: 28
                            visible: !!modelData.channelId
                            label: "UPLOADS"
                            labelPixelSize: 10
                            onClicked: stationNewsHub.checkUploads(modelData)
                        }
                        ActionButton {
                            width: 28
                            height: 28
                            visible: !!modelData.channelId
                            label: "×"
                            destructive: true
                            onClicked: stationNewsHub.removeCreator(modelData.channelId)
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 9
                visible: stationNewsHub.section === "CREATORS"

                StationSectionDivider {
                    width: parent.width
                    title: "YOUR YOUTUBE CHANNELS // SAVED LOCALLY"
                }
                TextField {
                    id: creatorLabel
                    width: parent.width
                    height: 34
                    font.pixelSize: 12
                    color: Colors.orange
                    placeholderText: "CHANNEL NAME // e.g. history creator"
                    background: Rectangle {
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                    }
                }
                TextField {
                    id: creatorId
                    width: parent.width
                    height: 34
                    font.pixelSize: 12
                    color: Colors.orange
                    placeholderText: "YOUTUBE CHANNEL ID (UC...) OR /channel/UC... URL"
                    background: Rectangle {
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                    }
                }
                ActionButton {
                    width: 155
                    height: 31
                    label: "ADD CREATOR"
                    labelPixelSize: 12
                    onClicked: stationNewsHub.saveCreator()
                }
                QuietText {
                    width: parent.width
                    text: stationNewsHub.notice !== "" ? stationNewsHub.notice
                          : "ONLY CANONICAL UC CHANNEL IDS FOR NOW // @HANDLE RESOLUTION LATER"
                    wrapMode: Text.WordWrap
                }
                StationSectionDivider {
                    width: parent.width
                    title: "RECENT UPLOADS // SELECT UPLOADS ABOVE TO CHECK"
                }
                QuietText {
                    width: parent.width
                    text: stationNewsHub.creatorFeedStatus
                    color: Colors.white
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: stationNewsHub.creatorFeedRows
                    delegate: ActionButton {
                        required property var modelData
                        width: hubContent.width
                        height: 43
                        labelPixelSize: 11
                        labelElide: Text.ElideRight
                        label: String(modelData.title || "UNTITLED VIDEO")
                        onClicked: stationNewsHub.chooseItem({
                            title: modelData.title,
                            source: "YOUTUBE // LATEST UPLOAD",
                            url: modelData.url,
                            access: String(modelData.time || "PUBLISHED TIME UNAVAILABLE"),
                            kind: "channel",
                            detail: "Creator feed record // open video in internal viewer"
                        })
                    }
                }
            }
        }
    }
    NeonScrollBar {
        flickable: catalogScroll
        handleStyle: "star"
        geometryHost: stationNewsHub
        visible: catalogScroll.visible && scrollable
    }
    Loader {
        anchors.fill: parent
        active: stationNewsHub.viewerOpen
        visible: active
        z: 5
        sourceComponent: Component {
            StationChannelScreen {
                selectedRecord: stationNewsHub.chosenRecord
                muted: stationNewsHub.channelMuted
                onCloseRequested: stationNewsHub.closeViewer()
            }
        }
    }
    onStationOpenChanged: { if (!stationOpen) closeViewer(); }
}
