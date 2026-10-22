// Pure calculations for read-only FinanceW allocation previews.
// No Actual import, disk IO, or budget mutation. Qt script import and Node VM tests.
function parseAllocationCents(text) {
    const raw = String(text === undefined || text === null ? "" : text).trim();
    if (!/^\d{1,9}(?:\.\d{1,2})?$/.test(raw))
        return null;
    const parts = raw.split(".");
    const cents = Number(parts[0]) * 100
                + Number((parts[1] || "").padEnd(2, "0"));
    return Number.isSafeInteger(cents) ? cents : null;
}

function previewAllocation(snapshot, categoryId, targetText) {
    if (!snapshot || snapshot.schemaVersion !== 1
            || snapshot.source !== "actual-budget" || snapshot.readOnly !== true
            || typeof snapshot.sourceKey !== "string"
            || !/^[a-f0-9]{64}$/.test(snapshot.sourceKey)
            || !/^(19|20)\d{2}-(0[1-9]|1[0-2])$/.test(snapshot.month || "")
            || !Array.isArray(snapshot.categories)
            || !Number.isSafeInteger(snapshot.toBudgetCents))
        return {ok:false,reason:"SOURCE NOT READY"};

    const matches = snapshot.categories.filter(function(cat) {
        return cat && cat.id === categoryId;
    });
    if (matches.length !== 1 || typeof categoryId !== "string" || !categoryId)
        return {ok:false,reason:"CATEGORY UNAVAILABLE"};
    const category = matches[0];
    if (!Number.isSafeInteger(category.budgetedCents)
            || !Number.isSafeInteger(category.availableCents)
            || typeof category.name !== "string")
        return {ok:false,reason:"INVALID CATEGORY DATA"};

    const targetCents = parseAllocationCents(targetText);
    if (targetCents === null)
        return {ok:false,reason:"AMOUNT // 0.00 TO 999999999.99"};
    const deltaCents = targetCents - category.budgetedCents;
    const toBudgetAfterCents = snapshot.toBudgetCents - deltaCents;
    const categoryAvailableAfterCents = category.availableCents + deltaCents;
    if (![deltaCents,toBudgetAfterCents,categoryAvailableAfterCents]
            .every(Number.isSafeInteger))
        return {ok:false,reason:"AMOUNT EXCEEDS SAFE RANGE"};
    return {
        ok:true,
        categoryId:categoryId,
        categoryName:category.name,
        month:snapshot.month,
        sourceKey:snapshot.sourceKey,
        originalBudgetedCents:category.budgetedCents,
        targetBudgetedCents:targetCents,
        allocationChangeCents:deltaCents,
        originalAvailableCents:category.availableCents,
        categoryAvailableAfterCents:categoryAvailableAfterCents,
        toBudgetBeforeCents:snapshot.toBudgetCents,
        toBudgetAfterCents:toBudgetAfterCents,
        exceedsUnallocatedFunds:toBudgetAfterCents < 0,
        categoryRemainsOverspent:categoryAvailableAfterCents < 0
    };
}
