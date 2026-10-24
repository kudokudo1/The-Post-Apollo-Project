// SEC Evidence Desk M4. Pure QML-compatible JavaScript, no IO.
// The desk compares disclosed facts; it does NOT infer causation or signals.
function filterFilings(rows, mode) {
    if (!Array.isArray(rows)) return [];
    if (mode === "insider")
        return rows.filter(function(row) { return row.form === "4" || row.form === "4/A"; });
    if (mode === "events")
        return rows.filter(function(row) { return row.form === "8-K" || row.form === "8-K/A"; });
    if (mode === "owners")
        return rows.filter(function(row) { return /^SC 13[DG](\/A)?$/.test(row.form); });
    if (mode === "reports")
        return rows.filter(function(row) { return /^10-[QK](\/A)?$/.test(row.form); });
    return rows.slice();
}

function filterTransactions(rows, mode) {
    if (!Array.isArray(rows)) return [];
    if (mode === "all") return rows.slice();
    if (mode === "other")
        return rows.filter(function(row) {
            return ["P", "S", "A", "M"].indexOf(row.code) < 0;
        });
    if (["P", "S", "A", "M"].indexOf(mode) < 0) return [];
    return rows.filter(function(row) { return row.code === mode; });
}

function brief(document) {
    if (!document || (document.kind !== "form4" && document.kind !== "form8k"))
        return null;
    if (document.kind === "form4") {
        if (!Array.isArray(document.transactions) || document.transactions.length > 20)
            return null;
        var counts = {P: 0, S: 0, A: 0, M: 0, other: 0};
        document.transactions.forEach(function(tx) {
            if (Object.prototype.hasOwnProperty.call(counts, tx.code))
                counts[tx.code]++;
            else
                counts.other++;
        });
        var names = Array.isArray(document.owners)
            ? document.owners.filter(function(n) { return typeof n === "string"; }).slice(0, 8)
            : [];
        var rows = document.transactions.slice(0, 3).map(function(tx) {
            return (tx.code || "?") + " // " + (tx.date || "DATE N/A")
                + " // SHARES " + (tx.shares || "N/A")
                + " // PRICE " + (tx.pricePerShare || "N/A");
        });
        return {
            label: "FORM 4 // NON-DERIVATIVE",
            summary: "P " + counts.P + "  S " + counts.S + "  A " + counts.A
                + "  M " + counts.M + "  OTHER " + counts.other,
            secondary: names.length ? "OWNERS: " + names.join(", ") : "OWNERS NOT REPORTED",
            excerpts: rows,
            caveat: "Code counts reflect only up to 20 inspected non-derivative rows."
        };
    }
    if (!Array.isArray(document.events) || document.events.length > 12)
        return null;
    var events = document.events.slice(0, 6).map(function(event) {
        return "ITEM " + event.item + " // " + event.category
            + " [" + event.source + "]";
    });
    return {
        label: "FORM 8-K // ITEMS",
        summary: document.events.length + " ITEM(S) IN INSPECTED DOCUMENT",
        secondary: "CLASSIFICATIONS AND NEAR-HEADING EVIDENCE ONLY",
        excerpts: events,
        caveat: "8-K items do not establish investment impact or completeness."
    };
}

function pinEvidence(existing, filing, document, cik) {
    if (!Array.isArray(existing) || !filing || !document || !/^\d{10}$/.test(cik)
            || document.cik !== cik || document.accession !== filing.accession
            || document.form !== filing.form || !/^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\//.test(document.documentUrl || ""))
        return null;
    if (!/^\d{10}-\d{2}-\d{6}$/.test(document.accession || ""))
        return null;
    var facts = brief(document);
    if (!facts) return null;
    var pinned = existing.filter(function(row) {
        return row.cik === cik && row.accession !== document.accession;
    });
    pinned.push({
        cik: cik, accession: document.accession, form: document.form,
        filedAt: filing.filedAt, documentUrl: document.documentUrl,
        retrievedAt: document.retrievedAt,
        facts: facts
    });
    // At most two documents, newest pin replaces the oldest.
    return pinned.slice(-2);
}
