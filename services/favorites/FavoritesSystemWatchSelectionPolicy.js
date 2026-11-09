.pragma library
.import "FavoritesResourcePolicy.js" as Resource

// U7b-J // Read-only SYSTEM row/box view selection. The short token is
// neither a permission nor a command. Source identifiers and box identities
// are reconstructed only by the AppControl owner from live telemetry.
var BOXES=["utilization","metric"];
var PREFIX="fav1:local:appcontrol:";
var MAX_RAW=400;
function validSourceId(value) {
    return typeof value==="string" && value.length<=128 &&
        /^system:(?:cpu|memory|swap|rootfs|disk:[A-Za-z0-9._-]{1,64}|gpu:[A-Za-z0-9._-]{1,64}|net:[A-Za-z0-9._-]{1,64})$/.test(value);
}
function rawFor(sourceId,boxId) {
    if(!validSourceId(sourceId) || (boxId!=="" && BOXES.indexOf(boxId)<0))
        return "";
    return boxId
        ? "watchbox|system|"+encodeURIComponent(sourceId)+"|"+encodeURIComponent(boxId)
        : "system|"+encodeURIComponent(sourceId);
}
function parseRaw(raw,kind) {
    if(typeof raw!=="string" || raw.length>MAX_RAW) return null;
    if(kind==="item") {
        if(raw.indexOf("system|")!==0) return null;
        let id="";
        try {id=decodeURIComponent(raw.slice(7));} catch(e) {return null;}
        return raw===rawFor(id,"") ? {raw:raw,kind:"item",sourceId:id,boxId:""} : null;
    }
    if(kind!=="monitor-watch") return null;
    const parts=raw.split("|");
    if(parts.length!==4 || parts[0]!=="watchbox" || parts[1]!=="system")
        return null;
    let id="",box="";
    try {
        id=decodeURIComponent(parts[2]);
        box=decodeURIComponent(parts[3]);
    } catch(e) {return null;}
    return box!=="" && raw===rawFor(id,box)
        ? {raw:raw,kind:kind,sourceId:id,boxId:box} : null;
}
function hex32(n) {return ("00000000"+(n>>>0).toString(16)).slice(-8);}
function fingerprint(raw) {
    let a=0x811c9dc5,b=0x9747b28c;
    for(let i=0;i<raw.length;i++)
        a=Math.imul(a^raw.charCodeAt(i),0x01000193)>>>0;
    for(let i=raw.length-1;i>=0;i--)
        b=Math.imul(b^raw.charCodeAt(i),0x5bd1e995)>>>0;
    return hex32(a)+hex32(b);
}
function tokenForRaw(raw,kind) {
    return parseRaw(raw,kind)
        ? (kind==="item"?"s-":"w-")+fingerprint(raw) : "";
}
function validToken(token) {
    return typeof token==="string" && /^[sw]-[0-9a-f]{16}$/.test(token);
}
function deny(reason) {return {ok:false,token:"",reason:reason};}
function plan(row) {
    if(!row || typeof row!=="object" || Array.isArray(row)
            || row.owner!=="appcontrol" || row.provider!=="appcontrol"
            || row.category!=="CPU++" || row.menu!=="SYSTEM"
            || row.readOnly!==true || row.isFavorite!==true
            || row.resolved!==true || typeof row.key!=="string"
            || (row.kind!=="item" && row.kind!=="monitor-watch")
            || row.favoriteType!==(row.kind==="item"?"FAVORITE":"METRIC WATCH"))
        return deny("UNSUPPORTED_RESOURCE");
    const prefix=PREFIX+row.kind+":";
    if(row.key.indexOf(prefix)!==0 || row.key.length>MAX_RAW+prefix.length+20)
        return deny("INVALID_RESOURCE");
    let raw="";
    try {raw=decodeURIComponent(row.key.slice(prefix.length));}
    catch(e) {return deny("INVALID_RESOURCE");}
    if(!parseRaw(raw,row.kind) ||
            row.key!==Resource.identityKey("appcontrol",row.kind,raw))
        return deny("INVALID_RESOURCE");
    return {ok:true,token:tokenForRaw(raw,row.kind),reason:""};
}
function resolveVisible(token,systemRows) {
    if(!validToken(token) || !Array.isArray(systemRows))
        return {ok:false,reason:"INVALID_CONTEXT"};
    const kind=token.charAt(0)==="w"?"monitor-watch":"item";
    let found=null,matches=0;
    for(const row of systemRows) {
        if(!row || typeof row!=="object" || row._systemRecord!==true
                || !validSourceId(row.id)) continue;
        const boxes=kind==="item"?[""]:BOXES;
        for(const box of boxes) {
            const raw=rawFor(row.id,box);
            if(tokenForRaw(raw,kind)!==token) continue;
            found={ok:true,sourceId:row.id,boxId:box,kind:kind,reason:""};
            matches++;
            if(matches>1)return {ok:false,reason:"AMBIGUOUS_LIVE_ID"};
        }
    }
    return matches===1 ? found : {ok:false,reason:"NO_MATCHING_LIVE_ID"};
}
function selectedIndex(sourceId,rows) {
    if(!validSourceId(sourceId) || !Array.isArray(rows)) return -1;
    let index=-1;
    for(let i=0;i<rows.length;i++) {
        if(rows[i] && rows[i]._systemRecord===true && rows[i].id===sourceId) {
            if(index>=0) return -1;
            index=i;
        }
    }
    return index;
}
