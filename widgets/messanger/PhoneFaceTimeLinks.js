// FaceTime link and Apple-device handoff formatting, QML-importable pure JS.
// No network, D-Bus, BlueFerry call, launch, account, storage or permissions.
// FaceTime invitation tokens are private capabilities: never log or persist.
//
// Only Apple's known HTTPS web-join origin and exact token shape may leave
// the explicit reviewed handoff UI. Do not map a number to a web invite.
function normalizeInvite(raw) {
    if (typeof raw !== "string" || raw.length > 2048)
        return "";
    var link = raw.trim();
    if (link.length < 35 || link.length > 2048)
        return "";
    // Keep the full invitation fragment unchanged: it contains the call key.
    // Reject credentials, query strings, deceptive hosts and redirections.
    var exact = /^https:\/\/facetime\.apple\.com\/join\/?#v=1&p=[A-Za-z0-9_+%/=-]{8,192}&k=[A-Za-z0-9_+%/=-]{8,192}$/;
    return exact.test(link) ? link : "";
}

function _phone(raw) {
    if (typeof raw !== "string" || raw.length > 40)
        return "";
    var trimmed = raw.trim();
    if (!/^[+]?[0-9 ()-]{3,40}$/.test(trimmed))
        return "";
    var digits = trimmed.replace(/[ ()-]/g, "");
    return /^[+]?[0-9]{3,18}$/.test(digits) ? digits : "";
}

function _email(raw) {
    if (typeof raw !== "string" || raw.length > 254)
        return "";
    var address = raw.trim();
    // Conservative ASCII email format only. Do not generate URI syntax with
    // embedded slash, colon, hash, question mark, whitespace or controls.
    if (!/^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/.test(address))
        return "";
    return address;
}

function appleDeviceLink(mode, card) {
    if ((mode !== "audio" && mode !== "video")
            || !card || card.hasAddressDetails !== true)
        return "";
    var numbers = card.phoneNumbers;
    var emails = card.emailAddresses;
    if (!Array.isArray(numbers) || !Array.isArray(emails)
            || numbers.length > 64 || emails.length > 64)
        return "";
    var target = "";
    // Only use an address actually reported in the current approved card.
    // No guessed recipient, ephemeral ID mapping or silent call initiation.
    for (var i = 0; i < numbers.length && target === ""; ++i)
        target = _phone(numbers[i]);
    for (var j = 0; j < emails.length && target === ""; ++j)
        target = _email(emails[j]);
    if (target === "")
        return "";
    return (mode === "audio" ? "facetime-audio:" : "facetime:") + target;
}

function supportMessage(mode) {
    if (mode === "audio")
        return "FaceTime Audio starts on an Apple device. You may select a Bluetooth audio route on the iPhone, but PHONE cannot verify FaceTime audio or control the call.";
    if (mode === "video")
        return "FaceTime Video starts on an Apple device. On Linux, joining an invited call in a compatible browser is possible; PHONE has no native FaceTime camera or call-control connection.";
    return "FaceTime connection not selected.";
}
