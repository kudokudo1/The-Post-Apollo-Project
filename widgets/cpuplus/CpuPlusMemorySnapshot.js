// Read-only Linux memory snapshot. All capacity values are KiB.
function parseSnapshot(raw) {
    if (typeof raw !== "string" || raw.length > 262144) return null;
    function metric(key) {
        const m = raw.match(new RegExp("^" + key + ":[ \\t]+(\\d+)[ \\t]+kB[ \\t]*$", "m"));
        return m ? Number(m[1]) : null;
    }
    const total = metric("MemTotal"), available = metric("MemAvailable");
    const swap = metric("SwapTotal"), free = metric("SwapFree");
    const some = raw.match(/^some avg10=(\d+(?:\.\d+)?) /m);
    const full = raw.match(/^full avg10=(\d+(?:\.\d+)?) /m);
    const swappiness = raw.match(/^(\d+)[ \t]*$/m);
    if ([total,available,swap,free].some(v => v === null || !Number.isSafeInteger(v))
            || total <= 0 || available > total || free > swap
            || !some || !full || Number(some[1]) > 100 || Number(full[1]) > 100
            || !swappiness || Number(swappiness[1]) > 200)
        return null;
    const rows = [];
    let active = false;
    for (const line of raw.split("\n")) {
        if (/^Filename\s+Type\s+Size\s+Used\s+Priority/.test(line)) { active = true; continue; }
        if (!active) continue;
        if (/^some /.test(line)) break;
        const m = line.trim().match(/^(\S+)\s+(partition|file)\s+(\d+)\s+(\d+)\s+(-?\d+)$/);
        if (!m) { if (line.trim()) return null; continue; }
        const size = Number(m[3]), used = Number(m[4]), priority = Number(m[5]);
        if (![size,used,priority].every(Number.isSafeInteger) || used > size) return null;
        rows.push({name:m[1], size:size, used:used, priority:priority,
                   kind:/^\/dev\/zram\d+$/.test(m[1]) ? "ZRAM" : "OTHER SWAP"});
    }
    if (!active) return null;
    return {total:total, available:available, swap:swap, free:free,
            some:Number(some[1]), full:Number(full[1]), swappiness:Number(swappiness[1]), rows:rows};
}
