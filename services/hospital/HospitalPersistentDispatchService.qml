import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property bool busy: false
    property string status: "READY"
    property string lastError: ""
    property string pendingRoomId: ""
    property string pendingBody: ""
    property string pendingWorkingDirectory: ""
    property string pendingChannel: "INTERCOM"
    property var pendingSpecialist: null
    property var sessionRows: []
    property string targetSessionId: ""
    property var lastTurnResult: null

    signal dispatchStarted(string roomId, string sessionId)
    signal dispatchCompleted(string roomId, string sessionId, var result)
    signal dispatchFailed(string roomId, string message)

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];
        return [
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-persistent-dispatch"
        ].concat(suffix);
    }

    function compactError(value) {
        const detail = String(value || "").trim();
        if (!detail)
            return "";

        const rows = detail.split("\n").map(function(row) {
            return String(row || "").trim();
        }).filter(function(row) {
            return row.length > 0;
        });

        let message = rows.length > 0 ? rows[rows.length - 1] : detail;
        if (message.length > 260)
            message = message.slice(0, 257) + "...";
        return message;
    }

    function liveSessions(rows) {
        const source = Array.isArray(rows) ? rows : [];
        return source.filter(function(row) {
            const status = String((row || {}).status || "").toUpperCase();
            return status !== "COMPLETE" && status !== "FAILED";
        });
    }

    function compatibleSession(rows, specialistValue) {
        const candidates = liveSessions(rows);
        const specialist = specialistValue || {};
        const wantedDoctor = String(specialist.id || "").trim();
        const wantedProvider =
            String(specialist.provider || "").trim().toLowerCase();

        if (wantedDoctor) {
            for (let i = 0; i < candidates.length; ++i) {
                if (String((candidates[i] || {}).doctorId || "") === wantedDoctor)
                    return candidates[i];
            }
        }

        if (wantedProvider) {
            const providerMatches = candidates.filter(function(row) {
                return String((row || {}).providerId || "")
                    .trim().toLowerCase() === wantedProvider;
            });

            if (providerMatches.length === 1)
                return providerMatches[0];
        }

        if (candidates.length === 1)
            return candidates[0];

        return null;
    }

    function dispatchToRoom(
        roomIdValue,
        bodyValue,
        specialistValue,
        workingDirectoryValue,
        channelValue
    ) {
        const roomId = String(roomIdValue || "").trim();
        const body = String(bodyValue || "").trim();

        if (!roomId || !body || busy)
            return false;

        pendingRoomId = roomId;
        pendingBody = body;
        pendingSpecialist = specialistValue || null;
        pendingWorkingDirectory =
            String(workingDirectoryValue || "").trim();
        pendingChannel =
            String(channelValue || "INTERCOM").trim().toUpperCase()
            || "INTERCOM";
        targetSessionId = "";
        sessionRows = [];
        lastTurnResult = null;
        lastError = "";
        status = pendingChannel + " // RESOLVING ROOM DOCTOR";
        busy = true;

        sessionsProcess.exec(pxArgs([
            "hospital",
            "sessions",
            "--room-id",
            roomId,
            "--json"
        ]));
        return true;
    }

    function startTurn() {
        const sessionId = String(targetSessionId || "").trim();

        if (!sessionId || !pendingBody) {
            fail("NO UNIQUE ACTIVE DOCTOR SESSION");
            return false;
        }

        const args = [
            "agent",
            "turn",
            sessionId,
            "--prompt-json-stdin",
            "--author-id",
            "operator",
            "--message-type",
            "chat"
        ];

        if (pendingWorkingDirectory) {
            args.push("--working-directory");
            args.push(pendingWorkingDirectory);
        }

        args.push("--json");
        status =
            pendingChannel
            + " // SENDING // SESSION "
            + sessionId;
        dispatchStarted(pendingRoomId, sessionId);
        turnProcess.exec(pxArgs(args));
        return true;
    }

    function fail(messageValue) {
        const room = pendingRoomId;
        const message =
            String(messageValue || "PERSISTENT DISPATCH FAILED").trim();

        lastError =
            pendingChannel
            + " STOPPED // "
            + message;
        status = "";
        busy = false;
        dispatchFailed(room, lastError);
        clearPending();
    }

    function clearPending() {
        pendingRoomId = "";
        pendingBody = "";
        pendingWorkingDirectory = "";
        pendingChannel = "INTERCOM";
        pendingSpecialist = null;
        sessionRows = [];
        targetSessionId = "";
    }

    Process {
        id: sessionsProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                try {
                    const result = JSON.parse(body || "[]");
                    if (!Array.isArray(result))
                        throw new Error("sessions returned non-array data");
                    root.sessionRows = result;
                } catch (error) {
                    root.lastError =
                        "ROOM SESSION LOOKUP // "
                        + root.compactError(body || error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = root.compactError(this.text);
                if (detail)
                    root.lastError = "ROOM SESSION LOOKUP // " + detail;
            }
        }

        onExited: function(code, exitStatus) {
            if (Number(code) !== 0 || root.lastError) {
                root.fail(
                    root.lastError
                    || ("SESSION LOOKUP EXIT " + String(code))
                );
                return;
            }

            const matched = root.compatibleSession(
                root.sessionRows,
                root.pendingSpecialist
            );

            if (!matched) {
                const liveCount =
                    root.liveSessions(root.sessionRows).length;
                root.fail(
                    liveCount > 1
                    ? "MULTIPLE ACTIVE DOCTOR SESSIONS // TARGET AMBIGUOUS"
                    : "NO ACTIVE DOCTOR SESSION"
                );
                return;
            }

            root.targetSessionId = String(matched.id || "");
            root.startTurn();
        }
    }

    Process {
        id: turnProcess

        stdinEnabled: true

        onStarted: {
            turnProcess.write(
                JSON.stringify({
                    prompt: root.pendingBody
                }) + "\n"
            );
        }

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                if (!body)
                    return;

                try {
                    root.lastTurnResult = JSON.parse(body);
                } catch (error) {
                    root.lastError =
                        "DOCTOR TURN // "
                        + root.compactError(body || error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = root.compactError(this.text);
                if (detail)
                    root.lastError = "DOCTOR TURN // " + detail;
            }
        }

        onExited: function(code, exitStatus) {
            const room = root.pendingRoomId;
            const session = root.targetSessionId;
            const result = root.lastTurnResult;

            if (Number(code) === 0
                    && !root.lastError
                    && result) {
                root.status =
                    root.pendingChannel
                    + " // DELIVERED // ROOM "
                    + room;
                root.busy = false;
                root.dispatchCompleted(room, session, result);
                root.clearPending();
                return;
            }

            root.fail(
                root.lastError
                || ("DOCTOR TURN EXIT " + String(code))
            );
        }
    }
}
