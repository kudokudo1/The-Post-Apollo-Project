import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string patientId: ""
    property string roomId: ""
    property string sourceSessionId: ""

    property var patientEntries: []
    property var roomEntries: []

    property bool patientLoading: false
    property bool roomLoading: false
    property bool writing: false
    property string lastError: ""
    property var lastWriteResult: null

    readonly property int patientActiveCount:
        activeCount(patientEntries)
    readonly property int roomActiveCount:
        activeCount(roomEntries)
    readonly property bool loading:
        patientLoading || roomLoading

    signal entriesRefreshed()
    signal entrySaved(var entry)
    signal entryStatusChanged(var entry)

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];

        return [
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-chart-manager"
        ].concat(suffix);
    }

    function compactPxError(value) {
        const detail = String(value || "").trim();

        if (!detail)
            return "";

        const lower = detail.toLowerCase();
        if (lower.indexOf("unknown command hospital") >= 0
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

        if (message.length > 260)
            message = message.slice(0, 257) + "...";

        return "HOSPITAL CHART // " + message;
    }

    function activeCount(entries) {
        const source = Array.isArray(entries) ? entries : [];
        let count = 0;

        for (let i = 0; i < source.length; ++i) {
            if (String((source[i] || {}).status || "") === "ACTIVE")
                ++count;
        }

        return count;
    }

    function entriesForScope(scopeValue) {
        return String(scopeValue || "").toUpperCase() === "PATIENT"
            ? patientEntries
            : roomEntries;
    }

    function clear() {
        patientEntries = [];
        roomEntries = [];
        patientLoading = false;
        roomLoading = false;
        lastError = "";
    }

    function refreshPatient() {
        const id = String(patientId || "").trim();

        if (!id) {
            patientEntries = [];
            return false;
        }

        if (patientLoading || patientListProcess.running)
            return false;

        patientLoading = true;
        lastError = "";

        patientListProcess.exec(pxArgs([
            "hospital",
            "chart-entries",
            "--scope",
            "PATIENT",
            "--patient-id",
            id,
            "--status",
            "ALL",
            "--limit",
            "200",
            "--json"
        ]));
        return true;
    }

    function refreshRoom() {
        const id = String(roomId || "").trim();

        if (!id) {
            roomEntries = [];
            return false;
        }

        if (roomLoading || roomListProcess.running)
            return false;

        roomLoading = true;
        lastError = "";

        roomListProcess.exec(pxArgs([
            "hospital",
            "chart-entries",
            "--scope",
            "ROOM",
            "--room-id",
            id,
            "--status",
            "ALL",
            "--limit",
            "200",
            "--json"
        ]));
        return true;
    }

    function refreshAll() {
        const patientStarted = refreshPatient();
        const roomStarted = refreshRoom();
        return patientStarted || roomStarted;
    }

    function addEntry(
        scopeValue,
        kindValue,
        titleValue,
        priorityValue,
        bodyValue,
        supersedesIdValue
    ) {
        const scope = String(scopeValue || "").trim().toUpperCase();
        const body = String(bodyValue || "").trim();
        const kind =
            String(kindValue || "NOTE").trim().toUpperCase() || "NOTE";
        const title = String(titleValue || "").trim();
        const priority = Math.max(
            0,
            Math.min(100, Number(priorityValue || 50))
        );
        const supersedesId =
            String(supersedesIdValue || "").trim();

        if (writing || writeProcess.running)
            return false;

        if (scope !== "PATIENT" && scope !== "ROOM") {
            lastError = "HOSPITAL CHART // UNKNOWN SCOPE // " + scope;
            return false;
        }

        if (!body) {
            lastError = "HOSPITAL CHART // ENTRY BODY IS EMPTY";
            return false;
        }

        if (scope === "PATIENT" && !patientId) {
            lastError = "HOSPITAL CHART // NO PATIENT";
            return false;
        }

        if (scope === "ROOM" && !roomId) {
            lastError = "HOSPITAL CHART // NO ROOM";
            return false;
        }

        const args = [
            "hospital",
            "chart-entry-add",
            "--scope",
            scope,
            "--entry-kind",
            kind,
            "--title",
            title,
            "--priority",
            String(Math.round(priority)),
            "--author-role",
            "operator",
            "--author-id",
            "operator",
            "--source-type",
            "HOSPITAL_UI"
        ];

        if (scope === "PATIENT") {
            args.push("--patient-id", String(patientId));
        } else {
            args.push("--room-id", String(roomId));
        }

        if (roomId) {
            args.push("--source-room-id", String(roomId));
        }

        if (sourceSessionId) {
            args.push(
                "--source-session-id",
                String(sourceSessionId)
            );
        }

        if (supersedesId) {
            args.push("--supersedes-id", supersedesId);
        }

        args.push("--body", body, "--json");

        writing = true;
        lastWriteResult = null;
        lastError = "";
        pendingWriteOperation = "ADD";
        writeProcess.exec(pxArgs(args));
        return true;
    }

    function setEntryStatus(entryIdValue, statusValue) {
        const entryId = String(entryIdValue || "").trim();
        const status =
            String(statusValue || "").trim().toUpperCase();

        if (writing || writeProcess.running)
            return false;

        if (!entryId) {
            lastError = "HOSPITAL CHART // NO ENTRY SELECTED";
            return false;
        }

        if (["ACTIVE", "RESOLVED", "ARCHIVED"].indexOf(status) < 0) {
            lastError =
                "HOSPITAL CHART // INVALID STATUS // " + status;
            return false;
        }

        writing = true;
        lastWriteResult = null;
        lastError = "";
        pendingWriteOperation = "STATUS";
        writeProcess.exec(pxArgs([
            "hospital",
            "chart-entry-status",
            entryId,
            status,
            "--json"
        ]));
        return true;
    }

    property string pendingWriteOperation: ""

    onPatientIdChanged: {
        patientEntries = [];
        if (patientId)
            Qt.callLater(root.refreshPatient);
    }

    onRoomIdChanged: {
        roomEntries = [];
        if (roomId)
            Qt.callLater(root.refreshRoom);
    }

    Process {
        id: patientListProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();
                if (!body)
                    return;

                try {
                    const result = JSON.parse(body);
                    if (!Array.isArray(result))
                        throw new Error("Patient Chart returned non-array data");

                    root.patientEntries = result;
                    root.lastError = "";
                } catch (error) {
                    root.patientEntries = [];
                    root.lastError = root.compactPxError(
                        body || error
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    root.lastError = root.compactPxError(detail);
            }
        }

        onExited: function(code, exitStatus) {
            root.patientLoading = false;
            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX PATIENT CHART EXIT " + String(code);
            root.entriesRefreshed();
        }
    }

    Process {
        id: roomListProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();
                if (!body)
                    return;

                try {
                    const result = JSON.parse(body);
                    if (!Array.isArray(result))
                        throw new Error("Room Chart returned non-array data");

                    root.roomEntries = result;
                    root.lastError = "";
                } catch (error) {
                    root.roomEntries = [];
                    root.lastError = root.compactPxError(
                        body || error
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    root.lastError = root.compactPxError(detail);
            }
        }

        onExited: function(code, exitStatus) {
            root.roomLoading = false;
            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX ROOM CHART EXIT " + String(code);
            root.entriesRefreshed();
        }
    }

    Process {
        id: writeProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();
                if (!body)
                    return;

                try {
                    root.lastWriteResult = JSON.parse(body);
                    root.lastError = "";
                } catch (error) {
                    root.lastWriteResult = null;
                    root.lastError = root.compactPxError(
                        body || error
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    root.lastError = root.compactPxError(detail);
            }
        }

        onExited: function(code, exitStatus) {
            const operation = root.pendingWriteOperation;
            root.writing = false;
            root.pendingWriteOperation = "";

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX HOSPITAL CHART WRITE EXIT " + String(code);

            if (Number(code) === 0 && root.lastWriteResult) {
                if (operation === "ADD")
                    root.entrySaved(root.lastWriteResult);
                else if (operation === "STATUS")
                    root.entryStatusChanged(root.lastWriteResult);
            }

            Qt.callLater(root.refreshAll);
        }
    }

    Component.onCompleted: refreshAll()
}
