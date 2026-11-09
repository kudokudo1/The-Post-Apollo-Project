.pragma library
.import "FavoritesResourcePolicy.js" as Resource
.import "../weather/WeatherHomeFavoritesPolicy.js" as WeatherHome

// U7b-A contract, not an action bridge. CPU++ may request one of the owner's
// fixed, non-sensitive HOME panel routes only. No paths, process commands,
// private saved IDs, stream URLs, callbacks or arbitrary route strings escape.
function deny(reason) {
    return {ok:false,owner:"",route:"",reason:reason};
}

function plan(row) {
    if (!row || typeof row!=="object" || Array.isArray(row)
            || row.readOnly!==true || row.resolved!==true
            || row.owner!=="weather-home" || row.provider!=="weather-home"
            || row.category!=="WEATHER" || row.kind!=="panel"
            || row.menu!=="HOME" || row.isFavorite!==true
            || typeof row.key!=="string")
        return deny("UNSUPPORTED_RESOURCE");

    // Never decode an arbitrary candidate key into an executable route.
    // Compare to canonical identities for the six known Weather-owned paths.
    for (const route of WeatherHome.PANELS) {
        if (row.key===Resource.identityKey("weather-home","panel",route))
            return {ok:true,owner:"weather",route:route,reason:""};
    }
    return deny("UNKNOWN_OR_STALE_IDENTITY");
}

// U7b-K // Read-only local navigation is not a permission or bookmark write.
// The existing six HOME routes are public in-widget pages, so the owning
// Weather UI can display them even if the favorites store is still loading,
// saving, stale or unavailable. This validation NEVER accepts an arbitrary
// external URL, command, path, terminal, station or provider action.
function localRouteAllows(route) {
    return WeatherHome.validPanel(route);
}

// Snapshot-based membership remains useful for read-only catalog diagnostics,
// but it is not a prerequisite for opening an already-known HOME view.
// The snapshot-membership diagnostic checks the original Weather store.
// A CPU++ plan is only a navigation request, not a writer or permission grant.
// Navigation uses localRouteAllows() instead, leaving this read-only diagnostic
// available for catalog freshness checks.
function ownerAllows(route,snapshot) {
    if (!WeatherHome.validPanel(route) || !snapshot
            || typeof snapshot!=="object" || Array.isArray(snapshot)
            || (snapshot.storageState!=="ready"
                && snapshot.storageState!=="empty"))
        return false;
    if (!WeatherHome.validList(snapshot.panelRoutes,
                            WeatherHome.validPanel,WeatherHome.PANELS.length)
            || !WeatherHome.validList(snapshot.cardKeys,
                            WeatherHome.validCardKey,WeatherHome.MAX_CARD_KEYS))
        return false;
    return snapshot.panelRoutes.indexOf(route)>=0;
}
