import QtQuick
import "../../components"

QtObject {
    id: systemPresentation

    // Pure SYSTEM presentation policy. This object has no host navigation,
    // no telemetry lifetime, and no destructive mutation state.
    function systemAccent(entry) {
        const category =
            String(entry && entry.category || "").toUpperCase();

        if (category === "CPU")
            return Colors.orange;
        if (category === "MEMORY")
            return Colors.magenta;
        if (category === "GPU")
            return Colors.omnitrix;
        if (category === "STORAGE")
            return Colors.blue;
        if (category === "NETWORK")
            return Colors.cyan;
        if (category === "SWAP")
            return Colors.yellow;

        return Colors.white;
    }

    function systemIconAccent(entry) {
        const category =
            String(entry && entry.category || "").toUpperCase();

        if (category === "NETWORK")
            return Colors.cyan;
        if (category === "STORAGE")
            return Colors.blue;

        return systemAccent(entry);
    }

    function systemRateMetricParts(entry) {
        const metric = String(entry && entry.metric || "");
        const pieces = metric.split("•");
        const result = [];

        for (let i = 0; i < pieces.length; i++) {
            const raw = String(pieces[i] || "").trim();
            const match = raw.match(/^([↓↑RW])\s*([0-9.]+)\s*(\S+\/s)$/);

            if (match) {
                result.push({
                    value: String(match[1]) + " " + String(match[2]),
                    unit: String(match[3])
                });
            } else if (raw.length > 0) {
                result.push({
                    value: raw,
                    unit: ""
                });
            }
        }

        return result;
    }

    function systemIconFor(entry) {
        const category =
            String(entry && entry.category || "").toUpperCase();
        const name = String(
            entry && (entry.name || entry.label) || ""
        ).toUpperCase();

        // DRM connector rows are named CARDN-<connector>-N. Keep the bare
        // CARDN device on the GPU glyph, but show connector rows as displays.
        const connectorNamed = /^CARD[0-9]+-/.test(name);

        if (category === "CPU")
            return "";
        if (category === "MEMORY")
            return "";
        if (category === "GPU")
            return (entry && entry.displayRelated) || connectorNamed
                   ? "󰍹" : "󰢮";
        if (category === "STORAGE")
            return "";
        if (category === "NETWORK")
            return "🛰";
        if (category === "SWAP")
            return "⇄";

        return "🖳";
    }

    function systemComponentWarning(entry) {
        if (!entry)
            return "";

        if (entry.controlKind === "network" && entry.canReboot)
            return "⚠︎ DISCONNECT MAY DROP NETWORK • REBOOT RESTARTS PC";

        if (entry.controlKind === "network")
            return "⚠︎ DISCONNECT MAY DROP NETWORK";

        if (entry.canReboot)
            return "⚠︎ REBOOT RESTARTS THIS PC";

        return "";
    }

    function contributorRows(entry) {
        if (!entry || !Array.isArray(entry.contributors))
            return [];

        return entry.contributors;
    }
}
