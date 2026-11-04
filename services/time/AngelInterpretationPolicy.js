.pragma library

// ANGEL M2 reference presentation. No journal writes, no passive network,
// no attribution of spiritual claims to measured astronomy or clock signals.
var MAX_DIGITS = 8;
var PROVIDER = "Astrology.com";
var SOURCE_ROOT = "https://www.astrology.com/numerology/angel-numbers/";

function validDigits(digits) {
    return typeof digits === "string"
           && digits.length >= 1 && digits.length <= MAX_DIGITS
           && !/[^0-9]/.test(digits);
}

function lookupEligible(digits) {
    // Provider has number-specific pages for short sequences. Do not infer
    // support for 5–8 digit IDs or silently strip leading zeroes.
    return validDigits(digits) && digits.length <= 4;
}

function lookupUrl(digits) {
    return lookupEligible(digits)
        ? SOURCE_ROOT + digits + "-meaning" : "";
}

function arithmeticReduction(digits) {
    if (!validDigits(digits)) return null;
    var sum = 0;
    for (var i = 0; i < digits.length; ++i)
        sum += Number(digits[i]);
    var root = sum;
    while (root >= 10) {
        var next = 0;
        while (root > 0) {
            next += root % 10;
            root = Math.floor(root / 10);
        }
        root = next;
    }
    return {sum: sum, digit: root};
}

function interpretResponse(raw, requested) {
    if (!lookupEligible(requested))
        return {ok: false, reason: "NO_SOURCE_FOR_LENGTH"};
    if (typeof raw !== "string" || raw.length === 0 || raw.length > 8192)
        return {ok: false, reason: "SOURCE_RESPONSE_INVALID"};
    var data;
    try { data = JSON.parse(raw); }
    catch (error) { return {ok: false, reason: "SOURCE_RESPONSE_INVALID"}; }
    if (!data || data.digits !== requested)
        return {ok: false, reason: "SOURCE_MISMATCH"};
    if (data.status !== "ready")
        return {ok: false, reason: String(data.status || "SOURCE_UNAVAILABLE").slice(0, 64)};
    if (data.provider !== PROVIDER || data.url !== lookupUrl(requested)
            || typeof data.section !== "string"
            || !/^Numerology meaning$/i.test(data.section)
            || typeof data.excerpt !== "string"
            || data.excerpt.length < 10 || data.excerpt.length > 250
            || /[\x00-\x1f\x7f]/.test(data.excerpt))
        return {ok: false, reason: "SOURCE_RESPONSE_INVALID"};
    return {
        ok: true,
        provider: PROVIDER,
        url: data.url,
        digits: data.digits,
        section: data.section,
        excerpt: data.excerpt
    };
}
