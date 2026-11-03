import QtQuick
import Quickshell
// M26-E replaces EONET/GDELT/Radio discovery ONLY in temp CI config.
Scope {
    property string domain: "map"
    property string mapCategory: ""
    property bool active: false
    property bool ready: domain === "map"
        && Quickshell.env("M26E_SOURCE") === "eonet"
    property bool usingCache: false
    property bool failed: false
    property bool loading: false
    property string errorText: ""
    property date lastUpdated: new Date()
    property double sourceClockMs: Date.now()
    property int retryWaitSeconds: 0
    property bool canRetry: false
    property var rows: ready ? [{
        id: "M26E-SHARED",
        title: "SYNTHETIC NASA EONET TEST",
        category: "Wildfires",
        categoryId: "wildfires",
        latitude: 0,
        longitude: 0,
        rawTime: new Date(Date.now() - 60000).toISOString(),
        time: new Date(Date.now() - 60000).toISOString()
    }] : []
    function refresh(manual) {return false;}
}
