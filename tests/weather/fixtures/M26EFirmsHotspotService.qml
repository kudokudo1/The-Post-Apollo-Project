import QtQuick
import Quickshell
// M26-E isolated FIRMS fixture: no API key and no network request.
Scope {
    property bool configured: false
    property bool ready: Quickshell.env("M26E_SOURCE") === "firms"
    property bool failed: false
    property bool loading: false
    property string errorText: ""
    property string lastBounds: ""
    property date lastUpdated: new Date()
    property var hotspots: ready ? [{
        id: "M26E-SHARED",
        title: "SYNTHETIC VIIRS HOTSPOT",
        latitude: 0,
        longitude: 0,
        acquiredUtc: new Date(Date.now() - 60000).toISOString(),
        confidenceLabel: "HIGH"
    }] : []
    function request(bounds) {return false;}
}
