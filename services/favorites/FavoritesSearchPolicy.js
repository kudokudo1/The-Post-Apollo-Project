.pragma library

// U9c // Presentation-only saved Favorites search, restricted to the fields
// already displayed as names, source categories, menus and item types.
// Never inspect raw favorite keys, resource IDs, commands or stored secrets.
// All query words match in ANY order. Exact partials win; typo tolerance is bounded.
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
// U9d // Bounded restricted Damerau-Levenshtein (one neighboring swap
// counts as one typo). Query words are matched independently and unordered.
// Keep short terms (MD, US, 1) and all digits EXACT to avoid unsafe
// overmatching of saved metrics, sensor numbers or abbreviations.
function typoBudget(term) {
    if(term.length<4 || term.length>32 || /[0-9]/.test(term))
        return 0;
    return term.length>=7 ? 2 : 1;
}
function withinEdits(a,b,limit) {
    if(Math.abs(a.length-b.length)>limit || a.length>32 || b.length>32)
        return false;
    let before=null,previous=[];
    for(let j=0;j<=b.length;j++)previous[j]=j;
    for(let i=1;i<=a.length;i++) {
        const current=[i];
        for(let j=1;j<=b.length;j++) {
            let cost=a.charAt(i-1)===b.charAt(j-1) ? 0 : 1;
            let distance=Math.min(
                previous[j]+1,current[j-1]+1,previous[j-1]+cost);
            if(i>1 && j>1
                    && a.charAt(i-1)===b.charAt(j-2)
                    && a.charAt(i-2)===b.charAt(j-1))
                distance=Math.min(distance,before[j-2]+1);
            current[j]=distance;
        }
        before=previous;
        previous=current;
    }
    return previous[b.length]<=limit;
}
function termMatches(content,sourceWords,term) {
    // Preserve every existing literal substring match, including "1".
    if(content.indexOf(term)>=0)return true;
    const budget=typoBudget(term);
    if(!budget)return false;
    for(const word of sourceWords) {
        if(word.length>32)continue;
        // Whole-word fuzzy match, plus a fuzzy start of a longer word.
        // E.g. "threm" finds "thermal" despite the swapped letters.
        if(withinEdits(term,word,budget)
                || (word.length>term.length
                    && withinEdits(term,word.slice(0,term.length),budget)))
            return true;
    }
    return false;
}
function matches(row,query) {
    const q=typeof query==="string" ? query.slice(0,MAX_QUERY) : "";
    const terms=words(q);
    if(terms.length===0)return true;
    const content=sourceText(row);
    if(!content)return false;
    const sourceWords=words(content);
    return terms.every(function(term) {
        return termMatches(content,sourceWords,term);
    });
}
