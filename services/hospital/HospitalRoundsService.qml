import QtQuick
import Quickshell

Scope {
    id: roundsService

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
    property bool scanInFlight: false
    property var currentFloor: ({})

    readonly property int floorCount: floors.length
    readonly property int roomCount: rooms.length

    signal refreshed()

    HospitalAuditService {
        id: auditProbe
    }

    Connections {
        target: auditProbe

        function onRunningChanged() {
            if (auditProbe.running || !roundsService.scanInFlight)
                return;

            // HospitalAuditService publishes its parsed snapshot immediately
            // after dropping running=false. Defer one turn so available/rooms
            // reflect the completed audit rather than the pre-parse state.
            Qt.callLater(roundsService.finishCurrentFloor);
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

        if (scanQueue.length === 0) {
            lastError = "ROUNDS // NO FLOORS DISCOVERED";
            return false;
        }

        running = true;
        scanNext();
        return true;
    }

    function scanNext() {
        scanIndex += 1;

        if (scanIndex >= scanQueue.length) {
            finishRounds();
            return;
        }

        const floor = scanQueue[scanIndex] || {};
        currentFloor = floor;

        if (!String(floor.repository || "")) {
            const nextFloors = floors.slice();
            nextFloors.push({
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
            floors = nextFloors;
            Qt.callLater(scanNext);
            return;
        }

        auditProbe.repository = String(floor.repository || "");
        auditProbe.resetResult();

        scanInFlight = true;
        auditProbe.runAudit(true);
    }

    function finishCurrentFloor() {
        if (!scanInFlight)
            return;

        scanInFlight = false;

        const floor = currentFloor || {};

        if (!auditProbe.available) {
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
                error: String(auditProbe.lastError || "AUDIT UNAVAILABLE")
            });
            floors = failedFloors;
            Qt.callLater(scanNext);
            return;
        }

        captureCurrentFloor(floor);
        Qt.callLater(scanNext);
    }

    function captureCurrentFloor(floor) {
        const source =
            Array.isArray(auditProbe.rooms)
            ? auditProbe.rooms
            : [];

        let floorAttention = 0;
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

        const nextFloors = floors.slice();
        nextFloors.push({
            floorIndex: Number(floor.floorIndex || 0),
            floorId: String(floor.floorId || ""),
            floorLabel: String(floor.floorLabel || "REPOSITORY"),
            origin: String(floor.origin || ""),
            repository: String(floor.repository || ""),
            bedCount: Number(floor.bedCount || 0),
            auditAvailable: true,
            status: String(auditProbe.status || "UNKNOWN"),
            defaultBranch: String(auditProbe.defaultBranch || ""),
            roomCount: source.length,
            attentionCount: floorAttention,
            workflowCount: Number(auditProbe.workflowCount || 0),
            runCount: Number(auditProbe.runCount || 0),
            error: ""
        });
        floors = nextFloors;
    }

    function finishRounds() {
        scanInFlight = false;
        running = false;

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
    }
}
