.pragma library

// ApolloHub local-link projection. Inputs are plain scalar observations from
// Quickshell.Networking; do not infer Internet reachability from a local link.
// Missing, malformed and unsupported readings stay unknown, never 0%.

function safeName(value) {
    return typeof value === "string" ? value.slice(0, 100) : "";
}

function signalPercent(value) {
    // The Quickshell API reports a real number from 0.0 to 1.0.
    // Coercing strings/arrays would falsely turn invalid readings into 0%.
    if (typeof value !== "number")
        return -1;
    var strength = value;
    return isFinite(strength) && strength >= 0 && strength <= 1
           ? Math.round(strength * 100) : -1;
}

// The dock's iw rx bitrate is a link estimate, not Internet throughput.
// Keep its units numeric and unknown on absent/invalid readings.
function linkSpeedMbps(value) {
    return typeof value === "number" && isFinite(value)
           && value > 0 && value <= 100000
           ? Math.round(value) : -1;
}

function snapshot(reading) {
    var data = reading && typeof reading === "object" ? reading : {};
    var wifiPresent = data.wifiPresent === true;
    var ethernetPresent = data.ethernetPresent === true;
    var wifiConnected = wifiPresent && data.wifiConnected === true;
    var ethernetConnected = ethernetPresent && data.ethernetConnected === true;

    // Wired takes precedence if both links are connected, but both still
    // remain visible. A device connection is not an Internet health test.
    var transport = ethernetConnected ? "ethernet"
                  : wifiConnected ? "wifi" : "none";
    var known = data.devicesKnown === true;
    var state = !known || (!wifiPresent && !ethernetPresent) ? "unavailable"
              : transport === "none" ? "disconnected" : "connected";

    return {
        state: state,
        connected: transport !== "none",
        transport: transport,
        // No HTTP probe and no inferred gateway/DNS/global connectivity.
        internetState: "unverified",
        wifi: {
            present: wifiPresent,
            connected: wifiConnected,
            interfaceName: wifiPresent ? safeName(data.wifiInterface) : "",
            networkName: wifiConnected ? safeName(data.wifiName) : "",
            signalPercent: wifiConnected ? signalPercent(data.wifiSignal) : -1
        },
        ethernet: {
            present: ethernetPresent,
            connected: ethernetConnected,
            interfaceName: ethernetPresent ? safeName(data.ethernetInterface) : ""
        },
        // Reuse the live dock's rx bitrate ONLY for the active Wi-Fi link.
        // Ethernet stays unknown until a validated wired source is shared.
        linkSpeedMbps: transport === "wifi"
                       ? linkSpeedMbps(data.wifiLinkSpeedMbps) : -1,
        linkSpeedApproximate: transport === "wifi"
    };
}
