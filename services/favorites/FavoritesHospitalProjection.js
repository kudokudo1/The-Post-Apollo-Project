.pragma library
.import "FavoritesReadOnlyAdapters.js" as Adapters

// U5d: Hospital Reception alone owns the durable activity pin/archive.
 // Caller MUST provide only the owner's sanitized, metadata-derived refs.
 // This projection never reads private activity keys, report title/body,
 // transcript, channel, room/worker context, or owner action callbacks.
var MAX_PINNED=5;
var SOURCES=["rounds","staff","reports","phone","intercom","activity"];
var KINDS=["room","staff","report","phone","intercom","activity"];
var UTC=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
function validAt(value) {
    return value==="" || (typeof value==="string" && UTC.test(value)
                          && !Number.isNaN(Date.parse(value)));
}
function build(snapshot) {
    if (snapshot===null || snapshot===undefined)
        return {rows:[],invalidCount:0,state:"disconnected"};
    if (!snapshot || typeof snapshot!=="object" || Array.isArray(snapshot))
        return {rows:[],invalidCount:1,state:"invalid"};
    // The original owner sets 'hydrated' even on FileView failure. Do not
    // upgrade that state into verified durable success or availability.
    if(snapshot.state!=="hydrated")
        return {rows:[],invalidCount:0,state:String(snapshot.state||"loading")};
    const pins=snapshot.pins;
    if (!Array.isArray(pins) || pins.length>MAX_PINNED)
        return {rows:[],invalidCount:1,state:"invalid"};
    const refs=[],data=Object.create(null);
    for(const pin of pins) {
        if (!pin || typeof pin!=="object" || Array.isArray(pin))
            return {rows:[],invalidCount:1,state:"invalid"};
        const source=pin.source,kind=pin.kind,at=pin.recordedAt,ref=pin.ref;
        if(SOURCES.indexOf(source)<0 || KINDS.indexOf(kind)<0
                || !validAt(at) || typeof ref!=="string")
            return {rows:[],invalidCount:1,state:"invalid"};
        const base="pinned|"+source+"|"+kind+"|"+(at||"undated")+"|";
        if(ref.indexOf(base)!==0 || !/^[1-5]$/.test(ref.slice(base.length))
                || data[ref])
            return {rows:[],invalidCount:1,state:"invalid"};
        data[ref]={source:source,kind:kind,at:at};
        refs.push(ref);
    }
    // Existing U0 adapter constructs source-scoped normalized identities;
    // the refs it sees contain only category, type, UTC and duplicate slot.
    const adapted=Adapters.hospital(refs);
    if(adapted.invalidCount || adapted.items.length!==refs.length)
        return {rows:[],invalidCount:adapted.invalidCount||1,state:"invalid"};
    const rows=[];
    for(const entry of adapted.items) {
        const meta=data[entry.resourceId];
        if(!meta)return {rows:[],invalidCount:1,state:"invalid"};
        const menu=meta.source.toUpperCase();
        const type=meta.kind.toUpperCase();
        const when=meta.at
            ? meta.at.slice(0,10)+" "+meta.at.slice(11,19)+" UTC"
            : "DATE UNAVAILABLE";
        const item=type+" // "+when;
        rows.push({
            key:entry.key,provider:"hospital",kind:"activity",
            label:"HOSPITAL // "+menu+" // "+item,
            sourceName:"HOSPITAL RECEPTION",menu:menu,item:item,
            favoriteType:"PINNED ACTIVITY",
            resolved:true,category:"HOSPITAL",owner:"hospital",
            readOnly:true,isFavorite:true,isPinned:true,
            available:"unresolved",capabilities:[]
        });
    }
    return {rows:rows,invalidCount:0,state:"hydrated"};
}
