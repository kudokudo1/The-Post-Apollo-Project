import QtQuick
import "../../components"

// B4 compact, read-only Media presentation. No new MPD instance, MPRIS
// selection, player command, or audio-routing action lives in this component.
Item {
    id: mediaMini

    property var mediaSnapshot: null

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
    readonly property string mpdTrack:
        !mpdFresh ? "--"
        : mpdState === "unloaded" ? "NO TRACK LOADED"
        : String(mpd.title || "--")
    readonly property string mpdArtist:
        mpdFresh && mpdState !== "unloaded" ? String(mpd.artist || "--") : "--"
    // Last known is deliberately NOT presented as live or currently playing.
    readonly property string mpdLastLoaded:
        mpd && mpd.lastKnownLoadedTitle
        ? String(mpd.lastKnownLoadedTitle) : "--"

    readonly property string mprisState:
        mpris && mpris.state ? String(mpris.state) : "unavailable"
    readonly property bool mprisSelected:
        mpris !== null && mpris.selected === true
    readonly property bool mprisObserved:
        mprisSelected && (mprisState === "playing"
                          || mprisState === "paused"
                          || mprisState === "stopped")
    readonly property string mprisPlayer:
        mprisSelected ? String(mpris.playerName || "SELECTED PLAYER")
        : mprisState === "selection-required" ? "SELECT PLAYER IN HI-FI"
        : mprisState === "player-missing" ? "SELECTED PLAYER MISSING"
        : "NO SELECTED PLAYER"
    readonly property string mprisTrack:
        mprisObserved ? String(mpris.title || "--") : "--"
    readonly property string mprisArtist:
        mprisObserved ? String(mpris.artist || "--") : "--"

    function stateLabel(value) {
        return String(value || "unavailable").toUpperCase().replace(/-/g, " ");
    }

    Row {
        id: sourceColumns
        anchors.fill: parent
        spacing: 12

        Column {
            width: Math.max(0, (sourceColumns.width - sourceColumns.spacing) / 2)
            spacing: 2

            GohuText {
                width: parent.width
                height: 17
                font.pixelSize: 12
                color: mediaMini.mpdFresh && mediaMini.mpdState === "playing"
                       ? Colors.green : Colors.orange
                elide: Text.ElideRight
                text: "MPD // " + mediaMini.stateLabel(mediaMini.mpdState)
            }
            GohuText {
                width: parent.width
                height: 17
                font.pixelSize: 12
                color: Colors.white
                elide: Text.ElideRight
                text: "TRACK  " + mediaMini.mpdTrack
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "ARTIST " + mediaMini.mpdArtist
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "LAST LOADED  " + mediaMini.mpdLastLoaded
            }
        }

        Column {
            width: Math.max(0, (sourceColumns.width - sourceColumns.spacing) / 2)
            spacing: 2

            GohuText {
                width: parent.width
                height: 17
                font.pixelSize: 12
                color: mediaMini.mprisObserved && mediaMini.mprisState === "playing"
                       ? Colors.green : Colors.orange
                elide: Text.ElideRight
                text: "MPRIS // " + mediaMini.stateLabel(mediaMini.mprisState)
            }
            GohuText {
                width: parent.width
                height: 17
                font.pixelSize: 12
                color: Colors.white
                elide: Text.ElideRight
                text: "PLAYER " + mediaMini.mprisPlayer
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "TRACK  " + mediaMini.mprisTrack
            }
            GohuText {
                width: parent.width
                height: 14
                font.pixelSize: 10
                color: Colors.cyan
                elide: Text.ElideRight
                text: "ARTIST " + mediaMini.mprisArtist
            }
        }
    }
}
