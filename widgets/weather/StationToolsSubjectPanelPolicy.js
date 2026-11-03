.pragma library

// TOOLS T1 // passive readers over existing source/store policies.
// No new writer, fetcher, terminal process or settings mutation.
var FORMAT = "post-apollo.weather.tools-panels.t1.v1";
var ROUTES = {
    "tools/overview": {kind:"overview", title:"TOOLS // STATION OPERATIONS"},
    "tools/terminal/star-map": {kind:"terminal", title:"TERMINAL // STAR MAP"},
    "tools/terminal/consoles": {kind:"terminal", title:"TERMINAL // CONTEXT CONSOLES"},
    "tools/sources/health": {kind:"sources", title:"SOURCES // LIVE HEALTH"},
    "tools/sources/provenance": {kind:"sources", title:"SOURCES // PROVENANCE"},
    "tools/storage/cache": {kind:"storage", title:"STORAGE // LAST KNOWN CACHE"},
    "tools/storage/history": {kind:"storage", title:"STORAGE // LIVE HISTORY"},
    "tools/storage/events": {kind:"storage", title:"STORAGE // EVENT ARCHIVE"},
    "tools/storage/frames": {kind:"storage", title:"STORAGE // FRAME CACHE CONTRACT"},
    "tools/settings/location": {kind:"settings", title:"SETTINGS // LOCATION CONTEXT"},
    "tools/settings/display": {kind:"settings", title:"SETTINGS // DISPLAY CONVENTIONS"}
};
function routeInfo(path) {
    return typeof path === "string"
        && Object.prototype.hasOwnProperty.call(ROUTES,path)
        ? ROUTES[path] : null;
}
function kindForRoute(path) {
    var row=routeInfo(path);
    return row ? row.kind : "";
}
function titleFor(path) {
    var row=routeInfo(path);
    return row ? row.title : "";
}
function shows(path,section) {
    if (!routeInfo(path)) return false;
    if (path === "tools/overview")
        return section === "health" || section === "storage"
            || section === "terminal" || section === "summary";
    if (section === "terminal")
        return kindForRoute(path) === "terminal";
    if (section === "health")
        return path === "tools/sources/health";
    if (section === "provenance")
        return path === "tools/sources/provenance";
    if (section === "storage")
        return kindForRoute(path) === "storage";
    if (section === "frames")
        return path === "tools/storage/frames";
    if (section === "location")
        return path === "tools/settings/location";
    if (section === "display")
        return path === "tools/settings/display";
    return false;
}
var CONSOLE_MODES = ["home","ground","sky","space","map","news","radio"];
function isConsoleMode(value) {
    return CONSOLE_MODES.indexOf(value) !== -1;
}
function terminalModeForRoute(path,consoleMode) {
    // Exact existing StationTerminal modes, not a CLASSIC route or command.
    if (path === "tools/terminal/star-map") return "terminal";
    if (path === "tools/terminal/consoles")
        return isConsoleMode(consoleMode) ? consoleMode : "home";
    return "";
}
function titleForTerminalAction(path) {
    if (path === "tools/terminal/star-map")
        return "LAUNCH STAR MAP";
    if (path === "tools/terminal/consoles")
        return "LAUNCH CONTEXT CONSOLE";
    return "";
}
function terminalInstructions(path) {
    if (path === "tools/terminal/star-map")
        return "START THE ORIGINAL STAR MAP KITTY IN THE STATION TERMINAL VIEWPORT. THE STATION HEADER CLOSE BUTTON TARGETS ONLY THIS CONFIRMED ACTOR. NO CLASSIC ROUTE IS OPENED.";
    if (path === "tools/terminal/consoles")
        return "CHOOSE HOME, GROUND, SKY, SPACE, MAP, NEWS OR RADIO. THE ORIGINAL KITTY CONTROLLER OPENS A PLAIN BASH CONSOLE WITH A UNIQUE MODE-SCOPED APP-ID, VERIFIED GEOMETRY AND EXACT CLOSE. NO CLASSIC PAGE IS OPENED.";
    return "";
}
function timestampMs(value) {
    if (!value || typeof value.getTime !== "function") return -1;
    var n=value.getTime();
    return isFinite(n) && n>0 ? n:-1;
}
function sampleAgeMinutes(value,nowMs) {
    var raw=String(value || "").trim();
    if (!raw) return -1;
    raw=raw.replace(" ","T");
    if (!/(Z|[+\-]\d{2}:?\d{2})$/i.test(raw)) raw+="Z";
    var t=Date.parse(raw),now=Number(nowMs);
    if (!isFinite(t)||t<=0||!isFinite(now)||now<=0||t>now+300000)
        return -1;
    return Math.max(0,Math.floor((now-t)/60000));
}
function sourceInput(weather,space,nowMs) {
    var w=weather || null, s=space || null;
    var now=Number(nowMs);
    return {
        nowMs: now,
        weather:{
            id:"weather",title:"WEATHER",provider:"WTTR.IN",
            ready:!!w&&!!w.ready,loading:!!w&&!!w.loading,
            error:w?String(w.errorText||""):"NO SERVICE",
            lastSuccessMs:timestampMs(w?w.lastUpdated:null),
            sampleAgeMinutes:-1,staleAfterMinutes:20
        },
        aqi:{
            id:"aqi",title:"AIR QUALITY",provider:"OPEN-METEO",
            ready:!!w&&!!w.aqiReady,loading:!!w&&!!w.aqiLoading,
            error:w?String(w.aqiErrorText||""):"NO SERVICE",
            lastSuccessMs:timestampMs(w?w.aqiLastUpdated:null),
            sampleAgeMinutes:-1,staleAfterMinutes:20
        },
        kp:{
            id:"kp",title:"KP INDEX",provider:"NOAA SWPC",
            ready:!!s&&!!s.kpReady,loading:!!s&&!!s.kpLoading,
            error:s?String(s.kpErrorText||""):"NO SERVICE",
            lastSuccessMs:timestampMs(s?s.kpLastUpdated:null),
            sampleAgeMinutes:s&&s.kpReady?sampleAgeMinutes(s.kpTime,now):-1,
            staleAfterMinutes:360
        },
        solarWind:{
            id:"solar-wind",title:"SOLAR WIND",provider:"NOAA SWPC",
            ready:!!s&&!!s.solarWindReady,loading:!!s&&!!s.solarWindLoading,
            error:s?String(s.solarWindErrorText||""):"NO SERVICE",
            lastSuccessMs:timestampMs(s?s.solarWindLastUpdated:null),
            sampleAgeMinutes:s&&s.solarWindReady?sampleAgeMinutes(s.solarWindTime,now):-1,
            staleAfterMinutes:45
        },
        magneticField:{
            id:"imf",title:"IMF",provider:"NOAA SWPC",
            ready:!!s&&!!s.magneticFieldReady,
            loading:!!s&&!!s.magneticFieldLoading,
            error:s?String(s.magneticFieldErrorText||""):"NO SERVICE",
            lastSuccessMs:timestampMs(s?s.magneticFieldLastUpdated:null),
            sampleAgeMinutes:s&&s.magneticFieldReady?sampleAgeMinutes(s.magneticFieldTime,now):-1,
            staleAfterMinutes:45
        },
        solarFlux:{
            id:"solar-flux",title:"F10.7 FLUX",provider:"NOAA SWPC",
            ready:!!s&&!!s.solarFluxReady,loading:!!s&&!!s.solarFluxLoading,
            error:s?String(s.solarFluxErrorText||""):"NO SERVICE",
            lastSuccessMs:timestampMs(s?s.solarFluxLastUpdated:null),
            sampleAgeMinutes:s&&s.solarFluxReady?sampleAgeMinutes(s.solarFluxTime,now):-1,
            staleAfterMinutes:2160
        }
    };
}
// M28-I: the original SPACE FIELD TIME values, not runtime catalogue specs.
// Read the SAME four existing NOAA SpaceService sample clocks and receipt dates.
// A fresh network receipt must never silently mean a fresh provider sample.
function fieldTimeRows(space,nowMs) {
    var s=space || null;
    var h=sourceInput(null,s,nowMs);
    var rows=[
        {id:"kp",title:"KP SAMPLE",value:s?s.kpTime:"",health:h.kp},
        {id:"solar-wind",title:"WIND SAMPLE",value:s?s.solarWindTime:"",health:h.solarWind},
        {id:"imf",title:"IMF SAMPLE",value:s?s.magneticFieldTime:"",health:h.magneticField},
        {id:"solar-flux",title:"FLUX SAMPLE",value:s?s.solarFluxTime:"",health:h.solarFlux}
    ];
    return rows.map(function(row) {
        var raw=String(row.value || "").trim();
        var info=row.health;
        var age=info.sampleAgeMinutes;
        var receipt=info.lastSuccessMs>0
            ? new Date(info.lastSuccessMs).toISOString() : "UNAVAILABLE";
        var status=!info.ready ? "NOT READY"
            : raw==="" ? "NO SAMPLE"
            : age<0 ? "TIME UNVERIFIED"
            : age>info.staleAfterMinutes ? "STALE" : "CURRENT";
        return {
            id:row.id, title:row.title,
            sampleClock:raw!=="" ? raw:"UNAVAILABLE",
            receiptClock:receipt,
            sampleAgeMinutes:age,
            status:status,
            ageText:age>=0 ? age+" MIN":"UNKNOWN",
            staleAfterMinutes:info.staleAfterMinutes
        };
    });
}

