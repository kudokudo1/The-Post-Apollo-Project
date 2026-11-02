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

var RETENTION_MEMORY_LAST_GOOD = "MEMORY_LAST_GOOD";
var RETENTION_PERSISTENT_LAST_GOOD = "PERSISTENT_LAST_GOOD";
var RETENTION_SESSION_CACHE = "SESSION_CACHE";
var RETENTION_KEY_BOUND = "KEY_BOUND";
var RETENTION_OPERATOR_SNAPSHOT = "OPERATOR_SNAPSHOT";
var RETENTION_FRAME_CACHE = "FRAME_CACHE";
var RETENTION_LOCAL = "LOCAL";
var RETENTION_NONE = "NONE";

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
        id:"weather-current",
        label:"CURRENT WEATHER",
        owner:"WeatherService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"GLOBAL",
        note:"current-condition view of the shared 15m WeatherService fetch"
    },
    {
        id:"weather-forecast",
        label:"WEATHER FORECAST",
        owner:"WeatherService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"GLOBAL",
        note:"forecast view of the same WeatherService response; receive time is not provider issue time"
    },
    {
        id:"air-quality",
        label:"AIR QUALITY + POLLEN",
        owner:"WeatherService.qml",
        mode:MODE_NORMAL_POLL,
        cadenceMs:900000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"GLOBAL",
        note:"Open-Meteo AQ request follows the shared weather location update"
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
        id:"space-kp",
        label:"NOAA PLANETARY KP",
        owner:"SpaceService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"SPACE",
        note:"Kp product from the shared SpaceService owner"
    },
    {
        id:"space-wind",
        label:"NOAA SOLAR WIND",
        owner:"SpaceService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"SPACE",
        note:"solar-wind product from the shared SpaceService owner"
    },
    {
        id:"space-imf",
        label:"NOAA IMF BT/BZ",
        owner:"SpaceService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"SPACE",
        note:"magnetic-field product from the shared SpaceService owner"
    },
    {
        id:"space-flux",
        label:"NOAA F10.7 FLUX",
        owner:"SpaceService.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"SPACE",
        note:"10.7cm flux product from the shared SpaceService owner"
    },
    {
        id:"nws-alerts",
        label:"NWS OFFICIAL ALERTS",
        owner:"services/notifications/NwsOfficialAlertNotificationProducer.qml",
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_SESSION_BACKGROUND,
        view:"GLOBAL",
        freshMs:600000,
        staleMs:1800000,
        note:"5m pinned-point poll; NWS alert service recommends no faster than 30s"
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
        mode:MODE_FAST_POLL,
        cadenceMs:300000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"GROUND/MAP",
        note:"5m shared poll against USGS summary feed, which publishes every minute"
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
        mode:MODE_SLOW_POLL,
        cadenceMs:1800000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"GROUND",
        note:"30m steady-state poll; NDBC says most stations report hourly"
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
        note:"15m strike-density product retained at matching 15m poll cadence"
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
        cadenceMs:360000,
        lifetime:LIFETIME_VIEW_SCOPED,
        view:"MAP",
        note:"matches GDACS documented six-minute principal-feed update cadence"
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

// M3 cache/offline policy. These are Post-Apollo presentation limits, not
// claims that the upstream provider guarantees usefulness for this duration.
// The limit describes how long a retained last-good payload may remain visible
// before Weather Station marks it EXPIRED. Disk persistence is not introduced
// here: MEMORY_LAST_GOOD and SESSION_CACHE remain process/session state.
var _cacheProfiles = {
    "weather": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:1200000, staleMs:5400000, expireMs:21600000
    },
    "weather-current": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:1200000, staleMs:5400000, expireMs:21600000
    },
    "weather-forecast": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:10800000, staleMs:86400000, expireMs:691200000
    },
    "air-quality": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:1800000, staleMs:10800000, expireMs:43200000
    },
    "space-core": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "space-kp": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "space-wind": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "space-imf": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "space-flux": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:1800000, staleMs:10800000, expireMs:43200000
    },
    "nws-alerts": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:21600000
    },
    "home-history": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:43200000, staleMs:86400000, expireMs:604800000
    },
    "seismic": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:86400000
    },
    "river": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:1800000, staleMs:7200000, expireMs:43200000
    },
    "marine": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:2700000, staleMs:7200000, expireMs:21600000
    },
    "coastal": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:1800000, staleMs:7200000, expireMs:86400000
    },
    "lightning": {
        retention:RETENTION_FRAME_CACHE,
        freshMs:1200000, staleMs:2700000, expireMs:7200000
    },
    "moon": {retention:RETENTION_KEY_BOUND},
    "eclipses": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:86400000, staleMs:604800000, expireMs:2592000000
    },
    "celnav": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "iss-passes": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:7200000, staleMs:21600000, expireMs:86400000
    },
    "planet-rise-set": {retention:RETENTION_KEY_BOUND},
    "meteor-showers": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:43200000, staleMs:86400000, expireMs:604800000
    },
    "aurora": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:1200000, staleMs:2700000, expireMs:7200000
    },
    "solar-flares": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:1800000, staleMs:7200000, expireMs:43200000
    },
    "xray-flux": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "swpc-alerts": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:1200000, staleMs:3600000, expireMs:21600000
    },
    "solar-cycle": {retention:RETENTION_KEY_BOUND},
    "noaa-scales": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "kp-forecast": {
        retention:RETENTION_MEMORY_LAST_GOOD,
        freshMs:1800000, staleMs:10800000, expireMs:43200000
    },
    "discovery": {
        retention:RETENTION_SESSION_CACHE,
        freshMs:1800000, staleMs:7200000, expireMs:86400000
    },
    "gdacs": {
        retention:RETENTION_PERSISTENT_LAST_GOOD,
        freshMs:900000, staleMs:3600000, expireMs:86400000
    },
    "firms": {
        retention:RETENTION_OPERATOR_SNAPSHOT,
        freshMs:7200000, staleMs:21600000, expireMs:86400000
    },
    "hms-smoke": {
        retention:RETENTION_OPERATOR_SNAPSHOT,
        freshMs:21600000, staleMs:43200000, expireMs:129600000
    },
    "rainviewer": {
        retention:RETENTION_FRAME_CACHE,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "gdelt-article-location": {
        retention:RETENTION_OPERATOR_SNAPSHOT,
        freshMs:21600000, staleMs:86400000, expireMs:604800000
    },
    "mrms-radar": {
        retention:RETENTION_FRAME_CACHE,
        freshMs:600000, staleMs:1800000, expireMs:7200000
    },
    "sky-local": {retention:RETENTION_LOCAL}
};

