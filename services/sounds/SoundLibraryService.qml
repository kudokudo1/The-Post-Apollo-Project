pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Shared Sound Library V1. Only explicit user actions run the bounded host.
// Alarms store stable IDs, not arbitrary user file paths.
Scope {
    id: library
    property var tones: []
    property bool busy: false
    property bool loaded: false
    property string feedback: "SOUND LIBRARY // NOT LOADED"
    property string selectedImportedId: ""
    property int revision: 0
    readonly property int maxTones: 32

    function byId(id) {
        const token = String(id || "");
        for (let i = 0; i < tones.length; i++)
            if (tones[i].id === token) return tones[i];
        return null;
    }
    function isImportedId(id) {
        return /^user-[0-9a-f]{64}$/.test(String(id || ""));
    }
    function sourceFor(id) {
        const match = byId(id);
        return match && isImportedId(id) ? String(match.url) : "";
    }
    function labelFor(id) {
        const match = byId(id);
        return match ? match.name : "";
    }
    function start(operation, extra) {
        if (busy) {
            feedback = "SOUND LIBRARY // BUSY // RETRY";
            return false;
        }
        if (["list","import","rename","delete"].indexOf(operation) < 0) {
            feedback = "SOUND LIBRARY // INVALID OPERATION";
            return false;
        }
        busy = true;
        feedback = operation.toUpperCase() + " // WORKING";
        selectedImportedId = "";
        const argv = ["python3", "-I", "-B",
            Quickshell.shellPath("services/sounds/SoundLibraryHost.py"),
            "--data-dir", Quickshell.dataDir, "--operation", operation];
        if (extra) {
            if (extra.source) argv.push("--source", String(extra.source));
            if (extra.name !== undefined) argv.push("--name", String(extra.name));
            if (extra.id) argv.push("--tone-id", String(extra.id));
        }
        helper.command = argv;
        helper.running = true;
        return true;
    }
    function refresh() { return start("list", {}); }
    function importAudio(fileUrl, displayName) {
        const url = String(fileUrl || "");
        if (!url.startsWith("file:") || !/\.(wav|mp3)$/i.test(url)) {
            feedback = "SOUND LIBRARY // CHOOSE WAV OR MP3";
            return false;
        }
        if (!validName(displayName)) {
            feedback = "SOUND LIBRARY // INVALID TONE NAME";
            return false;
        }
        return start("import", {source: url, name: displayName});
    }
    // Preserve older call sites; WAV and MP3 now share one safe import lane.
    function importWav(fileUrl, displayName) {
        return importAudio(fileUrl, displayName);
    }
    function validName(name) {
        const value = String(name || "");
        return value.trim().length > 0 && value.length <= 40
            && !/[\x00-\x1f\x7f]/.test(value);
    }
    function rename(id, name) {
        return isImportedId(id) && validName(name)
            && start("rename", {id: id, name: name});
    }
    function remove(id) {
        return isImportedId(id) && start("delete", {id: id});
    }
    function consume(raw) {
        let parsed;
        try {
            parsed = JSON.parse(String(raw || ""));
        } catch (e) {
            feedback = "SOUND LIBRARY // INVALID HOST REPLY";
            busy = false;
            return;
        }
        if (!parsed || parsed.ok !== true || !Array.isArray(parsed.tones)) {
            feedback = "SOUND LIBRARY // " + String(parsed && parsed.error || "HOST ERROR");
            busy = false;
            return;
        }
        if (parsed.tones.length > maxTones
                || parsed.tones.some(t => !isImportedId(t.id)
                    || !validName(t.name) || typeof t.url !== "string"
                    || !t.url.startsWith("file://"))) {
            feedback = "SOUND LIBRARY // INVALID CATALOG";
            busy = false;
            return;
        }
        tones = parsed.tones;
        selectedImportedId = isImportedId(parsed.selectedId) ? parsed.selectedId : "";
        loaded = true;
        revision += 1;
        busy = false;
        feedback = "SOUND LIBRARY // " + String(parsed.status || "ready").toUpperCase()
            + " // " + tones.length + " SAVED";
    }

    Process {
        id: helper
        running: false
        stdout: StdioCollector {
            onStreamFinished: library.consume(text)
        }
        onExited: function(code, status) {
            // Collector may flush after exit. Give it a short chance before
            // reporting malformed or absent output. No retries or mutations.
            missingReplyDelay.restart();
        }
    }
    Timer {
        id: missingReplyDelay
        interval: 300
        repeat: false
        onTriggered: {
            if (library.busy) {
                library.busy = false;
                library.feedback = "SOUND LIBRARY // HOST EXIT WITHOUT REPLY";
            }
        }
    }
    Component.onCompleted: refresh()
}
