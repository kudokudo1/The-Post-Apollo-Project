.pragma library

// Pure, non-mutating FinanceW category-create/rename proposal policy.
// Requires stable IDs from the authenticated Actual snapshot. No writers.
function previewCategoryPlan(snapshot, mode, categoryId, groupId, rawName) {
    function refuse(reason) { return {ok:false, reason:reason}; }
    if (!snapshot || snapshot.readOnly!==true || snapshot.source!=="actual-budget"
            || typeof snapshot.sourceKey!=="string"
            || !/^[0-9a-f]{64}$/.test(snapshot.sourceKey)
            || typeof snapshot.month!=="string"
            || !/^20\d{2}-(0[1-9]|1[0-2])$/.test(snapshot.month)
            || !Array.isArray(snapshot.categories)
            || !Array.isArray(snapshot.categoryGroups))
        return refuse("AUTHENTICATED SOURCE REQUIRED");
    if (mode!=="create" && mode!=="rename")
        return refuse("SELECT CREATE OR RENAME");
    if (typeof rawName!=="string") return refuse("ENTER A CATEGORY NAME");
    var name=rawName.trim().replace(/\s+/g," ");
    if (!name || name.length>80 || /[\u0000-\u001f\u007f]/.test(rawName))
        return refuse("NAME MUST BE 1 TO 80 CHARACTERS");
    var groups=snapshot.categoryGroups.filter(function(g) {
        return g && g.id===groupId && typeof g.name==="string";
    });
    if (groups.length!==1) return refuse("SELECT AN EXISTING EXPENSE GROUP");
    var current=null;
    if (mode==="rename") {
        var matches=snapshot.categories.filter(function(c) {
            return c && c.id===categoryId && c.groupId===groupId;
        });
        if (matches.length!==1 || !matches[0].name)
            return refuse("CATEGORY CHANGED // REVIEW AGAIN");
        current=matches[0];
        if (current.name===name) return refuse("NAME UNCHANGED");
    }
    if (snapshot.categories.some(function(c) {
        return c && c.groupId===groupId && c.name
            && c.name.trim().toLowerCase()===name.toLowerCase()
            && (mode==="create" || c.id!==categoryId);
    })) return refuse("NAME ALREADY USED IN THIS GROUP");
    return {
        ok:true, mode:mode, sourceKey:snapshot.sourceKey,
        month:snapshot.month, groupId:groupId, groupName:groups[0].name,
        categoryId:mode==="rename" ? categoryId : "",
        originalName:current ? current.name : "", proposedName:name,
        savesToActual:false
    };
}
