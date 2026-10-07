import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string sessionId: ""

    property string status: "IDLE"
    property int activePid: 0
    property string turnStartedAt: ""
    property int elapsedSeconds: 0
    property bool operating: false

    property bool refreshing: false
    property bool cancelling: false
    property bool quickRunning: false
    property string quickCommand: ""
    property string lastError: ""
    property var lastStatusPayload: null
    property var lastCancelResult: null
    property var lastQuickResult: null

    readonly property string displayStatus:
        cancelling
        ? "STOPPING"
        : sessionId.length === 0
        ? "NO SESSION"
        : status

    readonly property string elapsedLabel:
        formatElapsed(elapsedSeconds)

    signal statusRefreshed()
    signal turnCancelled(var result)
    signal quickCompleted(string command, var result)

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];

        return [
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-doctor-runtime"
        ].concat(suffix);
    }

    function compactPxError(value, context) {
        const detail = String(value || "").trim();

        if (!detail)
            return "";

        const lower = detail.toLowerCase();

        if (lower.indexOf("unknown command agent") >= 0
                || lower.indexOf("post-apollo px control bus") >= 0)
            return "PX RUNTIME OUT OF DATE // UPDATE POST-APOLLO DEV EXPERIENCE";

        const rows = detail.split("\n").map(function(row) {
            return String(row || "").trim();
        }).filter(function(row) {
            return row.length > 0;
        });

        let message =
            rows.length > 0
            ? rows[rows.length - 1]
            : detail;

        if (message.length > 240)
            message = message.slice(0, 237) + "...";

        const prefix = String(context || "").trim();
        return prefix ? prefix + " // " + message : message;
    }

    function formatElapsed(value) {
        const total = Math.max(0, Number(value || 0));
        const hours = Math.floor(total / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        const seconds = Math.floor(total % 60);

        function pad(part) {
            return part < 10 ? "0" + String(part) : String(part);
        }

        if (hours > 0)
            return String(hours) + ":" + pad(minutes) + ":" + pad(seconds);

        return pad(minutes) + ":" + pad(seconds);
    }

    function resetRuntime() {
        status = "IDLE";
        activePid = 0;
        turnStartedAt = "";
        elapsedSeconds = 0;
        operating = false;
        lastStatusPayload = null;
        lastError = "";
    }

    function applyStatus(payload) {
        const data = payload || {};
        const session = data.session || {};

        lastStatusPayload = data;
        status = String(
            data.status
            || session.status
            || "IDLE"
        ).toUpperCase();
        activePid = Number(
            data.activePid
            || session.activePid
            || 0
        );
        turnStartedAt = String(
            data.turnStartedAt
            || session.turnStartedAt
            || ""
        );
        elapsedSeconds = Math.max(
            0,
            Number(data.elapsedSeconds || 0)
        );
        operating =
            data.operating === true
            || (
                status === "OPERATING"
                && activePid > 0
            );
    }

    function refresh() {
        const id = String(sessionId || "").trim();

        if (!id) {
            resetRuntime();
            return false;
        }

        if (refreshing || statusProcess.running)
            return false;

        refreshing = true;
        lastError = "";

        statusProcess.exec(pxArgs([
            "agent",
            "status",
            id,
            "--json"
        ]));
        return true;
    }

    function cancel(reasonValue) {
        const id = String(sessionId || "").trim();

        if (!id || cancelling || cancelProcess.running)
            return false;

        cancelling = true;
        lastError = "";
        lastCancelResult = null;

        cancelProcess.exec(pxArgs([
            "agent",
            "cancel",
            id,
            "--reason",
            String(reasonValue || "OPERATOR"),
            "--json"
        ]));
        return true;
    }

    function quick(commandValue) {
        const id = String(sessionId || "").trim();
        const command =
            String(commandValue || "").trim().toUpperCase();
        const allowed = [
            "GO",
            "CONTINUE",
            "STATUS",
            "REPORT",
            "CHECKLIST",
            "NEXT",
            "PAUSE"
        ];

        if (!id || quickRunning || quickProcess.running)
            return false;

        if (allowed.indexOf(command) < 0) {
            lastError =
                "HOSPITAL QUICK // UNKNOWN COMMAND // " + command;
            return false;
        }

        if (operating
                && command !== "STATUS"
                && command !== "PAUSE") {
            lastError =
                "HOSPITAL QUICK // DOCTOR ALREADY OPERATING";
            return false;
        }

        quickRunning = true;
        quickCommand = command;
        lastError = "";
        lastQuickResult = null;

        quickProcess.exec(pxArgs([
            "agent",
            "quick",
            id,
            command,
            "--json"
        ]));
        return true;
    }

    onSessionIdChanged: {
        resetRuntime();

        if (sessionId)
            Qt.callLater(root.refresh);
    }

    Process {
        id: statusProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    root.applyStatus(JSON.parse(body));
                    root.lastError = "";
                } catch (error) {
                    root.lastError = root.compactPxError(
                        body || error,
                        "HOSPITAL DOCTOR STATUS"
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();

                if (detail)
                    root.lastError = root.compactPxError(
                        detail,
                        "HOSPITAL DOCTOR STATUS"
                    );
            }
        }

        onExited: function(code, exitStatus) {
            root.refreshing = false;

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX AGENT STATUS EXIT " + String(code);

            root.statusRefreshed();
        }
    }

    Process {
        id: cancelProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    root.lastCancelResult = JSON.parse(body);

                    if (root.lastCancelResult.session)
                        root.applyStatus({
                            session: root.lastCancelResult.session,
                            status:
                                root.lastCancelResult.session.status,
                            activePid:
                                root.lastCancelResult.session.activePid,
                            turnStartedAt:
                                root.lastCancelResult.session.turnStartedAt,
                            elapsedSeconds: 0,
                            operating: false
                        });
                } catch (error) {
                    root.lastError = root.compactPxError(
                        body || error,
                        "HOSPITAL DOCTOR STOP"
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();

                if (detail)
                    root.lastError = root.compactPxError(
                        detail,
                        "HOSPITAL DOCTOR STOP"
                    );
            }
        }

        onExited: function(code, exitStatus) {
            root.cancelling = false;

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX AGENT CANCEL EXIT " + String(code);

            if (Number(code) === 0 && root.lastCancelResult)
                root.turnCancelled(root.lastCancelResult);

            Qt.callLater(root.refresh);
        }
    }

    Process {
        id: quickProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    root.lastQuickResult = JSON.parse(body);
                    root.lastError = "";
                } catch (error) {
                    root.lastError = root.compactPxError(
                        body || error,
                        "HOSPITAL QUICK"
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();

                if (detail)
                    root.lastError = root.compactPxError(
                        detail,
                        "HOSPITAL QUICK"
                    );
            }
        }

        onExited: function(code, exitStatus) {
            const completedCommand = root.quickCommand;
            root.quickRunning = false;
            root.quickCommand = "";

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX AGENT QUICK EXIT " + String(code);

            if (Number(code) === 0 && root.lastQuickResult)
                root.quickCompleted(
                    completedCommand,
                    root.lastQuickResult
                );

            Qt.callLater(root.refresh);
        }
    }

    Timer {
        id: pollTimer

        interval: root.operating ? 1000 : 3000
        repeat: true
        running:
            root.sessionId.length > 0
            && !root.cancelling

        onTriggered: root.refresh()
    }

    Component.onCompleted: {
        if (sessionId)
            refresh();
    }
}
