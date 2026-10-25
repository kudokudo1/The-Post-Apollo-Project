.pragma library

// Social identities v1: ORGANIZATION DATA ONLY. No credentials, app sessions,
// login metadata or mutable browser paths belong in this document.
var VERSION = 1;
var MAX_IDENTITIES = 12;
var MAX_FAMILIES = 20;
var MAX_NAME = 32;
var MAX_FILE_BYTES = 65536;
var MAX_ID = 1000000000;

// Stable service IDs, in the existing selector order. An identity layout
// references these names, NEVER the host selector's numeric activation index.
var APP_IDS = [
    "sessions", "discord", "telegram", "x", "instagram", "facebook",
    "reddit", "threads", "pinterest", "truthsocial", "bluesky",
    "tumblr", "tiktok", "snapchat", "whatsapp", "messenger",
    "linkedin", "mastodon", "nextdoor", "steamchat", "element",
    "groupme", "lemon8", "quora", "pixelfed", "zalo", "signal",
    "wechat", "line", "viber", "kakaotalk", "bereal"
];

function integer(value, min, max) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= min && value <= max;
}

function cleanName(raw) {
    if (typeof raw !== "string") return "";
    var v = raw.trim();
    return v.length > 0 && v.length <= MAX_NAME
           && !/[\x00-\x1f\x7f]/.test(v) ? v : "";
}

function numberedId(raw, prefix) {
    if (typeof raw !== "string"
            || !new RegExp("^" + prefix + "-[1-9][0-9]*$").test(raw))
        return -1;
    var suffix = Number(raw.slice(prefix.length + 1));
    return integer(suffix, 1, MAX_ID) ? suffix : -1;
}

function validAppId(value) {
    return typeof value === "string" && APP_IDS.indexOf(value) !== -1;
}

function emptyLayout() {
    return {nextFamilyId: 1, families: [], hiddenAppIds: []};
}

// A neutral, temporary starting family, not operator-approved categories.
// Full catalog visibility is preserved until actual family rules are agreed.
function defaultLayout() {
    return {
        nextFamilyId: 2,
        families: [{
            id: "family-1", name: "ALL APPS",
            appIds: APP_IDS.slice(), expanded: true
        }],
        hiddenAppIds: []
    };
}

function initialDocument() {
    return {
        version: VERSION, nextIdentityId: 2, activeId: "identity-1",
        identities: [{id: "identity-1", name: "Default", layout: defaultLayout()}]
    };
}

function validLayout(layout) {
    if (!layout || typeof layout !== "object" || Array.isArray(layout)
            || !integer(layout.nextFamilyId, 1, MAX_ID)
            || !Array.isArray(layout.families)
            || layout.families.length > MAX_FAMILIES
            || !Array.isArray(layout.hiddenAppIds)
            || layout.hiddenAppIds.length > APP_IDS.length)
        return false;
    var familySeen = {}, familyNames = {}, appSeen = {}, highest = 0;
    for (var i = 0; i < layout.families.length; ++i) {
        var f = layout.families[i];
        if (!f || typeof f !== "object" || Array.isArray(f)
                || numberedId(f.id, "family") < 1
                || !cleanName(f.name) || f.name !== cleanName(f.name)
                || !Array.isArray(f.appIds) || typeof f.expanded !== "boolean")
            return false;
        var folded = f.name.toLowerCase();
        if (Object.prototype.hasOwnProperty.call(familySeen, f.id)
                || Object.prototype.hasOwnProperty.call(familyNames, folded))
            return false;
        familySeen[f.id] = true;
        familyNames[folded] = true;
        highest = Math.max(highest, numberedId(f.id, "family"));
        for (var j = 0; j < f.appIds.length; ++j) {
            var app = f.appIds[j];
            if (!validAppId(app) || Object.prototype.hasOwnProperty.call(appSeen, app))
                return false;
            appSeen[app] = true;
        }
    }
    if (highest >= layout.nextFamilyId) return false;
    var hiddenSeen = {};
    for (var k = 0; k < layout.hiddenAppIds.length; ++k) {
        var hidden = layout.hiddenAppIds[k];
        if (!validAppId(hidden)
                || Object.prototype.hasOwnProperty.call(hiddenSeen, hidden))
            return false;
        hiddenSeen[hidden] = true;
    }
    return true;
}

