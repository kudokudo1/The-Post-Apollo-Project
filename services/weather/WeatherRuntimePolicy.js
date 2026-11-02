.pragma library

// Weather Live Runtime M1
//
// This is the shared runtime vocabulary for Weather Station data ownership.
// It does not start network traffic. Existing provider services remain the
// fetch owners. The catalog records their CURRENT behavior so later cadence
// changes can be deliberate rather than inferred from scattered Timers.

var MODE_STREAM = "STREAM";
var MODE_FAST_POLL = "FAST_POLL";
var MODE_NORMAL_POLL = "NORMAL_POLL";
var MODE_SLOW_POLL = "SLOW_POLL";
var MODE_KEYED_FETCH = "KEYED_FETCH";
var MODE_LOCAL_CALC = "LOCAL_CALC";
var MODE_MANUAL = "MANUAL";

var LIFETIME_SESSION_BACKGROUND = "SESSION_BACKGROUND";
var LIFETIME_VIEW_SCOPED = "VIEW_SCOPED";
var LIFETIME_KEYED_VIEW = "KEYED_VIEW";
var LIFETIME_OPERATOR_REQUEST = "OPERATOR_REQUEST";
var LIFETIME_LOCAL = "LOCAL";

var _catalog = [
    {
        id:"weather",
        label:"WEATHER + FORECAST + AQI",
        owner:"WeatherService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"GLOBAL",
        freshMs:1200000,
        staleMs:21600000,
        note:"15m session-wide weather fetch; AQI follows the weather response"
    },
    {
        id:"space-core",
        label:"NOAA SPACE CORE",
        owner:"SpaceService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"GLOBAL",
        freshMs:600000,
        staleMs:1800000,
        note:"Kp, solar wind, magnetic field and solar flux share one 5m owner"
    },
    {
        id:"nws-alerts",
        label:"NWS OFFICIAL ALERTS",
        owner:"services/notifications/NwsOfficialAlertNotificationProducer.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"GLOBAL",
        freshMs:1800000,
        staleMs:3600000,
        note:"conditional on operator-pinned NWS alert point"
    },
    {
        id:"home-history",
        label:"HOME HISTORICAL FORECAST",
        owner:"WeatherHistoryService.qml",
        mode:MODE_SLOW_POLL,
        cadenceMs:21600000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"HOME",
        freshMs:43200000,
        staleMs:86400000,
        note:"historical forecast context; not live observations"
    },
    {
        id:"seismic",
        label:"USGS EARTHQUAKES",
        owner:"SeismicService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"GROUND/MAP",
        note:"one retained set shared by GROUND and MAP while either view owns it"
    },
    {
        id:"river",
        label:"NOAA NWPS RIVER",
        owner:"NwpsRiverService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"GROUND"
    },
    {
        id:"marine",
        label:"NOAA NDBC MARINE",
        owner:"NdbcMarineService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:600000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"GROUND"
    },
    {
        id:"coastal",
        label:"NOAA CO-OPS COASTAL",
        owner:"CoopsCoastalService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"GROUND"
    },
    {
        id:"lightning",
        label:"NOAA NOWCOAST LIGHTNING",
        owner:"NowcoastLightningService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"GROUND",
        note:"current code polls 15m; faster live cadence is a later provider-policy decision"
    },
    {
        id:"moon",
        label:"USNO MOON EPHEMERIS",
        owner:"UsnoMoonService.qml",
        mode:MODE_KEYED_FETCH,
        cadenceMs:0,
        lifetime:LIFETIME_KEYED_VIEW,
        view:"SKY",
        note:"fetches on date/location/UTC-offset request-key changes"
    },
    {
        id:"eclipses",
        label:"NASA GSFC ECLIPSES",
        owner:"NasaEclipseService.qml",
        mode:MODE_SLOW_POLL,
        cadenceMs:43200000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SKY"
    },
    {
        id:"celnav",
        label:"USNO CELESTIAL NAVIGATION",
        owner:"UsnoCelnavService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SKY"
    },
    {
        id:"iss-passes",
        label:"ISS PASS PREDICTION",
        owner:"IssPassService.qml",
        mode:MODE_SLOW_POLL,
        cadenceMs:7200000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SKY"
    },
    {
        id:"planet-rise-set",
        label:"USNO PLANET RISE/SET",
        owner:"UsnoPlanetRiseSetService.qml",
        mode:MODE_KEYED_FETCH,
        cadenceMs:0,
        lifetime:LIFETIME_KEYED_VIEW,
        view:"SKY",
        note:"fetches on date/location/UTC-offset request-key changes"
    },
    {
        id:"meteor-showers",
        label:"IAU METEOR SHOWERS",
        owner:"IauMeteorShowerService.qml",
        mode:MODE_SLOW_POLL,
        cadenceMs:21600000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SKY"
    },
    {
        id:"aurora",
        label:"NOAA OVATION AURORA",
        owner:"AuroraService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SPACE"
    },
    {
        id:"solar-flares",
        label:"NOAA GOES SOLAR FLARES",
        owner:"SolarFlareService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SPACE"
    },
    {
        id:"xray-flux",
        label:"NOAA GOES X-RAY FLUX",
        owner:"XrayFluxService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SPACE"
    },
    {
        id:"swpc-alerts",
        label:"NOAA SWPC ALERTS",
        owner:"SwpcAlertService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:600000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SPACE"
    },
    {
        id:"solar-cycle",
        label:"NOAA SOLAR CYCLE",
        owner:"SolarCycleService.qml",
        mode:MODE_KEYED_FETCH,
        cadenceMs:0,
        lifetime:LIFETIME_KEYED_VIEW,
        view:"SPACE",
        note:"refreshes when the month key changes, not on a repeating timer"
    },
    {
        id:"noaa-scales",
        label:"NOAA G/R/S SCALES",
        owner:"NoaaScalesService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SPACE"
    },
    {
        id:"kp-forecast",
        label:"NOAA KP FORECAST",
        owner:"KpForecastService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"SPACE"
    },
    {
        id:"discovery",
        label:"EONET / GDELT DISCOVERY",
        owner:"StationDiscoveryService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"MAP/NEWS"
    },
    {
        id:"gdacs",
        label:"GDACS GLOBAL DISASTERS",
        owner:"GdacsService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"MAP"
    },
    {
        id:"firms",
        label:"NASA FIRMS HOTSPOTS",
        owner:"FirmsHotspotService.qml",
        mode:MODE_MANUAL,
        cadenceMs:0,
        lifetime:LIFETIME_OPERATOR_REQUEST,
        view:"MAP"
    },
    {
        id:"hms-smoke",
        label:"NOAA HMS SMOKE",
        owner:"HmsSmokeService.qml",
        mode:MODE_MANUAL,
        cadenceMs:0,
        lifetime:LIFETIME_OPERATOR_REQUEST,
        view:"MAP"
    },
    {
        id:"rainviewer",
        label:"RAINVIEWER RADAR FALLBACK",
        owner:"RainViewerRadarService.qml",
        mode:MODE_MANUAL,
        cadenceMs:0,
        lifetime:LIFETIME_OPERATOR_REQUEST,
        view:"MAP"
    },
    {
        id:"gdelt-article-location",
        label:"GDELT ARTICLE LOCATION",
        owner:"GdeltArticleLocationService.qml",
        mode:MODE_MANUAL,
        cadenceMs:0,
        lifetime:LIFETIME_OPERATOR_REQUEST,
        view:"NEWS/MAP"
    },
    {
        id:"mrms-radar",
        label:"NOAA/NWS MRMS RADAR",
        owner:"widgets/weather/StationDiscovery.qml",
        mode:MODE_MANUAL,
        cadenceMs:0,
        lifetime:LIFETIME_OPERATOR_REQUEST,
        view:"MAP",
        note:"operator-requested Image snapshot; no repeating provider timer"
    },
    {
        id:"sky-local",
        label:"SKY LOCAL CALCULATIONS",
        owner:"widgets/weather/StationSky.qml",
        mode:MODE_LOCAL_CALC,
        cadenceMs:0,
        lifetime:LIFETIME_LOCAL,
        view:"SKY",
        note:"solar position/twilight derived locally from retained provider data"
    }
];

