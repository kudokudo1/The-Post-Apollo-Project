.pragma library
.import "FavoritesCollectionsPolicy.js" as CollectionRules

// U6b presentation-only collection index. The one-writer local CollectionsStore
// supplies its already-loaded array; current U5 candidates supply display names.
// We never decode, render, fetch, rehydrate, or actuate an absent provider key.
var MAX_GROUPS=24;
var MAX_MEMBERS=80;
var MAX_TOTAL=600;
var MAX_CANDIDATES=200;
var VISIBLE=["ready","empty","saving"];
function empty(state) {
    return {groups:[],count:0,memberCount:0,missingCount:0,
            state:state || "disconnected"};
}
function build(collections,candidates,storageState) {
    const state=String(storageState || "disconnected");
    if(VISIBLE.indexOf(state)<0) return empty(state);
    if(!Array.isArray(collections) || collections.length>MAX_GROUPS)
        return empty("invalid");
    const rows=candidates && Array.isArray(candidates.rows)
        ? candidates.rows.slice(0,MAX_CANDIDATES) : [];
    const byKey=Object.create(null),seenRows=Object.create(null);
    for(const row of rows) {
        if(!row || typeof row.key!=="string" || !row.key
                || seenRows[row.key] || !CollectionRules.checkMemberKey(row.key).ok)
            continue;
        seenRows[row.key]=true;
        byKey[row.key]=row;
    }
    const result=empty(state),ids=Object.create(null),names=Object.create(null);
    let total=0;
    for(const group of collections) {
        if(!group || typeof group!=="object" || Array.isArray(group)
                || !CollectionRules.validCollectionId(group.id)
                || !CollectionRules.normalizedName(group.name)
                || !Array.isArray(group.members) || group.members.length>MAX_MEMBERS
                || ids[group.id] || names[group.name.toLowerCase()])
            return empty("invalid");
        ids[group.id]=true;
        names[group.name.toLowerCase()]=true;
        const seenMembers=Object.create(null),items=[],matchedRows=[];
        for(const key of group.members) {
            if(typeof key!=="string" || seenMembers[key]
                    || !CollectionRules.checkMemberKey(key).ok)
                return empty("invalid");
            seenMembers[key]=true;
            total++;
            if(total>MAX_TOTAL) return empty("invalid");
            const candidate=byKey[key];
            if(!candidate) {
                // Never display the raw, possibly private persisted key.
                items.push({
                    key:"",name:"SAVED MEMBER UNAVAILABLE",
                    type:"SOURCE NOT LOADED",missing:true
                });
                continue;
            }
            matchedRows.push(candidate);
            const name=typeof candidate.item==="string" && candidate.item
                && candidate.resolved ? candidate.item
                : typeof candidate.label==="string" && candidate.label
                  ? candidate.label : "NAME UNAVAILABLE";
            items.push({
                key:key,
                name:name.slice(0,120),
                type:String(candidate.category || "SAVED").slice(0,32),
                missing:false
            });
        }
        result.groups.push({
            id:group.id,name:group.name,count:group.members.length,
            available:matchedRows.length,
            missing:group.members.length-matchedRows.length,
            items:items,rows:matchedRows
        });
    }
    result.count=result.groups.length;
    result.memberCount=total;
    result.missingCount=result.groups.reduce((n,g)=>n+g.missing,0);
    return result;
}
function section(view,id) {
    if(!view || !Array.isArray(view.groups) || typeof id!=="string")
        return null;
    return view.groups.find(g=>g.id===id) || null;
}
function rowsFor(view,id) {
    const group=section(view,id);
    return group ? group.rows : [];
}
