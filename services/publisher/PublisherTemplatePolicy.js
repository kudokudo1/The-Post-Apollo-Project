.pragma library

// P1.3 pure, deterministic template/fact substitution. No AI, network,
// authentication or publishing. A "locked fact" is copied VERBATIM on render,
// not an external certification that the underlying business claim is true.
var VERSION = 1;
var MAX_TEMPLATES = 80;
var MAX_PATTERN = 5000;
var MAX_OUTPUT = 10000;
var MAX_FACTS = 12;
var MAX_FACT_VALUE = 480;
var MAX_SOURCE = 1100000;
var MAX_SEQUENCE = 1000000000;
var CATEGORIES = ["recruitment", "resource", "announcement", "creator"];
var TOKEN = /\{\{([a-z][a-z0-9_]{0,31})\}\}/g;

function emptyDocument() {
    return {version:VERSION, nextId:1, templates:[]};
}
function plain(v) {
    return v !== null && typeof v === "object" && !Array.isArray(v)
        && Object.prototype.toString.call(v) === "[object Object]";
}
function exactly(v, fields) {
    if (!plain(v)) return false;
    var actual = Object.keys(v).sort(), wanted = fields.slice().sort();
    return actual.length === wanted.length && actual.every(function(x, i) {
        return x === wanted[i];
    });
}
function integer(n, low, high) {
    return typeof n === "number" && isFinite(n) && Math.floor(n) === n
        && n >= low && n <= high;
}
function safeText(s, max, allowNewlines) {
    if (typeof s !== "string" || s.length < 1 || s.length > max)
        return false;
    if (allowNewlines) return !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(s);
    return !/[\x00-\x1f\x7f]/.test(s);
}
function safeName(s) {
    return safeText(s, 100, false) && s.trim() === s;
}
function safeLanguage(s) {
    return typeof s === "string" && /^[a-z]{2,3}(?:-[A-Z]{2})?$/.test(s);
}
function safeCategory(s) { return CATEGORIES.indexOf(s) >= 0; }
function safeKey(s) {
    return typeof s === "string" && /^[a-z][a-z0-9_]{0,31}$/.test(s);
}
function safeFact(v) {
    return exactly(v, ["key", "value"]) && safeKey(v.key)
        && safeText(v.value, MAX_FACT_VALUE, false)
        && v.value.trim() === v.value
        && v.value.indexOf("{{") === -1 && v.value.indexOf("}}") === -1;
}
function safeFacts(facts) {
    if (!Array.isArray(facts) || facts.length > MAX_FACTS) return false;
    var keys = {};
    for (var i = 0; i < facts.length; i++) {
        var f = facts[i];
        if (!safeFact(f) || Object.prototype.hasOwnProperty.call(keys, f.key))
            return false;
        keys[f.key] = true;
    }
    return true;
}
function requiredKeys(category) {
    if (category === "recruitment")
        return ["role", "location", "apply_url"];
    if (category === "resource")
        return ["resource", "contact"];
    return [];
}
function render(pattern, facts, category) {
    if (!safeText(pattern, MAX_PATTERN, true)
            || !safeFacts(facts) || !safeCategory(category))
        return {ok:false, reason:"INVALID_TEMPLATE"};
    var lookup = {}, seen = {};
    for (var j = 0; j < facts.length; j++)
        lookup[facts[j].key] = facts[j].value;
    var required = requiredKeys(category);
    for (var k = 0; k < required.length; k++) {
        if (!Object.prototype.hasOwnProperty.call(lookup, required[k]))
            return {ok:false, reason:"REQUIRED_FACT_MISSING"};
    }
    // Reject malformed tokens and unmatched braces: no silent partial expansion.
    var stripped = pattern.replace(TOKEN, "");
    if (stripped.indexOf("{{") >= 0 || stripped.indexOf("}}") >= 0)
        return {ok:false, reason:"MALFORMED_PLACEHOLDER"};
    var missing = false;
    var expanded = pattern.replace(TOKEN, function(match, key) {
        seen[key] = true;
        if (!Object.prototype.hasOwnProperty.call(lookup, key)) {
            missing = true;
            return match;
        }
        return lookup[key];
    });
    if (missing) return {ok:false, reason:"UNBOUND_PLACEHOLDER"};
    for (var m = 0; m < facts.length; m++) {
        if (!seen[facts[m].key])
            return {ok:false, reason:"LOCKED_FACT_NOT_USED"};
    }
    if (expanded.length > MAX_OUTPUT)
        return {ok:false, reason:"OUTPUT_TOO_LARGE"};
    return {ok:true, body:expanded, facts:facts.length};
}
function parseFactLines(raw) {
    if (typeof raw !== "string" || raw.length > 10000)
        return {ok:false, reason:"INVALID_FACT_INPUT"};
    var lines = raw.split(/\r?\n/), result = [], seen = {};
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (line === "") continue;
        var pos = line.indexOf("=");
        if (pos < 1) return {ok:false, reason:"FACT_FORMAT_KEY_EQUALS_VALUE"};
        var key = line.slice(0, pos).trim();
        var value = line.slice(pos + 1).trim();
        if (!safeKey(key) || !safeText(value, MAX_FACT_VALUE, false)
                || value.indexOf("{{") >= 0 || value.indexOf("}}") >= 0)
            return {ok:false, reason:"INVALID_FACT"};
        if (Object.prototype.hasOwnProperty.call(seen, key))
            return {ok:false, reason:"DUPLICATE_FACT_KEY"};
        seen[key] = true;
        result.push({key:key, value:value});
        if (result.length > MAX_FACTS)
            return {ok:false, reason:"TOO_MANY_FACTS"};
    }
    return {ok:true, facts:result};
}
function factLines(facts) {
    return facts.map(function(f) { return f.key + " = " + f.value; }).join("\n");
}
function validateTemplate(t) {
    if (!exactly(t, ["id","name","category","language","pattern",
                     "facts","createdAtMs","updatedAtMs"])
            || typeof t.id !== "string" || !/^p[1-9][0-9]*$/.test(t.id)
            || !integer(Number(t.id.slice(1)), 1, MAX_SEQUENCE)
            || !safeName(t.name) || !safeCategory(t.category)
            || !safeLanguage(t.language) || !safeFacts(t.facts)
            || !integer(t.createdAtMs, 1, Number.MAX_SAFE_INTEGER)
            || !integer(t.updatedAtMs, t.createdAtMs, Number.MAX_SAFE_INTEGER))
        return {ok:false, reason:"INVALID_TEMPLATE_RECORD"};
    var rendered = render(t.pattern, t.facts, t.category);
    return rendered.ok ? {ok:true, reason:""} : rendered;
}
function validate(doc) {
    if (!plain(doc)) return {ok:false, reason:"INVALID_DOCUMENT"};
    if (doc.version !== VERSION) return {ok:false, reason:"UNSUPPORTED_VERSION"};
    if (!exactly(doc, ["version","nextId","templates"]))
        return {ok:false, reason:"UNKNOWN_FIELDS"};
    if (!integer(doc.nextId, 1, MAX_SEQUENCE))
        return {ok:false, reason:"INVALID_SEQUENCE"};
    if (!Array.isArray(doc.templates) || doc.templates.length > MAX_TEMPLATES)
        return {ok:false, reason:"TOO_MANY_TEMPLATES"};
    var ids = {}, maxId = 0;
    for (var i = 0; i < doc.templates.length; i++) {
        var t = doc.templates[i], result = validateTemplate(t);
        if (!result.ok) return result;
        if (Object.prototype.hasOwnProperty.call(ids, t.id))
            return {ok:false, reason:"DUPLICATE_TEMPLATE_ID"};
        ids[t.id] = true;
        maxId = Math.max(maxId, Number(t.id.slice(1)));
    }
    if (maxId >= doc.nextId) return {ok:false, reason:"SEQUENCE_REWIND"};
    if (JSON.stringify(doc).length > MAX_SOURCE)
        return {ok:false, reason:"DOCUMENT_TOO_LARGE"};
    return {ok:true, reason:""};
}
function parse(raw) {
    if (typeof raw !== "string" || raw.length > MAX_SOURCE)
        return {ok:false, reason:"INVALID_SOURCE"};
    var doc;
    try { doc = JSON.parse(raw); }
    catch (e) { return {ok:false, reason:"MALFORMED_JSON"}; }
    var result = validate(doc);
    return result.ok ? {ok:true, document:doc} : result;
}
function copy(doc) {
    return {version:VERSION,nextId:doc.nextId,templates:doc.templates.map(function(t) {
        return {id:t.id,name:t.name,category:t.category,language:t.language,
                pattern:t.pattern, facts:t.facts.map(function(f) {
                    return {key:f.key,value:f.value};
                }), createdAtMs:t.createdAtMs,updatedAtMs:t.updatedAtMs};
    })};
}
function save(doc, id, name, category, language, pattern, facts, now) {
    var current = validate(doc);
    if (!current.ok) return current;
    if (!safeName(name) || !safeCategory(category) || !safeLanguage(language)
            || !integer(now, 1, Number.MAX_SAFE_INTEGER) || typeof id !== "string")
        return {ok:false, reason:"INVALID_TEMPLATE_INPUT"};
    var output = render(pattern, facts, category);
    if (!output.ok) return output;
    var next = copy(doc);
    if (id === "") {
        if (next.templates.length >= MAX_TEMPLATES || next.nextId >= MAX_SEQUENCE)
            return {ok:false, reason:"TEMPLATE_LIMIT"};
        id = "p" + next.nextId++;
        next.templates.push({id:id,name:name,category:category,language:language,
                             pattern:pattern,facts:facts.map(function(f) {
                                 return {key:f.key,value:f.value};
                             }),createdAtMs:now,updatedAtMs:now});
    } else {
        var target = next.templates.filter(function(t) { return t.id === id; })[0];
        if (!target) return {ok:false, reason:"UNKNOWN_TEMPLATE"};
        if (now < target.updatedAtMs) return {ok:false, reason:"STALE_CLOCK"};
        target.name = name;
        target.category = category;
        target.language = language;
        target.pattern = pattern;
        target.facts = facts.map(function(f) {return {key:f.key,value:f.value};});
        target.updatedAtMs = now;
    }
    var result = validate(next);
    return result.ok ? {ok:true, document:next, templateId:id} : result;
}
function preview(name, category, language, pattern, lines) {
    if (!safeName(name) || !safeLanguage(language))
        return {ok:false, reason:"INVALID_TITLE_OR_LANGUAGE"};
    var parsed = parseFactLines(lines);
    if (!parsed.ok) return parsed;
    return render(pattern, parsed.facts, category);
}
function preset(category) {
    if (category === "recruitment")
        return {pattern:"We're hiring for {{role}} in {{location}}.\nApply: {{apply_url}}",
                facts:"role = \nlocation = \napply_url = "};
    if (category === "resource")
        return {pattern:"Resource available: {{resource}}.\nDetails: {{contact}}",
                facts:"resource = \ncontact = "};
    if (category === "announcement")
        return {pattern:"Announcement: {{headline}}\n{{details}}",
                facts:"headline = \ndetails = "};
    return {pattern:"New update: {{topic}}\n{{details}}",
            facts:"topic = \ndetails = "};
}
function view(state, doc, error) {
    var result = validate(doc);
    return {state:state,error:error || "",
        writable:result.ok && (state === "ready" || state === "empty"),
        templates:result.ok ? doc.templates.map(function(t) {
            return {id:t.id,name:t.name,category:t.category,language:t.language,
                    pattern:t.pattern,facts:t.facts.map(function(f) {
                        return {key:f.key,value:f.value};
                    }),createdAtMs:t.createdAtMs,updatedAtMs:t.updatedAtMs};
        }) : []};
}
