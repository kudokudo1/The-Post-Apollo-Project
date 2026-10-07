import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property var providers: []
    property bool loaded: false
    property bool refreshing: false
    property string lastError: ""
    property string lastRefreshedAt: ""

    signal providersRefreshed()

    readonly property int providerCount: providers.length
    readonly property int readyCount:
        providers.filter(function(row) {
            return !!(row || {}).available;
        }).length

    function pxArgs(args) {
        const suffix = Array.isArray(args) ? args : [];
        return [
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-provider-service"
        ].concat(suffix);
    }

    function compactPxError(value, context) {
        const detail = String(value || "").trim();

        if (!detail)
            return "";

        const lower = detail.toLowerCase();

        if (lower.indexOf("unknown command hospital") >= 0
                || lower.indexOf("unknown command agent") >= 0
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

        const prefix = String(context || "").trim();
        return prefix ? prefix + " // " + message : message;
    }

    function normalizeProvider(record) {
        const row = record || {};

        return {
            id: String(row.id || "").trim(),
            name: String(row.name || row.id || "PROVIDER").trim(),
            command: String(row.command || "").trim(),
            endpoint: String(row.endpoint || "").trim(),
            dialect: String(row.dialect || "").trim(),
            available: !!row.available,
            error: String(row.error || "").trim()
        };
    }

    function providerById(value) {
        const id = String(value || "").trim();

        for (let i = 0; i < providers.length; ++i) {
            const row = providers[i] || {};
            if (String(row.id || "") === id)
                return row;
        }

        return null;
    }

    function refresh() {
        if (refreshing || providerProcess.running)
            return false;

        refreshing = true;
        lastError = "";

        providerProcess.exec(pxArgs([
            "agent",
            "providers",
            "--json"
        ]));
        return true;
    }

    Process {
        id: providerProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();

                try {
                    const result = JSON.parse(body || "[]");

                    if (!Array.isArray(result))
                        throw new Error("PX agent providers returned non-array data");

                    root.providers = result.map(function(row) {
                        return root.normalizeProvider(row);
                    }).filter(function(row) {
                        return !!row.id;
                    });
                    root.lastError = "";
                } catch (error) {
                    root.providers = [];
                    root.lastError = root.compactPxError(
                        body || error,
                        "HOSPITAL PROVIDERS"
                    );
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail)
                    root.lastError = root.compactPxError(
                        detail,
                        "HOSPITAL PROVIDERS"
                    );
            }
        }

        onExited: function(code, exitStatus) {
            root.refreshing = false;
            root.loaded = true;
            root.lastRefreshedAt = new Date().toLocaleString();

            if (Number(code) !== 0 && !root.lastError)
                root.lastError =
                    "PX AGENT PROVIDERS EXIT " + String(code);

            root.providersRefreshed();
        }
    }

    Component.onCompleted: refresh()
}
