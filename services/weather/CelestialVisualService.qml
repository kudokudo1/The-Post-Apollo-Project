import QtQuick
import Quickshell
import Quickshell.Io

// MAGICK M5b // SINGLE on-demand read-only calculation owner, hosted by the
// persistent StationSubjectNavigator. Never polls, downloads, or writes files.
// Explicit opt-in runtime configuration:
//   POST_APOLLO_CELESTIAL_KERNEL=/absolute/path/de440s.bsp
//   POST_APOLLO_CELESTIAL_PYTHON=/path/to/venv/bin/python  (optional)
Scope {
    id: celestial

    property bool active: false
    property string route: ""
    property real anchorNowMs: 0
    property string kernelPath:
        String(Quickshell.env("POST_APOLLO_CELESTIAL_KERNEL") || "")
    property string pythonExecutable:
        String(Quickshell.env("POST_APOLLO_CELESTIAL_PYTHON") || "python3")

    property var visualData: null
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property string loadedKey: ""
    property string inflightKey: ""
    property date lastCalculated

    readonly property bool loading: calculation.running
    readonly property bool configured:
        kernelPath.trim() !== "" && pythonExecutable.trim() !== ""
    readonly property string anchorDayUtc:
        isFinite(anchorNowMs) && anchorNowMs > 0
        ? new Date(anchorNowMs).toISOString().slice(0, 10) : ""
    readonly property string currentKey:
        active && configured && anchorDayUtc !== ""
        ? kernelPath + "|" + pythonExecutable + "|" + anchorDayUtc
          + "|" + (route === "magick/astrology/retrogrades"
                   ? "mercury-sun" : "moon-sun")
        : ""
    readonly property string statusText:
        !configured ? "SET POST_APOLLO_CELESTIAL_KERNEL (AND SKYFIELD)"
        : anchorDayUtc === "" ? "UTC CLOCK UNAVAILABLE"
        : loading ? "JPL CALCULATION RUNNING"
        : failed ? errorText
        : ready ? "SOURCE-VERIFIED JPL DATA LOADED"
        : "READY // SELECT LOAD CALCULATION"

    function bodiesForRoute() {
        return route === "magick/astrology/retrogrades"
               ? ["mercury", "sun"] : ["moon", "sun"];
    }

    function request() {
        // A dated UTC calendar window; not the machine's local civil time.
        const midnight=Date.parse(anchorDayUtc + "T00:00:00.000Z");
        if (!isFinite(midnight))return null;
        const day=86400000;
        return {
            format:"post-apollo.weather.celestial-visual-data.v1",
            start_utc:new Date(midnight-14*day).toISOString(),
            end_utc:new Date(midnight+15*day).toISOString(),
            bodies:bodiesForRoute(),
            step_hours:12,
            rate_window_hours:6,
            orb_degrees:6,
            include_events:true
        };
    }

    function clearState() {
        if (calculation.running)
            calculation.running=false;
        visualData=null;
        ready=false;
        failed=false;
        errorText="";
        loadedKey="";
        inflightKey="";
    }

    function refresh() {
        if (!active || !configured || currentKey === ""
                || calculation.running)return false;
        const spec=request();
        if(!spec)return false;
        visualData=null;
        ready=false;
        failed=false;
        errorText="";
        inflightKey=currentKey;
        // QML Process uses argv directly. No shell, redirects, user expressions
        // or writes to shared weather caches, user files or global locations.
        calculation.command=[
            pythonExecutable, "-B",
            Quickshell.configDir
                + "/scripts/weather/celestial_visual_data.py",
            "--kernel", kernelPath,
            "--query-json", JSON.stringify(spec)
        ];
        calculation.running=true;
        return true;
    }

    function accept(raw) {
        if (!active || !configured || inflightKey === ""
                || inflightKey !== currentKey)return;
        try {
            const text=String(raw || "");
            if (text.length < 100 || text.length > 524288)
                throw new Error("unexpected response size");
            const value=JSON.parse(text);
            if (!value || value.format !==
                    "post-apollo.weather.celestial-visual-data.v1"
                    || !value.provenance
                    || !/^[a-fA-F0-9]{64}$/.test(
                        String(value.provenance.ephemeris_sha256 || ""))
                    || !Array.isArray(value.series)
                    || value.series.length !== 2
                    || !Array.isArray(value.relationships)
                    || value.relationships.length !== 1
                    || !Array.isArray(value.event_markers)
                    || !value.query
                    || value.query.origin !== "geocentric"
                    || value.query.position_model !== "apparent"
                    || value.query.frame !== "true-ecliptic-of-date"
                    || JSON.stringify(value.query.bodies) !==
                        JSON.stringify(bodiesForRoute().slice().sort()))
                throw new Error("invalid M4 response");
            visualData=value;
            ready=true;
            failed=false;
            errorText="";
            loadedKey=inflightKey;
            lastCalculated=new Date();
        } catch (error) {
            visualData=null;
            ready=false;
            failed=true;
            errorText="M4 RESPONSE INVALID OR INCOMPLETE";
        }
    }

    Process {
        id: calculation
        command: []
        stdout: StdioCollector {
            onStreamFinished: celestial.accept(text)
        }
        onExited: function(exitCode, exitStatus) {
            if (!celestial.active || celestial.inflightKey === ""
                    || celestial.inflightKey !== celestial.currentKey)
                return;
            if (exitCode !== 0) {
                celestial.visualData=null;
                celestial.ready=false;
                celestial.failed=true;
                celestial.errorText="JPL BACKEND UNAVAILABLE // CHECK PATH + SKYFIELD";
            } else if (!celestial.ready) {
                celestial.failed=true;
                if(celestial.errorText==="")
                    celestial.errorText="JPL BACKEND RETURNED NO DATA";
            }
        }
    }

    // Route/date/config changes invalidate the old result, but never
    // auto-start calculations. The operator must click LOAD again.
    onCurrentKeyChanged: clearState()
    onActiveChanged: {
        if (!active) clearState();
    }
}
