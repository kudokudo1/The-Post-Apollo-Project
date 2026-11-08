.pragma library
.import "FavoritesResourcePolicy.js" as Resource
.import "FavoritesDefaultPolicy.js" as Default
.import "FavoritesCollectionsPolicy.js" as Collections

// CPU++ V0: bounded, SAFE, local selection for management UI.
// AppControl raw path/command identities NEVER enter this candidate list.
// Owner stores and validation remain authoritative for actual edits.
var MAX_ROWS=80;
function list(clockZones, savedPlaces, defaults, pins) {
    const out=[], seen=Object.create(null);
    let rejected=0, total=0;
    function add(provider,kind,id,label,category,isFavorite,isPinned) {
        const normalized=Resource.normalize({
            provider:provider,kind:kind,resourceId:id,
            label:label,capabilities:["favorite","pin","collection"]
        });
        if (!normalized.ok || !Collections.checkMemberKey(normalized.record.key).ok) {
            rejected++;
            return;
        }
        const key=normalized.record.key;
        if (seen[key]) {
            const record=seen[key];
            record.isFavorite=record.isFavorite || isFavorite;
            record.isPinned=record.isPinned || isPinned;
            return;
        }
        total++;
        const record={
            key:key,provider:provider,kind:kind,resourceId:id,
            label:label,category:category,isFavorite:!!isFavorite,
            isPinned:!!isPinned,available:"unresolved",
            capabilities:["collection"]
        };
        seen[key]=record;
        if(out.length<MAX_ROWS)
            out.push(record);
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
            // Do not print arbitrary new-widget identity data. Provider/kind
            // are validated namespaces; original resourceId stays private.
            add(valid.provider,valid.kind,id,
                valid.provider.toUpperCase()+" // "+valid.kind.toUpperCase(),
                "NEW",isFavorite,!isFavorite);
        }
    }
    return {rows:out,total:total,shown:out.length,rejected:rejected};
}

function filterRows(records,category) {
    const list=records && Array.isArray(records.rows)?records.rows:[];
    if(category!=="CLOCK" && category!=="PLACES" && category!=="NEW")
        return list;
    return list.filter(item=>item.category===category);
}

function recordFor(records,key) {
    const rows=records && Array.isArray(records.rows)?records.rows:[];
    return rows.find(x=>x.key===key) || rows[0] || null;
}
