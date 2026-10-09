import QtQml
import Quickshell.Services.Mpris

// Generic browser/player adapter for the first Hi-Fi transport test.
// It never assumes Brave, YouTube, or a particular browser is installed.
// The external player is explicitly selected; no tab or source ownership is inferred.
QtObject {
    id: adapter

    property string selectedBusName: ""

    // playerctld repeats another player's metadata/controls and must not
    // be treated as an independently addressable playback instance.
    readonly property var availablePlayers: Mpris.players.values.filter(function(p) {
        return !!p && !!p.dbusName
               && p.dbusName.indexOf("org.mpris.MediaPlayer2.playerctld") !== 0;
    })

    readonly property var activePlayer: availablePlayers.find(function(p) {
        return p.dbusName === adapter.selectedBusName;
    }) || null

    readonly property bool connected: activePlayer !== null

    function selectNextPlayer() {
        const players = availablePlayers;
        if (players.length === 0) {
            selectedBusName = "";
            return false;
        }

        const index = players.findIndex(function(p) {
            return p.dbusName === adapter.selectedBusName;
        });

        selectedBusName = players[(index + 1) % players.length].dbusName;
        return true;
    }

    function supports(action) {
        const p = activePlayer;
        if (!p)
            return false;

        switch (action) {
        case "play": return p.canPlay;
        case "pause": return p.canPause;
        case "stop": return p.canControl;
        case "previous": return p.canGoPrevious;
        case "next": return p.canGoNext;
        case "rewind5":
        case "forward5": return p.canSeek;
        default: return false;
        }
    }

    // True means a supported command was sent, NOT proof that a remote browser
    // honored it. Live observed MPRIS state must remain the source of truth.
    function run(action) {
        if (!supports(action))
            return false;

        const p = activePlayer;
        switch (action) {
        case "play": p.play(); break;
        case "pause": p.pause(); break;
        case "stop": p.stop(); break;
        case "previous": p.previous(); break;
        case "next": p.next(); break;
        case "rewind5": p.seek(-5); break;
        case "forward5": p.seek(5); break;
        default: return false;
        }

        return true;
    }
}
