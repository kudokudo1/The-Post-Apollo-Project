import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string roomId: ""
    property var checkpoints: []
    property bool loading: false
    property string lastError: ""

    readonly property var latestCheckpoint:
        checkpoints.length > 0
        ? checkpoints[checkpoints.length - 1]
        : null

    readonly property int checkpointCount:
        checkpoints.length

    signal checkpointsRefreshed()

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];

        return [
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-room-checkpoints"
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

        if (message.length > 240)
            message = message.slice(0, 237) + "...";

        return "HOSPITAL CHECKPOINTS // " + message;
    }

    function clear() {
        checkpoints = [];
        loading = false;
        lastError = "";
    }

    function refresh() {
        const id = String(roomId || "").trim();

        if (!id) {
            clear();
            return false;
        }

        if (loading || listProcess.running)
            return false;

        loading = true;
        lastError = "";

        listProcess.exec(pxArgs([
            "hospital",
            "checkpoints",
            id,
            "--limit",
            "20",
            "--json"
        ]));
        return true;
    }

    onRoomIdChanged: {
        clear();

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
                        throw new Error(
                            "PX Hospital checkpoints returned non-array data"
                        );

                    root.checkpoints = result;
                    root.lastError = "";
                } catch (error) {
                    root.checkpoints = [];
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
            root.loading = false;

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX HOSPITAL CHECKPOINTS EXIT " + String(code);

            root.checkpointsRefreshed();
        }
    }

    Component.onCompleted: {
        if (roomId)
            refresh();
    }
}
