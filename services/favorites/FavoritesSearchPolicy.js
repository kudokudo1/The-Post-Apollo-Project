.pragma library

// U9c // Presentation-only saved Favorites search, restricted to the fields
// already displayed as names, source categories, menus and item types.
// Never inspect raw favorite keys, resource IDs, commands or stored secrets.
// All query words must match in ANY order; partial substrings are accepted.
var MAX_QUERY=120;
var FIELDS=["label","item","category","menu","favoriteType",
            "kind","sourceName","provider","owner"];
function normalized(value) {
    return String(value || "").toLowerCase()
        .replace(/[\u0300-\u036f]/g,"")
        .replace(/[^a-z0-9]+/g," ").trim();
}
function words(text) {
    const clean=normalized(text);
    return clean ? clean.split(/\s+/).filter(Boolean) : [];
}
function sourceText(row) {
    if(!row || typeof row!=="object" || Array.isArray(row))
        return "";
    const values=[];
    for(const field of FIELDS) {
        // Explicitly do not include key, resourceId, identifiers or actions.
        if(typeof row[field]==="string" && row[field].length)
            values.push(row[field].slice(0,160));
    }
    const searchable=normalized(values.join(" "));
    if(!searchable)return "";
    const pad=" "+searchable+" ";
    const aliases=[];
    // Equivalences only when the corresponding human-readable words exist.
    if(pad.includes(" maryland ")) aliases.push("md");
    if(pad.includes(" md ")) aliases.push("maryland");
    if(pad.includes(" united states ")) aliases.push("usa us");
    if(pad.includes(" usa ") || pad.includes(" u s a ")
            || pad.includes(" us ")) aliases.push("united states usa");
    if(pad.includes(" app ctrl ") || pad.includes(" appcontrol "))
        aliases.push("app control app ctrl appcontrol");
    if(pad.includes(" app control ")) aliases.push("app ctrl appcontrol");
    return searchable+" "+aliases.join(" ");
}
function matches(row,query) {
    const q=typeof query==="string" ? query.slice(0,MAX_QUERY) : "";
    const terms=words(q);
    if(terms.length===0)return true;
    const content=sourceText(row);
    return content.length>0 && terms.every(function(term) {
        return content.indexOf(term)>=0;
    });
}
