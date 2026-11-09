.pragma library

// U7a: review-only navigation destinations for already-normalized CPU++
// Favorites. This policy never forwards source IDs, credentials, callbacks,
// executable commands, URLs, paths, PID values or activity references.
function fail() {
    return {ok:false,owner:"",view:""};
}
function plan(row) {
    if(!row || typeof row!=="object" || Array.isArray(row)
            || row.readOnly!==true || typeof row.key!=="string"
            || row.key.length===0)
        return fail();
    const owner=row.owner,category=row.category,menu=row.menu;
    if(owner==="appcontrol"
            && ((category==="APP CTRL"
                 && ["APPS","FILES","RUN","WINDOWS","KILL","THERMAL","SYSTEM","OTHER"]
                     .indexOf(menu)>=0)
                || (category==="CPU++"
                    && ["KILL","THERMAL","SYSTEM"].indexOf(menu)>=0)))
        return {ok:true,owner:"appcontrol",
                view:menu==="OTHER"?"FAVORITES":menu};
    if(owner==="weather-home" && category==="WEATHER"
            && (menu==="HOME" || menu==="CARD"))
        return {ok:true,owner:"weather",view:"home"};
    if(owner==="radio" && category==="RADIO"
            && (menu==="FAVORITES" || menu==="RECENTS"))
        return {ok:true,owner:"weather",view:"radio"};
    if(owner==="notifications" && category==="NOTIFS"
            && menu==="SOURCES")
        return {ok:true,owner:"notifications",view:"favorites"};
    if(owner==="hospital" && category==="HOSPITAL"
            && ["ROUNDS","STAFF","REPORTS","PHONE","INTERCOM","ACTIVITY"]
                .indexOf(menu)>=0)
        return {ok:true,owner:"hospital",view:"reception"};
    return fail();
}