function countKeys(obj) {
    return obj && typeof obj === "object" && !Array.isArray(obj)
        ? Object.keys(obj).length:0;
}
function storeState(obj) {
    return obj?String(obj.storageState||"UNKNOWN").toUpperCase():"NOT CONNECTED";
}
function rev(obj) {
    var n=Number(obj&&obj.revision);
    return isFinite(n)&&n>=0?Math.floor(n):0;
}
function storageRows(cache,history,eventArchive,dossierArchive,nowMs) {
    var eventCount=-1;
    if (eventArchive && typeof eventArchive.eventCount==="function") {
        var count=Number(eventArchive.eventCount(nowMs));
        if (isFinite(count)&&count>=0) eventCount=Math.floor(count);
    }
    return [
        {id:"cache",title:"LAST-KNOWN CACHE",state:storeState(cache),
         revision:rev(cache),count:cache?countKeys(cache.document&&cache.document.records):-1,
         detail:"OPERATIONAL LAST-GOOD SOURCE RECORDS // NOT HISTORICAL OBSERVATIONS",
         error:cache?String(cache.errorCode||""):""},
        {id:"history",title:"LIVE HISTORY",state:storeState(history),
         revision:rev(history),count:history?countKeys(history.document&&history.document.series):-1,
         detail:"BOUNDED OBSERVATION SERIES // NOT FORECAST OR FRAME ARCHIVE",
         error:history?String(history.errorCode||""):""},
        {id:"events",title:"EVENT ARCHIVE",state:storeState(eventArchive),
         revision:rev(eventArchive),count:eventCount,
         detail:"PROVIDER-NATIVE EVENTS // OPERATOR-REQUESTED SNAPSHOTS",
         error:eventArchive?String(eventArchive.errorCode||""):""},
        {id:"dossiers",title:"DOSSIER ARCHIVE",state:storeState(dossierArchive),
         revision:rev(dossierArchive),count:-1,
         detail:"SEPARATE EXPLICIT DOSSIER CAPTURE // NO AUTOMATIC SAVE",
         error:dossierArchive?String(dossierArchive.errorCode||""):""}
    ];
}
function storageRowsFor(path,rows) {
    var array=Array.isArray(rows)?rows:[];
    if (path==="tools/overview") return array;
    if (path==="tools/storage/events")
        return array.filter(function(x){return x.id==="events"||x.id==="dossiers";});
    if (path==="tools/storage/cache")
        return array.filter(function(x){return x.id==="cache";});
    if (path==="tools/storage/history")
        return array.filter(function(x){return x.id==="history";});
    return [];
}
function frameSources(catalog) {
    return (Array.isArray(catalog)?catalog:[]).filter(function(x) {
        return x&&x.retention==="FRAME_CACHE";
    });
}
function locationLabel(weather) {
    if (!weather) return "NO WEATHER SERVICE ATTACHED";
    var la=String(weather.latitude||"").trim(),
        lo=String(weather.longitude||"").trim();
    if (!la||!lo) return "LOCATION NOT PRESENT IN CURRENT RESPONSE";
    var lat=Number(la),lon=Number(lo);
    if (!isFinite(lat)||!isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)
        return "LOCATION UNAVAILABLE";
    return lat.toFixed(3)+", "+lon.toFixed(3)+" // CURRENT PROVIDER LOCATION";
}
function timezoneLabel(weather) {
    if (!weather) return "NO WEATHER SERVICE ATTACHED";
    return String(weather.airQualityTimezone||"").trim()
        || "AIR QUALITY PROVIDER TIMEZONE NOT AVAILABLE";
}
