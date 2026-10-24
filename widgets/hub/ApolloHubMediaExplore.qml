import QtQuick
import "../../components"

// Stage 8E: taller Media tile presents already-observed MPD and MPRIS
// metadata. No playback, player selection, audio routing, polling or
// controller lifetime is owned here. This is Level 2 exploration only.
Item {
    id: mediaExplore

    property var mediaSnapshot: null
    property string selectedView: "both"
    readonly property int densityLevel: height >= 300 ? 3 : 2
    readonly property var mpd:
        mediaSnapshot && mediaSnapshot.mpd ? mediaSnapshot.mpd : null
    readonly property var mpris:
        mediaSnapshot && mediaSnapshot.mpris ? mediaSnapshot.mpris : null

    readonly property string mpdState:
        mpd && mpd.state ? String(mpd.state) : "disconnected"
    readonly property bool mpdFresh:
        mpd !== null && mpd.fresh === true
        && (mpdState === "playing" || mpdState === "paused"
            || mpdState === "stopped" || mpdState === "unloaded")
    readonly property string mprisState:
        mpris && mpris.state ? String(mpris.state) : "unavailable"
    readonly property bool mprisSelected:
        mpris !== null && mpris.selected === true
    readonly property bool mprisObserved:
        mprisSelected && (mprisState === "playing"
                          || mprisState === "paused"
                          || mprisState === "stopped")
    readonly property int playerCount:
        mpris && typeof mpris.playerCount === "number"
        && isFinite(mpris.playerCount) && mpris.playerCount >= 0
        ? Math.floor(mpris.playerCount) : 0

    function stateLabel(value) {
        return String(value || "unavailable").toUpperCase().replace(/-/g, " ");
    }
    function safeText(value, fallback) {
        return typeof value === "string" && value.length > 0 ? value : fallback;
    }

    readonly property string statusLine:
        selectedView === "both"
        ? "MEDIA // BOTH SOURCES // AUDIO OUTPUT NOT VERIFIED"
        : selectedView === "mpd"
        ? "MEDIA // MPD // " + stateLabel(mpdState)
          + " // AUDIO OUTPUT NOT VERIFIED"
        : "MEDIA // MPRIS // " + stateLabel(mprisState)
          + " // AUDIO OUTPUT NOT VERIFIED"

    readonly property string heading:
        selectedView === "mpd" ? "MPD // " + stateLabel(mpdState)
        : "MPRIS // " + stateLabel(mprisState)
    readonly property string primary:
        selectedView === "mpd"
        ? (!mpdFresh ? "TRACK UNAVAILABLE"
           : mpdState === "unloaded" ? "NO TRACK LOADED"
           : safeText(mpd.title, "TRACK UNKNOWN"))
        : !mprisObserved ? (mprisState === "selection-required"
                            ? "SELECT PLAYER IN HI-FI"
                            : mprisState === "player-missing"
                              ? "SELECTED PLAYER MISSING" : "TRACK UNAVAILABLE")
          : safeText(mpris.title, "TRACK UNKNOWN")
    readonly property string artist:
        selectedView === "mpd"
        ? "ARTIST // " + (mpdFresh && mpdState !== "unloaded"
                          ? safeText(mpd.artist, "--") : "--")
        : "ARTIST // " + (mprisObserved
                          ? safeText(mpris.artist, "--") : "--")
    readonly property string detailOne:
        selectedView === "mpd"
        ? "OBSERVATION // " + (mpdFresh
            ? stateLabel(safeText(mpd.observationSource, "UNKNOWN")) : "UNAVAILABLE")
        : "PLAYER // " + (mprisSelected
            ? safeText(mpris.playerName, "SELECTED PLAYER") : "NONE SELECTED")
    readonly property string detailTwo:
        selectedView === "mpd"
        ? "OBSERVED AGE // " + (mpdFresh && typeof mpd.ageSeconds === "number"
           && isFinite(mpd.ageSeconds) && mpd.ageSeconds >= 0
           ? String(Math.floor(mpd.ageSeconds)) + " SEC" : "--")
        : "ALBUM // " + (mprisObserved ? safeText(mpris.album, "--") : "--")
    readonly property string detailThree:
        selectedView === "mpd"
        ? "LAST KNOWN LOADED // " + (mpd && mpd.lastKnownLoadedTitle
            ? safeText(mpd.lastKnownLoadedTitle, "--") : "--")
        : "MPRIS PLAYERS // " + String(playerCount)
          + " // NO AUTOMATIC SELECTION"

    Row {
        id: sourceSelector
        width: parent.width
        height: mediaExplore.densityLevel === 3 ? 32 : 27
        spacing: 4

        Repeater {
            model: ["BOTH", "MPD", "MPRIS"]
            delegate: ActionButton {
                required property string modelData
                width: Math.max(1, (sourceSelector.width
                                    - 2 * sourceSelector.spacing) / 3)
                height: sourceSelector.height
                label: modelData
                labelPixelSize: 11
                selected: modelData.toLowerCase() === mediaExplore.selectedView
                trackLabelGlowLocally: true
                softGlowEnabled: false
                onLeftClicked: mediaExplore.selectedView = modelData.toLowerCase()
            }
        }
    }

    ApolloHubMediaMini {
        id: bothView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: sourceSelector.bottom
        anchors.topMargin: 8
        anchors.bottom: parent.bottom
        mediaSnapshot: mediaExplore.mediaSnapshot
        visible: mediaExplore.selectedView === "both"
    }

    Item {
        id: detailPane
        anchors.top: sourceSelector.bottom
        anchors.topMargin: 6
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        visible: mediaExplore.selectedView !== "both"
        Column {
            width: parent.width
            height: childrenRect.height
            anchors.centerIn: parent
            spacing: mediaExplore.densityLevel === 3 ? 9 : 4

            GohuText {
                width: parent.width
                height: mediaExplore.densityLevel === 3 ? 31 : 24
                font.pixelSize: mediaExplore.densityLevel === 3 ? 18 : 14
                color: mediaExplore.selectedView === "mpd" && mediaExplore.mpdFresh
                       && mediaExplore.mpdState === "playing"
                       || mediaExplore.selectedView === "mpris" && mediaExplore.mprisObserved
                       && mediaExplore.mprisState === "playing"
                       ? Colors.green : Colors.magenta
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: mediaExplore.heading
            }
            GohuText {
                width: parent.width
                height: mediaExplore.densityLevel === 3 ? 55 : 40
                font.pixelSize: mediaExplore.densityLevel === 3 ? 31 : 23
                color: mediaExplore.selectedView === "mpd" && mediaExplore.mpdFresh
                       || mediaExplore.selectedView === "mpris" && mediaExplore.mprisObserved
                       ? Colors.white : Colors.orange
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: mediaExplore.primary
            }
            GohuText {
                width: parent.width
                height: mediaExplore.densityLevel === 3 ? 28 : 24
                font.pixelSize: mediaExplore.densityLevel === 3 ? 16 : 13
                color: Colors.cyan
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
                text: mediaExplore.artist
            }
            Repeater {
                model: [mediaExplore.detailOne,
                        mediaExplore.detailTwo,
                        mediaExplore.detailThree]
                delegate: GohuText {
                    required property string modelData
                    width: parent.width
                    height: mediaExplore.densityLevel === 3 ? 24 : 20
                    font.pixelSize: mediaExplore.densityLevel === 3 ? 13 : 11
                    color: index === 2 ? Colors.orange : Colors.cyan
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    text: modelData
                }
            }
        }
    }
}
