pragma Singleton

import QtQuick
import Quickshell
import "../system"

// Authoritative runtime acquisition store. No widget dependency, persistence,
// process mutation, or additional timer. K1 preserves the existing acquisition
// implementation and lets the temporary donor adapter drive its cadence.
Scope {
    id: root

    readonly property var telemetry: sampler
    readonly property var rows: sampler.rows

    function publishSnapshot(rows) {
        sampler.rows = Array.isArray(rows) ? rows : [];
    }

    ProcessTelemetry {
        id: sampler
    }
}
