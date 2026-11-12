.pragma library

// U7a: review-only navigation destinations for already-normalized CPU++
// Favorites. This policy never forwards source IDs, credentials, callbacks,
// executable commands, URLs, paths, PID values or activity references.
function fail() {
    return {ok:false,owner:"",view:""};
}
function plan(row) {
    if(!row || typeof row!=="object" || Array.isArray(row)
            || typeof row.key!=="string" || row.key.length===0)
        return fail();
    // Angel numbers already belong to FavoritesDefaultStore. Opening its
    // journal changes a VIEW, never this source-owned favorite membership.
    if (row.owner==="angel" && row.provider==="angel"
            && row.category==="NEW" && row.kind==="number"
            && row.isFavorite===true && row.readOnly===false
            && /^fav1:local:angel:number:[0-9]{1,8}$/.test(row.key))
        return {ok:true,owner:"clock",view:"angel"};
    if (row.readOnly!==true) return fail();
    const owner=row.owner,category=row.category,menu=row.menu;
    if (owner==="clock-alarm" && category==="CLOCK" && menu==="ALARMS"
            && row.provider==="clock-alarm" && row.kind==="alarm"
            && row.isFavorite===true)
        return {ok:true,owner:"clock",view:"alarm"};
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
