import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: spaceService

    // ─────────────────────────────────────────────
    // PUBLIC STATE
    // ─────────────────────────────────────────────

    property bool kpReady: false
    property bool solarWindReady: false
    property bool magneticFieldReady: false
    property bool solarFluxReady: false

    readonly property bool ready: kpReady && solarWindReady && magneticFieldReady && solarFluxReady

    readonly property bool loading: kpFetch.running || solarWindFetch.running || magneticFieldFetch.running || solarFluxFetch.running

    // ─────────────────────────────────────────────
    // Kp / GEOMAGNETIC
    // ─────────────────────────────────────────────

    property real kp: -1

    readonly property string kpText: kp >= 0 ? kp.toFixed(1) : "--"

    readonly property string kpLabel: {
        if (kp < 0)
            return "UNKNOWN";

        if (kp < 2)
            return "QUIET";

        if (kp < 4)
            return "UNSETTLED";

        if (kp < 5)
            return "ACTIVE";

        if (kp < 6)
            return "G1 STORM";

        if (kp < 7)
            return "G2 STORM";

        if (kp < 8)
            return "G3 STORM";

        if (kp < 9)
            return "G4 STORM";

        return "G5 STORM";
    }

    // ─────────────────────────────────────────────
    // SOLAR WIND
    // ─────────────────────────────────────────────

    property real solarWindSpeed: -1

    readonly property string solarWindText: solarWindSpeed >= 0 ? Math.round(solarWindSpeed) + " KM/S" : "-- KM/S"

    // ─────────────────────────────────────────────
    // INTERPLANETARY MAGNETIC FIELD
    // ─────────────────────────────────────────────

    property real magneticFieldBt: 0
    property real magneticFieldBz: 0

    readonly property string btText: magneticFieldReady ? magneticFieldBt.toFixed(1) + " nT" : "-- nT"

    readonly property string bzText: magneticFieldReady ? magneticFieldBz.toFixed(1) + " nT" : "-- nT"

    readonly property string bzLabel: {
        if (!magneticFieldReady)
            return "UNKNOWN";

        if (magneticFieldBz <= -10)
            return "STRONG SOUTH";

        if (magneticFieldBz <= -5)
            return "SOUTH";

        if (magneticFieldBz < 0)
            return "SLIGHT SOUTH";

        if (magneticFieldBz >= 5)
            return "NORTH";

        return "NEUTRAL";
    }

    // ─────────────────────────────────────────────
    // SOLAR RADIO FLUX
    // ─────────────────────────────────────────────

    property real solarFlux: -1

    readonly property string solarFluxText: solarFlux >= 0 ? Math.round(solarFlux) + " SFU" : "-- SFU"

    // ─────────────────────────────────────────────
    // TIMESTAMPS
    // ─────────────────────────────────────────────

    property string kpTime: ""
    property string solarWindTime: ""
    property string magneticFieldTime: ""
    property string solarFluxTime: ""

    // ─────────────────────────────────────────────
    // ERROR STATE
    // ─────────────────────────────────────────────

    property string errorText: ""

    // ─────────────────────────────────────────────
    // ENDPOINTS
    // ─────────────────────────────────────────────

    readonly property string kpEndpoint: "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"

    readonly property string solarWindEndpoint: "https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json"

    readonly property string magneticFieldEndpoint: "https://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json"

    readonly property string solarFluxEndpoint: "https://services.swpc.noaa.gov/products/summary/10cm-flux.json"

    // ─────────────────────────────────────────────
    // Kp FETCH
    // ─────────────────────────────────────────────

    Process {
        id: kpFetch

        command: ["curl", "-fsSL", "--max-time", "10", spaceService.kpEndpoint]

        stdout: StdioCollector {
            onStreamFinished: {
                spaceService.parseKp(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                spaceService.errorText = "Kp request failed";
            }
        }
    }

    // ─────────────────────────────────────────────
    // SOLAR WIND FETCH
    // ─────────────────────────────────────────────

    Process {
        id: solarWindFetch

        command: ["curl", "-fsSL", "--max-time", "10", spaceService.solarWindEndpoint]

        stdout: StdioCollector {
            onStreamFinished: {
                spaceService.parseSolarWind(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                spaceService.errorText = "solar wind request failed";
            }
        }
    }

    // ─────────────────────────────────────────────
    // MAGNETIC FIELD FETCH
    // ─────────────────────────────────────────────

    Process {
        id: magneticFieldFetch

        command: ["curl", "-fsSL", "--max-time", "10", spaceService.magneticFieldEndpoint]

        stdout: StdioCollector {
            onStreamFinished: {
                spaceService.parseMagneticField(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                spaceService.errorText = "magnetic field request failed";
            }
        }
    }

    // ─────────────────────────────────────────────
    // SOLAR FLUX FETCH
    // ─────────────────────────────────────────────

    Process {
        id: solarFluxFetch

        command: ["curl", "-fsSL", "--max-time", "10", spaceService.solarFluxEndpoint]

        stdout: StdioCollector {
            onStreamFinished: {
                spaceService.parseSolarFlux(text);
            }
        }

        onExited: function (exitCode, exitStatus) {
            if (exitCode !== 0) {
                spaceService.errorText = "solar flux request failed";
            }
        }
    }

    // ─────────────────────────────────────────────
    // Kp PARSER
    // ─────────────────────────────────────────────

    function parseKp(rawText) {
        try {
            const data = JSON.parse(rawText);

            if (!Array.isArray(data) || data.length === 0) {
                throw new Error("No Kp data");
            }

            const latest = data[data.length - 1];

            kp = Number(latest.Kp);

            kpTime = latest.time_tag || "";

            kpReady = true;
        } catch (error) {
            console.log("SpaceService Kp parse error:", error);

            errorText = "Kp parse failed";
        }
    }

    // ─────────────────────────────────────────────
    // SOLAR WIND PARSER
    // ─────────────────────────────────────────────

    function parseSolarWind(rawText) {
        try {
            const data = JSON.parse(rawText);

            if (!Array.isArray(data) || data.length === 0) {
                throw new Error("No solar wind data");
            }

            const latest = data[0];

            solarWindSpeed = Number(latest.proton_speed);

            solarWindTime = latest.time_tag || "";

            solarWindReady = true;
        } catch (error) {
            console.log("SpaceService solar wind parse error:", error);

            errorText = "solar wind parse failed";
        }
    }

    // ─────────────────────────────────────────────
    // MAGNETIC FIELD PARSER
    // ─────────────────────────────────────────────

    function parseMagneticField(rawText) {
        try {
            const data = JSON.parse(rawText);

            if (!Array.isArray(data) || data.length === 0) {
                throw new Error("No magnetic field data");
            }

            const latest = data[0];

            magneticFieldBt = Number(latest.bt);

            magneticFieldBz = Number(latest.bz_gsm);

            magneticFieldTime = latest.time_tag || "";

            magneticFieldReady = true;
        } catch (error) {
            console.log("SpaceService magnetic field parse error:", error);

            errorText = "magnetic field parse failed";
        }
    }

    // ─────────────────────────────────────────────
    // SOLAR FLUX PARSER
    // ─────────────────────────────────────────────

    function parseSolarFlux(rawText) {
        try {
            const data = JSON.parse(rawText);

            if (!Array.isArray(data) || data.length === 0) {
                throw new Error("No solar flux data");
            }

            const latest = data[0];

            solarFlux = Number(latest.flux);

            solarFluxTime = latest.time_tag || "";

            solarFluxReady = true;
        } catch (error) {
            console.log("SpaceService solar flux parse error:", error);

            errorText = "solar flux parse failed";
        }
    }

    // ─────────────────────────────────────────────
    // REFRESH
    // ─────────────────────────────────────────────

    function refresh() {
        if (!kpFetch.running)
            kpFetch.running = true;

        if (!solarWindFetch.running)
            solarWindFetch.running = true;

        if (!magneticFieldFetch.running)
            magneticFieldFetch.running = true;

        if (!solarFluxFetch.running)
            solarFluxFetch.running = true;
    }

    // Refresh every five minutes.
    Timer {
        interval: 300000

        repeat: true
        running: true

        onTriggered: {
            spaceService.refresh();
        }
    }

    // ─────────────────────────────────────────────
    // INITIAL FETCH
    // ─────────────────────────────────────────────

    Component.onCompleted: {
        refresh();
    }
}
