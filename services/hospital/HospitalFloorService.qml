import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: floorService

    property string preferredFloorQuery: "taskbars-post-apollo"
    property bool discovering: false
    property string lastError: ""

    property int selectedFloorIndex: -1
    property int selectedBedIndex: -1

    property string floorId: ""
    property string floorLabel: "NO FLOOR"
    property string floorOrigin: ""

    property string bedLabel: "NO BED"
    property string bedPath: ""
    property string bedBranch: ""
    property string bedHead: ""
    property string bedWorktree: ""
    property bool bedIsLive: false

    property var pendingBeds: []
    property var allBeds: []
    property var rememberedBedByFloor: ({})

    property alias floorModel: floorRows
    property alias bedModel: bedRows

    readonly property int floorCount: floorRows.count
    readonly property int bedCount: bedRows.count

    signal floorsChanged()
    signal floorChanged()
    signal bedChanged()

    ListModel { id: floorRows }
    ListModel { id: bedRows }

    function normalizeOrigin(value) {
        let origin = String(value || "").trim();

        if (!origin || origin === "NO ORIGIN")
            return "";

        origin = origin
            .replace(/^git@([^:]+):/, "$1/")
            .replace(/^[a-zA-Z]+:\/\//, "")
            .replace(/\.git$/, "")
            .replace(/\/$/, "");

        return origin.toLowerCase();
    }

    function floorIdentity(bed) {
        const remote = normalizeOrigin(bed.origin);

        if (remote)
            return "remote:" + remote;

        return "local:" + String(bed.commonDir || bed.path || "");
    }

    function labelFromOrigin(origin, fallback) {
        const normalized = normalizeOrigin(origin);

        if (!normalized)
            return String(fallback || "LOCAL REPOSITORY");

        const pieces = normalized.split("/");
        return pieces.length > 0
            ? String(pieces[pieces.length - 1] || fallback || "REPOSITORY")
            : String(fallback || "REPOSITORY");
    }

    function floorAt(index) {
        if (index < 0 || index >= floorRows.count)
            return null;
        return floorRows.get(index);
    }

    function bedAt(index) {
        if (index < 0 || index >= bedRows.count)
            return null;
        return bedRows.get(index);
    }

    function floorIndexOfId(value) {
        const needle = String(value || "");

        for (let i = 0; i < floorRows.count; ++i) {
            if (String(floorRows.get(i).floorId || "") === needle)
                return i;
        }

        return -1;
    }

    function bedIndexOfPath(value) {
        const needle = String(value || "");

        for (let i = 0; i < bedRows.count; ++i) {
            if (String(bedRows.get(i).path || "") === needle)
                return i;
        }

        return -1;
    }

    function discover() {
        if (discovering)
            return;

        discovering = true;
        lastError = "";
        pendingBeds = [];
        scanWatchdog.restart();

        scanProcess.exec([
            "bash",
            "-lc",
            [
                'live="$HOME/.config/quickshell"',
                'declare -A seen',
                'for candidate in "$live" "$HOME"/Projects/*; do',
                '  [ -e "$candidate/.git" ] || continue',
                '  git -C "$candidate" rev-parse --is-inside-work-tree >/dev/null 2>&1 || continue',
                '  root="$(git -C "$candidate" rev-parse --show-toplevel 2>/dev/null || true)"',
                '  [ -n "$root" ] || continue',
                '  [ -z "${seen[$root]}" ] || continue',
                '  seen[$root]=1',
                '  origin="$(git -C "$root" remote get-url origin 2>/dev/null || true)"',
                '  [ -n "$origin" ] || origin="NO ORIGIN"',
                '  common="$(git -C "$root" rev-parse --git-common-dir 2>/dev/null || true)"',
                '  if [ -n "$common" ]; then',
                '    case "$common" in',
                '      /*) ;;',
                '      *) common="$(cd "$root" && cd "$common" 2>/dev/null && pwd -P || printf "%s" "$common")" ;;',
                '    esac',
                '  fi',
                '  branch="$(git -C "$root" branch --show-current 2>/dev/null || true)"',
                '  [ -n "$branch" ] || branch="DETACHED"',
                '  head="$(git -C "$root" rev-parse --short=10 HEAD 2>/dev/null || true)"',
                '  count="$(git -C "$root" status --porcelain=v1 2>/dev/null | wc -l | tr -d " ")"',
                '  if [ "$count" -eq 0 ]; then worktree="CLEAN"; else worktree="DIRTY • $count CHANGES"; fi',
                '  if [ "$root" = "$live" ]; then',
                '    label="LIVE QUICKSHELL"',
                '    is_live=1',
                '  else',
                '    label="$(basename "$root")"',
                '    is_live=0',
                '  fi',
                '  printf "BED\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n" "$label" "$root" "$origin" "$common" "$branch" "$head" "$worktree" "$is_live"',
                'done',
                'printf "DONE\\t\\n"'
            ].join("\n")
        ]);
    }

    function consumeScanLine(line) {
        const raw = String(line || "");
        const parts = raw.split("\t");
        const key = parts.length > 0 ? parts[0] : "";

        if (key === "BED") {
            pendingBeds.push({
                label: parts.length > 1 ? parts[1] : "LOCAL CHECKOUT",
                path: parts.length > 2 ? parts[2] : "",
                origin: parts.length > 3 ? parts[3] : "NO ORIGIN",
                commonDir: parts.length > 4 ? parts[4] : "",
                branch: parts.length > 5 ? parts[5] : "DETACHED",
                head: parts.length > 6 ? parts[6] : "",
                worktree: parts.length > 7 ? parts[7] : "",
                isLive: (parts.length > 8 ? parts[8] : "0") === "1"
            });
            return;
        }

        if (key === "DONE") {
            scanWatchdog.stop();
            discovering = false;
            rebuild();
        }
    }

    function rebuild() {
        const previousFloorId = floorId;
        const previousBedPath = bedPath;
        const unique = {};

        floorRows.clear();
        allBeds = pendingBeds.slice();

        for (let i = 0; i < allBeds.length; ++i) {
            const bed = allBeds[i];
            const identity = floorIdentity(bed);

            bed.floorId = identity;

            if (!unique[identity]) {
                unique[identity] = {
                    floorId: identity,
                    label: labelFromOrigin(bed.origin, bed.label),
                    origin: String(bed.origin || "NO ORIGIN"),
                    bedCount: 1
                };
            } else {
                unique[identity].bedCount += 1;
            }
        }

        const keys = Object.keys(unique).sort(function(a, b) {
            return String(unique[a].label).localeCompare(String(unique[b].label));
        });

        for (let i = 0; i < keys.length; ++i)
            floorRows.append(unique[keys[i]]);

        let index = floorIndexOfId(previousFloorId);

        if (index < 0 && preferredFloorQuery) {
            const needle = String(preferredFloorQuery).toLowerCase();

            for (let i = 0; i < floorRows.count; ++i) {
                const row = floorRows.get(i);

                if (String(row.label || "").toLowerCase().indexOf(needle) >= 0
                        || String(row.origin || "").toLowerCase().indexOf(needle) >= 0) {
                    index = i;
                    break;
                }
            }
        }

        if (index < 0 && floorRows.count > 0)
            index = 0;

        if (index >= 0)
            applyFloor(index, previousBedPath);
        else
            clearSelection();

        floorsChanged();
    }

    function clearSelection() {
        selectedFloorIndex = -1;
        selectedBedIndex = -1;
        floorId = "";
        floorLabel = "NO FLOOR";
        floorOrigin = "";
        bedRows.clear();
        bedLabel = "NO BED";
        bedPath = "";
        bedBranch = "";
        bedHead = "";
        bedWorktree = "";
        bedIsLive = false;
    }

    function applyFloor(index, preferredBedPath) {
        const floor = floorAt(index);

        if (!floor)
            return false;

        if (floorId && bedPath) {
            const remembered = rememberedBedByFloor;
            remembered[floorId] = bedPath;
            rememberedBedByFloor = remembered;
        }

        selectedFloorIndex = index;
        floorId = String(floor.floorId || "");
        floorLabel = String(floor.label || "REPOSITORY");
        floorOrigin = String(floor.origin || "");

        bedRows.clear();

        for (let i = 0; i < allBeds.length; ++i) {
            const bed = allBeds[i];

            if (String(bed.floorId || "") !== floorId)
                continue;

            bedRows.append({
                label: String(bed.label || "LOCAL CHECKOUT"),
                path: String(bed.path || ""),
                branch: String(bed.branch || "DETACHED"),
                head: String(bed.head || ""),
                worktree: String(bed.worktree || ""),
                isLive: Boolean(bed.isLive)
            });
        }

        let bedIndex = bedIndexOfPath(preferredBedPath);

        if (bedIndex < 0)
            bedIndex = bedIndexOfPath(rememberedBedByFloor[floorId]);

        if (bedIndex < 0) {
            for (let i = 0; i < bedRows.count; ++i) {
                if (Boolean(bedRows.get(i).isLive)) {
                    bedIndex = i;
                    break;
                }
            }
        }

        if (bedIndex < 0 && bedRows.count > 0)
            bedIndex = 0;

        if (bedIndex >= 0)
            applyBed(bedIndex);
        else {
            selectedBedIndex = -1;
            bedLabel = "NO LOCAL BED";
            bedPath = "";
            bedBranch = "";
            bedHead = "";
            bedWorktree = "";
            bedIsLive = false;
            bedChanged();
        }

        floorChanged();
        return true;
    }

    function selectFloor(index) {
        const requested = Number(index);

        if (requested < 0
                || requested >= floorRows.count
                || requested === selectedFloorIndex)
            return false;

        return applyFloor(requested, "");
    }

    function cycleFloor(delta) {
        if (floorRows.count <= 0)
            return;

        let index = selectedFloorIndex;

        if (index < 0)
            index = 0;
        else
            index = (index + Number(delta || 0) + floorRows.count) % floorRows.count;

        selectFloor(index);
    }

    function applyBed(index) {
        const bed = bedAt(index);

        if (!bed)
            return false;

        selectedBedIndex = index;
        bedLabel = String(bed.label || "LOCAL CHECKOUT");
        bedPath = String(bed.path || "");
        bedBranch = String(bed.branch || "DETACHED");
        bedHead = String(bed.head || "");
        bedWorktree = String(bed.worktree || "");
        bedIsLive = Boolean(bed.isLive);

        const remembered = rememberedBedByFloor;
        remembered[floorId] = bedPath;
        rememberedBedByFloor = remembered;

        bedChanged();
        return true;
    }

    function selectBed(index) {
        const requested = Number(index);

        if (requested < 0
                || requested >= bedRows.count
                || requested === selectedBedIndex)
            return false;

        return applyBed(requested);
    }

    function cycleBed(delta) {
        if (bedRows.count <= 0)
            return;

        let index = selectedBedIndex;

        if (index < 0)
            index = 0;
        else
            index = (index + Number(delta || 0) + bedRows.count) % bedRows.count;

        selectBed(index);
    }

    Process {
        id: scanProcess

        stdout: SplitParser {
            onRead: function(line) {
                floorService.consumeScanLine(line);
            }
        }

        stderr: SplitParser {
            onRead: function(line) {
                const message = String(line || "").trim();

                if (message)
                    floorService.lastError = message;
            }
        }
    }

    Timer {
        id: scanWatchdog
        interval: 8000
        repeat: false

        onTriggered: {
            floorService.discovering = false;
            floorService.lastError = "FLOOR / BED DISCOVERY TIMEOUT";
        }
    }

    Component.onCompleted: discover()
}
