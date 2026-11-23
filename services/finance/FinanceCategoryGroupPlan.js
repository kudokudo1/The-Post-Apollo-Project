.pragma library

// FinanceW M4: category GROUP proposal only. Absolutely no persistence,
// network, permit creation, or Actual mutators. Not a writer or consent UI.
function previewGroupPlan(snapshot, mode, groupId, rawName) {
    function refuse(reason) { return {ok:false, reason:reason}; }
    if (!snapshot || snapshot.readOnly!==true
            || snapshot.source!=="actual-budget"
            || typeof snapshot.sourceKey!=="string"
            || !/^[0-9a-f]{64}$/.test(snapshot.sourceKey)
            || typeof snapshot.month!=="string"
            || !/^20\d{2}-(0[1-9]|1[0-2])$/.test(snapshot.month)
            || !Array.isArray(snapshot.categoryGroups)
            || !Array.isArray(snapshot.categories))
        return refuse("AUTHENTICATED BUDGET REQUIRED");
    if (mode!=="create" && mode!=="rename")
        return refuse("CHOOSE NEW GROUP OR RENAME GROUP");
    if (typeof rawName!=="string")return refuse("ENTER GROUP NAME");
    var name=rawName.trim().replace(/\s+/g," ");
    if(!name || name.length>80 || /[\u0000-\u001f\u007f]/.test(rawName))
        return refuse("GROUP NAME MUST BE 1 TO 80 CHARACTERS");
    if(name.toLowerCase()==="income")
        return refuse("INCOME IS A RESERVED GROUP");
    if(mode==="create" && groupId!=="")
        return refuse("NEW GROUP CANNOT TARGET AN EXISTING ID");
    if(mode==="rename" && (typeof groupId!=="string"
            || !/^[A-Za-z0-9-]{4,80}$/.test(groupId)))
        return refuse("INVALID EXISTING GROUP ID");
    if(snapshot.categoryGroups.some(function(g){
        return !g || typeof g.id!=="string"
            || !/^[A-Za-z0-9-]{4,80}$/.test(g.id)
            || typeof g.name!=="string" || !g.name.trim()
            || (g.is_income!==undefined && g.is_income!==null
                && typeof g.is_income!=="boolean");
    }))return refuse("UNTRUSTED GROUP LIST");
    if(snapshot.categoryGroups.some(function(g,index){
        return snapshot.categoryGroups.slice(0,index).some(function(other){
            return other.id===g.id;
        });
    }))return refuse("AMBIGUOUS GROUP IDS // REFRESH");
    var current=null;
    if(mode==="rename") {
        var matches=snapshot.categoryGroups.filter(function(g){
            return g.id===groupId;
        });
        if(matches.length!==1)return refuse("GROUP CHANGED // REVIEW AGAIN");
        current=matches[0];
        if(current.is_income===true)
            return refuse("INCOME GROUP CANNOT BE RENAMED");
        if(current.name.trim().toLowerCase()===name.toLowerCase())
            return refuse("GROUP NAME UNCHANGED");
    }
    if(snapshot.categoryGroups.some(function(g) {
        return g.name.trim().toLowerCase()===name.toLowerCase()
            && (mode==="create" || g.id!==groupId);
    }))return refuse("GROUP NAME ALREADY USED");
    return {
        ok:true, mode:mode,
        sourceKey:snapshot.sourceKey,month:snapshot.month,
        groupId:mode==="rename"?groupId:"",
        originalName:current?current.name:"",
        proposedName:name,
        savesToActual:false
    };
}
