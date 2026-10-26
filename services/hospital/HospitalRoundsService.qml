import QtQuick
import Quickshell

Scope {
    id: roundsService

    readonly property bool subprocessLagProbeEnabled:
        String(Quickshell.env("POST_APOLLO_SUBPROCESS_LAG_PROBE") || "").trim() === "1"

    // Opt-in only; static stage IDs and counts, never subprocess output.
    function traceSubprocessLag(stage, size) {
        if (!subprocessLagProbeEnabled)
            return;
        console.warn("SYNTAGMA_SUBPROCESS_PROBE // service=hospital-rounds"
                     + " stage=" + stage + " size=" + Number(size || 0)
                     + " tsMs=" + Date.now());
    }

    // Inject the existing HospitalFloorService. Rounds never mutates a Floor,
    // Bed, Room, or branch; it only walks discovered Floors and reuses the
    // existing PX audit contract through a private HospitalAuditService.
    property var floorService: null

    property bool running: false
    property bool available: false
    property string lastError: ""
    property string lastRefreshedAt: ""

    property var floors: []
    property var rooms: []

    property int attentionCount: 0
    property int divergedCount: 0
    property int missingCount: 0
    property int aheadCount: 0

    property var scanQueue: []
    property int scanIndex: -1
    property int completedFloors: 0
    property var inFlightFloors: ({})
    readonly property int scanTotal: scanQueue.length
    readonly property int scanCompleted: completedFloors

    readonly property int floorCount: floors.length
    readonly property int roomCount: rooms.length

    signal refreshed()

    // Three independent, bounded read-only PX audits. A slow Floor no
    // longer prevents every other Floor from starting.
    HospitalAuditService { id: auditProbeA }
    HospitalAuditService { id: auditProbeB }
    HospitalAuditService { id: auditProbeC }

    Connections {
        target: auditProbeA
        function onRunningChanged() {
            if (!auditProbeA.running)
                Qt.callLater(function() { roundsService.finishSlot(0); });
        }
    }
    Connections {
        target: auditProbeB
        function onRunningChanged() {
            if (!auditProbeB.running)
                Qt.callLater(function() { roundsService.finishSlot(1); });
        }
    }
    Connections {
        target: auditProbeC
        function onRunningChanged() {
            if (!auditProbeC.running)
                Qt.callLater(function() { roundsService.finishSlot(2); });
        }
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function repositoryFromOrigin(value) {
        let origin = String(value || "").trim();

        if (!origin || origin === "NO ORIGIN")
            return "";

        origin = origin
            .replace(/^git@github\.com:/i, "github.com/")
            .replace(/^ssh:\/\/git@github\.com\//i, "github.com/")
            .replace(/^https?:\/\/github\.com\//i, "github.com/")
            .replace(/^git:\/\/github\.com\//i, "github.com/")
            .replace(/\.git$/i, "")
            .replace(/\/$/, "");

        const marker = "github.com/";
        const lower = origin.toLowerCase();
        const index = lower.indexOf(marker);

        if (index < 0)
            return "";

        const slug = origin.slice(index + marker.length);
        const parts = slug.split("/").filter(function(part) {
            return String(part || "").length > 0;
        });

        if (parts.length < 2)
            return "";

        return String(parts[0]) + "/" + String(parts[1]);
    }

    function attentionRank(stateValue) {
        const state = String(stateValue || "UNKNOWN").toUpperCase();

        if (state === "DIVERGED")
            return 100;
        if (state === "MISSING")
            return 90;
        if (state === "AHEAD")
            return 70;
        if (state === "BEHIND")
            return 60;
        if (state === "IN_MAIN" || state === "AT_MAIN")
            return 0;

        return 40;
    }

    function attentionLabel(stateValue) {
        const state = String(stateValue || "UNKNOWN").toUpperCase();

        if (state === "DIVERGED")
            return "ACTION";
        if (state === "MISSING")
            return "MISSING";
        if (state === "AHEAD")
            return "READY";
        if (state === "BEHIND")
            return "STALE";
        if (state === "IN_MAIN" || state === "AT_MAIN")
            return "CLEAR";

        return "CHECK";
    }

    function resetSnapshot() {
        floors = [];
        rooms = [];
        attentionCount = 0;
        divergedCount = 0;
        missingCount = 0;
        aheadCount = 0;
        available = false;
        lastError = "";
    }

    function refresh() {
        if (running)
            return false;

        if (!floorService) {
            lastError = "ROUNDS // FLOOR SERVICE MISSING";
            return false;
        }

        resetSnapshot();

        const queue = [];

        for (let i = 0; i < Number(floorService.floorCount || 0); ++i) {
            const floor = floorService.floorAt(i);

            if (!floor)
                continue;

            const origin = String(floor.origin || "");
            queue.push({
                floorIndex: i,
                floorId: String(floor.floorId || ""),
                floorLabel: String(floor.label || "REPOSITORY"),
                origin: origin,
                repository: repositoryFromOrigin(origin),
                bedCount: Number(floor.bedCount || 0)
            });
        }

        scanQueue = queue;
        scanIndex = -1;
        completedFloors = 0;
        inFlightFloors = ({});

        if (scanQueue.length === 0) {
            lastError = "ROUNDS // NO FLOORS DISCOVERED";
            return false;
        }

        running = true;
        scanNext();
        return true;
    }

    function auditors() {
        return [auditProbeA, auditProbeB, auditProbeC];
    }

    // Assign each queued Floor once. Slots run concurrently, but per-Floor
    // results are processed independently; failures cannot hide successes.
    function scanNext() {
        if (!running)
            return;

        const probes = auditors();
        let active = Object.assign({}, inFlightFloors);

        for (let slot = 0; slot < probes.length; ++slot) {
            if (active[String(slot)])
                continue;

            while (scanIndex + 1 < scanQueue.length) {
                scanIndex += 1;
                const floor = scanQueue[scanIndex] || {};

                if (!String(floor.repository || "")) {
                    const localFloors = floors.slice();
                    localFloors.push({
                        floorIndex: Number(floor.floorIndex || 0),
                        floorId: String(floor.floorId || ""),
                        floorLabel: String(floor.floorLabel || "REPOSITORY"),
                        origin: String(floor.origin || ""),
                        repository: "",
                        bedCount: Number(floor.bedCount || 0),
                        auditAvailable: false,
                        status: "LOCAL_ONLY",
                        roomCount: 0,
                        attentionCount: 0,
                        error: "NO GITHUB REMOTE"
                    });
                    floors = localFloors;
                    completedFloors += 1;
                    continue;
                }

                active[String(slot)] = floor;
                inFlightFloors = Object.assign({}, active);
                const probe = probes[slot];
                probe.repository = String(floor.repository || "");
                probe.resetResult();
                probe.runAudit(true);
                break;
            }
        }

        if (completedFloors >= scanQueue.length
                && Object.keys(inFlightFloors).length === 0)
            finishRounds();
    }

    function finishSlot(slot) {
        const key = String(slot);
        const floor = inFlightFloors[key];
        if (!running || !floor)
            return;

        const probe = auditors()[slot];
        if (probe.running)
            return;

        const active = Object.assign({}, inFlightFloors);
        delete active[key];
        inFlightFloors = active;

        if (!probe.available) {
            const failedFloors = floors.slice();
            failedFloors.push({
                floorIndex: Number(floor.floorIndex || 0),
                floorId: String(floor.floorId || ""),
                floorLabel: String(floor.floorLabel || "REPOSITORY"),
                origin: String(floor.origin || ""),
                repository: String(floor.repository || ""),
                bedCount: Number(floor.bedCount || 0),
                auditAvailable: false,
                status: "AUDIT_ERROR",
                roomCount: 0,
                attentionCount: 0,
                error: String(probe.lastError || "AUDIT UNAVAILABLE")
            });
            floors = failedFloors;
        } else {
            captureCurrentFloor(floor, probe);
        }

        completedFloors += 1;
        rebuildMetrics();
        Qt.callLater(scanNext);
    }

    function captureCurrentFloor(floor, probe) {
        const source =
            Array.isArray(probe.rooms)
            ? probe.rooms
            : [];

        let floorAttention = 0;
        traceSubprocessLag("rooms-copy:begin", rooms.length);
        const nextRooms = rooms.slice();

        for (let i = 0; i < source.length; ++i) {
            const room = source[i] || {};
            const state = String(room.state || "UNKNOWN").toUpperCase();
            const rank = attentionRank(state);

            if (rank > 0)
                floorAttention += 1;

            nextRooms.push({
                floorIndex: Number(floor.floorIndex || 0),
                floorId: String(floor.floorId || ""),
                floorLabel: String(floor.floorLabel || "REPOSITORY"),
                repository: String(floor.repository || ""),
                team: String(room.team || room.branch || "ROOM"),
                responsibility: String(room.responsibility || ""),
                branch: String(room.branch || ""),
                state: state,
                ahead: Number(room.ahead || 0),
                behind: Number(room.behind || 0),
                head: String(room.head || ""),
                updatedAt: String(room.updated_at || ""),
                attentionRank: rank,
                attentionLabel: attentionLabel(state)
            });
        }

        rooms = nextRooms;

        traceSubprocessLag("floors-copy:begin", floors.length);
        const nextFloors = floors.slice();
        nextFloors.push({
            floorIndex: Number(floor.floorIndex || 0),
            floorId: String(floor.floorId || ""),
            floorLabel: String(floor.floorLabel || "REPOSITORY"),
            origin: String(floor.origin || ""),
            repository: String(floor.repository || ""),
            bedCount: Number(floor.bedCount || 0),
            auditAvailable: true,
            status: String(probe.status || "UNKNOWN"),
            defaultBranch: String(probe.defaultBranch || ""),
            roomCount: source.length,
            attentionCount: floorAttention,
            workflowCount: Number(probe.workflowCount || 0),
            runCount: Number(probe.runCount || 0),
            error: ""
        });
        floors = nextFloors;
    }

    function finishRounds() {
        running = false;

        traceSubprocessLag("rooms-sort-copy:begin", rooms.length);
        const orderedRooms = rooms.slice().sort(function(a, b) {
            const rankDelta =
                Number(b.attentionRank || 0)
                - Number(a.attentionRank || 0);

            if (rankDelta !== 0)
                return rankDelta;

            const floorDelta =
                String(a.floorLabel || "")
                    .localeCompare(String(b.floorLabel || ""));

            if (floorDelta !== 0)
                return floorDelta;

            return String(a.team || "")
                .localeCompare(String(b.team || ""));
        });

        traceSubprocessLag("floors-sort-copy:begin", floors.length);
        const orderedFloors = floors.slice().sort(function(a, b) {
            return String(a.floorLabel || "")
                .localeCompare(String(b.floorLabel || ""));
        });

        rooms = orderedRooms;
        floors = orderedFloors;

        rebuildMetrics();

        available = floors.length > 0;
        lastRefreshedAt = nowIso();

        const failures = floors.filter(function(floor) {
            return !Boolean(floor.auditAvailable)
                && String(floor.status || "") !== "LOCAL_ONLY";
        });

        lastError =
            failures.length > 0
            ? "ROUNDS // "
              + String(failures.length)
              + " FLOOR AUDIT"
              + (failures.length === 1 ? "" : "S")
              + " UNAVAILABLE"
            : "";

        refreshed();
    }

    function rebuildMetrics() {
        traceSubprocessLag("metrics:begin", rooms.length);
        let attention = 0;
        let diverged = 0;
        let missing = 0;
        let ahead = 0;

        for (let i = 0; i < rooms.length; ++i) {
            const room = rooms[i] || {};
            const state = String(room.state || "").toUpperCase();

            if (Number(room.attentionRank || 0) > 0)
                attention += 1;
            if (state === "DIVERGED")
                diverged += 1;
            if (state === "MISSING")
                missing += 1;
            if (state === "AHEAD")
                ahead += 1;
        }

        attentionCount = attention;
        divergedCount = diverged;
        missingCount = missing;
        aheadCount = ahead;
        traceSubprocessLag("metrics:end", rooms.length);
    }
}
