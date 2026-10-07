import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string roomId: ""

    readonly property var allowedPermissions: [
        "READ",
        "EDIT",
        "TEST",
        "COMMIT",
        "PUSH",
        "OPEN_PR",
        "INTEGRATE"
    ]

    property var assignments: []
    property bool loading: false
    property bool writing: false
    property string lastError: ""
    property var lastWriteResult: null
    property string pendingOperation: ""

    readonly property int assignmentCount: assignments.length
    readonly property var activeAssignment: {
        for (let i = 0; i < assignments.length; ++i) {
            const row = assignments[i] || {};
            if (String(row.status || "") === "ACTIVE")
                return row;
        }
        return null;
    }

    signal assignmentsRefreshed()
    signal assignmentSaved(var assignment)
    signal assignmentActivated(var result)
    signal assignmentStatusChanged(var assignment)

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];

        return [
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-assignment-manager"
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

        let message = rows.length > 0 ? rows[rows.length - 1] : detail;
        if (message.length > 260)
            message = message.slice(0, 257) + "...";

        return "HOSPITAL ORDERS // " + message;
    }

    function refresh() {
        const room = String(roomId || "").trim();

        if (!room) {
            assignments = [];
            return false;
        }

        if (loading || listProcess.running)
            return false;

        loading = true;
        lastError = "";
        listProcess.exec(pxArgs([
            "hospital",
            "assignments",
            "--room-id",
            room,
            "--status",
            "ALL",
            "--limit",
            "200",
            "--json"
        ]));
        return true;
    }

    function permissionList(value) {
        const raw = String(value || "");
        const parts = raw.split(/[,\s]+/);
        const out = [];

        for (let i = 0; i < parts.length; ++i) {
            const item = String(parts[i] || "")
                .trim()
                .toUpperCase()
                .replace(/-/g, "_");
            if (item
                    && allowedPermissions.indexOf(item) >= 0
                    && out.indexOf(item) < 0)
                out.push(item);
        }

        if (out.indexOf("READ") < 0)
            out.unshift("READ");
        return out;
    }

    function createAssignment(
        titleValue,
        goalValue,
        constraintsValue,
        definitionValue,
        permissionsValue,
        checklistValue,
        questionsValue,
        phaseValue
    ) {
        const room = String(roomId || "").trim();
        const goal = String(goalValue || "").trim();

        if (!room || !goal || writing || writeProcess.running)
            return false;

        const args = [
            "hospital",
            "assignment-create",
            "--room-id",
            room,
            "--title",
            String(titleValue || "").trim(),
            "--goal",
            goal,
            "--constraints",
            String(constraintsValue || ""),
            "--definition-done",
            String(definitionValue || ""),
            "--permissions-json",
            JSON.stringify(permissionList(permissionsValue)),
            "--checklist",
            String(checklistValue || ""),
            "--open-questions",
            String(questionsValue || ""),
            "--phase",
            String(phaseValue || "PLANNING").trim().toUpperCase(),
            "--created-by-role",
            "operator",
            "--created-by-id",
            "operator",
            "--json"
        ];

        writing = true;
        pendingOperation = "CREATE";
        lastWriteResult = null;
        lastError = "";
        writeProcess.exec(pxArgs(args));
        return true;
    }

    function updateAssignment(
        assignmentIdValue,
        titleValue,
        goalValue,
        constraintsValue,
        definitionValue,
        permissionsValue,
        checklistValue,
        questionsValue,
        phaseValue
    ) {
        const id = String(assignmentIdValue || "").trim();
        const goal = String(goalValue || "").trim();

        if (!id || !goal || writing || writeProcess.running)
            return false;

        writing = true;
        pendingOperation = "UPDATE";
        lastWriteResult = null;
        lastError = "";
        writeProcess.exec(pxArgs([
            "hospital",
            "assignment-update",
            id,
            "--title",
            String(titleValue || "").trim(),
            "--goal",
            goal,
            "--constraints",
            String(constraintsValue || ""),
            "--definition-done",
            String(definitionValue || ""),
            "--permissions-json",
            JSON.stringify(permissionList(permissionsValue)),
            "--checklist",
            String(checklistValue || ""),
            "--open-questions",
            String(questionsValue || ""),
            "--phase",
            String(phaseValue || "PLANNING").trim().toUpperCase(),
            "--json"
        ]));
        return true;
    }

    function activateAssignment(assignmentIdValue) {
        const id = String(assignmentIdValue || "").trim();
        if (!id || writing || writeProcess.running)
            return false;

        writing = true;
        pendingOperation = "ACTIVATE";
        lastWriteResult = null;
        lastError = "";
        writeProcess.exec(pxArgs([
            "hospital",
            "assignment-activate",
            id,
            "--json"
        ]));
        return true;
    }

    function setAssignmentStatus(assignmentIdValue, statusValue) {
        const id = String(assignmentIdValue || "").trim();
        const status = String(statusValue || "").trim().toUpperCase();

        if (!id || writing || writeProcess.running)
            return false;

        if ([
            "DRAFT", "READY", "ACTIVE", "PAUSED",
            "COMPLETE", "CANCELLED"
        ].indexOf(status) < 0) {
            lastError = "HOSPITAL ORDERS // INVALID STATUS // " + status;
            return false;
        }

        writing = true;
        pendingOperation = "STATUS";
        lastWriteResult = null;
        lastError = "";
        writeProcess.exec(pxArgs([
            "hospital",
            "assignment-status",
            id,
            status,
            "--json"
        ]));
        return true;
    }

    onRoomIdChanged: {
        assignments = [];
        if (roomId)
            Qt.callLater(root.refresh);
    }

    Process {
        id: listProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();
                if (!body)
                    return;

                try {
                    const result = JSON.parse(body);
                    if (!Array.isArray(result))
                        throw new Error("Assignments returned non-array data");
                    root.assignments = result;
                    root.lastError = "";
                } catch (error) {
                    root.assignments = [];
                    root.lastError = root.compactPxError(body || error);
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
            root.loading = false;
            if (Number(code) !== 0 && !root.lastError)
                root.lastError = "PX HOSPITAL ASSIGNMENTS EXIT " + String(code);
            root.assignmentsRefreshed();
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
                    root.lastError = root.compactPxError(body || error);
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
            const operation = root.pendingOperation;
            root.writing = false;
            root.pendingOperation = "";

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX HOSPITAL ASSIGNMENT WRITE EXIT " + String(code);

            if (Number(code) === 0 && root.lastWriteResult) {
                if (operation === "ACTIVATE")
                    root.assignmentActivated(root.lastWriteResult);
                else if (operation === "STATUS")
                    root.assignmentStatusChanged(root.lastWriteResult);
                else
                    root.assignmentSaved(root.lastWriteResult);
            }

            Qt.callLater(root.refresh);
        }
    }

    Component.onCompleted: refresh()
}
