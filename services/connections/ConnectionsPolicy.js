.pragma library

// C1 inventory: public provider requirements and read-only observed state.
// This is deliberately NOT a secret store, an authenticated session registry,
// or a new Social account/identity writer. No raw credential may enter rows.
var IDS = [
    "social", "notifications", "proton-mail", "nasa-firms",
    "bbc-world", "al-jazeera-english", "gdelt"
];

function safeCount(value) {
    var n = Number(value);
    return isFinite(n) && n >= 0 ? Math.min(9999, Math.floor(n)) : 0;
}

function accountNamesCount(document, activeId) {
    var identities = document && document.identities;
    var record = identities && identities[String(activeId || "")];
    var accounts = record && record.accounts;
    if (!accounts || typeof accounts !== "object") return 0;
    var total = 0;
    Object.keys(accounts).forEach(function(serviceId) {
        var value = accounts[serviceId];
        total += Array.isArray(value) ? value.length
               : typeof value === "string" && value.trim() ? 1 : 0;
    });
    return safeCount(total);
}

function build(input) {
    var data = input || {};
    var identity = data.socialSnapshot || {};
    var identityState = String(data.socialState || "loading");
    var socialReady = (identityState === "ready" || identityState === "empty")
                      && typeof identity.activeId === "string"
                      && identity.activeId !== "";
    var name = socialReady ? String(identity.activeName || "DEFAULT").slice(0, 32)
                           : "NOT AVAILABLE";
    var count = socialReady
                ? accountNamesCount(data.socialAccounts, identity.activeId) : 0;
    var labelsReady = data.socialAccountState === "ready";
    var firsPresent = data.firmsKeyPresent === true;
    var notificationsActive = data.notificationsReady === true;

    return [
        {id:"social", title:"SOCIAL // IDENTITIES",
         status:socialReady ? "LAYOUT READY" : "LAYOUT UNAVAILABLE",
         kind:"metadata", accent:socialReady?"cyan":"orange",
         detail:socialReady ? "SELECTED // " + name : "SOCIAL STORAGE // " + identityState.toUpperCase(),
         context: labelsReady ? "SAVED ACCOUNT NAMES // " + count
                              : "SAVED ACCOUNT NAMES // NOT LOADED",
         consumers:"SOCIAL // FUTURE CONNECTION PROFILE CONTEXT",
         permissions:"LOCAL IDENTITY LAYOUT AND ACCOUNT DISPLAY NAMES ONLY",
         setup:"SOCIAL OWNS IDENTITY ORGANIZATION. THESE ARE NOT LOGINS, COOKIES OR AUTHENTICATED MAIL SESSIONS.",
         action:"RELOAD SOCIAL"},
        {id:"notifications", title:"NOTIFICATIONS",
         status:notificationsActive ? "LOCAL ENGINE READY" : "LOCAL ENGINE WAITING",
         kind:"local", accent:notificationsActive?"cyan":"orange",
         detail:"LOCAL NOTIFICATION ROUTES // NOT MAILBOX ACCESS",
         context:"MESSAGE ACTIONS REQUIRE VERIFIED SENDER AND MESSAGE IDENTITY",
         consumers:"NOTIFICATIONS // SOCIAL // FUTURE MAIL ADAPTER",
         permissions:"LOCAL NOTIFICATION HISTORY AND LIVE SENDER ACTIONS",
         setup:"EMAIL PREVIEWS CAN ROUTE TO SOCIAL. REPLY, ARCHIVE AND TRASH REQUIRE AN AUTHENTICATED MAIL ADAPTER.",
         action:"INSPECT"},
        {id:"proton-mail", title:"PROTON // MAIL",
         status:"ADAPTER NOT CONNECTED", kind:"account", accent:"orange",
         detail:"PROTON BROWSER/BRIDGE POLICIES EXIST // RELAY DORMANT",
         context:"SAVED SOCIAL ACCOUNT NAMES DO NOT PROVE MAILBOX ACCESS",
         consumers:"NOTIFICATIONS // SOCIAL // AUTHORIZED SETUP",
         permissions:"READ MESSAGE; SEND REPLY; MOVE/TRASH ONLY AFTER ACCOUNT + MESSAGE VERIFICATION",
         setup:"REQUIRES EXPLICIT ACCOUNT AUTHENTICATION AND A VERIFIED PROTON MAIL ADAPTER. NO MAIL ACTIONS AUTHORIZED YET.",
         action:"INSPECT"},
        {id:"nasa-firms", title:"NASA FIRMS // FIRES",
         status:firsPresent ? "KEY PRESENT // UNVERIFIED" : "KEY REQUIRED",
         kind:"api-key", accent:firsPresent?"yellow":"orange",
         detail:"EARTH // VIIRS NOAA-21 // MANUAL BOUNDED FETCH",
         context:"CREDENTIAL IS NEVER REVEALED OR COPIED TO SOCIAL SETTINGS",
         consumers:"WEATHER STATION // EARTH",
         permissions:"NASA FIRMS HOTSPOT AREA REQUESTS ONLY",
         setup:firsPresent
              ? "THE STARTUP ENVIRONMENT HAS A KEY-SHAPED VALUE. A SUCCESSFUL NASA REQUEST IS STILL REQUIRED TO VERIFY IT."
              : "SHARED CREDENTIAL BROKER NOT YET INSTALLED. AN API KEY IS REQUIRED; DO NOT PASTE IT INTO SOCIAL METADATA OR THIS STATUS VIEW.",
         action:"INSPECT"},
        {id:"bbc-world", title:"BBC // WORLD NEWS",
         status:"PUBLIC // ON DEMAND",kind:"public",accent:"cyan",
         detail:"PUBLISHER RSS // NO SIGN-IN REQUIRED",
         context:"CURRENT FEED AVAILABILITY IS CHECKED IN WEATHER STATION",
         consumers:"WEATHER STATION // MEDIA",
         permissions:"PUBLIC HEADLINE READ REQUEST",
         setup:"OPEN WEATHER STATION MEDIA NEWS AND USE LOAD BBC. NO KEY OR SHARED LOGIN REQUIRED.",
         action:"INSPECT"},
        {id:"al-jazeera-english", title:"AL JAZEERA // NEWS",
         status:"PUBLIC // ON DEMAND",kind:"public",accent:"cyan",
         detail:"PUBLISHER RSS // NO SIGN-IN REQUIRED",
         context:"CURRENT FEED AVAILABILITY IS CHECKED IN WEATHER STATION",
         consumers:"WEATHER STATION // MEDIA",
         permissions:"PUBLIC HEADLINE READ REQUEST",
         setup:"OPEN WEATHER STATION MEDIA NEWS AND USE LOAD AL JAZEERA. NO KEY OR SHARED LOGIN REQUIRED.",
         action:"INSPECT"},
        {id:"gdelt",title:"GDELT // NEWS ANALYSIS",
         status:"PUBLIC // RATE LIMITS",kind:"public",accent:"yellow",
         detail:"INDEPENDENT DOC API // PROVIDER CAN RETURN HTTP 429",
         context:"THIS VIEW DOES NOT CLAIM THE API IS CURRENTLY AVAILABLE",
         consumers:"WEATHER STATION // MEDIA",
         permissions:"PUBLIC ARTICLE DISCOVERY REQUEST",
         setup:"USE THE EXISTING GDELT RETRY NEWS CONTROL AFTER ITS COOLDOWN. NO CREDENTIAL IS USED.",
         action:"INSPECT"}
    ];
}

function find(rows, id) {
    var list = Array.isArray(rows) ? rows : [];
    for (var i = 0; i < list.length; ++i)
        if (list[i] && list[i].id === id) return list[i];
    return null;
}

function counters(rows) {
    var list = Array.isArray(rows) ? rows : [];
    var keys = 0, unresolved = 0, publicSources = 0;
    list.forEach(function(row) {
        if (!row) return;
        if (row.kind === "api-key" && row.status === "KEY REQUIRED") keys++;
        if (row.kind === "account" && row.status === "ADAPTER NOT CONNECTED") unresolved++;
        if (row.kind === "public") publicSources++;
    });
    return {keyRequired:keys, unverifiedAccounts:unresolved, publicSources:publicSources};
}
