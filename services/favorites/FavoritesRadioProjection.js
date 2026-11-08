.pragma library
.import "FavoritesReadOnlyAdapters.js" as Adapters

// U5c is an optional, presentation-only view of Weather Station RADIO's
// ALREADY-DECODED memory lists. The owner remains StationRadio.qml's single
// FileView / weather-radio-memory.json writer and Hi-Fi/MPD transport.
// Never accept URLs, stream hosts, media metadata or callable references.
var MAX_FAVORITES=10;
var MAX_RECENTS=8;
var ID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function safeTitle(raw) {
    if (typeof raw!=="string" || !raw || raw.length>100
            || raw!==raw.trim()
            || /[\u0000-\u001f\u007f\u2028\u2029]/.test(raw)
            || /(?:https?:\/\/|file:\/\/|rtsp:\/\/|www\.|\/home\/|\/var\/|bearer\s|password|secret|token)/i.test(raw))
        return "";
    return raw;
}
function sanitizeRows(input,max) {
    if (!Array.isArray(input) || input.length>max) return null;
    const out=[],seen=Object.create(null);
    for (const source of input) {
        if (!source || typeof source!=="object" || Array.isArray(source)
                || !source.ref || typeof source.ref!=="object"
                || source.ref.source!=="radio-browser"
                || source.ref.kind!=="station") return null;
        const uuid=source.ref.id;
        const title=safeTitle(source.title);
        if (typeof uuid!=="string" || !ID.test(uuid) || !title
                || seen[uuid]) return null;
        seen[uuid]=true;
        out.push({ref:{source:"radio-browser",kind:"station",id:uuid},
                  title:title});
    }
    return out;
}
function build(snapshot) {
    if (snapshot===null || snapshot===undefined)
        return {rows:[],invalidCount:0,state:"disconnected"};
    if (!snapshot || typeof snapshot!=="object" || Array.isArray(snapshot))
        return {rows:[],invalidCount:1,state:"invalid"};
    const state=String(snapshot.state || "loading");
    // FileView data must be explicitly declared loaded by its existing owner.
    if (state!=="ready" && state!=="empty")
        return {rows:[],invalidCount:0,state:state};
    const favorites=sanitizeRows(snapshot.favorites,MAX_FAVORITES);
    const recents=sanitizeRows(snapshot.recents,MAX_RECENTS);
    if (!favorites || !recents)
        return {rows:[],invalidCount:1,state:"invalid"};

    // Reuse U0 Radio Browser UUID adapter. It deduplicates stations that
    // appear in both lists, preserving favorite and recent membership.
    const adapted=Adapters.radio(favorites,recents);
    if (adapted.invalidCount)
        return {rows:[],invalidCount:adapted.invalidCount,state:"invalid"};
    const favoriteIDs=Object.create(null),recentIDs=Object.create(null);
    for (const entry of favorites) favoriteIDs[entry.ref.id]=true;
    for (const entry of recents) recentIDs[entry.ref.id]=true;
    const rows=[];
    for (const record of adapted.items) {
        const fav=!!favoriteIDs[record.resourceId];
        const recent=!!recentIDs[record.resourceId];
        const title=safeTitle(record.label);
        if (!title || (!fav && !recent))
            return {rows:[],invalidCount:1,state:"invalid"};
        const menu=fav?"FAVORITES":"RECENTS";
        const type=fav && recent?"FAVORITE + RECENT STATION"
            : fav?"FAVORITE STATION":"RECENT STATION";
        rows.push({
            key:record.key,provider:"radio",kind:"station",
            label:"RADIO // "+menu+" // "+title,
            sourceName:"WEATHER STATION RADIO",menu:menu,item:title,
            favoriteType:type,resolved:true,category:"RADIO",owner:"radio",
            readOnly:true,isFavorite:fav,isRecent:recent,isPinned:false,
            available:"unresolved",capabilities:[]
        });
    }
    return {rows:rows,invalidCount:0,state:state};
}
