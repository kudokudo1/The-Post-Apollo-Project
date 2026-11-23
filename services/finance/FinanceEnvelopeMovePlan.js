.pragma library

// FinanceW Simple M2a: read-only, two-envelope budget movement preview.
// This is NOT a bank transfer and NEVER writes Actual, disk, or credentials.
// A future operation must use an independent atomic/recoverable write guard.
var MAX_CENTS = 99999999999;
function boundedCents(n) {
    return Number.isSafeInteger(n) && Math.abs(n)<=MAX_CENTS;
}
function parseMoveCents(text) {
    const raw=String(text===undefined || text===null ? "" : text).trim();
    if(!/^\d{1,9}(?:\.\d{1,2})?$/.test(raw))return null;
    const parts=raw.split(".");
    const cents=Number(parts[0])*100
        + Number((parts[1]||"").padEnd(2,"0"));
    return boundedCents(cents) && cents>0 ? cents : null;
}
function previewEnvelopeMove(snapshot,fromId,toId,amountText) {
    if(!snapshot || snapshot.schemaVersion!==1
            || snapshot.source!=="actual-budget" || snapshot.readOnly!==true
            || typeof snapshot.sourceKey!=="string"
            || !/^[a-f0-9]{64}$/.test(snapshot.sourceKey)
            || !/^(19|20)\d{2}-(0[1-9]|1[0-2])$/.test(snapshot.month||"")
            || !Array.isArray(snapshot.categories)
            || !boundedCents(snapshot.toBudgetCents))
        return {ok:false,reason:"AUTHENTICATED BUDGET REQUIRED"};
    if(typeof fromId!=="string" || !fromId
            || typeof toId!=="string" || !toId)
        return {ok:false,reason:"SELECT TWO ENVELOPES"};
    if(fromId===toId)
        return {ok:false,reason:"CHOOSE DIFFERENT ENVELOPES"};

    // Refuse ambiguous IDs rather than guessing which budget row to change.
    const fromRows=snapshot.categories.filter(function(c) {
        return c && c.id===fromId;
    });
    const toRows=snapshot.categories.filter(function(c) {
        return c && c.id===toId;
    });
    if(fromRows.length!==1 || toRows.length!==1)
        return {ok:false,reason:"ENVELOPE NOT UNIQUE OR UNAVAILABLE"};
    const from=fromRows[0],to=toRows[0];
    if(![from,to].every(function(c){
        return typeof c.id==="string"
            && typeof c.name==="string" && !!c.name.trim()
            && typeof c.groupId==="string" && !!c.groupId
            && boundedCents(c.budgetedCents)
            && boundedCents(c.availableCents);
    }))return {ok:false,reason:"INVALID ENVELOPE BALANCES"};

    const cents=parseMoveCents(amountText);
    if(cents===null)
        return {ok:false,reason:"ENTER A POSITIVE MOVE AMOUNT"};
    // M2a deliberately refuses negative source-month allocations. A future
    // Actual-parity feature may extend this after an atomic writer review.
    if(cents>from.availableCents)
        return {ok:false,reason:"NOT ENOUGH AVAILABLE IN SOURCE ENVELOPE"};
    if(cents>from.budgetedCents)
        return {ok:false,reason:"MOVE EXCEEDS THIS MONTH'S SOURCE ASSIGNMENT"};

    const fromSetAfter=from.budgetedCents-cents;
    const toSetAfter=to.budgetedCents+cents;
    const fromAvailableAfter=from.availableCents-cents;
    const toAvailableAfter=to.availableCents+cents;
    if(![fromSetAfter,toSetAfter,fromAvailableAfter,toAvailableAfter]
           .every(boundedCents))
        return {ok:false,reason:"AMOUNT EXCEEDS SAFE FINANCIAL RANGE"};
    if(fromSetAfter<0 || fromAvailableAfter<0)
        return {ok:false,reason:"SOURCE ENVELOPE WOULD BE NEGATIVE"};
    if(from.budgetedCents+to.budgetedCents
           !==fromSetAfter+toSetAfter
           || from.availableCents+to.availableCents
           !==fromAvailableAfter+toAvailableAfter)
        return {ok:false,reason:"MOVE CONSERVATION FAILED"};

    return {
        ok:true,savesToActual:false,requiresAtomicWriter:true,
        sourceKey:snapshot.sourceKey,month:snapshot.month,
        fromCategoryId:from.id,fromName:from.name,fromGroupId:from.groupId,
        toCategoryId:to.id,toName:to.name,toGroupId:to.groupId,
        moveCents:cents,
        fromBudgetedBeforeCents:from.budgetedCents,
        fromBudgetedAfterCents:fromSetAfter,
        toBudgetedBeforeCents:to.budgetedCents,
        toBudgetedAfterCents:toSetAfter,
        fromAvailableBeforeCents:from.availableCents,
        fromAvailableAfterCents:fromAvailableAfter,
        toAvailableBeforeCents:to.availableCents,
        toAvailableAfterCents:toAvailableAfter,
        toBudgetBeforeCents:snapshot.toBudgetCents,
        toBudgetAfterCents:snapshot.toBudgetCents,
        destinationRemainsOverspent:toAvailableAfter<0
    };
}
