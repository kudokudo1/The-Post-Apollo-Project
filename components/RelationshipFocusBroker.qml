import QtQuick
import Quickshell.Io

// Koinoikos: widget-only registry; ordinary Sway app focus remains independent.
// This QtObject does NOT handle directional keys. Sway's binding mode owns them;
// scripts/koinoikos_focus.py consumes these explicitly registered surfaces.
QtObject {
    id: broker

    property var appControl: null
    property var hospital: null
    property var git: null
    property var cpu: null
    property var weather: null
    property bool active: false
    property string owner: ""
    property string previousOwner: ""
    property string hostOwner: ""

    signal previousOwnerRestorationRequested(string previous)

    function candidates() {
        const windows = [
            { id: "appcontrol", item: broker.appControl },
            { id: "hospital", item: broker.hospital },
            { id: "git", item: broker.git },
            { id: "cpu", item: broker.cpu },
            { id: "weather", item: broker.weather }
        ];
        const result = [];

        for (let i = 0; i < windows.length; ++i) {
            const row = windows[i];
            const w = row.item;
            if (!w || !w.menuOpen || !w.visible
                || w.width <= 0 || w.height <= 0)
                continue;

            result.push({
                id: row.id,
                x: Math.round(w.x),
                y: Math.round(w.y),
                w: Math.round(w.width),
                h: Math.round(w.height)
            });
        }
        return result;
    }

    function selectOwner(id) {
        if (!active)
            return false;
        const visible = candidates();
        for (let i = 0; i < visible.length; ++i) {
            if (visible[i].id === id) {
                owner = id;
                return true;
            }
        }
        return false;
    }

    function startMode(previous) {
        if (active)
            return true;
        previousOwner = previous;
        active = true;
        // Preserve Git/Hospital ownership when eligible, otherwise start
        // from a visible widget. Never anchor to a regular Sway window.
        if (!selectOwner(previous)) {
            const visible = candidates();
            owner = visible.length > 0 ? visible[0].id : "";
        }
        return true;
    }

    function stopMode() {
        if (!active)
            return;
        active = false;
        owner = "";
        previousOwnerRestorationRequested(previousOwner);
        previousOwner = "";
    }

    property IpcHandler ipc: IpcHandler {
        target: "relationshipFocus"

        function begin(): bool {
            return broker.startMode(broker.hostOwner);
        }

        function end(): void {
            broker.stopMode();
        }

        function snapshot(): string {
            return JSON.stringify({
                active: broker.active,
                owner: broker.owner,
                surfaces: broker.candidates()
            });
        }

        function select(id: string): bool {
            return broker.selectOwner(id);
        }
    }
}
