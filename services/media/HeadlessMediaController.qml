import QtQuick
import Quickshell
import Quickshell.Io

// Thin local UI client for the persistent, user-private Hi-Fi controller.
// This component never starts MPD or the server and never issues mpc commands.
// Closing the deck only stops UI observation, not music playback.
Scope {
    id: bridge

    property bool polling: false
    property var snapshot: null
    property string message: "SELECT A STATION TO LOAD"
    property string errorText: ""
    property string pendingAction: ""
    readonly property bool busy: commandProcess.running
    readonly property string playbackState:
        snapshot && snapshot.session ? String(snapshot.session.state || "unloaded") : "unknown"
    readonly property bool ownsPlayback:
        !!(snapshot && snapshot.session && snapshot.session.ownedByController)
    readonly property var loaded:
        snapshot && snapshot.loaded ? snapshot.loaded : null

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
        issue("snapshot", []);
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
            // Successful command issuance is not the same as audible audio.
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
        interval: 2400
        repeat: true
        running: bridge.polling
        triggeredOnStart: true
        onTriggered: bridge.refresh()
    }
}
