// Local display preferences only; never an authenticated model binding.
var TREE_KEYS = ["CHERRY", "MAPLE", "BRISTLECONE_PINE", "CEDAR", "MACINTOSH"];

function exact(value, keys) {
    return !!value && typeof value === "object" && !Array.isArray(value)
        && Object.keys(value).length === keys.length
        && keys.every(function(k) { return Object.prototype.hasOwnProperty.call(value, k); });
}
function validName(name) {
    return typeof name === "string" && (name === "" || /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(name));
}
function normalizeTrees(trees) {
    if (!exact(trees, TREE_KEYS)) return null;
    var result = {};
    for (var i = 0; i < TREE_KEYS.length; i++) {
        var k = TREE_KEYS[i], e = trees[k];
        if (!exact(e, ["small", "big", "form", "reasoning"]) ||
            !validName(e.small) || !validName(e.big) ||
            ["SMALL", "AUTO", "BIG"].indexOf(e.form) < 0 ||
            !Number.isInteger(e.reasoning) || e.reasoning < 0 || e.reasoning > 3)
            return null;
        result[k] = {small:e.small,big:e.big,form:e.form,reasoning:e.reasoning};
    }
    return result;
}
function pack(keys, equipment, reasoning) {
    if (!Array.isArray(keys) || !Array.isArray(equipment) || !Array.isArray(reasoning)
            || keys.length !== 5 || equipment.length !== 5 || reasoning.length !== 5)
        return null;
    var trees = {};
    for (var i = 0; i < keys.length; i++) {
        if (TREE_KEYS.indexOf(keys[i]) < 0 || trees[keys[i]] || !equipment[i]) return null;
        trees[keys[i]] = {small:equipment[i].small,big:equipment[i].big,
                         form:equipment[i].form,reasoning:reasoning[i]};
    }
    return normalizeTrees(trees);
}
function unpack(keys, trees) {
    var checked = normalizeTrees(trees);
    if (!checked || !Array.isArray(keys) || keys.length !== 5 ||
            TREE_KEYS.some(function(k) { return keys.indexOf(k) < 0; })) return null;
    return {
        equipment:keys.map(function(k) { var e=checked[k]; return {small:e.small,big:e.big,form:e.form}; }),
        reasoning:keys.map(function(k) { return checked[k].reasoning; })
    };
}
function parse(raw) {
    if (typeof raw !== "string" || raw.length > 8192) return null;
    var d;
    try { d=JSON.parse(raw); } catch(e) { return null; }
    if (!exact(d, ["source","production_authority","version","revision","trees"]) ||
        d.source !== "FORESTW_LOCAL_UI_PREFERENCES" || d.production_authority !== false ||
        d.version !== 1 || !Number.isSafeInteger(d.revision) || d.revision < 0) return null;
    var trees=normalizeTrees(d.trees);
    if (!trees) return null;
    if (d.revision === 0 && TREE_KEYS.some(function(k) {
        var e=trees[k]; return e.small!=="" || e.big!=="" || e.form!=="AUTO" || e.reasoning!==0;
    })) return null;
    return {revision:d.revision,trees:trees};
}
function same(a,b) {
    var x=normalizeTrees(a),y=normalizeTrees(b);
    return !!x && !!y && JSON.stringify(x)===JSON.stringify(y);
}
