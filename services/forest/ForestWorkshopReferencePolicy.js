// B6-R2 reference metadata only; no provider mapping or permission inference.
function key(x) { return typeof x === "string" && /^[a-z][a-z0-9-]{0,63}$/.test(x); }
function keys(x) {
    return Array.isArray(x) && x.length <= 128 && x.every(key)
        && x.every(function(v,i) { return x.indexOf(v) === i; });
}
function subset(x,y) { return x.every(function(v) { return y.indexOf(v)>=0; }); }
function exact(obj,fields) {
    return !!obj && typeof obj==="object" && !Array.isArray(obj)
        && Object.keys(obj).length===fields.length
        && fields.every(function(k) { return Object.prototype.hasOwnProperty.call(obj,k); });
}
function parse(raw,expected) {
    if (typeof raw!=="string" || raw.length>65536 || !Array.isArray(expected)) return null;
    var d;
    try { d=JSON.parse(raw); } catch(e) { return null; }
    if (!exact(d,["schema","inputs","profile","definitions","general_ready","workshops","plan",
                 "permission_granted","production_authority","model_execution_permitted","safe_actions"]) ||
        d.schema!=="post-apollo.forest.ui-workshop-reference.b6r2" ||
        d.profile!=="BRISTLECONE_HISTORICAL_REFERENCE" ||
        JSON.stringify(d.inputs)!==JSON.stringify(expected) ||
        d.permission_granted!==false || d.production_authority!==false ||
        d.model_execution_permitted!==false || !Array.isArray(d.safe_actions) || d.safe_actions.length!==0 ||
        !Array.isArray(d.definitions) || d.definitions.length<1 || d.definitions.length>128 ||
        !Array.isArray(d.workshops) || d.workshops.length<1 || d.workshops.length>128 ||
        !keys(d.general_ready)) return null;
    var ids=[];
    for(var i=0;i<d.definitions.length;i++) {
        var item=d.definitions[i];
        if (!exact(item,["key","kind","sticky_allowed","historical_target"]) || !key(item.key) ||
            ids.indexOf(item.key)>=0 || ["toolset","context","skill","capability"].indexOf(item.kind)<0 ||
            typeof item.sticky_allowed!=="boolean" ||
            (item.historical_target!==null && (typeof item.historical_target!=="string" ||
                !/^[a-z][a-z0-9_-]{0,63}$/.test(item.historical_target)))) return null;
        ids.push(item.key);
    }
    if (!subset(d.general_ready,ids)) return null;
    var workshopKeys=[], chosen=null;
    for(var j=0;j<d.workshops.length;j++) {
        var w=d.workshops[j];
        if (!exact(w,["key","core","ready"]) || !key(w.key) || workshopKeys.indexOf(w.key)>=0 ||
            !keys(w.core) || !w.core.length || !keys(w.ready) || !subset(w.core.concat(w.ready),ids) ||
            w.ready.some(function(v) { return w.core.indexOf(v)>=0; })) return null;
        workshopKeys.push(w.key);
        if (w.key===expected[0]) chosen=w;
    }
    var p=d.plan;
    if (!chosen || !exact(p,["workshop","core","selected","dormant","unresolved","status"]) ||
        p.workshop!==chosen.key || p.status!=="UNKNOWN_HOLD" ||
        !keys(p.core) || !keys(p.selected) || !keys(p.dormant) || !keys(p.unresolved) ||
        JSON.stringify(p.core)!==JSON.stringify(chosen.core) ||
        !subset(p.core,p.selected) || !subset(p.selected,ids) || !subset(p.dormant,ids) ||
        !subset(p.unresolved,p.selected) || p.selected.length+p.dormant.length!==ids.length ||
        p.dormant.some(function(v) { return p.selected.indexOf(v)>=0; })) return null;
    var g=expected[1]?expected[1].split(","):[], r=expected[2]?expected[2].split(","):[];
    if (!keys(g)||!keys(r)||!subset(g,d.general_ready)||!subset(r,chosen.ready)||
        !subset(g.concat(r),p.selected)||!subset(p.selected,p.core.concat(g,r))) return null;
    var unresolved=d.definitions.filter(function(v) {
        return v.historical_target===null && p.selected.indexOf(v.key)>=0;
    }).map(function(v) { return v.key; });
    if (!subset(unresolved,p.unresolved)||!subset(p.unresolved,unresolved)) return null;
    return d;
}
function toggle(values,value) {
    var next=values.slice(), i=next.indexOf(value);
    if (i<0) next.push(value); else next.splice(i,1);
    return next;
}
