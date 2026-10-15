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

    signal previousOwnerRestorationRequested(string previous)

    // PanelWindow is a QsWindow, not a positioned QtQuick Item. It does not
    // expose reliable x/y properties. Derive its desktop-space rectangle from
    // the actual attached ShellScreen, layer anchors and panel margins.
    // Never serialize NaN: JSON.stringify turns NaN into null, after which
    // the spatial Python router intentionally rejects the entire candidate.
    function panelRect(w) {
        if (!w || !w.screen || !w.anchors || !w.margins)
            return null;

        const screen = w.screen;
        const anchors = w.anchors;
        const margins = w.margins;
        const sx = Number(screen.x);
        const sy = Number(screen.y);
        const sw = Number(screen.width);
        const sh = Number(screen.height);
        const ww = Number(w.width);
        const wh = Number(w.height);
        const ml = Number(margins.left);
        const mr = Number(margins.right);
        const mt = Number(margins.top);
        const mb = Number(margins.bottom);

        const numbers = [sx, sy, sw, sh, ww, wh, ml, mr, mt, mb];
        for (let i = 0; i < numbers.length; ++i) {
            if (!isFinite(numbers[i]))
                return null;
        }
        if (sw <= 0 || sh <= 0 || ww <= 0 || wh <= 0)
            return null;

        // If both edges anchor a dimension, the window stretches from the
        // leading edge. If neither is anchored, layer-shell centers it.
        const x = anchors.left ? sx + ml
                : anchors.right ? sx + sw - ww - mr
                : sx + (sw - ww) / 2;
        const y = anchors.top ? sy + mt
                : anchors.bottom ? sy + sh - wh - mb
                : sy + (sh - wh) / 2;
        if (!isFinite(x) || !isFinite(y))
            return null;

        return {
            x: Math.round(x),
            y: Math.round(y),
            w: Math.round(ww),
            h: Math.round(wh)
        };
    }

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

            const rect = panelRect(w);
            if (!rect)
                continue;
            result.push({
                id: row.id,
                x: rect.x,
                y: rect.y,
                w: rect.w,
                h: rect.h
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