function sourceCatalog() {
    return _catalog.map(function(row) {
        const copy = {};
        const keys = Object.keys(row);
        for (let i = 0; i < keys.length; i++)
            copy[keys[i]] = row[keys[i]];
        return copy;
    });
}

function sourceSpec(id) {
    const key = String(id || "");
    for (let i = 0; i < _catalog.length; i++) {
        if (_catalog[i].id === key)
            return sourceCatalog()[i];
    }
    return null;
}

function timestampMs(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    if (typeof value === "number")
        return isFinite(value) && value > 0 ? value : -1;
    if (typeof value.getTime === "function") {
        const ms = value.getTime();
        return isFinite(ms) && ms > 0 ? ms : -1;
    }
    const parsed = Date.parse(String(value));
    return isFinite(parsed) && parsed > 0 ? parsed : -1;
}

function ageMs(value, nowValue) {
    const stamp = timestampMs(value);
    const now = timestampMs(nowValue);
    if (stamp <= 0 || now <= 0)
        return -1;
    return Math.max(0, now - stamp);
}

function ageMinutes(value, nowValue) {
    const age = ageMs(value, nowValue);
    return age < 0 ? -1 : Math.floor(age / 60000);
}

function effectiveFreshMs(spec) {
    if (!spec)
        return 0;
    if (Number(spec.freshMs) > 0)
        return Number(spec.freshMs);
    const cadence = Number(spec.cadenceMs) || 0;
    return cadence > 0 ? cadence * 2 : 0;
}

