import QtQuick
import Quickshell
import Quickshell.Io

// Team 8 — APPS Core Bottles discovery provider.
//
// Standalone and host-neutral. It owns only discovery/state for Bottles launch
// targets. It does not launch applications, touch AppControl navigation, infer
// semantic identity, or know anything about tabs/audio/process control.
Scope {
    id: bottleProvider

    property var names: []
    property string selectedName: ""
    property bool loading: false
    property string errorText: ""

    function collectNames(value, output) {
        if (value === null || value === undefined)
            return;

        if (typeof value === "string") {
            const name = value.trim();

            if (name && output.indexOf(name) === -1)
                output.push(name);

            return;
        }

        if (Array.isArray(value)) {
            for (let i = 0; i < value.length; i++) {
                const item = value[i];

                if (typeof item === "string") {
                    collectNames(item, output);
                    continue;
                }

                if (item && typeof item === "object") {
                    if (item.name)
                        collectNames(item.name, output);
                    else if (item.Name)
                        collectNames(item.Name, output);
                    else if (item.bottle)
                        collectNames(item.bottle, output);
                }
            }

            return;
        }

        if (typeof value === "object") {
            if (value.name)
                collectNames(value.name, output);

            if (value.Name)
                collectNames(value.Name, output);

            if (value.bottles)
                collectNames(value.bottles, output);

            const keys = Object.keys(value);

            for (let i = 0; i < keys.length; i++) {
                const key = keys[i];

                // Some Bottles versions return an object keyed by bottle name.
                if (key !== "bottles"
                        && key !== "name"
                        && key !== "Name"
                        && value[key]
                        && typeof value[key] === "object") {
                    collectNames(key, output);
                }
            }
        }
    }

    function namesFromPayload(payload) {
        const output = [];
        collectNames(payload, output);
        return output;
    }

    function namesFromText(rawText) {
        const output = [];
        const lines = String(rawText || "")
            .split(/\r?\n/)
            .map(function(line) { return line.trim(); })
            .filter(function(line) { return line.length > 0; });

        for (let i = 0; i < lines.length; i++) {
            const clean = lines[i]
                .replace(/^[-*]\s*/, "")
                .trim();

            if (clean && clean.toLowerCase() !== "bottles")
                output.push(clean);
        }

        return output;
    }

    function parseNames(rawText) {
        try {
            return namesFromPayload(
                JSON.parse(String(rawText || "[]"))
            );
        } catch (error) {
            // Preserve donor fallback for older/non-JSON bottles-cli output.
            return namesFromText(rawText);
        }
    }

    function refresh() {
        if (loading)
            return;

        loading = true;
        errorText = "";

        bottlesListProcess.exec([
            "sh",
            "-lc",
            "if command -v flatpak >/dev/null 2>&1 "
            + "&& flatpak info com.usebottles.bottles >/dev/null 2>&1; then "
            + "flatpak run --command=bottles-cli com.usebottles.bottles "
            + "--json list bottles; "
            + "elif command -v bottles-cli >/dev/null 2>&1; then "
            + "bottles-cli --json list bottles; "
            + "else exit 127; fi"
        ]);
    }

    Process {
        id: bottlesListProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const discovered =
                    bottleProvider.parseNames(text || "");

                bottleProvider.names = discovered;
                bottleProvider.selectedName =
                    discovered.length > 0 ? discovered[0] : "";
                bottleProvider.loading = false;

            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const message = String(text || "").trim();

                if (message) {
                    bottleProvider.errorText = message;
                }

                bottleProvider.loading = false;
            }
        }
    }
}
