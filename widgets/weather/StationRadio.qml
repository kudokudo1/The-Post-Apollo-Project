import QtQuick
import "../../components"
import "../../services/media" as MediaServices

// A news-first RADIO surface using the SAME private Hi-Fi controller and
// guarded MPD relay. No second Radio Browser fetcher, MPD or direct stream URLs.
// RADIO directory search / SELECT / LOAD never autoplays. Transport is shared.
Rectangle {
    id: stationRadio

    property bool stationOpen: true
    property int browseIndex: 0
    property int presetIndex: 0
    property string notice: "NEWS FIRST // CHOOSE A STATION"
    property string lastLoadRequestedId: ""
    property bool initialSearchSent: false
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

    // Start the default NEWS directory query once this view is mounted.
    // A pending snapshot or unavailable controller never becomes autoplay.
    Timer {
        interval: 800
        repeat: true
        running: stationRadio.stationOpen
                 && stationRadio.visible && !stationRadio.initialSearchSent
        onTriggered: {
            if (stationRadio.search("tag:news", null))
                stationRadio.initialSearchSent = true;
        }
    }

    color: Colors.black

    Flickable {
        id: radioScroll
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.implicitHeight + 22
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: content
            x: 18
            y: 10
            width: Math.max(0, radioScroll.width - 36)
            spacing: 10

            Row {
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
                width: parent.width
                title: "SHARED HI-FI // RADIO BROWSER // MPD"
            }

            QuietText {
                width: parent.width
                font.pixelSize: 11
                text: "SAME RADIO SERVICE AS HI-FI // DIRECTORY CLASSIFICATION IS NOT VERIFIED NEWS CONTENT"
            }

            Row {
                id: presetRow
                width: parent.width
                spacing: 6

                Repeater {
                    model: stationRadio.presets

                    delegate: ActionButton {
                        required property var modelData
                        required property int index
                        width: Math.max(65, (presetRow.width - 5 * presetRow.spacing) / 6)
                        height: 29
                        label: modelData.name
                        labelPixelSize: 10
                        selected: stationRadio.presetIndex === index
                        available: stationRadio.canOperate
                        onClicked: stationRadio.searchPreset(index)
                    }
                }
            }

            Row {
                id: queryRow
                width: parent.width
                height: 33
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
                    width: Math.max(150, queryRow.width - 82 - 92 - 2 * queryRow.spacing)
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
                width: parent.width
                text: "NAME / TAG:NEWS / TAG:TALK / COUNTRY:US / LANGUAGE:ENGLISH"
                font.pixelSize: 10
            }

            StationSectionDivider {
                width: parent.width
                title: "STATIONS // BROWSE + SELECT"
            }

            GohuText {
                width: parent.width
                text: "RESULTS " + stationRadio.browseItems.length
                      + " // " + (controller.browse
                                ? String(controller.browse.query || "ALL RADIO")
                                : "WAITING FOR CONTROLLER")
                color: Colors.cyan
                font.pixelSize: 12
            }

            QuietText {
                visible: stationRadio.browseItems.length === 0
                width: parent.width
                text: controller.errorText !== "" ? controller.message
                      : "NO STATIONS RETURNED // TRY SEARCH OR ALL RADIO"
                font.pixelSize: 12
            }

            Repeater {
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
                            width: Math.max(80, parent.width - 258)
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

            StationSectionDivider {
                width: parent.width
                title: "STATION CONTROLS // SELECT → LOAD → PLAY"
            }

            Row {
                width: parent.width
                spacing: 8

                ActionButton {
                    width: 105
                    height: 36
                    label: "SELECT"
                    labelPixelSize: 12
                    available: stationRadio.canOperate
                               && !!stationRadio.highlightedItem
                    onClicked: stationRadio.selectHighlighted()
                }

                ActionButton {
                    width: 100
                    height: 36
                    label: "LOAD"
                    labelPixelSize: 12
                    available: stationRadio.canOperate
                               && !!(stationRadio.selectedRef
                                     && stationRadio.selectedRef.source === "radio-browser")
                    onClicked: stationRadio.loadSelection()
                }

                ActionButton {
                    width: 100
                    height: 36
                    label: "ENTER"
                    labelPixelSize: 12
                    available: stationRadio.canOperate
                               && !!stationRadio.highlightedItem
                    onClicked: stationRadio.enterHighlighted()
                }

                ActionButton {
                    width: 100
                    height: 36
                    label: "PLAY"
                    labelPixelSize: 12
                    available: stationRadio.canPlaySelected
                    onClicked: stationRadio.playbackAction("play")
                }

                ActionButton {
                    width: 100
                    height: 36
                    label: "PAUSE"
                    labelPixelSize: 12
                    available: stationRadio.canTransport
                    onClicked: stationRadio.playbackAction("pause")
                }

                ActionButton {
                    width: 100
                    height: 36
                    label: "STOP"
                    labelPixelSize: 12
                    available: stationRadio.canTransport
                    onClicked: stationRadio.playbackAction("stop")
                }
            }

            GohuText {
                width: parent.width
                text: controller.errorText !== ""
                      ? controller.message : stationRadio.notice
                color: controller.errorText !== "" ? Colors.orange : Colors.cyan
                font.pixelSize: 12
            }

            QuietText {
                width: parent.width
                text: "SELECTED // " + (stationRadio.selectedRef
                      ? String(stationRadio.selectedRef.id) : "--")
                elide: Text.ElideMiddle
                font.pixelSize: 11
            }

            GohuText {
                width: parent.width
                text: "LOADED // "
                      + (stationRadio.loadedMedia && stationRadio.loadedMedia.item
                         ? String(stationRadio.loadedMedia.item.title || "--")
                           + " // " + String(stationRadio.loadedMedia.ref.source)
                         : "--")
                color: Colors.white
                elide: Text.ElideRight
                font.pixelSize: 12
            }

            QuietText {
                width: parent.width
                text: "SHARED MPD STATE // "
                      + controller.playbackState.toUpperCase()
                      + (controller.ownsPlayback ? " // CONTROLLER OWNED"
                         : " // NO VERIFIED PLAYBACK OWNERSHIP")
                font.pixelSize: 10
            }

            QuietText {
                width: parent.width
                text: "MPRIS EXTERNAL PLAYERS REMAIN A SEPARATE HI-FI MODE // WEATHER DOES NOT CLAIM THEIR CONTROL"
                font.pixelSize: 10
            }
        }
    }

    NeonScrollBar {
        flickable: radioScroll
        handleStyle: "star"
        geometryHost: stationRadio
        visible: scrollable
    }
}