function effectiveStaleMs(spec) {
    if (!spec)
        return 0;
    if (Number(spec.staleMs) > 0)
        return Number(spec.staleMs);
    const cadence = Number(spec.cadenceMs) || 0;
    return cadence > 0 ? cadence * 6 : 0;
}

function freshness(spec, receivedAt, nowValue) {
    if (!spec)
        return "UNKNOWN";
    if (spec.mode === MODE_MANUAL)
        return timestampMs(receivedAt) > 0 ? "SNAPSHOT" : "WAITING";
    if (spec.mode === MODE_KEYED_FETCH)
        return timestampMs(receivedAt) > 0 ? "KEYED" : "WAITING";
    if (spec.mode === MODE_LOCAL_CALC)
        return "LOCAL";

    const age = ageMs(receivedAt, nowValue);
    if (age < 0)
        return "UNKNOWN";

    const freshMs = effectiveFreshMs(spec);
    const staleMs = effectiveStaleMs(spec);
    if (freshMs > 0 && age <= freshMs)
        return "FRESH";
    if (staleMs > 0 && age <= staleMs)
        return "AGING";
    return "STALE";
}

function runtimeState(spec, input, nowValue) {
    const state = input || {};
    const active = state.active !== false;
    const ready = state.ready === true;
    const loading = state.loading === true;
    const failed = state.failed === true
        || String(state.errorText || "").length > 0;
    const receivedAtMs = timestampMs(state.receivedAt);
    const observedAtMs = timestampMs(state.observedAt);
    const nowMs = timestampMs(nowValue);

    let transport = "WAITING";
    if (!active)
        transport = "INACTIVE";
    else if (loading)
        transport = "LOADING";
    else if (ready)
        transport = failed ? "DEGRADED" : "READY";
    else if (failed)
        transport = "ERROR";

    return {
        id: spec ? spec.id : "",
        mode: spec ? spec.mode : "",
        lifetime: spec ? spec.lifetime : "",
        cadenceMs: spec ? Number(spec.cadenceMs) || 0 : 0,
        transport: transport,
        freshness: ready ? freshness(spec, receivedAtMs, nowMs) : "UNKNOWN",
        receivedAtMs: receivedAtMs,
        observedAtMs: observedAtMs,
        receivedAgeMs: ageMs(receivedAtMs, nowMs),
        observationAgeMs: ageMs(observedAtMs, nowMs),
        ready: ready,
        loading: loading,
        failed: failed,
        active: active
    };
}

function compactAgeMinutes(minutes) {
    const value = Number(minutes);
    if (!isFinite(value) || value < 0)
        return "--";
    if (value === 0)
        return "<1m";
    if (value < 60)
        return Math.floor(value) + "m";
    const hours = value / 60;
    return hours < 24 ? hours.toFixed(hours < 10 ? 1 : 0) + "h"
                      : Math.floor(hours / 24) + "d";
}

