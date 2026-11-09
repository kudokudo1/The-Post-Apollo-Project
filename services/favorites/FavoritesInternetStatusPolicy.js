.pragma library

// U8d // A view-only projection of the existing Network dock probe.
// ONLINE means one of two configured external HTTPS checks succeeded recently;
// LIMITED means repeat failure across those endpoints. Neither proves the
// whole Internet is healthy or down. A disconnected local link is distinct.
var STALE_MS=420000;
function view(code,label) {return {code:code,label:label};}
function plan(snapshot,nowMs) {
    if(!snapshot || typeof snapshot!=="object" || Array.isArray(snapshot))
        return view("checking","CHECKING");
    if(snapshot.localLinkAvailable===false
            && snapshot.linkKnownDown===true)
        return view("offline","NO LINK");
    if(snapshot.localLinkAvailable!==true)
        return view("checking","CHECKING");
    const at=Number(snapshot.lastSampleMs);
    if(!Number.isFinite(at) || at<=0
            || !Number.isFinite(nowMs) || nowMs<at
            || nowMs-at>STALE_MS)
        return view("checking","CHECKING");
    const stable=String(snapshot.reachability || "");
    if(stable==="reachable")
        return view("online","ONLINE");
    if(stable==="impaired")
        return view("limited","LIMITED");
    return view("checking","CHECKING");
}
