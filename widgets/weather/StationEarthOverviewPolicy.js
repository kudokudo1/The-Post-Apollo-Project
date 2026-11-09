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
// E7 // Tiny source-backed graphics only. No history is invented.
// Meters use explicit display-domain ratios; event/heat/flood marks are
// categorical counts, not false claims about sampling frequency.
function clamp01(v) {
    var n=finiteNumber(v);
    return n===null ? null : Math.max(0,Math.min(1,n));
}
function relative(value,maximum) {
    var v=finiteNumber(value), max=finiteNumber(maximum);
    if(v===null || max===null || max<0) return null;
    return max===0 ? 0 : clamp01(Math.abs(v)/max);
}
function pairedStage(g) {
    if(!g) return [];
    var o=finiteNumber(g.observedPrimary), f=finiteNumber(g.forecastPrimary);
    if(o===null && f===null) return [];
    var max=Math.max(Math.abs(o===null?0:o),Math.abs(f===null?0:f));
    return [relative(o,max),relative(f,max)];
}
function countMarks(number,slots) {
    var n=finiteNumber(number);
    if(n===null || n<0) return [];
    var result=[];
    for(var i=0;i<slots;i++) result.push(i<Math.floor(n) ? 1 : 0);
    return result;
}
function segmentRank(rank,max) {
    var n=finiteNumber(rank);
    return n===null || n<0 ? [] : countMarks(Math.min(n,max),max);
}
function chart(type,caption,values) {
    return {type:type,caption:caption,values:values};
}
// Genuine short-range AQI series from Open-Meteo's existing hourly forecast.
// A single observation is not a time-series and must not be drawn as one.
function forecastBars(weather) {
    var rows=weather && Array.isArray(weather.airQualityForecast)
        ?weather.airQualityForecast:[];
    var observations=[];
    for(var i=0;i<rows.length && observations.length<6;i++) {
        var n=finiteNumber(rows[i] ? rows[i].aqi : null);
        if(n!==null && n>=0) observations.push(n);
    }
    if(observations.length<2) return [];
    var max=0;
    for(var j=0;j<observations.length;j++)
        max=Math.max(max,observations[j]);
    return observations.map(function(value){return relative(value,max);});
}
function microcharts(index,river,weather,nws,seismic,heat,fireProducts) {
    var t=topic(index);
    if(t.id==="water") {
        var gauge=river && river.ready===true ? river.gauge : null;
        var stage=pairedStage(gauge);
        var observed=gauge?finiteNumber(gauge.observedPrimary):null;
        var forecast=gauge?finiteNumber(gauge.forecastPrimary):null;
        var peak=Math.max(Math.abs(observed===null?0:observed),
                          Math.abs(forecast===null?0:forecast));
        var category=gauge&&gauge.observedCategory
            ? gauge.observedCategory.rank : null;
        return [
            chart("bars","OBS / FCST",stage),
            chart("meter","RELATIVE",observed===null?[]:[relative(observed,peak)]),
            chart("meter","RELATIVE",forecast===null?[]:[relative(forecast,peak)]),
            chart("marks","NWPS CLASS",segmentRank(category,4))
        ];
    }
    if(t.id==="pollen") {
        var ready=weather && weather.aqiReady===true;
        var aqi=ready?finiteNumber(weather.aqi):null;
        var pm25=ready?finiteNumber(weather.pm25):null;
        var pm10=ready?finiteNumber(weather.pm10):null;
        var maximum=Math.max(pm25===null?0:pm25,pm10===null?0:pm10);
        var bands=[50,100,150,200,300,500], bandCount=0;
        if(aqi!==null && aqi>=0) {
            bandCount=1;
            while(bandCount<bands.length && aqi>bands[bandCount-1])
                bandCount++;
        }
        var species=weather && weather.pollenAvailable===true
            ? [weather.alderPollen,weather.birchPollen,weather.grassPollen,
               weather.mugwortPollen,weather.olivePollen,weather.ragweedPollen]
            : [];
        var pollenMax=0,hasPollen=false;
        for(var j=0;j<species.length;j++) {
            var point=finiteNumber(species[j]);
            if(point!==null && point>=0) {
                pollenMax=Math.max(pollenMax,point);
                hasPollen=true;
            }
        }
        var pollenBars=[];
        if(hasPollen) for(var k=0;k<species.length;k++) {
            var value=finiteNumber(species[k]);
            pollenBars.push(value===null || value<0 ? null
                : relative(value,pollenMax));
        }
        var nextAqi=ready ? forecastBars(weather) : [];
        return [
            nextAqi.length>1
                ? chart("bars","AQI / 6H",nextAqi)
                : chart("marks","AQI BAND",aqi===null || aqi<0?[]
                      :countMarks(bandCount,6)),
            chart("meter","VS PM PEAK",pm25===null || pm25<0?[]
                  :[relative(pm25,maximum)]),
            chart("meter","VS PM PEAK",pm10===null || pm10<0?[]
                  :[relative(pm10,maximum)]),
            chart("bars","6 SPECIES",pollenBars)
        ];
    }
    var nwsReady=!!nws && nws.configured===true && nws.ready===true;
    var earthquakeReady=!!seismic && seismic.ready===true;
    var alerts=nwsReady && Array.isArray(nws.alertList)?nws.alertList:null;
    var fires=nwsReady && Array.isArray(fireProducts)?fireProducts:null;
    var events=earthquakeReady && Array.isArray(seismic.events)
        ?seismic.events:null;
    var ranks={"below":0,"caution":1,"extreme-caution":2,
               "danger":3,"extreme-danger":4};
    var band=heat && heat.available===true && heat.band
        ?String(heat.band.id||""):"";
    return [
        chart("marks","5+ ALERTS",alerts?countMarks(alerts.length,5):[]),
        chart("marks","5+ PRODUCTS",fires?countMarks(fires.length,5):[]),
        chart("marks","5+ EVENTS",events?countMarks(events.length,5):[]),
        chart("marks","HEAT BAND",Object.prototype.hasOwnProperty.call(ranks,band)
              ?countMarks(ranks[band],4):[])
    ];
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
