// PHONE P32 // Pure, read-only projection of an already authorized in-memory
// Social PHONE snapshot. NEVER calls a provider, joins contact IDs to SMS,
// persists queries, changes Personal permissions, or claims a full phonebook.
// The current legacy BlueFerry 0.9.1 snapshot can contain only 100 contacts.

function _text(value) {
    return typeof value === "string" ? value : "";
}

function _fold(value) {
    return _text(value).trim().toLocaleLowerCase();
}

function _includes(value, query) {
    return _fold(value).indexOf(query) !== -1;
}

function filterConversations(conversations, query) {
    if (!Array.isArray(conversations))
        return [];
    var needle = _fold(query).slice(0, 128);
    var out = [];
    for (var i = 0; i < conversations.length; i++) {
        var row = conversations[i];
        if (!row || typeof row !== "object")
            continue;
        if (!needle || _includes(row.displayNameInProfile, needle)
                || _includes(row.nickname, needle)
                || _includes(row.lastMessage, needle))
            out.push(row);
    }
    return out;
}

function filterContacts(contacts, query) {
    if (!Array.isArray(contacts))
        return [];
    var needle = _fold(query).slice(0, 128);
    var out = [];
    for (var i = 0; i < contacts.length; i++) {
        var card = contacts[i];
        if (!card || typeof card !== "object")
            continue;
        if (!needle || _includes(card.displayNameInProfile, needle)
                || _includes(card.organization, needle)
                || _includes(card.primary, needle))
            out.push(card);
    }
    return out;
}

function sectionLetter(name) {
    var first = _text(name).trim().charAt(0).toUpperCase();
    return /^[A-Z]$/.test(first) ? first : "#";
}

function contactDirectoryRows(contacts) {
    // Do not sort or alter the provider array. Construct a list-only view with
    // headings. Equal names use their original snapshot order deterministically.
    if (!Array.isArray(contacts))
        return [];
    var entries = [];
    for (var i = 0; i < contacts.length; i++) {
        var card = contacts[i];
        if (!card || typeof card !== "object")
            continue;
        var name = _text(card.displayNameInProfile) || "Unnamed contact";
        entries.push({
            card: card, originalIndex: i, name: name,
            letter: sectionLetter(name), key: _fold(name)
        });
    }
    entries.sort(function(a, b) {
        if (a.letter !== b.letter)
            return a.letter < b.letter ? -1 : 1;
        if (a.key !== b.key)
            return a.key < b.key ? -1 : 1;
        return a.originalIndex - b.originalIndex;
    });
    var rows = [], previous = null;
    for (var j = 0; j < entries.length; j++) {
        var item = entries[j];
        if (item.letter !== previous) {
            previous = item.letter;
            rows.push({ kind: "heading", letter: previous });
        }
        rows.push({ kind: "contact", card: item.card });
    }
    return rows;
}
