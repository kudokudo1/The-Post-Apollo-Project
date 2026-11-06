.pragma library

// M7c // Pure viewport math for the MAGICK annual lunar/solar wheel.
// Coordinates are in Canvas pixels. Rendering/data source stay unchanged.
var MIN_ZOOM=1.0;
var MAX_ZOOM=8.0;
var DEFAULT_ZOOM=1.6;
function finite(value){
    return typeof value==="number"&&isFinite(value);
}
function clamp(value,min,max){
    return Math.max(min,Math.min(max,value));
}
function fitRadius(width,height){
    if(!finite(width)||!finite(height)||width<=0||height<=0)return 5;
    return Math.max(5,Math.min(width-8,height-8)*0.47);
}
function panLimit(radius,zoom){
    if(!finite(radius)||radius<=0||!finite(zoom))return 0;
    return Math.max(0,radius*(clamp(zoom,MIN_ZOOM,MAX_ZOOM)-1)+8);
}
function boundedPan(x,y,radius,zoom){
    var limit=panLimit(radius,zoom);
    return {x:clamp(finite(x)?x:0,-limit,limit),
            y:clamp(finite(y)?y:0,-limit,limit)};
}
function zoomAt(zoom,panX,panY,factor,pointerX,pointerY,width,height,radius){
    if(!finite(zoom)||!finite(factor)||factor<=0
       ||!finite(width)||!finite(height)||width<=0||height<=0)
       return null;
    var old=clamp(zoom,MIN_ZOOM,MAX_ZOOM);
    var next=clamp(old*factor,MIN_ZOOM,MAX_ZOOM);
    var px=finite(pointerX)?pointerX:width/2;
    var py=finite(pointerY)?pointerY:height/2;
    var sx=finite(panX)?panX:0,sy=finite(panY)?panY:0;
    var ratio=next/old;
    var desiredX=(px-width/2)*(1-ratio)+sx*ratio;
    var desiredY=(py-height/2)*(1-ratio)+sy*ratio;
    var bounded=boundedPan(desiredX,desiredY,radius,next);
    return {zoom:next,panX:bounded.x,panY:bounded.y};
}
function inversePoint(x,y,width,height,panX,panY,zoom){
    if(![x,y,width,height,panX,panY,zoom].every(finite)||zoom<=0)
        return null;
    return {x:(x-width/2-panX)/zoom,y:(y-height/2-panY)/zoom};
}
