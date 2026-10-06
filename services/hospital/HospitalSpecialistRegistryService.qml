import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property var specialists: []
    property bool loaded: false
    property bool probing: false
    property string lastError: ""
    property string lastRefreshedAt: ""

    property bool exitSeen: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property int exitCode: -1
    property string stdoutText: ""
    property string stderrText: ""

    signal registryLoaded()
    signal presenceRefreshed()

    readonly property int specialistCount: specialists.length
    readonly property int readyCount:
        specialists.filter(function(row) {
            return String((row || {}).presence || "") === "READY";
        }).length
    readonly property int offlineCount:
        specialists.filter(function(row) {
            return String((row || {}).presence || "") === "OFFLINE";
        }).length
    readonly property int unknownCount:
        specialists.filter(function(row) {
            return String((row || {}).presence || "") === "UNKNOWN";
        }).length
    readonly property int callableCount:
        specialists.filter(function(row) {
            const item = row || {};
            return !!item.callable
                && String(item.presence || "") === "READY";
        }).length

    function normalizeRecord(record) {
        const row = record || {};
        const capabilities =
            Array.isArray(row.capabilities)
            ? row.capabilities.map(function(value) {
                  return String(value || "").trim();
              }).filter(function(value) {
                  return value.length > 0;
              })
            : [];

        return {
            id: String(row.id || "").trim(),
            name: String(row.name || row.id || "SPECIALIST").trim(),
            provider: String(row.provider || "UNSPECIFIED").trim(),
            role: String(row.role || "SPECIALIST").trim(),
            kind: String(row.kind || "AGENT").trim(),
            transport: String(row.transport || "UNKNOWN").trim(),
            command: String(row.command || "").trim(),
            assignment: String(row.assignment || "UNASSIGNED").trim(),
            callable: !!row.callable,
            capabilities: capabilities,
            presence: "UNKNOWN",
            endpoint: "",
            lastSeen: ""
        };
    }

    function persistedRecord(record) {
        const row = record || {};

        return {
            id: String(row.id || ""),
            name: String(row.name || ""),
            provider: String(row.provider || ""),
            role: String(row.role || ""),
            kind: String(row.kind || ""),
            transport: String(row.transport || ""),
            command: String(row.command || ""),
            assignment: String(row.assignment || "UNASSIGNED"),
            callable: !!row.callable,
            capabilities:
                Array.isArray(row.capabilities)
                ? row.capabilities.slice()
                : []
        };
    }

    function loadRegistryFromDisk() {
        const raw = String(registryFile.text() || "").trim();

        if (!raw) {
            specialists = [];
            loaded = true;
            lastError = "SPECIALIST REGISTRY EMPTY";
            registryLoaded();
            return;
        }

        try {
            const parsed = JSON.parse(raw);
            const rows =
                parsed && Array.isArray(parsed.specialists)
                ? parsed.specialists
                : [];

            specialists = rows.map(function(row) {
                return root.normalizeRecord(row);
            }).filter(function(row) {
                return String(row.id || "").length > 0;
            });
            loaded = true;
            lastError = "";
            registryLoaded();
        } catch (error) {
            specialists = [];
            loaded = true;
            lastError = "SPECIALIST REGISTRY PARSE ERROR // " + String(error);
            registryLoaded();
        }
    }

    function persistRegistry() {
        registryFile.setText(JSON.stringify({
            version: 1,
            specialists: specialists.map(function(row) {
                return root.persistedRecord(row);
            })
        }, null, 2));
    }

    function specialistAt(index) {
        const requested = Number(index);

        if (requested < 0 || requested >= specialists.length)
            return null;

        return specialists[requested] || null;
    }

    function specialistById(value) {
        const id = String(value || "");

        for (let i = 0; i < specialists.length; ++i) {
            if (String((specialists[i] || {}).id || "") === id)
                return specialists[i];
        }

        return null;
    }

    function updateAssignment(idValue, assignmentValue) {
        const id = String(idValue || "");
        const assignment = String(assignmentValue || "UNASSIGNED").trim();
        const next = specialists.slice();
        let changed = false;

        for (let i = 0; i < next.length; ++i) {
            const row = next[i] || {};

            if (String(row.id || "") !== id)
                continue;

            next[i] = Object.assign({}, row, {
                assignment: assignment || "UNASSIGNED"
            });
            changed = true;
            break;
        }

        if (!changed)
            return false;

        specialists = next;
        persistRegistry();
        return true;
    }

    function refreshPresence() {
        if (probing || !loaded)
            return false;

        if (specialists.length === 0) {
            lastRefreshedAt = new Date().toLocaleString();
            presenceRefreshed();
            return true;
        }

        probing = true;
        lastError = "";
        exitSeen = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitCode = -1;
        stdoutText = "";
        stderrText = "";

        const args = [
            "bash",
            "-lc",
            [
                'while [ "$#" -ge 2 ]; do',
                '  id="$1"',
                '  cmd="$2"',
                '  shift 2',
                '  if [ -z "$cmd" ]; then',
                '    printf "%s\\tUNKNOWN\\t\\n" "$id"',
                '    continue',
                '  fi',
                '  if resolved="$(command -v "$cmd" 2>/dev/null)"; then',
                '    printf "%s\\tREADY\\t%s\\n" "$id" "$resolved"',
                '  else',
                '    printf "%s\\tOFFLINE\\t\\n" "$id"',
                '  fi',
                'done'
            ].join("\n"),
            "hospital-specialist-probe"
        ];

        for (let i = 0; i < specialists.length; ++i) {
            const row = specialists[i] || {};
            args.push(String(row.id || ""));
            args.push(String(row.command || ""));
        }

        probeProcess.exec(args);
        probeWatchdog.restart();
        return true;
    }

    function maybeFinishProbe() {
        if (!probing || !exitSeen || !stdoutSeen || !stderrSeen)
            return;

        probing = false;
        probeWatchdog.stop();

        if (exitCode !== 0) {
            lastError = String(
                stderrText
                || stdoutText
                || ("SPECIALIST PROBE EXIT " + exitCode)
            ).trim();
            return;
        }

        const presenceById = {};
        const rows = String(stdoutText || "").split(/\r?\n/);

        for (let i = 0; i < rows.length; ++i) {
            const line = String(rows[i] || "");

            if (!line)
                continue;

            const parts = line.split("\t");
            const id = String(parts[0] || "").trim();

            if (!id)
                continue;

            presenceById[id] = {
                presence: String(parts[1] || "UNKNOWN").trim(),
                endpoint: String(parts[2] || "").trim()
            };
        }

        const stamp = new Date().toLocaleString();

        specialists = specialists.map(function(record) {
            const row = record || {};
            const probe =
                presenceById[String(row.id || "")]
                || {
                    presence: "UNKNOWN",
                    endpoint: ""
                };

            return Object.assign({}, row, {
                presence: probe.presence,
                endpoint: probe.endpoint,
                lastSeen: stamp
            });
        });

        lastRefreshedAt = stamp;
        lastError = "";
        presenceRefreshed();
    }

    FileView {
        id: registryFile

        path: Qt.resolvedUrl("../../hospital-specialists.json")
        blockWrites: true
        atomicWrites: true
        printErrors: false

        onLoaded: root.loadRegistryFromDisk()
    }

    Process {
        id: probeProcess

        stdout: StdioCollector {
            onStreamFinished: {
                root.stdoutText = this.text;
                root.stdoutSeen = true;
                root.maybeFinishProbe();
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                root.stderrText = this.text;
                root.stderrSeen = true;
                root.maybeFinishProbe();
            }
        }

        onExited: function(code, exitStatus) {
            root.exitCode = Number(code);
            root.exitSeen = true;
            root.maybeFinishProbe();
        }
    }

    Timer {
        id: probeWatchdog

        interval: 8000
        repeat: false

        onTriggered: {
            if (!root.probing)
                return;

            root.probing = false;
            root.lastError = "SPECIALIST PRESENCE PROBE TIMEOUT";

            if (probeProcess.running)
                probeProcess.running = false;
        }
    }
}
