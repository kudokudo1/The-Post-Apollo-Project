// R6c1: disposable CI parent framing only, no Process, UI or Runtime authority.
// Contract R6a R1; counterpart runtime_public_child_r6b.py.
// ASCII JS string lengths equal wire bytes only after ASCII validation.
// Does not bound allocations inside Quickshell/Qt native conversion.
var CONTROL = 512, RESPONSE = 16384, TOTAL = 131072, FRAMES = 160, ACTIONS = 64;
function refuse() { throw new Error("R6_WIRE_REFUSED"); }
function own(o,k) { return Object.prototype.hasOwnProperty.call(o,k); }
function record(o) { return o !== null && typeof o === "object" && !Array.isArray(o); }
function exact(o,keys) {
    return record(o) && Object.keys(o).length === keys.length && keys.every(k=>own(o,k));
}
function token(s) { return typeof s === "string" && s.length === 32 && /^[0-9a-f]{32}$/.test(s); }
function integer(v,min,max) { return Number.isSafeInteger(v) && !Object.is(v,-0) && v>=min && v<=max; }
function forbidden(k) { return k==="__proto__" || k==="constructor" || k==="prototype"; }
function ascii(s,lf) {
    if (typeof s !== "string") refuse();
    for (let i=0;i<s.length;i++) {
        const n=s.charCodeAt(i);
        if ((n<32 || n>126) && !(lf && n===10)) refuse();
    }
}
function envelope(o) {
    if (!exact(o,["v","trial","action","kind","data"]) || o.v!==1
        || !token(o.trial) || !integer(o.action,1,ACTIONS)
        || typeof o.kind!=="string" || !record(o.data)) refuse();
    return o;
}
// Bounded lexical pass BEFORE JSON.parse or recursive canonical sort.
// String contents are scanned without counting delimiters as structure.
function preparse(s) {
    ascii(s,false);
    let i=0,nodes=0,tokens=0;
    const stack=[];
    while(i<s.length) {
        const c=s[i];
        tokens++;
        if(c==="{" || c==="[") {
            stack.push(c); nodes++; i++;
        } else if(c==="}" || c==="]") {
            if(stack.pop()!==(c==="}"?"{":"[")) refuse();
            i++;
        } else if(c==="," || c===":") i++;
        else if(c==='"') {
            nodes++; i++;
            let closed=false;
            while(i<s.length) {
                const d=s[i++];
                if(d==='"') { closed=true; break; }
                if(d==="\\") {
                    if(i>=s.length || (s[i]!=='"' && s[i]!=="\\")) refuse();
                    i++;
                }
            }
            if(!closed) refuse();
        } else if(c>="0" && c<="9") {
            const start=i++;
            while(i<s.length && s[i]>="0" && s[i]<="9") i++;
            if(i-start>16 || (c==="0" && i-start>1)
                || !integer(Number(s.slice(start,i)),0,Number.MAX_SAFE_INTEGER)) refuse();
            nodes++;
        } else {
            const literal=c==="t"?"true":c==="f"?"false":c==="n"?"null":"";
            if(!literal || s.slice(i,i+literal.length)!==literal) refuse();
            i+=literal.length; nodes++;
        }
        if(stack.length>8 || nodes>256 || tokens>512) refuse();
    }
    if(stack.length || !tokens) refuse();
}
// Canonical encoding is also bounded for locally constructed control frames.
// Called on parsed data only AFTER lexical limits, or fixed local owner data.
function canonical(o,cap) {
    let out="", nodes=0;
    function put(s) {
        if(out.length+s.length>=cap) refuse(); // reserve LF
        out+=s;
    }
    function string(s) {
        if(typeof s!=="string" || s.length>=cap) refuse();
        ascii(s,false); put(JSON.stringify(s));
    }
    function walk(v,depth) {
        if(++nodes>256) refuse();
        if(v===null || typeof v==="boolean") put(String(v));
        else if(typeof v==="number") {
            if(!integer(v,0,Number.MAX_SAFE_INTEGER)) refuse();
            put(String(v));
        } else if(typeof v==="string") string(v);
        else if(Array.isArray(v)) {
            if(depth>8 || v.length>256) refuse();
            put("[");
            for(let i=0;i<v.length;i++) {
                if(!own(v,i)) refuse();
                if(i) put(",");
                walk(v[i],depth+1);
            }
            put("]");
        } else if(record(v)) {
            if(depth>8) refuse();
            const keys=Object.keys(v);
            if(keys.length>256) refuse();
            keys.sort();
            put("{");
            for(let i=0;i<keys.length;i++) {
                const k=keys[i];
                if(++nodes>256 || forbidden(k)) refuse();
                if(i) put(",");
                string(k); put(":"); walk(v[k],depth+1);
            }
            put("}");
        } else refuse();
    }
    walk(o,1);
    preparse(out);
    return out+"\n";
}
function decode(line,cap) {
    if(typeof line!=="string" || line.length<2 || line.length>cap
        || line[line.length-1]!=="\n") refuse();
    const body=line.slice(0,-1);
    preparse(body);
    let o;
    try { o=JSON.parse(body); } catch(e) { refuse(); }
    // Equality refuses duplicate keys (including overwritten duplicates),
    // noncanonical order and alternative spellings before any dispatch.
    if(canonical(o,cap)!==line) refuse();
    return envelope(o);
}
// No frame queue: one complete bounded line handed synchronously to owner.
// Owner still MUST validate exact nested schemas, pending action, process/
// Loader identity and deadlines before consumer calls. No frame grants rights.
function createWire() {
    let partial="", bytes=0, frames=0, failed=false, ended=false, receiving=false;
    function snapshot() { return {bytes,frames,retained:partial.length,failed,ended}; }
    function stop() { failed=true; partial=""; return false; }
    function charge(n,f) {
        if(bytes+n>TOTAL || frames+f>FRAMES) refuse();
        bytes+=n; frames+=f;
    }
    function reserve(offered) {
        if(failed || ended || receiving) return false;
        const count=offered?4:2, size=(offered?2:1)*(CONTROL+RESPONSE);
        return bytes+size<=TOTAL && frames+count<=FRAMES;
    }
    function prepare(o) {
        if(failed || ended) return null;
        try {
            const line=canonical(envelope(o),CONTROL);
            charge(line.length,1); // attempted submission; no refund on failure
            return line;
        } catch(e) { stop(); return null; }
    }
    function receive(chunk,onFrame) {
        if(failed || ended || receiving) return stop();
        receiving=true;
        try {
            // Charge all observed ASCII code units conservatively before any
            // append/dispatch; rejected non-ASCII cannot be counted as raw bytes.
            if(typeof chunk!=="string" || chunk.length>TOTAL-bytes) refuse();
            charge(chunk.length,0);
            ascii(chunk,true);
            for(let i=0;i<chunk.length;i++) {
                if(failed || ended) refuse();
                if(!partial.length) charge(0,1);
                const c=chunk[i];
                if(c==="\n") {
                    const frame=decode(partial+"\n",RESPONSE);
                    partial="";
                    if(onFrame(frame)!==true || failed) refuse();
                } else {
                    if(partial.length>=RESPONSE-1) refuse();
                    partial+=c;
                }
            }
            return true;
        } catch(e) { return stop(); }
        finally { receiving=false; }
    }
    function end() {
        if(failed || ended || receiving || partial.length) return stop();
        ended=true; return true;
    }
    return {snapshot,reserve,prepare,receive,end,stop};
}
