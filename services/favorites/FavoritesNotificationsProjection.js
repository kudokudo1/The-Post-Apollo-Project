.pragma library
.import "FavoritesReadOnlyAdapters.js" as Adapters

// U5b: names of ALREADY-FAVORITED notification sources only. This file never
// examines notification history, message bodies, credentials, actions,
// DND/snooze policy, FileView or the owning singleton's writer.
var MAX_SOURCES=128;
function sourceKey(key) {
    if (typeof key!=="string") return "";
    const value=key.trim();
    if (!value || value.length>160 || value!==key
            || /[\u0000-\u001f\u007f\/\\|<>@]/.test(value)
            || /:\/\//.test(value))
        return "";
    return value;
}
function safeName(name) {
    if (typeof name!=="string") return "";
    const value=name.trim();
    if (value.length<2 || value.length>90
            || /[\u0000-\u001f\u007f\/\\|<>@]/.test(value)
            || /:\/\//.test(value)
            || /(?:password|access[\s_-]*token|secret[\s_-]*key)/i.test(value))
        return "";
    return value;
}
function fallbackName(key) {
    // An ordinary source key may itself be a recognizable app identifier.
    // Never decode website parent/site IDs or arbitrary URL-like identities.
    if (key.indexOf("website:")===0) return "WEBSITE SOURCE NAME UNAVAILABLE";
    if (!/^[a-zA-Z][a-zA-Z0-9 ._+()-]{0,80}$/.test(key))
        return "SOURCE NAME UNAVAILABLE";
    return safeName(key) || "SOURCE NAME UNAVAILABLE";
}
function build(snapshot) {
    if (snapshot===null || snapshot===undefined)
        return {rows:[],invalidCount:0,state:"disconnected"};
    if (!snapshot || typeof snapshot!=="object" || Array.isArray(snapshot))
        return {rows:[],invalidCount:1,state:"invalid"};

    // NotificationsService.favoritesReady becomes true after load attempts,
    // even if the persistence file failed. Status must agree too.
    const status=String(snapshot.status || "");
    if (snapshot.ready!==true
            || (status!=="ready" && status!=="saved"))
        return {rows:[],invalidCount:0,state:status || "loading"};

    const sourceRows=snapshot.sources;
    if (!Array.isArray(sourceRows) || sourceRows.length>MAX_SOURCES)
        return {rows:[],invalidCount:1,state:"invalid"};
    const clean=[],seen=Object.create(null);
    let rejected=0;
    for (const source of sourceRows) {
        if (!source || typeof source!=="object" || Array.isArray(source)) {
            rejected++;
            continue;
        }
        const key=sourceKey(source.appKey);
        if (!key || seen[key]) {rejected++;continue;}
        // sourceId is deliberately never read, copied, or used for display.
        const label=safeName(source.source) || fallbackName(key);
        seen[key]=true;
        clean.push({appKey:key,source:label});
    }
    const normalized=Adapters.notifications(clean);
    rejected+=normalized.invalidCount;
    const rows=[];
    for (const entry of normalized.items) {
        const saved=clean.find(function(item) {
            return item.appKey===entry.resourceId;
        });
        if (!saved) {rejected++;continue;}
        rows.push({
            key:entry.key,provider:"notifications",kind:"source",
            label:"NOTIFICATIONS // SOURCES // "+saved.source,
            sourceName:"NOTIFICATIONS",menu:"SOURCES",
            item:saved.source,favoriteType:"SOURCE FAVORITE",
            resolved:saved.source.indexOf("UNAVAILABLE")<0,
            category:"NOTIFS",owner:"notifications",
            readOnly:true,isFavorite:true,isPinned:false,
            available:"unresolved",capabilities:[]
        });
    }
    return {rows:rows,invalidCount:rejected,state:status};
}
