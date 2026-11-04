.pragma library

// Web Mercator (EPSG:3857) coordinates for interactive street tiles.
// Separate from Company's legacy equirectangular Natural Earth reference map.
var maxLat = 85.05112878;
function clamp(n,lo,hi) {return Math.max(lo,Math.min(hi,n));}
function zoomLevel(z) {
    var n=Number(z);
    return isFinite(n) ? clamp(Math.round(n),3,17) : 10;
}
function world(lon,lat,z) {
    var size=256*Math.pow(2,zoomLevel(z));
    var l=clamp(Number(lat),-maxLat,maxLat);
    var sin=Math.sin(l*Math.PI/180);
    return {
        x:clamp((Number(lon)+180)/360,0,1)*size,
        y:clamp(0.5-Math.log((1+sin)/(1-sin))/(4*Math.PI),0,1)*size
    };
}
function longitude(x,z) {
    return clamp(x/(256*Math.pow(2,zoomLevel(z)))*360-180,-180,180);
}
function latitude(y,z) {
    var t=Math.PI*(1-2*y/(256*Math.pow(2,zoomLevel(z))));
    return Math.atan(Math.sinh(t))*180/Math.PI;
}
function screen(lon,lat,width,height,z,centerLon,centerLat) {
    var p=world(lon,lat,z),c=world(centerLon,centerLat,z);
    return {x:width/2+p.x-c.x,y:height/2+p.y-c.y};
}
function invert(px,py,width,height,z,centerLon,centerLat) {
    if(!(width>0 && height>0))return null;
    var c=world(centerLon,centerLat,z);
    return {
        lon:longitude(c.x+px-width/2,z),
        lat:latitude(c.y+py-height/2,z)
    };
}
function pan(dx,dy,width,height,z,centerLon,centerLat) {
    return invert(width/2-dx,height/2-dy,width,height,z,centerLon,centerLat);
}
function zoomAt(px,py,width,height,z,centerLon,centerLat,direction) {
    var current=zoomLevel(z);
    var next=zoomLevel(current+(direction>0?1:-1));
    var underCursor=invert(px,py,width,height,current,centerLon,centerLat);
    if(!underCursor)return {lon:centerLon,lat:centerLat,zoom:current};
    var p=world(underCursor.lon,underCursor.lat,next);
    return {
        lon:longitude(p.x-(px-width/2),next),
        lat:latitude(p.y-(py-height/2),next),
        zoom:next
    };
}
function tilePosition(x,y,z,width,height,centerLon,centerLat) {
    var c=world(centerLon,centerLat,z);
    return {x:x*256-c.x+width/2,y:y*256-c.y+height/2};
}
