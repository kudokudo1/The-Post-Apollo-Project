import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: tracker

    property int intervalMs: 8
    property bool running: true
    property string errorText: ""
    property var lastPayload: null

    signal snapshot(var payload)
    signal bridgeError(string message)
    signal bridgeReady()

    Process {
        id: bridgeProcess

        command: [
            "python3",
            Quickshell.shellPath("services/windowassembly/WindowAssemblyBridge.py"),
            "--interval-ms",
            String(Math.max(1, tracker.intervalMs))
        ]

        running: tracker.running
        stdinEnabled: true

        stdout: SplitParser {
            onRead: function(data) {
                const raw = String(data || "").trim();

                if (raw.length === 0)
                    return;

                try {
                    const payload = JSON.parse(raw);

                    tracker.lastPayload = payload;

                    if (payload.op === "snapshot") {
                        tracker.snapshot(payload);
                        return;
                    }

                    if (payload.op === "error") {
                        tracker.errorText = String(payload.message || "window assembly bridge error");
                        tracker.bridgeError(tracker.errorText);
                        return;
                    }

                    if (payload.op === "defined") {
                        tracker.errorText = "";
                        tracker.bridgeReady();
                    }
                } catch (error) {
                    tracker.errorText = "WindowAssemblyTracker JSON: " + String(error);
                    tracker.bridgeError(tracker.errorText);
                }
            }
        }

        stderr: SplitParser {
            onRead: function(data) {
                const message = String(data || "").trim();

                if (message.length === 0)
                    return;

                tracker.errorText = message;
                tracker.bridgeError(message);
            }
        }
    }

    function send(payload) {
        if (!bridgeProcess.running)
            return false;

        bridgeProcess.write(JSON.stringify(payload) + "\n");
        return true;
    }

    function rect(x, y, width, height) {
        return {
            x: Math.round(Number(x)),
            y: Math.round(Number(y)),
            width: Math.max(1, Math.round(Number(width))),
            height: Math.max(1, Math.round(Number(height)))
        };
    }

    function transform(xRel, xPx, yRel, yPx, wRel, wPx, hRel, hPx) {
        return {
            xRel: Number(xRel),
            xPx: Number(xPx),
            yRel: Number(yRel),
            yPx: Number(yPx),
            wRel: Number(wRel),
            wPx: Number(wPx),
            hRel: Number(hRel),
            hPx: Number(hPx)
        };
    }

    function member(id, match, transformSpec, options) {
        const opts = options || {};

        return {
            id: String(id),
            match: match,
            transform: transformSpec,
            canLead: opts.canLead !== false,
            enabled: opts.enabled !== false,
            setup: opts.setup !== false,
            focusAfterSync: opts.focusAfterSync === true,
            tolerance: Math.max(0, Math.round(Number(opts.tolerance || 0)))
        };
    }

    function defineScene(sceneId, sceneRect, members, options) {
        const opts = options || {};

        return send({
            op: "define",
            scene: String(sceneId),
            rect: sceneRect,
            members: members,
            minimumWidth: Math.max(1, Math.round(Number(opts.minimumWidth || 1))),
            minimumHeight: Math.max(1, Math.round(Number(opts.minimumHeight || 1))),
            watch: opts.watch === true,
            sync: opts.sync !== false
        });
    }

    function setSceneRect(sceneId, sceneRect, syncFollowers) {
        return send({
            op: "scene",
            scene: String(sceneId),
            rect: sceneRect,
            sync: syncFollowers !== false
        });
    }

    function watchScene(sceneId, enabled) {
        return send({
            op: "watch",
            scene: String(sceneId),
            enabled: enabled === true
        });
    }

    function sampleScene(sceneId) {
        return send({
            op: "sample",
            scene: String(sceneId)
        });
    }

    function syncMember(sceneId, memberId, memberRect, options) {
        const opts = options || {};

        return send({
            op: "sync",
            scene: String(sceneId),
            member: String(memberId),
            rect: memberRect,
            focus: opts.focus === true,
            setup: opts.setup !== false
        });
    }

    function removeScene(sceneId) {
        return send({
            op: "remove",
            scene: String(sceneId)
        });
    }
}
