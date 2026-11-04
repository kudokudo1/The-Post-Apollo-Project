.pragma library

// Presentation geometry only. Same 1000×700 outer default as Weather Station,
// with Finance-style three-level controls. No service/data state is affected.
var levels = ["compact", "standard", "fullscreen"];

function normalize(level) {
    return levels.indexOf(level) >= 0 ? level : "standard";
}

function step(level, direction) {
    var index = levels.indexOf(normalize(level));
    return levels[Math.max(0, Math.min(levels.length-1,
                                      index + (direction < 0 ? -1 : 1)))];
}

function viewport(value, fallback) {
    var n=Number(value);
    return isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}

function frame(level, screenWidth, screenHeight, gutter, topInset, bottomGap) {
    var mode=normalize(level);
    var w=viewport(screenWidth,2560);
    var h=viewport(screenHeight,1440);
    var horizontal=Math.max(0,Math.floor(Number(gutter) || 0));
    var top=Math.max(0,Math.floor(Number(topInset) || 0));
    var bottom=Math.max(0,Math.floor(Number(bottomGap) || 0));
    var targetW=mode==="compact" ? 640 : mode==="standard" ? 1000 : w;
    var targetH=mode==="compact" ? 490 : mode==="standard" ? 700 : h;
    var outerWidth=Math.min(w,targetW);
    var outerHeight=Math.min(h,targetH);
    return {
        width:Math.max(1,outerWidth-2*horizontal),
        height:Math.max(1,outerHeight-top-bottom)
    };
}

function leftMargin(level,dockCenterX,screenWidth,panelWidth) {
    if (normalize(level)==="fullscreen") return 0;
    var room=Math.max(0,Number(screenWidth)-Number(panelWidth));
    var x=Number(dockCenterX)-Number(panelWidth)/2;
    return Math.max(0,Math.min(room,Math.round(isFinite(x)?x:0)));
}

function topMargin(level,chassisTopY,screenHeight,panelHeight,gutter) {
    if (normalize(level)==="fullscreen") return 0;
    var room=Math.max(0,Number(screenHeight)-Number(panelHeight));
    var y=Number(chassisTopY)-Number(gutter);
    return Math.max(0,Math.min(room,Math.round(isFinite(y)?y:0)));
}