function defaultRetention(spec) {
    if (!spec)
        return RETENTION_NONE;
    if (spec.mode === MODE_KEYED_FETCH)
        return RETENTION_KEY_BOUND;
    if (spec.mode === MODE_MANUAL)
        return RETENTION_OPERATOR_SNAPSHOT;
    if (spec.mode === MODE_LOCAL_CALC)
        return RETENTION_LOCAL;
    return RETENTION_MEMORY_LAST_GOOD;
}

function withCacheProfile(row) {
    if (!row)
        return null;
    const copy = {};
    const keys = Object.keys(row);
    for (let i = 0; i < keys.length; i++)
        copy[keys[i]] = row[keys[i]];

    const profile = _cacheProfiles[copy.id] || {};
    const profileKeys = Object.keys(profile);
    for (let i = 0; i < profileKeys.length; i++)
        copy[profileKeys[i]] = profile[profileKeys[i]];

    if (!copy.retention)
        copy.retention = defaultRetention(copy);
    return copy;
}

function sourceCatalog() {
    return _catalog.map(function(row) {
        return withCacheProfile(row);
    });
}

function sourceSpec(id) {
    const key = String(id || "");
    for (let i = 0; i < _catalog.length; i++) {
        if (_catalog[i].id === key)
            return withCacheProfile(_catalog[i]);
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

function effectiveExpireMs(spec) {
    if (!spec)
        return 0;
    if (Number(spec.expireMs) > 0)
        return Number(spec.expireMs);
    const staleMs = effectiveStaleMs(spec);
    return staleMs > 0 ? staleMs * 4 : 0;
}

function temporalBand(spec, receivedAt, nowValue) {
    if (!spec)
        return "UNKNOWN";
    if (spec.mode === MODE_KEYED_FETCH)
        return "KEYED";
    if (spec.mode === MODE_LOCAL_CALC)
        return "LOCAL";

    const age = ageMs(receivedAt, nowValue);
    if (age < 0)
        return "UNKNOWN";

    const freshMs = effectiveFreshMs(spec);
    const staleMs = effectiveStaleMs(spec);
    const expireMs = effectiveExpireMs(spec);

    if (freshMs > 0 && age <= freshMs)
        return "FRESH";
    if (staleMs > 0 && age <= staleMs)
        return "AGING";
    if (expireMs > 0 && age <= expireMs)
        return "STALE";
    if (expireMs > 0 && age > expireMs)
        return "EXPIRED";
    return "STALE";
}

function freshness(spec, receivedAt, nowValue) {
    if (!spec)
        return "UNKNOWN";
    // runtimeState() calls freshness only after the source is ready.
    // Manual/keyed readiness is therefore meaningful even when an older
    // service does not yet expose a dedicated receive timestamp.
    if (spec.mode === MODE_MANUAL)
        return "SNAPSHOT";
    if (spec.mode === MODE_KEYED_FETCH)
        return "KEYED";
    if (spec.mode === MODE_LOCAL_CALC)
        return "LOCAL";

    return temporalBand(spec, receivedAt, nowValue);
}

function retainsLastGood(spec) {
    if (!spec)
        return false;
    return spec.retention === RETENTION_MEMORY_LAST_GOOD
        || spec.retention === RETENTION_PERSISTENT_LAST_GOOD
        || spec.retention === RETENTION_SESSION_CACHE
        || spec.retention === RETENTION_FRAME_CACHE;
}

function availabilityState(spec, state, ageBand) {
    const value = state || {};
    const active = value.active !== false;
    const ready = value.ready === true;
    const loading = value.loading === true;
    const failed = value.failed === true;
    const usingCache = value.usingCache === true;
    const band = String(ageBand || "UNKNOWN");

    if (!active)
        return "INACTIVE";

    if (spec && spec.mode === MODE_LOCAL_CALC)
        return ready ? "LOCAL" : "WAITING";

    if (spec && spec.mode === MODE_KEYED_FETCH) {
        if (loading && !ready)
            return "READING";
        if (ready)
            return failed ? "KEY_DEGRADED" : "KEY_VALID";
        return failed ? "OFFLINE" : "WAITING";
    }

    if (usingCache && spec && spec.retention === RETENTION_FRAME_CACHE) {
        if (band === "EXPIRED")
            return "FRAME_CACHE_EXPIRED";
        if (band === "STALE")
            return "FRAME_CACHE_STALE";
        if (band === "AGING")
            return "FRAME_CACHE_AGING";
        return "FRAME_CACHE_FRESH";
    }

    if (spec && spec.mode === MODE_MANUAL) {
        if (loading && !ready)
            return "READING";
        if (!ready)
            return failed ? "OFFLINE" : "WAITING";
        if (band === "EXPIRED")
            return "SNAPSHOT_EXPIRED";
        if (band === "STALE")
            return "SNAPSHOT_STALE";
        if (band === "AGING")
            return "SNAPSHOT_AGING";
        return "SNAPSHOT";
    }

    if (!ready) {
        if (loading)
            return "READING";
        return failed ? "OFFLINE" : "WAITING";
    }

    const retained = failed || usingCache;
    if (retained && retainsLastGood(spec)) {
        if (band === "EXPIRED")
            return "CACHE_EXPIRED";
        if (band === "STALE")
            return "CACHE_STALE";
        if (band === "AGING")
            return "CACHE_AGING";
        return "CACHE_FRESH";
    }

    if (retained && !retainsLastGood(spec))
        return "OFFLINE";

    if (band === "EXPIRED")
        return "EXPIRED";
    if (band === "STALE")
        return "LIVE_STALE";
    if (band === "AGING")
        return "LIVE_AGING";
    return "LIVE";
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
    const ageBand = ready
        ? temporalBand(spec, receivedAtMs, nowMs)
        : "UNKNOWN";

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
        retention: spec ? spec.retention : RETENTION_NONE,
        cadenceMs: spec ? Number(spec.cadenceMs) || 0 : 0,
        expireMs: effectiveExpireMs(spec),
        transport: transport,
        freshness: ready ? freshness(spec, receivedAtMs, nowMs) : "UNKNOWN",
        ageBand: ageBand,
        availability: availabilityState(
            spec,
            {
                "active": active,
                "ready": ready,
                "loading": loading,
                "failed": failed,
                "usingCache": state.usingCache === true
            },
            ageBand
        ),
        usingCache: state.usingCache === true,
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
        retention: state.retention,
        cadenceMs: state.cadenceMs,
        expireMs: state.expireMs,
        transport: state.transport,
        freshness: state.freshness,
        ageBand: state.ageBand,
        availability: state.availability,
        usingCache: state.usingCache,
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

    const state = String(row.availability || "");
    if (state === "OFFLINE"
            || state === "EXPIRED"
            || state === "CACHE_EXPIRED"
            || state === "FRAME_CACHE_EXPIRED"
            || state === "SNAPSHOT_EXPIRED")
        return "red";

    if (state === "LIVE_STALE"
            || state === "CACHE_STALE"
            || state === "CACHE_AGING"
            || state === "FRAME_CACHE_STALE"
            || state === "FRAME_CACHE_AGING"
            || state === "SNAPSHOT_STALE"
            || state === "SNAPSHOT_AGING"
            || state === "LIVE_AGING"
            || state === "KEY_DEGRADED")
        return "yellow";

    if (state === "READING" || state === "WAITING")
        return "orange";
    if (state === "INACTIVE")
        return "blue";
    if (state === "CACHE_FRESH"
            || state === "FRAME_CACHE_FRESH"
            || state === "KEY_VALID")
        return "blue";
    if (state === "SNAPSHOT")
        return "magenta";
    if (state === "LOCAL")
        return "green";
    if (state === "LIVE")
        return "cyan";

    return row.transport === "ERROR" ? "red" : "orange";
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

function availabilityLabel(row) {
    if (!row)
        return "UNKNOWN";
    switch (String(row.availability || "")) {
    case "LIVE": return "LIVE // FRESH";
    case "LIVE_AGING": return "LIVE // AGING";
    case "LIVE_STALE": return "LIVE // STALE";
    case "EXPIRED": return "LIVE // EXPIRED";
    case "CACHE_FRESH": return "CACHE // FRESH";
    case "CACHE_AGING": return "CACHE // AGING";
    case "CACHE_STALE": return "CACHE // STALE";
    case "CACHE_EXPIRED": return "CACHE // EXPIRED";
    case "FRAME_CACHE_FRESH": return "FRAME CACHE // FRESH";
    case "FRAME_CACHE_AGING": return "FRAME CACHE // AGING";
    case "FRAME_CACHE_STALE": return "FRAME CACHE // STALE";
    case "FRAME_CACHE_EXPIRED": return "FRAME CACHE // EXPIRED";
    case "SNAPSHOT": return "SNAPSHOT // FRESH";
    case "SNAPSHOT_AGING": return "SNAPSHOT // AGING";
    case "SNAPSHOT_STALE": return "SNAPSHOT // STALE";
    case "SNAPSHOT_EXPIRED": return "SNAPSHOT // EXPIRED";
    case "KEY_VALID": return "KEYED // VALID";
    case "KEY_DEGRADED": return "KEYED // DEGRADED";
    case "LOCAL": return "LOCAL";
    case "READING": return "READING";
    case "OFFLINE": return "OFFLINE";
    case "WAITING": return "WAITING";
    case "INACTIVE": return "INACTIVE";
    default: return "UNKNOWN";
    }
}

function rowStateLabel(row) {
    return availabilityLabel(row);
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

function compactDurationMs(ms) {
    const value = Number(ms);
    if (!isFinite(value) || value <= 0)
        return "--";
    const minutes = value / 60000;
    if (minutes < 60)
        return Math.round(minutes) + "m";
    const hours = minutes / 60;
    if (hours < 24)
        return (hours < 10 && hours % 1 !== 0
                ? hours.toFixed(1) : Math.round(hours)) + "h";
    const days = hours / 24;
    return (days < 10 && days % 1 !== 0
            ? days.toFixed(1) : Math.round(days)) + "d";
}

function retentionLabel(row) {
    if (!row)
        return "--";
    if (row.retention === RETENTION_KEY_BOUND)
        return "KEY-BOUND";
    if (row.retention === RETENTION_LOCAL)
        return "LOCAL";
    if (row.retention === RETENTION_NONE)
        return "NO RETAIN";

    const limit = Number(row.expireMs) > 0
        ? compactDurationMs(row.expireMs) : "--";

    if (row.retention === RETENTION_OPERATOR_SNAPSHOT)
        return "SNAPSHOT≤" + limit;
    if (row.retention === RETENTION_FRAME_CACHE)
        return "FRAME≤" + limit;
    if (row.retention === RETENTION_SESSION_CACHE)
        return "SESSION≤" + limit;
    if (row.retention === RETENTION_PERSISTENT_LAST_GOOD)
        return "PERSIST≤" + limit;
    if (row.retention === RETENTION_MEMORY_LAST_GOOD)
        return "MEMORY≤" + limit;
    return row.retention;
}

function summarizeRows(rows) {
    const list = Array.isArray(rows) ? rows : [];
    let ready = 0;
    let loading = 0;
    let problem = 0;
    let stale = 0;
    let cached = 0;
    let expired = 0;
    let offline = 0;
    let manual = 0;
    let keyed = 0;
    let local = 0;

    for (let i = 0; i < list.length; i++) {
        const row = list[i] || {};
        const availability = String(row.availability || "");
        if (row.transport === "READY"
                || row.transport === "DEGRADED")
            ready++;
        if (row.transport === "LOADING")
            loading++;
        if (row.transport === "ERROR")
            problem++;
        if (row.ageBand === "STALE")
            stale++;
        if (availability.indexOf("CACHE_") === 0
                || availability.indexOf("FRAME_CACHE_") === 0)
            cached++;
        if (availability.indexOf("EXPIRED") >= 0)
            expired++;
        if (availability === "OFFLINE")
            offline++;
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
        cached: cached,
        expired: expired,
        offline: offline,
        manual: manual,
        keyed: keyed,
        local: local
    };
}

