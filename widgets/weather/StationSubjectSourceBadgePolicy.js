.pragma library

// M28-L: the station header remains the sole badge owner. This policy is
// deliberately pure: it reads live root Weather/Space runtime snapshots and
// the *loaded original* EARTH/WEATHER map runtime summary. No new provider.
// Official NWS alert precedence is handled by WeatherStationW before this.
function familyForPath(path,indexOpen) {
    if (indexOpen) return "index";
    if (typeof path !== "string") return "";
    var key=path.split("/")[0];
    return ["home","weather","cosmos","earth","media","magick","tools"]
        .indexOf(key)>=0 ? key:"";
}
function availability(state) {
    return state && typeof state.availability === "string"
        ? state.availability:"WAITING";
}
function stateToken(state) {
    var a=availability(state);
    if (a==="LIVE") return "LIVE";
    if (a==="LIVE_AGING") return "AGING";
    if (a==="LIVE_STALE") return "STALE";
    if (a==="EXPIRED") return "EXPIRED";
    if (a==="OFFLINE") return "OFFLINE";
    if (a==="READING") return "READING";
    if (a==="INACTIVE") return "INACTIVE";
    if (a==="WAITING") return "WAITING";
    if (a.indexOf("CACHE_")===0) return a.replace("_"," ");
    return "WAITING";
}
function runtimeTone(state) {
    var a=availability(state);
    if (a==="LIVE") return "magenta";
    if (a==="LIVE_AGING"||a==="LIVE_STALE") return "yellow";
    if (a==="EXPIRED"||a==="OFFLINE"||a==="CACHE_EXPIRED") return "red";
    if (a.indexOf("CACHE_")===0) return "blue";
    if (a==="READING"||a==="WAITING") return "orange";
    return "cyan";
}
function rowSummary(summary) {
    var s=summary||{};
    function count(field) {
        var n=Number(s[field]);
        return isFinite(n)&&n>0?Math.floor(n):0;
    }
    var ready=count("ready"), expired=count("expired"),
        loading=count("loading"), problem=count("problem"),
        offline=count("offline"), cached=count("cached"),
        stale=count("stale");
    if (expired>0 && expired>=ready)
        return {label:"EXPIRED",tone:"red"};
    if ((problem>0||offline>0)&&ready===0)
        return {label:"OFFLINE",tone:"red"};
    if (loading>0&&ready===0)
        return {label:"READING",tone:"orange"};
    if (cached>0) return {label:"CACHE",tone:"blue"};
    if (stale>0) return {label:"STALE",tone:"yellow"};
    if (ready>0) return {label:ready+" READY",tone:"magenta"};
    return {label:"WAITING",tone:"orange"};
}
function homeBadge(weather,space) {
    var w=availability(weather),s=availability(space);
    var wUp=w==="LIVE"||w==="LIVE_AGING"||w==="LIVE_STALE"
        ||w==="CACHE_FRESH"||w==="CACHE_AGING"||w==="CACHE_STALE";
    var sUp=s==="LIVE"||s==="LIVE_AGING"||s==="LIVE_STALE"
        ||s==="CACHE_FRESH"||s==="CACHE_AGING"||s==="CACHE_STALE";
    if (wUp&&sUp) {
        if (w.indexOf("CACHE_")===0||s.indexOf("CACHE_")===0)
            return {text:"HOME // CACHE",tone:"blue"};
        if (w==="LIVE_STALE"||s==="LIVE_STALE")
            return {text:"HOME // STALE",tone:"yellow"};
        if (w==="LIVE_AGING"||s==="LIVE_AGING")
            return {text:"HOME // AGING",tone:"yellow"};
        return {text:"HOME // 2 LIVE",tone:"magenta"};
    }
    if (wUp||sUp) return {text:"HOME // PARTIAL",tone:"yellow"};
    if (w==="READING"||s==="READING")
        return {text:"HOME // READING",tone:"orange"};
    if (w==="OFFLINE"||s==="OFFLINE"||w==="EXPIRED"||s==="EXPIRED")
        return {text:"HOME // OFFLINE",tone:"red"};
    return {text:"HOME // WAITING",tone:"orange"};
}
function badgeFor(path,indexOpen,weather,space,mapSummary) {
    var family=familyForPath(path,indexOpen);
    if (family==="index") return {text:"INDEX // PREVIEW",tone:"cyan"};
    if (family==="home") return homeBadge(weather,space);
    if (family==="weather") {
        // A map is a distinct view-scoped provider rack. Never treat a radar
        // render as the shared 15-minute weather reading.
        if (path.indexOf("weather/maps")===0) {
            var w=rowSummary(mapSummary);
            return {text:"WEATHER // "+w.label,tone:w.tone};
        }
        return {text:"WEATHER // "+stateToken(weather),tone:runtimeTone(weather)};
    }
    if (family==="cosmos")
        return {text:"COSMOS // "+stateToken(space),tone:runtimeTone(space)};
    if (family==="earth") {
        var e=rowSummary(mapSummary);
        return {text:"EARTH // "+e.label,tone:e.tone};
    }
    if (family==="media") return {text:"MEDIA // CATALOG",tone:"cyan"};
    if (family==="magick") return {text:"MAGICK // REFERENCE",tone:"cyan"};
    if (family==="tools") return {text:"TOOLS // SOURCES",tone:"cyan"};
    return {text:"SOURCES // UNKNOWN",tone:"orange"};
}
