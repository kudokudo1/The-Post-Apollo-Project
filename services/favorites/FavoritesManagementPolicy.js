.pragma library
.import "FavoritesResourcePolicy.js" as Resource
.import "FavoritesDefaultPolicy.js" as Default
.import "FavoritesCollectionsPolicy.js" as Collections
.import "FavoritesReadOnlyAdapters.js" as Adapters

// CPU++ candidate projection. The original AppControl store remains the ONLY
// owner of its four favorite/watch lists. This view never executes, writes or
// converts those keys into general collection/launch permissions.
var MAX_ROWS=200;
var MAX_APP_PER_FAMILY=512;
var APP_FAMILIES=[
    "favoriteKeys","favoriteDetailActionKeys",
    "favoriteMonitorBoxKeys","favoriteTaskMetricKeys"
];

function appControlClassification(record) {
    // Explicit donor key families from AppControlW.favoriteKeyFor and the
    // watch helpers, never the display name or an arbitrary command substring.
    const id=record.resourceId;
    if(record.kind==="task-watch")
        return {category:"CPU++",label:"PROCESS METRIC WATCH"};
    if(record.kind==="monitor-watch")
        return {category:"CPU++",label:
            id.indexOf("watchbox|thermal|")===0 ? "THERMAL METRIC WATCH"
            : id.indexOf("watchbox|system|")===0 ? "SYSTEM METRIC WATCH"
            : "MONITOR WATCH"};
    if(record.kind==="item") {
        if(id.indexOf("task|")===0)
            return {category:"CPU++",label:"PROCESS FAVORITE"};
        if(id.indexOf("thermal|")===0)
            return {category:"CPU++",label:"THERMAL FAVORITE"};
        if(id.indexOf("system|")===0)
            return {category:"CPU++",label:"SYSTEM FAVORITE"};
    }
    if(record.kind==="preferred-action")
        return {category:"APP CTRL",label:"PREFERRED ACTION"};
    return {category:"APP CTRL",label:"APP CONTROL FAVORITE"};
}

function list(clockZones, savedPlaces, defaults, pins, appControlSnapshot) {
    const out=[], seen=Object.create(null);
    let rejected=0,total=0;
    function accept(record) {
        if(seen[record.key]) {
            const existing=seen[record.key];
            existing.isFavorite=existing.isFavorite || record.isFavorite;
            existing.isPinned=existing.isPinned || record.isPinned;
            return;
        }
        seen[record.key]=record;
        total++;
        if(out.length<MAX_ROWS) out.push(record);
    }
    function add(provider,kind,id,label,category,isFavorite,isPinned) {
        const normalized=Resource.normalize({
            provider:provider,kind:kind,resourceId:id,
            label:label,capabilities:["favorite","pin","collection"]
        });
        if (!normalized.ok || !Collections.checkMemberKey(normalized.record.key).ok) {
            rejected++;
            return;
        }
        accept({
            key:normalized.record.key,
            provider:provider,kind:kind,resourceId:id,
            label:label,category:category,
            owner:provider,readOnly:false,
            isFavorite:!!isFavorite,isPinned:!!isPinned,
            available:"unresolved",capabilities:["collection"]
        });
    }

    // Read-only AppControl projection: uses the existing U0 adapter contract.
    // IDs remain in memory only for stable VIEW selection, never rendered,
    // persisted, passed to Collections, or used to launch/kill any process.
    if(appControlSnapshot!==undefined && appControlSnapshot!==null) {
        let valid=true;
        const bounded={};
        for (const field of APP_FAMILIES) {
            const input=appControlSnapshot[field];
            if(!Array.isArray(input)) {
                valid=false;
                rejected++;
                bounded[field]=[];
                continue;
            }
            bounded[field]=input.slice(0,MAX_APP_PER_FAMILY);
            rejected+=Math.max(0,input.length-MAX_APP_PER_FAMILY);
        }
        if(valid) {
            const items=Adapters.appControl(bounded);
            rejected+=items.invalidCount;
            for(const entry of items.items) {
                const classification=appControlClassification(entry);
                accept({
                    key:entry.key,
                    provider:"appcontrol",kind:entry.kind,
                    // The raw donor identity is intentionally NOT exported
                    // to the CPU++ management record or collection controls.
                    label:classification.label,
                    category:classification.category,
                    owner:"appcontrol",readOnly:true,
                    isFavorite:true,isPinned:false,
                    available:"unresolved",capabilities:[]
                });
            }
        }
    }

    const zones=Array.isArray(clockZones)?clockZones:[];
    for (const zone of zones.slice(0,9)) {
        if(typeof zone!=="string") {rejected++;continue;}
        add("time","timezone",zone,zone,"CLOCK",true,false);
    }
    const places=Array.isArray(savedPlaces)?savedPlaces:[];
    for(const entry of places.slice(0,34)) {
        if(!entry || !Number.isSafeInteger(entry.id)
                || entry.id<1 || !entry.place
                || typeof entry.place.label!=="string") {
            rejected++;
            continue;
        }
        add("places","saved-place",String(entry.id),
            entry.place.label,"PLACES",true,false);
    }
    for(const [array,isFavorite] of [[defaults,true],[pins,false]]) {
        if(!Array.isArray(array)) {rejected++;continue;}
        for(const key of array.slice(0,Default.MAX_FAVORITES)) {
            const valid=Default.checkKey(key);
            if(!valid.ok || !Collections.checkMemberKey(key).ok) {
                rejected++;
                continue;
            }
            const match=/^fav1:local:([^:]+):([^:]+):(.+)$/.exec(key);
            if(!match) {rejected++;continue;}
            const id=decodeURIComponent(match[3]);
            // New-provider resource IDs are also never printed. The label
            // conveys provider and kind only, not source commands/secrets.
            add(valid.provider,valid.kind,id,
                valid.provider.toUpperCase()+" // "+valid.kind.toUpperCase(),
                "NEW",isFavorite,!isFavorite);
        }
    }
    return {rows:out,total:total,shown:out.length,rejected:rejected};
}

function filterRows(records,category) {
    const rows=records && Array.isArray(records.rows)?records.rows:[];
    if(["CLOCK","PLACES","NEW","CPU++","APP CTRL"].indexOf(category)<0)
        return rows;
    return rows.filter(item=>item.category===category);
}

function recordFor(records,key) {
    const rows=records && Array.isArray(records.rows)?records.rows:[];
    return rows.find(x=>x.key===key) || rows[0] || null;
}
