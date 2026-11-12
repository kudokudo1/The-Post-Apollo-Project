.pragma library

// P1.2 // Pure local media reference policy. The file is NEVER copied,
// uploaded, deleted or opened here. An independent read-only probe must verify
// the file again before the UI can preview it.
var VERSION = 1;
var MAX_ASSETS = 250;
var MAX_LINKS = 1200;
var MAX_PER_DRAFT = 8;
var MAX_DOCUMENT = 1048576;
var MAX_SEQUENCE = 1000000000;
var VIDEO_LIMIT = 1073741824;
var IMAGE_LIMIT = 33554432;

function emptyDocument() {
    return {version: VERSION, nextId: 1, assets: [], links: []};
}
function plain(v) {
    return !!v && typeof v === "object" && !Array.isArray(v)
        && Object.prototype.toString.call(v) === "[object Object]";
}
function exactly(v, fields) {
    if (!plain(v)) return false;
    var one = Object.keys(v).sort(), two = fields.slice().sort();
    return one.length === two.length && one.every(function(key, i) {
        return key === two[i];
    });
}
function integer(n, min, max) {
    return typeof n === "number" && isFinite(n)
        && Math.floor(n) === n && n >= min && n <= max;
}
function goodUrl(v) {
    return typeof v === "string" && v.length > 9 && v.length <= 2048
        && v.slice(0, 8) === "file:///" && v.indexOf("#") < 0
        && v.indexOf("?") < 0 && !/[\x00-\x1f\x7f]/.test(v);
}
function goodTitle(v) {
    return typeof v === "string" && v.length > 0 && v.length <= 160
        && !/[\/\\\x00-\x1f\x7f]/.test(v);
}
function kindMime(kind, mime) {
    return (kind === "image"
        && ["image/png", "image/jpeg", "image/webp"].indexOf(mime) >= 0)
        || (kind === "video"
        && ["video/mp4", "video/webm", "video/quicktime"].indexOf(mime) >= 0);
}
function goodAsset(v) {
    return exactly(v, ["id", "sourceUrl", "title", "kind",
                       "mime", "sizeBytes", "stamp", "addedAtMs"])
        && typeof v.id === "string" && /^m[1-9][0-9]*$/.test(v.id)
        && integer(Number(v.id.slice(1)), 1, MAX_SEQUENCE)
        && goodUrl(v.sourceUrl) && goodTitle(v.title)
        && kindMime(v.kind, v.mime)
        && integer(v.sizeBytes, 1, v.kind === "image" ? IMAGE_LIMIT : VIDEO_LIMIT)
        && typeof v.stamp === "string" && /^[0-9a-f]{64}$/.test(v.stamp)
        && integer(v.addedAtMs, 1, Number.MAX_SAFE_INTEGER);
}
function goodLink(v) {
    return exactly(v, ["draftId", "assetId"])
        && typeof v.draftId === "string" && /^d[1-9][0-9]*$/.test(v.draftId)
        && typeof v.assetId === "string" && /^m[1-9][0-9]*$/.test(v.assetId);
}
function validate(doc) {
    if (!plain(doc)) return {ok:false, reason:"INVALID_DOCUMENT"};
    if (doc.version !== VERSION) return {ok:false, reason:"UNSUPPORTED_VERSION"};
    if (!exactly(doc, ["version", "nextId", "assets", "links"]))
        return {ok:false, reason:"UNKNOWN_FIELDS"};
    if (!integer(doc.nextId, 1, MAX_SEQUENCE))
        return {ok:false, reason:"INVALID_SEQUENCE"};
    if (!Array.isArray(doc.assets) || doc.assets.length > MAX_ASSETS
            || !Array.isArray(doc.links) || doc.links.length > MAX_LINKS)
        return {ok:false, reason:"CAPACITY_EXCEEDED"};
    var ids = {}, paths = {}, maxId = 0;
    for (var i = 0; i < doc.assets.length; i++) {
        var a = doc.assets[i];
        if (!goodAsset(a)) return {ok:false, reason:"INVALID_MEDIA_RECORD"};
        if (Object.prototype.hasOwnProperty.call(ids, a.id))
            return {ok:false, reason:"DUPLICATE_MEDIA_ID"};
        if (Object.prototype.hasOwnProperty.call(paths, a.sourceUrl))
            return {ok:false, reason:"DUPLICATE_SOURCE"};
        ids[a.id] = true;
        paths[a.sourceUrl] = true;
        maxId = Math.max(maxId, Number(a.id.slice(1)));
    }
    if (maxId >= doc.nextId) return {ok:false, reason:"SEQUENCE_REWIND"};
    var pairs = {}, counts = {};
    for (var j = 0; j < doc.links.length; j++) {
        var link = doc.links[j];
        if (!goodLink(link) || !Object.prototype.hasOwnProperty.call(ids, link.assetId))
            return {ok:false, reason:"INVALID_MEDIA_LINK"};
        var key = link.draftId + ":" + link.assetId;
        if (Object.prototype.hasOwnProperty.call(pairs, key))
            return {ok:false, reason:"DUPLICATE_MEDIA_LINK"};
        pairs[key] = true;
        counts[link.draftId] = (counts[link.draftId] || 0) + 1;
        if (counts[link.draftId] > MAX_PER_DRAFT)
            return {ok:false, reason:"TOO_MANY_ATTACHMENTS"};
    }
    if (JSON.stringify(doc).length > MAX_DOCUMENT)
        return {ok:false, reason:"DOCUMENT_TOO_LARGE"};
    return {ok:true, reason:""};
}
function parse(raw) {
    if (typeof raw !== "string" || raw.length > MAX_DOCUMENT)
        return {ok:false, reason:"INVALID_SOURCE"};
    var document;
    try { document = JSON.parse(raw); }
    catch (e) { return {ok:false, reason:"MALFORMED_JSON"}; }
    var result = validate(document);
    return result.ok ? {ok:true, document:document} : result;
}
function copy(doc) {
    return {version:VERSION, nextId:doc.nextId,
        assets:doc.assets.map(function(a) {
            return {id:a.id, sourceUrl:a.sourceUrl, title:a.title,
                kind:a.kind, mime:a.mime, sizeBytes:a.sizeBytes,
                stamp:a.stamp, addedAtMs:a.addedAtMs};
        }),
        links:doc.links.map(function(l) {
            return {draftId:l.draftId, assetId:l.assetId};
        })};
}
function register(doc, info, now) {
    var valid = validate(doc);
    if (!valid.ok) return valid;
    if (!exactly(info, ["sourceUrl", "title", "kind", "mime", "sizeBytes", "stamp"]))
        return {ok:false, reason:"INVALID_PROBE_RECEIPT"};
    var candidate = {id:"m1", sourceUrl:info.sourceUrl, title:info.title,
        kind:info.kind, mime:info.mime, sizeBytes:info.sizeBytes,
        stamp:info.stamp, addedAtMs:now};
    if (!goodAsset(candidate)) return {ok:false, reason:"INVALID_PROBE_RECEIPT"};
    for (var i = 0; i < doc.assets.length; i++) {
        if (doc.assets[i].sourceUrl === info.sourceUrl) {
            return doc.assets[i].stamp === info.stamp
                ? {ok:true, unchanged:true, assetId:doc.assets[i].id}
                : {ok:false, reason:"SOURCE_CHANGED_REVIEW_REQUIRED"};
        }
    }
    if (doc.assets.length >= MAX_ASSETS || doc.nextId >= MAX_SEQUENCE)
        return {ok:false, reason:"MEDIA_LIMIT"};
    var result = copy(doc);
    candidate.id = "m" + result.nextId++;
    result.assets.push(candidate);
    var check = validate(result);
    return check.ok ? {ok:true, document:result, assetId:candidate.id} : check;
}
function attach(doc, draftId, assetId) {
    var check = validate(doc);
    if (!check.ok) return check;
    if (typeof draftId !== "string" || !/^d[1-9][0-9]*$/.test(draftId))
        return {ok:false, reason:"DRAFT_MUST_BE_SAVED"};
    if (!doc.assets.some(function(a) { return a.id === assetId; }))
        return {ok:false, reason:"UNKNOWN_MEDIA"};
    var matches = doc.links.filter(function(l) { return l.draftId === draftId; });
    if (matches.some(function(l) { return l.assetId === assetId; }))
        return {ok:false, reason:"ALREADY_ATTACHED"};
    if (matches.length >= MAX_PER_DRAFT || doc.links.length >= MAX_LINKS)
        return {ok:false, reason:"ATTACHMENT_LIMIT"};
    var result = copy(doc);
    result.links.push({draftId:draftId, assetId:assetId});
    return {ok:true, document:result, draftId:draftId, assetId:assetId};
}
function detach(doc, draftId, assetId) {
    var check = validate(doc);
    if (!check.ok) return check;
    if (!doc.links.some(function(l) {
        return l.draftId === draftId && l.assetId === assetId;
    })) return {ok:false, reason:"NO_ATTACHMENT"};
    var result = copy(doc);
    result.links = result.links.filter(function(l) {
        return l.draftId !== draftId || l.assetId !== assetId;
    });
    return {ok:true, document:result, draftId:draftId, assetId:assetId};
}
function view(state, doc, error) {
    var valid = validate(doc);
    var ready = valid.ok && (state === "ready" || state === "empty");
    return {state:state, error:error || "", writable:ready,
        assets:valid.ok ? doc.assets.map(function(a) { return Object.assign({}, a); }) : [],
        links:valid.ok ? doc.links.map(function(l) { return Object.assign({}, l); }) : []};
}
