import QtQuick
import Quickshell
import Quickshell.Io

// ROOM CONTINUITY // read-only, exact-Room PX snapshot.
// One scoped read runs at a time, only while its Room view is open.
// On Room switches, prior results are discarded, never transferred.
// No provider launch, Session creation, room-bind, report or Chart write.
Scope {
    id: root
    property string roomId: ""
    property bool enabled: false
    property var snapshot: ({})
    property bool loading: false
    property bool loaded: false
    property string lastError: ""
    property string requestedRoomId: ""
    property string readStage: ""
    property int stageIndex: 0
    property bool refreshPending: false
    property bool refreshScheduled: false
    property var pendingSnapshot: ({})
    readonly property var stages: [
        "room", "assignments", "checkpoints", "reports",
        "roomChart", "patientChart"
    ]

    signal snapshotRefreshed()

    function pxArgs(args) {
        return [
            "bash", "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-room-continuity"
        ].concat(args);
    }

    function clearVisible() {
        snapshot = ({});
        loaded = false;
        lastError = "";
    }

    function scheduleRefresh() {
        if (root.refreshScheduled)
            return;
        root.refreshScheduled = true;
        Qt.callLater(function() {
            root.refreshScheduled = false;
            if (root.enabled && root.roomId)
                root.refresh();
        });
    }

    function refresh() {
        const id = String(root.roomId || "").trim();
        if (!root.enabled || !id) {
            clearVisible();
            return false;
        }
        if (reader.running || root.loading) {
            root.refreshPending = true;
            return false;
        }
        root.refreshPending = false;
        root.requestedRoomId = id;
        root.stageIndex = 0;
        root.pendingSnapshot = ({});
        root.readStage = "";
        root.loading = true;
        clearVisible();
        Qt.callLater(root.readNext);
        return true;
    }

    function readNext() {
        if (!root.loading)
            return;
        const id = String(root.roomId || "").trim();
        if (!root.enabled || !id || id !== root.requestedRoomId) {
            root.loading = false;
            if (root.enabled && id)
                Qt.callLater(root.refresh);
            return;
        }
        if (root.stageIndex >= root.stages.length) {
            root.snapshot = root.pendingSnapshot;
            root.loaded = true;
            root.loading = false;
            root.readStage = "";
            root.snapshotRefreshed();
            if (root.refreshPending)
                Qt.callLater(root.refresh);
            return;
        }

        const stage = root.stages[root.stageIndex];
        const patientId = String((root.pendingSnapshot.room || {}).patientId || "");
        if (stage === "patientChart" && !patientId) {
            root.pendingSnapshot.patientChart = [];
            root.stageIndex++;
            Qt.callLater(root.readNext);
            return;
        }
        const commands = {
            room: ["hospital", "room", id, "--json"],
            assignments: ["hospital", "assignments", "--room-id", id,
                          "--status", "ALL", "--limit", "200", "--json"],
            checkpoints: ["hospital", "checkpoints", id, "--limit", "20", "--json"],
            reports: ["hospital", "room-reports", id, "--limit", "50", "--json"],
            roomChart: ["hospital", "chart-entries", "--scope", "ROOM",
                        "--room-id", id, "--status", "ACTIVE",
                        "--limit", "60", "--json"],
            patientChart: ["hospital", "chart-entries", "--scope", "PATIENT",
                           "--patient-id", patientId, "--status", "ACTIVE",
                           "--limit", "60", "--json"]
        };
        root.readStage = stage;
        reader.outputText = "";
        reader.errorText = "";
        reader.exec(root.pxArgs(commands[stage]));
    }

    function validate(stage, payload) {
        const id = root.requestedRoomId;
        if (stage === "room") {
            if (!payload || Array.isArray(payload)
                    || String(payload.id || "") !== id)
                throw new Error("PX returned a different Room identity");
            return payload;
        }
        if (!Array.isArray(payload))
            throw new Error("PX returned a non-array " + stage);
        const patientId = String((root.pendingSnapshot.room || {}).patientId || "");
        for (let i = 0; i < payload.length; ++i) {
            const row = payload[i];
            if (!row || typeof row !== "object")
                throw new Error("PX returned malformed " + stage);
            if (stage === "patientChart") {
                if (String(row.scope || "") !== "PATIENT"
                        || String(row.patientId || "") !== patientId
                        || String(row.status || "") !== "ACTIVE")
                    throw new Error("PX returned foreign Patient Chart");
            } else if (String(row.roomId || "") !== id) {
                throw new Error("PX returned foreign Room " + stage);
            } else if (stage === "roomChart"
                    && (String(row.scope || "") !== "ROOM"
                        || String(row.status || "") !== "ACTIVE")) {
                throw new Error("PX returned a non-active Room Chart");
            }
        }
        return payload;
    }

    onRoomIdChanged: {
        clearVisible();
        if (enabled && roomId)
            root.scheduleRefresh();
    }
    onEnabledChanged: {
        if (!enabled)
            clearVisible();
        else if (roomId)
            root.scheduleRefresh();
    }

    Process {
        id: reader
        property string outputText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: reader.outputText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: reader.errorText = String(this.text || "")
        }
        onExited: function(code, exitStatus) {
            const id = String(root.roomId || "").trim();
            if (!root.enabled || id !== root.requestedRoomId) {
                root.loading = false;
                root.readStage = "";
                if (root.enabled && id)
                    Qt.callLater(root.refresh);
                return;
            }
            try {
                if (Number(code) !== 0)
                    throw new Error(String(reader.errorText || reader.outputText
                        || "PX EXIT " + String(code)).trim().slice(0,200));
                const value = JSON.parse(String(reader.outputText || "null"));
                root.pendingSnapshot[root.readStage] =
                    root.validate(root.readStage, value);
                root.stageIndex++;
                Qt.callLater(root.readNext);
            } catch (error) {
                root.loading = false;
                root.loaded = false;
                root.pendingSnapshot = ({});
                root.snapshot = ({});
                root.lastError = "ROOM CONTINUITY // "
                    + root.readStage.toUpperCase() + " // "
                    + String(error).slice(0,210);
                root.readStage = "";
                root.snapshotRefreshed();
                if (root.refreshPending)
                    Qt.callLater(root.refresh);
            }
        }
    }
}
