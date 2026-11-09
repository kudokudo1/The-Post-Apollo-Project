.pragma library

// E6 // Compact EARTH OVERVIEW summaries. Pure formatting over existing
// Weather, NWPS, NWS and USGS objects. No collectors, persistence or actions.
var TOPICS = [
    {id:"water",label:"WATER",route:"earth/water/rivers"},
    {id:"pollen",label:"AIR // POLLEN",route:"earth/ground/full"},
    {id:"environment",label:"ENVIRONMENT",route:"earth/ground/full"}
];

function wrap(index) {
    var n = TOPICS.length;
    if (!isFinite(Number(index))) return 0;
    return ((Math.floor(Number(index)) % n) + n) % n;
}
function topic(index) { return TOPICS[wrap(index)]; }
function finiteNumber(value) {
    if (value === null || value === undefined
            || (typeof value === "string" && value.trim() === "")) return null;
    var n = Number(value);
    return isFinite(n) ? n : null;
}
function reading(value, decimals, unit, allowNegative) {
    var n = finiteNumber(value);
    if (n === null || (!allowNegative && n < 0)) return "--";
    var result = n.toFixed(decimals);
    return result + (unit ? " " + String(unit) : "");
}
function entry(label, value, detail) {
    return {label:label,value:String(value),detail:String(detail || "")};
}
function clippedName(value) {
    var text = String(value || "").trim();
    return text ? text : "--";
}
function pollenPeak(weather) {
    if (!weather || weather.pollenAvailable !== true)
        return {name:"UNAVAILABLE",value:null};
    var fields = [
        ["ALDER",weather.alderPollen],["BIRCH",weather.birchPollen],
        ["GRASS",weather.grassPollen],["MUGWORT",weather.mugwortPollen],
        ["OLIVE",weather.olivePollen],["RAGWEED",weather.ragweedPollen]
    ];
    var best = {name:"UNAVAILABLE",value:null};
    for (var i=0;i<fields.length;i++) {
        var n = finiteNumber(fields[i][1]);
        if (n !== null && n >= 0 && (best.value === null || n > best.value))
            best = {name:fields[i][0],value:n};
    }
    return best;
}
function summarize(index,river,weather,nws,seismic,heat,fireProducts) {
    var t = topic(index);
    if (t.id === "water") {
        var usable = !!river && river.ready === true;
        var g = usable ? river.gauge : null;
        var pending = !river ? "SOURCE UNAVAILABLE"
            : !river.configured ? "LOCATION UNAVAILABLE"
            : river.failed ? "FEED ERROR // LAST GOOD MAY BE STALE"
            : river.loading ? "RECEIVING NWPS" : "AWAITING NWPS";
        var state = usable
            ? (river.usingPersistentCache ? "NWPS // CACHE" : "NWPS // OBSERVED")
            : pending;
        return {
            title:t.label,route:t.route,
            subtitle:"RIVERS // NEAREST NWPS GAUGE // MARINE + COAST IN WATER",
            cards:[
                entry("GAUGE",g ? clippedName(g.lid) : "--",
                      g ? clippedName(g.name) : state),
                entry("OBSERVED",g ? reading(g.observedPrimary,2,g.primaryUnits,true) : "--",
                      "NWPS // STAGE"),
                entry("FORECAST",g ? reading(g.forecastPrimary,2,g.primaryUnits,true) : "--",
                      "NWPS // STAGE"),
                entry("FLOOD STATUS",g && g.observedCategory
                      ? clippedName(g.observedCategory.label) : "--",
                      g && finiteNumber(g.distanceKm) !== null
                      ? reading(g.distanceKm,0,"KM FROM FIX",false)
                      : "NO EMERGENCY TARGETING")
            ],
            footer:state + " // GAUGE DATA IS NOT AN ALERT"
        };
    }
    if (t.id === "pollen") {
        var ready = !!weather && weather.aqiReady === true;
        var peak = pollenPeak(weather);
        var status = ready
            ? (weather.usingPersistentAqiCache ? "OPEN-METEO // CACHE"
               : "OPEN-METEO // AIR SAMPLE")
            : weather && weather.aqiLoading ? "RECEIVING AIR QUALITY"
            : "AIR QUALITY UNAVAILABLE";
        return {
            title:t.label,route:t.route,
            subtitle:"AIR QUALITY // PARTICULATES // POLLEN SPECIES",
            cards:[
                entry("US AQI",ready ? reading(weather.aqi,0,"",false) : "--",
                      ready ? clippedName(weather.aqiLabel) : status),
                entry("PM2.5",ready ? reading(weather.pm25,1,"µg/m³",false) : "--",
                      "PARTICULATES"),
                entry("PM10",ready ? reading(weather.pm10,1,"µg/m³",false) : "--",
                      "PARTICULATES"),
                entry("PEAK POLLEN",peak.value !== null
                      ? reading(peak.value,1,"gr/m³",false) : "--",
                      peak.name)
            ],
            footer:status + " // MODELLED LOCAL CONDITIONS"
        };
    }
    var configured = !!nws && nws.configured === true;
    var alertReady = configured && nws.ready === true;
    var alerts = alertReady && Array.isArray(nws.alertList)
        ? nws.alertList : [];
    var fires = alertReady && Array.isArray(fireProducts)
        ? fireProducts : [];
    var quakesReady = !!seismic && seismic.ready === true;
    var events = quakesReady && Array.isArray(seismic.events)
        ? seismic.events : [];
    var hot = heat && heat.available === true;
    var state = !configured ? "NWS ALERT POINT NOT CONFIGURED"
        : !alertReady ? "NWS ALERTS WAITING"
        : nws.usingPersistentCache ? "NWS // CACHE" : "NWS // OFFICIAL";
    return {
        title:t.label,route:t.route,
        subtitle:"NWS ALERTS + FIRE WEATHER // USGS SEISMIC // HEAT",
        cards:[
            entry("NWS ALERTS",alertReady ? String(alerts.length) : "--",
                  state),
            entry("FIRE PRODUCTS",alertReady ? String(fires.length) : "--",
                  "MATCHED NWS ALERTS"),
            entry("USGS QUAKES",quakesReady ? String(events.length) : "--",
                  quakesReady ? "PUBLISHED EVENTS" : "FEED UNAVAILABLE"),
            entry("HEAT INDEX",hot ? reading(heat.valueF,1,"°F",true) : "--",
                  hot && heat.band ? clippedName(heat.band.label)
                    : "TEMP / RH UNAVAILABLE")
        ],
        footer:"NWS PINNED POINT // USGS GLOBAL // HEAT INDEX IN SHADE"
    };
}