function validate(doc) {
    if (!doc || typeof doc !== "object" || Array.isArray(doc))
        return {ok:false, reason:"INVALID_DOCUMENT"};
    if (doc.version !== VERSION)
        return {ok:false, reason:"UNSUPPORTED_VERSION"};
    if (!integer(doc.nextIdentityId, 1, MAX_ID)
            || !Array.isArray(doc.identities)
            || doc.identities.length < 1
            || doc.identities.length > MAX_IDENTITIES)
        return {ok:false, reason:"INVALID_IDENTITIES"};
    var seen = {}, names = {}, highest = 0, activePresent = false;
    for (var i = 0; i < doc.identities.length; ++i) {
        var item = doc.identities[i];
        if (!item || typeof item !== "object" || Array.isArray(item)
                || numberedId(item.id, "identity") < 1
                || !cleanName(item.name) || item.name !== cleanName(item.name)
                || !validLayout(item.layout))
            return {ok:false, reason:"INVALID_IDENTITY"};
        var folded = item.name.toLowerCase();
        if (Object.prototype.hasOwnProperty.call(seen, item.id)
                || Object.prototype.hasOwnProperty.call(names, folded))
            return {ok:false, reason:"DUPLICATE_IDENTITY"};
        seen[item.id] = true;
        names[folded] = true;
        highest = Math.max(highest, numberedId(item.id, "identity"));
        if (item.id === doc.activeId) activePresent = true;
    }
    if (highest >= doc.nextIdentityId)
        return {ok:false, reason:"SEQUENCE_REWIND"};
    if (!activePresent)
        return {ok:false, reason:"INVALID_ACTIVE_ID"};
    return {ok:true, reason:""};
}

// Whitelist-only cloning discards unexpected fields, even if a manually
// edited file includes password, tokens, or executable-looking data.
function cloneLayout(layout) {
    return {
        nextFamilyId: layout.nextFamilyId,
        families: layout.families.map(function(f) {
            return {id:f.id, name:f.name, appIds:f.appIds.slice(),
                    expanded:f.expanded};
        }),
        hiddenAppIds: layout.hiddenAppIds.slice()
    };
}

function clone(doc) {
    return {version:VERSION, nextIdentityId:doc.nextIdentityId,
            activeId:doc.activeId,
            identities:doc.identities.map(function(item) {
                return {id:item.id, name:item.name,
                        layout:cloneLayout(item.layout)};
            })};
}

function parse(raw) {
    if (typeof raw !== "string" || raw.length === 0
            || raw.length > MAX_FILE_BYTES)
        return {ok:false, reason:"INVALID_FILE"};
    var doc;
    try { doc = JSON.parse(raw); }
    catch (e) { return {ok:false, reason:"INVALID_JSON"}; }
    var check = validate(doc);
    return check.ok ? {ok:true, reason:"", document:clone(doc)} : check;
}

function create(doc, name, mode, copyFromId) {
    var check = validate(doc);
    if (!check.ok) return check;
    var title = cleanName(name);
    if (!title) return {ok:false, reason:"INVALID_NAME"};
    if (doc.identities.some(function(i) {
        return i.name.toLowerCase() === title.toLowerCase();
    })) return {ok:false, reason:"DUPLICATE_NAME"};
    if (doc.identities.length >= MAX_IDENTITIES)
        return {ok:false, reason:"CAPACITY"};
    if (doc.nextIdentityId >= MAX_ID)
        return {ok:false, reason:"ID_EXHAUSTED"};
    if (mode !== "default" && mode !== "copy" && mode !== "empty")
        return {ok:false, reason:"INVALID_MODE"};

    var layout;
    if (mode === "copy") {
        var source = doc.identities.find(function(i) { return i.id === copyFromId; });
        if (!source) return {ok:false, reason:"INVALID_COPY_SOURCE"};
        layout = cloneLayout(source.layout);
    } else {
        layout = mode === "default" ? defaultLayout() : emptyLayout();
    }
    var next = clone(doc);
    var id = "identity-" + next.nextIdentityId++;
    next.identities.push({id:id, name:title, layout:layout});
    next.activeId = id; // Select layout only; NEVER trigger account login.
    return {ok:true, reason:"", document:next};
}

