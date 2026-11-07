.pragma library
.import "FavoritesResourcePolicy.js" as Resource

// U1: persistent default membership only for NEW local resource providers.
// Legacy providers remain sole writers of their existing favorites.
var SCHEMA = "post-apollo.favorites.default.v1";
var VERSION = 1;
var MAX_FAVORITES = 2048;
var MAX_PINS = 512;
var MAX_KEY_LENGTH = 8192;
var MAX_DOCUMENT_CHARS = 1048576;
var RESERVED_PROVIDERS = [
    "appcontrol", "weather-home", "radio", "time", "places",
    "notifications", "hospital"
];
var FEATURES = ["favorite", "pin"];

function empty() {
    return {schema:SCHEMA,version:VERSION,revision:0,favorites:[],pins:[]};
}

function checkKey(key) {
    if (typeof key !== "string" || key.length < 18
            || key.length > MAX_KEY_LENGTH)
        return {ok:false,reason:"INVALID_KEY"};
    const match = /^fav1:local:([a-z][a-z0-9-]{0,47}):([a-z][a-z0-9-]{0,47}):(.+)$/.exec(key);
    if (!match)
        return {ok:false,reason:"INVALID_KEY"};
    let resourceId = "";
    try {
        resourceId = decodeURIComponent(match[3]);
    } catch (error) {
        return {ok:false,reason:"INVALID_KEY"};
    }
    if (Resource.identityKey(match[1],match[2],resourceId) !== key)
        return {ok:false,reason:"INVALID_KEY"};
    if (RESERVED_PROVIDERS.indexOf(match[1]) >= 0)
        return {ok:false,reason:"EXTERNAL_OWNER"};
    return {ok:true,provider:match[1],kind:match[2]};
}

function validList(items,limit) {
    if (!Array.isArray(items) || items.length > limit)
        return false;
    const seen = Object.create(null);
    for (let i = 0; i < items.length; ++i) {
        const key = items[i];
        if (!checkKey(key).ok || seen[key])
            return false;
        seen[key] = true;
    }
    return true;
}

function validDocument(item) {
    if (!item || typeof item !== "object" || Array.isArray(item))
        return {ok:false,reason:"INVALID_DOCUMENT"};
    if (item.schema !== SCHEMA || item.version !== VERSION)
        return {ok:false,reason:"UNSUPPORTED_VERSION"};
    const fields = Object.keys(item).sort();
    if (fields.join("|") !== "favorites|pins|revision|schema|version")
        return {ok:false,reason:"UNSUPPORTED_FIELDS"};
    if (!Number.isSafeInteger(item.revision) || item.revision < 0)
        return {ok:false,reason:"INVALID_REVISION"};
    if (!validList(item.favorites,MAX_FAVORITES)
            || !validList(item.pins,MAX_PINS))
        return {ok:false,reason:"INVALID_MEMBERSHIP"};
    return {ok:true};
}

function parse(raw) {
    const input = String(raw === undefined || raw === null ? "" : raw);
    if (!input || input.length > MAX_DOCUMENT_CHARS)
        return {ok:false,reason:"INVALID_DOCUMENT"};
    let item;
    try {
        item = JSON.parse(input);
    } catch (error) {
        return {ok:false,reason:"INVALID_JSON"};
    }
    const check = validDocument(item);
    if (!check.ok)
        return check;
    return {ok:true,document:{
        schema:SCHEMA,version:VERSION,revision:item.revision,
        favorites:item.favorites.slice(),pins:item.pins.slice()
    }};
}

function contains(document,feature,key) {
    if (!document || FEATURES.indexOf(feature) < 0)
        return false;
    const rows = feature === "favorite" ? document.favorites : document.pins;
    return Array.isArray(rows) && rows.indexOf(key) >= 0;
}

function setFeature(document,feature,key,enabled) {
    if (FEATURES.indexOf(feature) < 0 || typeof enabled !== "boolean")
        return {ok:false,reason:"INVALID_FEATURE"};
    const valid = validDocument(document);
    if (!valid.ok)
        return valid;
    const identity = checkKey(key);
    if (!identity.ok)
        return identity;
    const old = feature === "favorite" ? document.favorites : document.pins;
    const index = old.indexOf(key);
    if ((index >= 0) === enabled)
        return {ok:true,changed:false,document:document};
    const maximum = feature === "favorite" ? MAX_FAVORITES : MAX_PINS;
    if (enabled && old.length >= maximum)
        return {ok:false,reason:"MEMBERSHIP_FULL"};
    if (document.revision >= Number.MAX_SAFE_INTEGER - 1)
        return {ok:false,reason:"REVISION_LIMIT"};
    const values = old.slice();
    if (enabled)
        values.unshift(key);
    else
        values.splice(index,1);
    const next = {
        schema:SCHEMA,version:VERSION,revision:document.revision + 1,
        favorites:feature === "favorite" ? values : document.favorites.slice(),
        pins:feature === "pin" ? values : document.pins.slice()
    };
    // The document, not just individual arrays, is bounded.
    if (JSON.stringify(next).length > MAX_DOCUMENT_CHARS)
        return {ok:false,reason:"DOCUMENT_FULL"};
    return {ok:true,changed:true,document:next};
}

function toggleFeature(document,feature,key) {
    return setFeature(document,feature,key,!contains(document,feature,key));
}
