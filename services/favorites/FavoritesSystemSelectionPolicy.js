.pragma library
.import "FavoritesResourcePolicy.js" as Resource

// U7b-D: select only four stable SYSTEM telemetry rows in the original
// AppControl owner. The wire token is a fixed family name, not a PID, file,
// network/device identity, metric value, action, or original favorite key.
var CORE=["cpu","memory","swap","rootfs"];

function validMetric(metric) {
    return typeof metric==="string" && CORE.indexOf(metric)>=0;
}
function sourceId(metric) {
    return validMetric(metric) ? "system:"+metric : "";
}
function savedKey(metric) {
    const id=sourceId(metric);
    return id ? "system|"+encodeURIComponent(id) : "";
}
function deny(reason) {
    return {ok:false,metric:"",reason:reason};
}
function plan(row) {
    if(!row || typeof row!=="object" || Array.isArray(row)
            || row.owner!=="appcontrol" || row.provider!=="appcontrol"
            || row.kind!=="item" || row.category!=="CPU++"
            || row.menu!=="SYSTEM" || row.favoriteType!=="FAVORITE"
            || row.readOnly!==true || row.isFavorite!==true
            || row.resolved!==true || typeof row.key!=="string")
        return deny("UNSUPPORTED_RESOURCE");
    for(const metric of CORE) {
        if(row.key===Resource.identityKey(
                "appcontrol","item",savedKey(metric)))
            return {ok:true,metric:metric,reason:""};
    }
    return deny("UNKNOWN_SYSTEM_ID");
}
// AppControl must recheck both its ONLY writer and current telemetry. The
// authoritative metric must exist exactly once in its live SYSTEM snapshot.
// A selection request never asks the telemetry provider to perform an action.
function ownerAllows(metric,originalSavedKeys,systemRows) {
    if(!validMetric(metric) || !Array.isArray(originalSavedKeys)
            || !Array.isArray(systemRows)) return false;
    const key=savedKey(metric),id=sourceId(metric);
    if(originalSavedKeys.filter(function(x){return x===key;}).length!==1)
        return false;
    let matches=0;
    for(const row of systemRows) {
        if(row && typeof row==="object" && row._systemRecord===true
                && row.id===id)
            matches++;
    }
    return matches===1;
}
function selectedIndex(metric,visibleRows) {
    if(!validMetric(metric) || !Array.isArray(visibleRows)) return -1;
    const id=sourceId(metric);
    let index=-1;
    for(let i=0;i<visibleRows.length;i++) {
        const row=visibleRows[i];
        if(row && row._systemRecord===true && row.id===id) {
            if(index>=0) return -1;
            index=i;
        }
    }
    return index;
}
