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


// Diagnostic help vocabulary only. Explicit phrase rules take precedence over
// shorter words; ambiguous measurements inherit the observation subject.
// Unrecognized prose and punctuation stay white. No runtime markup is trusted.
function helpRules(subject) {
    const scope=String(subject).toUpperCase();
    const busy=scope==="GPU"?"omnitrix":scope==="CPU"?"orange":"yellow";
    const bytes=scope==="NETWORK"?"cyan":scope==="STORAGE"?"blue":scope==="SWAP"?"yellow":scope==="GPU"?"omnitrix":scope==="CPU"?"orange":scope==="MEMORY"?"magenta":"cyan";
    return [
        ["omnitrix", "host\\s+kernel|host\\s+operating\\s+system|kernel|GPU|DRM|VRAM|hwmon|temp1|graphics(?:\\s+cards?)?|driver(?:s)?"],
        ["orange", "host[\\s-]+apollo|post-apollo|host\\s+CPU|CPU|processor(?:s)?|process(?:es)?|census|frequency|aggregate\\s+capacity"],
        ["magenta", "host\\s+RAM|RAM|resident|proportional|private\\s+memory|memory(?!\\s+pressure)"],
        ["blue", "DISK\\s+I/O|physical\\s+disk|storage|files?|metadata|size|modification\\s+time|replacement|throughput|writes?|transactions?|whole-device|block\\s+devices?|partition(?:s)?"],
        ["cyan", "network|RX|TX|packets?|interfaces?|loopback|threads?|endpoints?"],
        ["yellow", "memory\\s+pressure|swap|zram|PSI|workflows?|queue|latency|traffic|pressure|unavailable|availability|budgets?|stress\\s+test|clock\\s+changes|capacity|policy|stall(?:s)?"],
        ["red", "errors?|drops?|faults?|fail(?:ed|ures?)?|crash(?:es)?|bugs?"],
        [busy,"busy"],
        [bytes,"bytes?"]
    ];
}
function helpTokens(value, subject) {
    const text=String(value), rules=helpRules(subject);
    const alternatives=rules.map(rule=>"("+rule[1]+")");
    const regex=new RegExp("\\b(?:"+alternatives.join("|")+")\\b","gi");
    const result=[];
    let offset=0, match;
    while ((match=regex.exec(text))!==null) {
        if(match.index>offset)result.push({text:text.slice(offset,match.index),ink:"white"});
        const rule=match.slice(1).findIndex(v=>v!==undefined);
        result.push({text:match[0],ink:rules[rule][0]});
        offset=regex.lastIndex;
    }
    if(offset<text.length)result.push({text:text.slice(offset),ink:"white"});
    return result;
}
function formatHelp(value, subject, palette) {
    // Whitespace and punctuation outside recognized phrases remain neutral.
    return helpTokens(value,subject).map(token=>
        '<font color="'+escapeText(palette[token.ink]||palette.white)+'">'+escapeText(token.text)+'</font>'
    ).join("");
}
