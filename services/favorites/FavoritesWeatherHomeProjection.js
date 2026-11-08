.pragma library
.import "../weather/WeatherHomeFavoritesPolicy.js" as WeatherRules
.import "FavoritesReadOnlyAdapters.js" as Adapters

// U5a READ-ONLY projection of the existing Weather HOME owner. The caller
// injects its already-loaded snapshot; this script never mounts a writer,
// reads a file, invokes a provider action or claims live weather availability.
function build(snapshot) {
    const empty={rows:[],invalidCount:0,state:"disconnected"};
    if (snapshot===null || snapshot===undefined) return empty;
    if (!snapshot || typeof snapshot!=="object" || Array.isArray(snapshot))
        return {rows:[],invalidCount:1,state:"invalid"};
    const state=String(snapshot.storageState || "unknown");
    // Unreadable and not-yet-loaded owner data is not "zero favorites."
    // Do not invent an empty successful catalog for these states.
    if (state!=="ready" && state!=="empty")
        return {rows:[],invalidCount:0,state:state};

    const panels=snapshot.panelRoutes, cards=snapshot.cardKeys;
    if (!WeatherRules.validList(panels,WeatherRules.validPanel,
            WeatherRules.PANELS.length)
            || !WeatherRules.validList(cards,WeatherRules.validCardKey,
                WeatherRules.MAX_CARD_KEYS))
        return {rows:[],invalidCount:1,state:"invalid"};

    const adapter=Adapters.weatherHome({panelRoutes:panels,cardKeys:cards});
    if (adapter.invalidCount>0 || adapter.items.length!==panels.length+cards.length)
        return {rows:[],invalidCount:adapter.invalidCount || 1,state:"invalid"};

    const rows=[];
    for (const resource of adapter.items) {
        const id=resource.resourceId;
        const kind=resource.kind;
        let menu="", item="",favoriteType="";
        if (kind==="panel") {
            menu="HOME";
            item=id.slice(5).replace(/-/g," ").toUpperCase();
            favoriteType="HOME PANEL FAVORITE";
        } else if (kind==="card") {
            const split=id.indexOf("|");
            if (split<1) return {rows:[],invalidCount:1,state:"invalid"};
            menu="CARD";
            item=id.slice(0,split).toUpperCase()
                 +" // "+id.slice(split+1).replace(/-/g," ").toUpperCase();
            favoriteType="HOME CARD FAVORITE";
        } else return {rows:[],invalidCount:1,state:"invalid"};
        rows.push({
            key:resource.key,provider:"weather-home",kind:kind,
            label:"WEATHER // "+menu+" // "+item,
            sourceName:"WEATHER STATION",menu:menu,item:item,
            favoriteType:favoriteType,resolved:true,category:"WEATHER",
            owner:"weather-home",readOnly:true,
            isFavorite:true,isPinned:false,available:"unresolved",
            capabilities:[]
        });
    }
    return {rows:rows,invalidCount:0,state:state};
}
