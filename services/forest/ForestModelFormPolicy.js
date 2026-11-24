// ForestW local presentation choices only. No runtime binding, inference,
// resource or permission authority. Historical Model Form is independent of
// reasoning; AUTO is a routing policy, never an executable model.
function emptyEquipment(count) {
    var result = [];
    for (var i = 0; i < count; i++)
        result.push({ small: "", big: "", form: "AUTO" });
    return result;
}

function validForm(form) {
    return form === "AUTO" || form === "SMALL" || form === "BIG";
}

function validTree(choices, tree) {
    return Array.isArray(choices) && Number.isInteger(tree)
        && tree >= 0 && tree < choices.length && !!choices[tree];
}

function installed(status, models, name) {
    if (status !== "REACHABLE" || !Array.isArray(models)
            || typeof name !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/.test(name))
        return false;
    return models.some(function(record) { return record && record.name === name; });
}

function equip(choices, tree, slot, name, status, models) {
    if (!validTree(choices, tree) || (slot !== "small" && slot !== "big")
            || !installed(status, models, name))
        return null;
    var next = choices.slice();
    var old = choices[tree];
    next[tree] = {small: old.small, big: old.big, form: old.form};
    next[tree][slot] = name;
    return next;
}

function clearSlot(choices, tree, slot) {
    if (!validTree(choices, tree) || (slot !== "small" && slot !== "big"))
        return null;
    var next = choices.slice();
    var old = choices[tree];
    next[tree] = {small: old.small, big: old.big, form: old.form};
    next[tree][slot] = "";
    return next;
}

function chooseForm(choices, tree, form) {
    if (!validTree(choices, tree) || !validForm(form))
        return null;
    var next = choices.slice();
    var old = choices[tree];
    next[tree] = {small: old.small, big: old.big, form: form};
    return next;
}

function selectedModel(choice, status, models) {
    if (!choice || !validForm(choice.form) || choice.form === "AUTO")
        return "";
    var name = choice.form === "SMALL" ? choice.small : choice.big;
    return installed(status, models, name) ? name : "";
}

function slotLabel(choice, slot, status, models) {
    if (!choice || (slot !== "small" && slot !== "big") || !choice[slot])
        return "EMPTY";
    var name = choice[slot];
    if (status !== "REACHABLE") return name + " // UNVERIFIED";
    return installed(status, models, name) ? name : name + " // NOT FOUND";
}
