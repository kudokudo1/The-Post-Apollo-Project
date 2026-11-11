.pragma library

// User preference store, not a claim that Sway currently uses these values.
// Nothing in this document causes startup/runtime input commands on load.
var VERSION = 1;
var FACTORS = [0.25,0.5,0.75,1,1.25,1.5,1.75,2,2.5,3,4,5,6];
var MAX_SAVED = 32;
var DEVICE_ID = /^[A-Za-z0-9_.:+-]{1,160}$/;

function validFactor(value) {
    return typeof value === "number" && isFinite(value)
           && value >= 0.25 && value <= 6;
}
function validId(id) {
    return typeof id === "string" && DEVICE_ID.test(id);
}
function initialDocument() {
    return {version: VERSION, devices: []};
}
function validDocument(doc) {
    if (!doc || typeof doc !== "object" || Array.isArray(doc)
            || doc.version !== VERSION || !Array.isArray(doc.devices)
            || doc.devices.length > MAX_SAVED)
        return false;
    var seen = {};
    for (var i = 0; i < doc.devices.length; i++) {
        var item = doc.devices[i];
        if (!item || typeof item !== "object"
                || !validId(item.identifier) || !validFactor(item.factor)
                || Object.prototype.hasOwnProperty.call(seen, item.identifier))
            return false;
        seen[item.identifier] = true;
    }
    return true;
}
function parse(raw) {
    var doc;
    try { doc = JSON.parse(String(raw)); }
    catch (_) { return {ok:false, reason:"INVALID_JSON"}; }
    if (!validDocument(doc))
        return {ok:false, reason:"INVALID_PROFILE"};
    return {ok:true, document:{version:VERSION,
                               devices:doc.devices.map(function(x) {
                                   return {identifier:x.identifier, factor:x.factor};
                               })}};
}
function get(doc, id) {
    if (!validDocument(doc) || !validId(id)) return null;
    for (var i=0; i<doc.devices.length; i++)
        if (doc.devices[i].identifier === id) return doc.devices[i].factor;
    return null;
}
function withFactor(doc, id, factor) {
    if (!validDocument(doc) || !validId(id) || !validFactor(factor))
        return {ok:false, reason:"INVALID_CHOICE"};
    var next = {version:VERSION, devices:[]};
    var found = false;
    for (var i=0; i<doc.devices.length; i++) {
        var old = doc.devices[i];
        if (old.identifier === id) {
            next.devices.push({identifier:id, factor:factor});
            found = true;
        } else {
            next.devices.push({identifier:old.identifier, factor:old.factor});
        }
    }
    if (!found) {
        if (next.devices.length >= MAX_SAVED)
            return {ok:false, reason:"PROFILE_FULL"};
        next.devices.push({identifier:id,factor:factor});
    }
    return {ok:true, document:next};
}
