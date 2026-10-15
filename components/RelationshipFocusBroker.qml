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
    property var notifications: null
    property bool active: false
    property string owner: ""
    property string previousOwner: ""
    // Remember the selected widget across independent key holds, without
    // taking over native Sway focus or selecting on the prefix alone.
    property string lastWidgetOwner: ""
    property string hostOwner: ""
    // Diagnostic only: short seat-acquisition intent from the existing
    // coordinator. Kept independent from Koinoikos's selection policy.
    property string boostOwner: ""

    signal previousOwnerRestorationRequested(string previous)

    function candidates() {
        const windows = [
            { id: "appcontrol", item: broker.appControl },
            { id: "hospital", item: broker.hospital },
            { id: "git", item: broker.git },
            { id: "cpu", item: broker.cpu },
            { id: "weather", item: broker.weather },
            { id: "notifications", item: broker.notifications }
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
                lastWidgetOwner = id;
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
        // Entered only on the FIRST held direction, never on prefix alone.
        // Preserve live keyboard ownership first, then the last selected
        // widget from the previous hold, then a stable visible fallback.
        if (!selectOwner(previous) && !selectOwner(lastWidgetOwner)) {
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

    // Read-only diagnostics. No bindings, focus changes, text or page titles.
    // "active" and "activeFocusItem" are Qt-reported and may be unavailable;
    // even when present they are NOT compositor seat-key delivery evidence.
    function inspectWindow(id, w) {
        if (!w)
            return { id: id, present: false };
        const item = w.activeFocusItem;
        return {
            id: id,
            present: true,
            open: w.menuOpen === true,
            visible: w.visible === true,
            qtWindowActive: typeof w.active === "boolean" ? w.active : null,
            qtActiveFocusItem: item
                               ? String(item.objectName || "<unnamed>") : null,
            keyboardActive: typeof w.keyboardActive === "boolean"
                            ? w.keyboardActive : null,
            keyboardLock: typeof w.keyboardLock === "boolean"
                          ? w.keyboardLock : null,
            focusable: typeof w.focusable === "boolean" ? w.focusable : null
        };
    }

    function diagnosticSnapshot() {
        return JSON.stringify({
            koinoikosActive: active,
            koinoikosOwner: owner,
            logicalKeyboardOwner: hostOwner,
            focusBoostOwner: boostOwner,
            previousWidgetOwner: previousOwner,
            candidates: candidates(),
            windows: [
                inspectWindow("appcontrol", appControl),
                inspectWindow("hospital", hospital),
                inspectWindow("git", git),
                inspectWindow("cpu", cpu),
                inspectWindow("weather", weather),
                inspectWindow("notifications", notifications)
            ]
        });
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

        // Observe focus state without modifying it. Do not replace the
        // router-facing snapshot or imply that Qt focus proves seat focus.
        function diagnose(): string {
            return broker.diagnosticSnapshot();
        }

        function select(id: string): bool {
            return broker.selectOwner(id);
        }
    }
}
