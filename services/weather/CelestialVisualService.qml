import QtQuick
import Quickshell
import Quickshell.Io
import "CelestialVisualQueryPolicy.js" as Query
import "CelestialVisualInstallPolicy.js" as Install

// MAGICK M5c // Single on-demand calculation owner, hosted by WeatherStationW.
// Never polls, downloads, infers user location, or writes files.
// Automatically reuses the existing home-local MAGICK installation.
// Optional POST_APOLLO_CELESTIAL_KERNEL and POST_APOLLO_CELESTIAL_PYTHON
// environment overrides remain supported for development installations.
Scope {
    id: celestial

    property bool active: false
    property string route: ""
    property real anchorNowMs: 0
    // These resolve paths only, not file existence. A missing installation
    // fails safely when CALCULATE attempts to use the existing M4 backend.
    readonly property string installHome:
        String(Quickshell.env("HOME") || "")
    readonly property string kernelOverride:
        String(Quickshell.env("POST_APOLLO_CELESTIAL_KERNEL") || "")
    readonly property string pythonOverride:
        String(Quickshell.env("POST_APOLLO_CELESTIAL_PYTHON") || "")
    property string kernelPath:
        Install.resolveKernel(kernelOverride, installHome)
    property string pythonExecutable:
        Install.resolvePython(pythonOverride, installHome)
    readonly property string pathSource:
        Install.pathSource(kernelOverride, pythonOverride, installHome)

    property var visualData: null
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property string loadedKey: ""
    property string inflightKey: ""
    property date lastCalculated

    // M5c // Only two exact JPL targets per request, preserving M4 event limits.
    property string pairPreset: "moon-sun"
    property int dateOffsetDays: 0
    property int spanDays: 29
    readonly property string pairLabel:
        Query.pairFor(pairPreset) ? Query.pairFor(pairPreset).label : "UNKNOWN PAIR"
    readonly property string targetDayUtc:
        Query.dayFor(anchorDayUtc,dateOffsetDays)

    readonly property bool loading: calculation.running
    readonly property bool configured:
        kernelPath.trim() !== "" && pythonExecutable.trim() !== ""
    readonly property string anchorDayUtc:
        isFinite(anchorNowMs) && anchorNowMs > 0
        ? new Date(anchorNowMs).toISOString().slice(0, 10) : ""
    readonly property string currentKey:
        active && configured && targetDayUtc !== ""
        && Query.requestFor(anchorDayUtc,dateOffsetDays,pairPreset,spanDays)
        ? kernelPath + "|" + pythonExecutable + "|" + targetDayUtc
          + "|" + pairPreset + "|" + spanDays
        : ""
    readonly property string statusText:
        !configured ? "SET POST_APOLLO_CELESTIAL_KERNEL (AND SKYFIELD)"
        : targetDayUtc === "" ? "UTC CLOCK OR DATE RANGE UNAVAILABLE"
        : loading ? "JPL CALCULATION RUNNING"
        : failed ? errorText
        : ready ? "SOURCE-VERIFIED JPL DATA LOADED"
        : "READY // SELECT LOAD CALCULATION"

    function request() {
        return Query.requestFor(anchorDayUtc,dateOffsetDays,pairPreset,spanDays);
    }

    function shiftDate(days) {
        const next=Query.shiftOffset(dateOffsetDays,days);
        if (next===null)return false;
        dateOffsetDays=next;
        return true;
    }
    function returnToToday() { dateOffsetDays=0; }
    function cyclePair(direction) { pairPreset=Query.pairAfter(pairPreset,direction); }
    function setSpan(days) {
        if (Query.SPANS.indexOf(days)<0)return false;
        spanDays=days;
        return true;
    }
    function cycleSpan() { spanDays=Query.spanAfter(spanDays); }

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
                    || !Query.matchesResult(value,request()))
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

    // Route/date/pair/span changes invalidate results but never auto-load.
    // Navigating to RETROGRADES selects Mercury/Sun by default.
    onRouteChanged: {
        pairPreset=Query.initialPairForRoute(route);
        dateOffsetDays=0;
        spanDays=29;
    }
    onCurrentKeyChanged: clearState()
    onActiveChanged: {
        if (!active) clearState();
    }
}