function select(doc, id) {
    var check = validate(doc);
    if (!check.ok) return check;
    if (typeof id !== "string"
            || !doc.identities.some(function(i) { return i.id === id; }))
        return {ok:false, reason:"INVALID_IDENTITY"};
    if (doc.activeId === id) return {ok:false, reason:"NO_CHANGE"};
    var next = clone(doc);
    next.activeId = id;
    return {ok:true, reason:"", document:next};
}

// Family expansion is saved independently per Post-Apollo identity.
// Mutating layout preferences must never switch provider accounts.
function toggleFamily(doc, familyId) {
    var check = validate(doc);
    if (!check.ok) return check;
    if (typeof familyId !== "string")
        return {ok:false, reason:"INVALID_FAMILY"};
    var next = clone(doc);
    var active = next.identities.find(function(i) {
        return i.id === next.activeId;
    });
    var family = active.layout.families.find(function(f) {
        return f.id === familyId;
    });
    if (!family) return {ok:false, reason:"INVALID_FAMILY"};
    family.expanded = !family.expanded;
    return {ok:true, reason:"", document:next};
}

// Family manager v1: organization only, scoped to the currently active
// Post-Apollo identity. Stable family IDs and service IDs never become a
// provider credential, session path, or numeric launcher identity.
function createFamily(doc, name) {
    var checked = validate(doc);
    if (!checked.ok) return checked;
    var title = cleanName(name);
    if (!title) return {ok:false, reason:"INVALID_FAMILY_NAME"};
    var next = clone(doc);
    var identity = next.identities.find(function(i) {
        return i.id === next.activeId;
    });
    var layout = identity.layout;
    if (layout.families.length >= MAX_FAMILIES)
        return {ok:false, reason:"FAMILY_CAPACITY"};
    if (layout.nextFamilyId >= MAX_ID)
        return {ok:false, reason:"FAMILY_ID_EXHAUSTED"};
    if (layout.families.some(function(f) {
        return f.name.toLowerCase() === title.toLowerCase();
    })) return {ok:false, reason:"DUPLICATE_FAMILY_NAME"};
    var id = "family-" + layout.nextFamilyId++;
    layout.families.push({id:id, name:title, appIds:[], expanded:true});
    return {ok:true, reason:"", document:next, familyId:id};
}

function renameFamily(doc, familyId, name) {
    var checked = validate(doc);
    if (!checked.ok) return checked;
    if (typeof familyId !== "string")
        return {ok:false, reason:"INVALID_FAMILY"};
    var title = cleanName(name);
    if (!title) return {ok:false, reason:"INVALID_FAMILY_NAME"};
    var next = clone(doc);
    var identity = next.identities.find(function(i) {
        return i.id === next.activeId;
    });
    var family = identity.layout.families.find(function(f) {
        return f.id === familyId;
    });
    if (!family) return {ok:false, reason:"INVALID_FAMILY"};
    if (family.name === title) return {ok:false, reason:"NO_CHANGE"};
    if (identity.layout.families.some(function(f) {
        return f.id !== familyId
               && f.name.toLowerCase() === title.toLowerCase();
    })) return {ok:false, reason:"DUPLICATE_FAMILY_NAME"};
    family.name = title;
    return {ok:true, reason:"", document:next, familyId:familyId};
}

