import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "../../services/media" as MediaServices
import "StationRadioMemoryPolicy.js" as RadioMemory
import "StationMediaSubjectPanelPolicy.js" as MediaPanelPolicy

// A news-first RADIO surface using the SAME private Hi-Fi controller and
// guarded MPD relay. No second Radio Browser fetcher, MPD or direct stream URLs.
// RADIO directory search / SELECT / LOAD never autoplays. Transport is shared.
Rectangle {
    id: stationRadio

    property bool stationOpen: true
    property string subjectRoute: ""
    readonly property bool compactOverview: subjectRoute === "media/overview"
    function sectionVisible(group) {
        return MediaPanelPolicy.radioGroupVisible(subjectRoute,group);
    }
    onSubjectRouteChanged: {
        if (radioScroll)
            radioScroll.contentY = 0;
    }
    property int browseIndex: 0
    property int presetIndex: 0
    property string notice: "NEWS FIRST // CHOOSE A STATION"
    property string lastLoadRequestedId: ""
    property bool initialSearchSent: false
    property string recallTargetId: ""
    property string recallTargetTitle: ""
    property int recallAttempts: 0
    property string lastRememberedLoadedId: ""

    // U5c: status is established by this existing FileView, never by CPU++.
    // An unopened/error memory file is not an authoritative empty list.
    property string radioMemoryState: "loading"
    readonly property var favoriteItems:
        RadioMemory.decodeList(radioMemoryAdapter.favoriteEntries, 10)
    readonly property var recentItems:
        RadioMemory.decodeList(radioMemoryAdapter.recentEntries, 8)

    // Read-only boundary: copy public station identity/title only. No FileView
    // QObject, stream URL, playback controller or mutation callback escapes.
    readonly property var favoritesBridgeSnapshot: {
        const state=stationRadio.radioMemoryState;
        if (state!=="ready") return ({state:state,favorites:[],recents:[]});
        function copy(items) {
            return items.map(function(item) {
                return ({
                    ref:{source:item.ref.source,kind:item.ref.kind,id:item.ref.id},
                    title:item.title
                });
            });
        }
        return ({state:"ready",
                 favorites:copy(stationRadio.favoriteItems),
                 recents:copy(stationRadio.recentItems)});
    }

    readonly property var presets: [
        {name: "NEWS", query: "tag:news"},
        {name: "TALK", query: "tag:talk"},
        {name: "PUBLIC", query: "tag:public"},
        {name: "WEATHER", query: "tag:weather"},
        {name: "US RADIO", query: "country:US"},
        {name: "ALL RADIO", query: ""}
    ]
    readonly property var browseItems: controller.browse
        && Array.isArray(controller.browse.items)
        ? controller.browse.items : []
    readonly property var highlightedItem:
        browseIndex >= 0 && browseIndex < browseItems.length
        ? browseItems[browseIndex] : null
    readonly property bool highlightedFavorite:
        RadioMemory.isFavorite(
            radioMemoryAdapter.favoriteEntries,
            highlightedItem
        )
    readonly property var selectedRef: controller.selection
    readonly property var loadedMedia: controller.loaded
    readonly property bool loadedIsRadio:
        !!(loadedMedia && loadedMedia.ref
           && loadedMedia.ref.source === "radio-browser")
    readonly property bool loadMatchesView:
        loadedIsRadio && lastLoadRequestedId !== ""
        && loadedMedia.ref.id === lastLoadRequestedId
    readonly property bool canOperate:
        stationOpen && visible && !controller.busy
    readonly property bool canPlaySelected:
        canOperate && loadMatchesView
    readonly property bool canTransport:
        canOperate && loadedIsRadio && controller.ownsPlayback

    MediaServices.HeadlessMediaController {
        id: controller
        radioClient: "weather-radio"
        polling: stationRadio.stationOpen && stationRadio.visible
        // This is a UI observer of the EXISTING private controller,
        // not a second server; polling stops when RADIO is not loaded.
        pollingInterval: 6000
    }

    FileView {
        id: radioMemoryFile
        path: Quickshell.dataDir + "/weather-radio-memory.json"
        watchChanges: true
        onFileChanged: {
            stationRadio.radioMemoryState="loading";
            reload();
        }
        onLoaded: stationRadio.radioMemoryState="ready"
        onLoadFailed: function(error) {
            // Including FileNotFound: never present old in-memory favorites as
            // an authoritative cleared list. A successful future save heals it.
            stationRadio.radioMemoryState="unavailable";
        }
        onSaved: stationRadio.radioMemoryState="ready"
        onSaveFailed: function(error) {
            stationRadio.radioMemoryState="error";
        }
        onAdapterUpdated: writeAdapter()

        JsonAdapter {
            id: radioMemoryAdapter
            property list<string> favoriteEntries: []
            property list<string> recentEntries: []
        }
    }

    // Directory tags are community-supplied, not editorial certification.
    function broadcastTag(item) {
        const tags = String(item && (item.genre || item.album) || "").toLowerCase();
        if (/(^|[,\s])(news|current affairs)([,\s]|$)/.test(tags))
            return "NEWS";
        if (/(^|[,\s])(talk|politics)([,\s]|$)/.test(tags))
            return "TALK";
        if (/(^|[,\s])(weather)([,\s]|$)/.test(tags))
            return "WX";
        return "";
    }

    function search(query, cursor) {
        if (!canOperate)
            return false;
        recallTargetId = "";
        recallTargetTitle = "";
        recallAttempts = 0;
        recallDelay.stop();
        const requested = String(query || "").trim();
        if (controller.searchMedia("radio-browser", requested, cursor)) {
            browseIndex = 0;
            lastLoadRequestedId = "";
            notice = "SEARCH REQUESTED // " + (requested || "ALL RADIO");
            return true;
        }
        notice = "SEARCH BUSY // RETRY";
        return false;
    }

    function searchPreset(index) {
        if (index < 0 || index >= presets.length)
            return;
        presetIndex = index;
        queryInput.text = presets[index].query;
        search(queryInput.text, null);
    }

    function nextPage() {
        if (!controller.browse || !controller.browse.nextCursor)
            return;
        search(queryInput.text, String(controller.browse.nextCursor));
    }

    function highlight(index) {
        if (index >= 0 && index < browseItems.length)
            browseIndex = index;
    }

    function toggleHighlightedFavorite() {
        if (!highlightedItem)
            return;
        if (highlightedFavorite) {
            radioMemoryAdapter.favoriteEntries =
                RadioMemory.removeFavorite(
                    radioMemoryAdapter.favoriteEntries,
                    highlightedItem
                );
            notice = "FAVORITE REMOVED";
        } else {
            radioMemoryAdapter.favoriteEntries =
                RadioMemory.addFavorite(
                    radioMemoryAdapter.favoriteEntries,
                    highlightedItem,
                    10
                );
            notice = "FAVORITE SAVED // UUID + DISPLAY METADATA ONLY";
        }
    }

    function removeFavorite(item) {
        if (!item)
            return;
        radioMemoryAdapter.favoriteEntries =
            RadioMemory.removeFavorite(
                radioMemoryAdapter.favoriteEntries,
                item
            );
        notice = "FAVORITE REMOVED";
    }

    function rememberLoaded(item) {
        if (!item)
            return;
        radioMemoryAdapter.recentEntries =
            RadioMemory.touchRecent(
                radioMemoryAdapter.recentEntries,
                item,
                8
            );
    }

    function recallSaved(item) {
        const row = RadioMemory.normalize(item);
        if (!row || !canOperate)
            return false;
        const query = "name:" + row.title;
        queryInput.text = query;
        if (!search(query, null))
            return false;
        recallTargetId = row.ref.id;
        recallTargetTitle = row.title;
        recallAttempts = 0;
        notice = "RECALL SEARCH // VERIFYING SAVED UUID";
        return true;
    }

    function resolveRecall() {
        if (recallTargetId === "")
            return;
        if (!canOperate) {
            if (recallAttempts < 6) {
                recallAttempts += 1;
                recallDelay.restart();
            } else {
                notice = "RECALL BUSY // RETRY";
                recallTargetId = "";
                recallTargetTitle = "";
            }
            return;
        }

        for (let i = 0; i < browseItems.length; i++) {
            const item = browseItems[i];
            if (item && item.ref
                    && item.ref.source === "radio-browser"
                    && item.ref.id === recallTargetId) {
                browseIndex = i;
                const foundTitle = recallTargetTitle;
                recallTargetId = "";
                recallTargetTitle = "";
                if (controller.selectMedia(item.ref))
                    notice = "RECALL VERIFIED // " + foundTitle
                           + " // SELECTED // LOAD THEN PLAY";
                else
                    notice = "RECALL VERIFIED // SELECT BUSY";
                return;
            }
        }

        notice = "SAVED UUID NOT IN CURRENT DIRECTORY RESULTS";
        recallTargetId = "";
        recallTargetTitle = "";
    }

    function selectHighlighted() {
        if (!highlightedItem || !highlightedItem.ref || !canOperate)
            return;
        if (controller.selectMedia(highlightedItem.ref))
            notice = "SELECT REQUESTED // LOAD THEN PLAY";
        else
            notice = "CONTROLLER BUSY // RETRY SELECT";
    }

    function loadSelection() {
        if (!selectedRef || selectedRef.source !== "radio-browser" || !canOperate)
            return;
        if (controller.loadSelectedMedia()) {
            lastLoadRequestedId = selectedRef.id;
            notice = "LOAD REQUESTED // NO AUTOPLAY";
        } else {
            notice = "CONTROLLER BUSY // RETRY LOAD";
        }
    }

    function enterHighlighted() {
        if (!highlightedItem || !highlightedItem.ref || !canOperate)
            return;
        if (controller.loadMedia(highlightedItem.ref)) {
            lastLoadRequestedId = highlightedItem.ref.id;
            notice = "ENTER // QUEUE REQUESTED // PLAY SEPARATELY";
        } else {
            notice = "CONTROLLER BUSY // RETRY ENTER";
        }
    }

    function playbackAction(action) {
        if ((action === "play" ? canPlaySelected : canTransport)
                && controller.transport(action))
            notice = action.toUpperCase() + " REQUESTED // VERIFY STATUS";
        else
            notice = "NO VERIFIED RADIO CONTROL // SELECT + LOAD";
    }

    onBrowseItemsChanged: {
        if (recallTargetId !== "")
            recallDelay.restart();
    }

    onLoadedMediaChanged: {
        if (!loadedIsRadio || !loadedMedia || !loadedMedia.ref
                || !loadedMedia.item)
            return;
        const id = String(loadedMedia.ref.id || "");
        if (id === "" || id !== lastLoadRequestedId
                || id === lastRememberedLoadedId)
            return;
        rememberLoaded(loadedMedia.item);
        lastRememberedLoadedId = id;
    }

    Timer {
        id: recallDelay
        interval: 120
        repeat: false
        onTriggered: stationRadio.resolveRecall()
    }

    // Start the default NEWS directory query once this view is mounted.
    // A pending snapshot or unavailable controller never becomes autoplay.
    Timer {
        interval: 800
        repeat: true
        running: stationRadio.stationOpen
                 && stationRadio.visible && !stationRadio.initialSearchSent
                 && stationRadio.sectionVisible("directory")
        onTriggered: {
            if (stationRadio.search("tag:news", null))
                stationRadio.initialSearchSent = true;
        }
    }

    color: Colors.black

    // M1 // Only the directory/saved rows scroll. Original search actions
    // and MPD/select/load/enter/play controls retain their same callbacks.
    Column {
        id: fixedSearch
        objectName: "media-m1-radio-search-fixed"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        anchors.topMargin: 2
        spacing: 3
        visible: !stationRadio.compactOverview
        height: visible ? implicitHeight : 0
            Row {
            visible: stationRadio.sectionVisible("search")
                id: presetRow
                height: 26
                width: parent.width
                spacing: 6

                Repeater {
                    model: stationRadio.presets

                    delegate: ActionButton {
                        required property var modelData
                        required property int index
                        width: Math.max(1, (presetRow.width - 5 * presetRow.spacing) / 6)
                        height: 26
                        label: modelData.name
                        labelPixelSize: 10
                        selected: stationRadio.presetIndex === index
                        available: stationRadio.canOperate
                        onClicked: stationRadio.searchPreset(index)
                    }
                }
            }

            Row {
            visible: stationRadio.sectionVisible("search")
                id: queryRow
                width: parent.width
                height: 30
                spacing: 8

                ActionButton {
                    width: 82
                    height: parent.height
                    label: "SEARCH"
                    labelPixelSize: 11
                    available: stationRadio.canOperate
                    onClicked: stationRadio.search(queryInput.text, null)
                }

                Rectangle {
                    width: Math.max(1, queryRow.width - 82 - 92 - 2 * queryRow.spacing)
                    height: queryRow.height
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    TextInput {
                        id: queryInput
                        anchors.fill: parent
                        anchors.leftMargin: 7
                        anchors.rightMargin: 7
                        anchors.topMargin: 7
                        text: "tag:news"
                        font.pixelSize: 12
                        color: Colors.magenta
                        selectionColor: Colors.magenta
                        selectedTextColor: Colors.black
                        clip: true
                        activeFocusOnTab: true
                        cursorDelegate: Rectangle {
                            width: 2
                            height: Math.max(12, queryInput.cursorRectangle.height)
                            color: Colors.orange
                        }
                        onAccepted: stationRadio.search(text, null)
                    }
                }

                ActionButton {
                    width: 92
                    height: parent.height
                    label: "NEXT 50"
                    labelPixelSize: 10
                    available: stationRadio.canOperate
                               && !!(controller.browse
                                     && controller.browse.nextCursor)
                    onClicked: stationRadio.nextPage()
                }
            }

            QuietText {
            visible: stationRadio.sectionVisible("search")
                width: parent.width
                text: "NAME / TAG:NEWS / TAG:TALK / COUNTRY:US / LANGUAGE:ENGLISH"
                font.pixelSize: 10
            }


    }

    Flickable {
        id: radioScroll
        objectName: "media-m1-radio-directory-scroll"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: fixedSearch.bottom
        anchors.topMargin: fixedSearch.visible ? 3 : 0
        anchors.bottom: fixedTransport.top
        anchors.bottomMargin: fixedTransport.visible ? 3 : 0
        clip: true
        contentWidth: width
        contentHeight: content.implicitHeight + 12
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: content
            objectName: "media-m1-radio-results"
            x: 8
            y: 3
            width: Math.max(0,radioScroll.width-16)
            spacing: 6
            Row {
            visible: stationRadio.sectionVisible("header")
                width: parent.width
                spacing: 18

                GohuText {
                    text: "◉  RADIO // NEWS FIRST"
                    font.pixelSize: 23
                    color: Colors.cyan
                }

                GohuText {
                    text: controller.errorText !== ""
                          ? controller.errorText
                          : controller.busy ? "CONTROLLER WORKING"
                          : controller.playbackState.toUpperCase()
                    font.pixelSize: 12
                    color: controller.errorText !== "" ? Colors.orange
                           : controller.ownsPlayback ? Colors.green : Colors.white
                }
            }

            StationSectionDivider {
            visible: stationRadio.sectionVisible("source")
                width: parent.width
                title: "SHARED HI-FI // RADIO BROWSER // MPD"
            }

            QuietText {
            visible: stationRadio.sectionVisible("source")
                width: parent.width
                font.pixelSize: 11
                text: "SAME RADIO SERVICE AS HI-FI // DIRECTORY CLASSIFICATION IS NOT VERIFIED NEWS CONTENT"
            }

            StationSectionDivider {
            visible: stationRadio.sectionVisible("saved")
                width: parent.width
                title: "SAVED // FAVORITES + RECENTLY LOADED"
            }

            Row {
            visible: stationRadio.sectionVisible("saved")
                width: parent.width
                spacing: 10

                Column {
                    width: Math.max(0, (parent.width - 10) / 2)
                    spacing: 5

                    GohuText {
                        text: "FAVORITES // "
                              + stationRadio.favoriteItems.length
                              + " / 10"
                        color: Colors.magenta
                        font.pixelSize: 11
                    }

                    QuietText {
                        visible: stationRadio.favoriteItems.length === 0
                        width: parent.width
                        text: "NO SAVED STATIONS // HIGHLIGHT + FAVORITE"
                        font.pixelSize: 9
                    }

                    Repeater {
                        model: stationRadio.favoriteItems

                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 44
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.magenta

                            GohuText {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: 9
                                width: Math.max(40, parent.width - 154)
                                text: modelData.title
                                elide: Text.ElideRight
                                color: Colors.white
                                font.pixelSize: 10
                            }

                            ActionButton {
                                anchors.right: removeFavoriteButton.left
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.rightMargin: 6
                                width: 78
                                height: 28
                                label: "RECALL"
                                labelPixelSize: 9
                                available: stationRadio.canOperate
                                onClicked:
                                    stationRadio.recallSaved(modelData)
                            }

                            ActionButton {
                                id: removeFavoriteButton
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.rightMargin: 6
                                width: 44
                                height: 28
                                label: "X"
                                labelPixelSize: 10
                                accentColor: Colors.red
                                destructive: true
                                onClicked:
                                    stationRadio.removeFavorite(modelData)
                            }
                        }
                    }
                }

                Column {
                    width: Math.max(0, (parent.width - 10) / 2)
                    spacing: 5

                    GohuText {
                        text: "RECENTLY LOADED // "
                              + stationRadio.recentItems.length
                              + " / 8"
                        color: Colors.cyan
                        font.pixelSize: 11
                    }

                    QuietText {
                        visible: stationRadio.recentItems.length === 0
                        width: parent.width
                        text: "NO WEATHER RADIO LOADS RECORDED"
                        font.pixelSize: 9
                    }

                    Repeater {
                        model: stationRadio.recentItems

                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 44
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan

                            GohuText {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: 9
                                width: Math.max(40, parent.width - 102)
                                text: modelData.title
                                elide: Text.ElideRight
                                color: Colors.white
                                font.pixelSize: 10
                            }

                            ActionButton {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.rightMargin: 6
                                width: 78
                                height: 28
                                label: "RECALL"
                                labelPixelSize: 9
                                available: stationRadio.canOperate
                                onClicked:
                                    stationRadio.recallSaved(modelData)
                            }
                        }
                    }
                }
            }

            QuietText {
            visible: stationRadio.sectionVisible("saved")
                width: parent.width
                text: "RECALL SEARCHES THE LIVE DIRECTORY BY NAME, THEN REQUIRES THE EXACT SAVED UUID // NO STORED STREAM URL // NO AUTOPLAY"
                font.pixelSize: 9
            }

            StationSectionDivider {
            visible: stationRadio.sectionVisible("directory")
                width: parent.width
                title: "STATIONS // BROWSE + SELECT"
            }

            GohuText {
            visible: stationRadio.sectionVisible("directory")
                width: parent.width
                text: "RESULTS " + stationRadio.browseItems.length
                      + " // " + (controller.browse
                                ? String(controller.browse.query || "ALL RADIO")
                                : "WAITING FOR CONTROLLER")
                color: Colors.cyan
                font.pixelSize: 12
            }

            QuietText {
                visible: stationRadio.sectionVisible("directory") && (stationRadio.browseItems.length === 0)
                width: parent.width
                text: controller.errorText !== "" ? controller.message
                      : "NO STATIONS RETURNED // TRY SEARCH OR ALL RADIO"
                font.pixelSize: 12
            }

            Repeater {
            visible: stationRadio.sectionVisible("directory")
                model: stationRadio.browseItems

                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: content.width
                    height: 54
                    color: stationRadio.browseIndex === index
                           ? Colors.dark : Colors.black
                    border.width: 1
                    border.color: stationRadio.browseIndex === index
                                  ? Colors.magenta : Colors.cyan

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 11
                        anchors.rightMargin: 11
                        spacing: 10

                        GohuText {
                            width: 34
                            anchors.verticalCenter: parent.verticalCenter
                            font.pixelSize: 13
                            text: String(index + 1)
                            color: stationRadio.browseIndex === index
                                   ? Colors.orange : Colors.cyan
                        }

                        Column {
                            width: Math.max(80, parent.width - 282)
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 5

                            GohuText {
                                width: parent.width
                                text: String(modelData.title || "UNTITLED")
                                elide: Text.ElideRight
                                font.pixelSize: 13
                                color: Colors.white
                            }

                            QuietText {
                                width: parent.width
                                text: String(modelData.artist || "--")
                                      + " // " + String(modelData.genre || "UNTAGGED")
                                elide: Text.ElideRight
                                font.pixelSize: 10
                            }
                        }

                        GohuText {
                            width: 24
                            anchors.verticalCenter: parent.verticalCenter
                            text: RadioMemory.isFavorite(
                                      radioMemoryAdapter.favoriteEntries,
                                      modelData
                                  ) ? "★" : ""
                            font.pixelSize: 13
                            color: Colors.magenta
                            horizontalAlignment: Text.AlignHCenter
                        }

                        GohuText {
                            width: 52
                            anchors.verticalCenter: parent.verticalCenter
                            visible: stationRadio.broadcastTag(modelData) !== ""
                            text: stationRadio.broadcastTag(modelData)
                            font.pixelSize: 10
                            color: Colors.magenta
                        }

                        GohuText {
                            width: 132
                            anchors.verticalCenter: parent.verticalCenter
                            text: String(modelData.codec || "--")
                                  + " // " + Number(modelData.bitrate || 0)
                                  + " KBPS"
                            font.pixelSize: 10
                            color: Colors.cyan
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: stationRadio.highlight(index)
                        onDoubleClicked: {
                            stationRadio.highlight(index);
                            stationRadio.selectHighlighted();
                        }
                    }
                }
            }


        }
    }

    Column {
        id: fixedTransport
        objectName: "media-m1-radio-transport-fixed"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        anchors.bottomMargin: 3
        visible: !stationRadio.compactOverview
        height: visible ? implicitHeight : 0
        spacing: 2
            StationSectionDivider {
            visible: stationRadio.sectionVisible("transport")
                width: parent.width
                title: "STATION CONTROLS // SELECT → LOAD → PLAY"
            }

            Row {
                id: transportRow
                height: 29
            visible: stationRadio.sectionVisible("transport")
                width: parent.width
                spacing: 8

                ActionButton {
                    width: Math.max(1,(transportRow.width-6*transportRow.spacing)/7)
                    height: 29
                    label: "SELECT"
                    labelPixelSize: 9
                    available: stationRadio.canOperate
                               && !!stationRadio.highlightedItem
                    onClicked: stationRadio.selectHighlighted()
                }

                ActionButton {
                    width: Math.max(1,(transportRow.width-6*transportRow.spacing)/7)
                    height: 29
                    label: "LOAD"
                    labelPixelSize: 9
                    available: stationRadio.canOperate
                               && !!(stationRadio.selectedRef
                                     && stationRadio.selectedRef.source === "radio-browser")
                    onClicked: stationRadio.loadSelection()
                }

                ActionButton {
                    width: Math.max(1,(transportRow.width-6*transportRow.spacing)/7)
                    height: 29
                    label: "ENTER"
                    labelPixelSize: 9
                    available: stationRadio.canOperate
                               && !!stationRadio.highlightedItem
                    onClicked: stationRadio.enterHighlighted()
                }

                ActionButton {
                    width: Math.max(1,(transportRow.width-6*transportRow.spacing)/7)
                    height: 29
                    label: "PLAY"
                    labelPixelSize: 9
                    available: stationRadio.canPlaySelected
                    onClicked: stationRadio.playbackAction("play")
                }

                ActionButton {
                    width: Math.max(1,(transportRow.width-6*transportRow.spacing)/7)
                    height: 29
                    label: "PAUSE"
                    labelPixelSize: 9
                    available: stationRadio.canTransport
                    onClicked: stationRadio.playbackAction("pause")
                }

                ActionButton {
                    width: Math.max(1,(transportRow.width-6*transportRow.spacing)/7)
                    height: 29
                    label: "STOP"
                    labelPixelSize: 9
                    available: stationRadio.canTransport
                    onClicked: stationRadio.playbackAction("stop")
                }

                ActionButton {
                    width: Math.max(1,(transportRow.width-6*transportRow.spacing)/7)
                    height: 29
                    label: stationRadio.highlightedFavorite
                           ? "UNFAVORITE" : "FAVORITE"
                    labelPixelSize: 8
                    available: stationRadio.canOperate
                               && !!stationRadio.highlightedItem
                    selected: stationRadio.highlightedFavorite
                    onClicked: stationRadio.toggleHighlightedFavorite()
                }
            }

            GohuText {
            visible: stationRadio.sectionVisible("status")
                width: parent.width
                text: controller.errorText !== ""
                      ? controller.message : stationRadio.notice
                color: controller.errorText !== "" ? Colors.orange : Colors.cyan
                font.pixelSize: 9
            }

            QuietText {
            visible: stationRadio.sectionVisible("status")
                width: parent.width
                text: "SELECTED // " + (stationRadio.selectedRef
                      ? String(stationRadio.selectedRef.id) : "--")
                elide: Text.ElideMiddle
                font.pixelSize: 9
            }

            GohuText {
            visible: stationRadio.sectionVisible("status")
                width: parent.width
                text: "LOADED // "
                      + (stationRadio.loadedMedia && stationRadio.loadedMedia.item
                         ? String(stationRadio.loadedMedia.item.title || "--")
                           + " // " + String(stationRadio.loadedMedia.ref.source)
                         : "--")
                color: Colors.white
                elide: Text.ElideRight
                font.pixelSize: 9
            }

            QuietText {
            visible: stationRadio.sectionVisible("status")
                width: parent.width
                text: "SHARED MPD STATE // "
                      + controller.playbackState.toUpperCase()
                      + (controller.ownsPlayback ? " // CONTROLLER OWNED"
                         : " // NO VERIFIED PLAYBACK OWNERSHIP")
                font.pixelSize: 9
            }

            QuietText {
            visible: stationRadio.sectionVisible("status")
                width: parent.width
                text: "MPRIS EXTERNAL PLAYERS REMAIN A SEPARATE HI-FI MODE // WEATHER DOES NOT CLAIM THEIR CONTROL"
                font.pixelSize: 9
            }
    }

    NeonScrollBar {
        flickable: radioScroll
        handleStyle: "star"
        geometryHost: stationRadio
        visible: scrollable
    }
}
