.pragma library

// Source-backed help map, intentionally separate from the Prism placement
// registry. These are mounted shell entry points, not live service statuses.
// Order within each group follows shell.qml; the map is not pixel-scaled.
var zones = [
    { id: "top-left", label: "TOP LEFT", entries: [
        { name: "APP CONTROL", mount: "AppControlW" },
        { name: "WORKSPACES", mount: "Workspaces" },
        { name: "MEDIA", mount: "Mediaplayer" },
        { name: "CAMERA", mount: "CameraW" },
        { name: "HOSPITAL", mount: "HospitalW" },
        { name: "FINANCE", mount: "FinanceW" },
        { name: "GIT", mount: "GitW" },
        { name: "COMPANY NETWORK", mount: "CompanyNetworkW" },
        { name: "TO-DO", mount: "TasksW" },
        { name: "FOREST", mount: "ForestW" }
    ] },
    { id: "top-center", label: "TOP CENTER", entries: [
        { name: "APOLLO HUB", mount: "ApolloHubW" }
    ] },
    { id: "top-right", label: "TOP RIGHT", entries: [
        { name: "NETWORK", mount: "Network" },
        { name: "BLUETOOTH", mount: "Bluetooth" },
        { name: "CPU++", mount: "CpuPlusW" },
        { name: "WEATHER", mount: "WeatherStationW" },
        { name: "VOLUME", mount: "Volumebar" },
        { name: "MESSAGING", mount: "MessagingW" },
        { name: "CLOCK / TIME", mount: "TimeW" },
        { name: "NOTIFICATIONS", mount: "NotificationsHubW" }
    ] },
    { id: "bottom-left", label: "BOTTOM LEFT", entries: [
        { name: "TRASH", mount: "Trash" },
        { name: "PRISM", mount: "PrismDock" }
    ] },
    { id: "bottom-center", label: "BOTTOM CENTER", entries: [
        { name: "SYSTEM TRAY", mount: "Tray" }
    ] },
    { id: "bottom-right", label: "BOTTOM RIGHT", entries: [
        { name: "POWER", mount: "Power" }
    ] }
];

function mapZones() {
    return zones.map(function(zone) {
        return { id: zone.id, label: zone.label,
                 entries: zone.entries.map(function(entry) {
                     return { name: entry.name, mount: entry.mount };
                 }) };
    });
}
