.pragma library
.import "FavoritesResourcePolicy.js" as Resource

// U7b-E // Read-only selection, NOT a fan-control or thermal action bridge.
// CPU++ forwards only a short opaque view-selector. The AppControl owner
// resolves it against its *current* saved keys and live telemetry, refusing
// ambiguous/removed sensors. Device names and hwmon paths never cross shell.
var MAX_KEY_LENGTH=500;
var RAW_PREFIX="thermal|";
var KEY_PREFIX="fav1:local:appcontrol:item:";

function validSourceId(id) {
    return typeof id==="string" && id.length<=192
        && /^(?:thermal|fan):[A-Za-z0-9][A-Za-z0-9._+-]{0,63}:[A-Za-z0-9][A-Za-z0-9 ._+():-]{0,95}$/.test(id);
}
function parseSavedKey(raw) {
    if(typeof raw!=="string" || raw.length>MAX_KEY_LENGTH
            || raw.indexOf(RAW_PREFIX)!==0) return null;
    let id="";
    try {id=decodeURIComponent(raw.slice(RAW_PREFIX.length));}
    catch(error) {return null;}
    if(!validSourceId(id)
            || raw!==RAW_PREFIX+encodeURIComponent(id)) return null;
    return {raw:raw,sourceId:id,kind:id.indexOf("fan:")===0?"fan":"temperature"};
}
function parseResourceKey(key) {
    if(typeof key!=="string" || key.length>MAX_KEY_LENGTH+KEY_PREFIX.length
            || key.indexOf(KEY_PREFIX)!==0) return null;
    let raw="";
    try {raw=decodeURIComponent(key.slice(KEY_PREFIX.length));}
    catch(error) {return null;}
    const resource=parseSavedKey(raw);
    if(!resource
            || key!==Resource.identityKey("appcontrol","item",raw))
        return null;
    return resource;
}
function hex32(num) {return ("00000000"+(num>>>0).toString(16)).slice(-8);}
function fingerprint(raw) {
    // Two independent 32-bit non-cryptographic hashes in forward/reverse
    // order. This is a collision-resistant *selector*, not authorization.
    // The source owner always requires exactly one saved/live match.
    let a=0x811c9dc5,b=0x9747b28c;
    for(let i=0;i<raw.length;i++)
        a=Math.imul(a^raw.charCodeAt(i),0x01000193)>>>0;
    for(let i=raw.length-1;i>=0;i--)
        b=Math.imul(b^raw.charCodeAt(i),0x5bd1e995)>>>0;
    return hex32(a)+hex32(b);
}
function tokenForSavedKey(raw) {
    const item=parseSavedKey(raw);
    return item ? (item.kind==="fan"?"f-":"t-")+fingerprint(raw) : "";
}
function validToken(token) {
    return typeof token==="string" && /^[tf]-[0-9a-f]{16}$/.test(token);
}
function deny(reason) {return {ok:false,token:"",reason:reason};}
function plan(row) {
    if(!row || typeof row!=="object" || Array.isArray(row)
            || row.owner!=="appcontrol" || row.provider!=="appcontrol"
            || row.kind!=="item" || row.category!=="CPU++"
            || row.menu!=="THERMAL" || row.favoriteType!=="FAVORITE"
            || row.readOnly!==true || row.resolved!==true
            || row.isFavorite!==true)
        return deny("UNSUPPORTED_RESOURCE");
    const candidate=parseResourceKey(row.key);
    if(!candidate) return deny("UNSAFE_OR_STALE_ID");
    return {ok:true,token:tokenForSavedKey(candidate.raw),reason:""};
}
// Only the AppControl owner should call resolve. The returned sourceId must
// remain inside the owner and is NEVER a shell/CPU++ signal argument.
function resolve(token,savedKeys,thermalRows,fanRows) {
    if(!validToken(token) || !Array.isArray(savedKeys)
            || !Array.isArray(thermalRows) || !Array.isArray(fanRows))
        return {ok:false};
    let candidate=null,count=0;
    for(const raw of savedKeys) {
        const item=parseSavedKey(raw);
        if(!item || tokenForSavedKey(raw)!==token) continue;
        candidate=item;
        count++;
        if(count!==1) return {ok:false};
    }
    if(count!==1 || !candidate) return {ok:false};
    const rows=candidate.kind==="fan"?fanRows:thermalRows;
    let matches=0;
    for(const entry of rows) {
        if(entry && typeof entry==="object" && entry._thermalRecord===true
                && entry.sensorKind===candidate.kind
                && entry.id===candidate.sourceId)
            matches++;
    }
    if(matches!==1) return {ok:false};
    return {ok:true,kind:candidate.kind,sourceId:candidate.sourceId};
}
// U7b-G // Selection is a local READ-ONLY view operation, not favorite
// mutation or privileged device action. Once CPU++ has supplied a bounded,
// syntactically validated view token, the owner should resolve it against
// its own LIVE sensor rows, not gate opening the local view on a second
// favorites-store membership lookup that may be stale.
// The short token is not an authorization mechanism: only one genuine
// _thermalRecord in the matching sensor family can be selected. Neither
// device paths nor raw IDs leave AppControl.
function resolveVisible(token,thermalRows,fanRows) {
    if(!validToken(token) || !Array.isArray(thermalRows)
            || !Array.isArray(fanRows))
        return {ok:false,reason:"INVALID_CONTEXT"};
    const kind=token.charAt(0)==="f" ? "fan" : "temperature";
    const rows=kind==="fan" ? fanRows : thermalRows;
    let matchId="",matches=0;
    for(const row of rows) {
        if(!row || typeof row!=="object"
                || row._thermalRecord!==true
                || row.sensorKind!==kind
                || typeof row.id!=="string") continue;
        // Reconstruct ONLY AppControl's established favoriteKeyFor()
        // identity, without consulting stored favorites or display names.
        const raw="thermal|"+encodeURIComponent(row.id);
        const parsed=parseSavedKey(raw);
        if(!parsed || parsed.kind!==kind
                || tokenForSavedKey(raw)!==token) continue;
        matches++;
        if(matches>1) return {ok:false,reason:"AMBIGUOUS_LIVE_ID"};
        matchId=row.id;
    }
    if(matches!==1) return {ok:false,reason:"NO_MATCHING_LIVE_ID"};
    return {ok:true,reason:"",kind:kind,sourceId:matchId};
}

function selectedIndex(token,sourceId,visibleRows,kind) {
    if(!validToken(token) || !validSourceId(sourceId)
            || !Array.isArray(visibleRows)
            || (kind!=="fan" && kind!=="temperature")
            || (kind==="fan")!==(sourceId.indexOf("fan:")===0))
        return -1;
    let found=-1;
    for(let i=0;i<visibleRows.length;i++) {
        const item=visibleRows[i];
        if(item && item._thermalRecord===true
                && item.id===sourceId && item.sensorKind===kind) {
            if(found!==-1) return -1;
            found=i;
        }
    }
    return found;
}
