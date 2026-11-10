.pragma library

// W2b: dedicated Weather HOME bookmark identities. No data samples,
// source freshness claims, AppControl keys or mutable provider records.
var FORMAT = "post-apollo.weather-home-favorites.v1";
var VERSION = 1;
var MAX_CARD_KEYS = 32;
var PANELS = [
    "home/auto", "home/quick", "home/snapshot",
    "home/history", "home/runtime", "home/health"
];

function empty() {
    return {
        schema: FORMAT,
        version: VERSION,
        revision: 0,
        panelRoutes: [],
        cardKeys: []
    };
}

function validPanel(value) {
    return typeof value === "string" && PANELS.indexOf(value) >= 0;
}

function validCardKey(value) {
    return typeof value === "string"
        && /^(weather|sky|ground|space)\|[a-z][a-z0-9-]{0,63}$/.test(value);
}

function normalized(values, accept, limit) {
    var result = [];
    var rows = Array.isArray(values) ? values : [];
    for (var i = 0; i < rows.length; i++) {
        if (accept(rows[i]) && result.indexOf(rows[i]) < 0)
            result.push(rows[i]);
        if (result.length >= limit)
            break;
    }
    return result;
}

function validList(values, accept, limit) {
    if (!Array.isArray(values) || values.length > limit)
        return false;
    var seen = {};
    for (var i = 0; i < values.length; i++) {
        if (!accept(values[i]) || seen[values[i]])
            return false;
        seen[values[i]] = true;
    }
    return true;
}

function parse(raw) {
    var item;
    try {
        item = JSON.parse(String(raw));
    } catch (error) {
        return {ok:false,reason:"INVALID_JSON"};
    }
    if (!item || typeof item !== "object" || Array.isArray(item))
        return {ok:false,reason:"INVALID_DOCUMENT"};
    if (item.schema !== FORMAT || item.version !== VERSION)
        return {ok:false,reason:"UNSUPPORTED_VERSION"};
    if (!Number.isSafeInteger(item.revision) || item.revision < 0)
        return {ok:false,reason:"INVALID_REVISION"};
    if (!validList(item.panelRoutes,validPanel,PANELS.length)
        || !validList(item.cardKeys,validCardKey,MAX_CARD_KEYS))
        return {ok:false,reason:"INVALID_BOOKMARKS"};

    var document = empty();
    document.revision = item.revision;
    document.panelRoutes = item.panelRoutes.slice();
    document.cardKeys = item.cardKeys.slice();
    return {ok:true,reason:"",document:document};
}

function replacePanels(document, input) {
    if (!validList(input,validPanel,PANELS.length))
        return {ok:false,reason:"INVALID_PANELS"};
    return update(document,input,document.cardKeys);
}

function toggleCard(document, key) {
    if (!validCardKey(key))
        return {ok:false,reason:"INVALID_CARD_KEY"};
    var cards = document && Array.isArray(document.cardKeys)
        ? document.cardKeys.slice() : [];
    var at = cards.indexOf(key);
    if (at < 0) {
        if (cards.length >= MAX_CARD_KEYS)
            return {ok:false,reason:"CARD_LIMIT"};
        cards.push(key);
    } else {
        cards.splice(at,1);
    }
    return update(document,document.panelRoutes,cards);
}

function update(document, panelRoutes, cardKeys) {
    if (!document || document.schema !== FORMAT
        || document.version !== VERSION
        || !Number.isSafeInteger(document.revision)
        || document.revision < 0
        || document.revision >= Number.MAX_SAFE_INTEGER)
        return {ok:false,reason:"INVALID_BASE"};
    if (!validList(panelRoutes,validPanel,PANELS.length)
        || !validList(cardKeys,validCardKey,MAX_CARD_KEYS))
        return {ok:false,reason:"INVALID_BOOKMARKS"};
    var oldPanels = document.panelRoutes || [];
    var oldCards = document.cardKeys || [];
    var unchanged = oldPanels.length === panelRoutes.length
        && oldPanels.every(function(p,i) {return panelRoutes[i] === p;})
        && oldCards.length === cardKeys.length
        && oldCards.every(function(k,i) {return cardKeys[i] === k;});
    if (unchanged)
        return {ok:true,changed:false,document:document};
    return {ok:true,changed:true,document:{
        schema:FORMAT,
        version:VERSION,
        revision:document.revision+1,
        panelRoutes:panelRoutes.slice(),
        cardKeys:cardKeys.slice()
    }};
}
