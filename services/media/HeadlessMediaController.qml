import QtQuick
import Quickshell
import Quickshell.Io

// Thin local UI client for the persistent, user-private Hi-Fi controller.
// This component never starts MPD or the server and never issues mpc commands.
// Closing the deck only stops UI observation, not music playback.
Scope {
    id: bridge

    property bool polling: false
    // Legacy Hi-Fi leaves default; Weather RADIO uses a scoped catalog.
    // Only browsing/selection are per-client, MPD playback stays shared.
    property string radioClient: "default"
    property int pollingInterval: 2400
    property var snapshot: null
    property string message: "SELECT A STATION TO LOAD"
    property string errorText: ""
    property string pendingAction: ""
    // Snapshot polling is read-only observation, not a user-initiated load.
    // Never pulse/disable the cassette or transport keys every 2.4 seconds.
    readonly property bool busy: commandProcess.running && pendingAction !== "snapshot"
    readonly property string playbackState:
        snapshot && snapshot.session ? String(snapshot.session.state || "unloaded") : "unknown"
    readonly property bool ownsPlayback:
        !!(snapshot && snapshot.session && snapshot.session.ownedByController)
    readonly property var loaded:
        snapshot && snapshot.loaded ? snapshot.loaded : null
    readonly property var browse:
        snapshot && snapshot.browse ? snapshot.browse : null
    readonly property var selection:
        snapshot && snapshot.selection ? snapshot.selection : null
    property var inspectedItem: null

    function issue(action, additionalArgs) {
        // One CLI request at a time. Never overlap a transport command and
        // polling snapshot or accidentally target a different MPD item.
        if (commandProcess.running)
            return false;
        const argv = [
            "/usr/bin/python3",
            Quickshell.shellPath("scripts/media/media_controller_cli.py"),
            action
        ];
        const args = additionalArgs || [];
        for (let i = 0; i < args.length; i++)
            argv.push(String(args[i]));
        pendingAction = action;
        commandProcess.exec(argv);
        return true;
    }

    function refresh() {
        if (radioClient === "default")
            issue("snapshot", []);
        else
            issue("snapshot", ["--client", radioClient]);
    }

    // All browsing/selection requests use the same versioned CLI and private socket.
    // None of these methods starts playback or mutates another player's audio.
    function searchMedia(source, query, cursor) {
        if ((source !== "local-mpd" && source !== "youtube"
                && source !== "radio-browser")
                || typeof query !== "string"
                || (query.trim().length === 0 && source !== "radio-browser")
                || query.length > 256)
            return false;
        const args = [query, "--source", source];
        if (cursor !== undefined && cursor !== null && cursor !== "") {
            if ((source !== "youtube" && source !== "radio-browser")
                    || typeof cursor !== "string"
                    || cursor.length > 256)
                return false;
            args.push("--cursor", cursor);
        }
        if (source === "radio-browser" && radioClient !== "default")
            args.push("--client", radioClient);
        return issue("search", args);
    }

    function mediaRefArgs(ref) {
        if (!ref || typeof ref.id !== "string" || !ref.id.length
                || ref.id.length > 4096
                || (ref.source !== "local-mpd" && ref.source !== "youtube"
                    && ref.source !== "direct-stream"
                    && ref.source !== "radio-browser"))
            return null;
        const args = [ref.id, "--source", ref.source];
        if (ref.source === "radio-browser" && radioClient !== "default")
            args.push("--client", radioClient);
        return args;
    }

    function inspectMedia(ref) {
        const args = mediaRefArgs(ref);
        return args !== null && issue("inspect", args);
    }

    // SELECT stages media; LOAD queues it without autoplay; PLAY is separate.
    function selectMedia(ref) {
        const args = mediaRefArgs(ref);
        return args !== null && issue("select", args);
    }

    function loadSelectedMedia() {
        if (radioClient !== "default")
            return issue("load", ["--client", radioClient]);
        return issue("load", []);
    }

    // Contextual ENTER cues an exact local track or guarded radio station
    // without autoplay. YouTube and collection loading stay unavailable.
    function loadMedia(ref) {
        const args = mediaRefArgs(ref);
        if (args === null || (ref.source !== "local-mpd"
                              && ref.source !== "radio-browser"))
            return false;
        if (ref.source === "radio-browser" && radioClient !== "default")
            return issue("load", ["--uri", ref.id, "--source", ref.source,
                                  "--client", radioClient]);
        return issue("load", ["--uri", ref.id, "--source", ref.source]);
    }

    function loadRadio(url) {
        if (typeof url !== "string" || !url.startsWith("https://"))
            return false;
        return issue("load", ["--source", "direct-stream", "--uri", url]);
    }

    function transport(action) {
        const commands = {
            "play": ["play"],
            "pause": ["pause"],
            "stop": ["stop"],
            "previous": ["previous"],
            "next": ["next"],
            "rewind5": ["seek", "-5"],
            "forward5": ["seek", "5"]
        };
        const cmd = commands[action];
        if (!cmd)
            return false;
        return issue(cmd[0], cmd.slice(1));
    }

    function acceptResponse(raw) {
        let payload;
        try {
            payload = JSON.parse(String(raw || ""));
            if (!payload || payload.version !== 1 || typeof payload.ok !== "boolean")
                throw new Error("Unexpected controller response");
        } catch (err) {
            errorText = "BAD CONTROLLER RESPONSE";
            message = errorText;
            return;
        }
        if (!payload.ok) {
            errorText = payload.error
                ? String(payload.error.code || "CONTROLLER REFUSED")
                : "CONTROLLER REFUSED";
            message = errorText;
            return;
        }
        errorText = "";
        if (pendingAction === "snapshot") {
            snapshot = payload.result;
        } else {
            // Search and staged selection update local view data immediately.
            // The next snapshot reconciles this with the persistent controller.
            if (pendingAction === "search" && payload.result.browse) {
                snapshot = Object.assign({}, snapshot || {},
                                         { browse: payload.result.browse });
                inspectedItem = null;
            } else if (pendingAction === "select" && payload.result.selection) {
                snapshot = Object.assign({}, snapshot || {},
                                         { selection: payload.result.selection });
            } else if (pendingAction === "inspect" && payload.result.item) {
                inspectedItem = payload.result.item;
            }
            // A successful command result is NOT evidence of audible output.
            message = pendingAction.toUpperCase() + " / COMMAND ACCEPTED";
            followup.start();
        }
    }

    Process {
        id: commandProcess

        stdout: StdioCollector {
            onStreamFinished: bridge.acceptResponse(text)
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(text || "").trim();
                if (detail.length > 0) {
                    bridge.errorText = "CONTROLLER CONNECTION FAILED";
                    bridge.message = bridge.errorText;
                }
            }
        }
    }

    Timer {
        id: followup
        interval: 250
        repeat: false
        onTriggered: bridge.refresh()
    }

    Timer {
        interval: bridge.pollingInterval
        repeat: true
        running: bridge.polling
        triggeredOnStart: true
        onTriggered: bridge.refresh()
    }
}
