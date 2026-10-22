.pragma library

// Mail commands must be bound to a real, live sender callback or an
// authenticated mailbox adapter that supplies a stable message identity.
// Neither a notification title nor a website hostname identifies a message.
var operations = ["mark-read", "trash", "archive", "snooze", "spam", "star"];

function word(value) {
    return String(value === undefined || value === null ? "" : value).trim().toLowerCase();
}

function knownMailHost(value) {
    const host = word(value);
    return [
        "mail.proton.me", "mail.protonmail.com", "protonmail.com",
        "mail.google.com", "gmail.com", "mail.yahoo.com",
        "outlook.live.com", "outlook.office.com", "outlook.office365.com"
    ].indexOf(host) !== -1;
}

function knownMailClient(source, sourceId) {
    const text = word(source) + " " + word(sourceId);
    const words = text.split(/[^a-z0-9]+/);
    return ["thunderbird", "betterbird", "geary", "evolution",
            "kmail", "mailspring", "protonmail", "gmail", "outlook"]
        .some(function(name) { return words.indexOf(name) !== -1; });
}

function isEmail(entry) {
    if (!entry)
        return false;
    const category = word(entry.category);
    return category === "email" || category.startsWith("email.")
        || knownMailHost(entry.websiteHost)
        || knownMailClient(entry.source, entry.sourceId);
}

// Only narrow, literal advertised sender actions. No keyword searches in
// messages, no guessed message IDs, and never interpret "delete" as Trash
// (it could mean permanent deletion).
function operationFor(identifier, label) {
    const id = word(identifier).replace(/[_-]/g, " ");
    const name = word(label).replace(/[_-]/g, " ");
    const groups = [
        ["mark-read", ["mark as read", "mark read", "markread", "markreadmessage"]],
        ["trash", ["trash", "move to trash", "move to bin"]],
        ["archive", ["archive", "move to archive"]],
        ["snooze", ["snooze", "snooze email", "snooze message"]],
        ["spam", ["spam", "mark as spam", "report spam", "move to spam"]],
        ["star", ["star", "add star", "mark starred", "favorite email"]]
    ];
    for (let i = 0; i < groups.length; i++) {
        const aliases = groups[i][1];
        if (aliases.indexOf(id) !== -1 || aliases.indexOf(name) !== -1)
            return groups[i][0];
    }
    return "";
}

function availableActions(entry, nativeActions) {
    if (!isEmail(entry) || !nativeActions)
        return [];
    const found = {};
    const limit = Math.min(32, Number(nativeActions.length || 0));
    for (let i = 0; i < limit; i++) {
        const action = nativeActions[i];
        if (!action)
            continue;
        const identifier = String(action.identifier || "");
        if (identifier === "" || identifier === "default")
            continue;
        const kind = operationFor(identifier, action.text);
        if (kind !== "" && !found[kind])
            found[kind] = { "kind": kind, "identifier": identifier };
    }
    const matches = [];
    for (let i = 0; i < operations.length; i++)
        if (found[operations[i]])
            matches.push(found[operations[i]]);
    return matches;
}
