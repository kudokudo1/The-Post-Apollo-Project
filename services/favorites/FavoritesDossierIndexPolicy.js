.pragma library

// CPU++ presentation-only dossier derived from the SAME normalized candidate
// records used by the middle selector. Never parse raw favorite keys, scan a
// provider, infer availability, or copy owner action references.
var MAX_ROWS=200;
var ORDER=[
    "APP CTRL|APPS","APP CTRL|FILES","APP CTRL|RUN",
    "APP CTRL|WINDOWS","APP CTRL|REMOTE","APP CTRL|FAVORITES",
    "CPU++|KILL","CPU++|THERMAL","CPU++|SYSTEM",
    "WEATHER|HOME","WEATHER|CARD",
    "NOTIFS|SOURCES",
    "RADIO|FAVORITES","RADIO|RECENTS",
    "HOSPITAL|ROUNDS","HOSPITAL|STAFF","HOSPITAL|REPORTS",
    "HOSPITAL|PHONE","HOSPITAL|INTERCOM","HOSPITAL|ACTIVITY",
    "CLOCK|CLOCK","PLACES|PLACES","NEW|NEW"
];
function itemLabel(row,menu) {
    if (row.owner==="weather-home" || row.owner==="notifications"
            || row.owner==="radio" || row.owner==="hospital")
        return String(row.item || "NAME UNAVAILABLE");
    if (row.owner!=="appcontrol")
        return String(row.label || "NAME UNAVAILABLE");
    if (row.resolved && typeof row.item==="string" && row.item)
        return row.item;
    const fallback=String(row.label || "NAME UNAVAILABLE");
    const prefix=menu+" // ";
    return fallback.indexOf(prefix)===0
        ? fallback.slice(prefix.length) : fallback;
}
function build(candidates) {
    const source=candidates && Array.isArray(candidates.rows)
        ? candidates.rows.slice(0,MAX_ROWS) : [];
    const groups=[],byKey=Object.create(null),seen=Object.create(null);
    for (const row of source) {
        if (!row || typeof row.key!=="string" || !row.key
                || seen[row.key]) continue;
        const category=String(row.category || "");
        if (["APP CTRL","CPU++","WEATHER","NOTIFS","RADIO","HOSPITAL","CLOCK","PLACES","NEW"].indexOf(category)<0)
            continue;
        const menu=row.owner==="appcontrol" || row.owner==="weather-home"
            || row.owner==="notifications" || row.owner==="radio"
            || row.owner==="hospital"
            ? String(row.menu || "OTHER") : category;
        const key=category+"|"+menu;
        if (!byKey[key]) {
            const group={
                key:key,category:category,menu:menu,
                title:(category==="NOTIFS" ? "NOTIFICATIONS" : category)+" // "+menu,
                count:0,unresolved:0,items:[]
            };
            byKey[key]=group;
            groups.push(group);
        }
        const group=byKey[key];
        seen[row.key]=true;
        group.count++;
        if (row.owner==="appcontrol" && !row.resolved)
            group.unresolved++;
        group.items.push({
            key:row.key,category:category,menu:menu,
            name:itemLabel(row,menu),
            type:String(row.favoriteType || row.kind || "SAVED"),
            readOnly:!!row.readOnly,
            selected:false
        });
    }
    groups.sort(function(a,b){
        const ai=ORDER.indexOf(a.key),bi=ORDER.indexOf(b.key);
        const ar=ai>=0?ai:ORDER.length,br=bi>=0?bi:ORDER.length;
        if(ar!==br)return ar-br;
        return a.title.localeCompare(b.title);
    });
    const total=groups.reduce(function(n,g){return n+g.count;},0);
    return {groups:groups,total:total,groupCount:groups.length};
}
