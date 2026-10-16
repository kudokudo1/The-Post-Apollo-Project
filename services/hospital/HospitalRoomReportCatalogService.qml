import QtQuick
import Quickshell
import Quickshell.Io

// Read-only Hospital-wide index of PX's persistent Room Reports. The local
// certification-event history is a separate source and remains untouched.
Scope {
    id: root

    property var reports: []
    property bool loading: false
    property string lastError: ""
    property int totalRooms: 0
    property int scannedRooms: 0
    property int failedRooms: 0
    property int maxRooms: 80
    property int perRoomLimit: 15

    signal refreshed()

    function refresh() {
        if (loading || catalogProcess.running)
            return false;

        loading = true;
        lastError = "";

        const script = [
            'set -uo pipefail',
            'limit_rooms="$1"',
            'limit_reports="$2"',
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"',
            '[ -x "$px" ] || px="$HOME/.local/bin/px"',
            'if [ ! -x "$px" ]; then echo "PX NOT INSTALLED" >&2; exit 20; fi',
            'if ! command -v jq >/dev/null 2>&1; then echo "JQ MISSING" >&2; exit 21; fi',
            'tmpdir="$(mktemp -d)"',
            'trap \'rm -rf "$tmpdir"\' EXIT',
            'if ! "$px" hospital rooms --json > "$tmpdir/rooms.json"; then echo "PX ROOMS UNAVAILABLE" >&2; exit 22; fi',
            'if ! jq -e \'type == "array"\' "$tmpdir/rooms.json" >/dev/null; then echo "PX ROOMS INVALID JSON" >&2; exit 23; fi',
            'total="$(jq -r "length" "$tmpdir/rooms.json")"',
            'scanned=0',
            'failed=0',
            ': > "$tmpdir/reports.ndjson"',
            'while IFS= read -r room; do',
            '  if [ "$scanned" -ge "$limit_rooms" ]; then break; fi',
            '  id="$(printf "%s" "$room" | jq -r ".id // empty")"',
            '  team="$(printf "%s" "$room" | jq -r ".team // empty")"',
            '  if [ -z "$id" ]; then continue; fi',
            '  scanned=$((scanned + 1))',
            '  if ! "$px" hospital room-reports "$id" --limit "$limit_reports" --json > "$tmpdir/current.json" 2>"$tmpdir/error"; then failed=$((failed + 1)); continue; fi',
            '  if ! jq -c --arg roomId "$id" --arg team "$team" \'.[] | {id:(.id // ""),roomId:(.roomId // $roomId),team:$team,kind:(.kind // "DOCTOR_NOTE"),title:(.title // ""),body:((.body // "")[0:6000]),bodyTruncated:((.body // "" | length)>6000),repository:(.repository // ""),branch:(.branch // ""),headSha:(.headSha // ""),doctorId:(.doctorId // ""),createdAt:(.createdAt // "")}\' "$tmpdir/current.json" >> "$tmpdir/reports.ndjson"; then failed=$((failed + 1)); fi',
            'done < <(jq -c ".[]" "$tmpdir/rooms.json")',
            'jq -sc --argjson total "$total" --argjson scanned "$scanned" --argjson failed "$failed" \'{totalRooms:$total,scannedRooms:$scanned,failedRooms:$failed,reports:(sort_by(.createdAt)|reverse|.[0:150])}\' "$tmpdir/reports.ndjson"'
        ].join("\n");

        catalogProcess.exec([
            "bash", "-lc", script,
            "hospital-report-catalog",
            String(Math.max(1, Math.min(200, Number(maxRooms || 80)))),
            String(Math.max(1, Math.min(50, Number(perRoomLimit || 15))))
        ]);
        watchdog.restart();
        return true;
    }

    Process {
        id: catalogProcess
        stdout: StdioCollector {
            onStreamFinished: {
                const raw = String(this.text || "").trim();
                if (!raw)
                    return;
                try {
                    const data = JSON.parse(raw);
                    if (!Array.isArray(data.reports))
                        throw new Error("ROOM REPORT CATALOG EXPECTED ARRAY");
                    root.reports = data.reports;
                    root.totalRooms = Number(data.totalRooms || 0);
                    root.scannedRooms = Number(data.scannedRooms || 0);
                    root.failedRooms = Number(data.failedRooms || 0);
                    root.lastError = root.failedRooms > 0
                        ? "ROOM REPORTS // " + root.failedRooms + " ROOM READS FAILED"
                        : "";
                } catch (error) {
                    root.lastError = "ROOM REPORTS // INVALID CATALOG DATA: " + String(error);
                }
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                const raw = String(this.text || "").trim();
                if (raw && !root.lastError)
                    root.lastError = "ROOM REPORTS // " + raw.slice(0, 240);
            }
        }
        onExited: function(code, status) {
            root.loading = false;
            watchdog.stop();
            if (Number(code) !== 0 && !root.lastError)
                root.lastError = "ROOM REPORTS // PX EXIT " + String(code);
            root.refreshed();
        }
    }

    Timer {
        id: watchdog
        interval: 90000
        repeat: false
        onTriggered: {
            if (!root.loading)
                return;
            root.lastError = "ROOM REPORTS // READ TIMEOUT";
            root.loading = false;
            if (catalogProcess.running)
                catalogProcess.running = false;
            root.refreshed();
        }
    }
}