function displayRow(sourceId, input, nowValue) {
    const spec = sourceSpec(sourceId);
    const state = runtimeState(spec, input, nowValue);
    const receivedMinutes = state.receivedAgeMs < 0
        ? -1 : Math.floor(state.receivedAgeMs / 60000);
    const observationMinutes = state.observationAgeMs < 0
        ? -1 : Math.floor(state.observationAgeMs / 60000);

    return {
        id: state.id,
        label: spec ? spec.label : String(sourceId || "").toUpperCase(),
        mode: state.mode,
        lifetime: state.lifetime,
        cadenceMs: state.cadenceMs,
        transport: state.transport,
        freshness: state.freshness,
        receivedAgeMinutes: receivedMinutes,
        observationAgeMinutes: observationMinutes,
        ready: state.ready,
        loading: state.loading,
        failed: state.failed,
        active: state.active,
        detail: input && input.detail ? String(input.detail) : ""
    };
}

function statusToken(row) {
    if (!row)
        return "orange";
    if (row.transport === "ERROR")
        return "red";
    if (row.transport === "DEGRADED"
            || row.freshness === "STALE")
        return "yellow";
    if (row.transport === "LOADING")
        return "orange";
    if (row.transport === "INACTIVE")
        return "blue";
    if (row.freshness === "AGING")
        return "yellow";
    if (row.freshness === "SNAPSHOT")
        return "magenta";
    if (row.freshness === "KEYED")
        return "blue";
    if (row.freshness === "LOCAL")
        return "green";
    if (row.transport === "READY" && row.freshness === "FRESH")
        return "cyan";
    if (row.transport === "READY")
        return "cyan";
    return "orange";
}

function cadenceLabel(row) {
    if (!row)
        return "--";
    if (row.mode === MODE_STREAM)
        return "STREAM";
    if (row.mode === MODE_MANUAL)
        return "ON REQUEST";
    if (row.mode === MODE_KEYED_FETCH)
        return "ON KEY CHANGE";
    if (row.mode === MODE_LOCAL_CALC)
        return "LOCAL";
    const ms = Number(row.cadenceMs) || 0;
    if (ms <= 0)
        return row.mode || "--";
    const minutes = ms / 60000;
    if (minutes < 60)
        return minutes.toFixed(minutes < 10 && minutes % 1 !== 0 ? 1 : 0) + "m";
    const hours = minutes / 60;
    return hours < 24
        ? hours.toFixed(hours < 10 && hours % 1 !== 0 ? 1 : 0) + "h"
        : (hours / 24).toFixed((hours / 24) < 10 ? 1 : 0) + "d";
}

function rowStateLabel(row) {
    if (!row)
        return "UNKNOWN";
    const parts = [row.transport];
    if (row.freshness && row.freshness !== "UNKNOWN")
        parts.push(row.freshness);
    return parts.join(" // ");
}

function rowAgeLabel(row) {
    if (!row)
        return "RX --";
    const parts = [];
    if (row.receivedAgeMinutes >= 0)
        parts.push("RX " + compactAgeMinutes(row.receivedAgeMinutes));
    else if (row.freshness === "LOCAL")
        parts.push("LOCAL NOW");
    else
        parts.push("RX --");

    if (row.observationAgeMinutes >= 0)
        parts.push("OBS " + compactAgeMinutes(row.observationAgeMinutes));
    return parts.join(" // ");
}

function summarizeRows(rows) {
    const list = Array.isArray(rows) ? rows : [];
    let ready = 0;
    let loading = 0;
    let problem = 0;
    let stale = 0;
    let manual = 0;
    let keyed = 0;
    let local = 0;

    for (let i = 0; i < list.length; i++) {
        const row = list[i] || {};
        if (row.transport === "READY"
                || row.transport === "DEGRADED")
            ready++;
        if (row.transport === "LOADING")
            loading++;
        if (row.transport === "ERROR")
            problem++;
        if (row.freshness === "STALE")
            stale++;
        if (row.mode === MODE_MANUAL)
            manual++;
        if (row.mode === MODE_KEYED_FETCH)
            keyed++;
        if (row.mode === MODE_LOCAL_CALC)
            local++;
    }

    return {
        total: list.length,
        ready: ready,
        loading: loading,
        problem: problem,
        stale: stale,
        manual: manual,
        keyed: keyed,
        local: local
    };
}