// Membership changes are NOT app launch actions. The original provider
// index is derived later from APP_IDS by rowsForLayout, never persisted here.
// Moving an unassigned app into a family supports start-empty identities.
function moveAppToFamily(doc, appId, targetFamilyId) {
    var checked = validate(doc);
    if (!checked.ok) return checked;
    if (!validAppId(appId))
        return {ok:false, reason:"INVALID_APP"};
    if (typeof targetFamilyId !== "string")
        return {ok:false, reason:"INVALID_FAMILY"};
    var next = clone(doc);
    var identity = next.identities.find(function(i) {
        return i.id === next.activeId;
    });
    var families = identity.layout.families;
    var target = families.find(function(f) {
        return f.id === targetFamilyId;
    });
    if (!target) return {ok:false, reason:"INVALID_FAMILY"};
    if (target.appIds.indexOf(appId) !== -1)
        return {ok:false, reason:"NO_CHANGE"};
    for (var i = 0; i < families.length; ++i) {
        var index = families[i].appIds.indexOf(appId);
        if (index !== -1)
            families[i].appIds.splice(index, 1);
    }
    target.appIds.push(appId);
    // The app's existing hidden flag, if any, stays independent of placement.
    return {ok:true, reason:"", document:next,
            familyId:targetFamilyId, appId:appId};
}

// UI-only rows, with stable provider indices from the canonical catalog.
// A collapsed or hidden app is not reachable by keyboard activation.
function rowsForLayout(layout) {
    var rows = [], indices = [];
    var hidden = {};
    for (var i = 0; i < layout.hiddenAppIds.length; ++i)
        hidden[layout.hiddenAppIds[i]] = true;
    for (var f = 0; f < layout.families.length; ++f) {
        var family = layout.families[f];
        var members = family.appIds.filter(function(appId) {
            return !Object.prototype.hasOwnProperty.call(hidden, appId);
        });
        rows.push({kind:"family", familyId:family.id, title:family.name,
                   expanded:family.expanded, count:members.length});
        if (!family.expanded) continue;
        for (var j = 0; j < members.length; ++j) {
            var serviceIndex = APP_IDS.indexOf(members[j]);
            if (serviceIndex < 0) continue; // Validate before rendering.
            indices.push(serviceIndex);
            rows.push({kind:"app", serviceId:members[j],
                       serviceIndex:serviceIndex});
        }
    }
    if (layout.families.length === 0)
        rows.push({kind:"empty", title:"NO FAMILIES"});
    return {rows:rows, appIndices:indices};
}

function view(state, doc, reason) {
    var usable = (state === "ready" || state === "empty" || state === "saving")
                 && validate(doc).ok;
    // On malformed/newer config keep the original service rail accessible.
    // Never auto-repair or write over unrecognized on-disk state.
    var identity = usable ? doc.identities.find(function(i) {
        return i.id === doc.activeId;
    }) : null;
    var display = rowsForLayout(identity ? identity.layout : defaultLayout());
    var families = identity ? identity.layout.families.map(function(f) {
        return {id:f.id, title:f.name, count:f.appIds.length,
                expanded:f.expanded};
    }) : [];
    var appChoices = identity ? APP_IDS.map(function(appId, index) {
        var family = identity.layout.families.find(function(f) {
            return f.appIds.indexOf(appId) !== -1;
        });
        return {id:appId, serviceIndex:index,
                familyId:family ? family.id : ""};
    }) : [];
    return {
        familyOptions: families, appChoices: appChoices,
        nextFamilyId: identity ? identity.layout.nextFamilyId : -1,
        activeName: identity ? identity.name : "",
        railRows: display.rows, visibleAppIndices: display.appIndices,
        state: state, writable: state === "ready" || state === "empty",
        error: state === "error" || state === "unsupported"
               ? String(reason || "STORAGE_UNAVAILABLE").slice(0, 60) : "",
        activeId: usable ? doc.activeId : "",
        identities: usable ? doc.identities.map(function(i) {
            return {id:i.id, name:i.name, familyCount:i.layout.families.length};
        }) : []
    };
}
