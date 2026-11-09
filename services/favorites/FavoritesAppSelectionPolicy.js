.pragma library
.import "FavoritesResourcePolicy.js" as Resource

// U7b-C // AppControl APPS *selection*, never launch or execute.
// Only a conservative freedesktop DesktopEntry id crosses the CPU++->shell
// boundary, not a universal favorite key, command, path, PID or action.
var RESOURCE_PREFIX="fav1:local:appcontrol:item:";
function validDesktopId(value) {
    return typeof value==="string" && value.length<=128
        && /^[A-Za-z][A-Za-z0-9._+-]*$/.test(value);
}
function deny(reason) {
    return {ok:false,desktopId:"",reason:reason};
}
function plan(row) {
    if (!row || typeof row!=="object" || Array.isArray(row)
            || row.owner!=="appcontrol" || row.provider!=="appcontrol"
            || row.kind!=="item" || row.category!=="APP CTRL"
            || row.menu!=="APPS" || row.favoriteType!=="FAVORITE"
            || row.readOnly!==true || row.isFavorite!==true
            || row.resolved!==true || typeof row.key!=="string"
            || row.key.indexOf(RESOURCE_PREFIX)!==0)
        return deny("UNSUPPORTED_RESOURCE");
    let id="";
    try {id=decodeURIComponent(row.key.slice(RESOURCE_PREFIX.length));}
    catch(error) {return deny("INVALID_ID");}
    if (!validDesktopId(id)
            || Resource.identityKey("appcontrol","item",id)!==row.key)
        return deny("UNSAFE_ID");
    return {ok:true,desktopId:id,reason:""};
}
// Source owner rechecks BOTH original saved membership and current installed
// DesktopEntries. A missing, duplicate, hidden-command or stale source is
// refused. Never infer the target from a display name or search text.
function ownerAllows(desktopId,savedKeys,installedApps) {
    if(!validDesktopId(desktopId)
            || !Array.isArray(savedKeys) || !Array.isArray(installedApps)
            || savedKeys.filter(function(x) {return x===desktopId;}).length!==1)
        return false;
    let count=0;
    for (const entry of installedApps) {
        if (entry && typeof entry==="object" && !entry._hiddenCommand
                && typeof entry.id==="string" && entry.id===desktopId)
            count++;
    }
    return count===1;
}
function selectedIndex(desktopId,visibleApps) {
    if (!validDesktopId(desktopId) || !Array.isArray(visibleApps))
        return -1;
    let found=-1;
    for(let i=0;i<visibleApps.length;i++) {
        const entry=visibleApps[i];
        if(entry && !entry._hiddenCommand && entry.id===desktopId) {
            if(found>=0) return -1; // Ambiguous list must not select first.
            found=i;
        }
    }
    return found;
}
