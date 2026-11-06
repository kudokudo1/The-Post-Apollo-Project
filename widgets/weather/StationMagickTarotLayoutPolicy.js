.pragma library

// M6i // Pure responsive layout model for the M6g/M6h Tarot workspace.
// This file chooses only sizes and positions for the existing cards.
// It never alters the 78-card source, reads local artwork or saves spreads.
var FORMAT="post-apollo.weather.magick-tarot-layout.m6i.v1";
function finite(n){return typeof n==="number" && isFinite(n);}
function clamp(n,low,high){return Math.max(low,Math.min(high,n));}
function spread(width,height,id) {
    if(!finite(width)||!finite(height)||width<180||height<260||
       ["one","three","five"].indexOf(id)<0)return null;
    var count=id==="one"?1:id==="three"?3:5,
        columns=count===1?1:3,rows=count===5?2:1,gap=7,
        usableHeight=Math.max(150,height-229);
    var slotWidth=count===1
        ? Math.min(width*0.57,260)
        : (width-gap*(columns-1))/columns;
    var ratioHeight=slotWidth*1.58;
    var cardHeight=count===5
        ? Math.max(68,Math.min(194,ratioHeight,
                                (usableHeight-gap)/2))
        : Math.max(126,Math.min(count===1?365:304,
                                ratioHeight,usableHeight));
    // The flow is centered for a single card; other spreads use equal
    // columns and two stable rows, not five near-unreadable thumbnails.
    return {format:FORMAT,count:count,columns:columns,rows:rows,gap:gap,
        slotWidth:slotWidth,cardHeight:cardHeight,
        contentHeight:rows*cardHeight+(rows-1)*gap,
        centered:count===1};
}
function catalog(width,height) {
    if(!finite(width)||!finite(height)||width<180||height<260)
        return null;
    var pagesize=height>=575?8:height>=450?7:6,
        gap=8,previewWidth=clamp(width*0.43,112,235);
    return {format:FORMAT,pageSize:pagesize,previewWidth:previewWidth,
        listWidth:Math.max(55,width-previewWidth-gap),
        rowHeight:height>=450?30:28,
        previewHeight:Math.min(302,Math.max(204,height-248)),
        gap:gap};
}
function inspect(width,height) {
    if(!finite(width)||!finite(height)||width<180||height<260)
        return null;
    var available=Math.max(150,height-125);
    var cardWidth=clamp(Math.min(width*0.52,available/1.52),110,300);
    return {format:FORMAT,width:cardWidth,
        height:Math.min(available,cardWidth*1.54)};
}
function selectedCard(reading,index) {
    if(!reading || reading.ready!==true ||
       !Array.isArray(reading.cards) ||
       !Number.isInteger(index)||index<0||
       index>=reading.cards.length)return null;
    var card=reading.cards[index];
    return card && typeof card.id==="string" &&
           typeof card.title==="string" &&
           typeof card.position==="string" &&
           typeof card.reversed==="boolean" ? card : null;
}
function previewByClick(entries,id) {
    if(!Array.isArray(entries)||typeof id!=="string"||!id)return null;
    for(var i=0;i<entries.length;i++){
        var row=entries[i];
        if(row && row.id===id)return row;
    }
    return null;
}
