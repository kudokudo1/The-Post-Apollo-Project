.pragma library
.import "FavoritesResourcePolicy.js" as Resource
.import "FavoritesDefaultPolicy.js" as Default
.import "FavoritesCollectionsPolicy.js" as Collections
.import "FavoritesReadOnlyAdapters.js" as Adapters
.import "FavoritesWeatherHomeProjection.js" as WeatherHome
.import "FavoritesNotificationsProjection.js" as NotificationsProjection
.import "FavoritesRadioProjection.js" as RadioProjection
.import "FavoritesHospitalProjection.js" as HospitalProjection

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

// The AppControl owner may provide volatile display-only names keyed by the
// existing normalized resource key. No stored key is decoded into a label.
function approvedOwnerLabel(labels, key) {
    if (!labels || typeof labels !== "object"
            || !Object.prototype.hasOwnProperty.call(labels,key))
        return "";
    const value=labels[key];
    if (typeof value !== "string" || value.length>60
            || !/^[A-Za-z0-9][A-Za-z0-9 ._()+#&-]{0,59}$/.test(value))
        return "";
    const trimmed=value.trim();
    return trimmed.length>=2 ? trimmed : "";
}

// Only AppControl's source resolver may supply structured presentation facts.
// These are NOT executable references, liveness proofs or save permissions.
function approvedOwnerDescription(descriptions,key) {
    if (!descriptions || typeof descriptions!=="object"
            || !Object.prototype.hasOwnProperty.call(descriptions,key))
        return null;
    const value=descriptions[key];
    if (!value || typeof value!=="object") return null;
    if (["APPS","KILL","THERMAL","SYSTEM","RUN","WINDOWS","FILES"].indexOf(value.menu)<0
            || ["FAVORITE","PROCESS FAVORITE","PREFERRED ACTION",
                "METRIC WATCH","FILE FAVORITE","DIRECTORY FAVORITE",
                "SYMLINK FAVORITE"].indexOf(value.type)<0
            || typeof value.item!=="string") return null;
    const item=value.item.trim();
    if (value.menu==="FILES") {
        if (["FILE FAVORITE","DIRECTORY FAVORITE","SYMLINK FAVORITE",
             "FAVORITE"].indexOf(value.type)<0
                || !item || item.length>120 || item==="." || item===".."
                || /[\u0000-\u001f\u007f\u2028\u2029\/\\|<>]/.test(item)
                || /%(?:2f|5c|00|0a|0d)/i.test(item)
                || /^(?:file:|https?:|smb:|ssh:)/i.test(item))
            return null;
    } else if (!item || item.length>64
            || /[\u0000-\u001f\u007f\/\\|<>@]/.test(item)
            || /:\/\/|--(?:password|token|secret|key)/i.test(item))
        return null;
    return {menu:value.menu,item:item,type:value.type};
}
function appControlMenu(record) {
    const id=record.resourceId;
    if (record.kind==="task-watch" || id.indexOf("task|")===0)
        return "KILL";
    if (id.indexOf("thermal|")===0 || id.indexOf("watchbox|thermal|")===0)
        return "THERMAL";
    if (id.indexOf("system|")===0 || id.indexOf("watchbox|system|")===0)
        return "SYSTEM";
    if (id.indexOf("run:")===0 || id.indexOf("run|")===0)
        return "RUN";
    if (id.indexOf("hidden:")===0 || (record.kind==="preferred-action" && id.indexOf("app|")===0)
            || (record.kind==="item"
                && /^[A-Za-z][A-Za-z0-9 ._+()-]{0,95}$/.test(id)))
        return "APPS";
    const match=/^mode:([0-8]):/.exec(id);
    if (match) {
        const modes=["FAVORITES","APPS","FILES","RUN","WINDOWS",
                     "REMOTE","THERMAL","KILL","SYSTEM"];
        return modes[Number(match[1])];
    }
    return "OTHER";
}
function safeUnresolvedLabel(menu,classification,ordinal) {
    const type={
        "RUN":"SAVED COMMAND",
        "WINDOWS":"SAVED WINDOW",
        "FILES":"SAVED FILE",
        "REMOTE":"SAVED REMOTE ITEM",
        "APPS":"SAVED APPLICATION",
        "KILL":"SAVED PROCESS",
        "THERMAL":"SAVED SENSOR",
        "SYSTEM":"SAVED METRIC",
        "FAVORITES":"SAVED ITEM"
    };
    if (menu==="OTHER") return classification+" #"+ordinal;
    if (classification==="PREFERRED ACTION")
        return menu+" // PREFERRED ACTION #"+ordinal;
    if (classification.indexOf("METRIC WATCH")!==-1)
        return menu+" // METRIC WATCH #"+ordinal;
    return menu+" // "+(type[menu] || "SAVED ITEM")+" #"+ordinal;
}

function list(clockZones, savedPlaces, defaults, pins, appControlSnapshot, appControlDisplayLabels, appControlDescriptions, weatherHomeSnapshot, notificationsSnapshot, radioSnapshot, hospitalSnapshot) {
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
            const ordinalByType=Object.create(null);
            for(const entry of items.items) {
                const classification=appControlClassification(entry);
                const type=classification.label;
                const descriptor=approvedOwnerDescription(appControlDescriptions,entry.key);
                const menu=appControlMenu(entry);
                const group=menu==="OTHER" ? type : menu+"|"+type;
                ordinalByType[group]=(ordinalByType[group] || 0)+1;
                const fallback=approvedOwnerLabel(appControlDisplayLabels,entry.key)
                    || safeUnresolvedLabel(menu,type,ordinalByType[group]);
                accept({
                    key:entry.key,
                    provider:"appcontrol",kind:entry.kind,
                    // Identity stays private within the in-memory key. It is
                    // never printed or forwarded to a generic action/collection.
                    label:descriptor ? descriptor.menu+" // "+descriptor.item : fallback,
                    sourceName:"APP CONTROL",
                    menu:descriptor ? descriptor.menu : menu,
                    item:descriptor ? descriptor.item : "NAME UNAVAILABLE",
                    favoriteType:descriptor ? descriptor.type : type,
                    resolved:!!descriptor,
                    category:classification.category,
                    owner:"appcontrol",readOnly:true,
                    isFavorite:true,isPinned:false,
                    available:"unresolved",capabilities:[]
                });
            }
        }
    }

    // No duplicate Weather store. A read-only source snapshot is injected by
    // its owner after its single writer has loaded successfully.
    const weather=WeatherHome.build(weatherHomeSnapshot);
    rejected+=weather.invalidCount;
    for(const item of weather.rows) accept(item);

    // Notifications singleton already owns favorites. Only saved source
    // metadata enters this read-only projection, never message/history data.
    const notifications=NotificationsProjection.build(notificationsSnapshot);
    rejected+=notifications.invalidCount;
    for(const item of notifications.rows) accept(item);

    // Original Weather Station RADIO memory is optional and read-only here.
    // Never construct an extra FileView or delegate recall/playback to CPU++.
    const radio=RadioProjection.build(radioSnapshot);
    rejected+=radio.invalidCount;
    for(const item of radio.rows) accept(item);

    // Hospital Reception owns the only durable activity pins/archive.
    // Its public snapshot contains sanitized metadata, no private key/title.
    const hospital=HospitalProjection.build(hospitalSnapshot);
    rejected+=hospital.invalidCount;
    for(const item of hospital.rows) accept(item);

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
            // ANGEL is an opt-in new provider in the shared default store.
            // Its exact 1–8 digits are safe to present; other provider IDs
            // remain opaque. Keep category NEW so the existing default-store
            // remove/pin controls retain the correct owner and permissions.
            const angel=valid.provider==="angel" && valid.kind==="number"
                && /^[0-9]{1,8}$/.test(id);
            add(valid.provider,valid.kind,id,
                angel ? "ANGEL // "+id
                    : valid.provider.toUpperCase()+" // "+valid.kind.toUpperCase(),
                "NEW",isFavorite,!isFavorite);
        }
    }
    return {rows:out,total:total,shown:out.length,rejected:rejected};
}

function filterRows(records,category) {
    const rows=records && Array.isArray(records.rows)?records.rows:[];
    if(["CLOCK","PLACES","NEW","CPU++","APP CTRL","WEATHER","NOTIFS","RADIO","HOSPITAL"].indexOf(category)<0)
        return rows;
    return rows.filter(item=>item.category===category);
}

function recordFor(records,key) {
    const rows=records && Array.isArray(records.rows)?records.rows:[];
    return rows.find(x=>x.key===key) || rows[0] || null;
}
