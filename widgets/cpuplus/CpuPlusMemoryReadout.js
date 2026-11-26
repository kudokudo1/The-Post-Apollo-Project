// Presentation-only grammar. Escape all input (including device names) before rich text.
function escapeText(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}
function format(s, ink, white) {
    const text = String(s);
    const tokens = text.match(/(?:[A-Za-z]+|[0-9]+|\s+|[^A-Za-z0-9\s]+)/g) || [];
    return tokens.map(t => {
        const neutral = /^(?:B|KiB|MiB|GiB|TiB|KB|MB|GB|TB|Hz|kHz|MHz|GHz|ms|s|ns|us|kB|MS|SEC|MIN|HRS|RPM|INT|RPT|W|V|A|°C|°F)$/.test(t) || /^[^A-Za-z0-9\s]+$/.test(t);
        return '<font color="'+(neutral?white:ink)+'">'+escapeText(t)+'</font>';
    }).join("");
}
